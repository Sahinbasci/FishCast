"""P0: Rule category caps tests (G2).

Ensures per-category and total caps are enforced with trace data.
"""

from app.services.rules import evaluate_rules, build_rule_context, TIER1_SPECIES


class TestCategoryCaps:
    def test_total_cap_enforced(self, scoring_config, mock_weather, mock_spot, mock_solunar):
        """Stacking many positive rules should not exceed totalCap."""
        from datetime import datetime

        # Create fake rules that stack heavy bonuses in different categories
        fake_rules = [
            {
                "id": "test_wind_bonus",
                "condition": {"windSpeedKmh": ">=1"},
                "effects": [{"applyToSpecies": ["*"], "scoreBonus": 15}],
                "messageTR": "Test wind",
                "priority": 9,
                "category": "windCoast",
            },
            {
                "id": "test_weather_bonus",
                "condition": {"windSpeedKmh": ">=1"},
                "effects": [{"applyToSpecies": ["*"], "scoreBonus": 15}],
                "messageTR": "Test weather",
                "priority": 7,
                "category": "weatherMode",
            },
            {
                "id": "test_istanbul_bonus",
                "condition": {"windSpeedKmh": ">=1"},
                "effects": [{"applyToSpecies": ["*"], "scoreBonus": 12}],
                "messageTR": "Test istanbul",
                "priority": 6,
                "category": "istanbul",
            },
        ]

        now = datetime(2026, 10, 15, 10, 0)
        context = build_rule_context(mock_weather, mock_spot, mock_solunar, now)
        result = evaluate_rules(fake_rules, context, TIER1_SPECIES, scoring_config)

        total_cap = scoring_config["ruleBonusCaps"]["totalCap"]

        for sp in TIER1_SPECIES:
            bonus = result.species_bonuses.get(sp, 0)
            assert bonus <= total_cap, \
                f"{sp} bonus {bonus} exceeds totalCap {total_cap}"

    def test_per_category_cap_enforced(self, scoring_config, mock_weather, mock_spot, mock_solunar):
        """Per-category cap should limit bonuses within a single category."""
        from datetime import datetime

        # Stack multiple windCoast rules
        fake_rules = [
            {
                "id": f"test_wind_{i}",
                "condition": {"windSpeedKmh": ">=1"},
                "effects": [{"applyToSpecies": ["*"], "scoreBonus": 10}],
                "messageTR": f"Wind {i}",
                "priority": 9,
                "category": "windCoast",
            }
            for i in range(5)
        ]

        now = datetime(2026, 10, 15, 10, 0)
        context = build_rule_context(mock_weather, mock_spot, mock_solunar, now)
        result = evaluate_rules(fake_rules, context, TIER1_SPECIES, scoring_config)

        wind_cap = scoring_config["ruleBonusCaps"]["windCoastRules"]

        for sp in TIER1_SPECIES:
            cat_capped = result.category_capped_bonuses.get(sp, {}).get("windCoast", 0)
            assert cat_capped <= wind_cap, \
                f"{sp} windCoast capped bonus {cat_capped} exceeds cap {wind_cap}"

    def test_trace_data_present(self, scoring_config, mock_weather, mock_spot, mock_solunar):
        """RuleResult should have category cap trace fields."""
        from datetime import datetime

        fake_rules = [
            {
                "id": "test_trace",
                "condition": {"windSpeedKmh": ">=1"},
                "effects": [{"applyToSpecies": ["istavrit"], "scoreBonus": 5}],
                "messageTR": "Test",
                "priority": 9,
                "category": "windCoast",
            },
        ]

        now = datetime(2026, 10, 15, 10, 0)
        context = build_rule_context(mock_weather, mock_spot, mock_solunar, now)
        result = evaluate_rules(fake_rules, context, TIER1_SPECIES, scoring_config)

        assert hasattr(result, "category_raw_bonuses")
        assert hasattr(result, "category_capped_bonuses")
        assert "istavrit" in result.category_raw_bonuses
        assert "windCoast" in result.category_raw_bonuses["istavrit"]

    def test_negative_bonuses_uncapped(self, scoring_config, mock_weather, mock_spot, mock_solunar):
        """Negative bonuses should pass through without capping."""
        from datetime import datetime

        fake_rules = [
            {
                "id": "test_penalty",
                "condition": {"windSpeedKmh": ">=1"},
                "effects": [{"applyToSpecies": ["*"], "scoreBonus": -30}],
                "messageTR": "Penalty",
                "priority": 9,
                "category": "windCoast",
            },
        ]

        now = datetime(2026, 10, 15, 10, 0)
        context = build_rule_context(mock_weather, mock_spot, mock_solunar, now)
        result = evaluate_rules(fake_rules, context, TIER1_SPECIES, scoring_config)

        for sp in TIER1_SPECIES:
            assert result.species_bonuses.get(sp, 0) == -30, \
                f"{sp} negative bonus should not be capped"

    def test_active_rules_include_category(self, scoring_config, mock_weather, mock_spot, mock_solunar):
        """Active rules should include category field."""
        from datetime import datetime

        fake_rules = [
            {
                "id": "test_cat",
                "condition": {"windSpeedKmh": ">=1"},
                "effects": [{"applyToSpecies": ["*"], "scoreBonus": 3}],
                "messageTR": "Test",
                "priority": 7,
                "category": "weatherMode",
            },
        ]

        now = datetime(2026, 10, 15, 10, 0)
        context = build_rule_context(mock_weather, mock_spot, mock_solunar, now)
        result = evaluate_rules(fake_rules, context, TIER1_SPECIES, scoring_config)

        assert len(result.active_rules) == 1
        assert result.active_rules[0]["category"] == "weatherMode"

    def test_mixed_positive_negative_total_cap(self, scoring_config, mock_weather, mock_spot, mock_solunar):
        """v1.3.1: totalCap applies only to positives, negatives added after.

        windCoast(+12) + weatherMode(+15) + istanbul(-5)
        → positive capped: min(25, 12+15) = 25
        → final = 25 + (-5) = 20
        """
        from datetime import datetime

        fake_rules = [
            {
                "id": "test_wind_pos",
                "condition": {"windSpeedKmh": ">=1"},
                "effects": [{"applyToSpecies": ["istavrit"], "scoreBonus": 12}],
                "messageTR": "Wind +12",
                "priority": 9,
                "category": "windCoast",
            },
            {
                "id": "test_weather_pos",
                "condition": {"windSpeedKmh": ">=1"},
                "effects": [{"applyToSpecies": ["istavrit"], "scoreBonus": 15}],
                "messageTR": "Weather +15",
                "priority": 7,
                "category": "weatherMode",
            },
            {
                "id": "test_istanbul_neg",
                "condition": {"windSpeedKmh": ">=1"},
                "effects": [{"applyToSpecies": ["istavrit"], "scoreBonus": -5}],
                "messageTR": "Istanbul -5",
                "priority": 6,
                "category": "istanbul",
            },
        ]

        now = datetime(2026, 10, 15, 10, 0)
        context = build_rule_context(mock_weather, mock_spot, mock_solunar, now)
        result = evaluate_rules(fake_rules, context, TIER1_SPECIES, scoring_config)

        bonus = result.species_bonuses.get("istavrit", 0)
        assert bonus == 20, \
            f"Expected 20 (min(25, 12+15) + (-5)), got {bonus}"

    def test_trace_fields_enhanced(self, scoring_config, mock_weather, mock_spot, mock_solunar):
        """v1.3.1: New trace fields present on RuleResult."""
        from datetime import datetime

        fake_rules = [
            {
                "id": "test_pos",
                "condition": {"windSpeedKmh": ">=1"},
                "effects": [{"applyToSpecies": ["istavrit"], "scoreBonus": 10}],
                "messageTR": "Pos",
                "priority": 9,
                "category": "windCoast",
            },
            {
                "id": "test_neg",
                "condition": {"windSpeedKmh": ">=1"},
                "effects": [{"applyToSpecies": ["istavrit"], "scoreBonus": -3}],
                "messageTR": "Neg",
                "priority": 6,
                "category": "istanbul",
            },
        ]

        now = datetime(2026, 10, 15, 10, 0)
        context = build_rule_context(mock_weather, mock_spot, mock_solunar, now)
        result = evaluate_rules(fake_rules, context, TIER1_SPECIES, scoring_config)

        assert result.positive_total_raw.get("istavrit") == 10
        assert result.positive_total_capped.get("istavrit") == 10
        assert result.negative_total.get("istavrit") == -3
        assert result.final_rule_bonus.get("istavrit") == 7
