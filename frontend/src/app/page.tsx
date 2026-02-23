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
          <div
            className="w-12 h-12 mx-auto mb-4 rounded-xl flex items-center justify-center"
            style={{ background: "var(--gradient-ocean)" }}
          >
            <div className="w-5 h-5 border-2 border-white/40 border-t-white rounded-full animate-spin" />
          </div>
          <p className="text-slate-500 text-sm">Veriler hesaplanıyor...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* NO-GO Overlay */}
      {decision?.noGo?.isNoGo && (
        <NoGoOverlay
          reasonsTR={decision.noGo.reasonsTR}
          shelteredExceptions={decision.noGo.shelteredExceptions}
        />
      )}

      {/* Weather KPI Cards */}
      {decision?.daySummary && (
        <section className="animate-fade-up">
          <DaySummary summary={decision.daySummary} />
        </section>
      )}

      {/* Best Time Windows */}
      {decision?.bestWindows && decision.bestWindows.length > 0 && (
        <section className="animate-fade-up" style={{ animationDelay: "0.08s" }}>
          <h2 className="text-xl font-bold text-white tracking-tight mb-4">
            En İyi Zaman Pencereleri
          </h2>
          <BestWindows windows={decision.bestWindows} />
        </section>
      )}

      {/* Region Cards */}
      <section className="animate-fade-up" style={{ animationDelay: "0.16s" }}>
        <h2 className="text-xl font-bold text-white tracking-tight mb-4">
          Öne Çıkan Balık Avı Noktaları
        </h2>
        {decision?.regions ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {decision.regions.map((region) => (
              <RegionCard key={region.regionId} region={region} />
            ))}
          </div>
        ) : (
          <div className="card p-10 text-center text-slate-500">
            Karar verisi bekleniyor...
          </div>
        )}
      </section>

      {/* Map */}
      <section id="harita" className="animate-fade-up" style={{ animationDelay: "0.24s" }}>
        <h2 className="text-xl font-bold text-white tracking-tight mb-4">
          Harita
        </h2>
        {spots ? (
          <SpotMap spots={spots} scores={scores} />
        ) : (
          <div className="h-[400px] card flex items-center justify-center">
            <div className="text-center">
              <div className="w-6 h-6 mx-auto mb-2 border-2 border-blue-500/40 border-t-blue-500 rounded-full animate-spin" />
              <p className="text-slate-500 text-sm">Harita yükleniyor...</p>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
