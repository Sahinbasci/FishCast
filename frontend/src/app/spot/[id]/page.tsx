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
          <div className="text-4xl mb-4 animate-pulse">&#x1F3A3;</div>
          <p className="text-gray-500">Yükleniyor...</p>
        </div>
      </div>
    );
  }

  if (error || !spot) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <div className="text-4xl mb-4">&#x274C;</div>
          <p className="text-gray-500">{error || "Mera bulunamadı"}</p>
          <a href="/" className="text-blue-600 hover:underline text-sm mt-2 inline-block">
            Ana sayfaya dön
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <a href="/" className="text-sm text-blue-600 hover:underline">
        &larr; Ana Sayfa
      </a>
      <SpotDetail spot={spot} />
      <ReportForm spotId={spot.id} spotName={spot.name} />
    </div>
  );
}
