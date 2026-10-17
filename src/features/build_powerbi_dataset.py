from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
INPUT_FILE = ROOT / "models" / "country_analytics.csv"
OUTPUT_DIR = ROOT / "dashboards"
OUTPUT_FILE = OUTPUT_DIR / "olympic_country_dashboard.csv"


REQUIRED_COLUMNS = [
    "country",
    "athlete_count",
    "athlete_discipline_count",
    "team_count",
    "team_discipline_count",
    "team_event_count",
    "Gold",
    "Silver",
    "Bronze",
    "Total",
    "medal_rate_per_athlete",
    "gold_share",
    "medals_per_discipline",
    "performance_class",
]


NUMERIC_COLUMNS = [
    "athlete_count",
    "athlete_discipline_count",
    "team_count",
    "team_discipline_count",
    "team_event_count",
    "Gold",
    "Silver",
    "Bronze",
    "Total",
    "medal_rate_per_athlete",
    "gold_share",
    "medals_per_discipline",
]


def prepare_powerbi_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Prepare the supported dashboard schema without reading or writing files.

    Selecting REQUIRED_COLUMNS also excludes retired KPIs in older input CSVs.
    """
    missing = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {missing}"
        )

    df = df[REQUIRED_COLUMNS].copy()

    for column in NUMERIC_COLUMNS:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    df = df.dropna(subset=["country"])

    # Prevent duplicate country records in the dashboard.
    df = df.drop_duplicates(subset=["country"])

    # Sort countries by total medals, then gold medals.
    df = (
        df.sort_values(
            ["Total", "Gold", "country"],
            ascending=[False, False, True],
        )
        .reset_index(drop=True)
    )

    # Simple dashboard-friendly medal rank.
    df["medal_rank"] = (
        df["Total"]
        .rank(method="min", ascending=False)
        .astype(int)
    )

    # Human-readable performance label.
    df["performance_label"] = (
        df["performance_class"]
        .astype(str)
        .str.strip()
    )

    return df


def build_powerbi_dataset() -> pd.DataFrame:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input analytics dataset not found: {INPUT_FILE}"
        )

    df = prepare_powerbi_dataset(pd.read_csv(INPUT_FILE))

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    return df


if __name__ == "__main__":
    df = build_powerbi_dataset()

    print()
    print("Power BI dataset created successfully.")
    print(f"File: {OUTPUT_FILE}")
    print(f"Rows: {len(df)}")
    print(f"Columns: {len(df.columns)}")

    print()
    print("Columns:")
    for column in df.columns:
        print(f"  - {column}")

    print()
    print("Top 10 countries by total medals:")
    print(
        df[
            [
                "medal_rank",
                "country",
                "Gold",
                "Silver",
                "Bronze",
                "Total",
            ]
        ]
        .head(10)
        .to_string(index=False)
    )
