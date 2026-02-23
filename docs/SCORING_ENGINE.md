# SCORING_ENGINE.md — FishCast Skor Motoru

> Contract Version: 1.4.2 | 2026-02-23

## Formül (v1.3 — Additive Season)
```
weighted_sum = Σ(ağırlık_i × param_skor_i)          # 0.0–1.0
season_adj   = compute_season_adjustment(species, month, weighted_sum)  # additive int
capped_bonus = category_capped_rule_bonus(species)   # see § Category Caps

TürSkoru = clamp(0, 100,
    round(weighted_sum × 100 + season_adj) + capped_bonus
)
```

> **v1.2→v1.3 breaking change:** `sezon_çarpanı` (multiplicative, 0.0/1.0/1.2) replaced with `season_adj` (additive int). Off-season scores are **never zeroed** — they get a negative adjustment (e.g. -22) but remain positive.
>
> **Rule bonus cap:** Per-category caps + totalCap=25. See § Category Caps.
> **Final clamp:** Her tür skoru [0, 100] aralığına sıkıştırılır.
> **Backward compat:** `breakdown.seasonMultiplier` always 1.0 (deprecated). `breakdown.seasonAdjustment` is the authoritative additive value.

## Tür-Özel Ağırlıklar (toplam 1.0)

| Param | İstavrit | Çinekop | Sarıkanat | Palamut | Karagöz |
|-------|----------|---------|-----------|---------|---------|
| Basınç | 0.15 | 0.25 | 0.25 | 0.20 | 0.15 |
| Rüzgar | 0.20 | 0.20 | 0.20 | 0.20 | 0.15 |
| Su sıcaklığı | 0.25 | 0.15 | 0.15 | 0.20 | 0.20 |
| Solunar | 0.20 | 0.20 | 0.20 | 0.20 | 0.25 |
| Zaman | 0.20 | 0.20 | 0.20 | 0.20 | 0.25 |

---

## Parametre Skorları (0.0–1.0)

### 1. Basınç
```python
def pressure_score(hpa, change_3h):
    if 1010 <= hpa <= 1020: base = 1.0
    elif 1005 <= hpa < 1010 or 1020 < hpa <= 1025: base = 0.7
    elif 1000 <= hpa < 1005 or 1025 < hpa <= 1030: base = 0.4
    else: base = 0.2
    if change_3h < -2: base = min(1, base + 0.3)
    elif change_3h < -1: base = min(1, base + 0.15)
    elif change_3h > 2: base = max(0, base - 0.2)
    return base
```

### 2. Rüzgar
```python
def wind_score(kmh, dir_deg, shore):
    if kmh < 5: base = 0.65
    elif kmh <= 15: base = 0.90
    elif kmh <= 25: base = 0.75
    elif kmh <= 35: base = 0.40
    else: return 0.0  # triggers NO-GO via rule
    cardinal = deg_to_cardinal(dir_deg)
    if kmh >= 25:
        if cardinal in ["NE","N"] and shore == "anatolian": base -= 0.15
        elif cardinal in ["NE","N"] and shore == "european": base += 0.08
        elif cardinal in ["SW","S"] and shore == "european": base -= 0.15
        elif cardinal in ["SW","S"] and shore == "anatolian": base += 0.05
    return max(0, min(1, base))
```

### 3. Su Sıcaklığı
```python
SPECIES_TEMP = {
    "istavrit":{"min":10,"max":22,"pen":20}, "cinekop":{"min":12,"max":20,"pen":20},
    "sarikanat":{"min":12,"max":20,"pen":20}, "palamut":{"min":14,"max":22,"pen":20},
    "karagoz":{"min":10,"max":26,"pen":10},
}
MONTHLY_SEA_TEMP = {1:9,2:8,3:9,4:11,5:15,6:20,7:24,8:25,9:23,10:19,11:15,12:11}
```

### 4. Solunar
Major period=1.0, approaching major=0.7, minor period=0.7, outside=0.3+moon_bonus.

### 5. Zaman
Species-specific best hours. Night bonus: karagöz +0.3, levrek +0.3.

