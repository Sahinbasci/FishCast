/**
 * FishCast frontend constants.
 * API URL, region colors, species/technique Turkish names.
 */

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

/** Region pin renkleri */
export const REGION_COLORS: Record<string, string> = {
  avrupa: "#3B82F6",    // mavi
  anadolu: "#EF4444",   // kırmızı
  city_belt: "#F97316",  // turuncu
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

/** Skor renkleri */
export function getScoreColor(score: number): string {
  if (score >= 70) return "#22C55E"; // yeşil
  if (score >= 40) return "#EAB308"; // sarı
  return "#EF4444"; // kırmızı
}

/** Mode badge bilgisi */
export const MODE_CONFIG: Record<string, { emoji: string; label: string; color: string }> = {
  chasing: { emoji: "🟢", label: "Aktif", color: "#22C55E" },
  selective: { emoji: "🟡", label: "Seçici", color: "#EAB308" },
  holding: { emoji: "🔴", label: "Pasif", color: "#EF4444" },
};

/** Harita varsayılan merkez (Istanbul Boğazı) */
export const MAP_CENTER: [number, number] = [41.06, 29.03];
export const MAP_ZOOM = 12;
