from pathlib import Path

import pandas as pd

from src.quality.data_quality import load_csv


OUTPUT_DIR = Path("models")
OUTPUT_DIR.mkdir(exist_ok=True)


def build_country_analytics() -> pd.DataFrame:
    athletes = load_csv("Athletes.csv").drop_duplicates()
    teams = load_csv("Teams.csv").drop_duplicates()
    medals = load_csv("Medals.csv").copy()

    # Athlete participation
    athlete_stats = (
        athletes.groupby("Country")
        .agg(
            athlete_count=("PersonName", "nunique"),
            athlete_discipline_count=("Discipline", "nunique"),
        )
        .reset_index()
        .rename(columns={"Country": "country"})
    )

    # Team/event participation
    team_stats = (
        teams.groupby("Country")
        .agg(
            team_count=("TeamName", "nunique"),
            team_discipline_count=("Discipline", "nunique"),
            team_event_count=("Event", "nunique"),
        )
        .reset_index()
        .rename(columns={"Country": "country"})
    )

    # Medal outcomes
    medal_stats = (
        medals[
            ["TeamCountry", "Gold", "Silver", "Bronze", "Total"]
        ]
        .rename(columns={"TeamCountry": "country"})
    )

    # Combine analytics layers
    analytics = (
        athlete_stats
        .merge(team_stats, on="country", how="outer")
        .merge(medal_stats, on="country", how="left")
    )

    numeric_columns = [
        "athlete_count",
        "athlete_discipline_count",
        "team_count",
        "team_discipline_count",
        "team_event_count",
        "Gold",
        "Silver",
        "Bronze",
        "Total",
    ]

    analytics[numeric_columns] = analytics[numeric_columns].fillna(0)

    # Derived KPIs
    analytics["medal_rate_per_athlete"] = (
        analytics["Total"]
        / analytics["athlete_count"].replace(0, pd.NA)
    ).fillna(0)

    analytics["gold_share"] = (
        analytics["Gold"]
        / analytics["Total"].replace(0, pd.NA)
    ).fillna(0)

    analytics["medals_per_team_event"] = (
        analytics["Total"]
        / analytics["team_event_count"].replace(0, pd.NA)
    ).fillna(0)

    analytics["medals_per_discipline"] = (
        analytics["Total"]
        / analytics["athlete_discipline_count"].replace(0, pd.NA)
    ).fillna(0)

    # Performance class used by the ML classification experiment
    analytics["performance_class"] = pd.cut(
        analytics["Total"],
        bins=[-1, 0, 9, float("inf")],
        labels=["No Medal", "Medal", "High Medal"],
    )

    return analytics.sort_values(
        "Total",
        ascending=False,
    ).reset_index(drop=True)


def main():
    analytics = build_country_analytics()

    output_path = OUTPUT_DIR / "country_analytics.csv"
    analytics.to_csv(output_path, index=False)

    print(f"Saved: {output_path}")
    print(f"Rows: {len(analytics)}")
    print(f"Columns: {len(analytics.columns)}")

    print("\nTOP 10 COUNTRIES BY MEDALS")
    print("=" * 70)

    print(
        analytics[
            [
                "country",
                "Total",
                "Gold",
                "Silver",
                "Bronze",
                "athlete_count",
                "medal_rate_per_athlete",
            ]
        ]
        .head(10)
        .to_string(index=False)
    )

    print("\nTOP 10 MEDAL-EFFICIENT COUNTRIES")
    print("=" * 70)

    print(
        analytics[
            [
                "country",
                "Total",
                "athlete_count",
                "medal_rate_per_athlete",
            ]
        ]
        .sort_values(
            "medal_rate_per_athlete",
            ascending=False,
        )
        .head(10)
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()
