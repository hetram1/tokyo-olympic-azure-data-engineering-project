import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier

from src.ml.classify_medal_performance import FEATURES, CLASS_ORDER, evaluate_classification
from src.ml.persist_classification import (
    ARTIFACTS, _atomic_write, persist_classification_evaluation,
    sha256, verify_classification_artifacts,
)


class ClassificationArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='tokyo-classification-test-')
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / 'repository'
        self.root.mkdir()
        self.source = self.root / 'features.csv'
        self.data = pd.DataFrame([{'country': f'Country {i:02}', 'Total': [0, 3, 10][i % 3],
                                  **{c: (i + j) % 7 for j, c in enumerate(FEATURES)}}
                                 for i in range(30)])
        self.data.to_csv(self.source, index=False)
        self.model = RandomForestClassifier(n_estimators=5, max_depth=8, min_samples_leaf=2,
                                            class_weight='balanced', random_state=42, n_jobs=1)

    def save(self):
        return persist_classification_evaluation(self.source, self.root,
                                                 backup_root=self.base, estimator=self.model)

    def verify(self, digest):
        return verify_classification_artifacts(self.root, self.source, trusted_model_sha256=digest,
                                               expected_parameters=self.model.get_params(deep=False))

    def write_report(self, report):
        (self.root / ARTIFACTS[1]).write_text(json.dumps(report))

    def test_save_verify_metadata_and_retained_backups(self):
        originals = {}
        for path in ARTIFACTS:
            target = self.root / path; target.parent.mkdir(parents=True, exist_ok=True)
            originals[str(path)] = b'prior artifact, never deserialize'
            target.write_bytes(originals[str(path)])
        result, report, recovery = self.save()
        manifest = json.loads((recovery / 'backup_manifest.json').read_text())
        for path in ARTIFACTS:
            self.assertEqual((recovery / 'backup' / path).read_bytes(), originals[str(path)])
            self.assertEqual(manifest[str(path)], sha256(recovery / 'backup' / path))
        self.assertEqual(self.verify(report['artifacts']['model']['sha256']), report)
        self.assertEqual(report['dataset']['rows'], 30)
        self.assertEqual(report['class_order'], list(CLASS_ORDER))
        self.assertEqual(report['features'], FEATURES)
        self.assertIn('scikit-learn', report['versions'])
        self.assertIn('persist_classification.py', report['code_sha256'])
        self.assertIn('demonstration', report['final_model']['purpose'])
        self.assertEqual(len(report['fold_metrics']), 10)
        self.assertEqual(len(result.predictions), 30)

    def test_reproducible_artifact_bytes(self):
        _, first, _ = self.save()
        hashes = {str(p): sha256(self.root / p) for p in ARTIFACTS}
        _, second, _ = self.save()
        self.assertEqual(first, second)
        self.assertEqual(hashes, {str(p): sha256(self.root / p) for p in ARTIFACTS})

    def test_full_data_model_is_separate_from_oof_predictions(self):
        result, report, _ = self.save()
        digest = report['artifacts']['model']['sha256']
        self.assertEqual(sha256(self.root / ARTIFACTS[0]), digest)
        # This test loads only its own newly created model with a known digest.
        final = joblib.load(self.root / ARTIFACTS[0])
        self.assertEqual(final.tokyo_classification_provenance_['training_count'], 30)
        self.assertTrue(all(len(s) == 30 for s in final.estimators_samples_))
        replay = evaluate_classification(self.data, estimator=self.model)
        pd.testing.assert_frame_equal(result.predictions, replay.predictions)
        saved = pd.read_csv(self.root / ARTIFACTS[2], float_precision='round_trip')
        for c in CLASS_ORDER:
            np.testing.assert_allclose(saved['model_probability_' + c], replay.predictions['model_probability_' + c])
        oof = saved[['model_probability_' + c for c in CLASS_ORDER]].to_numpy()
        full = final.predict_proba(self.data[FEATURES])[:, [list(final.classes_).index(c) for c in CLASS_ORDER]]
        self.assertFalse(np.allclose(oof, full))
        self.verify(digest)  # Reconstructs pooled and fold metrics from the saved CSV.

    def test_model_hash_checked_before_loading(self):
        _, report, _ = self.save()
        (self.root / ARTIFACTS[0]).write_bytes(b'untrusted')
        with patch('joblib.load', side_effect=AssertionError('Unsafe load')) as load:
            with self.assertRaisesRegex(ValueError, 'Trusted model SHA256'):
                self.verify(report['artifacts']['model']['sha256'])
            load.assert_not_called()

    def test_csv_checksum_and_fold_tampering_rejected(self):
        _, report, _ = self.save()
        path = self.root / ARTIFACTS[2]
        rows = pd.read_csv(path, float_precision='round_trip')
        rows.loc[0, 'fold'] = 999
        rows.to_csv(path, index=False, float_format='%.17g')
        with self.assertRaisesRegex(ValueError, 'Prediction CSV SHA256'):
            self.verify(report['artifacts']['model']['sha256'])
        report['artifacts']['predictions']['sha256'] = sha256(path)
        self.write_report(report)
        with self.assertRaisesRegex(ValueError, 'fold assignment'):
            self.verify(report['artifacts']['model']['sha256'])

    def test_schema_metrics_and_metadata_tampering_rejected(self):
        _, report, _ = self.save()
        digest = report['artifacts']['model']['sha256']
        for key in ['class_order', 'features']:
            changed = json.loads(json.dumps(report)); changed[key].reverse(); self.write_report(changed)
            with self.assertRaises(ValueError):
                self.verify(digest)
        changed = json.loads(json.dumps(report)); changed['pooled_metrics']['model']['accuracy'] += .1
        self.write_report(changed)
        with self.assertRaisesRegex(ValueError, 'numeric'):
            self.verify(digest)
        changed = json.loads(json.dumps(report)); changed['final_model']['training_count'] = 20
        self.write_report(changed)
        with self.assertRaises(ValueError):
            self.verify(digest)
        self.write_report(report)
        self.source.write_text(self.source.read_text() + '\n')
        with self.assertRaisesRegex(ValueError, 'Dataset SHA256'):
            self.verify(digest)

    def test_probability_alignment_and_metric_reconstruction_reject_tampering(self):
        _, report, _ = self.save()
        path = self.root / ARTIFACTS[2]
        rows = pd.read_csv(path, float_precision='round_trip')
        # Preserve the checksum while injecting an invalid probability distribution.
        rows.loc[0, 'model_probability_No Medal'] = 2.0
        rows.to_csv(path, index=False, float_format='%.17g')
        report['artifacts']['predictions']['sha256'] = sha256(path); self.write_report(report)
        with self.assertRaises(ValueError):
            self.verify(report['artifacts']['model']['sha256'])

    def test_failed_replacement_restores_prior_outputs(self):
        originals = {}
        for i, path in enumerate(ARTIFACTS):
            target = self.root / path; target.parent.mkdir(parents=True, exist_ok=True)
            originals[path] = f'prior {i}'.encode(); target.write_bytes(originals[path])
        calls = 0

        def fail_second(path, content):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError('Simulated write failure')
            _atomic_write(path, content)

        with patch('src.ml.persist_classification._atomic_write', side_effect=fail_second):
            with self.assertRaisesRegex(OSError, 'Simulated'):
                self.save()
        for path, content in originals.items():
            self.assertEqual((self.root / path).read_bytes(), content)

    def test_staging_validation_failure_leaves_no_partial_outputs(self):
        with patch('src.ml.persist_classification.verify_classification_artifacts',
                   side_effect=ValueError('Simulated staging failure')):
            with self.assertRaisesRegex(ValueError, 'staging'):
                self.save()
        self.assertFalse(any((self.root / p).exists() for p in ARTIFACTS))

    def test_final_validation_failure_removes_only_new_transaction_outputs(self):
        original = verify_classification_artifacts
        calls = 0

        def fail_final(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise ValueError('Simulated final verification failure')
            return original(*args, **kwargs)

        with patch('src.ml.persist_classification.verify_classification_artifacts', side_effect=fail_final):
            with self.assertRaisesRegex(ValueError, 'final verification'):
                self.save()
        self.assertFalse(any((self.root / p).exists() for p in ARTIFACTS))
        self.assertTrue(self.source.exists())


if __name__ == '__main__':
    unittest.main()
