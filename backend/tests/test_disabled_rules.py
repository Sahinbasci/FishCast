"""Tests for the disabled rule mechanism in the rule engine.

Rules with `enabled: false` must be skipped during evaluation.
Rules without an `enabled` field default to active (enabled: true).
"""

import pytest
from unittest.mock import MagicMock

from app.services.rules import evaluate_rules, load_and_validate_rules, TIER1_SPECIES


class TestDisabledRuleMechanism:
    """Disabled rules (enabled: false) are skipped by evaluate_rules."""

    @pytest.fixture
    def base_context(self, mock_weather, mock_spot, mock_solunar):
        """A minimal rule evaluation context."""
        return {
            "windSpeedKmh": 12.0,
            "windDirDeg": 45,
            "windDirectionCardinal": "NE",
            "pressureHpa": 1015.0,
            "pressureChange3hHpa": -0.5,
            "pressureTrend": "stable",
            "airTempC": 15.0,
            "seaTempC": 16.0,
            "cloudCoverPct": 40.0,
            "shore": "european",
            "regionId": "avrupa",
            "spot": "tarabya",
            "pelagicCorridor": False,
            "features": ["kayalik", "rihtim"],
            "hour": 17,
            "minute": 0,
            "month": 10,
            "moonIllumination": 65.0,
            "solunarRating": 0.6,
            "wind_history_48h": None,
            "after_rain": False,
            "hours_since_rain": None,
            "moon_illumination": "65.0",
            "current_speed": None,
            "isDaylight": True,
            "waterMassProxy": "neutral",
            "waterMassStrength": 0.0,
            "shelteredFrom": ["NE", "N"],
        }

    def test_disabled_rule_is_skipped(self, base_context):
        """A rule with enabled: false should not fire even if condition matches."""
        rules = [
            {
                "id": "test_enabled",
                "condition": {"windSpeedKmh": ">=10"},
                "effects": [{"applyToSpecies": ["*"], "scoreBonus": 5}],
                "messageTR": "Active rule",
                "priority": 5,
                "category": "techniqueTime",
            },
            {
                "id": "test_disabled",
                "enabled": False,
                "condition": {"windSpeedKmh": ">=10"},
                "effects": [{"applyToSpecies": ["*"], "scoreBonus": 10}],
                "messageTR": "Disabled rule",
                "priority": 5,
                "category": "techniqueTime",
            },
        ]

        result = evaluate_rules(rules, base_context, species_list=TIER1_SPECIES)

        # Only the enabled rule should fire
        assert result.fired_rules_count == 1
        fired_ids = [r["ruleId"] for r in result.active_rules]
        assert "test_enabled" in fired_ids
        assert "test_disabled" not in fired_ids

    def test_rule_without_enabled_field_defaults_to_active(self, base_context):
        """Rules without an explicit `enabled` field should default to True."""
        rules = [
            {
                "id": "no_enabled_field",
                "condition": {"windSpeedKmh": ">=10"},
                "effects": [{"applyToSpecies": ["*"], "scoreBonus": 3}],
                "messageTR": "No enabled field",
                "priority": 5,
                "category": "techniqueTime",
            },
        ]

        result = evaluate_rules(rules, base_context, species_list=TIER1_SPECIES)

        assert result.fired_rules_count == 1
        fired_ids = [r["ruleId"] for r in result.active_rules]
        assert "no_enabled_field" in fired_ids

    def test_disabled_rules_dont_affect_species_bonuses(self, base_context):
        """Disabled rules' scoreBonus must not accumulate in species_bonuses."""
        rules = [
            {
                "id": "active_bonus",
                "condition": {"windSpeedKmh": ">=10"},
                "effects": [{"applyToSpecies": ["istavrit"], "scoreBonus": 5}],
                "messageTR": "Active",
                "priority": 5,
                "category": "techniqueTime",
            },
            {
                "id": "disabled_bonus",
                "enabled": False,
                "condition": {"windSpeedKmh": ">=10"},
                "effects": [{"applyToSpecies": ["istavrit"], "scoreBonus": 20}],
                "messageTR": "Disabled",
                "priority": 5,
                "category": "techniqueTime",
            },
        ]

        result = evaluate_rules(rules, base_context, species_list=TIER1_SPECIES)

        # Only the active rule's +5 should appear (capped at category cap)
        assert result.species_bonuses.get("istavrit", 0) == 5

    def test_disabled_rules_dont_trigger_nogo(self, base_context):
        """A disabled noGo rule must not set is_no_go."""
        rules = [
            {
                "id": "disabled_nogo",
                "enabled": False,
                "condition": {"windSpeedKmh": ">=10"},
                "effects": [{"applyToSpecies": ["*"], "scoreBonus": 0, "noGo": True}],
                "messageTR": "Disabled noGo",
                "priority": 10,
                "category": "absolute",
            },
        ]

        result = evaluate_rules(rules, base_context, species_list=TIER1_SPECIES)

        assert result.is_no_go is False
        assert result.fired_rules_count == 0

    def test_real_rules_total_vs_active_count(self):
        """Production rules.yaml: total rules > active rules (some disabled)."""
        all_rules = load_and_validate_rules()
        active_rules = [r for r in all_rules if r.get("enabled", True)]
        disabled_rules = [r for r in all_rules if not r.get("enabled", True)]

        total = len(all_rules)
        active = len(active_rules)
        disabled = len(disabled_rules)

        # Invariant: total = active + disabled
        assert total == active + disabled

        # We know there are disabled rules in the production ruleset
        assert disabled >= 1, "Expected at least 1 disabled rule in rules.yaml"
        assert active >= 1, "Expected at least 1 active rule in rules.yaml"

        # The disabled rules should have specific known IDs
        disabled_ids = {r["id"] for r in disabled_rules}
        assert "post_poyraz_migration" in disabled_ids
        assert "after_rain_bonus" in disabled_ids
        assert "strong_current_warning" in disabled_ids

    def test_real_disabled_rules_not_in_evaluation(self, base_context):
        """Evaluate real rules.yaml and verify disabled rules don't fire."""
        all_rules = load_and_validate_rules()

        result = evaluate_rules(all_rules, base_context, species_list=TIER1_SPECIES)

        fired_ids = {r["ruleId"] for r in result.active_rules}
        # None of the disabled rules should appear in fired rules
        assert "post_poyraz_migration" not in fired_ids
        assert "after_rain_bonus" not in fired_ids
        assert "strong_current_warning" not in fired_ids

    def test_enabled_true_explicitly_set(self, base_context):
        """A rule with enabled: true should fire normally."""
        rules = [
            {
                "id": "explicitly_enabled",
                "enabled": True,
                "condition": {"windSpeedKmh": ">=10"},
                "effects": [{"applyToSpecies": ["*"], "scoreBonus": 3}],
                "messageTR": "Explicitly enabled",
                "priority": 5,
                "category": "techniqueTime",
            },
        ]

        result = evaluate_rules(rules, base_context, species_list=TIER1_SPECIES)

        assert result.fired_rules_count == 1
        fired_ids = [r["ruleId"] for r in result.active_rules]
        assert "explicitly_enabled" in fired_ids

    def test_mix_of_enabled_disabled_and_default(self, base_context):
        """Mixed rules: some enabled, some disabled, some without field."""
        rules = [
            {
                "id": "rule_enabled_true",
                "enabled": True,
                "condition": {"windSpeedKmh": ">=10"},
                "effects": [{"applyToSpecies": ["*"], "scoreBonus": 2}],
                "messageTR": "Enabled",
                "priority": 5,
                "category": "techniqueTime",
            },
            {
                "id": "rule_disabled",
                "enabled": False,
                "condition": {"windSpeedKmh": ">=10"},
                "effects": [{"applyToSpecies": ["*"], "scoreBonus": 2}],
                "messageTR": "Disabled",
                "priority": 5,
                "category": "techniqueTime",
            },
            {
                "id": "rule_no_field",
                "condition": {"windSpeedKmh": ">=10"},
                "effects": [{"applyToSpecies": ["*"], "scoreBonus": 2}],
                "messageTR": "Default",
                "priority": 5,
                "category": "techniqueTime",
            },
        ]

        result = evaluate_rules(rules, base_context, species_list=TIER1_SPECIES)

        assert result.fired_rules_count == 2
        fired_ids = {r["ruleId"] for r in result.active_rules}
        assert "rule_enabled_true" in fired_ids
        assert "rule_no_field" in fired_ids
        assert "rule_disabled" not in fired_ids
