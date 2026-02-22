#!/usr/bin/env python3
"""FishCast v1.3.2 smoke test — offline decision generation.

Runs 4 canned weather scenarios through generate_decision() with real configs
but NO external API calls. Validates structure and prints summary.

Usage:
    cd backend && python3 scripts/smoke_decision.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml
from app.models.enums import DataQuality, PressureTrend
from app.models.spot import SpotOut
from app.services.decision import generate_decision
from app.services.rules import load_and_validate_rules

DATA_DIR = Path(__file__).resolve().parent.parent / "app" / "data"


class MockWeather:
    """Minimal WeatherData mock for smoke tests."""

    def __init__(
        self,
        wind_speed_kmh: float = 10.0,
        wind_dir_deg: int = 45,
        pressure_hpa: float = 1015.0,
        pressure_change_3h_hpa: float = -0.5,
        air_temp_c: float = 12.0,
        cloud_cover_pct: float = 40.0,
        sea_temp_c: Optional[float] = 14.0,
        wave_height_m: Optional[float] = 0.3,
        data_quality: str = "live",
        data_issues: Optional[list[str]] = None,
        wind_direction_cardinal: str = "NE",
        wind_direction_tr: str = "poyraz",
        pressure_trend: str = "stable",
    ):
        self.wind_speed_kmh = wind_speed_kmh
        self.wind_dir_deg = wind_dir_deg
        self.pressure_hpa = pressure_hpa
        self.pressure_change_3h_hpa = pressure_change_3h_hpa
        self.air_temp_c = air_temp_c
        self.cloud_cover_pct = cloud_cover_pct
        self.sea_temp_c = sea_temp_c
        self.wave_height_m = wave_height_m
        self.data_quality = DataQuality(data_quality)
        self.data_issues = data_issues or []
        self.wind_direction_cardinal = wind_direction_cardinal
        self.wind_direction_tr = wind_direction_tr
        self.pressure_trend = PressureTrend(pressure_trend)

    def to_dict(self) -> dict[str, Any]:
        return {"wind_speed_kmh": self.wind_speed_kmh, "sea_temp_c": self.sea_temp_c}


# ─── Scenarios ───────────────────────────────────────────────────────────────

SCENARIOS: list[dict[str, Any]] = [
    {
        "name": "Feb Palamut (off-season, parça potential)",
        "month": 2,
        "weather": MockWeather(
            wind_speed_kmh=8, wind_dir_deg=210, pressure_hpa=1018,
            pressure_change_3h_hpa=-1.5, air_temp_c=8, sea_temp_c=10.0,
            wave_height_m=0.4, wind_direction_cardinal="SW",
            wind_direction_tr="lodos", pressure_trend="falling",
        ),
    },
    {
        "name": "Jul LRF (summer calm, karagöz peak)",
        "month": 7,
        "weather": MockWeather(
            wind_speed_kmh=5, wind_dir_deg=180, pressure_hpa=1012,
            pressure_change_3h_hpa=0.2, air_temp_c=28, sea_temp_c=24.0,
            wave_height_m=0.1, wind_direction_cardinal="S",
            wind_direction_tr="kıble", pressure_trend="stable",
        ),
    },
    {
        "name": "Nov Poyraz (cinekop peak, strong NE)",
        "month": 11,
        "weather": MockWeather(
            wind_speed_kmh=25, wind_dir_deg=45, pressure_hpa=1020,
            pressure_change_3h_hpa=-2.0, air_temp_c=12, sea_temp_c=16.0,
            wave_height_m=1.2, wind_direction_cardinal="NE",
            wind_direction_tr="poyraz", pressure_trend="falling",
        ),
    },
    {
        "name": "Extreme Wind (noGo expected)",
        "month": 1,
        "weather": MockWeather(
            wind_speed_kmh=65, wind_dir_deg=0, pressure_hpa=1005,
            pressure_change_3h_hpa=-4.0, air_temp_c=5, sea_temp_c=9.0,
            wave_height_m=3.5, wind_direction_cardinal="N",
            wind_direction_tr="yıldız", pressure_trend="falling",
        ),
    },
]


def _mock_solunar() -> dict[str, Any]:
    """Minimal solunar data for smoke tests."""
    return {
        "majorPeriods": [{"start": "06:30", "end": "08:30"}],
        "minorPeriods": [{"start": "12:00", "end": "13:00"}],
        "moonPhase": "waxing_crescent",
        "moonIllumination": 0.25,
        "solunarRating": 0.6,
    }


def run_smoke() -> bool:
    """Run all 4 scenarios and print summary. Returns True if all pass."""
    # Load real configs
    raw_spots = json.loads((DATA_DIR / "spots.json").read_text(encoding="utf-8"))
    spots = [SpotOut.model_validate(s) for s in raw_spots]

    rules = load_and_validate_rules()

    with open(DATA_DIR / "scoring_config.yaml", encoding="utf-8") as f:
        scoring_config = yaml.safe_load(f)
    with open(DATA_DIR / "seasonality.yaml", encoding="utf-8") as f:
        seasonality_config = yaml.safe_load(f)

    solunar = _mock_solunar()
    all_ok = True

    print("=" * 70)
    print("FishCast v1.3.2 Smoke Test — 4 Scenarios")
    print("=" * 70)

    for i, scenario in enumerate(SCENARIOS, 1):
        name = scenario["name"]
        month = scenario["month"]
        weather = scenario["weather"]
        now = datetime(2026, month, 15, 10, 0, 0)

        try:
            decision = generate_decision(
                spots=spots,
                weather=weather,
                solunar_data=solunar,
                rules=rules,
                now=now,
                scoring_config=scoring_config,
                seasonality_config=seasonality_config,
                trace_level="minimal",
            )

            # Basic structure checks
            assert "meta" in decision, "Missing meta"
            assert "health" in decision, "Missing health"
            assert "noGo" in decision, "Missing noGo"
            assert "regions" in decision, "Missing regions"
            assert "reasonsCode" in decision["health"], "Missing reasonsCode in health"
            assert "reasonsTR" in decision["health"], "Missing reasonsTR in health"

            # Extract summary
            health_status = decision["health"]["status"]
            no_go = decision["noGo"]["isNoGo"]
            region_count = len(decision["regions"])

            top_species: list[str] = []
            for region in decision["regions"]:
                for target in region["recommendedSpot"]["targets"]:
                    sp = target["speciesId"]
                    if sp not in top_species:
                        top_species.append(sp)

            print(f"\n[{i}] {name}")
            print(f"    Health: {health_status} | NoGo: {no_go} | Regions: {region_count}")
            print(f"    Top species: {', '.join(top_species[:5])}")
            print(f"    ✅ PASS")

        except Exception as e:
            print(f"\n[{i}] {name}")
            print(f"    ❌ FAIL: {e}")
            all_ok = False

    print("\n" + "=" * 70)
    if all_ok:
        print("ALL 4 SCENARIOS PASSED ✅")
    else:
        print("SOME SCENARIOS FAILED ❌")
    print("=" * 70)

    return all_ok


if __name__ == "__main__":
    success = run_smoke()
    sys.exit(0 if success else 1)
