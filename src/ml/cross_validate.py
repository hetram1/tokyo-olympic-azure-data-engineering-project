"""Compare regression candidates within the training partition only."""

import pandas as pd

from src.ml.train_model import DATA_PATH, compare_training_models, split_country_data


def main():
    training, holdout = split_country_data(pd.read_csv(DATA_PATH))
    selected, _, summary, folds, _ = compare_training_models(training)
    print(f"Training countries: {len(training)}; reserved holdout: {len(holdout)} (not evaluated)")
    print("\nTRAINING-ONLY FOLD METRICS")
    print(folds.to_string(index=False))
    print("\nVALIDATION COMPARISON")
    print(summary.to_string(index=False))
    print(f"\nSelected by validation MAE: {selected}")


if __name__ == "__main__":
    main()
