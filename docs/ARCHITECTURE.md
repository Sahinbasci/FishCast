# ARCHITECTURE.md — FishCast Teknik Mimari

> Contract Version: 1.2 | 2026-02-19

## Sistem Diagramı
```
┌──────────────┐    ┌────────────────┐    ┌─────────────────┐
│  Next.js App │───▶│ FastAPI Backend │───▶│ Open-Meteo      │
│  (Vercel)    │◀───│ (Cloud Run)    │◀───│ Stormglass      │
│              │    │                │    │ ephem (solunar)  │
│ Decision UI  │    │ Decision Svc   │    │ Firebase         │
│ Map + Scores │    │ Scoring Engine │    └─────────────────┘
│ Reports      │    │ Rule Engine    │
└──────────────┘    │ Mode Engine    │
                    └────────────────┘
                           │
                    Firebase Firestore
```

## Veri Akışı
### Skor + Decision (3 saatte bir — Cloud Scheduler)
1. `POST /internal/calculate-scores`
2. Hava + solunar verileri topla, normalize et (units table)
3. Her mera için: tür skorları + mode derivation
4. Region arası en iyi mera seçimi → decision doc
5. Firestore: `scores/{date}/{spotId}` + `decisions/{date}`

### Av Raporu
1. Client → Firebase Storage direct upload → photoUrl
2. `POST /reports` (photoUrl + tür + teknik + yem)
3. Backend: validate + weatherSnapshot auto-fill
4. reportSignals24h güncelle

## Units Table
> Ref: `INSTRUCTIONS.md § Units Table`. Tüm Firestore fieldları, API ve scoring aynı birimleri kullanır.

## Database Şeması (Firestore)

### Collection: `spots`

```json
{
  "id": "bebek",
  "name": "Bebek",
  "lat": 41.0764,
  "lng": 29.0434,
  "accuracy": "approx",
  "type": "shore",
  "shore": "european",
  "regionId": "avrupa",
  "regionGroup": "bosporus_core",
  "district": "Beşiktaş",
  "description": "Boğaz'ın en popüler mera hattı",
  "pelagicCorridor": true,
  "urbanCrowdRisk": "high",
  "primarySpecies": ["levrek","cinekop","istavrit","karagoz"],
  "primaryTechniques": ["lrf","shore_jig","yemli_dip"],
  "techniqueBias": ["lrf","shore_jig"],
  "features": ["kayalık","akıntılı","gece_uygun","aydınlatmalı"],
  "depth": "medium",
  "currentExposure": "high",
  "windExposure": {
    "onshoreDirsDeg": [180, 225],
    "offshoreDirsDeg": [0, 45],
    "shelterScore0to1": 0.4
  },
  "specialRules": ["bebek_night_levrek"]
}
```

#### Spots Dataset (spots.json — 16 Mera)

