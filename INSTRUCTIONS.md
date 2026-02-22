# INSTRUCTIONS.md — FishCast Project

> Contract Version: 1.3.2 | 2026-02-22

## Proje
**FishCast** — Istanbul kıyı balıkçıları için veri temelli av karar destek sistemi.
MVP: 3 hafta. Kural motoru balıkçı feedback'iyle agresif iterate edilecek.

## Changelog v1.3.2 (2026-02-22)
- **Health block reason codes**: `reasonsCode[]` (machine), `reasonsTR[]` (Turkish), `reasons` alias (backward compat).
- **Trace guard**: `ALLOW_TRACE_FULL` env var gates `traceLevel=full` in production. Meta shows `traceLevelRequested`/`traceLevelApplied` when downgraded.
- **Telemetry**: Structured JSON logging via `fishcast.telemetry` logger. Event: `decision_generated`.
- **SeasonStatus UI config**: `SEASON_STATUS_CONFIG` in frontend constants.ts. SpeciesScore.tsx config-driven.
- **Smoke script**: `backend/scripts/smoke_decision.py` — 4 offline scenarios.
- **health.py fix**: `rulesCount` 24→31, `rulesetVersion` → `20260222.2`.
- **Runbook**: `docs/RUNBOOK_PROD.md` — endpoints, health interpretation, troubleshooting, telemetry.
- **Ruleset**: 20260222.2

## Changelog v1.3 (2026-02-22)
- **Additive season adjustment**: `seasonMultiplier` (multiplicative) → `seasonAdjustment` (additive). Off-season scores never zeroed.
- **Backward compat**: `breakdown.seasonMultiplier` always 1.0 (deprecated), `breakdown.seasonAdjustment` is authoritative.
- **Shoulder season**: New `"shoulder"` status in SeasonStatus enum.
- **Parça ihtimali**: Off-season + favorable conditions → reduced penalty, `isParca: true`.
- **Config injection (DI)**: All scoring/rules functions accept configs explicitly. `scoring_config.yaml` + `seasonality.yaml` loaded at startup.
- **Rule category caps**: Explicit `category` field per rule. Per-category caps + totalCap=25 with trace data.
- **7 new rules** (total 31): lodos/poyraz water mass effects, pressure falling/rising, summer LRF.
- **Wind normalization**: Single canonical utility `app/utils/wind.py`. 16→8 cardinal mapping.
- **Water mass proxy**: Lodos→warm Marmara, Poyraz→cold Black Sea. Config-driven thresholds.
- **Daylight computation**: `compute_daylight()` via ephem, timezone-safe (`Europe/Istanbul`).
- **Sheltered exceptions**: noGo + `shelteredExceptions[]` for sheltered spots (LRF-only, severe warning).
- **Optional spot fields**: `techniqueSuitability`, `windExposureMap`, `shelteredFrom`, `corridorPotential`, `seasonalHints`.
- **Confidence never 0.0**: Minimum 0.1, even off-season + fallback data.
- **TIER1_SPECIES**: mirmir promoted to Tier 1 (6 species scored).
- **Ruleset**: 20260222.1

## Changelog v1.2
- Decision Output v1: `GET /decision/today` endpoint, canonical contract
- Species Behavior Mode: `chasing|selective|holding` per species-day
- 16 Istanbul merası (regionId: anadolu/avrupa/city_belt) + coord accuracy tracking
- `dataQuality` enum (`live|cached|fallback`) + `dataIssues[]` string array
- `noGo` unified object: `{isNoGo, reasonsTR[]}`
- Rule bonus cap: per-species max +30
- 6 yeni Istanbul-specific rules (toplam 24)
- `windExposure` restructured: `{onshoreDirsDeg[], offshoreDirsDeg[], shelterScore0to1}`
- `modeHint` in rule DSL effects
- `bestWindowIndex` linking targets to windows
- `reportSignals24h` formalized
- `meta.contractVersion` + `meta.timezone` in Decision Output

## Tech Stack
- **Frontend:** Next.js 14 (App Router), TypeScript, Tailwind CSS
- **Maps:** Leaflet.js (OpenStreetMap)
- **Backend:** Python FastAPI (Google Cloud Run)
- **Database:** Firebase Firestore
- **Auth:** Firebase Authentication (Google + Email)
- **Hosting:** Vercel (frontend), GCP Cloud Run (API)
- **Data:** Open-Meteo (hava), Stormglass (su sıcaklığı/dalga), custom solunar (ephem)

## Proje Yapısı
```
fishcast/
├── frontend/src/
│   ├── app/          # page.tsx, spot/[id]/, decision/
│   ├── components/   # map/, score/, decision/, community/, ui/
│   ├── lib/          # api.ts, schemas.ts, types.ts, firebase.ts, constants.ts
│   └── hooks/
├── backend/app/
│   ├── main.py
│   ├── routers/      # scores, spots, reports, health, decision
│   ├── services/     # scoring, weather, solunar, rules, cache, decision, mode
│   ├── models/       # Pydantic models + enums.py
│   └── data/         # spots.json, species.json, rules.yaml, rules_schema.json
├── docs/
└── INSTRUCTIONS.md
```

## Coding Invariants (KRİTİK)

