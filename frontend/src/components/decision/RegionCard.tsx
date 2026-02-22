"use client";

import Link from "next/link";
import type { RegionDecisionType } from "@/lib/types";
import { REGION_COLORS, REGION_NAMES_TR } from "@/lib/constants";
import TargetCard from "./TargetCard";
import TechniqueTag from "./TechniqueTag";

interface RegionCardProps {
  region: RegionDecisionType;
}

export default function RegionCard({ region }: RegionCardProps) {
  const spot = region.recommendedSpot;
  const regionColor = REGION_COLORS[region.regionId] || "#3b82f6";
  const regionName = REGION_NAMES_TR[region.regionId] || region.regionId;

  return (
    <div
      className="card-interactive overflow-hidden"
      style={{
        // Region-tinted glow on hover handled via CSS .card-interactive
      }}
    >
      {/* Region accent bar */}
      <div
        className="h-1.5 w-full"
        style={{
          background: `linear-gradient(90deg, ${regionColor}, ${regionColor}60)`,
        }}
      />

      <div
        className="p-5 space-y-4"
        style={{
          background: `linear-gradient(180deg, ${regionColor}08, transparent 40%)`,
        }}
      >
        {/* Region label + Spot name */}
        <div>
          <div
            className="text-[11px] font-semibold uppercase tracking-wider mb-1"
            style={{ color: regionColor }}
          >
            {regionName}
          </div>
          <Link
            href={`/spot/${spot.spotId}`}
            className="text-xl font-bold text-white hover:text-blue-300 transition-colors"
          >
            {spot.nameTR}
          </Link>
          <div className="text-xs text-slate-500 mt-0.5">
            {Math.round(spot.spotWindBandKmhMin)}-{Math.round(spot.spotWindBandKmhMax)} km/h
          </div>
        </div>

        {/* Targets */}
        <div className="space-y-2">
          {spot.targets.slice(0, 3).map((t) => (
            <TargetCard key={t.speciesId} target={t} />
          ))}
        </div>

        {/* Techniques */}
        {(spot.recommendedTechniques.length > 0 || spot.avoidTechniques.length > 0) && (
          <div className="flex flex-wrap gap-2 pt-1">
            {spot.recommendedTechniques.map((t) => (
              <TechniqueTag
                key={t.techniqueId}
                name={t.techniqueNameTR}
                type="recommended"
                hint={t.setupHintTR}
              />
            ))}
            {spot.avoidTechniques.map((t) => (
              <TechniqueTag
                key={t.techniqueId}
                name={t.techniqueNameTR}
                type="avoid"
                reason={t.reasonTR}
              />
            ))}
          </div>
        )}

        {/* WhyTR */}
        {spot.whyTR.length > 0 && (
          <div
            className="text-xs text-slate-400 space-y-1 pt-3"
            style={{ borderTop: "1px solid rgba(255,255,255,0.06)" }}
          >
            {spot.whyTR.map((w, i) => (
              <div key={i} className="flex gap-1.5">
                <span className="text-blue-400 flex-shrink-0">&#x25B8;</span>
                <span>{w}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
