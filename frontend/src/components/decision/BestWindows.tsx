"use client";

import type { BestWindowType } from "@/lib/types";
import { getScoreBg, getScoreColor } from "@/lib/constants";

interface BestWindowsProps {
  windows: BestWindowType[];
}

function ClockIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
  );
}

export default function BestWindows({ windows }: BestWindowsProps) {
  if (!windows.length) return null;

  return (
    <div className="flex gap-3 overflow-x-auto pb-2 -mx-1 px-1">
      {windows.map((w, i) => {
        const bg = getScoreBg(w.score0to100);
        const color = getScoreColor(w.score0to100);
        return (
          <div
            key={i}
            className="card-interactive flex-shrink-0 min-w-[240px] p-5"
          >
            {/* Time + Score */}
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <ClockIcon className="w-4 h-4 text-slate-400" />
                <span className="font-extrabold text-white text-lg tracking-tight">
                  {w.startLocal} - {w.endLocal}
                </span>
              </div>
              <span
                className="score-pill text-white text-sm font-bold"
                style={{
                  background: bg,
                  boxShadow: `0 0 12px ${color}40`,
                }}
              >
                {w.score0to100}
              </span>
            </div>

            {/* Reasons */}
            <div className="space-y-1">
              {w.reasonsTR.map((r, j) => (
                <div key={j} className="text-xs text-slate-400">
                  {r}
                </div>
              ))}
            </div>

            {/* Score bar */}
            <div className="mt-4 h-2 rounded-full" style={{ background: "rgba(255,255,255,0.06)" }}>
              <div
                className="h-full rounded-full transition-all duration-700"
                style={{
                  width: `${w.score0to100}%`,
                  background: bg,
                  boxShadow: `0 0 8px ${color}30`,
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
