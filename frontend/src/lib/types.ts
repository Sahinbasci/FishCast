/**
 * FishCast TypeScript types — z.infer exports from Zod schemas.
 */

import { z } from "zod";
import {
  DecisionResponse,
  DaySummary,
  BestWindow,
  RegionDecision,
  RecommendedSpot,
  DecisionTarget,
  TechniqueReco,
  AvoidTechnique,
  NoGo,
  SpeciesScore,
  ScoreBreakdown,
  SpotSchema,
  Solunar,
  ReportRequest,
} from "./schemas";

export type DecisionResponseType = z.infer<typeof DecisionResponse>;
export type DaySummaryType = z.infer<typeof DaySummary>;
export type BestWindowType = z.infer<typeof BestWindow>;
export type RegionDecisionType = z.infer<typeof RegionDecision>;
export type RecommendedSpotType = z.infer<typeof RecommendedSpot>;
export type DecisionTargetType = z.infer<typeof DecisionTarget>;
export type TechniqueRecoType = z.infer<typeof TechniqueReco>;
export type AvoidTechniqueType = z.infer<typeof AvoidTechnique>;
export type NoGoType = z.infer<typeof NoGo>;
export type SpeciesScoreType = z.infer<typeof SpeciesScore>;
export type ScoreBreakdownType = z.infer<typeof ScoreBreakdown>;
export type SpotType = z.infer<typeof SpotSchema>;
export type SolunarType = z.infer<typeof Solunar>;
export type ReportRequestType = z.infer<typeof ReportRequest>;

/** Scores today endpoint response item */
export interface SpotScoreSummary {
  spotId: string;
  spotName: string;
  regionId: string;
  overallScore: number;
  noGo: { isNoGo: boolean; reasonsTR: string[] };
  topSpecies: {
    speciesId: string;
    speciesNameTR: string;
    score0to100: number;
    mode: string;
  }[];
}

/** Spot detail score endpoint response */
export interface SpotDetailScore {
  spotId: string;
  date: string;
  meta: { contractVersion: string; generatedAt: string; timezone: string };
  overallScore: number;
  noGo: { isNoGo: boolean; reasonsTR: string[] };
  weather: Record<string, unknown>;
  solunar: SolunarType;
  speciesScores: SpeciesScoreType[];
  activeRules: { ruleId: string; appliedBonus: number; affectedSpecies: string[]; messageTR: string }[];
}