## Season Adjustment (v1.3 — Additive)

Config-driven via `seasonality.yaml`. Per-species entries define:
- `peakMonths`, `peakAdjustment` (e.g. +15)
- `shoulderMonths`, `shoulderAdjustment` (e.g. +5)
- `offMonths`, `offAdjustment` (e.g. -25)
- `offFloor` (minimum score contribution, e.g. 8)
- `parcaConditionThreshold` (weighted_sum threshold for parça ihtimali)
- `parcaPenaltyReduction` (penalty reduction when parça triggers)
- `confidenceImpact` per status (0.0 for peak, 0.35 for off)

**Parça Behavior:** Off-season + high weighted_sum → penalty reduced. "Parça ihtimali" flag set.

**Season statuses:** `"peak"`, `"shoulder"` (NEW v1.3), `"active"`, `"off"` (v1.3.1: canonical, replaces "closed" mapping).
`"off"` = off-season (fish catchable via parça). `"closed"` retained in enum for backward compat but no longer emitted by scoring engine.

> **DEPRECATED:** `seasonMultiplier` always returns 1.0 in breakdown. Use `seasonAdjustment` instead.

---

## Mode Derivation (MVP Heuristic)

> Bilimsel kesinlik iddiası yok. Balıkçı feedback'iyle iterate edilecek.

```python
def derive_mode(species, weather, solunar, spot, report_signals=None):
    """
    Returns: "chasing" | "selective" | "holding"

    Inputs:
        weather: {pressureTrend, pressureChange3hHpa, windSpeedKmh, windDirDeg}
        solunar: {solunarRating: 0-1}
        spot: {windExposure: {onshoreDirsDeg[], shelterScore0to1}}
        report_signals: {naturalBaitBias: bool} | None
    """
    # P1: Report signals override (last 24h community data)
    if report_signals and report_signals.get("naturalBaitBias"):
        if species in ["cinekop", "sarikanat", "lufer"]:
            return "selective"

    # P2: Extreme conditions → holding
    if weather.windSpeedKmh > 25:
        return "holding"
    if abs(weather.pressureChange3hHpa) > 3:
        return "holding"

    # P3: Onshore wind check (species sensitive to exposure)
    is_onshore = weather.windDirDeg in range_match(spot.windExposure.onshoreDirsDeg)
    if is_onshore and weather.windSpeedKmh > 15 and spot.windExposure.shelterScore0to1 < 0.4:
        if species in ["cinekop", "sarikanat"]:
            return "holding"

    # P4: Good solunar + stable → chasing
    if solunar.solunarRating >= 0.6 and weather.pressureTrend == "stable":
        return "chasing"
    if solunar.solunarRating >= 0.8:
        return "chasing"

    # P5: Falling pressure → selective for çinekop/sarıkanat
    if weather.pressureTrend == "falling" and weather.pressureChange3hHpa < -1:
        if species in ["cinekop", "sarikanat"]:
            return "selective"
        return "chasing"

    # P6: Rising pressure → holding
    if weather.pressureTrend == "rising" and weather.pressureChange3hHpa > 1:
        return "holding"

    return "chasing"  # default
```

### Mode → Technique Impact
| Mode | Lure | Bait | Etkisi |
|------|------|------|--------|
| chasing | Önerilir | Çalışır | Normal scoring |
| selective | avoidTechniques | Tercih edilir | Spin/shore_jig → avoidTechniques |
| holding | Kaçın | Yavaş teknikler | Sadece yemli_dip/surf |

---

## Confidence Computation (v1.3)

Config-driven via `scoring_config.yaml["confidenceFactors"]`.

```python
def compute_confidence(data_quality, has_reports_24h, season_status,
                       season_confidence_impact, scoring_config,
                       coord_accuracy="approx", fired_rules_count=0):
    factors = scoring_config["confidenceFactors"]
    base = factors["dataQualityBase"][data_quality]      # live=0.9, cached=0.7, fallback=0.5
    if has_reports_24h:
        base += factors["reportBoost"]                    # +0.1
    if coord_accuracy == "approx":
        base -= factors.get("approxCoordPenalty", 0.05)   # -0.05
    base -= season_confidence_impact                      # off=0.35, shoulder=0.1, peak=0.0
    return max(0.1, round(base, 2))                       # NEVER 0.0
```

