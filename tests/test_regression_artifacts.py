import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
from sklearn.ensemble import RandomForestRegressor

from src.ml.persist_regression import (
    ARTIFACTS, PREDICTION_COLUMNS, _write_atomic, persist_regression_evaluation,
    sha256, verify_regression_artifacts,
)
from src.ml.train_model import FEATURES, split_country_data


class RegressionArtifactTests(unittest.TestCase):
    def setUp(self):
        self.sandbox = tempfile.TemporaryDirectory(prefix='tokyo-artifact-test-')
        self.addCleanup(self.sandbox.cleanup)
        self.base = Path(self.sandbox.name)
        self.root = self.base / 'repository'
        self.root.mkdir()
        self.source = self.root / 'features.csv'
        self.data = pd.DataFrame([
            {'country': f'Country {i:02d}', **{feature: i + j + 1 for j, feature in enumerate(FEATURES)},
             'Total': float(i + 10)} for i in range(30)
        ])
        self.data.to_csv(self.source, index=False)
        self.models = {'Random Forest': RandomForestRegressor(n_estimators=5, random_state=42, n_jobs=1)}

    def save(self):
        return persist_regression_evaluation(self.source, self.root, backup_root=self.base, candidates=self.models)

    def verify(self, digest):
        return verify_regression_artifacts(self.root, self.source, trusted_model_sha256=digest)

    def test_save_reload_report_predictions_and_backup(self):
        stale = self.root / ARTIFACTS[0]
        stale.parent.mkdir()
        stale.write_bytes(b'old model: never deserialize this test fixture')
        previous_hash = sha256(stale)
        result, report, recovery = self.save()
        self.assertEqual(sha256(recovery / 'backup' / ARTIFACTS[0]), previous_hash)
        manifest = json.loads((recovery / 'backup_manifest.json').read_text())
        self.assertEqual(manifest['original_sha256'][str(ARTIFACTS[0])], previous_hash)
        self.assertEqual(report['source_dataset']['sha256'], sha256(self.source))
        self.assertEqual(report['split']['training_count'], 24)
        self.assertEqual(report['split']['holdout_count'], 6)
        self.assertEqual(report['selected_model'], 'Random Forest')
        self.assertEqual(report['features'], FEATURES)
        self.assertEqual(len(report['cross_validation']['fold_metrics']), 5)
        self.assertIn('python', report['versions'])
        self.assertIn('scikit-learn', report['versions'])
        self.assertTrue(any('already inspected' in text for text in report['limitations']))
        predictions = pd.read_csv(self.root / ARTIFACTS[2], float_precision='round_trip')
        self.assertEqual(list(predictions), PREDICTION_COLUMNS)
        self.assertEqual(predictions.country.tolist(), sorted(result.test_countries))
        self.assertEqual(self.verify(report['model_artifact']['sha256']), report)
        training, holdout = split_country_data(self.data)
        self.assertEqual(result.model.tokyo_training_provenance_['train_countries'], list(training.country))
        self.assertFalse(set(training.country) & set(holdout.country))
        self.assertTrue(all(len(sample) == len(training) for sample in result.model.estimators_samples_))

    def test_reproducibility_of_saved_files(self):
        _, first, _ = self.save()
        first_hashes = {str(p): sha256(self.root / p) for p in ARTIFACTS}
        _, second, _ = self.save()
        self.assertEqual(first, second)
        self.assertEqual(first_hashes, {str(p): sha256(self.root / p) for p in ARTIFACTS})

    def test_model_checksum_checked_before_deserialization(self):
        _, report, _ = self.save()
        (self.root / ARTIFACTS[0]).write_bytes(b'untrusted replacement')
        with patch('joblib.load', side_effect=AssertionError('Must not load mismatched model')) as load:
            with self.assertRaisesRegex(ValueError, 'SHA256'):
                self.verify(report['model_artifact']['sha256'])
            load.assert_not_called()

    def test_prediction_and_report_schema_tampering_rejected(self):
        _, report, _ = self.save()
        path = self.root / ARTIFACTS[1]
        altered = dict(report, features=list(reversed(FEATURES)))
        path.write_text(json.dumps(altered))
        with self.assertRaisesRegex(ValueError, 'schema'):
            self.verify(report['model_artifact']['sha256'])
        path.write_text(json.dumps(report))
        predictions = pd.read_csv(self.root / ARTIFACTS[2])
        predictions.loc[0, 'predicted_total'] += 100
        predictions.to_csv(self.root / ARTIFACTS[2], index=False)
        with self.assertRaisesRegex(ValueError, 'Prediction CSV SHA256'):
            self.verify(report['model_artifact']['sha256'])
        # Even updating the CSV checksum cannot hide mismatched model predictions.
        report['predictions_artifact']['sha256'] = sha256(self.root / ARTIFACTS[2])
        path.write_text(json.dumps(report))
        with self.assertRaises(AssertionError):
            self.verify(report['model_artifact']['sha256'])

    def test_changed_source_is_rejected(self):
        _, report, _ = self.save()
        self.source.write_text(self.source.read_text() + '\n')
        with self.assertRaisesRegex(ValueError, 'Source dataset SHA256'):
            self.verify(report['model_artifact']['sha256'])

    def test_failed_replacement_rolls_back_all_prior_artifacts(self):
        originals = {}
        for i, relative in enumerate(ARTIFACTS):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            originals[relative] = f'prior artifact {i}'.encode()
            path.write_bytes(originals[relative])
        calls = 0

        def fail_second_write(path, content):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError('Simulated output failure')
            return _write_atomic(path, content)

        with patch('src.ml.persist_regression._write_atomic', side_effect=fail_second_write):
            with self.assertRaisesRegex(OSError, 'Simulated'):
                self.save()
        for relative, content in originals.items():
            self.assertEqual((self.root / relative).read_bytes(), content)
        recovery = next(self.base.glob('tokyo-step17-*'))
        self.assertTrue((recovery / 'backup' / ARTIFACTS[0]).exists())

    def test_invalid_source_does_not_replace_existing_model(self):
        path = self.root / ARTIFACTS[0]
        path.parent.mkdir()
        path.write_bytes(b'original')
        self.data.drop(columns=FEATURES[0]).to_csv(self.source, index=False)
        with self.assertRaisesRegex(ValueError, 'schema'):
            self.save()
        self.assertEqual(path.read_bytes(), b'original')
        self.assertFalse((self.root / ARTIFACTS[1]).exists())


if __name__ == '__main__':
    unittest.main()
