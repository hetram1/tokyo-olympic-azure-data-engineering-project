import unittest
from unittest.mock import patch

import pandas as pd

from src.quality.data_quality import clean_and_validate_coaches, load_csv, run_quality_checks


class CoachCleaningTests(unittest.TestCase):
    def test_real_source_missing_events_and_known_duplicate(self):
        raw = load_csv("Coaches.csv")
        original = raw.copy(deep=True)
        duplicates = raw.loc[raw.duplicated(keep=False)]
        self.assertEqual(duplicates.to_dict("records"), [{
            "Name": "GUERRERO Rolando", "Country": "Mexico",
            "Discipline": "Baseball/Softball", "Event": "Softball",
        }] * 2)
        cleaned, report = clean_and_validate_coaches(raw)
        self.assertEqual((len(raw), len(cleaned)), (394, 393))
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["duplicate_rows_removed"], 1)
        warnings = {warning["code"]: warning for warning in report["warnings"]}
        self.assertEqual(warnings["known_exact_duplicate"]["rows"], 1)
        self.assertEqual(warnings["unspecified_event"]["rows"], 145)
        self.assertEqual(warnings["unspecified_event"]["by_discipline"], {
            "Artistic Swimming": 28, "Basketball": 50, "Football": 31,
            "Handball": 5, "Hockey": 9, "Rugby Sevens": 1, "Volleyball": 21,
        })
        self.assertEqual(cleaned.Event.isna().sum(), 145)
        pd.testing.assert_frame_equal(raw, original)

    def test_whitespace_idempotence_and_unspecified_events(self):
        raw = pd.DataFrame([
            (" Élodie  Martin\t", " France ", " Swimming\n", " Men "),
            (" Coach B ", "Japan", "Football", None),
            ("Coach C", "Japan", "Football", " \t"),
        ], columns=["Name", "Country", "Discipline", "Event"], index=[9, 4, 2])
        original = raw.copy(deep=True)
        cleaned, report = clean_and_validate_coaches(raw)
        self.assertEqual(cleaned.loc[9].tolist(), ["Élodie  Martin", "France", "Swimming", "Men"])
        self.assertTrue(cleaned.loc[[4, 2], "Event"].isna().all())
        self.assertEqual(report["errors"], [])
        again, _ = clean_and_validate_coaches(cleaned)
        pd.testing.assert_frame_equal(again, cleaned)
        pd.testing.assert_frame_equal(raw, original)

    def test_exact_dedup_after_normalization_preserves_distinct_assignments(self):
        raw = pd.DataFrame([
            (" Coach A ", " France ", "Hockey", " Men "),
            ("Coach A", "France", "Hockey", "Men"),
            ("Coach A", "France", "Hockey", "Women"),
            ("Coach A", "France", "Football", "Men"),
            ("Coach A", "Japan", "Hockey", "Men"),
            ("Coach A", "France", "Hockey", None),
        ], columns=["Name", "Country", "Discipline", "Event"])
        cleaned, report = clean_and_validate_coaches(raw)
        self.assertEqual(len(cleaned), 5)
        self.assertEqual(cleaned.duplicated().sum(), 0)
        self.assertEqual(report["errors"], [{"code": "unexpected_exact_duplicates", "rows": 1}])
        self.assertEqual(cleaned.Event.isna().sum(), 1)

    def test_invalid_schema_identity_and_types_are_errors(self):
        raw = pd.DataFrame({"Name": ["Coach"]})
        cleaned, report = clean_and_validate_coaches(raw)
        self.assertEqual(report["errors"][0]["code"], "invalid_schema")
        pd.testing.assert_frame_equal(raw, cleaned)
        repeated_columns = pd.DataFrame([["A", "B"]], columns=["Name", "Name"])
        _, report = clean_and_validate_coaches(repeated_columns)
        self.assertTrue(report["errors"][0]["duplicate_column_labels"])
        invalid = pd.DataFrame({
            "Name": [" \t", "Coach"], "Country": [None, "Japan"],
            "Discipline": ["Football", 123], "Event": [None, 42],
        })
        _, report = clean_and_validate_coaches(invalid)
        errors = {(e["code"], e.get("column")) for e in report["errors"]}
        self.assertEqual(errors, {
            ("missing_identity", "Name"), ("missing_identity", "Country"),
            ("invalid_text_type", "Discipline"), ("invalid_text_type", "Event"),
        })

    def test_quality_integration_keeps_raw_profile_and_other_datasets(self):
        results = run_quality_checks()
        self.assertEqual(results["Coaches"]["rows"], 394)
        self.assertEqual(results["Coaches"]["missing_values"], {"Event": 145})
        self.assertEqual(results["Coaches"]["duplicate_rows"], 1)
        self.assertEqual(results["Coaches"]["cleaning_validation"]["output_rows"], 393)
        with patch("src.quality.data_quality.clean_and_validate_coaches",
                   return_value=(None, {"sentinel": True})):
            other = run_quality_checks()
        for dataset in ("Athletes", "Teams", "Medals", "EntriesGender"):
            self.assertEqual(results[dataset], other[dataset])


if __name__ == "__main__":
    unittest.main()
