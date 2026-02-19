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

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="bg-white rounded-xl shadow-sm border p-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-800">{spot.name}</h1>
            <p className="text-sm text-gray-500">{spot.description}</p>
          </div>
          {score && <ScoreGauge score={score.overallScore} size="lg" noGo={score.noGo.isNoGo} />}
        </div>
        <div className="flex flex-wrap gap-2 mt-3">
          <Badge label={REGION_NAMES_TR[spot.regionId] || spot.regionId} />
          <Badge label={spot.shore === "european" ? "Avrupa" : "Anadolu"} />
          {spot.pelagicCorridor && <Badge label="Pelajik Koridor" color="#6366F1" bgColor="#EEF2FF" />}
          <Badge label={`Kalabalık: ${spot.urbanCrowdRisk}`} />
          <Badge label={`Derinlik: ${spot.depth}`} />
          <Badge label={`Doğruluk: ${spot.accuracy}`} color="#9CA3AF" bgColor="#F3F4F6" />
        </div>
        <div className="flex flex-wrap gap-1 mt-2">
          {spot.features.map((f) => (
            <span key={f} className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
              {f}
            </span>
          ))}
        </div>
      </div>

      {/* Weather */}
      {score?.weather && (
        <div className="bg-white rounded-xl shadow-sm border p-4">
          <h2 className="font-semibold text-gray-800 mb-2">Hava Durumu</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-sm text-gray-600">
            <div>Rüzgar: {(score.weather as Record<string, number>).windSpeedKmh?.toFixed(0)} km/h</div>
            <div>Basınç: {(score.weather as Record<string, number>).pressureHpa?.toFixed(0)} hPa</div>
            <div>Su: {(score.weather as Record<string, number>).seaTempC?.toFixed(1)}°C</div>
            <div>Hava: {(score.weather as Record<string, number>).airTempC?.toFixed(0)}°C</div>
          </div>
        </div>
      )}

      {/* Species Scores */}
      {loading ? (
        <div className="bg-white rounded-xl shadow-sm border p-8 text-center text-gray-400">
          Skorlar hesaplanıyor...
        </div>
      ) : score?.speciesScores ? (
        <div className="space-y-2">
          <h2 className="font-semibold text-gray-800">Tür Skorları</h2>
          {score.speciesScores.map((sp) => (
            <SpeciesScoreRow key={sp.speciesId} species={sp} />
          ))}
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border p-8 text-center text-gray-400">
          Skor verisi bulunamadı
        </div>
      )}

      {/* Active Rules */}
      {score?.activeRules && score.activeRules.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border p-4">
          <h2 className="font-semibold text-gray-800 mb-2">Aktif Kurallar</h2>
          <div className="space-y-1">
            {score.activeRules.map((rule) => (
              <div key={rule.ruleId} className="text-sm text-gray-600 flex gap-2">
                <span className="text-blue-400 flex-shrink-0">&#x25B8;</span>
                <span>{rule.messageTR}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
