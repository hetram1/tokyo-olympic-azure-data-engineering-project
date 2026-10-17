from pathlib import Path

import pandas as pd

from src.quality.gender_data import validate_gender_data

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def clean_and_validate_coaches(coaches: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Clean a copy and report errors separately from permitted missing events.

    Event is optional: an absent assignment is not evidence of an invalid coach.
    See docs/coach_cleaning.md. No assignments or coach identities are inferred.
    """
    cleaned = coaches.copy(deep=True)
    required = ["Name", "Country", "Discipline", "Event"]
    report = {
        "input_rows": len(coaches),
        "output_rows": len(coaches),
        "duplicate_rows_removed": 0,
        "errors": [],
        "warnings": [],
    }
    missing = check_required_columns(coaches, required)
    if missing or not coaches.columns.is_unique:
        report["errors"].append({
            "code": "invalid_schema",
            "missing_columns": missing,
            "duplicate_column_labels": not coaches.columns.is_unique,
        })
        return cleaned, report

    for column in required:
        cleaned[column] = cleaned[column].map(
            lambda value: value.strip() if isinstance(value, str) else value
        )
        invalid = cleaned[column].map(
            lambda value: not isinstance(value, str) and not pd.isna(value)
        )
        if invalid.any():
            report["errors"].append({
                "code": "invalid_text_type", "column": column,
                "rows": int(invalid.sum()),
            })
        if column != "Event":
            absent = cleaned[column].isna() | cleaned[column].eq("").fillna(False)
            if absent.any():
                report["errors"].append({
                    "code": "missing_identity", "column": column,
                    "rows": int(absent.sum()),
                })

    # A whitespace-only optional Event represents an unspecified assignment.
    cleaned["Event"] = cleaned["Event"].mask(cleaned["Event"].eq("").fillna(False), pd.NA)
    duplicates = cleaned.duplicated()
    removed = int(duplicates.sum())
    known = (
        cleaned["Name"].eq("GUERRERO Rolando")
        & cleaned["Country"].eq("Mexico")
        & cleaned["Discipline"].eq("Baseball/Softball")
        & cleaned["Event"].eq("Softball")
    ).fillna(False)
    # Only the one documented redundant row is expected; other duplicates
    # are removed by the same exact-row rule but remain explicit errors.
    expected = min(int((duplicates & known).sum()), 1)
    if expected:
        report["warnings"].append({"code": "known_exact_duplicate", "rows": expected})
    if removed > expected:
        report["errors"].append({
            "code": "unexpected_exact_duplicates", "rows": removed - expected,
        })
    cleaned = cleaned.loc[~duplicates].copy()
    missing_events = cleaned["Event"].isna()
    if missing_events.any():
        distribution = cleaned.loc[missing_events].groupby("Discipline", dropna=False).size()
        report["warnings"].append({
            "code": "unspecified_event",
            "rows": int(missing_events.sum()),
            "by_discipline": {str(key): int(value) for key, value in distribution.items()},
        })
    report["output_rows"] = len(cleaned)
    report["duplicate_rows_removed"] = removed
    return cleaned, report


def clean_athlete_names(athletes: pd.DataFrame) -> pd.DataFrame:
    """Strip surrounding PersonName whitespace on a copy, without inferring IDs.

    Preserve accents, case, internal whitespace and non-string/missing values.
    Callers remove exact full-row duplicates after normalizing country keys;
    matching names alone never justify removing distinct source records.
    """
    cleaned = athletes.copy(deep=True)
    cleaned["PersonName"] = cleaned["PersonName"].map(
        lambda value: value.strip() if isinstance(value, str) else value
    )
    return cleaned


def normalize_country_key(value: str) -> str:
    """Trim a country key and repair only the documented Teams.csv alias.

    Apply to derived join keys, leaving loaded source values unchanged for
    provenance and raw quality profiling. Missing/non-string values pass through.
    """
    if not isinstance(value, str):
        return value
    value = value.strip()
    return {"C�te d'Ivoire": "Côte d'Ivoire"}.get(value, value)


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

    # Preserve raw profiling above; expose the coach policy as a separate result.
    _, results["Coaches"]["cleaning_validation"] = clean_and_validate_coaches(coaches)

    results["Medals"]["invalid_medal_totals"] = check_medal_totals(medals)

    results["Medals"]["negative_values"] = check_non_negative(
        medals,
        ["Gold", "Silver", "Bronze", "Total"],
    )

    gender_validation = validate_gender_data(entries, athletes)
    results["EntriesGender"]["validation"] = gender_validation
    results["EntriesGender"]["invalid_gender_totals"] = gender_validation["invalid_gender_totals"]
    results["EntriesGender"]["negative_values"] = gender_validation["negative_values"]

    return results


if __name__ == "__main__":
    results = run_quality_checks()

    for dataset, checks in results.items():
        print("\n" + "=" * 70)
        print(dataset)
        print("=" * 70)

        for check, value in checks.items():
            print(f"{check}: {value}")
