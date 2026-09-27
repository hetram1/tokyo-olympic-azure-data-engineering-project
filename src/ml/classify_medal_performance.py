from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    average_precision_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.preprocessing import label_binarize


DATA_PATH = Path("models/country_features.csv")

FEATURES = [
    "athlete_count",
    "athlete_discipline_count",
    "team_count",
    "team_discipline_count",
    "team_event_count",
]

TARGET = "Total"


def create_classes(df: pd.DataFrame) -> pd.Series:
    """
    Create medal-performance classes from Tokyo medal totals.

    0       -> No Medal
    1-9     -> Medal
    10+     -> High Medal
    """
    return pd.cut(
        df[TARGET],
        bins=[-1, 0, 9, float("inf")],
        labels=["No Medal", "Medal", "High Medal"],
    )


def main():
    df = pd.read_csv(DATA_PATH)

    X = df[FEATURES]
    y = create_classes(df)

    print("CLASS DISTRIBUTION")
    print("=" * 70)
    print(y.value_counts().sort_index())

    print("\nCLASS PROPORTIONS")
    print("=" * 70)
    print(
        y.value_counts(normalize=True)
        .sort_index()
        .round(4)
    )

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=8,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )

    cv = StratifiedKFold(
        n_splits=5,
        shuffle=True,
        random_state=42,
    )

    predictions = cross_val_predict(
        model,
        X,
        y,
        cv=cv,
        method="predict",
        n_jobs=1,
    )

    probabilities = cross_val_predict(
        model,
        X,
        y,
        cv=cv,
        method="predict_proba",
        n_jobs=1,
    )

    classes = model.fit(X, y).classes_

    print("\nCLASSIFICATION REPORT")
    print("=" * 70)
    print(
        classification_report(
            y,
            predictions,
            zero_division=0,
        )
    )

    precision = precision_score(
        y,
        predictions,
        average="weighted",
        zero_division=0,
    )

    recall = recall_score(
        y,
        predictions,
        average="weighted",
        zero_division=0,
    )

    f1 = f1_score(
        y,
        predictions,
        average="weighted",
        zero_division=0,
    )

    y_binary = label_binarize(
        y,
        classes=classes,
    )

    roc_auc = roc_auc_score(
        y_binary,
        probabilities,
        multi_class="ovr",
        average="weighted",
    )

    pr_auc = average_precision_score(
        y_binary,
        probabilities,
        average="weighted",
    )

    print("CROSS-VALIDATED METRICS")
    print("=" * 70)
    print(f"Weighted Precision : {precision:.4f}")
    print(f"Weighted Recall    : {recall:.4f}")
    print(f"Weighted F1        : {f1:.4f}")
    print(f"ROC-AUC            : {roc_auc:.4f}")
    print(f"PR-AUC             : {pr_auc:.4f}")

    print("\nCONFUSION MATRIX")
    print("=" * 70)
    print(
        pd.DataFrame(
            confusion_matrix(
                y,
                predictions,
                labels=classes,
            ),
            index=classes,
            columns=classes,
        )
    )


if __name__ == "__main__":
    main()
