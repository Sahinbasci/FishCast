# TASKS.md — FishCast 3-Week MVP Plan

> Contract Version: 1.4.2 | 2026-02-23

---

## Week 1: Foundation + Static Data + Skeleton UI

**Goal:** 16 mera haritada, statik detay sayfaları, Zod/Pydantic aligned.

### Backend
- [x] FastAPI scaffold (main.py, routers/, models/, data/)
- [x] GET /health endpoint
- [x] GET /spots (spots.json — 16 mera, regionId, windExposure, accuracy)
- [x] GET /species (species.json — 9 tür)
- [x] GET /techniques (statik)
- [x] Pydantic models aligned with API_CONTRACTS.md canonical types
- [x] models/enums.py: tüm enum'lar (RegionId, SpeciesMode, DataQuality)
- [x] Firebase project setup
- [x] Cloud Run deploy (basic)

### Frontend
- [x] Next.js 14 scaffold
- [x] lib/schemas.ts: Zod schemas (DecisionResponse + SpeciesScore + all enums)
- [x] lib/api.ts: typed fetch wrappers
- [x] Leaflet harita: 16 pin (region renk kodlu: avrupa=mavi, anadolu=kırmızı, city_belt=turuncu)
- [x] Spot detay sayfası /spot/[id]
- [x] Mobile responsive + Vercel deploy

### Acceptance
- [x] GET /spots 16 mera döner, regionId + accuracy field'ları var
- [x] Harita 16 pin, regionId renkleri doğru
- [x] Lighthouse mobile > 80

---

## Week 2: Weather + Solunar + Scoring + Mode

**Goal:** Gerçek skorlar + mode derivation + bestWindows.

### Backend
- [x] Open-Meteo entegrasyonu (windSpeedKmh, pressureHpa, airTempC, etc.)
- [x] Stormglass entegrasyonu (seaTempC, waveHeightM) + cache + fallback
- [x] dataQuality derivation: "live" / "cached" / "fallback" based on source status
- [x] Solunar (ephem) → majorPeriods[], minorPeriods[], solunarRating
- [x] 5 parametre fonksiyonu (pressure, wind, seaTemp, solunar, time)
- [x] Mode derivation (SCORING_ENGINE.md § Mode Derivation)
- [x] bestWindows computation (solunar major/minor + conditions → 2-4 windows)
- [x] Score doc writer → Firestore (speciesScores MAP with mode field)
- [x] Cron: POST /internal/calculate-scores (3h)
- [x] GET /scores/today + GET /scores/spot/{spotId} (MAP→ARRAY transform)
- [x] Confidence computation (dataQuality + reports + season)
- [x] Rule bonus cap enforcement (per-category + totalCap=25)

### Frontend
- [x] Skor kartı (0-100 gauge, renk)
- [x] Harita pinleri skor renginde
- [x] Spot: hava + solunar + tür skorları + mode badge
- [x] bestWindows zaman çizelgesi

### Acceptance
- [x] 16 spot × 6 tür skorlanır (mirmir Tier 1 dahil)
- [x] Her tür mode field içerir (chasing/selective/holding)
- [x] bestWindows hesaplanır (2-4 window)
- [x] Stormglass kapat → dataQuality="fallback", skorlar üretilir
- [x] Per-category caps + totalCap=25 enforced

---

## Week 3: Rule Engine + Decision Output + Reports + Deploy

**Goal:** Decision Output v1, 31 kural (28 aktif + 3 disabled), topluluk raporları, production.

### Backend — Rule Engine
- [x] rules.yaml: 31 kural (28 active + 3 disabled pending data sources)
- [x] rules_schema.json + startup validation (invalid = crash)
- [x] Conflict resolution: bonus STACK+CAP, techniques MERGE, modeHint priority-wins
- [x] removeFromTechniques + avoidTechniques logic
- [x] NO-GO single authority: nogo_extreme_wind rule only
- [x] rulesetVersion tracking (20260223.1)
- [x] Disabled rule mechanism: enabled/disableReason fields (v1.4.2)
- [x] isDaylight conditions for night rules (v1.4.2)
- [x] waterMassStrength graded scaling (v1.4.2)

