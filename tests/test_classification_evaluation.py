import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score, average_precision_score

from src.ml.classify_medal_performance import (
    CLASS_ORDER, FEATURES, classification_metrics, classification_model,
    create_classes, evaluate_classification, validate_classification_input,
)


def data():
    totals = [0] * 13 + [3] * 12 + [10] * 10
    return pd.DataFrame([{'country': f'Country {i:02}', 'Total': total,
                          **{c: (i + j) % 11 for j, c in enumerate(FEATURES)}}
                         for i, total in enumerate(totals)])


def forest():
    return RandomForestClassifier(n_estimators=5, max_depth=8, min_samples_leaf=2,
                                  class_weight='balanced', random_state=42, n_jobs=1)


class RecordingClassifier(ClassifierMixin, BaseEstimator):
    events = []

    def fit(self, X, y):
        self.classes_ = np.array(CLASS_ORDER[::-1])
        self.training_ = set(X.index)
        type(self).events.append(('fit', tuple(X.index)))
        return self

    def predict(self, X):
        assert not self.training_ & set(X.index)
        type(self).events.append(('predict', tuple(X.index)))
        return np.repeat('High Medal', len(X))

    def predict_proba(self, X):
        assert not self.training_ & set(X.index)
        type(self).events.append(('probability', tuple(X.index)))
        return np.tile([.7, .2, .1], (len(X), 1))


