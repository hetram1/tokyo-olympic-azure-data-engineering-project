"""Persist OOF evidence and a distinct full-data demonstration classifier."""

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
from sklearn.base import clone
from sklearn.model_selection import StratifiedKFold

from src.ml.classify_medal_performance import (
    CLASS_ORDER, DATA_PATH, FEATURES, N_SPLITS, RANDOM_STATE, TARGET,
    classification_metrics, classification_model, evaluate_classification,
    validate_classification_input,
)

ARTIFACTS = (Path('models/medal_classification_model.joblib'),
             Path('reports/classification_evaluation.json'),
             Path('reports/classification_oof_predictions.csv'))
CLASS_DEFINITIONS = {'No Medal': 'Total = 0', 'Medal': '1 <= Total <= 9', 'High Medal': 'Total >= 10'}
LIMITATIONS = [
    'Exploratory same-Olympics evaluation; not future-Olympics forecasting or independent external validation.',
    'Data and CV results were already inspected; no hyperparameter tuning or model selection in this run.',
    'Small skewed classes; athlete-name proxies, source coverage and absent-medal-row zero assumptions limit validity.',
    'Pre-event feature availability is unverified; probabilities are not established as calibrated.',
    'Final full-data model is for demonstration/inference only; its predictions are not OOF evaluation evidence.',
    'Native libraries/platforms and source/code/environment differences can affect reproducibility.',
]
CV = {'splitter': 'StratifiedKFold', 'n_splits': N_SPLITS, 'shuffle': True,
      'random_state': RANDOM_STATE, 'ordering': 'normalized country key ascending'}
PROVENANCE = {'evaluation': 'Step 20 evaluator; one training-only fit per fold; pooled OOF metrics',
              'final_model': 'Separate fit on all validated countries; demonstration/inference only',
              'baseline': 'Most-frequent class fitted independently on each identical training fold; lexical ties',
              'aggregation': 'Pooled OOF metrics; fold metrics also retained; no in-sample performance scores'}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _code_hashes():
    return {name: sha256(Path(__file__).with_name(name))
            for name in ('classify_medal_performance.py', 'persist_classification.py')}


def _versions():
    return {'python': platform.python_version(), **{name: importlib.metadata.version(name)
            for name in ('numpy', 'pandas', 'scipy', 'scikit-learn', 'joblib')}}


