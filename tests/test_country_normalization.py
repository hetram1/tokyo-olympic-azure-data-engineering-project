import unittest
from unittest.mock import patch

import pandas as pd

from src.features.build_analytics import build_country_analytics
from src.features.build_features import build_country_features
from src.quality.data_quality import load_csv, normalize_country_key


class CountryNormalizationTests(unittest.TestCase):
    def test_only_known_alias_and_whitespace_are_normalized(self):
        for value, expected in [
            (" C�te d'Ivoire \t", "Côte d'Ivoire"),
            (" Côte d'Ivoire ", "Côte d'Ivoire"),
            (" Japan ", "Japan"),
            ("Unknown � country", "Unknown � country"),
            ("C�te d�Ivoire", "C�te d�Ivoire"),
            (None, None),
        ]:
            with self.subTest(value=value):
                self.assertEqual(normalize_country_key(value), expected)
                self.assertEqual(normalize_country_key(expected), expected)

    def assert_combined_country(self, table):
        self.assertNotIn("C�te d'Ivoire", table["country"].tolist())
        country = table.loc[table["country"].eq("Côte d'Ivoire")]
        self.assertEqual(len(country), 1)
        expected = {
            "athlete_count": 29,
            "athlete_discipline_count": 5,
            "team_count": 1,
            "team_discipline_count": 1,
            "team_event_count": 1,
            "Gold": 0,
            "Silver": 0,
            "Bronze": 1,
            "Total": 1,
        }
        self.assertEqual(country.iloc[0][list(expected)].to_dict(), expected)
        self.assertEqual(len(table), 206)
        self.assertTrue(table["country"].is_unique)
        self.assertEqual(table["Total"].sum(), 1080)

    def test_both_country_tables_combine_source_information(self):
        for builder in (build_country_features, build_country_analytics):
            with self.subTest(builder=builder.__name__):
                self.assert_combined_country(builder())

    def test_all_country_join_inputs_trim_whitespace_without_mutation(self):
        sources = {
            filename: load_csv(filename)
            for filename in ("Athletes.csv", "Teams.csv", "Medals.csv", "Coaches.csv", "EntriesGender.csv")
        }
        for filename, frame in sources.items():
            if filename == "EntriesGender.csv":
                continue
            column = "TeamCountry" if filename == "Medals.csv" else "Country"
            frame[column] = " \t" + frame[column] + " "
        originals = {name: frame.copy(deep=True) for name, frame in sources.items()}
        for module, builder in (
            ("src.features.build_features", build_country_features),
            ("src.features.build_analytics", build_country_analytics),
        ):
            with self.subTest(builder=builder.__name__):
                with patch(module + ".load_csv", side_effect=sources.__getitem__):
                    self.assert_combined_country(builder())
                for name, frame in sources.items():
                    pd.testing.assert_frame_equal(frame, originals[name])

    def test_raw_loader_preserves_corrupted_source_country(self):
        teams = load_csv("Teams.csv")
        self.assertEqual(teams["Country"].eq("C�te d'Ivoire").sum(), 1)
        self.assertIn("C�te d�Ivoire", teams["TeamName"].tolist())


if __name__ == "__main__":
    unittest.main()
