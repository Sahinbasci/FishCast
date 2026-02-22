"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { API_URL, SPECIES_NAMES_TR, TECHNIQUE_NAMES_TR } from "@/lib/constants";

interface CatchReport {
  id?: string;
  spotId: string;
  species: string;
  quantity: number;
  avgSize: string;
  technique: string;
  notes?: string;
  timestamp: string;
}

export default function CatchesPage() {
  const { user, loading: authLoading, signInWithGoogle, signOut, getIdToken, isConfigured } = useAuth();
  const [catches, setCatches] = useState<CatchReport[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;

    const fetchCatches = async () => {
      setLoading(true);
      setError(null);
      try {
        const token = await getIdToken();
        if (!token) {
          setError("Oturum suresi dolmus. Lutfen tekrar giris yapin.");
          return;
        }

        const res = await fetch(`${API_URL}/reports/user`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.status === 401) {
          setError("Oturum gecersiz. Lutfen tekrar giris yapin.");
          await signOut();
          return;
        }
        if (res.ok) {
          const data = await res.json();
          setCatches(data.reports || []);
        } else {
          setError("Raporlar yuklenemedi. Lutfen tekrar deneyin.");
        }
      } catch {
        setError("Baglanti hatasi. Lutfen internet baglantinizi kontrol edin.");
      } finally {
        setLoading(false);
      }
    };

    fetchCatches();
  }, [user, getIdToken, signOut]);

  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="w-6 h-6 border-2 border-white/40 border-t-white rounded-full animate-spin" />
      </div>
    );
  }

  if (!user) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="card p-8 text-center max-w-sm">
          <div
            className="w-12 h-12 mx-auto mb-4 rounded-xl flex items-center justify-center"
            style={{ background: "var(--gradient-ocean)" }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
          </div>
          <h2 className="text-lg font-bold text-white mb-2">Giris Gerekli</h2>
          <p className="text-[var(--text-muted)] text-sm mb-4">
            Av raporlarinizi gormek icin giris yapin.
          </p>
          {isConfigured && (
            <button
              onClick={signInWithGoogle}
              className="px-4 py-2 rounded-[var(--radius-md)] text-sm font-bold text-white"
              style={{ background: "var(--gradient-ocean)" }}
            >
              Google ile Giris Yap
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-white">Av Raporlarim</h1>
        <span className="text-xs text-[var(--text-muted)]">{catches.length} rapor</span>
      </div>

      {error && (
        <div className="card p-4 border border-[rgba(239,68,68,0.3)]">
          <p className="text-sm text-[var(--red-light)]">{error}</p>
        </div>
      )}

      {loading ? (
        <div className="card p-8 text-center">
          <div className="w-6 h-6 mx-auto mb-2 border-2 border-white/40 border-t-white rounded-full animate-spin" />
          <p className="text-[var(--text-muted)] text-sm">Yukleneniyor...</p>
        </div>
      ) : catches.length === 0 && !error ? (
        <div className="card p-8 text-center">
          <p className="text-[var(--text-muted)]">Henuz rapor gondermediniz.</p>
          <a href="/" className="text-[var(--blue-light)] text-sm mt-2 inline-block hover:text-[var(--blue-bright)]">
            Ana sayfaya don &rarr;
          </a>
        </div>
      ) : (
        <div className="space-y-3">
          {catches.map((c, i) => (
            <div key={c.id || i} className="card p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="font-semibold text-white">
                  {SPECIES_NAMES_TR[c.species] || c.species}
                </span>
                <span className="text-xs text-[var(--text-dim)]">
                  {new Date(c.timestamp).toLocaleDateString("tr-TR")}
                </span>
              </div>
              <div className="flex gap-4 text-xs text-[var(--text-secondary)]">
                <span>{c.quantity} adet</span>
                <span>{c.avgSize}</span>
                <span>{TECHNIQUE_NAMES_TR[c.technique] || c.technique}</span>
              </div>
              {c.notes && (
                <p className="mt-2 text-xs text-[var(--text-muted)]">{c.notes}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
