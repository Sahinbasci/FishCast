"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { MAP_CENTER, MAP_ZOOM, REGION_COLORS, getScoreColor } from "@/lib/constants";
import type { SpotType, SpotScoreSummary } from "@/lib/types";

const MapContainer = dynamic(
  () => import("react-leaflet").then((m) => m.MapContainer),
  { ssr: false },
);
const TileLayer = dynamic(
  () => import("react-leaflet").then((m) => m.TileLayer),
  { ssr: false },
);
const CircleMarker = dynamic(
  () => import("react-leaflet").then((m) => m.CircleMarker),
  { ssr: false },
);
const Popup = dynamic(
  () => import("react-leaflet").then((m) => m.Popup),
  { ssr: false },
);

interface SpotMapProps {
  spots: SpotType[];
  scores?: SpotScoreSummary[];
}

export default function SpotMap({ spots, scores }: SpotMapProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <div className="h-[400px] lg:h-[600px] card flex items-center justify-center">
        <div className="text-center">
          <div className="w-6 h-6 mx-auto mb-2 border-2 border-[var(--blue-primary)]/40 border-t-[var(--blue-primary)] rounded-full animate-spin" />
          <span className="text-[var(--text-dim)] text-sm">Harita yükleniyor...</span>
        </div>
      </div>
    );
  }

  const scoreMap = new Map(scores?.map((s) => [s.spotId, s]));

  return (
    <div className="h-[400px] lg:h-[600px] rounded-[var(--radius-lg)] overflow-hidden border border-[var(--border-subtle)]">
      <link
        rel="stylesheet"
        href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
      />
      <MapContainer
        center={MAP_CENTER}
        zoom={MAP_ZOOM}
        className="h-full w-full"
        scrollWheelZoom={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {spots.map((spot) => {
          const scoreData = scoreMap.get(spot.id);
          const regionColor = REGION_COLORS[spot.regionId] || "#3b82f6";
          const pinColor = scoreData ? getScoreColor(scoreData.overallScore) : regionColor;
          const scoreVal = scoreData?.overallScore;

          return (
            <CircleMarker
              key={spot.id}
              center={[spot.lat, spot.lng]}
              radius={10}
              pathOptions={{
                color: "#0a1628",
                fillColor: pinColor,
                fillOpacity: 0.9,
                weight: 2,
              }}
            >
              <Popup>
                <div className="text-sm min-w-[160px]">
                  <div className="font-bold text-white text-base">{spot.name}</div>
                  {scoreVal !== undefined && (
                    <div className="mt-2 flex items-center gap-2.5">
                      <span
                        className="score-pill"
                        style={{
                          background: `${pinColor}20`,
                          color: pinColor,
                          border: `1px solid ${pinColor}40`,
                        }}
                      >
                        {scoreVal}
                      </span>
                      <span className="text-[var(--text-muted)] text-xs">Genel Skor</span>
                    </div>
                  )}
                  {scoreData?.topSpecies && scoreData.topSpecies.length > 0 && (
                    <div className="mt-2 space-y-0.5 text-xs text-[var(--text-secondary)]">
                      {scoreData.topSpecies.slice(0, 2).map((sp) => (
                        <div key={sp.speciesId} className="flex justify-between">
                          <span>{sp.speciesNameTR}</span>
                          <span className="font-semibold text-white">{sp.score0to100}</span>
                        </div>
                      ))}
                    </div>
                  )}
                  <a
                    href={`/spot/${spot.id}`}
                    className="text-[var(--blue-light)] hover:text-[var(--blue-bright)] text-xs mt-2.5 inline-block font-semibold transition-colors"
                  >
                    Detaya Git &rarr;
                  </a>
                </div>
              </Popup>
            </CircleMarker>
          );
        })}
      </MapContainer>
    </div>
  );
}