> **v1.3:** Confidence **never returns 0.0** (min 0.1). Off-season reduces confidence but does not eliminate it.

---

## NO-GO — Single Authority

> NO-GO'nun TEK kaynağı rule engine'dir. Kodda ayrı bir `if windSpeed >= 35` YOKTUR.

Kural: `nogo_extreme_wind` (priority 10, rules.yaml). Bu kural match ettiğinde:
1. `noGo.isNoGo = true`
2. `noGo.reasonsTR = [rule.messageTR]`
3. `overallScore = 0`
4. Tür skorları yine hesaplanır (explanation amaçlı), `suppressedByNoGo = true`

E�er gelecekte başka NO-GO tetikleyicileri eklenecekse, yeni bir rule yazılır (priority 10). Kod DEĞİŞMEZ.

---

## Rule Engine DSL

### Operators
| Op | Syntax | Example |
|----|--------|---------|
| >= | `">=35"` | `windSpeedKmh: ">=35"` |
| < | `"<14"` | `seaTempC: "<14"` |
| range | `[min,max]` | `windSpeedKmh_range: [3,8]` |
| time | `"HH:MM-HH:MM"` | `time: "20:00-05:00"` (wraps midnight) |
| months | `[int]` | `month: [9,10,11]` |
| string | `"val"` | `spot: "kandilli"` |
| list OR | `["a","b"]` | `windDirectionCardinal: ["NE","N"]` |
| regionId | `"id"` | `regionId: "city_belt"` |
| bool | `true` | `pelagicCorridor: true` |

All condition fields are AND'd. Lists are OR within field.

### Rule Schema (v1.4.2)
```yaml
- id: string               # unique, snake_case
  enabled: true             # NEW v1.4.2: optional, default true. Set false to disable rule.
  disableReason: null       # NEW v1.4.2: optional string explaining why disabled.
  condition: {}             # all AND'd
  effects:
    - applyToSpecies: ["*"] | ["species_id", ...]
      scoreBonus: int       # capped per-category + totalCap
      techniqueHints: []    # optional
      removeFromTechniques: [] # optional
      modeHint: null        # optional: "chasing"|"selective"|"holding"
      noGo: false           # optional
  messageTR: string
  priority: 1-10
  category: string          # "absolute"|"windCoast"|"weatherMode"|"istanbul"|"techniqueTime"
```

### Disabled Rules (v1.4.2)
Rules with `enabled: false` are skipped during evaluation. They remain in rules.yaml for tracking and are counted in `/_meta.disabledRulesCount`. Currently 3 disabled:
- `post_poyraz_migration` — wind_history_48h data source not implemented
- `after_rain_bonus` — rain data not yet integrated from Open-Meteo
- `strong_current_warning` — Bosphorus current_speed API (SHOD) pending

### Rule Categories (v1.3)
| Category | Priority Range | Description |
|----------|---------------|-------------|
| `absolute` | 10 | NoGo triggers, hard constraints |
| `windCoast` | 9 | Shore-specific wind effects |
| `weatherMode` | 7-8 | Pressure, temperature, water mass |
| `istanbul` | 5-6 | Istanbul-specific spot/corridor rules |
| `techniqueTime` | 4-5 | Time-of-day technique recommendations |

### Category Caps (v1.3)
Per-species bonus capping from `scoring_config.yaml["ruleBonusCaps"]`:
```yaml
ruleBonusCaps:
  windCoastRules: 12
  weatherModeRules: 15
  istanbulRules: 10
  techniqueTimeRules: 8
  totalCap: 25
```

1. Group fired rule bonuses by `category` per species.
2. Apply per-category cap (e.g., windCoast max 12).
3. Sum capped **positive** categories → apply totalCap (25) to positives only.
4. Negative bonuses **floored at -20** (v1.4.2): `final = min(totalCap, Σpos_capped) + max(negativeFloor, Σneg)`.
5. Trace data stored: `category_raw_bonuses`, `category_capped_bonuses`, `positive_total_raw`, `positive_total_capped`, `negative_total`, `final_rule_bonus`.

