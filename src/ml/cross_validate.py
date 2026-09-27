from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold

DATA_PATH = Path("models/country_features.csv")

FEATURES = [
    "athlete_count",
    "athlete_discipline_count",
    "team_count",
    "team_discipline_count",
    "team_event_count",
]

TARGET = "Total"


def main():
    df = pd.read_csv(DATA_PATH)

    X = df[FEATURES]
    y = df[TARGET]

    kfold = KFold(
        n_splits=5,
        shuffle=True,
        random_state=42,
    )

    results = []

    for fold, (train_idx, test_idx) in enumerate(
        kfold.split(X),
        start=1,
    ):
        X_train = X.iloc[train_idx]
        X_test = X.iloc[test_idx]

        y_train = y.iloc[train_idx]
        y_test = y.iloc[test_idx]

        model = RandomForestRegressor(
            n_estimators=300,
            max_depth=8,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
        )

        model.fit(X_train, y_train)

        predictions = model.predict(X_test)

        mae = mean_absolute_error(y_test, predictions)

        rmse = mean_squared_error(
            y_test,
            predictions,
        ) ** 0.5

        r2 = r2_score(y_test, predictions)

        results.append(
            {
                "fold": fold,
                "mae": mae,
                "rmse": rmse,
                "r2": r2,
            }
        )

    results_df = pd.DataFrame(results)

    print("\n5-FOLD CROSS-VALIDATION")
    print("=" * 70)
    print(results_df.to_string(index=False))

    print("\nMEAN")
    print("-" * 70)
    print(results_df[["mae", "rmse", "r2"]].mean())

    print("\nSTANDARD DEVIATION")
    print("-" * 70)
    print(results_df[["mae", "rmse", "r2"]].std())


if __name__ == "__main__":
    main()
