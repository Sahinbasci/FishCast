"use client";

import useSWR from "swr";
import { API_URL } from "@/lib/constants";
import type { DecisionResponseType } from "@/lib/types";

const fetcher = (url: string) => fetch(url).then((r) => r.json());

/** Decision fetch with SWR (3 min polling) */
export function useDecision() {
  const { data, error, isLoading } = useSWR<DecisionResponseType>(
    `${API_URL}/decision/today`,
    fetcher,
    { refreshInterval: 180000 },
  );
  return { decision: data, error, isLoading };
}
