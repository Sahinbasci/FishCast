"use client";

import type { BestWindowType } from "@/lib/types";
import { getScoreColor } from "@/lib/constants";

interface BestWindowsProps {
  windows: BestWindowType[];
}

export default function BestWindows({ windows }: BestWindowsProps) {
  if (!windows.length) return null;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
      <h2 className="text-lg font-semibold text-gray-800 mb-3">En İyi Zaman Pencereleri</h2>
      <div className="flex gap-3 overflow-x-auto pb-2">
        {windows.map((w, i) => (
          <div
            key={i}
            className="flex-shrink-0 min-w-[160px] rounded-lg border-2 p-3"
            style={{ borderColor: getScoreColor(w.score0to100) }}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="font-semibold text-gray-800">
                {w.startLocal} - {w.endLocal}
              </span>
              <span
                className="text-sm font-bold px-2 py-0.5 rounded-full text-white"
                style={{ backgroundColor: getScoreColor(w.score0to100) }}
              >
                {w.score0to100}
              </span>
            </div>
            <div className="space-y-1">
              {w.reasonsTR.map((r, j) => (
                <div key={j} className="text-xs text-gray-500">
                  {r}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