### Conflict Resolution
1. All matching rules fire (no short-circuit).
2. `scoreBonus`: summed per species per category, category-capped, then totalCap'd.
3. `techniqueHints`: merged, deduped, priority-ordered.
4. `removeFromTechniques`: applied after merge.
5. `modeHint`: highest priority wins. Same priority → alphabetical first.
6. `messageTR`: concatenated " | ", priority DESC.
7. `noGo`: any true → NO-GO.

### Startup Validation
`rules.yaml` validated against `rules_schema.json` at boot. Invalid → app crash with error.

### New Condition Fields (v1.3)
| Field | Type | Source |
|-------|------|--------|
| `isDaylight` | bool | `compute_daylight()` via ephem |
| `waterMassProxy` | string | `"lodos"\|"poyraz"\|"neutral"` from wind + config |
| `waterMassStrength` | float | 0.0–1.0, linear between weak/strong thresholds |
| `shelteredFrom` | list[str] | From spot data, 8-cardinal directions |

### Wind Normalization (v1.3)
Single canonical utility: `app/utils/wind.py`
- `degrees_to_cardinal_8(deg)` — 0→N, 45→NE, 90→E, ...
- `normalize_cardinal_8(card)` — NNE→NE, WSW→SW, ...

### Water Mass Proxy (v1.3, graded v1.4.2)
Lodos (SW/S) pushes warm Marmara water into Bosphorus → palamut favorable.
Poyraz (NE/N) pushes cold Black Sea water → bluefish (cinekop/sarıkanat) favorable.
Config: `scoring_config.yaml["waterMassProxy"]`.

**Graded Effect (v1.4.2):** Water mass proxy rules now scale bonus by `waterMassStrength` (0.0–1.0). A light poyraz gives proportionally less bonus than a strong one. Formula: `score_bonus = round(raw_bonus × wm_strength)`.

### 31 Rules (28 active + 3 disabled)

