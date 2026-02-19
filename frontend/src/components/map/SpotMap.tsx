"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { MAP_CENTER, MAP_ZOOM, REGION_COLORS, getScoreColor } from "@/lib/constants";
import type { SpotType, SpotScoreSummary } from "@/lib/types";

// Leaflet SSR disabled
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
const Tooltip = dynamic(
  () => import("react-leaflet").then((m) => m.Tooltip),
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
      <div className="h-[400px] lg:h-[600px] bg-gray-100 rounded-xl flex items-center justify-center">
        <span className="text-gray-400">Harita yükleniyor...</span>
      </div>
    );
  }

  const scoreMap = new Map(scores?.map((s) => [s.spotId, s]));

  return (
    <div className="h-[400px] lg:h-[600px] rounded-xl overflow-hidden border border-gray-200">
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
          const score = scoreMap.get(spot.id);
          const regionColor = REGION_COLORS[spot.regionId] || "#3B82F6";
          const pinColor = score ? getScoreColor(score.overallScore) : regionColor;

          return (
            <CircleMarker
              key={spot.id}
              center={[spot.lat, spot.lng]}
              radius={score ? 12 : 8}
              pathOptions={{
                color: pinColor,
                fillColor: pinColor,
                fillOpacity: 0.8,
                weight: 2,
              }}
            >
              {score && (
                <Tooltip direction="top" offset={[0, -10]} permanent>
                  <span className="font-bold text-xs">{score.overallScore}</span>
                </Tooltip>
              )}
              <Popup>
                <div className="text-sm">
                  <div className="font-bold">{spot.name}</div>
                  {score && (
                    <div className="mt-1">
                      Skor: <strong>{score.overallScore}</strong>
                    </div>
                  )}
                  <a
                    href={`/spot/${spot.id}`}
                    className="text-blue-600 hover:underline text-xs mt-1 inline-block"
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
