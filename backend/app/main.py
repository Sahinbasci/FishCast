"""FishCast API — Istanbul Kıyı Balıkçılığı Karar Destek Sistemi.

Ana FastAPI uygulaması. Startup'ta JSON/YAML data dosyalarını yükler,
rules.yaml'ı JSON Schema ile validate eder,
CORS middleware ve tüm router'ları yapılandırır.
"""

from __future__ import annotations

import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

import yaml

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models.spot import SpotOut
from app.models.species_model import SpeciesOut
from app.models.technique import TechniqueOut
from app.routers import decision, health, internal, reports, scores, species, spots, techniques
from app.services.firebase import initialize_firebase
from app.models.enums import SpeciesId
from app.services.rules import load_and_validate_rules

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

DATA_DIR = Path(__file__).parent / "data"


def _load_json(filename: str) -> list[dict]:
    """JSON dosyasını DATA_DIR'den yükler.

    Args:
        filename: Yüklenecek JSON dosyasının adı.

    Returns:
        JSON içeriği (list of dict).

    Raises:
        FileNotFoundError: Dosya bulunamazsa.
        json.JSONDecodeError: JSON parse hatası.
    """
    file_path = DATA_DIR / filename
    with open(file_path, encoding="utf-8") as f:
        return json.load(f)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Uygulama yaşam döngüsü: startup'ta data yükleme ve validation.

    Startup'ta:
    1. spots.json, species.json, techniques.json yükle + Pydantic validate
    2. rules.yaml yükle + JSON Schema validate (geçersiz → crash)
    3. Firebase initialize (opsiyonel)
    4. Stormglass API key'i env'den al
    """
    # --- Startup ---
    logger.info("FishCast API başlatılıyor...")

    # Spots: 16 mera
    raw_spots = _load_json("spots.json")
    app.state.spots = [SpotOut.model_validate(s) for s in raw_spots]
    logger.info("Yüklendi: %d mera", len(app.state.spots))

    # Species: 9 tür
    raw_species = _load_json("species.json")
    app.state.species = [SpeciesOut.model_validate(s) for s in raw_species]
    logger.info("Yüklendi: %d tür", len(app.state.species))

    # Techniques: 7 teknik
    raw_techniques = _load_json("techniques.json")
    app.state.techniques = [
        TechniqueOut.model_validate(t) for t in raw_techniques
    ]
    logger.info("Yüklendi: %d teknik", len(app.state.techniques))

    # Rules: 24 kural — JSON Schema validation (geçersiz → app crash)
    app.state.rules = load_and_validate_rules()
    logger.info("Yüklendi: %d kural", len(app.state.rules))

    # Scoring config (v1.3 — weights, temps, thresholds, caps)
    with open(DATA_DIR / "scoring_config.yaml", encoding="utf-8") as f:
        app.state.scoring_config = yaml.safe_load(f)
    logger.info("Yüklendi: scoring_config.yaml")

    # Seasonality config (v1.3 — additive season adjustments, parça behavior)
    with open(DATA_DIR / "seasonality.yaml", encoding="utf-8") as f:
        app.state.seasonality_config = yaml.safe_load(f)
    # Validate: every species key must be a valid SpeciesId
    valid_species = {e.value for e in SpeciesId}
    for sp_key in app.state.seasonality_config.get("species", {}):
        if sp_key not in valid_species:
            raise SystemExit(
                f"FATAL: seasonality.yaml has unknown species '{sp_key}'. "
                f"Valid: {valid_species}"
            )
    logger.info(
        "Yüklendi: seasonality.yaml (%d tür)",
        len(app.state.seasonality_config.get("species", {})),
    )

    # Stormglass API key
    app.state.stormglass_api_key = os.environ.get("STORMGLASS_API_KEY")
    if app.state.stormglass_api_key:
        logger.info("Stormglass API key bulundu")
    else:
        logger.warning("STORMGLASS_API_KEY env var yok — fallback kullanılacak")

    # Trace guard: ALLOW_TRACE_FULL (default false — prod'da full trace kapalı)
    app.state.allow_trace_full = os.getenv("ALLOW_TRACE_FULL", "false").lower() == "true"
    logger.info("ALLOW_TRACE_FULL = %s", app.state.allow_trace_full)

    # Firebase (opsiyonel — yoksa da API çalışır)
    try:
        initialize_firebase()
    except Exception as e:
        logger.warning("Firebase init atlandı: %s", e)

    logger.info("FishCast API hazır.")

    yield

    # --- Shutdown ---
    logger.info("FishCast API kapatılıyor...")


app = FastAPI(
    title="FishCast API",
    description="Istanbul Kıyı Balıkçılığı Karar Destek Sistemi",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "https://fishcast.app",
        "https://www.fishcast.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Router mount'lar — tümü /api/v1 prefix ile
API_PREFIX = "/api/v1"
app.include_router(health.router, prefix=API_PREFIX, tags=["Health"])
app.include_router(spots.router, prefix=API_PREFIX, tags=["Spots"])
app.include_router(species.router, prefix=API_PREFIX, tags=["Species"])
app.include_router(techniques.router, prefix=API_PREFIX, tags=["Techniques"])
app.include_router(scores.router, prefix=API_PREFIX, tags=["Scores"])
app.include_router(decision.router, prefix=API_PREFIX, tags=["Decision"])
app.include_router(reports.router, prefix=API_PREFIX, tags=["Reports"])
app.include_router(internal.router, prefix=API_PREFIX, tags=["Internal"])


@app.get("/", summary="API root", tags=["Root"])
async def root() -> dict[str, str]:
    """API root endpoint.

    Returns:
        Hoşgeldin mesajı ve docs linki.
    """
    return {"message": "FishCast API v1.0.0", "docs": "/docs"}
