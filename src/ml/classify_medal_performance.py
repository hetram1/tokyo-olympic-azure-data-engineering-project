"""Exploratory same-Olympics classification; evaluation writes no artifacts."""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, average_precision_score, confusion_matrix, roc_auc_score
from sklearn.model_selection import StratifiedKFold

from src.quality.data_quality import normalize_country_key

DATA_PATH = Path("models/country_features.csv")
FEATURES = ["athlete_count", "athlete_discipline_count", "team_count",
            "team_discipline_count", "team_event_count"]
TARGET = "Total"
# Semantic order, used for every matrix axis and probability vector. Never infer
# probability order from categorical display order or fit a full-data estimator.
CLASS_ORDER = ("No Medal", "Medal", "High Medal")
N_SPLITS = 5
RANDOM_STATE = 42


@dataclass
class ClassificationEvaluation:
    class_order: tuple
    class_distribution: dict
    fold_assignments: list[dict]
    model_metrics: dict
    baseline_metrics: dict
    fold_metrics: list[dict]
    predictions: pd.DataFrame


def _validate_counts(data, columns):
    for column in columns:
        values = data[column]
        if (not pd.api.types.is_numeric_dtype(values.dtype)
                or pd.api.types.is_bool_dtype(values.dtype)
                or pd.api.types.is_complex_dtype(values.dtype)):
            raise ValueError(f"{column} must contain real numeric counts, not booleans or strings")
        if values.isna().any():
            raise ValueError(f"{column} must contain finite nonnegative integer-valued counts")
        if (not np.isfinite(values.to_numpy(dtype=float)).all()
                or (values < 0).any() or (values % 1 != 0).any()):
            raise ValueError(f"{column} must contain finite nonnegative integer-valued counts")


def create_classes(data):
    """Validate targets before mapping exactly 0 / 1–9 / 10+ medals."""
    if not isinstance(data, pd.DataFrame) or not data.columns.is_unique or TARGET not in data:
        raise ValueError("Invalid target schema: expected a unique Total column")
    _validate_counts(data, [TARGET])
    return pd.Series(np.select([data[TARGET].eq(0), data[TARGET].le(9)],
                               CLASS_ORDER[:2], default=CLASS_ORDER[2]),
                     index=data.index, name="actual_class")


def validate_classification_input(data):
    required = ["country", *FEATURES, TARGET]
    if not isinstance(data, pd.DataFrame):
        raise ValueError("Invalid input schema: expected a DataFrame")
    missing = [c for c in required if c not in data]
    if missing or not data.columns.is_unique:
        raise ValueError(f"Invalid input schema; missing columns: {missing}; columns must be unique")
    ordered = data[required].copy(deep=True)
    if not ordered.country.map(lambda x: isinstance(x, str) and bool(x.strip())).all():
        raise ValueError("country identifiers must be nonblank strings")
    ordered["country"] = ordered.country.map(normalize_country_key)
    if ordered.country.duplicated().any():
        raise ValueError("country identifiers must be unique after normalization")
    if ordered.country.str.contains('\ufffd', regex=False).any():
        raise ValueError("country identifiers contain unresolved replacement characters")
    _validate_counts(ordered, [*FEATURES, TARGET])
    ordered = ordered.sort_values("country").reset_index(drop=True)
    labels = create_classes(ordered)
    counts = labels.value_counts().reindex(CLASS_ORDER, fill_value=0)
    if (counts < N_SPLITS).any():
        raise ValueError(f"Each of the three classes needs at least {N_SPLITS} countries; got {counts.to_dict()}")
    return ordered, labels


def classification_model():
    """Preserve the existing prespecified classifier; no result-based tuning."""
    return RandomForestClassifier(n_estimators=300, max_depth=8, min_samples_leaf=2,
                                  class_weight="balanced", random_state=42, n_jobs=-1)


