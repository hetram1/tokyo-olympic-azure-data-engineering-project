"""Read-only validation of discipline-level gender entries and source coverage."""

import math
from numbers import Real

import pandas as pd


def validate_gender_data(entries: pd.DataFrame, athletes: pd.DataFrame | None = None) -> dict:
    """Report structural errors and observational warnings without cleaning data.

    Counts must be finite, non-negative integer-valued numbers (not booleans or
    numeric strings). Gender totals are entry aggregates, not verified people.
    Cross-source comparison uses exact discipline labels and raw athlete rows.
    """
    required = ["Discipline", "Female", "Male", "Total"]
    report = {"rows": len(entries), "errors": [], "warnings": [],
              "invalid_gender_totals": 0, "negative_values": {}}
    missing = [column for column in required if column not in entries.columns]
    if missing or not entries.columns.is_unique:
        report["errors"].append({"code": "invalid_schema", "missing_columns": missing,
                                 "duplicate_column_labels": not entries.columns.is_unique})
        return report

    discipline_valid = entries.Discipline.map(lambda v: isinstance(v, str) and bool(v.strip()))
    if not discipline_valid.all():
        report["errors"].append({"code": "invalid_discipline", "rows": int((~discipline_valid).sum())})
    labels = entries.loc[discipline_valid, "Discipline"]
    duplicate_count = int(labels.duplicated().sum())
    if duplicate_count:
        report["errors"].append({"code": "duplicate_discipline", "rows": duplicate_count,
                                 "disciplines": sorted(labels[labels.duplicated(keep=False)].unique())})
    whitespace = labels.ne(labels.str.strip())
    if whitespace.any():
        report["warnings"].append({"code": "discipline_whitespace", "rows": int(whitespace.sum())})

    valid_counts = pd.Series(True, index=entries.index)
    for column in required[1:]:
        values = entries[column]
        missing_count = int(values.isna().sum())
        if missing_count:
            report["errors"].append({"code": "missing_count", "column": column, "rows": missing_count})
        valid = values.map(lambda v: isinstance(v, Real) and not isinstance(v, bool)
                          and math.isfinite(v) and v == int(v))
        invalid = ~valid & ~values.isna()
        if invalid.any():
            report["errors"].append({"code": "invalid_integer_count", "column": column,
                                     "rows": int(invalid.sum())})
        negative = values.map(lambda v: isinstance(v, Real) and not isinstance(v, bool)
                             and math.isfinite(v) and v < 0)
        report["negative_values"][column] = int(negative.sum())
        if negative.any():
            report["errors"].append({"code": "negative_count", "column": column,
                                     "rows": int(negative.sum())})
        valid_counts &= valid & ~negative

    # Python integers avoid overflow in fixed-width integer arithmetic.
    usable = entries.loc[valid_counts, required[1:]]
    bad_totals = sum(int(female) + int(male) != int(total)
                     for female, male, total in usable.itertuples(index=False, name=None))
    report["invalid_gender_totals"] = bad_totals
    if bad_totals:
        report["errors"].append({"code": "invalid_gender_totals", "rows": bad_totals})
    if report["errors"]:
        return report
    report["totals"] = {column: sum(int(v) for v in entries[column]) for column in required[1:]}

    if athletes is None:
        return report
    athlete_columns = ["PersonName", "Country", "Discipline"]
    if not athletes.columns.is_unique or any(c not in athletes.columns for c in athlete_columns):
        report["errors"].append({"code": "invalid_athlete_comparison_schema"})
        return report
    athlete_labels_valid = athletes.Discipline.map(lambda v: isinstance(v, str) and bool(v.strip()))
    if not athlete_labels_valid.all():
        report["errors"].append({"code": "invalid_athlete_discipline",
                                 "rows": int((~athlete_labels_valid).sum())})
        return report
    gender_labels, athlete_labels = set(labels), set(athletes.Discipline)
    coverage = {"gender_only": sorted(gender_labels - athlete_labels),
                "athlete_only": sorted(athlete_labels - gender_labels)}
    report["discipline_coverage"] = coverage
    if any(coverage.values()):
        report["warnings"].append({"code": "discipline_coverage_difference", **coverage})
    rows_by_discipline = athletes.groupby("Discipline").size()
    gender_by_discipline = entries.set_index("Discipline").Total
    report["discipline_comparison"] = [
        {"discipline": label, "gender_entries": int(gender_by_discipline[label]),
         "raw_athlete_rows": int(rows_by_discipline[label]),
         "difference": int(gender_by_discipline[label]) - int(rows_by_discipline[label])}
        for label in sorted(gender_labels & athlete_labels)
    ]
    difference = report["totals"]["Total"] - len(athletes)
    report["raw_athlete_rows"] = len(athletes)
    report["gender_minus_raw_athlete_rows"] = difference
    mismatch_count = sum(row["difference"] != 0 for row in report["discipline_comparison"])
    if difference or mismatch_count:
        report["warnings"].append({"code": "participation_count_difference",
                                   "overall_difference": difference,
                                   "mismatched_common_disciplines": mismatch_count})
    report["warnings"].append({
        "code": "source_granularity_limit",
        "message": "Discipline gender entries and athlete records are not proven equivalent; "
                   "names are not reliable person IDs and Athletes has no gender field. "
                   "Differences cannot establish missing people or gender assignments.",
    })
    return report
