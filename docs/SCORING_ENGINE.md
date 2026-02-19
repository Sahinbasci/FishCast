# SCORING_ENGINE.md — FishCast Skor Motoru

> Contract Version: 1.2 | 2026-02-19

## Formül
```
TürSkoru = clamp(0, 100,
    round(Σ(ağırlık_i × param_skor_i) × 100 × sezon_çarpanı)
    + min(30, Σ(kural_bonusu))
)
```

> **Rule bonus cap:** Per-species max **+30 puan**. Negatif bonuslar cap'lenmez.
> **Final clamp:** Her tür skoru [0, 100] aralığına sıkıştırılır.

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

## Sezon Çarpanı
out_of_season=0.0, in_season=1.0, peak=1.2.

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

## Confidence Computation

```python
def compute_confidence(data_quality, has_reports_24h, season_mult):
    """
    Simple, stable confidence formula.
    Returns: float 0.0-1.0
    """
    base = {"live": 0.9, "cached": 0.7, "fallback": 0.5}[data_quality]
    if has_reports_24h:
        base = min(1.0, base + 0.1)
    if season_mult == 0:
        return 0.0  # off-season
    if season_mult < 1.0:
        base *= 0.9  # slight penalty for non-peak
    return round(base, 2)
```

> Basit ve stabil. Overcomplexity yok. `dataQuality` enum direkt kullanılır.

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

### Rule Schema
```yaml
- id: string               # unique, snake_case
  condition: {}             # all AND'd
  effects:
    - applyToSpecies: ["*"] | ["species_id", ...]
      scoreBonus: int       # capped at +30 per species (summed across rules)
      techniqueHints: []    # optional
      removeFromTechniques: [] # optional
      modeHint: null        # optional: "chasing"|"selective"|"holding"
      noGo: false           # optional
  messageTR: string
  priority: 1-10
```

### Conflict Resolution
1. All matching rules fire (no short-circuit).
2. `scoreBonus`: summed per species, then capped at +30.
3. `techniqueHints`: merged, deduped, priority-ordered.
4. `removeFromTechniques`: applied after merge.
5. `modeHint`: highest priority wins. Same priority → alphabetical first.
6. `messageTR`: concatenated " | ", priority DESC.
7. `noGo`: any true → NO-GO.

### Startup Validation
`rules.yaml` validated against `rules_schema.json` at boot. Invalid → app crash with error.

### 24 Rules

```yaml
# === ABSOLUTE (Priority 10) ===
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

- id: "post_poyraz_migration"
  condition: {wind_history_48h: "poyraz"}
  effects: [{applyToSpecies: ["palamut","cinekop"], scoreBonus: 10}]
  messageTR: "Poyraz sonrası göç — palamut/çinekop giriyor!"
  priority: 7

- id: "lodos_sarayburnu_palamut"
  condition: {windDirectionCardinal: ["S","SW"], spot: "sarayburnu"}
  effects: [{applyToSpecies: ["palamut"], scoreBonus: 20, techniqueHints: ["capari","spin"], modeHint: "chasing"}]
  messageTR: "Sarayburnu lodos = palamut patlar!"
  priority: 7

- id: "after_rain_bonus"
  condition: {after_rain: true, hours_since_rain: "<=24"}
  effects: [{applyToSpecies: ["levrek"], scoreBonus: 12}, {applyToSpecies: ["karagoz"], scoreBonus: 8}]
  messageTR: "Yağmur sonrası — levrek/karagöz aktif!"
  priority: 6

- id: "full_moon_night_levrek"
  condition: {moon_illumination: ">90", time: "21:00-03:00"}
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
  condition: {time: "20:00-00:00", windSpeedKmh_range: [3,8]}
  effects: [{applyToSpecies: ["istavrit","karagoz","mirmir"], scoreBonus: 0, techniqueHints: ["lrf"]}]
  messageTR: "LRF altın saati!"
  priority: 5

- id: "bebek_night_levrek"
  condition: {spot: "bebek", time: "20:00-05:00"}
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

- id: "strong_current_warning"
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
  condition: {time: "20:00-05:00", features_include: "kayalık"}
  effects: [{applyToSpecies: ["karagoz"], scoreBonus: 8, techniqueHints: ["lrf","yemli_dip"], removeFromTechniques: ["spin","capari","shore_jig"]}]
  messageTR: "Gece kayalık — karagöz LRF/yemli dip ile, spin/çapari kaçın."
  priority: 5
```

## Ruleset Versioning
Format: `"YYYYMMDD.N"`. Her score/decision doc'ta `meta` içinde. Git revert ile rollback.

## Testing
1. Per-rule: min 1 test / kural
2. Determinism: same input → same output
3. Mode: golden fixtures (3 gün) — `TASKS.md § Golden Fixtures`
4. Bonus cap: no species exceeds +30 from rules
5. Startup: rules.yaml JSON Schema → invalid = crash
