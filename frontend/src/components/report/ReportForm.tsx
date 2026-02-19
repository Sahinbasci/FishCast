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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

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
        setError("Rapor göndermek için giriş yapmalısınız");
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
      <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-green-700 text-center">
        Rapor başarıyla gönderildi!
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-sm border p-4 space-y-3">
      <h3 className="font-semibold text-gray-800">Av Raporu - {spotName}</h3>

      <div className="grid grid-cols-2 gap-3">
        <select
          value={species}
          onChange={(e) => setSpecies(e.target.value)}
          required
          className="border rounded-lg px-3 py-2 text-sm"
        >
          <option value="">Tür seçin</option>
          {Object.entries(SPECIES_NAMES_TR).map(([id, name]) => (
            <option key={id} value={id}>{name}</option>
          ))}
        </select>

        <select
          value={technique}
          onChange={(e) => setTechnique(e.target.value)}
          required
          className="border rounded-lg px-3 py-2 text-sm"
        >
          <option value="">Teknik seçin</option>
          {Object.entries(TECHNIQUE_NAMES_TR).map(([id, name]) => (
            <option key={id} value={id}>{name}</option>
          ))}
        </select>

        <input
          type="number"
          min={1}
          max={100}
          value={quantity}
          onChange={(e) => setQuantity(Number(e.target.value))}
          placeholder="Adet"
          required
          className="border rounded-lg px-3 py-2 text-sm"
        />

        <input
          type="number"
          min={1}
          max={100}
          value={avgSize}
          onChange={(e) => setAvgSize(e.target.value)}
          placeholder="Ort. boy (cm)"
          required
          className="border rounded-lg px-3 py-2 text-sm"
        />
      </div>

      <textarea
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        maxLength={500}
        placeholder="Notlar (opsiyonel)"
        className="w-full border rounded-lg px-3 py-2 text-sm"
        rows={2}
      />

      {error && <p className="text-sm text-red-600">{error}</p>}

      <button
        type="submit"
        className="w-full bg-blue-600 text-white rounded-lg py-2 text-sm font-semibold hover:bg-blue-700 transition"
      >
        Rapor Gönder
      </button>
    </form>
  );
}
