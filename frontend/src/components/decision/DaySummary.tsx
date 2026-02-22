"use client";

import type { DaySummaryType } from "@/lib/types";

/* ── Inline SVG Weather Icons ── */

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

function ThermometerIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z" />
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

/* ── Component ── */

interface DaySummaryProps {
  summary: DaySummaryType;
}

export default function DaySummary({ summary }: DaySummaryProps) {
  const trendArrow =
    summary.pressureTrend === "falling"
      ? "\u2193"
      : summary.pressureTrend === "rising"
        ? "\u2191"
        : "\u2192";

  return (
    <div className="space-y-3">
      {/* 4 Separate KPI Glass Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {/* Wind */}
        <div className="metric-cell flex flex-col items-center">
          <WindIcon className="w-6 h-6 text-sky-400 mb-2" />
          <div className="text-white font-extrabold text-2xl sm:text-3xl tracking-tight">
            {Math.round(summary.windSpeedKmhMin)}-{Math.round(summary.windSpeedKmhMax)}
          </div>
          <div className="text-sky-400 text-sm font-semibold mt-0.5">km/h</div>
          <div className="text-slate-400 text-xs mt-1">{summary.windDirectionTR}</div>
        </div>

        {/* Pressure */}
        <div className="metric-cell flex flex-col items-center">
          <BarometerIcon className="w-6 h-6 text-orange-400 mb-2" />
          <div className="text-orange-400 font-extrabold text-2xl sm:text-3xl tracking-tight">
            {Math.round(summary.pressureHpa)}
            <span className="text-lg ml-1">{trendArrow}</span>
          </div>
          <div className="text-orange-400/70 text-sm font-semibold mt-0.5">hPa</div>
          <div className="text-slate-400 text-xs mt-1">
            3s: {summary.pressureChange3hHpa > 0 ? "+" : ""}
            {summary.pressureChange3hHpa.toFixed(1)}
          </div>
        </div>

        {/* Air Temperature */}
        <div className="metric-cell flex flex-col items-center">
          <ThermometerIcon className="w-6 h-6 text-green-400 mb-2" />
          <div className="text-green-400 font-extrabold text-2xl sm:text-3xl tracking-tight">
            {Math.round(summary.airTempCMin)}-{Math.round(summary.airTempCMax)}
            <span className="text-lg">&deg;C</span>
          </div>
          <div className="text-slate-400 text-xs mt-1.5">Hava Sıcaklığı</div>
        </div>

        {/* Sea Temperature */}
        <div className="metric-cell flex flex-col items-center">
          <WaveIcon className="w-6 h-6 text-cyan-400 mb-2" />
          <div className="text-cyan-400 font-extrabold text-2xl sm:text-3xl tracking-tight">
            {summary.seaTempC ? summary.seaTempC.toFixed(1) : "\u2014"}
            <span className="text-lg">&deg;C</span>
          </div>
          <div className="text-slate-400 text-xs mt-1.5">Su Sıcaklığı</div>
        </div>
      </div>

      {/* Data quality warnings */}
      {summary.dataIssues.length > 0 && (
        <div
          className="text-xs text-orange-300 rounded-xl px-4 py-2.5 backdrop-blur-md"
          style={{
            background: "rgba(249, 115, 22, 0.08)",
            border: "1px solid rgba(249, 115, 22, 0.20)",
          }}
        >
          {summary.dataIssues.map((issue, i) => (
            <div key={i}>{issue}</div>
          ))}
        </div>
      )}
    </div>
  );
}
