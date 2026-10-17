"""Verified, exact Teams.csv text repairs; evidence: docs/teams_text_corrections.md."""

import pandas as pd


# Column-specific aliases only. Never replace arbitrary U+FFFD characters.
TEAM_TEXT_CORRECTIONS = {
    "Country": {"C�te d'Ivoire": "Côte d'Ivoire"},
    "TeamName": {"C�te d�Ivoire": "Côte d'Ivoire"},
    "Event": {
        "Men's �p�e Team": "Men's Épée Team",
        "Women's �p�e Team": "Women's Épée Team",
    },
}


def correct_team_text(teams: pd.DataFrame) -> pd.DataFrame:
    """Return a corrected copy, preserving raw input, index and unknown values.

    Country whitespace normalization remains the responsibility of
    normalize_country_key, applied by both country-table builders.
    """
    corrected = teams.copy(deep=True)
    for column, aliases in TEAM_TEXT_CORRECTIONS.items():
        corrected[column] = corrected[column].replace(aliases)
    return corrected
