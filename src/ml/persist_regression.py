"""Persist and verify a trusted run of the existing regression evaluation."""

import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import tempfile

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import KFold

from src.ml.train_model import (
    DATA_PATH, FEATURES, RANDOM_STATE, TARGET, evaluate_regression,
    print_evaluation, regression_metrics, split_country_data,
)


ARTIFACTS = (
    Path('models/medal_prediction_model.joblib'),
    Path('reports/regression_evaluation.json'),
    Path('reports/regression_holdout_predictions.csv'),
)
PREDICTION_COLUMNS = ['country', 'actual_total', 'predicted_total', 'absolute_error']
LIMITATIONS = [
    'Same-Olympics country estimation, not prospective medal prediction.',
    'The holdout was already inspected in Step 16; it is not independent external validation.',
    'Small, skewed country sample; participation proxies and athlete-name identities are imperfect.',
    'Pre-event availability of participation features is unverified; no temporal or causal claim.',
    'Do not tune using holdout results or refit this evaluation artifact on all 206 countries.',
]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def training_fingerprint(training):
    records = training[['country', *FEATURES, TARGET]].to_csv(index=False, float_format='%.17g')
    return hashlib.sha256(records.encode('utf-8')).hexdigest()


def _write_atomic(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Temporary sibling permits atomic replacement even across filesystem mounts.
    descriptor, name = tempfile.mkstemp(prefix='.' + path.name + '-', dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, 'wb') as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()  # Only our own unfinished temporary file.


def verify_regression_artifacts(output_root, source_path, *, trusted_model_sha256):
    """Verify only a model created by this run, using its already-known digest.

    Never use this to deserialize an arbitrary existing joblib file. SHA256 checks
    corruption/identity; it does not establish trust in a third-party pickle.
    """
    root, source_path = Path(output_root), Path(source_path)
    report = json.loads((root / ARTIFACTS[1]).read_text())
    if report['features'] != FEATURES or report['target'] != TARGET:
        raise ValueError('Artifact feature/target schema does not match regression code')
    if report['source_dataset']['sha256'] != sha256(source_path):
        raise ValueError('Source dataset SHA256 mismatch')
    if sha256(root / ARTIFACTS[0]) != trusted_model_sha256 or report['model_artifact']['sha256'] != trusted_model_sha256:
        raise ValueError('Trusted model SHA256 mismatch; do not deserialize')
    if report['predictions_artifact']['sha256'] != sha256(root / ARTIFACTS[2]):
        raise ValueError('Prediction CSV SHA256 mismatch')
    data = pd.read_csv(source_path)
    training, holdout = split_country_data(data)
    split = report['split']
    if split['random_seed'] != RANDOM_STATE or split['test_size'] != 0.20 or split['cv_folds'] != 5:
        raise ValueError('Unexpected evaluation split configuration')
    if (split['train_countries'] != list(training.country) or split['holdout_countries'] != list(holdout.country)
            or split['training_count'] != len(training) or split['holdout_count'] != len(holdout)):
        raise ValueError('Artifact country partitions do not match the source split')
    if report['training_data_sha256'] != training_fingerprint(training):
        raise ValueError('Training data fingerprint mismatch')
    if report['source_dataset']['rows'] != len(data) or report['feature_dtypes'] != {
            c: str(training[c].dtype) for c in FEATURES}:
        raise ValueError('Source row count or feature dtypes differ from report')
    partitions = []
    for fold, (fit, validation) in enumerate(KFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE).split(training), 1):
        partitions.append({'fold': fold, 'train_countries': list(training.iloc[fit].country),
                           'validation_countries': list(training.iloc[validation].country)})
    if report['cross_validation']['partitions'] != partitions:
        raise ValueError('CV partitions differ from the training-only split')
    summary = pd.DataFrame(report['cross_validation']['summary'])
    folds = pd.DataFrame(report['cross_validation']['fold_metrics'])
    if folds.duplicated(['model', 'fold']).any() or len(folds) != 5 * len(summary):
        raise ValueError('Invalid model/fold result keys')
    for partition in partitions:
        fold = folds.loc[folds.fold.eq(partition['fold'])]
        if (set(fold.model) != set(summary.model)
                or not fold.train_rows.eq(len(partition['train_countries'])).all()
                or not fold.validation_rows.eq(len(partition['validation_countries'])).all()):
            raise ValueError('CV sample counts do not match training-only partitions')
    recomputed = folds.groupby('model').agg(
        mae_mean=('mae', 'mean'), mae_std=('mae', 'std'),
        rmse_mean=('rmse', 'mean'), rmse_std=('rmse', 'std'),
        r2_mean=('r2', 'mean'), r2_std=('r2', 'std'),
    ).sort_index()
    pd.testing.assert_frame_equal(recomputed, summary.set_index('model').sort_index()[recomputed.columns],
                                  rtol=1e-12, atol=1e-12)
    winner = summary.sort_values(['mae_mean', 'model']).iloc[0]['model']
    if winner != report['selected_model'] or report['holdout_metrics']['model'] != winner:
        raise ValueError('Selected model disagrees with training-only CV')
    predictions = pd.read_csv(root / ARTIFACTS[2], float_precision='round_trip')
    if list(predictions.columns) != PREDICTION_COLUMNS or predictions.country.duplicated().any():
        raise ValueError('Invalid holdout prediction schema/country keys')
    expected_countries = sorted(holdout.country)
    if predictions.country.tolist() != expected_countries or predictions.isna().any().any():
        raise ValueError('Holdout predictions must cover exactly the sorted holdout countries')
    if not np.isfinite(predictions[PREDICTION_COLUMNS[1:]].to_numpy(dtype=float)).all():
        raise ValueError('Predictions must be finite numeric values')
    held = holdout.set_index('country').loc[expected_countries]
    np.testing.assert_array_equal(predictions.actual_total, held[TARGET])
    # This is the newly generated model, whose digest was established before load.
    model = joblib.load(root / ARTIFACTS[0])
    if model.get_params(deep=False) != report['model_hyperparameters']:
        raise ValueError('Persisted model hyperparameters differ from report')
    model_class = type(model).__module__ + '.' + type(model).__name__
    if model_class != report['model_class']:
        raise ValueError('Persisted model class differs from report')
    if model.feature_names_in_.tolist() != FEATURES or model.n_features_in_ != len(FEATURES):
        raise ValueError('Persisted model input schema mismatch')
    provenance = model.tokyo_training_provenance_
    if provenance != {'source_sha256': report['source_dataset']['sha256'],
                      'training_sha256': report['training_data_sha256'],
                      'train_countries': split['train_countries'], 'training_count': len(training)}:
        raise ValueError('Persisted model training provenance mismatch')
    # Public forest bootstrap samples additionally confirm fit population size.
    if hasattr(model, 'estimators_samples_') and any(len(s) != len(training) for s in model.estimators_samples_):
        raise ValueError('Forest was not fitted on the reported training sample count')
    reloaded = model.predict(held[FEATURES])
    np.testing.assert_allclose(reloaded, predictions.predicted_total, rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(predictions.absolute_error,
                               np.abs(predictions.actual_total - predictions.predicted_total), rtol=1e-12, atol=1e-12)
    metrics = regression_metrics(predictions.actual_total, predictions.predicted_total)
    for key, value in metrics.items():
        if not np.isclose(value, report['holdout_metrics'][key], rtol=1e-12, atol=1e-12):
            raise ValueError(f'Prediction/report metric mismatch: {key}')
    return report


def persist_regression_evaluation(source_path=DATA_PATH, output_root=Path('.'), *, backup_root=None, candidates=None):
    """Evaluate once, stage/verify, then replace three outputs with rollback.

    candidates is an estimator-injection seam for fast tests, not a holdout-driven
    tuning interface. Normal CLI execution always uses the prespecified candidates.
    All prior artifacts and their digests are retained outside output_root.
    """
    source_path, root = Path(source_path).resolve(), Path(output_root).resolve()
    work = Path(tempfile.mkdtemp(prefix='tokyo-step17-', dir=backup_root))
    if work == root or root in work.parents:
        raise ValueError('Backup directory must be outside the output repository')
    backup, stage = work / 'backup', work / 'staged'
    originals = {}
    for relative in ARTIFACTS:
        target = root / relative
        if target.exists():
            destination = backup / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, destination)
            originals[str(relative)] = sha256(target)
            if sha256(destination) != originals[str(relative)]:
                raise ValueError(f'Backup checksum mismatch: {relative}')
        else:
            originals[str(relative)] = None
    manifest = {'original_sha256': originals, 'repository': str(root), 'source': str(source_path)}
    (work / 'backup_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    source_digest = sha256(source_path)
    data = pd.read_csv(source_path)
    result = evaluate_regression(data, candidates=candidates)
    training, _ = split_country_data(data)
    if tuple(training.country) != result.train_countries:
        raise ValueError('Evaluation training partition changed')
    fingerprint = training_fingerprint(training)
    result.model.tokyo_training_provenance_ = {
        'source_sha256': source_digest, 'training_sha256': fingerprint,
        'train_countries': list(result.train_countries), 'training_count': len(training),
    }
    (stage / 'models').mkdir(parents=True)
    (stage / 'reports').mkdir(parents=True)
    joblib.dump(result.model, stage / ARTIFACTS[0], compress=3)
    prediction_rows = result.predictions[PREDICTION_COLUMNS].sort_values('country').reset_index(drop=True)
    prediction_rows.to_csv(stage / ARTIFACTS[2], index=False, float_format='%.17g')
    model_digest = sha256(stage / ARTIFACTS[0])
    report = {
        'schema_version': 1,
        'selected_model': result.selected_name,
        'model_class': type(result.model).__module__ + '.' + type(result.model).__name__,
        'model_hyperparameters': result.model.get_params(deep=False),
        'features': FEATURES, 'feature_dtypes': {c: str(training[c].dtype) for c in FEATURES}, 'target': TARGET,
        'source_dataset': {'path': str(source_path), 'sha256': source_digest, 'rows': len(data)},
        'training_data_sha256': fingerprint,
        'split': {'random_seed': RANDOM_STATE, 'test_size': 0.20, 'cv_folds': 5,
                  'procedure': 'Sort by country; sklearn train_test_split; shuffled KFold on training only, seed 42',
                  'training_count': len(result.train_countries), 'holdout_count': len(result.test_countries),
                  'train_countries': list(result.train_countries), 'holdout_countries': list(result.test_countries)},
        'selection_criterion': 'Lowest mean training-only fold validation MAE; ties by alphabetical model name',
        'cross_validation': {'summary': result.validation_summary.to_dict('records'),
                             'fold_metrics': result.fold_metrics.to_dict('records'),
                             'partitions': result.cv_partitions,
                             'aggregation': 'Unweighted fold means and sample standard deviations'},
        'holdout_metrics': result.holdout_metrics,
        'model_artifact': {'path': str(ARTIFACTS[0]), 'sha256': model_digest},
        'predictions_artifact': {'path': str(ARTIFACTS[2]), 'sha256': sha256(stage / ARTIFACTS[2])},
        'versions': {'python': platform.python_version(), **{name: importlib.metadata.version(name)
                     for name in ['numpy', 'pandas', 'scipy', 'scikit-learn', 'xgboost', 'joblib']}},
        'limitations': LIMITATIONS,
    }
    (stage / ARTIFACTS[1]).write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + '\n')
    report = verify_regression_artifacts(stage, source_path, trusted_model_sha256=model_digest)
    if sha256(source_path) != source_digest:
        raise ValueError('Source changed during evaluation; outputs not replaced')
    for relative in ARTIFACTS:
        target = root / relative
        actual = sha256(target) if target.exists() else None
        if actual != originals[str(relative)]:
            raise ValueError(f'Concurrent change to {relative}; outputs not replaced')
    try:
        for relative in ARTIFACTS:
            _write_atomic(root / relative, (stage / relative).read_bytes())
        verify_regression_artifacts(root, source_path, trusted_model_sha256=model_digest)
    except BaseException:
        for relative in ARTIFACTS:
            if originals[str(relative)] is not None:
                _write_atomic(root / relative, (backup / relative).read_bytes())
            elif (root / relative).exists():
                (root / relative).unlink()  # Only a new artifact from this failed transaction.
        raise
    (work / 'completed_sha256.json').write_text(json.dumps({str(p): sha256(root / p) for p in ARTIFACTS}, indent=2) + '\n')
    return result, report, work


def main():
    result, report, recovery = persist_regression_evaluation()
    print_evaluation(result)
    print(f'\nRecovery directory: {recovery}')
    print(f'Model SHA256: {report["model_artifact"]["sha256"]}')
    print('Saved and verified:', ', '.join(str(p) for p in ARTIFACTS))


if __name__ == '__main__':
    main()