```yaml
# === ABSOLUTE (Priority 10) === [category: absolute]
- id: "nogo_extreme_wind"
  condition: {windSpeedKmh: ">=35"}
  effects: [{applyToSpecies: ["*"], scoreBonus: 0, noGo: true}]
  messageTR: "DİKKAT: 35+ km/h — kıyıdan avlanılamaz!"
  priority: 10

- id: "karagoz_never_spin"
  condition: {species_in_context: ["karagoz"]}
  effects: [{applyToSpecies: ["karagoz"], scoreBonus: 0, removeFromTechniques: ["spin"]}]
  messageTR: "Karagöz spin ile tutulmaz — LRF/yemli dip dene."
  priority: 10

# === WIND + SHORE (Priority 9) ===
- id: "poyraz_anatolian_penalty"
  condition: {windDirectionCardinal: ["NE","N"], windSpeedKmh: ">=25", shore: "anatolian"}
  effects: [{applyToSpecies: ["*"], scoreBonus: -15}]
  messageTR: "Kuvvetli poyraz — Anadolu yakası dalgalı."
  priority: 9

- id: "poyraz_european_bonus"
  condition: {windDirectionCardinal: ["NE","N"], windSpeedKmh: ">=25", shore: "european"}
  effects: [{applyToSpecies: ["*"], scoreBonus: 8}]
  messageTR: "Poyraz — Avrupa yakası korunaklı."
  priority: 9

- id: "lodos_european_penalty"
  condition: {windDirectionCardinal: ["SW","S"], windSpeedKmh: ">=25", shore: "european"}
  effects: [{applyToSpecies: ["*"], scoreBonus: -15}]
  messageTR: "Lodos — Avrupa yakası bulanık."
  priority: 9

- id: "lodos_anatolian_bonus"
  condition: {windDirectionCardinal: ["SW","S"], windSpeedKmh: ">=25", shore: "anatolian"}
  effects: [{applyToSpecies: ["*"], scoreBonus: 5}]
  messageTR: "Lodos — Anadolu yakası sakin."
  priority: 9

# === WEATHER + MODE (Priority 7-8) ===
- id: "pressure_drop_evening"
  condition: {pressureChange3hHpa: "<-1", time: "16:00-20:00"}
  effects: [{applyToSpecies: ["lufer","cinekop"], scoreBonus: 15}]
  messageTR: "Basınç düşüşü + akşam = av patlaması!"
  priority: 8

- id: "cinekop_selective_day"
  condition: {pressureChange3hHpa: "<-1.5"}
  effects: [{applyToSpecies: ["cinekop","sarikanat"], scoreBonus: 0, modeHint: "selective", techniqueHints: ["yemli_dip","kursun_arkasi"], removeFromTechniques: ["spin"]}]
  messageTR: "Basınç düşüşü — çinekop seçici, doğal yem tercih et."
  priority: 7

- id: "cinekop_bait_fallback"
  condition: {seaTempC: "<14"}
  effects: [{applyToSpecies: ["cinekop","sarikanat"], scoreBonus: 0, techniqueHints: ["yemli_dip","kursun_arkasi"], removeFromTechniques: ["spin"], modeHint: "selective"}]
  messageTR: "Soğuk su — çinekop/sarıkanat yeme geç."
  priority: 7

- id: "post_poyraz_migration"            # DISABLED: wind_history_48h not available
  enabled: false
  condition: {wind_history_48h: "poyraz"}
  effects: [{applyToSpecies: ["palamut","cinekop"], scoreBonus: 10}]
  messageTR: "Poyraz sonrası göç — palamut/çinekop giriyor!"
  priority: 7

- id: "lodos_sarayburnu_palamut"
  condition: {windDirectionCardinal: ["S","SW"], spot: "sarayburnu"}
  effects: [{applyToSpecies: ["palamut"], scoreBonus: 20, techniqueHints: ["capari","spin"], modeHint: "chasing"}]
  messageTR: "Sarayburnu lodos = palamut patlar!"
  priority: 7

- id: "after_rain_bonus"                  # DISABLED: rain data not yet integrated
  enabled: false
  condition: {after_rain: true, hours_since_rain: "<=24"}
  effects: [{applyToSpecies: ["levrek"], scoreBonus: 12}, {applyToSpecies: ["karagoz"], scoreBonus: 8}]
  messageTR: "Yağmur sonrası — levrek/karagöz aktif!"
  priority: 6

- id: "full_moon_night_levrek"
  condition: {moon_illumination: ">90", isDaylight: false}    # v1.4.2: isDaylight replaces time range
  effects: [{applyToSpecies: ["levrek"], scoreBonus: 18, techniqueHints: ["shore_jig","yemli_dip"]}]
  messageTR: "Dolunay gecesi — levrek altın saati!"
  priority: 6

- id: "kandilli_lufer_center"
  condition: {spot: "kandilli", month: [9,10,11]}
  effects: [{applyToSpecies: ["lufer","cinekop","sarikanat"], scoreBonus: 15, techniqueHints: ["spin","kursun_arkasi"]}]
  messageTR: "Kandilli lüfer merkezi."
  priority: 6

# === TIME + TECHNIQUE (Priority 4-5) ===
- id: "night_lrf_golden"
  condition: {isDaylight: false, windSpeedKmh_range: [3,8]}    # v1.4.2: isDaylight replaces time range
  effects: [{applyToSpecies: ["istavrit","karagoz","mirmir"], scoreBonus: 0, techniqueHints: ["lrf"]}]
  messageTR: "LRF altın saati!"
  priority: 5

- id: "bebek_night_levrek"
  condition: {spot: "bebek", isDaylight: false}                 # v1.4.2: isDaylight replaces time range
  effects: [{applyToSpecies: ["levrek"], scoreBonus: 12, techniqueHints: ["shore_jig","lrf","yemli_dip"]}]
  messageTR: "Bebek gece levrek merkezi."
  priority: 5

- id: "cold_water_deep_istavrit"
  condition: {seaTempC: "<10", month: [12,1,2,3]}
  effects: [{applyToSpecies: ["istavrit"], scoreBonus: -10, techniqueHints: ["capari"]}]
  messageTR: "Soğuk su — istavrit derine indi, ağır çapari."
  priority: 5

- id: "spin_morning_wtd"
  condition: {time: "05:00-07:00"}
  effects: [{applyToSpecies: ["lufer","palamut"], scoreBonus: 0, techniqueHints: ["spin"]}]
  messageTR: "WTD surface lure — sabah yüzeyde avlanırlar."
  priority: 4

- id: "strong_current_warning"             # DISABLED: current_speed API pending
  enabled: false
  condition: {current_speed: ">=4"}
  effects: [{applyToSpecies: ["*"], scoreBonus: 0}]
  messageTR: "Akıntı güçlü — sinker artır."
  priority: 4

# === ISTANBUL-SPECIFIC (Priority 5-6) ===
- id: "pelagic_corridor_chasing"
  condition: {pelagicCorridor: true, month: [9,10,11]}
  effects: [{applyToSpecies: ["palamut","cinekop","sarikanat"], scoreBonus: 8, modeHint: "chasing"}]
  messageTR: "Pelajik koridor aktif — göçmen türler geçiyor!"
  priority: 6

- id: "city_belt_istavrit_sunset"
  condition: {regionId: "city_belt", time: "16:00-19:00"}
  effects: [{applyToSpecies: ["istavrit"], scoreBonus: 10, techniqueHints: ["capari","yemli_dip"], modeHint: "chasing"}]
  messageTR: "Şehir hattı akşam üstü — çapari ile istavrit garantili!"
  priority: 5

- id: "levrek_onshore_wind_bonus"
  condition: {windSpeedKmh_range: [8,20], shore: "european", windDirectionCardinal: ["SW","S"]}
  effects: [{applyToSpecies: ["levrek"], scoreBonus: 10, modeHint: "chasing"}]
  messageTR: "Kıyıya vuran lodos = levrek aktifleşir."
  priority: 6

- id: "wind_safety_band_warning"
  condition: {windSpeedKmh: ">=25"}
  effects: [{applyToSpecies: ["*"], scoreBonus: 0}]
  messageTR: "Rüzgar güçlü — mera seçiminde rüzgara korunaklı noktaları tercih et."
  priority: 5

- id: "night_rocky_karagoz"
  condition: {isDaylight: false, features_include: "kayalık"}   # v1.4.2: isDaylight replaces time range
  effects: [{applyToSpecies: ["karagoz"], scoreBonus: 8, techniqueHints: ["lrf","yemli_dip"], removeFromTechniques: ["spin","capari","shore_jig"]}]
  messageTR: "Gece kayalık — karagöz LRF/yemli dip ile, spin/çapari kaçın."
  priority: 5
  category: istanbul

# === NEW v1.3 RULES ===

- id: "lodos_palamut_water_boost"
  condition: {waterMassProxy: "lodos", waterMassStrength: ">=0.3"}
  effects: [{applyToSpecies: ["palamut"], scoreBonus: 10, modeHint: "chasing"}]
  messageTR: "Lodos sıcak Marmara suyu getiriyor — palamut aktif!"
  priority: 7
  category: weatherMode

- id: "lodos_bluefish_water_penalty"
  condition: {waterMassProxy: "lodos", waterMassStrength: ">=0.3"}
  effects: [{applyToSpecies: ["cinekop","sarikanat"], scoreBonus: -8}]
  messageTR: "Lodos sıcak su — çinekop/sarıkanat pasifleşiyor."
  priority: 7
  category: weatherMode

- id: "poyraz_bluefish_water_boost"
  condition: {waterMassProxy: "poyraz", waterMassStrength: ">=0.3"}
  effects: [{applyToSpecies: ["cinekop","sarikanat"], scoreBonus: 10, modeHint: "chasing"}]
  messageTR: "Poyraz soğuk Karadeniz suyu — çinekop/sarıkanat hareketleniyor!"
  priority: 7
  category: weatherMode

- id: "poyraz_palamut_water_penalty"
  condition: {waterMassProxy: "poyraz", waterMassStrength: ">=0.3"}
  effects: [{applyToSpecies: ["palamut"], scoreBonus: -5}]
  messageTR: "Poyraz soğuk su — palamut yavaşlıyor."
  priority: 7
  category: weatherMode

- id: "pressure_falling_aggressive"
  condition: {pressureTrend: "falling", pressureChange3hHpa: "<-1.5"}
  effects: [{applyToSpecies: ["*"], scoreBonus: 5, modeHint: "chasing", techniqueHints: ["spin","kursun_arkasi"]}]
  messageTR: "Basınç hızla düşüyor — aktif avlanma zamanı!"
  priority: 7
  category: weatherMode

- id: "pressure_rising_passive"
  condition: {pressureTrend: "rising", pressureChange3hHpa: ">1.5"}
  effects: [{applyToSpecies: ["*"], scoreBonus: -3, modeHint: "holding", techniqueHints: ["yemli_dip"]}]
  messageTR: "Basınç yükseliyor — balık pasif, dip tekniği tercih et."
  priority: 7
  category: weatherMode

- id: "summer_low_wind_lrf"
  condition: {month: [6,7,8], windSpeedKmh: "<=10"}
  effects: [{applyToSpecies: ["istavrit","karagoz","mirmir"], scoreBonus: 5, techniqueHints: ["lrf"]}]
  messageTR: "Yaz sakin — LRF ile küçük balık avı ideal!"
  priority: 5
  category: techniqueTime
```

