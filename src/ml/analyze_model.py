"""Inspect the model chosen by the shared, training-only regression procedure."""

import pandas as pd

from src.ml.train_model import DATA_PATH, FEATURES, evaluate_regression, print_evaluation


def main():
    result = evaluate_regression(pd.read_csv(DATA_PATH))
    print_evaluation(result)
    if hasattr(result.model, "feature_importances_"):
        importance = pd.DataFrame({"feature": FEATURES,
                                   "importance": result.model.feature_importances_})
        print("\nSELECTED-MODEL FEATURE IMPORTANCE (training fit)")
        print(importance.sort_values("importance", ascending=False).to_string(index=False))
    else:
        print("\nSelected mean baseline has no feature importances.")


if __name__ == "__main__":
    main()
