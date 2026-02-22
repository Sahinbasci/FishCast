"use client";

import { useState } from "react";

interface NoGoOverlayProps {
  reasonsTR: string[];
}

export default function NoGoOverlay({ reasonsTR }: NoGoOverlayProps) {
  const [dismissed, setDismissed] = useState(false);

  if (dismissed) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/85 backdrop-blur-xl">
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
        <div className="space-y-2 mb-8">
          {reasonsTR.map((reason, i) => (
            <p key={i} className="text-sm text-red-300">
              {reason}
            </p>
          ))}
        </div>
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
