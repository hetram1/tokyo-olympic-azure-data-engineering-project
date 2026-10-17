import unittest
from unittest.mock import patch

import pandas as pd

from src.features.build_analytics import build_country_analytics
from src.features.build_features import build_country_features
from src.quality.data_quality import load_csv
from src.quality.team_text import TEAM_TEXT_CORRECTIONS, correct_team_text
from src.quality.gates import DataQualityError


class TeamTextTests(unittest.TestCase):
    def test_raw_inventory_and_exact_corrections(self):
        raw = load_csv("Teams.csv")
        original = raw.copy(deep=True)
        self.assertEqual(len(raw), 743)
        counts = {
            column: raw[column].str.contains("�", regex=False).sum()
            for column in raw
        }
        self.assertEqual(counts, {
            "TeamName": 1, "Discipline": 0, "Country": 1, "Event": 17,
        })
        self.assertEqual(sum(raw[c].str.count("�").sum() for c in raw), 37)
        fixed = correct_team_text(raw)
        for column in raw:
            expected = raw[column].copy()
            for old, new in TEAM_TEXT_CORRECTIONS.get(column, {}).items():
                mask = raw[column].eq(old)
                expected.loc[mask] = new
            pd.testing.assert_series_equal(fixed[column], expected)
        self.assertEqual(fixed["Event"].eq("Men's Épée Team").sum(), 9)
        self.assertEqual(fixed["Event"].eq("Women's Épée Team").sum(), 8)
        ivory = fixed.loc[fixed["Country"].eq("Côte d'Ivoire")]
        self.assertEqual(len(ivory), 1)
        self.assertEqual(ivory.iloc[0]["TeamName"], "Côte d'Ivoire")
        self.assertFalse(fixed.apply(lambda c: c.str.contains("�", regex=False)).any().any())
        pd.testing.assert_frame_equal(raw, original)
        pd.testing.assert_frame_equal(correct_team_text(fixed), fixed)

    def test_unknown_values_missing_values_and_other_columns_are_preserved(self):
        raw = pd.DataFrame({
            "Country": ["Unknown � country", None, "Japan"],
            "TeamName": ["Unknown � team", None, "Men's �p�e Team"],
            "Discipline": ["Unknown � sport", None, "Fencing"],
            "Event": ["Unknown � event", None, "Men's Sabre Team"],
        }, index=[8, 4, 2])
        pd.testing.assert_frame_equal(correct_team_text(raw), raw)

    def test_both_builders_apply_layer_and_preserve_country_tables(self):
        # Bypassing verified repairs must now be blocked by the shared gate.
        for module, builder in (
            ("src.features.build_features", build_country_features),
            ("src.features.build_analytics", build_country_analytics),
        ):
            with self.subTest(builder=builder.__name__):
                with patch("src.quality.gates.correct_team_text", side_effect=lambda x: x):
                    with self.assertRaises(DataQualityError):
                        builder()
                with patch("src.quality.gates.correct_team_text", wraps=correct_team_text) as repair:
                    after = builder()
                repair.assert_called_once()
                self.assertEqual(len(after), 206)
                self.assertTrue(after["country"].is_unique)
                self.assertEqual(after[["Gold", "Silver", "Bronze", "Total"]].sum().to_dict(),
                                 {"Gold": 340, "Silver": 338, "Bronze": 402, "Total": 1080})


if __name__ == "__main__":
    unittest.main()
