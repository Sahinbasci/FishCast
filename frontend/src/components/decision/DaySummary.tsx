"use client";

import type { DaySummaryType } from "@/lib/types";
import Badge from "@/components/ui/Badge";

interface DaySummaryProps {
  summary: DaySummaryType;
}

const QUALITY_COLORS: Record<string, { color: string; bg: string }> = {
  live: { color: "#22C55E", bg: "#DCFCE7" },
  cached: { color: "#EAB308", bg: "#FEF9C3" },
  fallback: { color: "#EF4444", bg: "#FEE2E2" },
};

export default function DaySummary({ summary }: DaySummaryProps) {
  const qc = QUALITY_COLORS[summary.dataQuality] || QUALITY_COLORS.fallback;
  const trendArrow = summary.pressureTrend === "falling" ? "↓" : summary.pressureTrend === "rising" ? "↑" : "→";

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-semibold text-gray-800">Hava Durumu</h2>
        <Badge
          label={summary.dataQuality === "live" ? "Canlı" : summary.dataQuality === "cached" ? "Önbellek" : "Tahmini"}
          color={qc.color}
          bgColor={qc.bg}
        />
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
        <div className="bg-blue-50 rounded-lg p-3 text-center">
          <div className="text-blue-600 font-semibold text-lg">
            {Math.round(summary.windSpeedKmhMin)}-{Math.round(summary.windSpeedKmhMax)}
          </div>
          <div className="text-gray-500 text-xs">km/h {summary.windDirectionTR}</div>
        </div>
        <div className="bg-purple-50 rounded-lg p-3 text-center">
          <div className="text-purple-600 font-semibold text-lg">
            {Math.round(summary.pressureHpa)} {trendArrow}
          </div>
          <div className="text-gray-500 text-xs">hPa ({summary.pressureChange3hHpa > 0 ? "+" : ""}{summary.pressureChange3hHpa.toFixed(1)})</div>
        </div>
        <div className="bg-orange-50 rounded-lg p-3 text-center">
          <div className="text-orange-600 font-semibold text-lg">
            {Math.round(summary.airTempCMin)}-{Math.round(summary.airTempCMax)}°
          </div>
          <div className="text-gray-500 text-xs">Hava Sıcaklığı</div>
        </div>
        <div className="bg-cyan-50 rounded-lg p-3 text-center">
          <div className="text-cyan-600 font-semibold text-lg">
            {summary.seaTempC ? `${summary.seaTempC.toFixed(1)}°` : "—"}
          </div>
          <div className="text-gray-500 text-xs">Su Sıcaklığı</div>
        </div>
      </div>
      {summary.dataIssues.length > 0 && (
        <div className="mt-2 text-xs text-amber-600 bg-amber-50 rounded p-2">
          {summary.dataIssues.map((issue, i) => (
            <div key={i}>{issue}</div>
          ))}
        </div>
      )}
    </div>
  );
}
