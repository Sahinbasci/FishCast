"use client";

import Link from "next/link";
import type { RegionDecisionType } from "@/lib/types";
import { REGION_COLORS, REGION_NAMES_TR } from "@/lib/constants";
import TargetCard from "./TargetCard";
import TechniqueTag from "./TechniqueTag";

/** Map whyTR message keywords to icon + color for visual categorization */
function getWhyIcon(msg: string): { icon: string; color: string } {
  const lower = msg.toLowerCase();
  if (lower.includes("dikkat") || lower.includes("uyarı"))
    return { icon: "\u26A0\uFE0F", color: "text-amber-400" };
  if (lower.includes("rüzgar") || lower.includes("poyraz") || lower.includes("lodos"))
    return { icon: "\uD83C\uDF2C\uFE0F", color: "text-sky-400" };
  if (lower.includes("basınç"))
    return { icon: "\uD83D\uDCC9", color: "text-violet-400" };
  if (lower.includes("koridor") || lower.includes("pelajik") || lower.includes("göç"))
    return { icon: "\uD83D\uDC1F", color: "text-cyan-400" };
  if (lower.includes("korunaklı") || lower.includes("sakin"))
    return { icon: "\uD83D\uDEE1\uFE0F", color: "text-emerald-400" };
  if (lower.includes("sıcak") || lower.includes("soğuk") || lower.includes("su"))
    return { icon: "\uD83C\uDF0A", color: "text-blue-400" };
  if (lower.includes("gece") || lower.includes("dolunay"))
    return { icon: "\uD83C\uDF19", color: "text-indigo-400" };
  return { icon: "\u25B8", color: "text-blue-400" };
}

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

        {/* Report Signals 24h */}
        {spot.reportSignals24h && spot.reportSignals24h.totalReports > 0 && (
          <div className="flex items-center gap-2 text-xs text-emerald-400/80 pt-1">
            <span>&#x1F4CA;</span>
            <span>
              Son 24s: {spot.reportSignals24h.totalReports} rapor
              {spot.reportSignals24h.naturalBaitBias && (
                <span className="text-amber-400 ml-1">&middot; Doğal yem trendi</span>
              )}
            </span>
          </div>
        )}

        {/* WhyTR — categorized with keyword-based icons */}
        {spot.whyTR.length > 0 && (
          <div
            className="space-y-1.5 pt-3"
            style={{ borderTop: "1px solid rgba(255,255,255,0.06)" }}
          >
            <div className="text-[10px] font-medium uppercase tracking-wider text-slate-500 mb-1">
              Neden burada?
            </div>
            {spot.whyTR.map((w, i) => {
              const { icon, color } = getWhyIcon(w);
              return (
                <div key={i} className="flex gap-2 items-start text-xs text-slate-400">
                  <span className={`${color} flex-shrink-0 text-sm leading-4`}>{icon}</span>
                  <span className="leading-4">{w}</span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
