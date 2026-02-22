"""P0: Schema validation tests.

Ensures rules.yaml validates against rules_schema.json,
all IDs unique, all rules have category.
"""

import json
import yaml
from pathlib import Path

import jsonschema

DATA_DIR = Path(__file__).parent.parent / "app" / "data"


class TestRulesSchemaValidation:
    def test_rules_validate_against_schema(self):
        """rules.yaml must validate against rules_schema.json."""
        with open(DATA_DIR / "rules.yaml") as f:
            rules = yaml.safe_load(f)
        with open(DATA_DIR / "rules_schema.json") as f:
            schema = json.load(f)

        jsonschema.validate(instance=rules, schema=schema)

    def test_all_rule_ids_unique(self):
        """All rule IDs must be unique."""
        with open(DATA_DIR / "rules.yaml") as f:
            rules = yaml.safe_load(f)

        ids = [r["id"] for r in rules]
        assert len(ids) == len(set(ids)), f"Duplicate IDs: {[x for x in ids if ids.count(x) > 1]}"

    def test_all_rules_have_category(self):
        """All rules must have an explicit category field."""
        with open(DATA_DIR / "rules.yaml") as f:
            rules = yaml.safe_load(f)

        for rule in rules:
            assert "category" in rule, f"Rule '{rule['id']}' missing category field"

    def test_valid_categories(self):
        """All category values must be from the allowed set."""
        valid = {"absolute", "windCoast", "weatherMode", "istanbul", "techniqueTime"}
        with open(DATA_DIR / "rules.yaml") as f:
            rules = yaml.safe_load(f)

        for rule in rules:
            cat = rule.get("category")
            assert cat in valid, f"Rule '{rule['id']}' has invalid category '{cat}'"

    def test_exact_rule_count(self):
        """Should have exactly 31 rules (v1.3)."""
        with open(DATA_DIR / "rules.yaml") as f:
            rules = yaml.safe_load(f)
        assert len(rules) == 31, f"Expected exactly 31 rules, got {len(rules)}"
