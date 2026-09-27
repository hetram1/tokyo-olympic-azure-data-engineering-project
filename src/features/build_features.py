from pathlib import Path

import pandas as pd

from src.quality.data_quality import load_csv


OUTPUT_DIR = Path(__file__).resolve().parents[2] / "models"
OUTPUT_DIR.mkdir(exist_ok=True)


def build_country_features() -> pd.DataFrame:
    """Build country-level participation features and medal targets."""

    athletes = load_csv("Athletes.csv")
    teams = load_csv("Teams.csv")
    medals = load_csv("Medals.csv")

    # Remove exact duplicate athlete records.
    athletes = athletes.drop_duplicates()

    # Remove exact duplicate team records.
    teams = teams.drop_duplicates()

    # ---------------------------------------------------------
    # Athlete participation features
    # ---------------------------------------------------------

    athlete_features = (
        athletes.groupby("Country")
        .agg(
            athlete_count=("PersonName", "nunique"),
            athlete_discipline_count=("Discipline", "nunique"),
        )
        .reset_index()
        .rename(columns={"Country": "country"})
    )

    # ---------------------------------------------------------
    # Team participation features
    # ---------------------------------------------------------

    team_features = (
        teams.groupby("Country")
        .agg(
            team_count=("TeamName", "nunique"),
            team_discipline_count=("Discipline", "nunique"),
            team_event_count=("Event", "nunique"),
        )
        .reset_index()
        .rename(columns={"Country": "country"})
    )

    # ---------------------------------------------------------
    # Medal target
    # ---------------------------------------------------------

    medal_targets = (
        medals[
            [
                "TeamCountry",
                "Gold",
                "Silver",
                "Bronze",
                "Total",
            ]
        ]
        .copy()
        .rename(columns={"TeamCountry": "country"})
    )

    # ---------------------------------------------------------
    # Combine participation features
    # ---------------------------------------------------------

    features = athlete_features.merge(
        team_features,
        on="country",
        how="outer",
    )

    features = features.merge(
        medal_targets,
        on="country",
        how="left",
    )

    # Countries without medals receive a target of zero.
    medal_columns = ["Gold", "Silver", "Bronze", "Total"]

    for column in medal_columns:
        features[column] = features[column].fillna(0)

    # Participation counts should also be zero where no
    # corresponding records exist.
    participation_columns = [
        "athlete_count",
        "athlete_discipline_count",
        "team_count",
        "team_discipline_count",
        "team_event_count",
    ]

    for column in participation_columns:
        features[column] = features[column].fillna(0).astype(int)

    # Sort for reproducibility.
    features = features.sort_values("country").reset_index(drop=True)

    return features


if __name__ == "__main__":
    df = build_country_features()

    output_path = OUTPUT_DIR / "country_features.csv"
    df.to_csv(output_path, index=False)

    print(f"Created: {output_path}")
    print(f"Rows: {len(df)}")
    print(f"Columns: {len(df.columns)}")
    print()
    print(df.head(10).to_string(index=False))
