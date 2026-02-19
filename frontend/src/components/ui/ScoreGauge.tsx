import { getScoreColor } from "@/lib/constants";

interface ScoreGaugeProps {
  score: number;
  size?: "sm" | "md" | "lg";
  noGo?: boolean;
}

export default function ScoreGauge({ score, size = "md", noGo = false }: ScoreGaugeProps) {
  const sizeClasses = {
    sm: "w-10 h-10 text-sm",
    md: "w-14 h-14 text-lg",
    lg: "w-20 h-20 text-2xl",
  };

  if (noGo) {
    return (
      <div className={`${sizeClasses[size]} rounded-full bg-gray-200 flex items-center justify-center font-bold`}>
        <span className="text-gray-500">&#x26D4;</span>
      </div>
    );
  }

  const color = getScoreColor(score);

  return (
    <div
      className={`${sizeClasses[size]} rounded-full flex items-center justify-center font-bold text-white`}
      style={{ backgroundColor: color }}
    >
      {score}
    </div>
  );
}
