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
  const regionColor = REGION_COLORS[region.regionId] || "#3B82F6";
  const regionName = REGION_NAMES_TR[region.regionId] || region.regionId;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      <div className="px-4 py-2 text-white text-sm font-semibold" style={{ backgroundColor: regionColor }}>
        {regionName}
      </div>
      <div className="p-4 space-y-3">
        {/* Spot info */}
        <div>
          <Link href={`/spot/${spot.spotId}`} className="text-lg font-bold text-gray-800 hover:text-blue-600 transition">
            {spot.nameTR}
          </Link>
          <div className="text-xs text-gray-400">
            Rüzgar bandı: {spot.spotWindBandKmhMin}-{spot.spotWindBandKmhMax} km/h
          </div>
        </div>

        {/* Targets */}
        <div className="space-y-2">
          {spot.targets.map((t) => (
            <TargetCard key={t.speciesId} target={t} />
          ))}
        </div>

        {/* Techniques */}
        {(spot.recommendedTechniques.length > 0 || spot.avoidTechniques.length > 0) && (
          <div className="flex flex-wrap gap-1">
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
          <div className="text-xs text-gray-500 space-y-1 border-t pt-2">
            {spot.whyTR.map((w, i) => (
              <div key={i} className="flex gap-1">
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
