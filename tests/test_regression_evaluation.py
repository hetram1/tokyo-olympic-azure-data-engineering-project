import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor

from src.ml.train_model import (
    FEATURES, TARGET, candidate_models, compare_training_models,
    evaluate_regression, regression_metrics, split_country_data,
)


def country_data():
    rows = []
    for i in range(30):
        rows.append({"country": f"Country {i:02d}", **{feature: i + j + 1
                     for j, feature in enumerate(FEATURES)}, TARGET: float(i + 10)})
    return pd.DataFrame(rows)


class RecordingRegressor(RegressorMixin, BaseEstimator):
    events = []

    def __init__(self, name="mean", constant=None):
        self.name = name
        self.constant = constant

    def fit(self, X, y):
        type(self).events.append((self.name, "fit", tuple(X.index)))
        self.value_ = float(y.mean()) if self.constant is None else self.constant
        return self

    def predict(self, X):
        type(self).events.append((self.name, "predict", tuple(X.index)))
        return np.full(len(X), self.value_)


class RegressionEvaluationTests(unittest.TestCase):
    def test_partitions_are_disjoint_and_cv_stays_inside_training(self):
        data = country_data()
        result = evaluate_regression(data, candidates={"Baseline": DummyRegressor()})
        train, test = set(result.train_countries), set(result.test_countries)
        self.assertFalse(train & test)
        self.assertEqual(train | test, set(data.country))
        validation_countries = []
        for fold in result.cv_partitions:
            fit, validation = set(fold["train_countries"]), set(fold["validation_countries"])
            self.assertFalse(fit & validation)
            self.assertEqual(fit | validation, train)
            self.assertFalse((fit | validation) & test)
            validation_countries.extend(fold["validation_countries"])
        self.assertCountEqual(validation_countries, result.train_countries)

    def test_reproducibility_including_reordered_input(self):
        candidates = {"Baseline": DummyRegressor(), "Forest": RandomForestRegressor(
            n_estimators=8, random_state=42, n_jobs=1)}
        first = evaluate_regression(country_data(), candidates=candidates)
        second = evaluate_regression(country_data().sample(frac=1, random_state=7), candidates=candidates)
        self.assertEqual(first.selected_name, second.selected_name)
        self.assertEqual(first.train_countries, second.train_countries)
        self.assertEqual(first.test_countries, second.test_countries)
        self.assertEqual(first.holdout_metrics, second.holdout_metrics)
        pd.testing.assert_frame_equal(first.validation_summary, second.validation_summary)
        pd.testing.assert_frame_equal(first.predictions, second.predictions)

    def test_selection_does_not_use_holdout_outcomes(self):
        data = country_data()
        candidates = {"Mean": DummyRegressor(), "Zero": DummyRegressor(strategy="constant", constant=0)}
        original = evaluate_regression(data, candidates=candidates)
        changed = data.copy()
        changed.loc[changed.country.isin(original.test_countries), TARGET] = 0
        altered = evaluate_regression(changed, candidates=candidates)
        self.assertEqual(original.selected_name, "Mean")
        self.assertEqual(altered.selected_name, "Mean")
        pd.testing.assert_frame_equal(original.validation_summary, altered.validation_summary)
        pd.testing.assert_frame_equal(original.fold_metrics, altered.fold_metrics)
        np.testing.assert_array_equal(original.predictions.predicted_total, altered.predictions.predicted_total)
        self.assertNotEqual(original.holdout_metrics["mae"], altered.holdout_metrics["mae"])
        # On altered holdout outcomes Zero would win; selection must still be Mean.
        self.assertGreater(altered.holdout_metrics["mae"], 0)

    def test_holdout_predicted_once_and_never_used_in_fit(self):
        RecordingRegressor.events = []
        data = country_data()
        training, holdout = split_country_data(data)
        result = evaluate_regression(data, candidates={
            "Mean": RecordingRegressor(), "Zero": RecordingRegressor("zero", 0),
        })
        holdout_indices = set(holdout.index)
        holdout_calls = []
        full_training_fits = []
        for name, event, indices in RecordingRegressor.events:
            indices = set(indices)
            if event == "fit":
                self.assertFalse(indices & holdout_indices)
                if indices == set(training.index):
                    full_training_fits.append(name)
            elif indices & holdout_indices:
                self.assertEqual(indices, holdout_indices)
                holdout_calls.append(name)
        self.assertEqual(full_training_fits, [result.model.name])
        self.assertEqual(holdout_calls, [result.model.name])

    def test_baseline_uses_each_fold_training_mean_and_final_training_mean(self):
        data = country_data()
        result = evaluate_regression(data, candidates={"Baseline": DummyRegressor(strategy="mean")})
        by_country = data.set_index("country")[TARGET]
        for partition, (_, metrics) in zip(result.cv_partitions, result.fold_metrics.iterrows()):
            fit_y = by_country.loc[list(partition["train_countries"])]
            validation_y = by_country.loc[list(partition["validation_countries"])]
            expected = regression_metrics(validation_y, [fit_y.mean()] * len(validation_y))
            for metric, value in expected.items():
                self.assertAlmostEqual(metrics[metric], value)
        final_mean = by_country.loc[list(result.train_countries)].mean()
        np.testing.assert_allclose(result.predictions.predicted_total, final_mean)
        self.assertAlmostEqual(result.model.constant_[0, 0], final_mean)

    def test_metrics_and_result_schemas(self):
        self.assertEqual(regression_metrics([0, 2], [1, 1]), {"mae": 1.0, "rmse": 1.0, "r2": 0.0})
        result = evaluate_regression(country_data(), candidates={"Baseline": DummyRegressor()})
        self.assertEqual(list(result.validation_summary), ["model", "mae_mean", "mae_std",
                         "rmse_mean", "rmse_std", "r2_mean", "r2_std"])
        self.assertEqual(list(result.fold_metrics), ["model", "fold", "train_rows", "validation_rows", "mae", "rmse", "r2"])
        self.assertEqual(set(result.holdout_metrics), {"model", "mae", "rmse", "r2"})
        self.assertEqual(list(result.predictions), ["country", "actual_total", "predicted_total", "residual", "absolute_error"])
        np.testing.assert_allclose(result.predictions.absolute_error, result.predictions.residual.abs())

    def test_default_candidates_and_deterministic_tie_break(self):
        models = candidate_models()
        self.assertEqual(list(models), ["Baseline", "Random Forest", "XGBoost"])
        self.assertEqual(models["Baseline"].strategy, "mean")
        for name in ("Random Forest", "XGBoost"):
            self.assertEqual(models[name].random_state, 42)
            self.assertEqual(models[name].n_jobs, 1)
        training, _ = split_country_data(country_data())
        selected, _, _, _, _ = compare_training_models(training, candidates={
            "Z": DummyRegressor(), "A": DummyRegressor()})
        self.assertEqual(selected, "A")

    def test_input_not_mutated_and_no_files_saved(self):
        data = country_data()
        original = data.copy(deep=True)
        with patch("joblib.dump", side_effect=AssertionError("Model write")), \
             patch("pandas.DataFrame.to_csv", side_effect=AssertionError("CSV write")), \
             patch("pathlib.Path.mkdir", side_effect=AssertionError("Directory write")):
            evaluate_regression(data, candidates={"Baseline": DummyRegressor()})
        pd.testing.assert_frame_equal(data, original)

    def test_invalid_inputs_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "one feature row"):
            split_country_data(pd.concat([country_data(), country_data().iloc[[0]]]))
        with self.assertRaisesRegex(ValueError, "schema"):
            split_country_data(country_data().drop(columns=FEATURES[0]))
        with self.assertRaisesRegex(ValueError, "finite"):
            split_country_data(country_data().assign(Total=float("nan")))
        with self.assertRaisesRegex(ValueError, "validation fold"):
            evaluate_regression(country_data().iloc[:8])


if __name__ == "__main__":
    unittest.main()