## Sheltered Exceptions (v1.3)

When noGo triggers (wind >= 35 km/h), sheltered spots are listed as exceptions:
- Check each spot's `shelteredFrom[]` against normalized wind cardinal
- If sheltered → add to `noGo.shelteredExceptions[]`
- Each entry: `{spotId, allowedTechniques: ["lrf"], warningLevel: "severe", messageTR}`
- Only LRF allowed at sheltered spots during noGo

## Dependency Injection (v1.3)

All scoring/rules functions accept configs explicitly — no module-level globals.
- `scoring_config`: loaded from `scoring_config.yaml` at startup → `app.state.scoring_config`
- `seasonality_config`: loaded from `seasonality.yaml` at startup → `app.state.seasonality_config`
- Configs validated at startup (species keys must match SpeciesId enum)

## Ruleset Versioning
Format: `"YYYYMMDD.N"`. Current: `20260223.1`. Her score/decision doc'ta `meta` içinde. Git revert ile rollback.

## Trace Guard (v1.3.2)

Env var `ALLOW_TRACE_FULL` (default `"false"`) gates `traceLevel=full` in production:
- When `false`: `full` requests downgraded to `minimal`
- Meta includes `traceLevelRequested` / `traceLevelApplied` when downgraded
- `none` and `minimal` always allowed regardless of env

## Telemetry (v1.3.2)

Structured JSON logging via `fishcast.telemetry` logger after each `generate_decision()`:
- Event: `decision_generated`
- Fields: contractVersion, healthStatus, dataQuality, noGo, topSpecies[:3], latencyMs, regionCount
- Compatible with Cloud Run structured logging (jsonPayload)

## Testing
1. Per-rule: min 1 test / kural
2. Determinism: same input → same output
3. Mode: golden fixtures (4 scenarios) — `TASKS.md § Golden Fixtures`
4. Category caps: per-category + totalCap enforced with trace
5. Startup: rules.yaml JSON Schema → invalid = crash
6. Contract compat: dual-field (seasonAdjustment + seasonMultiplier), no zero scores
7. Wind normalization: 8-cardinal and 16→8 mapping
8. Daylight: timezone-safe Istanbul compute
9. Health block: reasonsCode + reasonsTR + reasons alias (v1.3.2)
10. Trace guard: blocked/allowed/meta shows downgrade (v1.3.2)
11. Smoke script: 4 offline scenarios — `backend/scripts/smoke_decision.py`