1. **HARDCODE YASAK:** Balıkçılık bilgisi ASLA kodda if/else ile yazılmaz. Spot metadata → `spots.json`, domain kuralları → `rules.yaml`. Kod generic kalır.
2. **Tüm enum'lar TEK canonical listeden gelir** → `API_CONTRACTS.md § Canonical Types`. Her dosya aynı enum'ları kullanır.
3. **MAP→ARRAY transform:** Firestore MAP, API ARRAY. Transform API layer'da. Kuralı `API_CONTRACTS.md § MAP vs ARRAY Transform`'de TEK YERDE tanımlı.
4. **Contract Version bump:** Major feature/schema değişikliğinde version artar, tüm dosyalarda güncellenir.
5. **Koordinat doğruluğu:** approx koordinatlar `accuracy:"approx"` olarak işaretlenmeli. Verified olmayan koordinatı verified olarak sunma.
6. **Zod (frontend) + Pydantic (backend)** → tüm API response'lar validate edilir.
7. **solunar:** HER YERDE ARRAY — `majorPeriods[]`, `minorPeriods[]`.
8. **Fotoğraf:** Client → Firebase Storage → `photoUrl`. Base64 YASAK.
9. **Her score/decision doc:** `meta.contractVersion` zorunlu.
10. **rules.yaml:** Startup JSON Schema validate → geçersiz = crash.

## Decision Output v1 — Özet

> `GET /decision/today` — Ana ürün çıktısı. Full contract: `API_CONTRACTS.md`.

İçerir: `meta` + `daySummary` (koşullar + dataQuality enum + dataIssues) + `bestWindows[]` (2-4) + `regions[]` (3 bölge × mera × türler × teknikler × whyTR) + `noGo` object.

### Species Behavior Mode
- **`chasing`** — Aktif, lure etkili
- **`selective`** — Seçici, doğal yem tercih
- **`holding`** — Pasif, dip/yavaş teknikler

Derivation: `SCORING_ENGINE.md § Mode Derivation`. MVP heuristic — bilimsel kesinlik iddiası yok.

## Units Table (KANONİK — Tek Kaynak)

| Canonical Name | Unit | Provider |
|---------------|------|----------|
| `windSpeedKmh` | km/h | Open-Meteo |
| `windDirDeg` | 0-359° | Open-Meteo |
| `windDirectionTR` | enum string | Derived |
| `windDirectionCardinal` | "N","NE" etc | Derived |
| `pressureHpa` | hPa | Open-Meteo |
| `pressureChange3hHpa` | hPa | Computed |
| `airTempC` | °C | Open-Meteo |
| `seaTempC` | °C | Stormglass |
| `waveHeightM` | m | Stormglass |
| `cloudCoverPct` | 0-100% | Open-Meteo |

> Normalization: `services/weather.py` tek noktada. m/s→km/h: ×3.6, °F→°C: (F-32)×5/9.

## Wind Direction Derivation
```python
def deg_to_cardinal(deg: float) -> str:
    dirs = ["N","NE","E","SE","S","SW","W","NW"]
    return dirs[round(deg / 45) % 8]

CARDINAL_TO_TR = {
    "N":"yıldız","NE":"poyraz","E":"gün_doğusu","SE":"kıble",
    "S":"keşişleme","SW":"lodos","W":"gün_batısı","NW":"karayel"
}
```

## MVP Tür Listesi

### Tier 1 (6 tür — skorlanır + mode)
| ID | Ad | Sezon |
|----|----|-------|
| `istavrit` | İstavrit | Yıl boyu (pik Eyl-Kas) |
| `cinekop` | Çinekop | Eyl-Ara |
| `sarikanat` | Sarıkanat | Eyl-Ara |
| `palamut` | Palamut | Ağu-Kas |
| `karagoz` | Karagöz | Yıl boyu |
| `mirmir` | Mirmir | Yıl boyu (v1.3'te Tier 1'e terfi) |

### Tier 2 — v1.1
`lufer`, `levrek`, `kolyoz`

## Teknikler (7)
| ID | Ad |
|----|----|
| `capari` | Çapari |
| `kursun_arkasi` | Kurşun Arkası |
| `spin` | Spin |
| `lrf` | LRF |
| `surf` | Surf |
| `yemli_dip` | Yemli Dip |
| `shore_jig` | Shore Jig |

## MVP Istanbul Meralar (16)

### Region IDs
| regionId | Açıklama |
|----------|----------|
| `avrupa` | Boğaz Avrupa (Tarabya→Boyacıköy + Baltalimanı) |
| `city_belt` | Tarihi yarımada + Karaköy (Sarayburnu→Galata) |
| `anadolu` | Boğaz Anadolu (Kandilli→Selvi) |

> Full spot dataset with coords: `ARCHITECTURE.md § Spots Dataset`.

## Rüzgar Skalası
| km/h | Skor | Durum |
|------|------|-------|
| 0-5 | 65 | Sakin |
| 5-15 | 90 | İDEAL |
| 15-25 | 75 | Sert |
| 25-35 | 40 | Zor |
| 35+ | 0 | NO-GO |

> NO-GO tek kaynak: `nogo_extreme_wind` rule (rules.yaml, priority 10). `SCORING_ENGINE.md § NO-GO Single Authority`.

## Kod Standartları
1. TypeScript strict — `any` YASAK
2. JSDoc/docstring her fonksiyona
3. Component max 150 satır
4. Zod validate (frontend), Pydantic (backend)
5. Error handling + Türkçe mesaj
6. Türkçe UI, İngilizce kod
7. Git: `feat:`, `fix:`, `refactor:`, `docs:`, `data:`
8. Istanbul bilgisi kodda HARDCODE YASAK

## Referanslar
- `docs/ARCHITECTURE.md` — Firestore şeması, spot metadata, data source policy
- `docs/SCORING_ENGINE.md` — Ağırlıklar, 31 kural, mode derivation, NO-GO authority, category caps
- `docs/API_CONTRACTS.md` — Decision Output v1, canonical types, MAP→ARRAY transform
- `docs/TASKS.md` — 3 haftalık MVP + golden fixtures
