"use client";

import { useDecision } from "@/hooks/useDecision";
import { useSpots, useScoresToday } from "@/hooks/useSpots";
import DaySummary from "@/components/decision/DaySummary";
import BestWindows from "@/components/decision/BestWindows";
import RegionCard from "@/components/decision/RegionCard";
import NoGoOverlay from "@/components/decision/NoGoOverlay";
import SpotMap from "@/components/map/SpotMap";

export default function HomePage() {
  const { decision, isLoading: decisionLoading } = useDecision();
  const { spots } = useSpots();
  const { scores } = useScoresToday();

  if (decisionLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <div className="text-4xl mb-4 animate-pulse">&#x1F3A3;</div>
          <p className="text-gray-500">Veriler hesaplanıyor...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* NO-GO Overlay */}
      {decision?.noGo?.isNoGo && (
        <NoGoOverlay reasonsTR={decision.noGo.reasonsTR} />
      )}

      {/* Day Summary */}
      {decision?.daySummary && (
        <DaySummary summary={decision.daySummary} />
      )}

      {/* Best Windows */}
      {decision?.bestWindows && (
        <BestWindows windows={decision.bestWindows} />
      )}

      {/* Region Cards + Map */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Region Cards */}
        <div className="lg:col-span-2">
          <h2 className="text-lg font-semibold text-gray-800 mb-3">Bölge Önerileri</h2>
          {decision?.regions ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {decision.regions.map((region) => (
                <RegionCard key={region.regionId} region={region} />
              ))}
            </div>
          ) : (
            <div className="bg-white rounded-xl border p-8 text-center text-gray-400">
              Karar verisi bekleniyor...
            </div>
          )}
        </div>

        {/* Map */}
        <div id="harita" className="lg:col-span-1">
          <h2 className="text-lg font-semibold text-gray-800 mb-3">Harita</h2>
          {spots ? (
            <SpotMap spots={spots} scores={scores} />
          ) : (
            <div className="h-[400px] bg-gray-100 rounded-xl flex items-center justify-center text-gray-400">
              Harita yükleniyor...
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
