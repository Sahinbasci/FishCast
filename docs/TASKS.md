# TASKS.md — FishCast 3-Week MVP Plan

> Contract Version: 1.2 | 2026-02-19

---

## Week 1: Foundation + Static Data + Skeleton UI

**Goal:** 16 mera haritada, statik detay sayfaları, Zod/Pydantic aligned.

### Backend
- [ ] FastAPI scaffold (main.py, routers/, models/, data/)
- [ ] GET /health endpoint
- [ ] GET /spots (spots.json — 16 mera, regionId, windExposure, accuracy)
- [ ] GET /species (species.json — 9 tür)
- [ ] GET /techniques (statik)
- [ ] Pydantic models aligned with API_CONTRACTS.md canonical types
- [ ] models/enums.py: tüm enum'lar (RegionId, SpeciesMode, DataQuality)
- [ ] Firebase project setup
- [ ] Cloud Run deploy (basic)

### Frontend
- [ ] Next.js 14 scaffold
- [ ] lib/schemas.ts: Zod schemas (DecisionResponse + SpeciesScore + all enums)
- [ ] lib/api.ts: typed fetch wrappers
- [ ] Leaflet harita: 16 pin (region renk kodlu: avrupa=mavi, anadolu=kırmızı, city_belt=turuncu)
- [ ] Spot detay sayfası /spot/[id]
- [ ] Mobile responsive + Vercel deploy

### Acceptance
- [ ] GET /spots 16 mera döner, regionId + accuracy field'ları var
- [ ] Harita 16 pin, regionId renkleri doğru
- [ ] Lighthouse mobile > 80

---

## Week 2: Weather + Solunar + Scoring + Mode

**Goal:** Gerçek skorlar + mode derivation + bestWindows.

### Backend
- [ ] Open-Meteo entegrasyonu (windSpeedKmh, pressureHpa, airTempC, etc.)
- [ ] Stormglass entegrasyonu (seaTempC, waveHeightM) + cache + fallback
- [ ] dataQuality derivation: "live" / "cached" / "fallback" based on source status
- [ ] Solunar (ephem) → majorPeriods[], minorPeriods[], solunarRating
- [ ] 5 parametre fonksiyonu (pressure, wind, seaTemp, solunar, time)
- [ ] Mode derivation (SCORING_ENGINE.md § Mode Derivation)
- [ ] bestWindows computation (solunar major/minor + conditions → 2-4 windows)
- [ ] Score doc writer → Firestore (speciesScores MAP with mode field)
- [ ] Cron: POST /internal/calculate-scores (3h)
- [ ] GET /scores/today + GET /scores/spot/{spotId} (MAP→ARRAY transform)
- [ ] Confidence computation (dataQuality + reports + season)
- [ ] Rule bonus cap enforcement (max +30)

### Frontend
- [ ] Skor kartı (0-100 gauge, renk)
- [ ] Harita pinleri skor renginde
- [ ] Spot: hava + solunar + tür skorları + mode badge
- [ ] bestWindows zaman çizelgesi

### Acceptance
- [ ] 16 spot × 5 tür skorlanır
- [ ] Her tür mode field içerir (chasing/selective/holding)
- [ ] bestWindows hesaplanır (2-4 window)
- [ ] Stormglass kapat → dataQuality="fallback", skorlar üretilir
- [ ] No species rule bonus exceeds +30

---

## Week 3: Rule Engine + Decision Output + Reports + Deploy

**Goal:** Decision Output v1, 24 kural, topluluk raporları, production.

### Backend — Rule Engine
- [ ] rules.yaml: 24 kural (modeHint, regionId, pelagicCorridor conditions)
- [ ] rules_schema.json + startup validation (invalid = crash)
- [ ] Conflict resolution: bonus STACK+CAP, techniques MERGE, modeHint priority-wins
- [ ] removeFromTechniques + avoidTechniques logic
- [ ] NO-GO single authority: nogo_extreme_wind rule only
- [ ] rulesetVersion tracking

### Backend — Decision Output v1
- [ ] GET /decision/today endpoint (full DecisionResponse schema)
- [ ] Decision service: per-region best spot selection
- [ ] reportSignals24h aggregation
- [ ] whyTR generation from rule messageTR + conditions
- [ ] avoidTechniques from mode + removeFromTechniques
- [ ] Decision doc → Firestore decisions/{date}

### Backend — Reports
- [ ] POST /reports (photoUrl, no base64)
- [ ] GET /reports/spot/{spotId} (24h public, all auth)
- [ ] Firebase Auth middleware
- [ ] reportSignals24h update on new report

### Frontend — Decision UI
- [ ] /decision page: Daily Decision ana blok
  - daySummary card (rüzgar, basınç trend, sıcaklık, dataQuality badge)
  - bestWindows zaman çizelgesi (horizontal)
  - 3 region kartı: mera + türler + teknikler + whyTR + avoidTechniques
  - Mode göstergesi per tür (🟢/🟡/🔴)
  - noGo full-screen overlay (isNoGo=true)
- [ ] Rapor formu + rapor kartları
- [ ] Auth: Google sign-in
- [ ] Error states + loading skeletons

### Deploy & Beta
- [ ] Production: Vercel + Cloud Run + Cloud Scheduler (3h)
- [ ] 3 deneyimli balıkçı beta
- [ ] Golden test fixtures pass
- [ ] Feedback → rulesetVersion iteration

### Acceptance
- [ ] GET /decision/today doğru DecisionResponse schema döner
- [ ] 3 region'da recommendedSpot var
- [ ] Mode koşula göre değişir
- [ ] avoidTechniques selective modda spin içerir
- [ ] 24 kural unit test geçer
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
