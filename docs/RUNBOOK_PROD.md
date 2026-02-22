# FishCast Production Runbook

> v1.3.2 | 2026-02-22

## Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/health` | GET | No | System health check |
| `/api/v1/decision/today` | GET | No | Daily decision output |
| `/api/v1/scores/today` | GET | No | All spot summary scores |
| `/api/v1/scores/spot/{id}` | GET | No | Detailed spot score |
| `/api/v1/spots` | GET | No | All spots |
| `/api/v1/species` | GET | No | All species |
| `/api/v1/techniques` | GET | No | All techniques |
| `/api/v1/reports` | POST | Yes | Submit catch report |

## Health Endpoint

```bash
curl https://api.fishcast.app/api/v1/health
```

Expected response:
```json
{"status":"ok","engineVersion":"1.0.0","rulesetVersion":"20260222.2","rulesCount":31}
```

## Health Block Interpretation

The `/decision/today` response includes a `health` block:

| Status | Meaning | Action |
|--------|---------|--------|
| `good` | All data sources live, no missing fields | Normal operation |
| `degraded` | Cached data or missing wave height | Monitor, scores still valid |
| `bad` | Fallback data or missing sea temperature | Alert, scores may be inaccurate |

### Reason Codes

| Code | Description |
|------|-------------|
| `data_quality_fallback` | Weather API unavailable, using fallback |
| `data_quality_cached` | Using cached weather data |
| `provider_issue` | Provider-specific issue (see `reasonsTR` for details) |
| `missing_sea_temp` | Sea temperature data unavailable |
| `missing_wave_height` | Wave height data unavailable |

## Env Vars

| Var | Required | Default | Description |
|-----|----------|---------|-------------|
| `STORMGLASS_API_KEY` | No | None | Stormglass API key for sea temp/wave data |
| `ALLOW_TRACE_FULL` | No | `"false"` | Enable full trace output (dev/staging only) |

## Trace Level Guard

Production should keep `ALLOW_TRACE_FULL=false`. When a client requests `traceLevel=full`:
- Response will contain `traceLevel=minimal` (downgraded)
- `meta.traceLevelRequested` = `"full"`, `meta.traceLevelApplied` = `"minimal"`

To enable full trace (dev/staging):
```bash
export ALLOW_TRACE_FULL=true
```

## Smoke Test

Run offline decision scenarios (no external API calls):
```bash
cd backend && python3 scripts/smoke_decision.py
```

Expected: 4/4 scenarios pass. If any fail, check config file integrity.

## Troubleshooting

### Health status "bad"
1. Check `reasonsCode[]` in health response
2. If `data_quality_fallback`: check STORMGLASS_API_KEY and Open-Meteo availability
3. If `missing_sea_temp`: Stormglass API may be down or rate-limited

### Health status "degraded"
1. If `data_quality_cached`: weather data is stale, check cache TTL
2. If `missing_wave_height`: non-critical, scores still valid

### NoGo triggered unexpectedly
1. Check `noGo.reasonsTR[]` for rule explanation
2. NoGo is always from rule engine (`nogo_extreme_wind`, wind >= 35 km/h)
3. Check `shelteredExceptions[]` for sheltered spots

### Decision latency high
1. Check telemetry logs: `fishcast.telemetry` logger
2. Normal latency: < 100ms for generate_decision()
3. External API calls (weather, solunar) are the bottleneck

### Rules validation fails at startup
1. `rules.yaml` validated against `rules_schema.json` at boot
2. Invalid rules = app crash (by design)
3. Check error message for specific rule ID

## Telemetry

Structured JSON logs via `fishcast.telemetry` logger:
```json
{
  "event": "decision_generated",
  "contractVersion": "1.3",
  "healthStatus": "good",
  "dataQuality": "live",
  "noGo": false,
  "topSpecies": ["cinekop", "sarikanat", "istavrit"],
  "latencyMs": 45.2,
  "regionCount": 3
}
```

Filter in Cloud Run logs:
```
jsonPayload.event="decision_generated"
```

## Monitoring Checklist

- [ ] `/health` returns `status: "ok"` with `rulesCount: 31`
- [ ] `/decision/today` returns 3 regions with species scores
- [ ] `health.status` is `"good"` (not degraded/bad)
- [ ] Telemetry logs show `latencyMs < 200`
- [ ] Smoke script passes 4/4
