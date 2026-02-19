"use client";

import { useState } from "react";

interface NoGoOverlayProps {
  reasonsTR: string[];
}

export default function NoGoOverlay({ reasonsTR }: NoGoOverlayProps) {
  const [dismissed, setDismissed] = useState(false);

  if (dismissed) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-red-600/95">
      <div className="text-center text-white max-w-md px-6">
        <div className="text-8xl mb-6">&#x26D4;</div>
        <h1 className="text-3xl font-bold mb-4">
          UYARI: Bugün kıyıdan balıkçılık tehlikeli!
        </h1>
        <div className="space-y-2 mb-8">
          {reasonsTR.map((reason, i) => (
            <p key={i} className="text-lg text-red-100">
              {reason}
            </p>
          ))}
        </div>
        <button
          onClick={() => setDismissed(true)}
          className="px-6 py-3 bg-white text-red-600 rounded-lg font-semibold hover:bg-red-50 transition"
        >
          Detayları Gör
        </button>
      </div>
    </div>
  );
}
