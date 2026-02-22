# Release Notes — FishCast v1.3.2

> Production Readiness Pack | 2026-02-22

## Changes

### Health Block: Structured Reason Codes
- `reasonsCode[]` (machine-readable): `data_quality_fallback`, `data_quality_cached`, `provider_issue`, `missing_sea_temp`, `missing_wave_height`
- `reasonsTR[]` (Turkish text, human-readable)
- `reasons` alias (backward compat, same reference as `reasonsTR`)
- Health block always present in `/decision/today` response

### Trace Guard
- New env var: `ALLOW_TRACE_FULL` (default `"false"`)
- When `false`, `traceLevel=full` requests are downgraded to `minimal`
- Meta includes `traceLevelRequested` / `traceLevelApplied` when downgraded
- Applies to both `/decision/today` and `/scores/spot/{spotId}`

### Telemetry
- Structured JSON logging via `fishcast.telemetry` logger
- Event: `decision_generated` with fields: contractVersion, healthStatus, dataQuality, noGo, topSpecies, latencyMs, regionCount
- Compatible with Cloud Run / GCP structured logging

### SeasonStatus UI Config
- `SEASON_STATUS_CONFIG` in `frontend/src/lib/constants.ts`
- Centralized label/color/bg/showBreakdown per status
- `SpeciesScore.tsx` refactored: config-driven badges, breakdown gated by `showBreakdown`

### Smoke Script
- `backend/scripts/smoke_decision.py` — 4 offline scenarios
- Uses real configs (spots.json, rules.yaml, scoring/seasonality configs)
- No external API calls

### health.py Fixes
- `rulesCount`: 24 -> 31
- `rulesetVersion`: 20260219.1 -> 20260222.2

## Compatibility Notes
- All new fields are **optional** — no breaking changes
- `reasons` field kept as alias for backward compat
- `reasonsCode` / `reasonsTR` are additive
- `traceLevelRequested` / `traceLevelApplied` only appear when trace is downgraded
- Frontend Zod schemas updated with optional fields

## New Env Vars
| Var | Default | Description |
|-----|---------|-------------|
| `ALLOW_TRACE_FULL` | `"false"` | Gates traceLevel=full in production |

## Deploy Order
1. Backend deploy (new env var defaults safe)
2. Frontend deploy (Zod schemas backward-compatible)
3. Set `ALLOW_TRACE_FULL=true` only in dev/staging if needed

## Rollback
- Backend: revert to v1.3.1 tag. Health block returns `reasons` only (no `reasonsCode`/`reasonsTR`). Frontend handles missing fields via optional Zod.
- Frontend: revert to v1.3.1 tag. Backend response has extra fields that frontend ignores.

## Test Results
- 55 backend tests pass (was 47 in v1.3.1)
- Frontend `tsc --noEmit` clean
- Smoke script: 4/4 scenarios pass
