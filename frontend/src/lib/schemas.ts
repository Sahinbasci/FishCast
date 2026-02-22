/**
 * FishCast Zod schemas — API_CONTRACTS.md canonical types.
 * Single source of truth for frontend validation.
 */

import { z } from "zod";

// === ENUMS ===
export const SpeciesId = z.enum([
  "istavrit", "cinekop", "sarikanat", "palamut", "karagoz",
  "lufer", "levrek", "kolyoz", "mirmir",
]);
export const TechniqueId = z.enum([
  "capari", "kursun_arkasi", "spin", "lrf", "surf", "yemli_dip", "shore_jig",
]);
export const BaitId = z.enum([
  "istavrit_fileto", "krace_fileto", "hamsi_fileto", "karides",
  "midye", "deniz_kurdu", "boru_kurdu", "mamun",
]);
export const Shore = z.enum(["european", "anatolian"]);
export const RegionId = z.enum(["anadolu", "avrupa", "city_belt"]);
export const SpeciesMode = z.enum(["chasing", "selective", "holding"]);
export const DataQuality = z.enum(["live", "cached", "fallback"]);
export const PressureTrend = z.enum(["falling", "rising", "stable"]);
export const SeasonStatus = z.enum(["peak", "shoulder", "active", "off", "closed"]);
export const CoordAccuracy = z.enum(["approx", "verified"]);

// === DECISION OUTPUT SCHEMAS ===
export const DecisionMeta = z.object({
  contractVersion: z.string(),
  generatedAt: z.string(),
  timezone: z.string(),
  traceLevelRequested: z.string().optional(),
  traceLevelApplied: z.string().optional(),
});

export const DaySummary = z.object({
  windSpeedKmhMin: z.number(),
  windSpeedKmhMax: z.number(),
  windDirDeg: z.number(),
  windDirectionTR: z.string(),
  pressureHpa: z.number(),
  pressureChange3hHpa: z.number(),
  pressureTrend: PressureTrend,
  airTempCMin: z.number(),
  airTempCMax: z.number(),
  seaTempC: z.number().nullable(),
  cloudCoverPct: z.number().nullable(),
  waveHeightM: z.number().nullable(),
  dataQuality: DataQuality,
  dataIssues: z.array(z.string()),
});

export const BestWindow = z.object({
  startLocal: z.string(),
  endLocal: z.string(),
  score0to100: z.number(),
  confidence0to1: z.number(),
  reasonsTR: z.array(z.string()),
});

export const DecisionTarget = z.object({
  speciesId: SpeciesId,
  speciesNameTR: z.string(),
  score0to100: z.number(),
  confidence0to1: z.number(),
  mode: SpeciesMode,
  bestWindowIndex: z.number().nullable(),
});

export const TechniqueReco = z.object({
  techniqueId: TechniqueId,
  techniqueNameTR: z.string(),
  setupHintTR: z.string().nullable(),
});

export const AvoidTechnique = z.object({
  techniqueId: TechniqueId,
  techniqueNameTR: z.string(),
  reasonTR: z.string(),
});

export const ReportSignals = z.object({
  totalReports: z.number(),
  techniqueCounts: z.record(z.string(), z.number()),
  naturalBaitBias: z.boolean(),
  notesTR: z.array(z.string()).optional(),
}).nullable();

export const RecommendedSpot = z.object({
  spotId: z.string(),
  nameTR: z.string(),
  spotWindBandKmhMin: z.number(),
  spotWindBandKmhMax: z.number(),
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
  spotNameTR: z.string().optional(),
  allowedTechniques: z.array(z.string()),
  warningLevel: z.string(),
  messageTR: z.string(),
});

export const NoGo = z.object({
  isNoGo: z.boolean(),
  reasonsTR: z.array(z.string()),
  shelteredExceptions: z.array(ShelteredExceptionEntry).optional(), // v1.3
});

export const HealthBlock = z.object({
  status: z.enum(["good", "degraded", "bad"]),
  reasonsCode: z.array(z.string()).optional(),
  reasonsTR: z.array(z.string()).optional(),
  reasons: z.array(z.string()).optional(),
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
  health: HealthBlock.optional(),
});

// === SCORE SCHEMAS ===
export const SolunarPeriod = z.object({ start: z.string(), end: z.string() });
export const Solunar = z.object({
  majorPeriods: z.array(SolunarPeriod),
  minorPeriods: z.array(SolunarPeriod),
  moonPhase: z.string(),
  moonIllumination: z.number(),
  solunarRating: z.number(),
});

export const ScoreBreakdown = z.object({
  pressure: z.number(),
  wind: z.number(),
  seaTemp: z.number(),
  solunar: z.number(),
  time: z.number(),
  seasonMultiplier: z.number(),
  seasonAdjustment: z.number().optional(), // v1.3 authoritative
  rulesBonus: z.number(),
});

export const SpeciesScore = z.object({
  speciesId: SpeciesId,
  speciesNameTR: z.string(),
  score0to100: z.number(),
  suppressedByNoGo: z.boolean(),
  bestTime: z.string().nullable(),
  confidence0to1: z.number(),
  seasonStatus: SeasonStatus,
  mode: SpeciesMode,
  recommendedTechniques: z.array(TechniqueReco),
  avoidTechniques: z.array(AvoidTechnique),
  breakdown: ScoreBreakdown.optional(),
});

// === SPOT SCHEMA ===
export const WindExposure = z.object({
  onshoreDirsDeg: z.array(z.number()),
  offshoreDirsDeg: z.array(z.number()),
  shelterScore0to1: z.number(),
});

export const SpotSchema = z.object({
  id: z.string(),
  name: z.string(),
  lat: z.number(),
  lng: z.number(),
  accuracy: CoordAccuracy,
  shore: Shore,
  regionId: RegionId,
  regionGroup: z.string(),
  pelagicCorridor: z.boolean(),
  urbanCrowdRisk: z.string(),
  primarySpecies: z.array(z.string()),
  primaryTechniques: z.array(z.string()),
  techniqueBias: z.array(z.string()),
  features: z.array(z.string()),
  depth: z.string(),
  currentExposure: z.string(),
  windExposure: WindExposure,
  specialRules: z.array(z.string()),
  description: z.string().nullable().optional(),
});

// === REPORT SCHEMA ===
export const ReportRequest = z.object({
  spotId: z.string(),
  species: SpeciesId,
  quantity: z.number().min(1).max(100),
  avgSize: z.string().regex(/^\d+cm$/),
  technique: TechniqueId,
  bait: BaitId.nullable(),
  notes: z.string().max(500).nullable().optional(),
  photoUrl: z.string().nullable().optional(),
});
