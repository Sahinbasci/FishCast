"""FishCast decision service.

Decision Output v1 üretir: her region için en iyi mera, bestWindows,
targets, teknikler, avoidTechniques, whyTR, noGo.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from app.models.enums import DataQuality, SpeciesId
from app.models.spot import SpotOut
from app.services.mode import derive_mode
from app.services.rules import (
    TIER1_SPECIES,
    RuleResult,
    build_rule_context,
    evaluate_rules,
)
from app.services.scoring import (
    calculate_species_score,
    season_multiplier,
)
from app.services.weather import WeatherData

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
    """bestWindows hesaplar: solunar + hava koşullarına göre 2-4 pencere.

    Args:
        solunar_data: Solunar verisi.
        weather: WeatherData objesi.

    Returns:
        BestWindow listesi (2-4 eleman).
    """
    windows: list[dict[str, Any]] = []

    # Major periods → high score windows
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

    # Minor periods → medium score windows
    for period in solunar_data.get("minorPeriods", []):
        reasons_minor: list[str] = ["Minor solunar periyodu"]
        score_minor = 65

        windows.append({
            "startLocal": period["start"],
            "endLocal": period["end"],
            "score0to100": min(100, score_minor),
            "confidence0to1": 0.6,
            "reasonsTR": reasons_minor,
        })

    # Sort by score DESC, limit to 4
    windows.sort(key=lambda w: w["score0to100"], reverse=True)
    return windows[:4]


def compute_spot_scores(
    spot: SpotOut,
    weather: WeatherData,
    solunar_data: dict[str, Any],
    rules: list[dict[str, Any]],
    now: datetime,
    report_signals: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Tek bir spot için tüm tür skorlarını hesaplar.

    Args:
        spot: Mera objesi.
        weather: WeatherData.
        solunar_data: Solunar verisi.
        rules: Validated rules listesi.
        now: Mevcut zaman.
        report_signals: Son 24h rapor sinyalleri.

    Returns:
        {speciesScores: {species_id: score_data}, overallScore, noGo, activeRules}
    """
    # Build context and evaluate rules
    context = build_rule_context(weather, spot, solunar_data, now)
    rule_result = evaluate_rules(rules, context, TIER1_SPECIES)

    shore_str = spot.shore.value if hasattr(spot.shore, 'value') else spot.shore
    has_reports = report_signals is not None and report_signals.get("totalReports", 0) > 0

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
        )

        # Mode derivation
        mode = derive_mode(sp_id, weather, solunar_data, spot, report_signals)

        # Override mode with rule modeHint (if any)
        if sp_id in rule_result.mode_hints:
            mode = rule_result.mode_hints[sp_id][1]

        # Techniques
        recommended_techniques: list[dict[str, Any]] = []
        avoid_techniques: list[dict[str, Any]] = []

        # Get rule-based technique hints
        rule_hints = rule_result.technique_hints.get(sp_id, [])
        rule_removes = rule_result.remove_techniques.get(sp_id, [])

        # Mode-based avoidTechniques
        mode_avoids = MODE_AVOID_TECHNIQUES.get(mode, [])

        # Build recommended list
        if rule_hints:
            for tech_id in rule_hints:
                if tech_id not in rule_removes and tech_id not in mode_avoids:
                    recommended_techniques.append({
                        "techniqueId": tech_id,
                        "techniqueNameTR": TECHNIQUE_NAME_TR.get(tech_id, tech_id),
                        "setupHintTR": None,
                    })

        # Build avoid list from mode + rules
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

        if score_data["seasonStatus"] != "closed":
            score_sum += score_data["score"]
            score_count += 1

    overall_score = round(score_sum / max(1, score_count))
    if rule_result.is_no_go:
        overall_score = 0

    return {
        "speciesScores": species_scores,
        "overallScore": overall_score,
        "noGo": {
            "isNoGo": rule_result.is_no_go,
            "reasonsTR": rule_result.no_go_reasons_tr,
        },
        "activeRules": rule_result.active_rules,
    }


