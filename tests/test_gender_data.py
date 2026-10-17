import unittest
from unittest.mock import patch

import pandas as pd

from src.quality.data_quality import load_csv, run_quality_checks
from src.quality.gender_data import validate_gender_data


class GenderDataTests(unittest.TestCase):
    def valid_entries(self):
        return pd.DataFrame({"Discipline": ["A", "B"], "Female": [2, 0],
                             "Male": [3, 4], "Total": [5, 4]})

    def test_valid_data_and_input_preservation(self):
        entries = self.valid_entries()
        original = entries.copy(deep=True)
        report = validate_gender_data(entries)
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["totals"], {"Female": 2, "Male": 7, "Total": 9})
        pd.testing.assert_frame_equal(entries, original)

    def test_invalid_arithmetic(self):
        entries = self.valid_entries()
        entries.loc[0, "Total"] = 6
        report = validate_gender_data(entries)
        self.assertEqual(report["invalid_gender_totals"], 1)
        self.assertIn("invalid_gender_totals", [e["code"] for e in report["errors"]])

    def test_invalid_counts(self):
        for value, expected in [(-1, "negative_count"), (1.5, "invalid_integer_count"),
                                (float("inf"), "invalid_integer_count"),
                                (True, "invalid_integer_count"), ("2", "invalid_integer_count"),
                                (None, "missing_count")]:
            with self.subTest(value=value):
                entries = self.valid_entries().astype({"Female": object})
                entries.loc[0, "Female"] = value
                self.assertIn(expected, [e["code"] for e in validate_gender_data(entries)["errors"]])
        entries = self.valid_entries().assign(Female=None)
        self.assertIn("missing_count", [e["code"] for e in validate_gender_data(entries)["errors"]])

    def test_duplicate_disciplines_are_errors_not_silently_removed(self):
        for conflicting in (False, True):
            entries = self.valid_entries()
            extra = entries.iloc[[0]].copy()
            if conflicting:
                extra["Female"], extra["Total"] = 3, 6
            entries = pd.concat([entries, extra], ignore_index=True)
            original = entries.copy(deep=True)
            report = validate_gender_data(entries)
            self.assertIn("duplicate_discipline", [e["code"] for e in report["errors"]])
            pd.testing.assert_frame_equal(entries, original)

    def test_missing_schema_and_discipline_fields(self):
        for column in self.valid_entries():
            report = validate_gender_data(self.valid_entries().drop(columns=column))
            self.assertEqual(report["errors"][0]["code"], "invalid_schema")
        for value in (None, " \t", 123):
            entries = self.valid_entries().astype({"Discipline": object})
            entries.loc[0, "Discipline"] = value
            self.assertIn("invalid_discipline", [e["code"] for e in validate_gender_data(entries)["errors"]])
        duplicate_columns = pd.DataFrame([[1, 2]], columns=["Total", "Total"])
        self.assertTrue(validate_gender_data(duplicate_columns)["errors"][0]["duplicate_column_labels"])

    def test_coverage_difference_is_warning_and_comparison_preserves_records(self):
        entries = self.valid_entries()
        athletes = pd.DataFrame({"PersonName": ["Same", "Same", "Other"],
                                 "Country": ["X", "X", "Y"], "Discipline": ["A", "A", "C"]})
        original = athletes.copy(deep=True)
        report = validate_gender_data(entries, athletes)
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["discipline_coverage"], {"gender_only": ["B"], "athlete_only": ["C"]})
        self.assertEqual(report["raw_athlete_rows"], 3)
        self.assertEqual(report["discipline_comparison"], [{
            "discipline": "A", "gender_entries": 5, "raw_athlete_rows": 2, "difference": 3,
        }])
        pd.testing.assert_frame_equal(athletes, original)

    def test_current_data_integrity_and_quality_integration(self):
        entries, athletes = load_csv("EntriesGender.csv"), load_csv("Athletes.csv")
        original_entries, original_athletes = entries.copy(deep=True), athletes.copy(deep=True)
        report = validate_gender_data(entries, athletes)
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["rows"], 46)
        self.assertEqual(report["totals"], {"Female": 5432, "Male": 5884, "Total": 11316})
        self.assertEqual(report["discipline_coverage"], {"gender_only": [], "athlete_only": []})
        self.assertEqual(report["gender_minus_raw_athlete_rows"], 231)
        comparisons = report["discipline_comparison"]
        self.assertEqual(sum(c["difference"] for c in comparisons), 231)
        self.assertEqual(sum(c["difference"] != 0 for c in comparisons), 45)
        pd.testing.assert_frame_equal(entries, original_entries)
        pd.testing.assert_frame_equal(athletes, original_athletes)
        self.assertEqual(run_quality_checks()["EntriesGender"]["validation"], report)

    def test_quality_runner_reports_invalid_schema_without_arithmetic_crash(self):
        def source(filename):
            frame = load_csv(filename)
            return frame.drop(columns="Female") if filename == "EntriesGender.csv" else frame

        with patch("src.quality.data_quality.load_csv", side_effect=source):
            result = run_quality_checks()["EntriesGender"]
        self.assertIn("invalid_schema", [e["code"] for e in result["validation"]["errors"]])


if __name__ == "__main__":
    unittest.main()