def _equal(actual, expected):
    """Compare JSON-safe nested evidence without rounding metrics."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or actual.keys() != expected.keys():
            raise ValueError('Evidence metadata keys differ')
        for key in expected:
            _equal(actual[key], expected[key])
    elif isinstance(expected, (list, tuple)):
        if not isinstance(actual, (list, tuple)) or len(actual) != len(expected):
            raise ValueError('Evidence sequence differs')
        for a, b in zip(actual, expected):
            _equal(a, b)
    elif isinstance(expected, float):
        if not isinstance(actual, (int, float)) or not np.isclose(actual, expected, rtol=1e-12, atol=1e-12):
            raise ValueError('Evidence numeric value differs')
    elif actual != expected:
        raise ValueError('Evidence value differs')


def _columns():
    return ['country', 'actual_total', 'actual_class', 'fold',
            *[column for name in ('model', 'baseline') for column in
              [name + '_predicted_class', *[name + '_probability_' + c for c in CLASS_ORDER]]]]


def _atomic_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
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
            temporary.unlink()  # Only this operation's unfinished temporary file.


def verify_classification_artifacts(output_root, source_path, *, trusted_model_sha256,
                                    expected_evaluation=None, expected_parameters=None):
    """Reload only this run's trusted model, after checking its known digest.

    A digest is an identity check, not permission to load arbitrary pickle files.
    This verifier reconstructs metrics/memberships, not new fold models. During
    persistence expected_evaluation also binds saved CSV values to the live OOF run.
    """
    root, source = Path(output_root), Path(source_path)
    report = json.loads((root / ARTIFACTS[1]).read_text())
    if (sha256(root / ARTIFACTS[0]) != trusted_model_sha256
            or report['artifacts']['model']['sha256'] != trusted_model_sha256):
        raise ValueError('Trusted model SHA256 mismatch; do not deserialize')
    if report['artifacts']['predictions']['sha256'] != sha256(root / ARTIFACTS[2]):
        raise ValueError('Prediction CSV SHA256 mismatch')
    if report['dataset']['sha256'] != sha256(source):
        raise ValueError('Dataset SHA256 mismatch')
    ordered, labels = validate_classification_input(pd.read_csv(source))
    expected_metadata = {'schema_version': 1, 'class_order': list(CLASS_ORDER), 'features': FEATURES,
        'target': TARGET, 'class_definitions': CLASS_DEFINITIONS, 'cv': CV,
        'class_distribution': {c: int(labels.eq(c).sum()) for c in CLASS_ORDER},
        'feature_dtypes': {c: str(ordered[c].dtype) for c in FEATURES},
        'versions': _versions(), 'code_sha256': _code_hashes(), 'limitations': LIMITATIONS,
        'provenance': PROVENANCE}
    for key, value in expected_metadata.items():
        _equal(report[key], value)
    _equal(report['dataset'], {'path': str(source.resolve()), 'sha256': sha256(source), 'rows': len(ordered)})
    for key, path in [('model', ARTIFACTS[0]), ('predictions', ARTIFACTS[2])]:
        _equal(report['artifacts'][key]['path'], str(path))
    rows = pd.read_csv(root / ARTIFACTS[2], float_precision='round_trip')
    if list(rows.columns) != _columns() or rows.isna().any().any():
        raise ValueError('Invalid prediction schema or missing values')
    if rows.country.tolist() != ordered.country.tolist():
        raise ValueError('OOF countries must cover exactly the sorted source countries')
    np.testing.assert_array_equal(rows.actual_total, ordered[TARGET])
    np.testing.assert_array_equal(rows.actual_class, labels)
    if expected_evaluation is not None:
        pd.testing.assert_frame_equal(rows, expected_evaluation.predictions[_columns()], check_dtype=False,
                                      rtol=1e-12, atol=1e-12)
    memberships, folds = [], []
    seen = np.zeros(len(rows), dtype=int)
    for fold, (train, validation) in enumerate(StratifiedKFold(
            n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE).split(ordered[FEATURES], labels), 1):
        memberships.append({'fold': fold, 'train_countries': list(ordered.country.iloc[train]),
                            'validation_countries': list(ordered.country.iloc[validation])})
        if not rows.fold.iloc[validation].eq(fold).all() or np.intersect1d(train, validation).size:
            raise ValueError('OOF fold assignment differs from training-only CV')
        seen[validation] += 1
        counts = labels.iloc[train].value_counts()
        majority = sorted(counts[counts.eq(counts.max())].index)[0]
        for name in ('model', 'baseline'):
            part = rows.iloc[validation]
            probabilities = part[[name + '_probability_' + c for c in CLASS_ORDER]].to_numpy()
            predicted = part[name + '_predicted_class']
            if name == 'baseline':
                np.testing.assert_array_equal(predicted, np.repeat(majority, len(part)))
                np.testing.assert_array_equal(probabilities,
                    np.tile([float(c == majority) for c in CLASS_ORDER], (len(part), 1)))
            # Tied maxima may legitimately use the estimator's lexical ordering.
            chosen = np.array([CLASS_ORDER.index(c) for c in predicted])
            if not np.allclose(probabilities[np.arange(len(part)), chosen], probabilities.max(axis=1),
                               rtol=1e-12, atol=1e-12):
                raise ValueError('Probability/class alignment mismatch')
            folds.append({'fold': fold, 'estimator': name, 'training_count': len(train),
                          'validation_count': len(validation), 'metrics': classification_metrics(
                              part.actual_class, predicted, probabilities)})
    if not (seen == 1).all():
        raise ValueError('Incomplete OOF coverage')
    _equal(report['fold_memberships'], memberships)
    _equal(report['fold_metrics'], folds)
    for name in ('model', 'baseline'):
        _equal(report['pooled_metrics'][name], classification_metrics(rows.actual_class,
            rows[name + '_predicted_class'], rows[[name + '_probability_' + c for c in CLASS_ORDER]]))
    # The full-data model is checked for schema/provenance and inference replay,
    # never used to reconstruct or score the OOF evidence.
    model = joblib.load(root / ARTIFACTS[0])
    _equal(report['model_name'], type(model).__module__ + '.' + type(model).__name__)
    _equal(report['model_parameters'], model.get_params(deep=False))
    if expected_parameters is not None:
        _equal(report['model_parameters'], expected_parameters)
    _equal(model.feature_names_in_.tolist(), FEATURES)
    _equal(int(model.n_features_in_), len(FEATURES))
    _equal(model.classes_.tolist(), sorted(CLASS_ORDER))
    _equal(report['final_model'], {'purpose': PROVENANCE['final_model'], 'training_count': len(ordered),
        'train_countries': ordered.country.tolist(), 'native_class_order': model.classes_.tolist()})
    _equal(model.tokyo_classification_provenance_, {'source_sha256': report['dataset']['sha256'],
        'training_count': len(ordered), 'train_countries': ordered.country.tolist(),
        'purpose': PROVENANCE['final_model']})
    if any(len(sample) != len(ordered) for sample in model.estimators_samples_):
        raise ValueError('Final forest fit population differs')
    _equal(report['inference_replay']['predicted_classes'], model.predict(ordered[FEATURES]).tolist())
    probability = model.predict_proba(ordered[FEATURES])
    classification_metrics(labels, model.predict(ordered[FEATURES]),
        probability[:, [list(model.classes_).index(c) for c in CLASS_ORDER]])
    np.testing.assert_allclose(probability, report['inference_replay']['native_probabilities'], rtol=1e-12, atol=1e-12)
    return report


def persist_classification_evaluation(source_path=DATA_PATH, output_root=Path('.'), *,
                                      backup_root=None, estimator=None):
    """Evaluate once, fit a separate final model, stage/verify and replace with rollback.

    Estimator injection is for small synthetic tests only; CLI uses frozen settings.
    Backups are outside output_root, retained even when staging or verification fails.
    """
    source, root = Path(source_path).resolve(), Path(output_root).resolve()
    if source in [root / path for path in ARTIFACTS]:
        raise ValueError('Source must not be an output artifact')
    work = Path(tempfile.mkdtemp(prefix='tokyo-classification-', dir=backup_root)).resolve()
    if work == root or root in work.parents:
        raise ValueError('Backup directory must be outside output repository')
    originals = {}
    for path in ARTIFACTS:
        target = root / path
        if target.is_symlink():
            raise ValueError('Refusing to replace a symlink artifact')
        originals[str(path)] = sha256(target) if target.exists() else None
        if target.exists():
            destination = work / 'backup' / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, destination)
            if sha256(destination) != originals[str(path)]:
                raise ValueError('Backup checksum mismatch')
    (work / 'backup_manifest.json').write_text(json.dumps(originals, indent=2) + '\n')
    digest = sha256(source)
    data = pd.read_csv(source)
    ordered, labels = validate_classification_input(data)
    candidate = classification_model() if estimator is None else estimator
    evaluation = evaluate_classification(data, estimator=candidate)
    final = clone(candidate).fit(ordered[FEATURES], labels)
    final.tokyo_classification_provenance_ = {'source_sha256': digest,
        'training_count': len(ordered), 'train_countries': ordered.country.tolist(),
        'purpose': PROVENANCE['final_model']}
    stage = work / 'staged'
    (stage / 'models').mkdir(parents=True)
    (stage / 'reports').mkdir(parents=True)
    evaluation.predictions[_columns()].to_csv(stage / ARTIFACTS[2], index=False, float_format='%.17g')
    joblib.dump(final, stage / ARTIFACTS[0], compress=3)
    model_digest = sha256(stage / ARTIFACTS[0])
    report = {'schema_version': 1, 'model_name': type(final).__module__ + '.' + type(final).__name__,
        'model_parameters': final.get_params(deep=False), 'class_order': list(CLASS_ORDER),
        'features': FEATURES, 'feature_dtypes': {c: str(ordered[c].dtype) for c in FEATURES},
        'target': TARGET, 'class_definitions': CLASS_DEFINITIONS,
        'dataset': {'path': str(source), 'sha256': digest, 'rows': len(ordered)},
        'cv': CV, 'class_distribution': evaluation.class_distribution,
        'pooled_metrics': {'model': evaluation.model_metrics, 'baseline': evaluation.baseline_metrics},
        'fold_metrics': evaluation.fold_metrics, 'fold_memberships': evaluation.fold_assignments,
        'versions': _versions(), 'code_sha256': _code_hashes(), 'provenance': PROVENANCE,
        'limitations': LIMITATIONS, 'artifacts': {
            'model': {'path': str(ARTIFACTS[0]), 'sha256': model_digest},
            'predictions': {'path': str(ARTIFACTS[2]), 'sha256': sha256(stage / ARTIFACTS[2])}},
        'final_model': {'purpose': PROVENANCE['final_model'], 'training_count': len(ordered),
            'train_countries': ordered.country.tolist(), 'native_class_order': final.classes_.tolist()},
        'inference_replay': {'predicted_classes': final.predict(ordered[FEATURES]).tolist(),
            'native_probabilities': final.predict_proba(ordered[FEATURES]).tolist()}}
    (stage / ARTIFACTS[1]).write_text(json.dumps(report, indent=2, sort_keys=True,
                                               ensure_ascii=False, allow_nan=False) + '\n')
    parameters = candidate.get_params(deep=False)
    verify_classification_artifacts(stage, source, trusted_model_sha256=model_digest,
                                   expected_evaluation=evaluation, expected_parameters=parameters)
    if sha256(source) != digest:
        raise ValueError('Source changed; outputs not replaced')
    for path in ARTIFACTS:
        target = root / path
        if (sha256(target) if target.exists() else None) != originals[str(path)]:
            raise ValueError('Concurrent artifact change; outputs not replaced')
    try:
        for path in ARTIFACTS:
            _atomic_write(root / path, (stage / path).read_bytes())
        report = verify_classification_artifacts(root, source, trusted_model_sha256=model_digest,
            expected_evaluation=evaluation, expected_parameters=parameters)
    except BaseException:
        for path in ARTIFACTS:
            if originals[str(path)] is not None:
                _atomic_write(root / path, (work / 'backup' / path).read_bytes())
            elif (root / path).exists():
                (root / path).unlink()  # Only a new output belonging to this failed transaction.
        raise
    (work / 'completed_sha256.json').write_text(json.dumps({str(p): sha256(root / p) for p in ARTIFACTS}, indent=2) + '\n')
    return evaluation, report, work


def main():
    _, report, recovery = persist_classification_evaluation()
    print('OOF evidence and separate full-data demonstration model saved and verified.')
    print('Recovery directory:', recovery)
    print(json.dumps(report['pooled_metrics'], indent=2))
    for path in ARTIFACTS:
        print(sha256(path), path)


if __name__ == '__main__':
    main()
