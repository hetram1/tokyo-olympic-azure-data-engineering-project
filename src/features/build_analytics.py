from pathlib import Path

import pandas as pd

from src.quality.data_quality import load_csv
from src.quality.gates import load_validated_sources
from src.features.team_counts import aggregate_team_counts


OUTPUT_DIR = Path("models")


def build_country_analytics() -> pd.DataFrame:
    sources, quality_report = load_validated_sources(loader=load_csv)
    athletes, teams, medals = (sources[name] for name in ("Athletes", "Teams", "Medals"))

    # athlete_count is a distinct normalized-name proxy, not verified people.
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
    team_stats = aggregate_team_counts(teams)

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
        .merge(team_stats, on="country", how="outer", validate="one_to_one")
        .merge(medal_stats, on="country", how="left", validate="one_to_one")
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

    analytics = analytics.sort_values(
        "Total",
        ascending=False,
    ).reset_index(drop=True)
    analytics.attrs["data_quality_report"] = quality_report
    return analytics


def main():
    analytics = build_country_analytics()

    OUTPUT_DIR.mkdir(exist_ok=True)
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