### Backend — Decision Output v1
- [x] GET /decision/today endpoint (full DecisionResponse schema)
- [x] Decision service: per-region best spot selection
- [x] reportSignals24h aggregation
- [x] whyTR generation from rule messageTR + conditions
- [x] avoidTechniques from mode + removeFromTechniques
- [x] Decision doc → Firestore decisions/{date}

### Backend — Reports
- [x] POST /reports (photoUrl, no base64)
- [x] GET /reports/spot/{spotId} (24h public aggregate, auth own reports)
- [x] Firebase Auth middleware (async verify_id_token v1.4.2)
- [x] reportSignals24h update on new report

### Frontend — Decision UI
- [x] /decision page: Daily Decision ana blok
  - daySummary card (rüzgar, basınç trend, sıcaklık, dataQuality badge)
  - bestWindows zaman çizelgesi (horizontal)
  - 3 region kartı: mera + türler + teknikler + whyTR + avoidTechniques
  - Mode göstergesi per tür
  - noGo full-screen overlay (isNoGo=true) + sheltered alternatives (v1.4.2)
- [x] Rapor formu + rapor kartları
- [x] Auth: Google sign-in
- [x] Error states + loading skeletons
- [x] RegionCard reportSignals24h display (v1.4.2)

### Deploy & Beta
- [x] Production: Vercel + Cloud Run + Cloud Scheduler (3h)
- [ ] 3 deneyimli balıkçı beta
- [ ] Golden test fixtures pass
- [ ] Feedback → rulesetVersion iteration

### Acceptance
- [x] GET /decision/today doğru DecisionResponse schema döner
- [x] 3 region'da recommendedSpot var
- [x] Mode koşula göre değişir
- [x] avoidTechniques selective modda spin içerir
- [x] 31 kural (28 active) unit test geçer
- [ ] Golden fixtures 3 gün pass
- [ ] Beta balıkçılar uçtan uca kullanabilir

---

## Golden Test Fixtures

### Fixture 1: Calm Day — Chasing
```
Input:
  windSpeedKmh: 10, windDirDeg: 45, pressureHpa: 1015,
  pressureChange3hHpa: 0.2, pressureTrend: "stable",
  seaTempC: 18, month: 10, solunarRating: 0.8
  reportSignals24h: null

Expected:
  noGo.isNoGo: false
  dataQuality: "live"
  regions[regionId="avrupa"].recommendedSpot.targets[0].mode: "chasing"
  regions[regionId="avrupa"].recommendedSpot.avoidTechniques: []
  bestWindows.length: >= 2
```

### Fixture 2: Pressure Drop — Selective
```
Input:
  windSpeedKmh: 14, windDirDeg: 200, pressureHpa: 1008,
  pressureChange3hHpa: -2.5, pressureTrend: "falling",
  seaTempC: 13, month: 11, solunarRating: 0.5
  reportSignals24h: {naturalBaitBias: true, totalReports: 5}

Expected:
  noGo.isNoGo: false
  cinekop target mode: "selective"
  avoidTechniques contains techniqueId "spin"
  recommendedTechniques contains "kursun_arkasi" or "yemli_dip"
```

### Fixture 3: Storm — NO-GO
```
Input:
  windSpeedKmh: 40, windDirDeg: 45, pressureHpa: 998,
  pressureChange3hHpa: -4.0, pressureTrend: "falling",
  seaTempC: 12, month: 12, solunarRating: 0.3

Expected:
  noGo.isNoGo: true
  noGo.reasonsTR length >= 1
  All species suppressedByNoGo: true
  overallScore: 0 (in scores endpoint)
```

---

## Post-MVP (Week 4+)
- [ ] Pro tier + iyzico
- [ ] 7-day forecast
- [ ] Push notifications
- [ ] Tier 2 türler scoring + mode
- [ ] Marmara kıyısı (regionGroup: "marmara_kıyı")
- [ ] ML model complement (v2.0)
- [ ] Coord accuracy verification campaign

## Definition of Done
1. TypeScript strict / Pydantic validate
2. Canonical types match API_CONTRACTS.md
3. Mobile responsive
4. Error handling + Türkçe mesaj
5. Git: feat/fix/refactor/docs/data
6. No hardcoded fishing lore in code
