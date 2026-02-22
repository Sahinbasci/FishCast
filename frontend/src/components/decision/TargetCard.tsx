import type { DecisionTargetType } from "@/lib/types";
import ScoreGauge from "@/components/ui/ScoreGauge";
import ModeBadge from "@/components/ui/ModeBadge";
import ConfidenceDot from "@/components/ui/ConfidenceDot";

interface TargetCardProps {
  target: DecisionTargetType;
}

export default function TargetCard({ target }: TargetCardProps) {
  return (
    <div
      className="flex items-center gap-3.5 rounded-2xl p-3 transition-all hover:bg-white/[0.06]"
      style={{
        background: "rgba(255, 255, 255, 0.04)",
        border: "1px solid rgba(255, 255, 255, 0.06)",
      }}
    >
      <ScoreGauge score={target.score0to100} size="md" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-bold text-white text-base truncate">
            {target.speciesNameTR}
          </span>
          <ModeBadge mode={target.mode} />
        </div>
        <ConfidenceDot confidence={target.confidence0to1} />
      </div>
    </div>
  );
}
