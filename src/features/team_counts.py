"""Shared counting definitions for normalized, text-corrected team records."""

import pandas as pd


TEAM_ENTRY_KEY = ["Country", "Discipline", "Event", "TeamName"]
TEAM_EVENT_KEY = ["Country", "Discipline", "Event"]


def aggregate_team_counts(teams: pd.DataFrame) -> pd.DataFrame:
    """Count distinct entries and discipline/event pairs per country.

    Callers apply country normalization and verified Teams text corrections
    first. TeamName distinguishes multiple entries in the same country/event
    (e.g. beach volleyball pairs); it is not a globally unique team identity.
    Duplicate composite entries count once, even with differing extra columns.
    """
    missing = [column for column in TEAM_ENTRY_KEY if column not in teams.columns]
    if missing:
        raise ValueError(f"Missing team identity columns: {missing}")
    if teams[TEAM_ENTRY_KEY].isna().any().any():
        raise ValueError("Team identity columns must not contain missing values")

    entries = teams.drop_duplicates(subset=TEAM_ENTRY_KEY)
    counts = entries.groupby("Country").agg(
        team_count=("TeamName", "size"),
        team_discipline_count=("Discipline", "nunique"),
    )
    counts["team_event_count"] = (
        entries.drop_duplicates(subset=TEAM_EVENT_KEY).groupby("Country").size()
    )
    return counts.reset_index().rename(columns={"Country": "country"})
