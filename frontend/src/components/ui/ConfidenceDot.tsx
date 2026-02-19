interface ConfidenceDotProps {
  confidence: number;
}

export default function ConfidenceDot({ confidence }: ConfidenceDotProps) {
  const color = confidence >= 0.7 ? "#22C55E" : confidence >= 0.4 ? "#EAB308" : "#EF4444";
  const label = confidence >= 0.7 ? "Yüksek" : confidence >= 0.4 ? "Orta" : "Düşük";

  return (
    <span className="inline-flex items-center gap-1 text-xs text-gray-500">
      <span className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
      {label} ({Math.round(confidence * 100)}%)
    </span>
  );
}