```json
[
  {
    "id": "tarabya", "name": "Tarabya",
    "lat": 41.1297, "lng": 29.0534, "accuracy": "approx",
    "shore": "european", "regionId": "avrupa", "regionGroup": "bosporus_core",
    "pelagicCorridor": false, "urbanCrowdRisk": "low",
    "techniqueBias": ["yemli_dip", "capari"],
    "windExposure": {"onshoreDirsDeg": [0,45], "offshoreDirsDeg": [180,225], "shelterScore0to1": 0.6}
  },
  {
    "id": "emirgan", "name": "Emirgan",
    "lat": 41.1073, "lng": 29.0556, "accuracy": "approx",
    "shore": "european", "regionId": "avrupa", "regionGroup": "bosporus_core",
    "pelagicCorridor": true, "urbanCrowdRisk": "medium",
    "techniqueBias": ["lrf", "yemli_dip"],
    "windExposure": {"onshoreDirsDeg": [45,90], "offshoreDirsDeg": [225,270], "shelterScore0to1": 0.5}
  },
  {
    "id": "asiyan", "name": "Aşiyan",
    "lat": 41.0854, "lng": 29.0497, "accuracy": "approx",
    "shore": "european", "regionId": "avrupa", "regionGroup": "bosporus_core",
    "pelagicCorridor": true, "urbanCrowdRisk": "low",
    "techniqueBias": ["lrf", "shore_jig"],
    "windExposure": {"onshoreDirsDeg": [180,225], "offshoreDirsDeg": [0,45], "shelterScore0to1": 0.3}
  },
  {
    "id": "bebek", "name": "Bebek",
    "lat": 41.0764, "lng": 29.0434, "accuracy": "approx",
    "shore": "european", "regionId": "avrupa", "regionGroup": "bosporus_core",
    "pelagicCorridor": true, "urbanCrowdRisk": "high",
    "techniqueBias": ["lrf", "shore_jig"],
    "windExposure": {"onshoreDirsDeg": [180,225], "offshoreDirsDeg": [0,45], "shelterScore0to1": 0.4}
  },
  {
    "id": "arnavutkoy", "name": "Arnavutköy",
    "lat": 41.0687, "lng": 29.0376, "accuracy": "approx",
    "shore": "european", "regionId": "avrupa", "regionGroup": "bosporus_core",
    "pelagicCorridor": true, "urbanCrowdRisk": "medium",
    "techniqueBias": ["spin", "kursun_arkasi"],
    "windExposure": {"onshoreDirsDeg": [180,225], "offshoreDirsDeg": [0,45], "shelterScore0to1": 0.5}
  },
  {
    "id": "rumeli_hisari", "name": "Rumeli Hisarı",
    "lat": 41.0848, "lng": 29.0564, "accuracy": "approx",
    "shore": "european", "regionId": "avrupa", "regionGroup": "bosporus_core",
    "pelagicCorridor": true, "urbanCrowdRisk": "medium",
    "techniqueBias": ["spin", "shore_jig"],
    "windExposure": {"onshoreDirsDeg": [45,90], "offshoreDirsDeg": [225,270], "shelterScore0to1": 0.3}
  },
  {
    "id": "boyacikoy", "name": "Boyacıköy",
    "lat": 41.0919, "lng": 29.0542, "accuracy": "approx",
    "shore": "european", "regionId": "avrupa", "regionGroup": "bosporus_core",
    "pelagicCorridor": false, "urbanCrowdRisk": "low",
    "techniqueBias": ["yemli_dip", "lrf"],
    "windExposure": {"onshoreDirsDeg": [45,90], "offshoreDirsDeg": [225,270], "shelterScore0to1": 0.6}
  },
  {
    "id": "baltalimani", "name": "Baltalimanı",
    "lat": 41.0975, "lng": 29.0522, "accuracy": "approx",
    "shore": "european", "regionId": "avrupa", "regionGroup": "bosporus_core",
    "pelagicCorridor": true, "urbanCrowdRisk": "low",
    "techniqueBias": ["lrf", "yemli_dip"],
    "windExposure": {"onshoreDirsDeg": [45,90], "offshoreDirsDeg": [225,270], "shelterScore0to1": 0.4}
  },
  {
    "id": "sarayburnu", "name": "Sarayburnu",
    "lat": 41.0047, "lng": 28.9836, "accuracy": "approx",
    "shore": "european", "regionId": "city_belt", "regionGroup": "city_belt",
    "pelagicCorridor": true, "urbanCrowdRisk": "high",
    "techniqueBias": ["capari", "spin"],
    "windExposure": {"onshoreDirsDeg": [180,225], "offshoreDirsDeg": [0,45], "shelterScore0to1": 0.3}
  },
  {
    "id": "karakoy", "name": "Karaköy",
    "lat": 41.0222, "lng": 28.9769, "accuracy": "approx",
    "shore": "european", "regionId": "city_belt", "regionGroup": "city_belt",
    "pelagicCorridor": false, "urbanCrowdRisk": "high",
    "techniqueBias": ["yemli_dip", "capari"],
    "windExposure": {"onshoreDirsDeg": [0,45], "offshoreDirsDeg": [180,225], "shelterScore0to1": 0.7}
  },
  {
    "id": "eminonu", "name": "Eminönü",
    "lat": 41.0176, "lng": 28.9686, "accuracy": "approx",
    "shore": "european", "regionId": "city_belt", "regionGroup": "city_belt",
    "pelagicCorridor": false, "urbanCrowdRisk": "high",
    "techniqueBias": ["yemli_dip", "capari"],
    "windExposure": {"onshoreDirsDeg": [0,45], "offshoreDirsDeg": [180,225], "shelterScore0to1": 0.7}
  },
  {
    "id": "galata", "name": "Galata Köprüsü",
    "lat": 41.0201, "lng": 28.9734, "accuracy": "approx",
    "shore": "european", "regionId": "city_belt", "regionGroup": "city_belt",
    "pelagicCorridor": false, "urbanCrowdRisk": "high",
    "techniqueBias": ["yemli_dip", "capari"],
    "windExposure": {"onshoreDirsDeg": [], "offshoreDirsDeg": [], "shelterScore0to1": 0.9}
  },
  {
    "id": "kandilli", "name": "Kandilli-Çubuklu",
    "lat": 41.0673, "lng": 29.0561, "accuracy": "approx",
    "shore": "anatolian", "regionId": "anadolu", "regionGroup": "bosporus_core",
    "pelagicCorridor": true, "urbanCrowdRisk": "low",
    "techniqueBias": ["spin", "kursun_arkasi"],
    "windExposure": {"onshoreDirsDeg": [0,45], "offshoreDirsDeg": [180,225], "shelterScore0to1": 0.3}
  },
  {
    "id": "uskudar", "name": "Üsküdar",
    "lat": 41.0267, "lng": 29.0144, "accuracy": "approx",
    "shore": "anatolian", "regionId": "anadolu", "regionGroup": "bosporus_core",
    "pelagicCorridor": false, "urbanCrowdRisk": "high",
    "techniqueBias": ["yemli_dip", "capari"],
    "windExposure": {"onshoreDirsDeg": [180,225], "offshoreDirsDeg": [0,45], "shelterScore0to1": 0.5}
  },
  {
    "id": "beykoz", "name": "Beykoz",
    "lat": 41.1297, "lng": 29.0961, "accuracy": "approx",
    "shore": "anatolian", "regionId": "anadolu", "regionGroup": "bosporus_core",
    "pelagicCorridor": true, "urbanCrowdRisk": "low",
    "techniqueBias": ["lrf", "yemli_dip"],
    "windExposure": {"onshoreDirsDeg": [0,45], "offshoreDirsDeg": [180,225], "shelterScore0to1": 0.4}
  },
  {
    "id": "selvi", "name": "Selvi Noktası",
    "lat": 41.1100, "lng": 29.0800, "accuracy": "approx",
    "shore": "anatolian", "regionId": "anadolu", "regionGroup": "bosporus_core",
    "pelagicCorridor": true, "urbanCrowdRisk": "low",
    "techniqueBias": ["spin", "kursun_arkasi"],
    "windExposure": {"onshoreDirsDeg": [0,45], "offshoreDirsDeg": [180,225], "shelterScore0to1": 0.3}
  }
]
```

