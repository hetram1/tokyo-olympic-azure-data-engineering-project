from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split


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

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
    )

    model = RandomForestRegressor(
        n_estimators=300,
        max_depth=8,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )

    model.fit(X_train, y_train)

    importance = (
        pd.DataFrame(
            {
                "feature": FEATURES,
                "importance": model.feature_importances_,
            }
        )
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )

    print("\nFEATURE IMPORTANCE")
    print("=" * 60)
    print(importance.to_string(index=False))

    predictions = model.predict(X_test)

    errors = pd.DataFrame(
        {
            "country": df.loc[X_test.index, "country"].values,
            "actual_total": y_test.values,
            "predicted_total": predictions.round(2),
            "absolute_error": (
                y_test.values - predictions
            ).astype(float),
        }
    )

    errors["absolute_error"] = errors["absolute_error"].abs()

    print("\nLARGEST PREDICTION ERRORS")
    print("=" * 60)
    print(
        errors
        .sort_values("absolute_error", ascending=False)
        .head(10)
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()
