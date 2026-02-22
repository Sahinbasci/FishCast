"""FishCast test fixtures — shared across all P0 tests."""

import yaml
import pytest
from pathlib import Path
from unittest.mock import MagicMock

DATA_DIR = Path(__file__).parent.parent / "app" / "data"


@pytest.fixture
def scoring_config():
    """Load real scoring_config.yaml."""
    with open(DATA_DIR / "scoring_config.yaml") as f:
        return yaml.safe_load(f)


@pytest.fixture
def seasonality_config():
    """Load real seasonality.yaml."""
    with open(DATA_DIR / "seasonality.yaml") as f:
        return yaml.safe_load(f)


@pytest.fixture
def mock_weather():
    """Typical Istanbul weather for testing."""
    w = MagicMock()
    w.wind_speed_kmh = 12.0
    w.wind_dir_deg = 45  # NE
    w.wind_direction_cardinal = "NE"
    w.wind_direction_tr = "poyraz"
    w.pressure_hpa = 1015.0
    w.pressure_change_3h_hpa = -0.5
    w.pressure_trend = MagicMock(value="stable")
    w.air_temp_c = 15.0
    w.cloud_cover_pct = 40.0
    w.sea_temp_c = 16.0
    w.wave_height_m = 0.5
    w.data_quality = MagicMock(value="live")
    w.data_issues = []
    return w


@pytest.fixture
def mock_weather_extreme_wind():
    """Extreme wind for noGo testing."""
    w = MagicMock()
    w.wind_speed_kmh = 38.0
    w.wind_dir_deg = 45  # NE
    w.wind_direction_cardinal = "NE"
    w.wind_direction_tr = "poyraz"
    w.pressure_hpa = 1010.0
    w.pressure_change_3h_hpa = -1.0
    w.pressure_trend = MagicMock(value="falling")
    w.air_temp_c = 12.0
    w.cloud_cover_pct = 70.0
    w.sea_temp_c = 14.0
    w.wave_height_m = 2.0
    w.data_quality = MagicMock(value="live")
    w.data_issues = []
    return w


@pytest.fixture
def mock_solunar():
    """Typical solunar data."""
    return {
        "majorPeriods": [{"start": "06:00", "end": "08:00"}],
        "minorPeriods": [{"start": "12:00", "end": "13:00"}],
        "moonPhase": "waxing_gibbous",
        "moonIllumination": 65.0,
        "solunarRating": 0.6,
    }


@pytest.fixture
def mock_spot():
    """Mock SpotOut for testing."""
    spot = MagicMock()
    spot.id = "tarabya"
    spot.name = "Tarabya"
    spot.shore = MagicMock(value="european")
    spot.region_id = MagicMock(value="avrupa")
    spot.pelagic_corridor = False
    spot.features = ["kayalık", "rıhtım"]
    spot.accuracy = MagicMock(value="approx")
    spot.wind_exposure = MagicMock()
    spot.wind_exposure.onshore_dirs_deg = [225]
    spot.wind_exposure.offshore_dirs_deg = [45]
    spot.wind_exposure.shelter_score_0to1 = 0.6
    spot.primary_techniques = ["lrf", "yemli_dip"]
    spot.technique_bias = ["lrf"]
    spot.sheltered_from = ["NE", "N"]
    spot.wind_exposure_map = {"NE": "favorable", "SW": "hostile"}
    spot.corridor_potential = 0.2
    return spot


@pytest.fixture
def mock_spot_bebek():
    """Mock Bebek spot — key for sheltered exception test."""
    spot = MagicMock()
    spot.id = "bebek"
    spot.name = "Bebek"
    spot.shore = MagicMock(value="european")
    spot.region_id = MagicMock(value="avrupa")
    spot.pelagic_corridor = True
    spot.features = ["korunaklı", "kayalık"]
    spot.accuracy = MagicMock(value="verified")
    spot.wind_exposure = MagicMock()
    spot.wind_exposure.onshore_dirs_deg = [225]
    spot.wind_exposure.offshore_dirs_deg = [45]
    spot.wind_exposure.shelter_score_0to1 = 0.7
    spot.primary_techniques = ["shore_jig", "lrf"]
    spot.technique_bias = ["shore_jig"]
    spot.sheltered_from = ["NE", "N"]
    spot.wind_exposure_map = {"NE": "favorable", "SW": "hostile"}
    spot.corridor_potential = 0.7
    return spot
