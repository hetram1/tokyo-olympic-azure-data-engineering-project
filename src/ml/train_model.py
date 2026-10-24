"""Training-only model selection followed by one selected-model holdout evaluation."""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, train_test_split
from xgboost import XGBRegressor


DATA_PATH = Path("models/country_features.csv")
FEATURES = [
    "athlete_count", "athlete_discipline_count", "team_count",
    "team_discipline_count", "team_event_count",
]
TARGET = "Total"
RANDOM_STATE = 42


@dataclass
class RegressionEvaluation:
    selected_name: str
    model: object
    validation_summary: pd.DataFrame
    fold_metrics: pd.DataFrame
    cv_partitions: list[dict]
    train_countries: tuple[str, ...]
    test_countries: tuple[str, ...]
    holdout_metrics: dict
    predictions: pd.DataFrame


def split_country_data(data, *, random_state=RANDOM_STATE, test_size=0.20):
    """Split country identities independently of outcomes; never mutate inputs."""
    required = ["country", *FEATURES, TARGET]
    missing = [column for column in required if column not in data.columns]
    if missing or not data.columns.is_unique:
        raise ValueError(f"Invalid feature schema; missing columns: {missing}")
    countries = data.country
    if not countries.map(lambda v: isinstance(v, str) and bool(v.strip())).all():
        raise ValueError("country must contain nonblank country keys")
    if countries.duplicated().any():
        raise ValueError("Expected one feature row per country")
    values = data[[*FEATURES, TARGET]]
    if any(not pd.api.types.is_numeric_dtype(values[c]) or pd.api.types.is_bool_dtype(values[c])
           for c in values):
        raise ValueError("Features and target must be numeric counts")
    if not np.isfinite(values.to_numpy(dtype=float)).all() or (values < 0).any().any():
        raise ValueError("Features and target must be finite, non-negative counts")
    # Stable country ordering makes shuffled input rows reproduce the same split.
    ordered = data[required].sort_values("country").reset_index(drop=True)
    train, test = train_test_split(ordered, test_size=test_size, random_state=random_state)
    if len(test) < 2:
        raise ValueError("Holdout needs at least two countries for R²")
    return train.copy(), test.copy()


def candidate_models(random_state=RANDOM_STATE):
    """Prespecified candidates; retain existing features and hyperparameters."""
    return {
        "Baseline": DummyRegressor(strategy="mean"),
        "Random Forest": RandomForestRegressor(
            n_estimators=300, max_depth=8, min_samples_leaf=2,
            random_state=random_state, n_jobs=1,
        ),
        "XGBoost": XGBRegressor(
            n_estimators=300, max_depth=4, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8,
            objective="reg:squarederror", random_state=random_state, n_jobs=1,
        ),
    }


def regression_metrics(actual, predicted):
    return {
        "mae": float(mean_absolute_error(actual, predicted)),
        "rmse": float(mean_squared_error(actual, predicted) ** 0.5),
        "r2": float(r2_score(actual, predicted)),
    }


def compare_training_models(training, *, candidates=None, n_splits=5, random_state=RANDOM_STATE):
    """CV selection accepts training data only, never the holdout partition.

    Each estimator is cloned/refitted in each shared fold. The baseline learns
    its mean from that fold's training outcomes. No data-dependent preprocessing
    is needed by these tree/constant models; any future preprocessing must be
    inside the cloned estimator's sklearn Pipeline, not fitted on all countries.
    """
    models = candidate_models(random_state) if candidates is None else candidates
    if not models:
        raise ValueError("At least one candidate is required")
    if n_splits < 2 or len(training) // n_splits < 2:
        raise ValueError("Each validation fold needs at least two countries for R²")
    splits = list(KFold(n_splits=n_splits, shuffle=True, random_state=random_state).split(training))
    rows, partitions = [], []
    for fold, (fit_indices, validation_indices) in enumerate(splits, 1):
        fit = training.iloc[fit_indices]
        validation = training.iloc[validation_indices]
        partitions.append({"fold": fold, "train_countries": tuple(fit.country),
                           "validation_countries": tuple(validation.country)})
        for name, estimator in models.items():
            model = clone(estimator)
            model.fit(fit[FEATURES], fit[TARGET])
            predictions = model.predict(validation[FEATURES])
            rows.append({"model": name, "fold": fold, "train_rows": len(fit),
                         "validation_rows": len(validation),
                         **regression_metrics(validation[TARGET], predictions)})
    folds = pd.DataFrame(rows)
    summary = folds.groupby("model", sort=False).agg(
        mae_mean=("mae", "mean"), mae_std=("mae", "std"),
        rmse_mean=("rmse", "mean"), rmse_std=("rmse", "std"),
        r2_mean=("r2", "mean"), r2_std=("r2", "std"),
    ).reset_index()
    # Model name is a deterministic tie-break, not a holdout-based decision.
    summary = summary.sort_values(["mae_mean", "model"]).reset_index(drop=True)
    selected = summary.iloc[0]["model"]
    return selected, clone(models[selected]), summary, folds, partitions


def evaluate_regression(data, *, candidates=None, random_state=RANDOM_STATE,
                        test_size=0.20, n_splits=5):
    """Run evaluation in memory; no model/prediction files or directories written."""
    training, holdout = split_country_data(data, random_state=random_state, test_size=test_size)
    selected, model, summary, folds, partitions = compare_training_models(
        training, candidates=candidates, n_splits=n_splits, random_state=random_state,
    )
    model.fit(training[FEATURES], training[TARGET])
    # Only the selected/refitted model predicts on holdout, once per invocation.
    predicted = model.predict(holdout[FEATURES])
    metrics = {"model": selected, **regression_metrics(holdout[TARGET], predicted)}
    predictions = pd.DataFrame({
        "country": holdout.country.to_numpy(),
        "actual_total": holdout[TARGET].to_numpy(),
        "predicted_total": predicted,
        "residual": holdout[TARGET].to_numpy() - predicted,
        "absolute_error": np.abs(holdout[TARGET].to_numpy() - predicted),
    })
    return RegressionEvaluation(
        selected, model, summary, folds, partitions,
        tuple(training.country), tuple(holdout.country), metrics, predictions,
    )


def print_evaluation(result):
    print(f"Training countries: {len(result.train_countries)}; holdout: {len(result.test_countries)}")
    print("\nTRAINING-ONLY 5-FOLD VALIDATION (means and sample standard deviations)")
    print(result.validation_summary.to_string(index=False))
    print(f"\nSelected by validation MAE: {result.selected_name}")
    print("FINAL HOLDOUT (selected model only)")
    print(pd.DataFrame([result.holdout_metrics]).to_string(index=False))
    print("\nLARGEST HOLDOUT ERRORS")
    print(result.predictions.sort_values(["absolute_error", "country"], ascending=[False, True])
          .head(10).to_string(index=False))


def main():
    print_evaluation(evaluate_regression(pd.read_csv(DATA_PATH)))


if __name__ == "__main__":
    main()