> Tüm koordinatlar `accuracy:"approx"`. Production öncesi GPS ile doğrulanmalı.

### Collection: `scores`
Path: `scores/{YYYY-MM-DD}/{spotId}`

```json
{
  "spotId": "bebek",
  "date": "2026-02-19",
  "meta": {"contractVersion":"1.2","generatedAt":"2026-02-19T06:00:00Z","timezone":"Europe/Istanbul"},
  "overallScore": 72,
  "noGo": {"isNoGo": false, "reasonsTR": []},
  "weather": {
    "windSpeedKmh": 12, "windDirDeg": 45, "windDirectionCardinal": "NE",
    "windDirectionTR": "poyraz", "pressureHpa": 1018, "pressureChange3hHpa": -1.5,
    "pressureTrend": "falling", "airTempC": 14, "seaTempC": 12.5,
    "waveHeightM": 0.4, "cloudCoverPct": 45
  },
  "dataSources": {
    "pressure": {"provider":"open_meteo","status":"ok","updatedAt":"2026-02-19T06:00:00Z"},
    "seaTemp": {"provider":"stormglass","status":"ok","updatedAt":"2026-02-19T03:00:00Z"},
    "wind": {"provider":"open_meteo","status":"ok","updatedAt":"2026-02-19T06:00:00Z"}
  },
  "solunar": {
    "majorPeriods": [{"start":"06:30","end":"08:30"},{"start":"18:45","end":"20:45"}],
    "minorPeriods": [{"start":"12:15","end":"13:15"},{"start":"00:30","end":"01:30"}],
    "moonPhase": "waxing_crescent", "moonIllumination": 35, "solunarRating": 0.7
  },
  "speciesScores": {
    "cinekop": {
      "score": 82, "suppressedByNoGo": false, "bestTime": "17:00-19:00",
      "confidence0to1": 0.78, "seasonStatus": "peak", "mode": "selective",
      "recommendedTechniques": ["kursun_arkasi","yemli_dip"],
      "avoidTechniques": ["spin"],
      "breakdown": {"pressure":0.85,"wind":0.90,"seaTemp":0.50,"solunar":0.70,"time":0.40,"seasonMultiplier":1.2,"rulesBonus":15}
    }
  },
  "activeRules": [{"ruleId":"bebek_night_levrek","appliedBonus":12,"affectedSpecies":["levrek"],"messageTR":"Bebek gece levrek merkezi."}]
}
```

