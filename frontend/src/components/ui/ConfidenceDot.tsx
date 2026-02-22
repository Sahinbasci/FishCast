interface ConfidenceDotProps {
  confidence: number;
}

export default function ConfidenceDot({ confidence }: ConfidenceDotProps) {
  const color = confidence >= 0.7 ? "#22c55e" : confidence >= 0.4 ? "#f97316" : "#ef4444";
  const label = confidence >= 0.7 ? "Yüksek" : confidence >= 0.4 ? "Orta" : "Düşük";

  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-[var(--text-muted)]">
      <span
        className="w-2 h-2 rounded-full"
        style={{
          backgroundColor: color,
          boxShadow: `0 0 8px ${color}50`,
        }}
      />
      {label} ({Math.round(confidence * 100)}%)
    </span>
  );
}
