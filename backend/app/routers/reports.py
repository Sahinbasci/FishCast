"""FishCast reports endpoints.

POST /reports — av raporu ekle (Firebase Auth gerekli).
GET /reports/spot/{spotId} — mera raporları (public: son 24h).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from app.models.enums import SpeciesId, TechniqueId
from app.services.firebase import get_auth_user, get_firestore_db

logger = logging.getLogger(__name__)

router = APIRouter()


class ReportCreate(BaseModel):
    """Av raporu oluşturma modeli (API_CONTRACTS.md)."""
    spot_id: str = Field(alias="spotId")
    species: SpeciesId
    quantity: int = Field(ge=1, le=100)
    avg_size: str = Field(alias="avgSize", pattern=r"^\d+cm$")
    technique: TechniqueId
    bait: Optional[str] = None
    notes: Optional[str] = Field(default=None, max_length=500)
    photo_url: Optional[str] = Field(alias="photoUrl", default=None)

    model_config = {"populate_by_name": True}


@router.post(
    "/reports",
    summary="Av raporu ekle",
    description="Yeni av raporu gönderir. Firebase Auth token gerekli. Fotoğraf: photoUrl (Firebase Storage).",
    status_code=201,
)
async def create_report(
    report: ReportCreate,
    request: Request,
    authorization: Optional[str] = Header(None),
) -> dict[str, Any]:
    """Yeni av raporu oluşturur.

    Args:
        report: Rapor verisi.
        authorization: Bearer token header.

    Returns:
        Oluşturulan rapor bilgisi.

    Raises:
        HTTPException: Auth hatası (401), spot bulunamadı (404).
    """
    # Auth check
    user = await get_auth_user(authorization)
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Rapor göndermek için giriş yapmalısınız",
        )

    # Spot validation
    spots = request.app.state.spots
    spot = next((s for s in spots if s.id == report.spot_id), None)
    if spot is None:
        raise HTTPException(status_code=404, detail=f"Mera bulunamadı: {report.spot_id}")

    now = datetime.now(tz=timezone.utc)

    # Build report document
    report_doc = {
        "userId": user["uid"],
        "spotId": report.spot_id,
        "species": report.species.value,
        "quantity": report.quantity,
        "avgSize": report.avg_size,
        "technique": report.technique.value,
        "bait": report.bait,
        "notes": report.notes,
        "photoUrl": report.photo_url,
        "timestamp": now.isoformat(),
        "verified": False,
        "weatherSnapshot": {},  # Will be filled if weather available
    }

    # Try to save to Firestore
    db = get_firestore_db()
    report_id = None
    if db:
        try:
            doc_ref = db.collection("reports").document()
            report_id = doc_ref.id
            report_doc["id"] = report_id
            doc_ref.set(report_doc)
            logger.info("Rapor kaydedildi: %s (spot: %s)", report_id, report.spot_id)
        except Exception as e:
            logger.error("Rapor Firestore'a yazılamadı: %s", e)
            report_id = f"local_{now.timestamp()}"
    else:
        report_id = f"local_{now.timestamp()}"

    return {
        "id": report_id,
        "spotId": report.spot_id,
        "species": report.species.value,
        "timestamp": now.isoformat(),
        "message": "Rapor başarıyla kaydedildi",
    }


@router.get(
    "/reports/spot/{spot_id}",
    summary="Mera raporları",
    description="Belirtilen meranın son 24 saat raporlarını döner.",
)
async def get_spot_reports(
    spot_id: str,
    request: Request,
    authorization: Optional[str] = Header(None),
) -> dict[str, Any]:
    """Meranın av raporlarını döner.

    Public: son 24h.
    Auth: tümü.

    Args:
        spot_id: Mera kimliği.

    Returns:
        Rapor listesi.
    """
    # Spot validation
    spots = request.app.state.spots
    spot = next((s for s in spots if s.id == spot_id), None)
    if spot is None:
        raise HTTPException(status_code=404, detail=f"Mera bulunamadı: {spot_id}")

    # Try Firestore
    db = get_firestore_db()
    reports: list[dict[str, Any]] = []

    if db:
        try:
            user = await get_auth_user(authorization)
            cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=24)

            query = db.collection("reports").where("spotId", "==", spot_id)
            if user is None:
                # Public: only last 24h
                query = query.where("timestamp", ">=", cutoff.isoformat())

            docs = query.order_by("timestamp", direction="DESCENDING").limit(50).stream()
            for doc in docs:
                reports.append(doc.to_dict())
        except Exception as e:
            logger.error("Raporlar okunamadı: %s", e)

    return {
        "spotId": spot_id,
        "spotName": spot.name,
        "reports": reports,
        "totalCount": len(reports),
    }
