"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { API_URL } from "@/lib/constants";
import type { SpotType } from "@/lib/types";
import SpotDetail from "@/components/spot/SpotDetail";
import ReportForm from "@/components/report/ReportForm";

export default function SpotPage() {
  const params = useParams();
  const spotId = params.id as string;
  const [spot, setSpot] = useState<SpotType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_URL}/spots/${spotId}`)
      .then((r) => {
        if (!r.ok) throw new Error("Mera bulunamadı");
        return r.json();
      })
      .then((d) => setSpot(d))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [spotId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <div className="w-12 h-12 mx-auto mb-3 rounded-[var(--radius-lg)] flex items-center justify-center" style={{ background: "var(--gradient-ocean)" }}>
            <div className="w-5 h-5 border-2 border-white/40 border-t-white rounded-full animate-spin" />
          </div>
          <p className="text-[var(--text-muted)] text-sm">Yükleniyor...</p>
        </div>
      </div>
    );
  }

  if (error || !spot) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <div className="w-12 h-12 mx-auto mb-3 rounded-full flex items-center justify-center" style={{ background: "var(--gradient-sunset)" }}>
            <span className="text-xl">&#x274C;</span>
          </div>
          <p className="text-[var(--text-secondary)] mb-2">{error || "Mera bulunamadı"}</p>
          <a href="/" className="text-[var(--blue-light)] hover:text-[var(--blue-bright)] text-sm font-semibold inline-block transition-colors">
            Ana sayfaya dön &rarr;
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <a href="/" className="inline-flex items-center gap-1 text-sm text-[var(--text-muted)] hover:text-[var(--blue-light)] transition-colors">
        <span>&larr;</span>
        <span>Ana Sayfa</span>
      </a>
      <SpotDetail spot={spot} />
      <ReportForm spotId={spot.id} spotName={spot.name} />
    </div>
  );
}
