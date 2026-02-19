import type { DecisionTargetType } from "@/lib/types";
import ScoreGauge from "@/components/ui/ScoreGauge";
import ModeBadge from "@/components/ui/ModeBadge";
import ConfidenceDot from "@/components/ui/ConfidenceDot";

interface TargetCardProps {
  target: DecisionTargetType;
}

export default function TargetCard({ target }: TargetCardProps) {
  return (
    <div className="flex items-center gap-3 bg-gray-50 rounded-lg p-2">
      <ScoreGauge score={target.score0to100} size="sm" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium text-gray-800 text-sm truncate">
            {target.speciesNameTR}
          </span>
          <ModeBadge mode={target.mode} />
        </div>
        <ConfidenceDot confidence={target.confidence0to1} />
      </div>
    </div>
  );
}
