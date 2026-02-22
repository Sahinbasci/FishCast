# API_CONTRACTS.md — FishCast API

> Contract Version: 1.3.2 | 2026-02-22

## Base
- Dev: `http://localhost:8000/api/v1`
- Prod: `https://api.fishcast.app/api/v1`
- Auth: `Authorization: Bearer <firebase_id_token>` (where required)

---

## MAP vs ARRAY Transform (TEK KAYNAK)

Firestore `speciesScores` bir **MAP** olarak saklanır (key: speciesId). API'de **ARRAY** olarak döner.

**Transform kuralı (API layer'da uygulanır):**
1. MAP → entries → array
2. Sort: score DESC, speciesId ASC (tie-break)
3. Her entry'ye `speciesId` ve `speciesNameTR` inject

Bu kural burada TEK YERDE tanımlıdır. Diğer dosyalar buraya referans verir.

---

## Endpoints

### 1. GET `/health` — Public
```json
{"status":"ok","engineVersion":"1.0.0","rulesetVersion":"20260222.2","rulesCount":31}
```

### 2. GET `/decision/today` — Public (DECISION OUTPUT v1)

**Query params:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `traceLevel` | `"none"\|"minimal"\|"full"` | `"none"` | Trace detail in spot scores |

**Response includes `health` block (always present, v1.3.2 enhanced):**
```json
"health": {
  "status": "good"|"degraded"|"bad",
  "reasonsCode": [],
  "reasonsTR": [],
  "reasons": [],
  "normalized": { "windSpeedKmhRaw": 12.0, "windCardinalDerived": "NE", "pressureTrendDerived": "stable" }
}
```

**Reason codes (v1.3.2):** `data_quality_fallback`, `data_quality_cached`, `provider_issue`, `missing_sea_temp`, `missing_wave_height`.

**Trace guard (v1.3.2):** When `ALLOW_TRACE_FULL=false` (default), `traceLevel=full` is downgraded to `minimal`. Meta includes `traceLevelRequested` / `traceLevelApplied` when downgraded.

```json
{
  "meta": {
    "contractVersion": "1.3",
    "generatedAt": "2026-02-19T06:00:00Z",
    "timezone": "Europe/Istanbul"
  },
  "daySummary": {
    "windSpeedKmhMin": 8,
    "windSpeedKmhMax": 15,
    "windDirDeg": 45,
    "windDirectionTR": "poyraz",
    "pressureHpa": 1018,
    "pressureChange3hHpa": -1.5,
    "pressureTrend": "falling",
    "airTempCMin": 10,
    "airTempCMax": 16,
    "seaTempC": 12.5,
    "cloudCoverPct": 45,
    "waveHeightM": 0.4,
    "dataQuality": "live",
    "dataIssues": []
  },
  "bestWindows": [
    {
      "startLocal": "06:30",
      "endLocal": "08:30",
      "score0to100": 88,
      "confidence0to1": 0.82,
      "reasonsTR": [
        "Major solunar periyodu",
        "Basınç düşüşü aktiviteyi artırır"
      ]
    },
    {
      "startLocal": "16:00",
      "endLocal": "19:00",
      "score0to100": 82,
      "confidence0to1": 0.75,
      "reasonsTR": [
        "Minor solunar yaklaşıyor",
        "İstavrit akşam patlaması"
      ]
    }
  ],
  "regions": [
    {
      "regionId": "avrupa",
      "recommendedSpot": {
        "spotId": "arnavutkoy",
        "nameTR": "Arnavutköy",
        "spotWindBandKmhMin": 5,
        "spotWindBandKmhMax": 25,
        "whyTR": [
          "Pelajik koridorda — göçmen türler geçişte",
          "Poyraz hafif — Avrupa yakası korunaklı",
          "Basınç düşüşü çinekopu aktifleştiriyor"
        ],
        "targets": [
          {
            "speciesId": "cinekop",
            "speciesNameTR": "Çinekop",
            "score0to100": 82,
            "confidence0to1": 0.78,
            "mode": "selective",
            "bestWindowIndex": 1
          },
          {
            "speciesId": "istavrit",
            "speciesNameTR": "İstavrit",
            "score0to100": 75,
            "confidence0to1": 0.65,
            "mode": "chasing",
            "bestWindowIndex": 0
          }
        ],
        "recommendedTechniques": [
          {"techniqueId": "kursun_arkasi", "techniqueNameTR": "Kurşun Arkası", "setupHintTR": "Taze istavrit fileto ile"},
          {"techniqueId": "yemli_dip", "techniqueNameTR": "Yemli Dip", "setupHintTR": null}
        ],
        "avoidTechniques": [
          {"techniqueId": "spin", "techniqueNameTR": "Spin", "reasonTR": "Çinekop bugün seçici — lure verimsiz"}
        ],
        "reportSignals24h": {
          "totalReports": 8,
          "techniqueCounts": {"kursun_arkasi": 4, "yemli_dip": 3, "spin": 1},
          "naturalBaitBias": true,
          "notesTR": ["Son 24h: doğal yem 7/8 raporda tercih edilmiş"]
        }
      }
    },
    {
      "regionId": "anadolu",
      "recommendedSpot": {
        "spotId": "kandilli",
        "nameTR": "Kandilli-Çubuklu",
        "spotWindBandKmhMin": 5,
        "spotWindBandKmhMax": 20,
        "whyTR": [
          "Poyraz Anadolu'yu etkiliyor — dikkatli ol",
          "Kandilli pelajik koridor üzerinde"
        ],
        "targets": [
          {
            "speciesId": "istavrit",
            "speciesNameTR": "İstavrit",
            "score0to100": 68,
            "confidence0to1": 0.55,
            "mode": "chasing",
            "bestWindowIndex": 0
          }
        ],
        "recommendedTechniques": [
          {"techniqueId": "capari", "techniqueNameTR": "Çapari", "setupHintTR": "150g sinker"}
        ],
        "avoidTechniques": [],
        "reportSignals24h": null
      }
    },
    {
      "regionId": "city_belt",
      "recommendedSpot": {
        "spotId": "galata",
        "nameTR": "Galata Köprüsü",
        "spotWindBandKmhMin": 0,
        "spotWindBandKmhMax": 30,
        "whyTR": [
          "Rüzgardan korunaklı",
          "Çapari ile istavrit garantili"
        ],
        "targets": [
          {
            "speciesId": "istavrit",
            "speciesNameTR": "İstavrit",
            "score0to100": 70,
            "confidence0to1": 0.60,
            "mode": "chasing",
            "bestWindowIndex": 1
          }
        ],
        "recommendedTechniques": [
          {"techniqueId": "capari", "techniqueNameTR": "Çapari", "setupHintTR": null},
          {"techniqueId": "yemli_dip", "techniqueNameTR": "Yemli Dip", "setupHintTR": null}
        ],
        "avoidTechniques": [],
        "reportSignals24h": null
      }
    }
  ],
  "noGo": {
    "isNoGo": false,
    "reasonsTR": [],
    "shelteredExceptions": [
      {
        "spotId": "bebek",
        "allowedTechniques": ["lrf"],
        "warningLevel": "severe",
        "messageTR": "Bebek korunaklı — sadece LRF, dikkatli ol!"
      }
    ]
  }
}
```

> **dataQuality:** Enum `"live"|"cached"|"fallback"`. Issues in `dataIssues[]`.
> **bestWindowIndex:** 0-based index into `bestWindows[]`. null if no specific window.
> **noGo:** Object `{isNoGo, reasonsTR[], shelteredExceptions[]}`. Tek kaynak: rule engine.
> **shelteredExceptions (v1.3):** Only present when `isNoGo=true`. Lists sheltered spots where limited fishing is possible.
> **reportSignals24h:** null if no reports in 24h. Present only when data exists.
> **mode:** `"chasing"|"selective"|"holding"`. Affects technique ranking, not safety.

### 3. GET `/scores/today` — Public
Harita pini için tüm mera özetleri. (Schema unchanged from v1.1, `mode` field added per species.)

### 4. GET `/scores/spot/{spotId}` — Public
Detay skoru. speciesScores as ARRAY (see § MAP vs ARRAY Transform above).

**Query params:** `traceLevel` (`"none"|"minimal"|"full"`, default `"none"`) — controls trace detail in response.

### 5. GET `/spots` — Public
### 6. POST `/reports` — Auth (photoUrl only, no base64)
### 7. GET `/reports/spot/{spotId}` — Public (24h) / Auth (all)
### 8. GET `/species` — Public
### 9. GET `/techniques` — Public

---

## Canonical Types — Zod (Frontend)

```typescript
import { z } from "zod";

// ENUMS
export const SpeciesId = z.enum(["istavrit","cinekop","sarikanat","palamut","karagoz","lufer","levrek","kolyoz","mirmir"]);
export const TechniqueId = z.enum(["capari","kursun_arkasi","spin","lrf","surf","yemli_dip","shore_jig"]);
export const BaitId = z.enum(["istavrit_fileto","krace_fileto","hamsi_fileto","karides","midye","deniz_kurdu","boru_kurdu","mamun"]);
export const Shore = z.enum(["european","anatolian"]);
export const RegionId = z.enum(["anadolu","avrupa","city_belt"]);
export const SpeciesMode = z.enum(["chasing","selective","holding"]);
export const DataQuality = z.enum(["live","cached","fallback"]);
export const PressureTrend = z.enum(["falling","rising","stable"]);
export const SeasonStatus = z.enum(["peak","shoulder","active","off","closed"]); // "off" = off-season (v1.3.1)
export const CoordAccuracy = z.enum(["approx","verified"]);

// DECISION OUTPUT
export const DecisionMeta = z.object({
  contractVersion: z.string(),
  generatedAt: z.string(),
  timezone: z.literal("Europe/Istanbul"),
  traceLevelRequested: z.string().optional(),  // NEW v1.3.2: present when trace downgraded
  traceLevelApplied: z.string().optional(),    // NEW v1.3.2: present when trace downgraded
});

export const DaySummary = z.object({
  windSpeedKmhMin: z.number(), windSpeedKmhMax: z.number(),
  windDirDeg: z.number().min(0).max(359), windDirectionTR: z.string(),
  pressureHpa: z.number(), pressureChange3hHpa: z.number(),
  pressureTrend: PressureTrend,
  airTempCMin: z.number(), airTempCMax: z.number(),
  seaTempC: z.number().nullable(), cloudCoverPct: z.number().nullable(),
  waveHeightM: z.number().nullable(),
  dataQuality: DataQuality, dataIssues: z.array(z.string()),
});

export const BestWindow = z.object({
  startLocal: z.string(), endLocal: z.string(),
  score0to100: z.number().int().min(0).max(100),
  confidence0to1: z.number().min(0).max(1),
  reasonsTR: z.array(z.string()),
});

export const DecisionTarget = z.object({
  speciesId: SpeciesId, speciesNameTR: z.string(),
  score0to100: z.number().int().min(0).max(100),
  confidence0to1: z.number().min(0).max(1),
  mode: SpeciesMode,
  bestWindowIndex: z.number().int().nullable(),
});

export const TechniqueReco = z.object({
  techniqueId: TechniqueId, techniqueNameTR: z.string(),
  setupHintTR: z.string().nullable(),
});

export const AvoidTechnique = z.object({
  techniqueId: TechniqueId, techniqueNameTR: z.string(),
  reasonTR: z.string(),
});

export const ReportSignals = z.object({
  totalReports: z.number().int(),
  techniqueCounts: z.record(z.number()),
  naturalBaitBias: z.boolean(),
  notesTR: z.array(z.string()).optional(),
}).nullable();

export const RecommendedSpot = z.object({
  spotId: z.string(), nameTR: z.string(),
  spotWindBandKmhMin: z.number(), spotWindBandKmhMax: z.number(),
  whyTR: z.array(z.string()),
  targets: z.array(DecisionTarget),
  recommendedTechniques: z.array(TechniqueReco),
  avoidTechniques: z.array(AvoidTechnique),
  reportSignals24h: ReportSignals,
});

export const RegionDecision = z.object({
  regionId: RegionId,
  recommendedSpot: RecommendedSpot,
});

export const ShelteredExceptionEntry = z.object({
  spotId: z.string(),
  allowedTechniques: z.array(z.string()),
  warningLevel: z.string(),
  messageTR: z.string(),
});

export const NoGo = z.object({
  isNoGo: z.boolean(),
  reasonsTR: z.array(z.string()),
  shelteredExceptions: z.array(ShelteredExceptionEntry).optional(),  // NEW v1.3
});

export const HealthBlock = z.object({  // v1.3.1 + v1.3.2 enhanced
  status: z.enum(["good","degraded","bad"]),
  reasonsCode: z.array(z.string()).optional(),  // NEW v1.3.2: machine codes
  reasonsTR: z.array(z.string()).optional(),     // NEW v1.3.2: Turkish text
  reasons: z.array(z.string()).optional(),        // backward compat alias
  normalized: z.object({
    windSpeedKmhRaw: z.number(),
    windCardinalDerived: z.string(),
    pressureTrendDerived: z.string(),
  }),
});

export const DecisionResponse = z.object({
  meta: DecisionMeta,
  daySummary: DaySummary,
  bestWindows: z.array(BestWindow),
  regions: z.array(RegionDecision),
  noGo: NoGo,
  health: HealthBlock.optional(),  // NEW v1.3.1
});

// SCORE TYPES (per-spot detail)
export const SolunarPeriod = z.object({ start: z.string(), end: z.string() });
export const Solunar = z.object({
  majorPeriods: z.array(SolunarPeriod), minorPeriods: z.array(SolunarPeriod),
  moonPhase: z.string(), moonIllumination: z.number(), solunarRating: z.number(),
});

export const ScoreBreakdown = z.object({
  pressure: z.number(), wind: z.number(), seaTemp: z.number(),
  solunar: z.number(), time: z.number(),
  seasonMultiplier: z.number(),  // DEPRECATED v1.3: always 1.0
  seasonAdjustment: z.number().optional(),  // NEW v1.3: additive int
  rulesBonus: z.number(),
});

export const SpeciesScore = z.object({
  speciesId: SpeciesId, speciesNameTR: z.string(),
  score0to100: z.number().int(), suppressedByNoGo: z.boolean(),
  bestTime: z.string().nullable(), confidence0to1: z.number(),
  seasonStatus: SeasonStatus, mode: SpeciesMode,
  recommendedTechniques: z.array(TechniqueReco),
  avoidTechniques: z.array(AvoidTechnique),
  breakdown: ScoreBreakdown.optional(),
});

export const ReportRequest = z.object({
  spotId: z.string(), species: SpeciesId,
  quantity: z.number().min(1).max(100),
  avgSize: z.string().regex(/^\d+cm$/),
  technique: TechniqueId, bait: BaitId.nullable(),
  notes: z.string().max(500).nullable().optional(),
  photoUrl: z.string().nullable().optional(),
});
```

## Canonical Types — Pydantic (Backend)

```python
from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional

class SpeciesId(str, Enum):
    istavrit="istavrit"; cinekop="cinekop"; sarikanat="sarikanat"
    palamut="palamut"; karagoz="karagoz"; lufer="lufer"
    levrek="levrek"; kolyoz="kolyoz"; mirmir="mirmir"

class TechniqueId(str, Enum):
    capari="capari"; kursun_arkasi="kursun_arkasi"; spin="spin"
    lrf="lrf"; surf="surf"; yemli_dip="yemli_dip"; shore_jig="shore_jig"

class RegionId(str, Enum):
    anadolu="anadolu"; avrupa="avrupa"; city_belt="city_belt"

class SpeciesMode(str, Enum):
    chasing="chasing"; selective="selective"; holding="holding"

class DataQuality(str, Enum):
    live="live"; cached="cached"; fallback="fallback"

class PressureTrend(str, Enum):
    falling="falling"; rising="rising"; stable="stable"

class DecisionMeta(BaseModel):
    contract_version: str = Field(alias="contractVersion")
    generated_at: str = Field(alias="generatedAt")
    timezone: str
    class Config: populate_by_name = True

class DaySummary(BaseModel):
    wind_speed_kmh_min: float = Field(alias="windSpeedKmhMin")
    wind_speed_kmh_max: float = Field(alias="windSpeedKmhMax")
    wind_dir_deg: int = Field(alias="windDirDeg")
    wind_direction_tr: str = Field(alias="windDirectionTR")
    pressure_hpa: float = Field(alias="pressureHpa")
    pressure_change_3h_hpa: float = Field(alias="pressureChange3hHpa")
    pressure_trend: PressureTrend = Field(alias="pressureTrend")
    air_temp_c_min: float = Field(alias="airTempCMin")
    air_temp_c_max: float = Field(alias="airTempCMax")
    sea_temp_c: Optional[float] = Field(alias="seaTempC")
    cloud_cover_pct: Optional[float] = Field(alias="cloudCoverPct")
    wave_height_m: Optional[float] = Field(alias="waveHeightM")
    data_quality: DataQuality = Field(alias="dataQuality")
    data_issues: list[str] = Field(alias="dataIssues")
    class Config: populate_by_name = True

class BestWindow(BaseModel):
    start_local: str = Field(alias="startLocal")
    end_local: str = Field(alias="endLocal")
    score: int = Field(alias="score0to100", ge=0, le=100)
    confidence: float = Field(alias="confidence0to1", ge=0, le=1)
    reasons_tr: list[str] = Field(alias="reasonsTR")
    class Config: populate_by_name = True

class DecisionTarget(BaseModel):
    species_id: str = Field(alias="speciesId")
    species_name_tr: str = Field(alias="speciesNameTR")
    score: int = Field(alias="score0to100", ge=0, le=100)
    confidence: float = Field(alias="confidence0to1", ge=0, le=1)
    mode: SpeciesMode
    best_window_index: Optional[int] = Field(alias="bestWindowIndex")
    class Config: populate_by_name = True

class TechniqueReco(BaseModel):
    technique_id: str = Field(alias="techniqueId")
    technique_name_tr: str = Field(alias="techniqueNameTR")
    setup_hint_tr: Optional[str] = Field(alias="setupHintTR")
    class Config: populate_by_name = True

class AvoidTechnique(BaseModel):
    technique_id: str = Field(alias="techniqueId")
    technique_name_tr: str = Field(alias="techniqueNameTR")
    reason_tr: str = Field(alias="reasonTR")
    class Config: populate_by_name = True

class ReportSignals(BaseModel):
    total_reports: int = Field(alias="totalReports")
    technique_counts: dict[str,int] = Field(alias="techniqueCounts")
    natural_bait_bias: bool = Field(alias="naturalBaitBias")
    notes_tr: Optional[list[str]] = Field(alias="notesTR", default=None)
    class Config: populate_by_name = True

class RecommendedSpot(BaseModel):
    spot_id: str = Field(alias="spotId")
    name_tr: str = Field(alias="nameTR")
    spot_wind_band_min: float = Field(alias="spotWindBandKmhMin")
    spot_wind_band_max: float = Field(alias="spotWindBandKmhMax")
    why_tr: list[str] = Field(alias="whyTR")
    targets: list[DecisionTarget]
    recommended_techniques: list[TechniqueReco] = Field(alias="recommendedTechniques")
    avoid_techniques: list[AvoidTechnique] = Field(alias="avoidTechniques")
    report_signals_24h: Optional[ReportSignals] = Field(alias="reportSignals24h")
    class Config: populate_by_name = True

class RegionDecision(BaseModel):
    region_id: str = Field(alias="regionId")
    recommended_spot: RecommendedSpot = Field(alias="recommendedSpot")
    class Config: populate_by_name = True

class NoGo(BaseModel):
    is_no_go: bool = Field(alias="isNoGo")
    reasons_tr: list[str] = Field(alias="reasonsTR")
    class Config: populate_by_name = True

class DecisionResponse(BaseModel):
    meta: DecisionMeta
    day_summary: DaySummary = Field(alias="daySummary")
    best_windows: list[BestWindow] = Field(alias="bestWindows")
    regions: list[RegionDecision]
    no_go: NoGo = Field(alias="noGo")
    class Config: populate_by_name = True

class ReportCreate(BaseModel):
    spot_id: str = Field(alias="spotId")
    species: SpeciesId
    quantity: int = Field(ge=1, le=100)
    avg_size: str = Field(alias="avgSize", pattern=r"^\d+cm$")
    technique: TechniqueId
    bait: Optional[str] = None
    notes: Optional[str] = Field(default=None, max_length=500)
    photo_url: Optional[str] = Field(alias="photoUrl", default=None)
    class Config: populate_by_name = True
```

---

## Error Format
```json
{"error":{"code":"VALIDATION_ERROR","message":"...","status":422}}
```
Codes: AUTH_REQUIRED(401), PRO_REQUIRED(403), NOT_FOUND(404), VALIDATION_ERROR(422), RATE_LIMIT(429), SERVER_ERROR(500).

## Rate Limiting
Public: 30/min | Free: 60/min | Pro: 120/min
