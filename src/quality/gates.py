"""Source validation and preparation shared by both country-table builders."""

import math
from numbers import Real

import pandas as pd

from src.quality.data_quality import (
    check_medal_totals, check_non_negative, clean_and_validate_coaches,
    clean_athlete_names, load_csv, normalize_country_key,
)
from src.quality.gender_data import validate_gender_data
from src.quality.team_text import correct_team_text


SCHEMAS = {
    "Athletes": ["PersonName", "Country", "Discipline"],
    "Coaches": ["Name", "Country", "Discipline", "Event"],
    "EntriesGender": ["Discipline", "Female", "Male", "Total"],
    "Medals": ["Rank", "TeamCountry", "Gold", "Silver", "Bronze", "Total", "Rank by Total"],
    "Teams": ["TeamName", "Discipline", "Country", "Event"],
}


class DataQualityError(ValueError):
    """Blocking source errors, with the full structured report attached."""

    def __init__(self, report):
        self.report = report
        details = "\n".join(
            f"{e['dataset']}: {e['code']}: {e['message']}; records={e.get('records', [])}"
            for e in report["errors"]
        )
        super().__init__("Source data-quality gate failed. Repair or verify these inputs:\n" + details)


def validate_sources(sources: dict[str, pd.DataFrame]) -> tuple[dict, dict]:
    """Prepare copies and collect errors/warnings; never write or infer aliases.

    Record samples include source dataframe indices (CSV row index, not line
    number). All error counts are complete; samples are capped at five records.
    Call load_validated_sources for enforcement and single-pass loading.
    """
    report = {"errors": [], "warnings": [], "datasets": {}, "joins": {}}
    prepared = {}

    def issue(level, dataset, code, message, frame=None, mask=None, **details):
        item = {"dataset": dataset, "code": code, "message": message, **details}
        if frame is not None:
            affected = frame if mask is None else frame.loc[mask]
            item["affected_rows"] = len(affected)
            item["records"] = [{"source_index": str(index), **row.to_dict()}
                               for index, row in affected.head(5).iterrows()]
        report[level].append(item)

    for name, columns in SCHEMAS.items():
        raw = sources.get(name)
        if raw is None or not isinstance(raw, pd.DataFrame):
            issue("errors", name, "missing_dataset", "Supply the source dataframe")
            continue
        missing = [c for c in columns if c not in raw.columns]
        if missing or not raw.columns.is_unique:
            issue("errors", name, "invalid_schema",
                  f"Required columns missing: {missing}; column labels must be unique")
            continue
        frame = raw.copy(deep=True)
        if name == "Athletes":
            frame = clean_athlete_names(frame)
        elif name == "Teams":
            frame = correct_team_text(frame)
        elif name == "Coaches":
            frame, coach_report = clean_and_validate_coaches(frame)
            report["datasets"][name] = coach_report
            for level in ("errors", "warnings"):
                for finding in coach_report[level]:
                    sample = raw
                    column = finding.get("column")
                    if column:
                        sample = raw.loc[raw[column].map(
                            lambda v: not isinstance(v, str) or not bool(v.strip()))]
                    elif "duplicate" in finding["code"]:
                        normalized = raw.map(lambda v: v.strip() if isinstance(v, str) else v)
                        sample = raw.loc[normalized.duplicated(keep=False)]
                    elif finding["code"] == "unspecified_event":
                        sample = raw.loc[raw.Event.isna() | raw.Event.eq("").fillna(False)]
                    issue(level, name, finding["code"], str(finding), sample, **{
                        "validation": finding,
                    })
        country_column = "TeamCountry" if name == "Medals" else "Country"
        if country_column in frame:
            frame[country_column] = frame[country_column].map(normalize_country_key)

        text_columns = {"Athletes": columns, "Teams": columns,
                        "Coaches": ["Name", "Country", "Discipline"],
                        "Medals": ["TeamCountry"], "EntriesGender": ["Discipline"]}[name]
        for column in text_columns:
            invalid = ~frame[column].map(lambda v: isinstance(v, str) and bool(v.strip()))
            if invalid.any():
                issue("errors", name, "invalid_identity", f"{column} must be nonblank text",
                      frame, invalid)
        for column in frame.columns:
            bad = frame[column].map(lambda v: isinstance(v, str) and "�" in v)
            if bad.any():
                issue("errors", name, "unresolved_replacement_character",
                      f"{column} contains U+FFFD after verified corrections; verify source spelling",
                      frame, bad)

        if name in ("Athletes", "Teams"):
            duplicates = frame.duplicated()
            if duplicates.any():
                issue("warnings", name, "exact_duplicates_removed",
                      "Remove only redundant full records after existing normalization", frame, duplicates)
            frame = frame.loc[~duplicates].copy()
            key = columns  # Athlete assignment / composite team entry, not name alone.
            collision = frame.duplicated(subset=key, keep=False)
            if collision.any():
                issue("errors", name, "conflicting_duplicate_key",
                      f"Conflicting records share identity {key}; verify extra fields", frame, collision)
        prepared[name] = frame

    medals = prepared.get("Medals")
    if medals is not None:
        numeric_valid = True
        for column in ("Rank", "Gold", "Silver", "Bronze", "Total", "Rank by Total"):
            valid = medals[column].map(lambda v: isinstance(v, Real) and not isinstance(v, bool)
                                       and math.isfinite(v) and v == int(v))
            if not valid.all():
                numeric_valid = False
                issue("errors", "Medals", "invalid_integer_count",
                      f"{column} must contain finite integer numbers, not missing values, strings or booleans",
                      medals, ~valid)
        if numeric_valid:
            negative = check_non_negative(medals, ["Gold", "Silver", "Bronze", "Total"])
            for column, count in negative.items():
                if count:
                    issue("errors", "Medals", "negative_count", f"{column} must be non-negative",
                          medals, medals[column] < 0)
            if check_medal_totals(medals):
                bad = medals.Total != medals.Gold + medals.Silver + medals.Bronze
                issue("errors", "Medals", "invalid_medal_totals", "Total must equal Gold + Silver + Bronze",
                      medals, bad)
            for column in ("Rank", "Rank by Total"):
                if (medals[column] < 1).any():
                    issue("errors", "Medals", "invalid_rank", f"{column} must be positive (ties permitted)",
                          medals, medals[column] < 1)
        duplicated = medals.TeamCountry.duplicated(keep=False)
        if duplicated.any():
            issue("errors", "Medals", "duplicate_country_key",
                  "One medal row per normalized country is required; duplicates multiply joins",
                  medals, duplicated)

    entries = prepared.get("EntriesGender")
    athletes = prepared.get("Athletes")
    if entries is not None:
        # Raw athlete rows preserve the documented +231 comparison warning.
        gender_report = validate_gender_data(entries, sources.get("Athletes"))
        report["datasets"]["EntriesGender"] = gender_report
        for level in ("errors", "warnings"):
            for finding in gender_report[level]:
                column = finding.get("column")
                sample = entries
                if column:
                    sample = entries.loc[entries[column].map(
                        lambda v: not (isinstance(v, Real) and not isinstance(v, bool)
                                       and math.isfinite(v) and v == int(v) and v >= 0))]
                elif finding["code"] == "invalid_discipline":
                    sample = entries.loc[~entries.Discipline.map(
                        lambda v: isinstance(v, str) and bool(v.strip()))]
                elif finding["code"] == "duplicate_discipline":
                    sample = entries.loc[entries.Discipline.duplicated(keep=False)]
                elif finding["code"] == "invalid_gender_totals":
                    bad = entries.apply(lambda row: all(
                        isinstance(row[c], Real) and not isinstance(row[c], bool)
                        and math.isfinite(row[c]) and row[c] == int(row[c]) and row[c] >= 0
                        for c in ("Female", "Male", "Total")) and
                        int(row.Female) + int(row.Male) != int(row.Total), axis=1)
                    sample = entries.loc[bad]
                issue(level, "EntriesGender", finding["code"], str(finding),
                      sample if level == "errors" else None, validation=finding)

    # Joins are meaningful only after all text/key validation has succeeded.
    if not report["errors"]:
        teams = prepared["Teams"]
        athlete_countries = set(athletes.Country)
        team_countries = set(teams.Country)
        participation = athlete_countries | team_countries
        medal_countries = set(medals.TeamCountry)
        missing_medals = medal_countries - participation
        team_only = team_countries - athlete_countries
        report["joins"] = {
            "participating_countries": len(participation),
            "medal_countries": len(medal_countries),
            "medal_countries_without_participation": sorted(missing_medals),
            "team_countries_without_athletes": sorted(team_only),
            "countries_without_medals": sorted(participation - medal_countries),
            "athlete_countries_without_teams": sorted(athlete_countries - team_countries),
        }
        if missing_medals:
            issue("errors", "Medals", "unmatched_country_key",
                  "Medal countries lack participation keys; verify source names without guessing aliases",
                  medals, medals.TeamCountry.isin(missing_medals))
        if team_only:
            issue("errors", "Teams", "unmatched_country_key",
                  "Team countries lack athlete keys and would create zero-athlete countries; verify coverage/identity",
                  teams, teams.Country.isin(team_only))
        country_spellings = {}
        for name, frame in prepared.items():
            column = "TeamCountry" if name == "Medals" else "Country"
            if column in frame:
                for country in frame[column].unique():
                    country_spellings.setdefault(country.casefold(), set()).add(country)
        for spellings in country_spellings.values():
            if len(spellings) > 1:
                issue("errors", "Country joins", "contradictory_country_keys",
                      f"Case-only country variants require source review: {sorted(spellings)}")
        repeated = athletes.duplicated(["Country", "PersonName"], keep=False)
        if repeated.any():
            issue("warnings", "Athletes", "repeated_names",
                  "Different discipline records share names; retain records, names are not person IDs",
                  athletes, repeated)
    report["valid"] = not report["errors"]
    return prepared, report


def load_validated_sources(loader=None) -> tuple[dict, dict]:
    """Load each of five files once, enforce errors, return prepared copies/report."""
    loader = load_csv if loader is None else loader
    sources = {}
    load_errors = []
    for name in SCHEMAS:
        try:
            sources[name] = loader(name + ".csv")
        except (OSError, ValueError, KeyError) as exc:
            load_errors.append({"dataset": name, "code": "source_load_failed", "message": str(exc)})
    prepared, report = validate_sources(sources)
    report["errors"].extend(load_errors)
    report["valid"] = not report["errors"]
    if report["errors"]:
        raise DataQualityError(report)
    return prepared, report
