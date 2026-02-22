import { getScoreColor } from "@/lib/constants";

interface ScoreGaugeProps {
  score: number;
  size?: "sm" | "md" | "lg" | "xl";
  noGo?: boolean;
}

export default function ScoreGauge({ score, size = "md", noGo = false }: ScoreGaugeProps) {
  const sizeConfig = {
    sm: { wh: "w-10 h-10", text: "text-sm", ring: 36, stroke: 3, r: 15 },
    md: { wh: "w-14 h-14", text: "text-lg", ring: 52, stroke: 3.5, r: 22 },
    lg: { wh: "w-20 h-20", text: "text-2xl", ring: 76, stroke: 4, r: 32 },
    xl: { wh: "w-28 h-28", text: "text-4xl", ring: 108, stroke: 5, r: 46 },
  };

  const cfg = sizeConfig[size];

  if (noGo) {
    return (
      <div
        className={`${cfg.wh} rounded-full flex items-center justify-center`}
        style={{
          background: "var(--glass-bg-strong)",
          border: "1px solid var(--border-subtle)",
        }}
      >
        <span className="text-[var(--text-dim)]">&#x26D4;</span>
      </div>
    );
  }

  const color = getScoreColor(score);
  const circumference = 2 * Math.PI * cfg.r;
  const progress = (score / 100) * circumference;

  return (
    <div className={`${cfg.wh} relative flex items-center justify-center flex-shrink-0`}>
      <svg className="absolute inset-0 -rotate-90" viewBox={`0 0 ${cfg.ring} ${cfg.ring}`}>
        {/* Track */}
        <circle
          cx={cfg.ring / 2}
          cy={cfg.ring / 2}
          r={cfg.r}
          fill="none"
          stroke="rgba(255,255,255,0.08)"
          strokeWidth={cfg.stroke}
        />
        {/* Progress */}
        <circle
          cx={cfg.ring / 2}
          cy={cfg.ring / 2}
          r={cfg.r}
          fill="none"
          stroke={color}
          strokeWidth={cfg.stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference - progress}
          style={{
            filter: `drop-shadow(0 0 8px ${color}80)`,
            transition: "stroke-dashoffset 1s cubic-bezier(0.16, 1, 0.3, 1)",
          }}
        />
      </svg>
      <span
        className={`${cfg.text} font-bold`}
        style={{
          color,
          textShadow: score >= 70 ? `0 0 12px ${color}60` : "none",
        }}
      >
        {score}
      </span>
    </div>
  );
}
