from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor


DATA_PATH = Path("models/country_features.csv")
MODEL_DIR = Path("models")
MODEL_DIR.mkdir(exist_ok=True)

FEATURES = [
    "athlete_count",
    "athlete_discipline_count",
    "team_count",
    "team_discipline_count",
    "team_event_count",
]

TARGET = "Total"


def evaluate_model(name, model, X_test, y_test):
    """Evaluate a regression model."""
    predictions = model.predict(X_test)

    mae = mean_absolute_error(y_test, predictions)
    rmse = mean_squared_error(
        y_test,
        predictions,
    ) ** 0.5
    r2 = r2_score(y_test, predictions)

    print(f"\n{name}")
    print("-" * 50)
    print(f"MAE  : {mae:.4f}")
    print(f"RMSE : {rmse:.4f}")
    print(f"R²   : {r2:.4f}")

    return {
        "model": name,
        "mae": mae,
        "rmse": rmse,
        "r2": r2,
    }


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

    print(f"Dataset size : {len(df)}")
    print(f"Training     : {len(X_train)}")
    print(f"Test         : {len(X_test)}")
    print(f"Features     : {FEATURES}")
    print(f"Target       : {TARGET}")

    results = []

    # ---------------------------------------------------------
    # Baseline: predict the training-set mean
    # ---------------------------------------------------------

    baseline_prediction = y_train.mean()

    baseline_predictions = [baseline_prediction] * len(y_test)

    baseline_mae = mean_absolute_error(
        y_test,
        baseline_predictions,
    )

    baseline_rmse = mean_squared_error(
        y_test,
        baseline_predictions,
    ) ** 0.5

    baseline_r2 = r2_score(
        y_test,
        baseline_predictions,
    )

    print("\nBaseline")
    print("-" * 50)
    print(f"MAE  : {baseline_mae:.4f}")
    print(f"RMSE : {baseline_rmse:.4f}")
    print(f"R²   : {baseline_r2:.4f}")

    results.append(
        {
            "model": "Baseline",
            "mae": baseline_mae,
            "rmse": baseline_rmse,
            "r2": baseline_r2,
        }
    )

    # ---------------------------------------------------------
    # Random Forest
    # ---------------------------------------------------------

    random_forest = RandomForestRegressor(
        n_estimators=300,
        max_depth=8,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )

    random_forest.fit(X_train, y_train)

    results.append(
        evaluate_model(
            "Random Forest",
            random_forest,
            X_test,
            y_test,
        )
    )

    # ---------------------------------------------------------
    # XGBoost
    # ---------------------------------------------------------

    xgboost = XGBRegressor(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="reg:squarederror",
        random_state=42,
        n_jobs=4,
    )

    xgboost.fit(X_train, y_train)

    results.append(
        evaluate_model(
            "XGBoost",
            xgboost,
            X_test,
            y_test,
        )
    )

    # ---------------------------------------------------------
    # Select model by lowest MAE
    # ---------------------------------------------------------

    results_df = pd.DataFrame(results)

    print("\nMODEL COMPARISON")
    print("=" * 70)
    print(
        results_df
        .sort_values("mae")
        .to_string(index=False)
    )

    best_name = results_df.loc[
        results_df["mae"].idxmin(),
        "model",
    ]

    if best_name == "Random Forest":
        best_model = random_forest
    elif best_name == "XGBoost":
        best_model = xgboost
    else:
        best_model = None

    if best_model is not None:
        model_path = MODEL_DIR / "medal_prediction_model.joblib"
        joblib.dump(best_model, model_path)
        print(f"\nSaved best model: {model_path}")


if __name__ == "__main__":
    main()
