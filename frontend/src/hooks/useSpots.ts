"use client";

import useSWR from "swr";
import { API_URL } from "@/lib/constants";
import type { SpotType, SpotScoreSummary } from "@/lib/types";

const fetcher = (url: string) => fetch(url).then((r) => r.json());

/** Spots fetch with SWR */
export function useSpots() {
  const { data, error, isLoading } = useSWR<SpotType[]>(
    `${API_URL}/spots`,
    fetcher,
  );
  return { spots: data, error, isLoading };
}

/** Scores today fetch with SWR (3 min polling) */
export function useScoresToday() {
  const { data, error, isLoading } = useSWR<SpotScoreSummary[]>(
    `${API_URL}/scores/today`,
    fetcher,
    { refreshInterval: 180000 },
  );
  return { scores: data, error, isLoading };
}
