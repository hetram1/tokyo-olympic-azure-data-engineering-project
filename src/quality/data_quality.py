from pathlib import Path

import pandas as pd


DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def load_csv(filename: str) -> pd.DataFrame:
    """Load a CSV while handling source datasets with different encodings."""
    path = DATA_DIR / filename

    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")

    for encoding in ("utf-8", "ISO-8859-1"):
        try:
            return pd.read_csv(path, encoding=encoding)
        except UnicodeDecodeError:
            continue

    raise ValueError(f"Unable to decode {filename}")


def check_required_columns(
    df: pd.DataFrame,
    required_columns: list[str],
) -> list[str]:
    """Return missing required columns."""
    return [
        column
        for column in required_columns
        if column not in df.columns
    ]


def check_duplicates(df: pd.DataFrame) -> int:
    """Return the number of duplicate rows."""
    return int(df.duplicated().sum())


def check_missing_values(df: pd.DataFrame) -> dict[str, int]:
    """Return missing-value counts by column."""
    return {
        column: int(count)
        for column, count in df.isna().sum().items()
        if count > 0
    }


def check_medal_totals(df: pd.DataFrame) -> int:
    """Count rows where Total != Gold + Silver + Bronze."""
    expected = df["Gold"] + df["Silver"] + df["Bronze"]
    return int((df["Total"] != expected).sum())


def check_gender_totals(df: pd.DataFrame) -> int:
    """Count rows where Total != Female + Male."""
    expected = df["Female"] + df["Male"]
    return int((df["Total"] != expected).sum())


def check_non_negative(
    df: pd.DataFrame,
    columns: list[str],
) -> dict[str, int]:
    """Count negative values in selected numeric columns."""
    violations = {}

    for column in columns:
        violations[column] = int((df[column] < 0).sum())

    return violations


def profile_dataframe(
    df: pd.DataFrame,
    name: str,
    required_columns: list[str],
) -> dict:
    """Generate a general data-quality profile."""
    return {
        "dataset": name,
        "rows": len(df),
        "columns": len(df.columns),
        "missing_required_columns": check_required_columns(
            df, required_columns
        ),
        "missing_values": check_missing_values(df),
        "duplicate_rows": check_duplicates(df),
    }


def run_quality_checks() -> dict:
    """Run dataset-specific quality checks."""

    athletes = load_csv("Athletes.csv")
    coaches = load_csv("Coaches.csv")
    entries = load_csv("EntriesGender.csv")
    medals = load_csv("Medals.csv")
    teams = load_csv("Teams.csv")

    results = {
        "Athletes": profile_dataframe(
            athletes,
            "Athletes",
            ["PersonName", "Country", "Discipline"],
        ),
        "Coaches": profile_dataframe(
            coaches,
            "Coaches",
            ["Name", "Country", "Discipline", "Event"],
        ),
        "EntriesGender": profile_dataframe(
            entries,
            "EntriesGender",
            ["Discipline", "Female", "Male", "Total"],
        ),
        "Medals": profile_dataframe(
            medals,
            "Medals",
            [
                "Rank",
                "TeamCountry",
                "Gold",
                "Silver",
                "Bronze",
                "Total",
                "Rank by Total",
            ],
        ),
        "Teams": profile_dataframe(
            teams,
            "Teams",
            ["TeamName", "Discipline", "Country", "Event"],
        ),
    }

    results["Medals"]["invalid_medal_totals"] = check_medal_totals(medals)

    results["Medals"]["negative_values"] = check_non_negative(
        medals,
        ["Gold", "Silver", "Bronze", "Total"],
    )

    results["EntriesGender"]["invalid_gender_totals"] = check_gender_totals(
        entries
    )

    results["EntriesGender"]["negative_values"] = check_non_negative(
        entries,
        ["Female", "Male", "Total"],
    )

    return results


if __name__ == "__main__":
    results = run_quality_checks()

    for dataset, checks in results.items():
        print("\n" + "=" * 70)
        print(dataset)
        print("=" * 70)

        for check, value in checks.items():
            print(f"{check}: {value}")
