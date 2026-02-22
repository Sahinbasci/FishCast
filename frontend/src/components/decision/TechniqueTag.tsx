interface TechniqueTagProps {
  name: string;
  type: "recommended" | "avoid";
  hint?: string | null;
  reason?: string;
}

// Assign unique colors to technique pills for visual variety
const TECHNIQUE_COLORS: Record<string, string> = {
  "Çapari": "#22c55e",
  "Kurşun Arkası": "#f59e0b",
  "Spin": "#ef4444",
  "LRF": "#06b6d4",
  "Surf": "#8b5cf6",
  "Yemli Dip": "#f97316",
  "Shore Jig": "#ec4899",
};

export default function TechniqueTag({ name, type, hint, reason }: TechniqueTagProps) {
  const isRecommended = type === "recommended";
  const fallbackColor = isRecommended ? "#22c55e" : "#ef4444";
  const dotColor = isRecommended ? (TECHNIQUE_COLORS[name] || fallbackColor) : "#ef4444";

  return (
    <div
      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold backdrop-blur-md cursor-default transition-all hover:scale-105"
      style={{
        color: isRecommended ? "var(--text-primary)" : "#f87171",
        backgroundColor: isRecommended
          ? "rgba(255, 255, 255, 0.08)"
          : "rgba(239, 68, 68, 0.10)",
        border: `1px solid ${isRecommended ? "rgba(255,255,255,0.12)" : "rgba(239,68,68,0.20)"}`,
        boxShadow: "inset 0 1px 0 rgba(255,255,255,0.04)",
      }}
      title={hint || reason || ""}
    >
      <span
        className="w-2.5 h-2.5 rounded-full flex-shrink-0"
        style={{
          backgroundColor: dotColor,
          boxShadow: `0 0 6px ${dotColor}60`,
        }}
      />
      <span>{name}</span>
    </div>
  );
}