def classification_metrics(actual, predicted, probabilities):
    """Pooled metrics with explicit undefined values; AP is not trapezoidal PR area.

    Undefined per-class precision/recall/F1 is None. Macro/weighted aggregates
    use a documented zero contribution for undefined components (not omission).
    AUC/AP aggregates are None unless all class-wise quantities are defined.
    """
    actual, predicted = np.asarray(actual), np.asarray(predicted)
    probabilities = np.asarray(probabilities, dtype=float)
    if (actual.ndim != 1 or predicted.shape != actual.shape or not len(actual)
            or not np.isin(actual, CLASS_ORDER).all() or not np.isin(predicted, CLASS_ORDER).all()):
        raise ValueError("Invalid class labels or prediction dimensions")
    if (probabilities.shape != (len(actual), len(CLASS_ORDER))
            or not np.isfinite(probabilities).all() or (probabilities < 0).any()
            or (probabilities > 1).any() or not np.allclose(probabilities.sum(axis=1), 1)):
        raise ValueError("Invalid aligned probability matrix")
    matrix = confusion_matrix(actual, predicted, labels=CLASS_ORDER)
    per_class, undefined = {}, []
    for i, label in enumerate(CLASS_ORDER):
        support, calls, tp = int(matrix[i].sum()), int(matrix[:, i].sum()), int(matrix[i, i])
        binary = actual == label
        metrics = {"support": support, "precision": tp / calls if calls else None,
                   "recall": tp / support if support else None,
                   "f1": 2 * tp / (support + calls) if support + calls else None,
                   "roc_auc_ovr": float(roc_auc_score(binary, probabilities[:, i]))
                   if 0 < support < len(actual) else None,
                   "average_precision": float(average_precision_score(binary, probabilities[:, i]))
                   if support else None}
        undefined.extend(f"{label}: {key}" for key, value in metrics.items() if value is None)
        per_class[label] = metrics
    result = {"accuracy": float(accuracy_score(actual, predicted)), "per_class": per_class,
              "confusion_matrix": matrix.tolist(), "undefined_metrics": undefined,
              "undefined_aggregate_policy": "Zero contribution for undefined precision/recall/F1; no omission"}
    weights = np.array([per_class[c]["support"] for c in CLASS_ORDER]) / len(actual)
    for metric in ("precision", "recall", "f1", "roc_auc_ovr", "average_precision"):
        values = [per_class[c][metric] for c in CLASS_ORDER]
        valid = all(v is not None for v in values) or metric in ("precision", "recall", "f1")
        result["macro_" + metric] = float(np.mean([v or 0 for v in values])) if valid else None
        result["weighted_" + metric] = float(np.dot(weights, [v or 0 for v in values])) if valid else None
    return result


def _aligned_predictions(model, features):
    labels = model.predict(features)
    probabilities = model.predict_proba(features)
    if len(model.classes_) != len(CLASS_ORDER) or set(model.classes_) != set(CLASS_ORDER):
        raise ValueError("Fitted estimator has invalid class labels")
    probabilities = probabilities[:, [list(model.classes_).index(c) for c in CLASS_ORDER]]
    # Also validates labels and probability ranges before assignment.
    if not np.isin(labels, CLASS_ORDER).all():
        raise ValueError("Estimator predicted invalid class labels")
    return labels, probabilities


def evaluate_classification(data, *, estimator=None):
    """Return country-keyed OOF evidence only; never fit on all countries or save.

    estimator is a test-injection seam; the CLI always uses the unchanged forest.
    Majority ties use sklearn's deterministic lexical class ordering.
    """
    ordered, labels = validate_classification_input(data)
    features = ordered[FEATURES]
    estimator = classification_model() if estimator is None else estimator
    rows = pd.DataFrame({"country": ordered.country, "actual_total": ordered[TARGET],
                         "actual_class": labels})
    seen = np.zeros(len(ordered), dtype=int)
    partitions, folds = [], []
    for fold, (train, validation) in enumerate(StratifiedKFold(
            n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE).split(features, labels), 1):
        if np.intersect1d(train, validation).size or seen[validation].any():
            raise ValueError("Invalid overlapping CV partitions")
        partitions.append({"fold": fold, "train_countries": tuple(ordered.country.iloc[train]),
                           "validation_countries": tuple(ordered.country.iloc[validation])})
        rows.loc[validation, "fold"] = fold
        for name, candidate in (("model", estimator), ("baseline", DummyClassifier(strategy="most_frequent"))):
            fitted = clone(candidate).fit(features.iloc[train], labels.iloc[train])
            predicted, probability = _aligned_predictions(fitted, features.iloc[validation])
            metrics = classification_metrics(labels.iloc[validation], predicted, probability)
            rows.loc[validation, name + "_predicted_class"] = predicted
            for i, label in enumerate(CLASS_ORDER):
                rows.loc[validation, name + "_probability_" + label] = probability[:, i]
            folds.append({"fold": fold, "estimator": name, "training_count": len(train),
                          "validation_count": len(validation), "metrics": metrics})
        seen[validation] += 1
    if not (seen == 1).all():
        raise ValueError("Every country must receive exactly one OOF prediction")
    rows["fold"] = rows.fold.astype(int)
    metrics = {}
    for name in ("model", "baseline"):
        metrics[name] = classification_metrics(labels, rows[name + "_predicted_class"],
            rows[[name + "_probability_" + label for label in CLASS_ORDER]].to_numpy())
    return ClassificationEvaluation(CLASS_ORDER, {c: int(labels.eq(c).sum()) for c in CLASS_ORDER},
                                    partitions, metrics["model"], metrics["baseline"], folds, rows)


def main():
    import json

    result = evaluate_classification(pd.read_csv(DATA_PATH))
    print("Exploratory same-Olympics OOF evaluation; probabilities are not established as calibrated.")
    print(json.dumps({"class_order": result.class_order, "class_distribution": result.class_distribution,
                      "model": result.model_metrics, "majority_baseline": result.baseline_metrics,
                      "fold_metrics": result.fold_metrics}, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
