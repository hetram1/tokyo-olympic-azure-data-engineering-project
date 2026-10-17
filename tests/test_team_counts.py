import unittest

import pandas as pd

from src.features.build_analytics import build_country_analytics
from src.features.build_features import build_country_features
from src.features.team_counts import TEAM_ENTRY_KEY, TEAM_EVENT_KEY, aggregate_team_counts
from src.quality.data_quality import load_csv, normalize_country_key
from src.quality.team_text import correct_team_text


class TeamCountTests(unittest.TestCase):
    def test_repeated_names_shared_event_labels_and_multiple_entries(self):
        teams = pd.DataFrame([
            ("A", "Basketball", "Men", "National team", 1),
            ("A", "Basketball", "Women", "National team", 2),
            ("A", "Volleyball", "Men", "National team", 3),
            ("A", "Volleyball", "Women", "National team", 4),
            ("A", "Beach Volleyball", "Men", "Pair 1", 5),
            ("A", "Beach Volleyball", "Men", "Pair 2", 6),
            ("A", "Beach Volleyball", "Men", "Pair 2", 7),
            ("B", "Basketball", "Men", "National team", 8),
        ], columns=TEAM_ENTRY_KEY + ["extra_metadata"])
        original = teams.copy(deep=True)
        counts = aggregate_team_counts(teams).set_index("country")
        self.assertEqual(counts.loc["A"].to_dict(), {
            "team_count": 6, "team_discipline_count": 3, "team_event_count": 5,
        })
        self.assertEqual(counts.loc["B"].to_dict(), {
            "team_count": 1, "team_discipline_count": 1, "team_event_count": 1,
        })
        pd.testing.assert_frame_equal(teams, original)

    def test_source_composite_identity_and_multiple_pairs(self):
        teams = correct_team_text(load_csv("Teams.csv"))
        teams["Country"] = teams["Country"].map(normalize_country_key)
        self.assertEqual(len(teams), 743)
        self.assertEqual(teams.duplicated().sum(), 0)
        self.assertEqual(teams.duplicated(TEAM_ENTRY_KEY).sum(), 0)
        self.assertEqual(teams.duplicated(TEAM_EVENT_KEY).sum(), 12)
        counts = aggregate_team_counts(teams)
        self.assertEqual(counts.team_count.sum(), 743)
        self.assertEqual(counts.team_event_count.sum(), 731)

    def test_builders_agree_and_preserve_country_and_medal_totals(self):
        features = build_country_features().set_index("country").sort_index()
        analytics = build_country_analytics().set_index("country").sort_index()
        pd.testing.assert_frame_equal(features, analytics[features.columns], check_dtype=False)
        for frame in (features, analytics):
            self.assertEqual(len(frame), 206)
            self.assertTrue(frame.index.is_unique)
            self.assertEqual(frame[["Gold", "Silver", "Bronze", "Total"]].sum().to_dict(),
                             {"Gold": 340, "Silver": 338, "Bronze": 402, "Total": 1080})
            for country, expected in {
                "United States of America": (47, 45),
                "Japan": (48, 48),
                "People's Republic of China": (33, 32),
                "Great Britain": (28, 28),
                "Côte d'Ivoire": (1, 1),
            }.items():
                with self.subTest(country=country):
                    self.assertEqual(tuple(frame.loc[country, ["team_count", "team_event_count"]]), expected)

    def test_incomplete_identity_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Missing team identity columns"):
            aggregate_team_counts(pd.DataFrame({"Country": ["A"]}))
        incomplete = pd.DataFrame([("A", "Fencing", None, "A")], columns=TEAM_ENTRY_KEY)
        with self.assertRaisesRegex(ValueError, "missing values"):
            aggregate_team_counts(incomplete)


if __name__ == "__main__":
    unittest.main()
