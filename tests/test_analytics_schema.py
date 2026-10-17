import unittest

import pandas as pd

from src.features.build_analytics import build_country_analytics
from src.features.build_features import build_country_features
from src.features.build_powerbi_dataset import (
    NUMERIC_COLUMNS,
    REQUIRED_COLUMNS,
    prepare_powerbi_dataset,
)


class AnalyticsSchemaTests(unittest.TestCase):
    def test_analytics_schema_and_retained_values(self):
        analytics = build_country_analytics()
        expected = [
            "country", "athlete_count", "athlete_discipline_count",
            "team_count", "team_discipline_count", "team_event_count",
            "Gold", "Silver", "Bronze", "Total", "medal_rate_per_athlete",
            "gold_share", "medals_per_discipline", "performance_class",
        ]
        self.assertEqual(list(analytics.columns), expected)
        self.assertEqual(REQUIRED_COLUMNS, expected)
        self.assertEqual(NUMERIC_COLUMNS, expected[1:-1])
        features = build_country_features().set_index("country").sort_index()
        retained = analytics.set_index("country").sort_index()
        pd.testing.assert_frame_equal(features, retained[features.columns], check_dtype=False)
        self.assertEqual(len(analytics), 206)
        self.assertEqual(analytics[["Gold", "Silver", "Bronze", "Total"]].sum().to_dict(),
                         {"Gold": 340, "Silver": 338, "Bronze": 402, "Total": 1080})

    def test_zero_event_medal_winners_have_no_team_efficiency_score(self):
        analytics = build_country_analytics()
        zero_events = analytics.loc[(analytics.team_event_count == 0) & (analytics.Total > 0)]
        self.assertFalse(zero_events.empty)
        self.assertIn("Georgia", zero_events.country.tolist())
        for table in (analytics, prepare_powerbi_dataset(analytics)):
            self.assertNotIn("medals_per_team_event", table.columns)
        self.assertEqual(zero_events.set_index("country").loc["Georgia", "Total"], 8)

    def test_export_preserves_columns_ranks_and_labels_without_mutating_input(self):
        analytics = build_country_analytics()
        original = analytics.copy(deep=True)
        dashboard = prepare_powerbi_dataset(analytics)
        self.assertEqual(list(dashboard.columns), REQUIRED_COLUMNS + ["medal_rank", "performance_label"])
        self.assertEqual(len(dashboard), 206)
        pd.testing.assert_frame_equal(
            dashboard[REQUIRED_COLUMNS].sort_values("country").reset_index(drop=True),
            analytics.sort_values("country").reset_index(drop=True),
            check_dtype=False,
        )
        self.assertEqual(dashboard.iloc[0]["country"], "United States of America")
        pd.testing.assert_series_equal(
            dashboard.medal_rank,
            dashboard.Total.rank(method="min", ascending=False).astype(int),
            check_names=False,
        )
        self.assertEqual(dashboard.performance_label.tolist(),
                         dashboard.performance_class.astype(str).str.strip().tolist())
        pd.testing.assert_frame_equal(analytics, original)

    def test_export_drops_legacy_kpi_and_still_requires_retained_columns(self):
        analytics = build_country_analytics()
        expected = prepare_powerbi_dataset(analytics)
        legacy = analytics.assign(medals_per_team_event=123.0)
        pd.testing.assert_frame_equal(prepare_powerbi_dataset(legacy), expected)
        self.assertIn("medals_per_team_event", legacy.columns)
        with self.assertRaisesRegex(ValueError, "team_event_count"):
            prepare_powerbi_dataset(analytics.drop(columns="team_event_count"))


if __name__ == "__main__":
    unittest.main()