> **speciesScores:** Firestore=MAP, API=ARRAY. Transform kuralı: `API_CONTRACTS.md § MAP vs ARRAY Transform`.
> **noGo:** Unified object. Tek kaynak: rule engine. Detay: `SCORING_ENGINE.md § NO-GO`.

### Collection: `decisions`
Path: `decisions/{YYYY-MM-DD}` — full schema: `API_CONTRACTS.md § GET /decision/today`.

### Collection: `reports`
```json
{
  "id":"auto", "userId":"uid", "spotId":"bebek", "species":"cinekop",
  "quantity":5, "avgSize":"15cm", "timestamp":"2026-02-19T17:30:00Z",
  "photoUrl":"gs://fishcast-bucket/reports/...",
  "technique":"kursun_arkasi", "bait":"istavrit_fileto", "notes":"...",
  "verified":false,
  "weatherSnapshot":{"pressureHpa":1018,"seaTempC":12.5,"windSpeedKmh":12,"windDirDeg":45}
}
```

## Enum Tanımları (Canonical)
```typescript
type SpeciesId = "istavrit"|"cinekop"|"sarikanat"|"palamut"|"karagoz"|"lufer"|"levrek"|"kolyoz"|"mirmir"
type TechniqueId = "capari"|"kursun_arkasi"|"spin"|"lrf"|"surf"|"yemli_dip"|"shore_jig"
type Shore = "european"|"anatolian"
type RegionId = "anadolu"|"avrupa"|"city_belt"
type RegionGroup = "bosporus_core"|"city_belt"|"marmara_kıyı"
type SpeciesMode = "chasing"|"selective"|"holding"
type DataQuality = "live"|"cached"|"fallback"
type PressureTrend = "falling"|"rising"|"stable"
type DataSourceStatus = "ok"|"cached"|"fallback"|"error"
type SeasonStatus = "peak"|"active"|"closed"
type CrowdRisk = "low"|"medium"|"high"
type CoordAccuracy = "approx"|"verified"
type WindCardinal = "N"|"NE"|"E"|"SE"|"S"|"SW"|"W"|"NW"
```

## Data Source Policy
| Param | Provider | Fallback | TTL |
|-------|----------|----------|-----|
| pressure, wind, airTemp, cloud | Open-Meteo | Last cache | 1h |
| seaTemp, wave | Stormglass | MONTHLY_SEA_TEMP | 3h |
| solunar | ephem | N/A | 24h |

ASLA skor üretimi atlanmaz. Fallback kullanılır, `dataQuality` buna göre set edilir.
