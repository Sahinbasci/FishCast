"""FishCast telemetry — structured decision event logging.

v1.3.2: Emits JSON-structured log events for observability.
Uses standard logging (fishcast.telemetry) — compatible with Cloud Run / GCP.
"""

from __future__ import annotations

import json
import logging
from typing import Any

_telem_logger = logging.getLogger("fishcast.telemetry")


def log_decision_event(decision: dict[str, Any], latency_ms: float) -> None:
    """Log a structured telemetry event after decision generation.

    Fields emitted:
    - event: "decision_generated"
    - contractVersion: from meta
    - healthStatus: from health block
    - dataQuality: from daySummary
    - noGo: boolean
    - topSpecies: top 3 species IDs across all regions
    - latencyMs: wall-clock time for generate_decision()
    - regionCount: number of regions in output
    """
    meta = decision.get("meta", {})
    health = decision.get("health", {})
    day_summary = decision.get("daySummary", {})
    no_go = decision.get("noGo", {})
    regions = decision.get("regions", [])

    # Collect top species across all regions (deduplicated, score-ordered)
    seen: set[str] = set()
    top_species: list[str] = []
    for region in regions:
        spot = region.get("recommendedSpot", {})
        for target in spot.get("targets", []):
            sp_id = target.get("speciesId", "")
            if sp_id and sp_id not in seen:
                seen.add(sp_id)
                top_species.append(sp_id)

    event = {
        "event": "decision_generated",
        "contractVersion": meta.get("contractVersion", "?"),
        "healthStatus": health.get("status", "unknown"),
        "dataQuality": day_summary.get("dataQuality", "unknown"),
        "noGo": no_go.get("isNoGo", False),
        "topSpecies": top_species[:3],
        "latencyMs": latency_ms,
        "regionCount": len(regions),
    }

    _telem_logger.info(json.dumps(event, ensure_ascii=False))
