"use client";

import { useState } from "react";
import { API_URL, SPECIES_NAMES_TR, TECHNIQUE_NAMES_TR } from "@/lib/constants";

interface ReportFormProps {
  spotId: string;
  spotName: string;
}

export default function ReportForm({ spotId, spotName }: ReportFormProps) {
  const [species, setSpecies] = useState("");
  const [technique, setTechnique] = useState("");
  const [quantity, setQuantity] = useState(1);
  const [avgSize, setAvgSize] = useState("");
  const [notes, setNotes] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");
  const [needsAuth, setNeedsAuth] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setNeedsAuth(false);

    try {
      const res = await fetch(`${API_URL}/reports`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          spotId,
          species,
          technique,
          quantity,
          avgSize: `${avgSize}cm`,
          notes: notes || null,
          photoUrl: null,
          bait: null,
        }),
      });

      if (res.status === 401) {
        setNeedsAuth(true);
        return;
      }
      if (!res.ok) throw new Error("Gönderim hatası");

      setSubmitted(true);
    } catch {
      setError("Rapor gönderilemedi. Lütfen tekrar deneyin.");
    }
  };

  if (submitted) {
    return (
      <div className="card p-6 text-center">
        <div
          className="w-12 h-12 mx-auto mb-3 rounded-full flex items-center justify-center"
          style={{ background: "var(--gradient-success)" }}
        >
          <span className="text-xl">&#x2705;</span>
        </div>
        <p className="text-[var(--green-primary)] font-semibold">Rapor başarıyla gönderildi!</p>
        <button
          onClick={() => {
            setSubmitted(false);
            setSpecies("");
            setTechnique("");
            setQuantity(1);
            setAvgSize("");
            setNotes("");
          }}
          className="mt-3 text-sm text-[var(--blue-light)] hover:text-[var(--blue-bright)] underline underline-offset-4 transition-colors"
        >
          Yeni rapor gönder
        </button>
      </div>
    );
  }

  const inputClass =
    "w-full border border-[var(--border-subtle)] rounded-[var(--radius-md)] px-3.5 py-2.5 text-sm bg-[var(--bg-input)] text-[var(--text-primary)] placeholder-[var(--text-dim)] focus:bg-[var(--bg-card-alt)] focus:border-[var(--border-blue)] focus:ring-1 focus:ring-[var(--blue-primary)]/20 outline-none transition-all";

  return (
    <form onSubmit={handleSubmit} className="card p-5 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-bold text-white text-lg">Av Raporu &mdash; {spotName}</h3>
        <span className="text-xs text-[var(--text-muted)] font-medium">Topluluk verisi</span>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <select value={species} onChange={(e) => setSpecies(e.target.value)} required className={inputClass}>
          <option value="">Tür seçin</option>
          {Object.entries(SPECIES_NAMES_TR).map(([id, name]) => (
            <option key={id} value={id}>{name}</option>
          ))}
        </select>

        <select value={technique} onChange={(e) => setTechnique(e.target.value)} required className={inputClass}>
          <option value="">Teknik seçin</option>
          {Object.entries(TECHNIQUE_NAMES_TR).map(([id, name]) => (
            <option key={id} value={id}>{name}</option>
          ))}
        </select>

        <input type="number" min={1} max={100} value={quantity} onChange={(e) => setQuantity(Number(e.target.value))} placeholder="Adet" required className={inputClass} />
        <input type="number" min={1} max={100} value={avgSize} onChange={(e) => setAvgSize(e.target.value)} placeholder="Ort. boy (cm)" required className={inputClass} />
      </div>

      <textarea value={notes} onChange={(e) => setNotes(e.target.value)} maxLength={500} placeholder="Notlar (opsiyonel)" className={`${inputClass} resize-none`} rows={2} />

      {needsAuth && (
        <div className="bg-[rgba(249,115,22,0.08)] border border-[rgba(249,115,22,0.2)] rounded-[var(--radius-md)] p-3.5">
          <p className="text-[var(--orange-primary)] font-semibold mb-1 text-sm">Rapor göndermek için giriş yapmalısınız</p>
          <p className="text-[var(--orange-warm)] opacity-60 text-xs">Firebase Authentication henüz yapılandırılmamış.</p>
        </div>
      )}

      {error && (
        <div className="bg-[rgba(239,68,68,0.08)] border border-[rgba(239,68,68,0.2)] rounded-[var(--radius-md)] p-3.5">
          <p className="text-sm text-[var(--red-light)]">{error}</p>
        </div>
      )}

      <button
        type="submit"
        className="w-full rounded-[var(--radius-md)] py-2.5 text-sm font-bold text-white transition-all active:scale-[0.98]"
        style={{ background: "var(--gradient-ocean)" }}
      >
        Rapor Gönder
      </button>
    </form>
  );
}
