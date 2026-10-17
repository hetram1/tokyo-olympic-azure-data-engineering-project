import unittest
from unittest.mock import patch

import pandas as pd

from src.features.build_features import build_country_features
from src.features.build_analytics import build_country_analytics
from src.quality.gates import DataQualityError, SCHEMAS, load_validated_sources, validate_sources


def valid_sources():
    return {
        "Athletes": pd.DataFrame([
            ("Alex", "A", "Swimming"), ("Alex", "A", "Athletics"),
            ("Blair", "B", "Swimming"),
        ], columns=SCHEMAS["Athletes"]),
        "Teams": pd.DataFrame([("A", "Swimming", "A", "Relay")],
                              columns=SCHEMAS["Teams"]),
        "Medals": pd.DataFrame([(1, "A", 1, 0, 0, 1, 1)], columns=SCHEMAS["Medals"]),
        "Coaches": pd.DataFrame([("Coach", "A", "Swimming", None)], columns=SCHEMAS["Coaches"]),
        "EntriesGender": pd.DataFrame([("Swimming", 2, 2, 4), ("Athletics", 1, 1, 2)],
                                      columns=SCHEMAS["EntriesGender"]),
    }


class QualityGateTests(unittest.TestCase):
    def enforce(self, sources):
        return load_validated_sources(loader=lambda file: sources[file.removesuffix(".csv")])

    def assert_blocked(self, sources, dataset, code):
        with self.assertRaises(DataQualityError) as context:
            self.enforce(sources)
        errors = context.exception.report["errors"]
        self.assertTrue(any(e["dataset"] == dataset and e["code"] == code for e in errors), errors)
        self.assertIn(dataset, str(context.exception))
        return errors

    def test_valid_input_warnings_and_no_mutation(self):
        sources = valid_sources()
        originals = {k: v.copy(deep=True) for k, v in sources.items()}
        prepared, report = self.enforce(sources)
        self.assertTrue(report["valid"])
        warnings = {w["code"] for w in report["warnings"]}
        self.assertTrue({"unspecified_event", "participation_count_difference",
                         "source_granularity_limit", "repeated_names"}.issubset(warnings))
        self.assertEqual(report["joins"]["countries_without_medals"], ["B"])
        self.assertEqual(report["joins"]["athlete_countries_without_teams"], ["B"])
        self.assertTrue(pd.isna(prepared["Coaches"].iloc[0].Event))
        for name in sources:
            pd.testing.assert_frame_equal(sources[name], originals[name])

    def test_schema_and_required_identities_block(self):
        for dataset, columns in SCHEMAS.items():
            for column in columns:
                sources = valid_sources()
                sources[dataset] = sources[dataset].drop(columns=column)
                with self.subTest(dataset=dataset, missing=column):
                    self.assert_blocked(sources, dataset, "invalid_schema")
        for dataset, column in [("Athletes", "PersonName"), ("Athletes", "Country"),
                                ("Teams", "Event"), ("Teams", "TeamName"),
                                ("Coaches", "Name"), ("Medals", "TeamCountry"),
                                ("EntriesGender", "Discipline")]:
            sources = valid_sources()
            sources[dataset].loc[0, column] = None
            with self.subTest(dataset=dataset, column=column):
                errors = self.assert_blocked(sources, dataset, "invalid_identity")
                self.assertTrue(any(e.get("records") for e in errors))

    def test_invalid_medal_numbers_and_arithmetic(self):
        for value in (None, "1", 1.5, float("inf"), True):
            sources = valid_sources()
            sources["Medals"] = sources["Medals"].astype({"Gold": object})
            sources["Medals"].loc[0, "Gold"] = value
            with self.subTest(value=value):
                self.assert_blocked(sources, "Medals", "invalid_integer_count")
        sources = valid_sources()
        sources["Medals"].loc[0, "Gold"] = -1
        self.assert_blocked(sources, "Medals", "negative_count")
        sources = valid_sources()
        sources["Medals"].loc[0, "Total"] = 2
        errors = self.assert_blocked(sources, "Medals", "invalid_medal_totals")
        record = next(e for e in errors if e["code"] == "invalid_medal_totals")["records"][0]
        self.assertEqual(record["TeamCountry"], "A")

    def test_gender_errors_and_affected_records(self):
        for column, value, code in [("Female", -1, "negative_count"),
                                    ("Total", 123, "invalid_gender_totals"),
                                    ("Female", "2", "invalid_integer_count")]:
            sources = valid_sources()
            sources["EntriesGender"] = sources["EntriesGender"].astype({column: object})
            sources["EntriesGender"].loc[1, column] = value
            with self.subTest(code=code):
                errors = self.assert_blocked(sources, "EntriesGender", code)
                finding = next(e for e in errors if e["code"] == code)
                self.assertEqual(finding["records"][0]["Discipline"], "Athletics")
        sources = valid_sources()
        sources["EntriesGender"] = pd.concat([sources["EntriesGender"], sources["EntriesGender"].iloc[[0]]])
        self.assert_blocked(sources, "EntriesGender", "duplicate_discipline")

    def test_duplicate_keys_and_unexpected_coach_duplicates(self):
        sources = valid_sources()
        sources["Medals"] = pd.concat([sources["Medals"], sources["Medals"]], ignore_index=True)
        self.assert_blocked(sources, "Medals", "duplicate_country_key")
        sources = valid_sources()
        sources["Medals"] = pd.concat([sources["Medals"],
                                       sources["Medals"].assign(TeamCountry=" A ")], ignore_index=True)
        self.assert_blocked(sources, "Medals", "duplicate_country_key")
        sources = valid_sources()
        sources["Coaches"] = pd.concat([sources["Coaches"], sources["Coaches"]], ignore_index=True)
        self.assert_blocked(sources, "Coaches", "unexpected_exact_duplicates")
        sources = valid_sources()
        sources["Teams"] = pd.concat([sources["Teams"].assign(extra=1),
                                       sources["Teams"].assign(extra=2)], ignore_index=True)
        self.assert_blocked(sources, "Teams", "conflicting_duplicate_key")

    def test_known_corrections_and_exact_dedup_are_reused(self):
        sources = valid_sources()
        sources["Athletes"].loc[0, "Country"] = " Côte d'Ivoire "
        sources["Teams"].loc[0, ["Country", "TeamName", "Event"]] = [
            "C�te d'Ivoire", "C�te d�Ivoire", "Men's �p�e Team"]
        sources["Medals"].loc[0, "TeamCountry"] = "Côte d'Ivoire"
        sources["Coaches"].loc[0, "Country"] = "Côte d'Ivoire"
        sources["Athletes"] = pd.concat([sources["Athletes"], sources["Athletes"].iloc[[0]]], ignore_index=True)
        prepared, report = self.enforce(sources)
        self.assertEqual(prepared["Teams"].iloc[0].Event, "Men's Épée Team")
        self.assertEqual(prepared["Teams"].iloc[0].TeamName, "Côte d'Ivoire")
        self.assertEqual(len(prepared["Athletes"]), 3)
        self.assertIn("exact_duplicates_removed", [w["code"] for w in report["warnings"]])

    def test_unknown_replacement_characters_are_errors(self):
        for dataset, column in [("Athletes", "PersonName"), ("Teams", "Event"),
                                ("Coaches", "Name"), ("EntriesGender", "Discipline"),
                                ("Medals", "TeamCountry")]:
            sources = valid_sources()
            sources[dataset].loc[0, column] = "Unknown �"
            with self.subTest(dataset=dataset):
                self.assert_blocked(sources, dataset, "unresolved_replacement_character")

    def test_unmatched_and_contradictory_country_keys(self):
        for dataset, column in [("Medals", "TeamCountry"), ("Teams", "Country")]:
            sources = valid_sources()
            sources[dataset].loc[0, column] = "Unverified alias"
            self.assert_blocked(sources, dataset, "unmatched_country_key")
        sources = valid_sources()
        sources["Coaches"].loc[0, "Country"] = "a"
        self.assert_blocked(sources, "Country joins", "contradictory_country_keys")

    def test_both_builders_enforce_gate_before_aggregation_and_load_once(self):
        for module, builder in [("src.features.build_features", build_country_features),
                                ("src.features.build_analytics", build_country_analytics)]:
            sources = valid_sources()
            with self.subTest(builder=builder.__name__):
                with patch(module + ".load_csv", side_effect=lambda f: sources[f.removesuffix(".csv")]) as loader:
                    result = builder()
                self.assertEqual(loader.call_count, 5)
                self.assertEqual(set(result.country), {"A", "B"})
                self.assertTrue(result.attrs["data_quality_report"]["warnings"])
                sources["Medals"].loc[0, "Total"] = 999
                with patch(module + ".load_csv", side_effect=lambda f: sources[f.removesuffix(".csv")]):
                    with patch(module + ".aggregate_team_counts") as aggregate:
                        with self.assertRaises(DataQualityError):
                            builder()
                        aggregate.assert_not_called()

    def test_source_loading_failures_are_actionable(self):
        with self.assertRaises(DataQualityError) as context:
            load_validated_sources(loader=lambda f: (_ for _ in ()).throw(FileNotFoundError(f)))
        self.assertIn("Athletes.csv", str(context.exception))
        self.assertFalse(context.exception.report["valid"])

    def test_real_sources_pass_without_hardcoded_universal_counts(self):
        _, report = load_validated_sources()
        self.assertTrue(report["valid"])
        self.assertEqual(report["joins"]["participating_countries"], 206)
        self.assertEqual(report["joins"]["medal_countries"], 93)
        self.assertEqual(report["joins"]["medal_countries_without_participation"], [])
        self.assertEqual(report["joins"]["team_countries_without_athletes"], [])
        self.assertTrue({"known_exact_duplicate", "unspecified_event"}.issubset(
            {w["code"] for w in report["warnings"]}))


if __name__ == "__main__":
    unittest.main()
