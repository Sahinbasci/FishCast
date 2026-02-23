"""FishCast rule engine — v1.3 hardened.

rules.yaml'ı yükler, startup'ta JSON Schema ile validate eder,
kuralları evaluate eder, category-based caps ile conflict resolution uygular.

v1.3 additions:
- Explicit category field per rule (absolute, windCoast, weatherMode, istanbul, techniqueTime)
- Per-category bonus caps from scoring_config["ruleBonusCaps"]
- Category cap trace in RuleResult
- isDaylight, waterMassProxy, shelteredFrom in context
- mirmir promoted to Tier 1
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml
import jsonschema

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"

# Tier 1 species for wildcard expansion (v1.3: mirmir promoted)
TIER1_SPECIES = [
    "istavrit", "cinekop", "sarikanat", "palamut", "karagoz", "mirmir",
]
ALL_SPECIES = [
    "istavrit", "cinekop", "sarikanat", "palamut", "karagoz",
    "lufer", "levrek", "kolyoz", "mirmir",
]

# Category inference from priority (fallback when rule has no explicit category)
_PRIORITY_TO_CATEGORY: dict[int, str] = {
    10: "absolute",
    9: "windCoast",
    8: "weatherMode",
    7: "weatherMode",
    6: "istanbul",
    5: "techniqueTime",
    4: "techniqueTime",
}


def _infer_category(priority: int) -> str:
    """Infer rule category from priority (backward compat)."""
    return _PRIORITY_TO_CATEGORY.get(priority, "techniqueTime")


def load_and_validate_rules() -> list[dict[str, Any]]:
    """rules.yaml'ı yükler ve JSON Schema ile validate eder.

    Returns:
        Validated rules listesi.

    Raises:
        SystemExit: Validation hatası → app crash.
    """
    rules_path = DATA_DIR / "rules.yaml"
    schema_path = DATA_DIR / "rules_schema.json"

    try:
        with open(rules_path, encoding="utf-8") as f:
            rules = yaml.safe_load(f)
    except Exception as e:
        logger.critical("rules.yaml yüklenemedi: %s", e)
        raise SystemExit(f"FATAL: rules.yaml yüklenemedi: {e}") from e

    try:
        with open(schema_path, encoding="utf-8") as f:
            schema = json.load(f)
    except Exception as e:
        logger.critical("rules_schema.json yüklenemedi: %s", e)
        raise SystemExit(f"FATAL: rules_schema.json yüklenemedi: {e}") from e

    try:
        jsonschema.validate(instance=rules, schema=schema)
    except jsonschema.ValidationError as e:
        logger.critical("rules.yaml validation hatası: %s", e.message)
        raise SystemExit(f"FATAL: rules.yaml geçersiz — {e.message}") from e

    # Unique ID check
    ids = [r["id"] for r in rules]
    if len(ids) != len(set(ids)):
        dupes = [x for x in ids if ids.count(x) > 1]
        raise SystemExit(f"FATAL: rules.yaml'da tekrarlanan ID: {set(dupes)}")

    logger.info("rules.yaml validated: %d kural yüklendi", len(rules))
    return rules


# --- Condition Evaluation ---

def _eval_comparison(actual: Any, condition_val: str) -> bool:
    """>=, <, <=, > operatörlerini evaluate eder."""
    if actual is None:
        return False

    try:
        if condition_val.startswith(">="):
            return float(actual) >= float(condition_val[2:])
        elif condition_val.startswith("<="):
            return float(actual) <= float(condition_val[2:])
        elif condition_val.startswith(">"):
            return float(actual) > float(condition_val[1:])
        elif condition_val.startswith("<"):
            return float(actual) < float(condition_val[1:])
    except (ValueError, TypeError):
        return False
    return False


def _eval_time(current_hour: int, current_minute: int, time_range: str) -> bool:
    """Zaman aralığı kontrolü (midnight wrapping destekli)."""
    try:
        parts = time_range.split("-")
        start_parts = parts[0].strip().split(":")
        end_parts = parts[1].strip().split(":")
        start_min = int(start_parts[0]) * 60 + int(start_parts[1])
        end_min = int(end_parts[0]) * 60 + int(end_parts[1])
        current_min = current_hour * 60 + current_minute

        if start_min <= end_min:
            return start_min <= current_min <= end_min
        return current_min >= start_min or current_min <= end_min
    except (ValueError, IndexError):
        return False


def _eval_range(actual: Any, range_val: list) -> bool:
    """[min, max] aralık kontrolü."""
    if actual is None or len(range_val) != 2:
        return False
    try:
        return float(range_val[0]) <= float(actual) <= float(range_val[1])
    except (ValueError, TypeError):
        return False


def evaluate_condition(
    condition: dict[str, Any],
    context: dict[str, Any],
) -> bool:
    """Tek bir kural condition'ını evaluate eder.

    Tüm field'lar AND ile birleştirilir. Liste değerler OR ile.
    """
    for field, expected in condition.items():
        actual = context.get(field)

        # time: "HH:MM-HH:MM"
        if field == "time":
            hour = context.get("hour", 0)
            minute = context.get("minute", 0)
            if not _eval_time(hour, minute, expected):
                return False
            continue

        # month: [int]
        if field == "month":
            month = context.get("month", 0)
            if isinstance(expected, list):
                if month not in expected:
                    return False
            else:
                if month != expected:
                    return False
            continue

        # Range: field_range: [min, max]
        if field.endswith("_range"):
            base_field = field.replace("_range", "")
            actual_val = context.get(base_field)
            if not _eval_range(actual_val, expected):
                return False
            continue

        # features_include: string
        if field == "features_include":
            features = context.get("features", [])
            if expected not in features:
                return False
            continue

        # species_in_context: list — always true (applied per-species in effects)
        if field == "species_in_context":
            continue

        # Bool fields
        if field in ("pelagicCorridor", "after_rain", "isDaylight"):
            if actual is None:
                return False
            if bool(actual) != bool(expected):
                return False
            continue

        # Comparison operators (string starting with >=, <, etc.)
        if isinstance(expected, str) and expected and expected[0] in ">=<":
            if not _eval_comparison(actual, expected):
                return False
            continue

        # List OR (e.g., windDirectionCardinal: ["NE", "N"])
        if isinstance(expected, list) and not field.endswith("_range"):
            if actual not in expected:
                return False
            continue

        # Exact string/value match
        if actual != expected:
            return False

    return True


def build_rule_context(
    weather: Any,
    spot: Any,
    solunar_data: dict[str, Any],
    now: Optional[datetime] = None,
    daylight_data: Optional[dict[str, Any]] = None,
    water_mass_proxy: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Rule evaluation için context dict oluşturur.

    v1.3: isDaylight, waterMassProxy, shelteredFrom added.
    """
    if now is None:
        now = datetime.now()

    ctx = {
        "windSpeedKmh": weather.wind_speed_kmh,
        "windDirDeg": weather.wind_dir_deg,
        "windDirectionCardinal": weather.wind_direction_cardinal,
        "pressureHpa": weather.pressure_hpa,
        "pressureChange3hHpa": weather.pressure_change_3h_hpa,
        "pressureTrend": weather.pressure_trend.value if hasattr(weather.pressure_trend, 'value') else weather.pressure_trend,
        "airTempC": weather.air_temp_c,
        "seaTempC": weather.sea_temp_c,
        "cloudCoverPct": weather.cloud_cover_pct,
        "shore": spot.shore.value if hasattr(spot.shore, 'value') else spot.shore,
        "regionId": spot.region_id.value if hasattr(spot.region_id, 'value') else spot.region_id,
        "spot": spot.id,
        "pelagicCorridor": spot.pelagic_corridor,
        "features": spot.features,
        "hour": now.hour,
        "minute": now.minute,
        "month": now.month,
        "moonIllumination": solunar_data.get("moonIllumination", 50),
        "solunarRating": solunar_data.get("solunarRating", 0.5),
        # Contextual fields (may not always be available)
        "wind_history_48h": None,
        "after_rain": False,
        "hours_since_rain": None,
        "moon_illumination": str(solunar_data.get("moonIllumination", 50)),
        "current_speed": None,
    }

    # v1.3 additions
    if daylight_data:
        ctx["isDaylight"] = daylight_data.get("isDaylight", True)
    else:
        ctx["isDaylight"] = True  # safe default

    if water_mass_proxy:
        ctx["waterMassProxy"] = water_mass_proxy.get("type", "neutral")
        ctx["waterMassStrength"] = water_mass_proxy.get("strength", 0.0)
    else:
        ctx["waterMassProxy"] = "neutral"
        ctx["waterMassStrength"] = 0.0

    # Spot sheltered directions (safe default: empty list)
    ctx["shelteredFrom"] = getattr(spot, "sheltered_from", None) or []

    return ctx


