"use client";

import { useState } from "react";

interface ShelteredExceptionType {
  spotId: string;
  spotNameTR?: string;
  allowedTechniques: string[];
  warningLevel: string;
  messageTR: string;
}

interface NoGoOverlayProps {
  reasonsTR: string[];
  shelteredExceptions?: ShelteredExceptionType[];
}

export default function NoGoOverlay({
  reasonsTR,
  shelteredExceptions,
}: NoGoOverlayProps) {
  const [dismissed, setDismissed] = useState(false);

  if (dismissed) return null;

  const hasAlternatives =
    shelteredExceptions && shelteredExceptions.length > 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/85 backdrop-blur-xl overflow-y-auto py-8">
      <div className="text-center max-w-md px-6">
        <div
          className="w-20 h-20 mx-auto mb-6 rounded-full flex items-center justify-center"
          style={{ background: "var(--gradient-sunset)" }}
        >
          <span className="text-4xl">&#x26D4;</span>
        </div>
        <h1 className="text-2xl font-bold text-white mb-4">
          Bugün kıyıdan balıkçılık tehlikeli!
        </h1>
        <div className="space-y-2 mb-6">
          {reasonsTR.map((reason, i) => (
            <p key={i} className="text-sm text-red-300">
              {reason}
            </p>
          ))}
        </div>

        {/* Sheltered Alternatives */}
        {hasAlternatives && (
          <div className="mb-6 text-left">
            <div className="border border-amber-500/30 rounded-xl bg-amber-950/20 p-4">
              <h2 className="text-sm font-bold text-amber-400 mb-3 text-center">
                Korunaklı Alternatifler
              </h2>
              <div className="space-y-3">
                {shelteredExceptions!.map((exc) => (
                  <div
                    key={exc.spotId}
                    className="bg-slate-800/60 rounded-lg p-3"
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-amber-400 text-xs">&#x26A0;</span>
                      <span className="text-sm font-semibold text-white">
                        {exc.spotNameTR || exc.spotId}
                      </span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 font-medium uppercase">
                        {exc.warningLevel}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 mb-1.5">
                      {exc.messageTR}
                    </p>
                    <div className="flex gap-1.5 flex-wrap">
                      {exc.allowedTechniques.map((tech) => (
                        <span
                          key={tech}
                          className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 font-medium"
                        >
                          {tech.toUpperCase()}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        <button
          onClick={() => setDismissed(true)}
          className="px-8 py-3 rounded-xl text-sm font-bold text-white transition-all hover:scale-105 active:scale-95"
          style={{ background: "var(--gradient-ocean)" }}
        >
          Detayları Gör
        </button>
      </div>
    </div>
  );
}
