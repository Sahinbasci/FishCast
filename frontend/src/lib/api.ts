/**
 * FishCast API client — typed fetch wrappers.
 */

import { API_URL } from "./constants";
import type {
  DecisionResponseType,
  SpotType,
  SpotScoreSummary,
  SpotDetailScore,
} from "./types";

async function fetchJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    next: { revalidate: 180 }, // 3 min cache
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

/** GET /decision/today */
export async function getDecision(): Promise<DecisionResponseType> {
  return fetchJSON<DecisionResponseType>("/decision/today");
}

/** GET /spots */
export async function getSpots(): Promise<SpotType[]> {
  return fetchJSON<SpotType[]>("/spots");
}

/** GET /spots/{id} */
export async function getSpot(id: string): Promise<SpotType> {
  return fetchJSON<SpotType>(`/spots/${id}`);
}

/** GET /scores/today */
export async function getScoresToday(): Promise<SpotScoreSummary[]> {
  return fetchJSON<SpotScoreSummary[]>("/scores/today");
}

/** GET /scores/spot/{id} */
export async function getSpotScore(id: string): Promise<SpotDetailScore> {
  return fetchJSON<SpotDetailScore>(`/scores/spot/${id}`);
}

/** GET /species */
export async function getSpecies(): Promise<Record<string, unknown>[]> {
  return fetchJSON<Record<string, unknown>[]>("/species");
}

/** GET /techniques */
export async function getTechniques(): Promise<Record<string, unknown>[]> {
  return fetchJSON<Record<string, unknown>[]>("/techniques");
}

/** POST /reports — requires auth token */
export async function submitReport(
  data: Record<string, unknown>,
  token: string,
): Promise<Record<string, unknown>> {
  const res = await fetch(`${API_URL}/reports`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    throw new Error(`Report submit failed: ${res.status}`);
  }
  return res.json();
}