# --- Rule Evaluation Result ---

class RuleResult:
    """Tek bir spot için tüm kuralların evaluation sonucu."""

    def __init__(self) -> None:
        self.is_no_go: bool = False
        self.no_go_reasons_tr: list[str] = []
        self.species_bonuses: dict[str, int] = {}
        self.technique_hints: dict[str, list[str]] = {}
        self.remove_techniques: dict[str, list[str]] = {}
        self.mode_hints: dict[str, tuple[int, str]] = {}
        self.messages_tr: list[tuple[int, str]] = []
        self.active_rules: list[dict[str, Any]] = []
        self.fired_rules_count: int = 0
        # v1.3 category cap trace
        self.category_raw_bonuses: dict[str, dict[str, int]] = {}   # species → {cat → raw}
        self.category_capped_bonuses: dict[str, dict[str, int]] = {}  # species → {cat → capped}
        # v1.3.1 enhanced trace (positive-only totalCap)
        self.positive_total_raw: dict[str, int] = {}    # before totalCap
        self.positive_total_capped: dict[str, int] = {} # after totalCap
        self.negative_total: dict[str, int] = {}         # sum of all negatives
        self.final_rule_bonus: dict[str, int] = {}       # final = capped_pos + neg


def evaluate_rules(
    rules: list[dict[str, Any]],
    context: dict[str, Any],
    species_list: Optional[list[str]] = None,
    scoring_config: Optional[dict[str, Any]] = None,
) -> RuleResult:
    """Tüm kuralları evaluate eder ve category-based caps ile conflict resolution uygular.

    v1.3: Per-category caps from scoring_config["ruleBonusCaps"].
    """
    if species_list is None:
        species_list = TIER1_SPECIES

    result = RuleResult()

    # Track bonuses per species per category for capping
    # species → category → sum of raw bonuses
    cat_bonuses: dict[str, dict[str, int]] = {}

    sorted_rules = sorted(rules, key=lambda r: r.get("priority", 1), reverse=True)

    for rule in sorted_rules:
        # B1: Skip disabled rules (default: enabled=True)
        if not rule.get("enabled", True):
            continue

        condition = rule.get("condition", {})
        effects = rule.get("effects", [])
        priority = rule.get("priority", 1)
        message_tr = rule.get("messageTR", "")
        category = rule.get("category") or _infer_category(priority)

        if not evaluate_condition(condition, context):
            continue

        result.fired_rules_count += 1
        rule_affected_species: list[str] = []

        # B3: Apply waterMassStrength graded scaling for water mass rules
        # If a rule has waterMassProxy condition and waterMassStrength is in context,
        # scale the bonus proportionally (0.0-1.0) instead of binary full effect.
        rule_id = rule.get("id", "")
        is_water_mass_rule = "waterMassProxy" in condition
        wm_strength = context.get("waterMassStrength", 1.0) if is_water_mass_rule else 1.0

        for effect in effects:
            apply_to = effect.get("applyToSpecies", ["*"])
            raw_bonus = effect.get("scoreBonus", 0)
            # Scale bonus by water mass strength (graded, not binary)
            score_bonus = round(raw_bonus * wm_strength) if is_water_mass_rule else raw_bonus
            technique_hints = effect.get("techniqueHints", [])
            remove_techniques = effect.get("removeFromTechniques", [])
            mode_hint = effect.get("modeHint")
            no_go = effect.get("noGo", False)

            target_species = species_list if "*" in apply_to else [
                s for s in apply_to if s in species_list or s in ALL_SPECIES
            ]

            for sp in target_species:
                # Track by category
                if sp not in cat_bonuses:
                    cat_bonuses[sp] = {}
                cat_bonuses[sp][category] = cat_bonuses[sp].get(category, 0) + score_bonus

                # Sum into species_bonuses (raw, will be capped later)
                result.species_bonuses[sp] = result.species_bonuses.get(sp, 0) + score_bonus

                if technique_hints:
                    existing = result.technique_hints.get(sp, [])
                    for th in technique_hints:
                        if th not in existing:
                            existing.append(th)
                    result.technique_hints[sp] = existing

                if remove_techniques:
                    existing_rm = result.remove_techniques.get(sp, [])
                    for rt in remove_techniques:
                        if rt not in existing_rm:
                            existing_rm.append(rt)
                    result.remove_techniques[sp] = existing_rm

                if mode_hint:
                    current = result.mode_hints.get(sp)
                    if current is None or priority > current[0] or (
                        priority == current[0] and mode_hint < current[1]
                    ):
                        result.mode_hints[sp] = (priority, mode_hint)

                rule_affected_species.append(sp)

            if no_go:
                result.is_no_go = True
                if message_tr not in result.no_go_reasons_tr:
                    result.no_go_reasons_tr.append(message_tr)

        if message_tr:
            result.messages_tr.append((priority, message_tr))

        result.active_rules.append({
            "ruleId": rule["id"],
            "category": category,
            "appliedBonus": sum(e.get("scoreBonus", 0) for e in effects),
            "affectedSpecies": list(set(rule_affected_species)),
            "messageTR": message_tr,
        })

    # --- Category-based capping ---
    if scoring_config and "ruleBonusCaps" in scoring_config:
        caps = scoring_config["ruleBonusCaps"]
    else:
        caps = {"windCoastRules": 12, "istanbulSpecial": 10,
                "techniqueTime": 8, "weatherMode": 15, "totalCap": 25}

    # Map category names to cap config keys
    cat_cap_map = {
        "windCoast": caps.get("windCoastRules", 12),
        "istanbul": caps.get("istanbulSpecial", 10),
        "techniqueTime": caps.get("techniqueTime", 8),
        "weatherMode": caps.get("weatherMode", 15),
        "absolute": 999,  # no cap on absolute rules
    }
    total_cap = caps.get("totalCap", 25)

    for sp in list(result.species_bonuses.keys()):
        sp_cats = cat_bonuses.get(sp, {})
        result.category_raw_bonuses[sp] = dict(sp_cats)

        positive_total = 0
        negative_total = 0
        capped_cats: dict[str, int] = {}

        for cat, raw_bonus in sp_cats.items():
            cap_val = cat_cap_map.get(cat, total_cap)
            if raw_bonus > 0:
                capped = min(raw_bonus, cap_val)
                positive_total += capped
            else:
                capped = raw_bonus
                negative_total += capped
            capped_cats[cat] = capped

        result.category_capped_bonuses[sp] = capped_cats

        # v1.3.1: totalCap applies only to positives; negatives added after
        capped_positive = min(positive_total, total_cap)
        final_bonus = capped_positive + negative_total

        result.positive_total_raw[sp] = positive_total
        result.positive_total_capped[sp] = capped_positive
        result.negative_total[sp] = negative_total
        result.final_rule_bonus[sp] = final_bonus
        result.species_bonuses[sp] = final_bonus

    # Apply removeFromTechniques AFTER merge
    for sp in result.technique_hints:
        remove_list = result.remove_techniques.get(sp, [])
        result.technique_hints[sp] = [
            t for t in result.technique_hints[sp] if t not in remove_list
        ]

    return result


def get_combined_messages(result: RuleResult) -> str:
    """Rule messageTR'leri birleştirir (priority DESC, " | " separator)."""
    sorted_msgs = sorted(result.messages_tr, key=lambda x: x[0], reverse=True)
    unique_msgs: list[str] = []
    for _, msg in sorted_msgs:
        if msg not in unique_msgs:
            unique_msgs.append(msg)
    return " | ".join(unique_msgs)
