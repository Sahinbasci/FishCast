"""FishCast rule engine.

rules.yaml'ı yükler, startup'ta JSON Schema ile validate eder,
24 kuralı evaluate eder, conflict resolution uygular.

Operators: >=, <, range, time (midnight wrap), months, string, list OR,
           regionId, bool, pelagicCorridor, features_include, species_in_context.

Conflict Resolution (SCORING_ENGINE.md):
    1. All matching rules fire (no short-circuit)
    2. scoreBonus: summed per species, capped at +30
    3. techniqueHints: merged, deduped, priority-ordered
    4. removeFromTechniques: applied after merge
    5. modeHint: highest priority wins, same priority → alphabetical
    6. messageTR: concatenated " | ", priority DESC
    7. noGo: any true → NO-GO
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

# Tier 1 species for wildcard expansion
TIER1_SPECIES = ["istavrit", "cinekop", "sarikanat", "palamut", "karagoz"]
ALL_SPECIES = [
    "istavrit", "cinekop", "sarikanat", "palamut", "karagoz",
    "lufer", "levrek", "kolyoz", "mirmir",
]


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
    """>=, <, <=, > operatörlerini evaluate eder.

    Args:
        actual: Gerçek değer.
        condition_val: ">=-35" gibi string.

    Returns:
        Koşul sağlanıyor mu.
    """
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
    """Zaman aralığı kontrolü (midnight wrapping destekli).

    Args:
        current_hour: Mevcut saat.
        current_minute: Mevcut dakika.
        time_range: "HH:MM-HH:MM" formatında.

    Returns:
        Zaman aralığında mı.
    """
    try:
        parts = time_range.split("-")
        start_parts = parts[0].strip().split(":")
        end_parts = parts[1].strip().split(":")
        start_min = int(start_parts[0]) * 60 + int(start_parts[1])
        end_min = int(end_parts[0]) * 60 + int(end_parts[1])
        current_min = current_hour * 60 + current_minute

        if start_min <= end_min:
            return start_min <= current_min <= end_min
        # Wraps midnight
        return current_min >= start_min or current_min <= end_min
    except (ValueError, IndexError):
        return False


def _eval_range(actual: Any, range_val: list) -> bool:
    """[min, max] aralık kontrolü.

    Args:
        actual: Gerçek değer.
        range_val: [min, max] listesi.

    Returns:
        Aralıkta mı.
    """
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

    Args:
        condition: Kural condition dict'i.
        context: Evaluation context (weather, spot, time, etc.).

    Returns:
        Tüm condition'lar sağlanıyor mu.
    """
    for field, expected in condition.items():
        actual = context.get(field)

        # --- Özel handler'lar ---

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
        if field in ("pelagicCorridor", "after_rain"):
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
) -> dict[str, Any]:
    """Rule evaluation için context dict oluşturur.

    Args:
        weather: WeatherData objesi.
        spot: SpotOut objesi.
        solunar_data: Solunar verisi.
        now: Mevcut zaman. None ise datetime.now().

    Returns:
        Evaluation context dict'i.
    """
    if now is None:
        now = datetime.now()

    return {
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


# --- Rule Evaluation Result ---

class RuleResult:
    """Tek bir spot için tüm kuralların evaluation sonucu."""

    def __init__(self) -> None:
        self.is_no_go: bool = False
        self.no_go_reasons_tr: list[str] = []
        self.species_bonuses: dict[str, int] = {}  # species_id → sum of bonuses
        self.technique_hints: dict[str, list[str]] = {}  # species_id → techniques
        self.remove_techniques: dict[str, list[str]] = {}  # species_id → techniques to remove
        self.mode_hints: dict[str, tuple[int, str]] = {}  # species_id → (priority, mode)
        self.messages_tr: list[tuple[int, str]] = []  # (priority, message) for sorting
        self.active_rules: list[dict[str, Any]] = []


def evaluate_rules(
    rules: list[dict[str, Any]],
    context: dict[str, Any],
    species_list: Optional[list[str]] = None,
) -> RuleResult:
    """Tüm kuralları evaluate eder ve conflict resolution uygular.

    Args:
        rules: Validated rules listesi.
        context: Evaluation context.
        species_list: Hedef türler. None ise TIER1_SPECIES.

    Returns:
        RuleResult: Tüm sonuçlar birleştirilmiş.
    """
    if species_list is None:
        species_list = TIER1_SPECIES

    result = RuleResult()

    # Sort by priority DESC for conflict resolution
    sorted_rules = sorted(rules, key=lambda r: r.get("priority", 1), reverse=True)

    for rule in sorted_rules:
        condition = rule.get("condition", {})
        effects = rule.get("effects", [])
        priority = rule.get("priority", 1)
        message_tr = rule.get("messageTR", "")

        if not evaluate_condition(condition, context):
            continue

        # Rule matched
        rule_affected_species: list[str] = []

        for effect in effects:
            apply_to = effect.get("applyToSpecies", ["*"])
            score_bonus = effect.get("scoreBonus", 0)
            technique_hints = effect.get("techniqueHints", [])
            remove_techniques = effect.get("removeFromTechniques", [])
            mode_hint = effect.get("modeHint")
            no_go = effect.get("noGo", False)

            # Resolve wildcard
            target_species = species_list if "*" in apply_to else [
                s for s in apply_to if s in species_list or s in ALL_SPECIES
            ]

            for sp in target_species:
                # scoreBonus: sum
                result.species_bonuses[sp] = result.species_bonuses.get(sp, 0) + score_bonus

                # techniqueHints: merge dedup
                if technique_hints:
                    existing = result.technique_hints.get(sp, [])
                    for th in technique_hints:
                        if th not in existing:
                            existing.append(th)
                    result.technique_hints[sp] = existing

                # removeFromTechniques: merge dedup
                if remove_techniques:
                    existing_rm = result.remove_techniques.get(sp, [])
                    for rt in remove_techniques:
                        if rt not in existing_rm:
                            existing_rm.append(rt)
                    result.remove_techniques[sp] = existing_rm

                # modeHint: highest priority wins
                if mode_hint:
                    current = result.mode_hints.get(sp)
                    if current is None or priority > current[0] or (
                        priority == current[0] and mode_hint < current[1]
                    ):
                        result.mode_hints[sp] = (priority, mode_hint)

                rule_affected_species.append(sp)

            # noGo: any true → NO-GO
            if no_go:
                result.is_no_go = True
                if message_tr not in result.no_go_reasons_tr:
                    result.no_go_reasons_tr.append(message_tr)

        # Record message
        if message_tr:
            result.messages_tr.append((priority, message_tr))

        # Record active rule
        result.active_rules.append({
            "ruleId": rule["id"],
            "appliedBonus": sum(
                e.get("scoreBonus", 0) for e in effects
            ),
            "affectedSpecies": list(set(rule_affected_species)),
            "messageTR": message_tr,
        })

    # Apply bonus cap: per-species max +30 (negatives uncapped)
    for sp in result.species_bonuses:
        bonus = result.species_bonuses[sp]
        if bonus > 30:
            result.species_bonuses[sp] = 30

    # Apply removeFromTechniques AFTER merge
    for sp in result.technique_hints:
        remove_list = result.remove_techniques.get(sp, [])
        result.technique_hints[sp] = [
            t for t in result.technique_hints[sp] if t not in remove_list
        ]

    return result


def get_combined_messages(result: RuleResult) -> str:
    """Rule messageTR'leri birleştirir (priority DESC, " | " separator).

    Args:
        result: RuleResult.

    Returns:
        Birleştirilmiş mesaj string'i.
    """
    sorted_msgs = sorted(result.messages_tr, key=lambda x: x[0], reverse=True)
    unique_msgs: list[str] = []
    for _, msg in sorted_msgs:
        if msg not in unique_msgs:
            unique_msgs.append(msg)
    return " | ".join(unique_msgs)