def generate_decision(
    spots: list[SpotOut],
    weather: WeatherData,
    solunar_data: dict[str, Any],
    rules: list[dict[str, Any]],
    now: Optional[datetime] = None,
    report_signals_map: Optional[dict[str, dict[str, Any]]] = None,
) -> dict[str, Any]:
    """Decision Output v1 üretir.

    Args:
        spots: 16 mera listesi.
        weather: WeatherData.
        solunar_data: Solunar verisi.
        rules: Validated rules listesi.
        now: Mevcut zaman.
        report_signals_map: {spotId: reportSignals} dict.

    Returns:
        DecisionResponse dict (API_CONTRACTS.md § GET /decision/today).
    """
    if now is None:
        now = datetime.now()

    if report_signals_map is None:
        report_signals_map = {}

    # Compute scores for all spots
    spot_results: dict[str, dict[str, Any]] = {}
    for spot in spots:
        signals = report_signals_map.get(spot.id)
        spot_results[spot.id] = compute_spot_scores(
            spot, weather, solunar_data, rules, now, signals
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

    # Region decisions
    regions_output: list[dict[str, Any]] = []
    region_ids = ["avrupa", "anadolu", "city_belt"]
    spot_by_id = {s.id: s for s in spots}

    for region_id in region_ids:
        region_spots = [s for s in spots if (s.region_id.value if hasattr(s.region_id, 'value') else s.region_id) == region_id]

        if not region_spots:
            continue

        # Select best spot (highest overall, not noGo)
        best_spot = max(
            region_spots,
            key=lambda s: spot_results[s.id]["overallScore"] if not spot_results[s.id]["noGo"]["isNoGo"] else -1,
        )

        result = spot_results[best_spot.id]
        species_scores = result["speciesScores"]

        # Top targets (score DESC, max 4)
        sorted_species = sorted(
            [
                (sp_id, data)
                for sp_id, data in species_scores.items()
                if data["seasonStatus"] != "closed"
            ],
            key=lambda x: (-x[1]["score"], x[0]),
        )[:4]

        targets: list[dict[str, Any]] = []
        for sp_id, sp_data in sorted_species:
            # Find best window index
            best_window_idx: Optional[int] = None
            if best_windows:
                best_window_idx = 0  # default to highest scored window

            targets.append({
                "speciesId": sp_id,
                "speciesNameTR": SPECIES_NAME_TR.get(sp_id, sp_id),
                "score0to100": sp_data["score"],
                "confidence0to1": sp_data["confidence0to1"],
                "mode": sp_data["mode"],
                "bestWindowIndex": best_window_idx,
            })

        # Recommended techniques (from top species)
        recommended_techniques: list[dict[str, Any]] = []
        seen_techniques: set[str] = set()
        for _, sp_data in sorted_species:
            for tech in sp_data.get("recommendedTechniques", []):
                tid = tech["techniqueId"]
                if tid not in seen_techniques:
                    seen_techniques.add(tid)
                    recommended_techniques.append(tech)

        # If no rule-based techniques, use spot's primary techniques
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

        # Avoid techniques (union from all species)
        avoid_techniques: list[dict[str, Any]] = []
        seen_avoid: set[str] = set()
        for _, sp_data in sorted_species:
            for tech in sp_data.get("avoidTechniques", []):
                tid = tech["techniqueId"]
                if tid not in seen_avoid:
                    seen_avoid.add(tid)
                    avoid_techniques.append(tech)

        # whyTR: 2-3 Türkçe bullet
        why_tr: list[str] = []
        # Add active rule messages
        for rule_info in result["activeRules"][:2]:
            if rule_info["messageTR"] and rule_info["messageTR"] not in why_tr:
                why_tr.append(rule_info["messageTR"])
        # Add generic condition info
        if best_spot.pelagic_corridor:
            why_tr.append("Pelajik koridorda — göçmen türler geçişte")
        if weather.wind_speed_kmh <= 15:
            cardinal = weather.wind_direction_cardinal
            tr_name = weather.wind_direction_tr
            why_tr.append(f"{tr_name.capitalize()} hafif — uygun koşullar")
        why_tr = why_tr[:3]

        # Report signals
        spot_signals = report_signals_map.get(best_spot.id)

        regions_output.append({
            "regionId": region_id,
            "recommendedSpot": {
                "spotId": best_spot.id,
                "nameTR": best_spot.name,
                "spotWindBandKmhMin": max(0, weather.wind_speed_kmh - 5),
                "spotWindBandKmhMax": weather.wind_speed_kmh + 10,
                "whyTR": why_tr,
                "targets": targets,
                "recommendedTechniques": recommended_techniques[:3],
                "avoidTechniques": avoid_techniques,
                "reportSignals24h": spot_signals,
            },
        })

    # Day summary
    day_summary = {
        "windSpeedKmhMin": max(0, weather.wind_speed_kmh - 3),
        "windSpeedKmhMax": weather.wind_speed_kmh + 5,
        "windDirDeg": weather.wind_dir_deg,
        "windDirectionTR": weather.wind_direction_tr,
        "pressureHpa": weather.pressure_hpa,
        "pressureChange3hHpa": weather.pressure_change_3h_hpa,
        "pressureTrend": weather.pressure_trend.value,
        "airTempCMin": weather.air_temp_c - 3,
        "airTempCMax": weather.air_temp_c + 3,
        "seaTempC": weather.sea_temp_c,
        "cloudCoverPct": weather.cloud_cover_pct,
        "waveHeightM": weather.wave_height_m,
        "dataQuality": weather.data_quality.value,
        "dataIssues": weather.data_issues,
    }

    return {
        "meta": {
            "contractVersion": "1.2",
            "generatedAt": datetime.now(tz=timezone.utc).isoformat(),
            "timezone": "Europe/Istanbul",
        },
        "daySummary": day_summary,
        "bestWindows": best_windows,
        "regions": regions_output,
        "noGo": {
            "isNoGo": global_no_go,
            "reasonsTR": global_no_go_reasons,
        },
    }
