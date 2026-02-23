"""FishCast decision service — v1.3 hardened.

Decision Output v1.3: config-injected, additive seasonality, category caps,
sheltered exceptions, water mass proxy, isDaylight.
Contract version: 1.3.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional

from app.models.spot import SpotOut
from app.services.mode import derive_mode
from app.services.rules import (
    TIER1_SPECIES,
    build_rule_context,
    evaluate_rules,
)
from app.services.scoring import (
    calculate_species_score,
    compute_water_mass_proxy,
)
from app.services.solunar import compute_daylight
from app.services.weather import WeatherData
from app.utils.telemetry import log_decision_event
from app.utils.wind import normalize_cardinal_8

logger = logging.getLogger(__name__)

# Tür adları (Türkçe)
SPECIES_NAME_TR: dict[str, str] = {
    "istavrit": "İstavrit",
    "cinekop": "Çinekop",
    "sarikanat": "Sarıkanat",
    "palamut": "Palamut",
    "karagoz": "Karagöz",
    "lufer": "Lüfer",
    "levrek": "Levrek",
    "kolyoz": "Kolyoz",
    "mirmir": "Mırmır",
}

# Teknik adları (Türkçe)
TECHNIQUE_NAME_TR: dict[str, str] = {
    "capari": "Çapari",
    "kursun_arkasi": "Kurşun Arkası",
    "spin": "Spin",
    "lrf": "LRF",
    "surf": "Surf",
    "yemli_dip": "Yemli Dip",
    "shore_jig": "Shore Jig",
}

# Mode → avoid techniques mapping
MODE_AVOID_TECHNIQUES: dict[str, list[str]] = {
    "selective": ["spin", "shore_jig"],
    "holding": ["spin", "shore_jig", "capari"],
}


def compute_best_windows(
    solunar_data: dict[str, Any],
    weather: WeatherData,
) -> list[dict[str, Any]]:
    """bestWindows hesaplar: solunar + hava koşullarına göre 2-4 pencere."""
    windows: list[dict[str, Any]] = []

    for period in solunar_data.get("majorPeriods", []):
        reasons: list[str] = ["Major solunar periyodu"]
        score = 80

        if weather.pressure_change_3h_hpa < -1:
            reasons.append("Basınç düşüşü aktiviteyi artırır")
            score += 8

        if 5 <= weather.wind_speed_kmh <= 15:
            reasons.append("İdeal rüzgar koşulları")
            score += 5

        windows.append({
            "startLocal": period["start"],
            "endLocal": period["end"],
            "score0to100": min(100, score),
            "confidence0to1": round(min(1.0, 0.7 + weather.data_quality.value.count("l") * 0.2), 2),
            "reasonsTR": reasons,
        })

    for period in solunar_data.get("minorPeriods", []):
        windows.append({
            "startLocal": period["start"],
            "endLocal": period["end"],
            "score0to100": 65,
            "confidence0to1": 0.6,
            "reasonsTR": ["Minor solunar periyodu"],
        })

    windows.sort(key=lambda w: w["score0to100"], reverse=True)
    return windows[:4]


def compute_spot_scores(
    spot: SpotOut,
    weather: WeatherData,
    solunar_data: dict[str, Any],
    rules: list[dict[str, Any]],
    now: datetime,
    report_signals: Optional[dict[str, Any]] = None,
    scoring_config: Optional[dict[str, Any]] = None,
    seasonality_config: Optional[dict[str, Any]] = None,
    daylight_data: Optional[dict[str, Any]] = None,
    water_mass_proxy: Optional[dict[str, Any]] = None,
    trace_level: str = "none",
) -> dict[str, Any]:
    """Tek bir spot için tüm tür skorlarını hesaplar.

    v1.3: Accepts scoring_config, seasonality_config, daylight_data, water_mass_proxy.
    v1.3.1: trace_level param for debugging.
    """
    # Build context with v1.3 fields
    context = build_rule_context(
        weather, spot, solunar_data, now,
        daylight_data=daylight_data,
        water_mass_proxy=water_mass_proxy,
    )
    rule_result = evaluate_rules(
        rules, context, TIER1_SPECIES,
        scoring_config=scoring_config,
    )

    shore_str = spot.shore.value if hasattr(spot.shore, 'value') else spot.shore
    has_reports = report_signals is not None and report_signals.get("totalReports", 0) > 0
    coord_accuracy = spot.accuracy.value if hasattr(spot.accuracy, 'value') else spot.accuracy

    # Pressure config for mode derivation
    pressure_config = None
    if scoring_config and "pressureThresholds" in scoring_config:
        pressure_config = scoring_config["pressureThresholds"]

    species_scores: dict[str, dict[str, Any]] = {}
    score_sum = 0
    score_count = 0

    for sp_id in TIER1_SPECIES:
        bonus = rule_result.species_bonuses.get(sp_id, 0)

        score_data = calculate_species_score(
            species_id=sp_id,
            weather=weather,
            solunar_data=solunar_data,
            shore=shore_str,
            rule_bonus=bonus,
            month=now.month,
            hour=now.hour,
            minute=now.minute,
            data_quality=weather.data_quality,
            has_reports_24h=has_reports,
            scoring_config=scoring_config,
            seasonality_config=seasonality_config,
            coord_accuracy=coord_accuracy,
            fired_rules_count=rule_result.fired_rules_count,
        )

        # Mode derivation
        mode = derive_mode(
            sp_id, weather, solunar_data, spot, report_signals,
            pressure_config=pressure_config,
        )

        # Override mode with rule modeHint (if any)
        if sp_id in rule_result.mode_hints:
            mode = rule_result.mode_hints[sp_id][1]

        # Techniques
        recommended_techniques: list[dict[str, Any]] = []
        avoid_techniques: list[dict[str, Any]] = []

        rule_hints = rule_result.technique_hints.get(sp_id, [])
        rule_removes = rule_result.remove_techniques.get(sp_id, [])
        mode_avoids = MODE_AVOID_TECHNIQUES.get(mode, [])

        if rule_hints:
            for tech_id in rule_hints:
                if tech_id not in rule_removes and tech_id not in mode_avoids:
                    recommended_techniques.append({
                        "techniqueId": tech_id,
                        "techniqueNameTR": TECHNIQUE_NAME_TR.get(tech_id, tech_id),
                        "setupHintTR": None,
                    })

        all_avoids = set(mode_avoids) | set(rule_removes)
        for tech_id in all_avoids:
            reason = "Mod pasif — bu teknik etkisiz" if mode == "holding" else \
                     "Tür seçici — yapay yem yerine doğal yem tercih et" if mode == "selective" else \
                     "Kural gereği kaçınılmalı"
            avoid_techniques.append({
                "techniqueId": tech_id,
                "techniqueNameTR": TECHNIQUE_NAME_TR.get(tech_id, tech_id),
                "reasonTR": reason,
            })

        species_scores[sp_id] = {
            "score": score_data["score"],
            "suppressedByNoGo": rule_result.is_no_go,
            "bestTime": score_data.get("bestTime"),
            "confidence0to1": score_data["confidence"],
            "seasonStatus": score_data["seasonStatus"],
            "mode": mode,
            "recommendedTechniques": recommended_techniques[:3],
            "avoidTechniques": avoid_techniques,
            "breakdown": score_data.get("breakdown"),
        }

        if score_data["seasonStatus"] != "off":
            score_sum += score_data["score"]
            score_count += 1

    overall_score = round(score_sum / max(1, score_count))
    if rule_result.is_no_go:
        overall_score = 0

    # Build trace based on trace_level
    trace: Optional[dict[str, Any]] = None
    dq_val = weather.data_quality.value if hasattr(weather.data_quality, 'value') else weather.data_quality
    if trace_level == "minimal":
        trace = {
            "firedRulesCount": rule_result.fired_rules_count,
            "activeRuleIds": [r["ruleId"] for r in rule_result.active_rules],
            "dataQuality": dq_val,
        }
    elif trace_level == "full":
        trace = {
            "firedRulesCount": rule_result.fired_rules_count,
            "activeRuleIds": [r["ruleId"] for r in rule_result.active_rules],
            "dataQuality": dq_val,
            "categoryRawBonuses": rule_result.category_raw_bonuses,
            "categoryCappedBonuses": rule_result.category_capped_bonuses,
            "positiveTotalRaw": rule_result.positive_total_raw,
            "positiveTotalCapped": rule_result.positive_total_capped,
            "negativeTotal": rule_result.negative_total,
            "finalRuleBonus": rule_result.final_rule_bonus,
        }

    result_dict: dict[str, Any] = {
        "speciesScores": species_scores,
        "overallScore": overall_score,
        "noGo": {
            "isNoGo": rule_result.is_no_go,
            "reasonsTR": rule_result.no_go_reasons_tr,
        },
        "activeRules": rule_result.active_rules,
    }
    if trace is not None:
        result_dict["trace"] = trace

    return result_dict


def _compute_sheltered_exceptions(
    spots: list[SpotOut],
    wind_cardinal: str,
    scoring_config: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    """Compute sheltered exceptions for spots during noGo.

    If global noGo=true, check each spot's shelteredFrom. If wind cardinal
    (normalized) is in shelteredFrom → exception with LRF only + severe warning.
    """
    if scoring_config is None:
        return []

    sheltered_cfg = scoring_config.get("shelteredExceptions", {})
    allowed_techniques = sheltered_cfg.get("allowedTechniques", ["lrf"])
    warning_level = sheltered_cfg.get("warningLevel", "severe")

    norm = normalize_cardinal_8(wind_cardinal)
    exceptions: list[dict[str, Any]] = []

    for spot in spots:
        sheltered_from = getattr(spot, "sheltered_from", None) or []
        if norm in sheltered_from:
            exceptions.append({
                "spotId": spot.id,
                "spotNameTR": spot.name,
                "allowedTechniques": allowed_techniques,
                "warningLevel": warning_level,
                "messageTR": f"{spot.name} korunaklı — sadece {'/'.join(t.upper() for t in allowed_techniques)} ile dikkatli av.",
            })

    return exceptions


def _compute_health_block(weather: WeatherData) -> dict[str, Any]:
    """Compute data health block for decision response.

    Status: "good" | "degraded" | "bad" based on data quality and missing fields.
    v1.3.2: reasonsCode (machine codes) + reasonsTR (Turkish text) + reasons alias.
    """
    reasons_code: list[str] = []
    reasons_tr: list[str] = list(weather.data_issues)
    status = "good"
    dq = weather.data_quality.value if hasattr(weather.data_quality, 'value') else weather.data_quality

    if dq == "fallback":
        status = "bad"
        reasons_code.append("data_quality_fallback")
    elif dq == "cached":
        status = "degraded"
        reasons_code.append("data_quality_cached")

    for _ in weather.data_issues:
        reasons_code.append("provider_issue")

    if weather.sea_temp_c is None:
        status = "bad"
        reasons_code.append("missing_sea_temp")
        reasons_tr.append("Su sıcaklığı verisi yok")

    if weather.wave_height_m is None and status == "good":
        status = "degraded"
        reasons_code.append("missing_wave_height")
        reasons_tr.append("Dalga yüksekliği verisi yok")

    cardinal = weather.wind_direction_cardinal if hasattr(weather, 'wind_direction_cardinal') else "N"
    trend = weather.pressure_trend.value if hasattr(weather.pressure_trend, 'value') else weather.pressure_trend

    normalized = {
        "windSpeedKmhRaw": round(weather.wind_speed_kmh, 1),
        "windCardinalDerived": cardinal,
        "pressureTrendDerived": trend,
    }

    return {
        "status": status,
        "reasonsCode": reasons_code,
        "reasonsTR": reasons_tr,
        "reasons": reasons_tr,
        "normalized": normalized,
    }


def generate_decision(
    spots: list[SpotOut],
    weather: WeatherData,
    solunar_data: dict[str, Any],
    rules: list[dict[str, Any]],
    now: Optional[datetime] = None,
    report_signals_map: Optional[dict[str, dict[str, Any]]] = None,
    scoring_config: Optional[dict[str, Any]] = None,
    seasonality_config: Optional[dict[str, Any]] = None,
    trace_level: str = "none",
) -> dict[str, Any]:
    """Decision Output v1.3.2.

    v1.3: Config-injected, sheltered exceptions, water mass proxy, daylight.
    v1.3.1: Health block, trace support, SeasonStatus "off".
    v1.3.2: reasonsCode, trace guard, telemetry.
    """
    t0 = time.monotonic()

    if now is None:
        now = datetime.now()

    if report_signals_map is None:
        report_signals_map = {}

    # Compute once per decision
    daylight_data = compute_daylight(now)
    water_mass_proxy = compute_water_mass_proxy(
        weather.wind_direction_cardinal,
        weather.wind_speed_kmh,
        scoring_config,
    )

    # Compute scores for all spots
    spot_results: dict[str, dict[str, Any]] = {}
    for spot in spots:
        signals = report_signals_map.get(spot.id)
        spot_results[spot.id] = compute_spot_scores(
            spot, weather, solunar_data, rules, now, signals,
            scoring_config=scoring_config,
            seasonality_config=seasonality_config,
            daylight_data=daylight_data,
            water_mass_proxy=water_mass_proxy,
            trace_level=trace_level,
        )

    # Best windows
    best_windows = compute_best_windows(solunar_data, weather)

    # Global noGo (from any spot)
    global_no_go = any(r["noGo"]["isNoGo"] for r in spot_results.values())
    global_no_go_reasons: list[str] = []
    if global_no_go:
        for r in spot_results.values():
            for reason in r["noGo"]["reasonsTR"]:
                if reason not in global_no_go_reasons:
                    global_no_go_reasons.append(reason)

    # Sheltered exceptions (only computed when noGo is active)
    sheltered_exceptions: list[dict[str, Any]] = []
    if global_no_go:
        sheltered_exceptions = _compute_sheltered_exceptions(
            spots, weather.wind_direction_cardinal, scoring_config
        )

    # Region decisions
    regions_output: list[dict[str, Any]] = []
    region_ids = ["avrupa", "anadolu", "city_belt"]

    for region_id in region_ids:
        region_spots = [s for s in spots if (s.region_id.value if hasattr(s.region_id, 'value') else s.region_id) == region_id]

        if not region_spots:
            continue

        best_spot = max(
            region_spots,
            key=lambda s: spot_results[s.id]["overallScore"] if not spot_results[s.id]["noGo"]["isNoGo"] else -1,
        )

        result = spot_results[best_spot.id]
        species_scores = result["speciesScores"]

        sorted_species = sorted(
            [
                (sp_id, data)
                for sp_id, data in species_scores.items()
                if data["seasonStatus"] != "off"
            ],
            key=lambda x: (-x[1]["score"], x[0]),
        )[:4]

        targets: list[dict[str, Any]] = []
        for sp_id, sp_data in sorted_species:
            best_window_idx: Optional[int] = None
            if best_windows:
                best_window_idx = 0

            targets.append({
                "speciesId": sp_id,
                "speciesNameTR": SPECIES_NAME_TR.get(sp_id, sp_id),
                "score0to100": sp_data["score"],
                "confidence0to1": sp_data["confidence0to1"],
                "mode": sp_data["mode"],
                "bestWindowIndex": best_window_idx,
            })

        recommended_techniques: list[dict[str, Any]] = []
        seen_techniques: set[str] = set()
        for _, sp_data in sorted_species:
            for tech in sp_data.get("recommendedTechniques", []):
                tid = tech["techniqueId"]
                if tid not in seen_techniques:
                    seen_techniques.add(tid)
                    recommended_techniques.append(tech)

        if not recommended_techniques:
            for tech_id in (best_spot.technique_bias or best_spot.primary_techniques)[:3]:
                tid = tech_id.value if hasattr(tech_id, 'value') else tech_id
                if tid not in seen_techniques:
                    seen_techniques.add(tid)
                    recommended_techniques.append({
                        "techniqueId": tid,
                        "techniqueNameTR": TECHNIQUE_NAME_TR.get(tid, tid),
                        "setupHintTR": None,
                    })

        avoid_techniques: list[dict[str, Any]] = []
        seen_avoid: set[str] = set()
        for _, sp_data in sorted_species:
            for tech in sp_data.get("avoidTechniques", []):
                tid = tech["techniqueId"]
                if tid not in seen_avoid:
                    seen_avoid.add(tid)
                    avoid_techniques.append(tech)

        why_tr: list[str] = []
        for rule_info in result["activeRules"][:2]:
            if rule_info["messageTR"] and rule_info["messageTR"] not in why_tr:
                why_tr.append(rule_info["messageTR"])
        if best_spot.pelagic_corridor:
            why_tr.append("Pelajik koridorda — göçmen türler geçişte")
        if weather.wind_speed_kmh <= 15:
            tr_name = weather.wind_direction_tr
            why_tr.append(f"{tr_name.capitalize()} hafif — uygun koşullar")
        why_tr = why_tr[:3]

        spot_signals = report_signals_map.get(best_spot.id)

        regions_output.append({
            "regionId": region_id,
            "recommendedSpot": {
                "spotId": best_spot.id,
                "nameTR": best_spot.name,
                "spotWindBandKmhMin": round(max(0, weather.wind_speed_kmh - 5)),
                "spotWindBandKmhMax": round(weather.wind_speed_kmh + 10),
                "whyTR": why_tr,
                "targets": targets,
                "recommendedTechniques": recommended_techniques[:3],
                "avoidTechniques": avoid_techniques,
                "reportSignals24h": spot_signals,
            },
        })

    # Day summary
    day_summary = {
        "windSpeedKmhMin": round(max(0, weather.wind_speed_kmh - 3)),
        "windSpeedKmhMax": round(weather.wind_speed_kmh + 5),
        "windDirDeg": weather.wind_dir_deg,
        "windDirectionTR": weather.wind_direction_tr,
        "pressureHpa": weather.pressure_hpa,
        "pressureChange3hHpa": weather.pressure_change_3h_hpa,
        "pressureTrend": weather.pressure_trend.value,
        "airTempCMin": round(weather.air_temp_c - 3),
        "airTempCMax": round(weather.air_temp_c + 3),
        "seaTempC": weather.sea_temp_c,
        "cloudCoverPct": weather.cloud_cover_pct,
        "waveHeightM": weather.wave_height_m,
        "dataQuality": weather.data_quality.value,
        "dataIssues": weather.data_issues,
    }

    # Health block (always present)
    health = _compute_health_block(weather)

    decision = {
        "meta": {
            "contractVersion": "1.4.2",
            "generatedAt": datetime.now(tz=timezone.utc).isoformat(),
            "timezone": "Europe/Istanbul",
        },
        "daySummary": day_summary,
        "bestWindows": best_windows,
        "regions": regions_output,
        "noGo": {
            "isNoGo": global_no_go,
            "reasonsTR": global_no_go_reasons,
            "shelteredExceptions": sheltered_exceptions,
        },
        "health": health,
    }

    # Telemetry (v1.3.2)
    latency_ms = round((time.monotonic() - t0) * 1000, 1)
    log_decision_event(decision, latency_ms)

    return decision
