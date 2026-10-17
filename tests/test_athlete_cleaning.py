import unittest
from unittest.mock import patch

import pandas as pd

from src.features.build_analytics import build_country_analytics
from src.features.build_features import build_country_features
from src.quality.data_quality import clean_athlete_names, load_csv


class AthleteCleaningTests(unittest.TestCase):
    def test_whitespace_only_cleaning_copy_and_idempotence(self):
        raw = pd.DataFrame({
            "PersonName": [" \tÉlodie  D'Ávila\n", "van ROUWENDAAL Sharon", None, pd.NA],
            "Country": [" France "] * 4,
            "Discipline": ["Swimming"] * 4,
        }, index=[7, 3, 8, 2])
        original = raw.copy(deep=True)
        expected = raw.copy(deep=True)
        expected.loc[7, "PersonName"] = "Élodie  D'Ávila"
        cleaned = clean_athlete_names(raw)
        pd.testing.assert_frame_equal(cleaned, expected)
        pd.testing.assert_frame_equal(raw, original)
        pd.testing.assert_frame_equal(clean_athlete_names(cleaned), cleaned)

    def test_source_findings_and_exact_deduplication(self):
        raw = load_csv("Athletes.csv")
        original = raw.copy(deep=True)
        duplicates = raw.loc[raw.duplicated(keep=False)]
        self.assertEqual(duplicates.to_dict("records"), [
            {"PersonName": "ALI Mohamed", "Country": "Bahrain", "Discipline": "Handball"},
        ] * 2)
        whitespace = raw.loc[raw.PersonName.ne(raw.PersonName.str.strip())]
        self.assertEqual(whitespace.to_dict("records"), [
            {"PersonName": "GIRAUD Aurelien ", "Country": "France", "Discipline": "Skateboarding"},
        ])
        cleaned = clean_athlete_names(raw)
        self.assertEqual(len(cleaned), 11085)
        self.assertEqual(cleaned.duplicated().sum(), 1)
        deduplicated = cleaned.drop_duplicates()
        self.assertEqual(len(deduplicated), 11084)
        repeated_names = deduplicated.loc[
            deduplicated.duplicated(["Country", "PersonName"], keep=False)
        ]
        self.assertEqual(len(repeated_names), 26)
        self.assertEqual(repeated_names.groupby(["Country", "PersonName"]).ngroups, 13)
        pd.testing.assert_frame_equal(raw, original)

    def test_both_builders_clean_before_exact_dedup_and_preserve_distinct_records(self):
        athletes = pd.DataFrame([
            (" Élodie ", "France", "Swimming"),
            ("Élodie", "France", "Swimming"),
            ("Élodie", "France", "Athletics"),
            ("Élodie", "Japan", "Judo"),
        ], columns=["PersonName", "Country", "Discipline"])
        self.assertEqual(len(clean_athlete_names(athletes).drop_duplicates()), 3)
        original = athletes.copy(deep=True)
        results = []
        for module, builder in (
            ("src.features.build_features", build_country_features),
            ("src.features.build_analytics", build_country_analytics),
        ):
            with self.subTest(builder=builder.__name__):
                def source(filename):
                    raw = load_csv(filename)
                    if filename == "Athletes.csv":
                        # Keep other country keys so the full-source join gate
                        # can still verify the existing medal and team records.
                        return pd.concat([raw.loc[~raw.Country.isin(["France", "Japan"])],
                                          athletes], ignore_index=True)
                    return raw

                with patch(module + ".load_csv", side_effect=source):
                    with patch("src.quality.gates.clean_athlete_names", wraps=clean_athlete_names) as clean:
                        result = builder().set_index("country")
                clean.assert_called_once()
                self.assertEqual(result.loc["France", "athlete_count"], 1)
                self.assertEqual(result.loc["France", "athlete_discipline_count"], 2)
                self.assertEqual(result.loc["Japan", "athlete_count"], 1)
                results.append(result[["athlete_count", "athlete_discipline_count"]].sort_index())
        pd.testing.assert_frame_equal(results[0], results[1], check_dtype=False)
        pd.testing.assert_frame_equal(athletes, original)

    def test_real_builder_integrity_and_name_count_proxy(self):
        for builder in (build_country_features, build_country_analytics):
            with self.subTest(builder=builder.__name__):
                result = builder()
                self.assertEqual(len(result), 206)
                self.assertEqual(result.athlete_count.sum(), 11071)
                self.assertEqual(result.set_index("country").loc["France", "athlete_count"], 377)
                self.assertEqual(result[["Gold", "Silver", "Bronze", "Total"]].sum().to_dict(),
                                 {"Gold": 340, "Silver": 338, "Bronze": 402, "Total": 1080})


if __name__ == "__main__":
    unittest.main()
