"use client";

import { useEffect, useState } from "react";
import type { SpotType, SpotDetailScore } from "@/lib/types";
import { API_URL, REGION_NAMES_TR } from "@/lib/constants";
import Badge from "@/components/ui/Badge";
import ScoreGauge from "@/components/ui/ScoreGauge";
import SpeciesScoreRow from "./SpeciesScore";

interface SpotDetailProps {
  spot: SpotType;
}

const DEPTH_TR: Record<string, string> = {
  shallow: "Sığ",
  medium: "Orta",
  deep: "Derin",
};

const CROWD_TR: Record<string, string> = {
  low: "Düşük",
  medium: "Orta",
  high: "Yüksek",
};

const FEATURE_TR: Record<string, string> = {
  kayalık: "Kayalık",
  kumlu: "Kumlu",
  akıntılı: "Akıntılı",
  sakin: "Sakin",
  derin: "Derin",
  sığ: "Sığ",
  gece_uygun: "Gece Uygun",
  aydınlatmalı: "Aydınlatmalı",
  aile_uygun: "Aile Uygun",
  korunaklı: "Korunaklı",
  kalabalık: "Kalabalık",
  ikonik: "İkonik",
  tarihi: "Tarihi",
  rüzgara_açık: "Rüzgara Açık",
  doğal: "Doğal",
};

/* ── Inline Weather Icons ── */
function WindIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <path d="M9.59 4.59A2 2 0 1 1 11 8H2" />
      <path d="M12.59 19.41A2 2 0 1 0 14 16H2" />
      <path d="M17.74 7.74A2.5 2.5 0 1 1 19.5 12H2" />
    </svg>
  );
}
function BarometerIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <path d="M12 6v6l4 2" />
    </svg>
  );
}
function WaveIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 6c.6.5 1.2 1 2.5 1C7 7 7 5 9.5 5c2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1" />
      <path d="M2 12c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1" />
      <path d="M2 18c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1" />
    </svg>
  );
}
function ThermometerIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z" />
    </svg>
  );
}

export default function SpotDetail({ spot }: SpotDetailProps) {
  const [score, setScore] = useState<SpotDetailScore | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_URL}/scores/spot/${spot.id}`)
      .then((r) => r.json())
      .then((d) => setScore(d))
      .catch(() => setScore(null))
      .finally(() => setLoading(false));
  }, [spot.id]);

  const weather = score?.weather as Record<string, number> | undefined;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="card p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-white">{spot.name}</h1>
            {spot.description && (
              <p className="text-sm text-slate-400 mt-1">{spot.description}</p>
            )}
          </div>
          {score && (
            <ScoreGauge score={score.overallScore} size="lg" noGo={score.noGo.isNoGo} />
          )}
        </div>
        <div className="flex flex-wrap gap-2 mt-4">
          <Badge label={REGION_NAMES_TR[spot.regionId] || spot.regionId} color="#3b82f6" />
          {spot.regionId === "city_belt" && (
            <Badge
              label={spot.shore === "european" ? "Avrupa Yakası" : "Anadolu Yakası"}
              color="#8b5cf6"
            />
          )}
          {spot.pelagicCorridor && <Badge label="Pelajik Koridor" color="#a78bfa" />}
          <Badge
            label={`Kalabalık: ${CROWD_TR[spot.urbanCrowdRisk] || spot.urbanCrowdRisk}`}
            color="#f97316"
          />
          <Badge
            label={`Derinlik: ${DEPTH_TR[spot.depth] || spot.depth}`}
            color="#06b6d4"
          />
        </div>
        <div className="flex flex-wrap gap-1.5 mt-3">
          {spot.features.map((f) => (
            <span
              key={f}
              className="text-xs text-slate-400 px-2.5 py-1 rounded-full backdrop-blur-sm"
              style={{
                background: "var(--glass-bg-strong)",
                border: "1px solid var(--border-subtle)",
              }}
            >
              {FEATURE_TR[f] || f}
            </span>
          ))}
        </div>
      </div>

      {/* Weather — 4 separate cards */}
      {weather && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="metric-cell flex flex-col items-center">
            <WindIcon className="w-5 h-5 text-sky-400 mb-1.5" />
            <div className="text-sky-400 font-bold text-xl">
              {weather.windSpeedKmh?.toFixed(0)}
            </div>
            <div className="text-slate-500 text-xs mt-0.5">km/h Rüzgar</div>
          </div>
          <div className="metric-cell flex flex-col items-center">
            <BarometerIcon className="w-5 h-5 text-orange-400 mb-1.5" />
            <div className="text-orange-400 font-bold text-xl">
              {weather.pressureHpa?.toFixed(0)}
            </div>
            <div className="text-slate-500 text-xs mt-0.5">hPa Basınç</div>
          </div>
          <div className="metric-cell flex flex-col items-center">
            <WaveIcon className="w-5 h-5 text-cyan-400 mb-1.5" />
            <div className="text-cyan-400 font-bold text-xl">
              {weather.seaTempC?.toFixed(1)}&deg;
            </div>
            <div className="text-slate-500 text-xs mt-0.5">Su Sıcaklığı</div>
          </div>
          <div className="metric-cell flex flex-col items-center">
            <ThermometerIcon className="w-5 h-5 text-green-400 mb-1.5" />
            <div className="text-green-400 font-bold text-xl">
              {weather.airTempC?.toFixed(0)}&deg;
            </div>
            <div className="text-slate-500 text-xs mt-0.5">Hava Sıcaklığı</div>
          </div>
        </div>
      )}

      {/* Species Scores — Grid */}
      {loading ? (
        <div className="card p-8 text-center">
          <div className="w-6 h-6 mx-auto mb-2 border-2 border-blue-500/40 border-t-blue-500 rounded-full animate-spin" />
          <p className="text-slate-500 text-sm">Skorlar hesaplanıyor...</p>
        </div>
      ) : score?.speciesScores ? (
        <div>
          <h2 className="section-label mb-4">Tür Skorları</h2>
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
            {score.speciesScores.map((sp) => (
              <SpeciesScoreRow key={sp.speciesId} species={sp} />
            ))}
          </div>
        </div>
      ) : (
        <div className="card p-8 text-center text-slate-500">
          Skor verisi bulunamadı
        </div>
      )}

      {/* Active Rules */}
      {score?.activeRules && score.activeRules.length > 0 && (
        <div className="card p-5">
          <h2 className="section-label mb-3">Aktif Kurallar</h2>
          <div className="space-y-2">
            {score.activeRules.map((rule) => (
              <div key={rule.ruleId} className="text-sm text-slate-400 flex gap-2 items-start">
                <span className="text-blue-400 flex-shrink-0 mt-0.5">&#x25B8;</span>
                <span>{rule.messageTR}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
