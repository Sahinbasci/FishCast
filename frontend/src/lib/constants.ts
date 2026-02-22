/**
 * FishCast frontend constants.
 * API URL, region colors, species/technique Turkish names.
 */

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

/** Region pin renkleri */
export const REGION_COLORS: Record<string, string> = {
  avrupa: "#3b82f6",
  anadolu: "#ef4444",
  city_belt: "#f97316",
};

/** Region Türkçe adları */
export const REGION_NAMES_TR: Record<string, string> = {
  avrupa: "Avrupa Yakası",
  anadolu: "Anadolu Yakası",
  city_belt: "Şehir Hattı",
};

/** Tür Türkçe adları */
export const SPECIES_NAMES_TR: Record<string, string> = {
  istavrit: "İstavrit",
  cinekop: "Çinekop",
  sarikanat: "Sarıkanat",
  palamut: "Palamut",
  karagoz: "Karagöz",
  lufer: "Lüfer",
  levrek: "Levrek",
  kolyoz: "Kolyoz",
  mirmir: "Mırmır",
};

/** Teknik Türkçe adları */
export const TECHNIQUE_NAMES_TR: Record<string, string> = {
  capari: "Çapari",
  kursun_arkasi: "Kurşun Arkası",
  spin: "Spin",
  lrf: "LRF",
  surf: "Surf",
  yemli_dip: "Yemli Dip",
  shore_jig: "Shore Jig",
};

/** Skor renkleri — vibrant */
export function getScoreColor(score: number): string {
  if (score >= 70) return "#22c55e";
  if (score >= 40) return "#f97316";
  return "#ef4444";
}

/** Skor gradient background */
export function getScoreBg(score: number): string {
  if (score >= 70) return "linear-gradient(135deg, #22c55e, #06b6d4)";
  if (score >= 40) return "linear-gradient(135deg, #f97316, #f59e0b)";
  return "linear-gradient(135deg, #ef4444, #f97316)";
}

/** Mode badge bilgisi */
export const MODE_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  chasing: { label: "Aktif", color: "#22c55e", bg: "rgba(34, 197, 94, 0.15)" },
  selective: { label: "Seçici", color: "#f97316", bg: "rgba(249, 115, 22, 0.15)" },
  holding: { label: "Pasif", color: "#ef4444", bg: "rgba(239, 68, 68, 0.15)" },
};

/** SeasonStatus UI config — v1.3.2 */
export const SEASON_STATUS_CONFIG: Record<string, { label: string; color: string; bg: string; showBreakdown: boolean }> = {
  peak:     { label: "Sezon Zirvesi",               color: "#22c55e", bg: "rgba(34,197,94,0.12)",  showBreakdown: true },
  shoulder: { label: "Geçiş Dönemi",                color: "#06b6d4", bg: "rgba(6,182,212,0.12)",  showBreakdown: true },
  active:   { label: "Sezonda",                     color: "#f59e0b", bg: "rgba(245,158,11,0.12)", showBreakdown: true },
  off:      { label: "Sezon Dışı (Parça İhtimali)", color: "#8b5cf6", bg: "rgba(139,92,246,0.12)", showBreakdown: false },
  closed:   { label: "Kapalı (Legacy)",             color: "var(--text-dim)", bg: "var(--glass-bg-strong)", showBreakdown: false },
};

/** Harita varsayılan merkez (Istanbul Boğazı) */
export const MAP_CENTER: [number, number] = [41.06, 29.03];
export const MAP_ZOOM = 12;
