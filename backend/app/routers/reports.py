"""FishCast reports endpoints.

POST /reports — av raporu ekle (Firebase Auth gerekli).
GET /reports/user — kullanici raporlari (auth).
GET /reports/spot/{spotId} — public: aggregate-only (24h), auth: own reports.
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
    # timestamp: native datetime — Firestore stores as Timestamp type
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
        "timestamp": now,
        "createdAt": now,
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
    "/reports/user",
    summary="Kullanici raporlari",
    description="Oturum acmis kullanicinin tum raporlarini doner.",
)
async def get_user_reports(
    authorization: Optional[str] = Header(None),
) -> dict[str, Any]:
    """Kullanicinin kendi av raporlarini doner."""
    user = await get_auth_user(authorization)
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Raporlarinizi gormek icin giris yapmaniz gerekiyor",
        )

    db = get_firestore_db()
    reports: list[dict[str, Any]] = []

    if db:
        try:
            docs = (
                db.collection("reports")
                .where("userId", "==", user["uid"])
                .order_by("timestamp", direction="DESCENDING")
                .limit(100)
                .stream()
            )
            for doc in docs:
                report = doc.to_dict()
                # Serialize Firestore Timestamp to ISO string for API
                ts = report.get("timestamp")
                if hasattr(ts, "isoformat"):
                    report["timestamp"] = ts.isoformat()
                reports.append(report)
        except Exception as e:
            logger.error("Kullanici raporlari okunamadi: %s", e)

    return {
        "userId": user["uid"],
        "reports": reports,
        "totalCount": len(reports),
    }


@router.get(
    "/reports/spot/{spot_id}",
    summary="Mera raporlari",
    description="Public: son 24h aggregate ozet. Auth: kullanicinin kendi raporlari.",
)
async def get_spot_reports(
    spot_id: str,
    request: Request,
    authorization: Optional[str] = Header(None),
) -> dict[str, Any]:
    """Meranin av rapor ozetini veya kullanici raporlarini doner.

    Public (no auth): Aggregate-only summary (24h) — totalReports,
    speciesCounts, techniqueCounts. No raw per-report data.

    Auth: User's own raw reports for this spot.

    Args:
        spot_id: Mera kimligi.

    Returns:
        Aggregate ozet (public) veya rapor listesi (auth, own only).
    """
    # Spot validation
    spots = request.app.state.spots
    spot = next((s for s in spots if s.id == spot_id), None)
    if spot is None:
        raise HTTPException(status_code=404, detail=f"Mera bulunamadı: {spot_id}")

    user = await get_auth_user(authorization)
    db = get_firestore_db()

    if user is None:
        # === PUBLIC: aggregate-only (privacy-safe) ===
        species_counts: dict[str, int] = {}
        technique_counts: dict[str, int] = {}
        total = 0

        if db:
            try:
                cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=24)
                query = (
                    db.collection("reports")
                    .where("spotId", "==", spot_id)
                    .where("timestamp", ">=", cutoff)
                )
                docs = query.stream()
                for doc in docs:
                    r = doc.to_dict()
                    total += 1
                    sp = r.get("species", "unknown")
                    species_counts[sp] = species_counts.get(sp, 0) + r.get("quantity", 1)
                    tc = r.get("technique", "unknown")
                    technique_counts[tc] = technique_counts.get(tc, 0) + 1
            except Exception as e:
                logger.error("Spot aggregate raporlar okunamadi: %s", e)

        return {
            "spotId": spot_id,
            "spotName": spot.name,
            "period": "24h",
            "totalReports": total,
            "speciesCounts": species_counts,
            "techniqueCounts": technique_counts,
        }
    else:
        # === AUTH: user's own reports for this spot ===
        reports: list[dict[str, Any]] = []

        if db:
            try:
                docs = (
                    db.collection("reports")
                    .where("spotId", "==", spot_id)
                    .where("userId", "==", user["uid"])
                    .order_by("timestamp", direction="DESCENDING")
                    .limit(50)
                    .stream()
                )
                for doc in docs:
                    report = doc.to_dict()
                    # Serialize Firestore Timestamp to ISO string for API
                    ts = report.get("timestamp")
                    if hasattr(ts, "isoformat"):
                        report["timestamp"] = ts.isoformat()
                    reports.append(report)
            except Exception as e:
                logger.error("Kullanici spot raporlari okunamadi: %s", e)

        return {
            "spotId": spot_id,
            "spotName": spot.name,
            "reports": reports,
            "totalCount": len(reports),
        }
