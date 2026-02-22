# FishCast Production Runbook

> v1.4.1 | 2026-02-22

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
| `/api/v1/reports/user` | GET | Yes | User's own reports |
| `/api/v1/reports/spot/{id}` | GET | No | Spot aggregate (24h public) |
| `/api/v1/_meta` | GET | No | Deploy guard / runtime config |

## Deploy Architecture

```
Frontend (Next.js 14) ──── Vercel
Backend  (FastAPI)    ──── Cloud Run (europe-west1)
Database              ──── Firebase Firestore
Auth                  ──── Firebase Auth (Google Sign-In)
Weather               ──── Open-Meteo + Stormglass
Solunar               ──── ephem (local computation)
CI/CD                 ──── GitHub Actions
```

## Cloud Run Deploy

```bash
# Build and push
IMAGE=europe-west1-docker.pkg.dev/$PROJECT_ID/fishcast/fishcast-api:latest
docker build -t $IMAGE ./backend
docker push $IMAGE

# Deploy
gcloud run deploy fishcast-api \
  --image $IMAGE \
  --region europe-west1 \
  --allow-unauthenticated \
  --set-env-vars "ALLOW_TRACE_FULL=false,OFFLINE_MODE=false,GIT_SHA=$(git rev-parse HEAD),CORS_ALLOWED_ORIGINS=https://fishcast.app,https://www.fishcast.app" \
  --set-secrets "STORMGLASS_API_KEY=stormglass-api-key:latest" \
  --memory 512Mi --cpu 1 \
  --concurrency 40 \
  --min-instances 0 --max-instances 3 \
  --timeout 60
```

## Vercel Deploy

```bash
cd frontend
vercel --prod
# Set env vars in Vercel dashboard:
# NEXT_PUBLIC_API_URL=https://fishcast-api-xxxxx.run.app/api/v1
# NEXT_PUBLIC_FIREBASE_API_KEY=...
# NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=...
# NEXT_PUBLIC_FIREBASE_PROJECT_ID=...
```

## Env Vars

### Backend (Cloud Run)

| Var | Required | Default | Description |
|-----|----------|---------|-------------|
| `STORMGLASS_API_KEY` | No | None | Sea temp/wave data |
| `ALLOW_TRACE_FULL` | No | `"false"` | Full trace (dev only) |
| `OFFLINE_MODE` | No | `"false"` | Skip external APIs |
| `CORS_ALLOWED_ORIGINS` | No | localhost+127.0.0.1+fishcast.app | Comma-separated origins |
| `GIT_SHA` | No | `"unknown"` | Git commit SHA (set by CI/CD) |

### Frontend (Vercel)

| Var | Required | Description |
|-----|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Yes | Backend API base URL |
| `NEXT_PUBLIC_FIREBASE_API_KEY` | Yes | Firebase web app config |
| `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN` | Yes | Firebase auth domain |
| `NEXT_PUBLIC_FIREBASE_PROJECT_ID` | Yes | Firebase project ID |
| `NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET` | No | Firebase storage |
| `NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID` | No | FCM sender ID |
| `NEXT_PUBLIC_FIREBASE_APP_ID` | Yes | Firebase app ID |

## Health Endpoint

```bash
curl https://api.fishcast.app/api/v1/health
```

Expected response:
```json
{"status":"ok","engineVersion":"1.0.0","rulesetVersion":"20260222.2","rulesCount":31}
```

## /_meta Endpoint (Deploy Guard)

```bash
curl https://api.fishcast.app/api/v1/_meta
```

Expected response:
```json
{"offlineMode":false,"allowTraceFull":false,"rulesetVersion":"20260222.2","rulesCount":31,"buildSha":"abc123..."}
```

Deploy workflow asserts `offlineMode==false` and `allowTraceFull==false` after every deploy.

## Health Block Interpretation

| Status | Meaning | Action |
|--------|---------|--------|
| `good` | All data sources live | Normal operation |
| `degraded` | Cached data or missing wave height | Monitor |
| `bad` | Fallback data or missing sea temperature | Alert |

### Reason Codes

| Code | Description |
|------|-------------|
| `data_quality_fallback` | Weather API unavailable, using fallback |
| `data_quality_cached` | Using cached weather data |
| `provider_issue` | Provider-specific issue |
| `missing_sea_temp` | Sea temperature data unavailable |
| `missing_wave_height` | Wave height data unavailable |

## Trace Level Guard

Production: `ALLOW_TRACE_FULL=false`. Requests for `traceLevel=full` downgraded to `minimal`.

## Smoke Test

```bash
cd backend && OFFLINE_MODE=true python3 scripts/smoke_decision.py
```

Expected: 4/4 scenarios pass.

## Firestore Collections

| Collection | Purpose | Access |
|------------|---------|--------|
| `reports` | User catch reports | Owner read/write; aggregate via backend API |
| `decisions/{date}` | Daily decision snapshots | Backend write, public read |
| `scores/{date}/spots/{id}` | Per-spot scores | Backend write, public read |
| `cache/stormglass_latest` | Weather cache | Backend only |
| `users/{uid}` | User profiles | User own data only |

## Firestore Security (v1.4.1)

Reports collection hardened:
- **Field allowlist**: Only permitted fields accepted (hasOnly check)
- **Type validation**: spotId/species/technique string<=50, quantity int 1-100, timestamp Firestore Timestamp
- **Size guard**: notes<=500 chars, max 15 fields per document
- **Immutable fields**: userId, spotId, timestamp cannot change after creation
- **No delete**: `allow delete: if false`

## Firebase Deploy

```bash
# Deploy security rules + indexes
firebase deploy --only firestore:rules,firestore:indexes

# Verify rules are active
firebase firestore:rules:list
```

**Security model:**
- `reports`: Owner-only client reads. Public spot aggregates via backend Admin SDK.
- `decisions`, `scores`: Public read, backend-only writes.
- `cache`: No client access.
- `users/{uid}`: Owner-only.

## CI/CD

- **On PR:** secret leak check + backend tests + frontend tsc + smoke (`.github/workflows/ci.yml`)
- **On main:** Docker build validation (main repo only, not forks)
- **Manual deploy:** `.github/workflows/deploy.yml` (staging/production, /_meta guard)

## Troubleshooting

### Health status "bad"
1. Check `reasonsCode[]` in health response
2. If `data_quality_fallback`: check STORMGLASS_API_KEY and Open-Meteo
3. If `missing_sea_temp`: Stormglass may be rate-limited

### NoGo triggered unexpectedly
1. Check `noGo.reasonsTR[]` for rule explanation
2. NoGo only from rule engine (`nogo_extreme_wind`, wind >= 35 km/h)
3. Check `shelteredExceptions[]` for sheltered spots

### Rules validation fails at startup
1. `rules.yaml` validated against `rules_schema.json` at boot
2. Invalid rules = app crash (by design)

### Auth token errors
- Expired tokens: User gets 401, frontend redirects to re-login
- Revoked tokens: Same behavior (check_revoked=True enforced)
- Categorized logging in firebase.py for debugging

## Monitoring Checklist

- [ ] `/health` returns `status: "ok"` with `rulesCount: 31`
- [ ] `/_meta` returns `offlineMode: false` and `allowTraceFull: false`
- [ ] `/decision/today` returns 3 regions with species scores
- [ ] `health.status` is `"good"`
- [ ] Telemetry logs show `latencyMs < 200`
- [ ] Smoke script passes 4/4
- [ ] Firebase Auth login works
- [ ] POST /reports returns 201 for authed users
- [ ] POST /reports returns 401 without auth
- [ ] GET /reports/spot/{id} (no auth) returns aggregate only