class ClassificationEvaluationTests(unittest.TestCase):
    def test_exact_target_boundaries_and_integer_float_nullable_types(self):
        for dtype in ['int64', 'float64', 'Int64', 'Float64']:
            self.assertEqual(create_classes(pd.DataFrame({'Total': pd.Series([0, 1, 9, 10], dtype=dtype)})).tolist(),
                             ['No Medal', 'Medal', 'Medal', 'High Medal'])

    def test_invalid_targets_and_numeric_types(self):
        for value in [-1, -.5, .5, 9.5, np.nan, np.inf, -np.inf, True, '1', 1+0j, None]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                create_classes(pd.DataFrame({'Total': [value]}))
        for column in FEATURES:
            for value in [-1, .5, np.inf, np.nan, True, '2', 2+0j]:
                bad = data(); bad[column] = value
                with self.subTest(column=column, value=value), self.assertRaises(ValueError):
                    validate_classification_input(bad)

    def test_schema_country_validation_and_normalization_collisions(self):
        invalid = [None, data().drop(columns='Total'), data().drop(columns=FEATURES[0]),
                   data().rename(columns={FEATURES[0]: FEATURES[1]})]
        for country in ['', '  ', None, 42]:
            bad = data(); bad['country'] = bad.country.astype(object)
            bad.loc[0, 'country'] = country; invalid.append(bad)
        bad = data(); bad.loc[1, 'country'] = ' Country 00 '; invalid.append(bad)
        bad = data(); bad.loc[0, 'country'] = 'Unknown �'; invalid.append(bad)
        for bad in invalid:
            with self.subTest(), self.assertRaises(ValueError):
                validate_classification_input(bad)
        bad = data(); bad.loc[0, 'country'] = ' Country 00 '
        ordered, _ = validate_classification_input(bad)
        self.assertEqual(ordered.country.iloc[0], 'Country 00')

    def test_insufficient_or_missing_classes(self):
        for bad in [data().iloc[:25], data().iloc[:-6], data().iloc[:0]]:
            with self.assertRaisesRegex(ValueError, 'at least 5'):
                evaluate_classification(bad)

    def test_class_alignment_and_five_training_only_fits(self):
        RecordingClassifier.events = []
        result = evaluate_classification(data(), estimator=RecordingClassifier())
        self.assertEqual(result.class_order, CLASS_ORDER)
        for label, value in zip(CLASS_ORDER, [.1, .2, .7]):
            np.testing.assert_allclose(result.predictions['model_probability_' + label], value)
        events = RecordingClassifier.events
        self.assertEqual([e[0] for e in events], ['fit', 'predict', 'probability'] * 5)
        seen = []
        for i, partition in enumerate(result.fold_assignments):
            train, validation = set(partition['train_countries']), set(partition['validation_countries'])
            self.assertFalse(train & validation)
            self.assertEqual(train | validation, set(data().country))
            seen.extend(validation)
            self.assertEqual(len(events[i * 3][1]), len(train))
        self.assertCountEqual(seen, data().country)

    def test_repeated_and_shuffled_inputs_reproduce_without_mutation(self):
        original = data(); before = original.copy(deep=True)
        first = evaluate_classification(original, estimator=forest())
        second = evaluate_classification(original.sample(frac=1, random_state=9), estimator=forest())
        pd.testing.assert_frame_equal(original, before)
        pd.testing.assert_frame_equal(first.predictions, second.predictions)
        self.assertEqual(first.fold_assignments, second.fold_assignments)
        self.assertEqual(first.model_metrics, second.model_metrics)
        self.assertEqual(first.fold_metrics, second.fold_metrics)

    def test_fold_specific_majority_baseline(self):
        result = evaluate_classification(data(), estimator=forest())
        truth = create_classes(data()); truth.index = data().country
        majorities = []
        for partition in result.fold_assignments:
            counts = truth.loc[list(partition['train_countries'])].value_counts()
            # DummyClassifier uses lexical class order to break majority ties.
            majority = sorted(counts[counts.eq(counts.max())].index)[0]
            majorities.append(majority)
            rows = result.predictions.set_index('country').loc[list(partition['validation_countries'])]
            self.assertTrue(rows.baseline_predicted_class.eq(majority).all())
            for label in CLASS_ORDER:
                self.assertTrue(rows['baseline_probability_' + label].eq(float(label == majority)).all())
        self.assertGreater(len(set(majorities)), 1)  # Full-data majority would fail this fixture.

    def test_confusion_and_all_metrics_reproduce(self):
        result = evaluate_classification(data(), estimator=forest())
        for name, metrics in [('model', result.model_metrics), ('baseline', result.baseline_metrics)]:
            rows = result.predictions; y = rows.actual_class; pred = rows[name + '_predicted_class']
            report = classification_report(y, pred, labels=CLASS_ORDER, output_dict=True, zero_division=0)
            self.assertEqual(metrics['confusion_matrix'], confusion_matrix(y, pred, labels=CLASS_ORDER).tolist())
            self.assertEqual(metrics['accuracy'], report['accuracy'])
            for aggregate in ['macro', 'weighted']:
                for key, source in [('precision', 'precision'), ('recall', 'recall'), ('f1', 'f1-score')]:
                    self.assertAlmostEqual(metrics[aggregate + '_' + key], report[aggregate + ' avg'][source])
            for label in CLASS_ORDER:
                binary = y.eq(label); probability = rows[name + '_probability_' + label]
                self.assertAlmostEqual(metrics['per_class'][label]['roc_auc_ovr'], roc_auc_score(binary, probability))
                self.assertAlmostEqual(metrics['per_class'][label]['average_precision'], average_precision_score(binary, probability))
        self.assertEqual(len(result.fold_metrics), 10)
        for entry in result.fold_metrics:
            subset = result.predictions.loc[result.predictions.fold.eq(entry['fold'])]; name = entry['estimator']
            self.assertEqual(entry['metrics'], classification_metrics(subset.actual_class,
                subset[name + '_predicted_class'], subset[[name + '_probability_' + c for c in CLASS_ORDER]]))

    def test_undefined_metrics_and_invalid_labels_probabilities(self):
        metrics = classification_metrics(['No Medal'] * 2, ['No Medal'] * 2, [[1, 0, 0]] * 2)
        self.assertIsNone(metrics['macro_roc_auc_ovr'])
        self.assertIsNone(metrics['macro_average_precision'])
        self.assertIsNone(metrics['per_class']['Medal']['precision'])
        self.assertIn('Medal: precision', metrics['undefined_metrics'])
        for actual, predicted, probability in [(['bad'], ['No Medal'], [[1, 0, 0]]),
                (['Medal'], ['bad'], [[1, 0, 0]]), (['Medal'], ['Medal'], [[1, 1, 0]]),
                (['Medal'], ['Medal'], [[np.nan, 0, 1]])]:
            with self.assertRaises(ValueError):
                classification_metrics(actual, predicted, probability)

    def test_no_artifact_writes(self):
        with patch('builtins.open', side_effect=AssertionError('File access')), \
             patch('joblib.dump', side_effect=AssertionError('Model write')), \
             patch('pandas.DataFrame.to_csv', side_effect=AssertionError('CSV write')), \
             patch('pathlib.Path.mkdir', side_effect=AssertionError('Directory write')), \
             patch('pathlib.Path.write_text', side_effect=AssertionError('Report write')):
            evaluate_classification(data(), estimator=RecordingClassifier())

    def test_prespecified_model_parameters(self):
        params = classification_model().get_params()
        for key, value in dict(n_estimators=300, max_depth=8, min_samples_leaf=2,
                               class_weight='balanced', random_state=42, n_jobs=-1).items():
            self.assertEqual(params[key], value)


if __name__ == '__main__':
    unittest.main()
