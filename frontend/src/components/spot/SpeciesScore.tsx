import type { SpeciesScoreType } from "@/lib/types";
import ScoreGauge from "@/components/ui/ScoreGauge";
import ModeBadge from "@/components/ui/ModeBadge";
import ConfidenceDot from "@/components/ui/ConfidenceDot";
import TechniqueTag from "@/components/decision/TechniqueTag";
import { SEASON_STATUS_CONFIG } from "@/lib/constants";

interface SpeciesScoreProps {
  species: SpeciesScoreType;
}

export default function SpeciesScoreRow({ species }: SpeciesScoreProps) {
  const seasonCfg = SEASON_STATUS_CONFIG[species.seasonStatus];
  const isDimmed = species.seasonStatus === "closed" || species.seasonStatus === "off";

  return (
    <div className={`card p-5 text-center ${isDimmed ? "opacity-40" : ""}`}>
      {/* Score Gauge — prominent, centered */}
      <div className="flex justify-center mb-3">
        <ScoreGauge score={species.score0to100} size="lg" noGo={species.suppressedByNoGo} />
      </div>

      {/* Name + Status */}
      <div className="mb-2">
        <span className="font-bold text-white text-base">{species.speciesNameTR}</span>
        <div className="flex items-center justify-center gap-2 mt-1.5">
          <ModeBadge mode={species.mode} />
          {seasonCfg && species.seasonStatus !== "active" && (
            <span
              className="text-[11px] font-semibold px-2 py-0.5 rounded-full"
              style={{
                color: seasonCfg.color,
                backgroundColor: seasonCfg.bg,
                border: `1px solid ${seasonCfg.color}25`,
              }}
            >
              {seasonCfg.label}
            </span>
          )}
        </div>
      </div>

      {/* Confidence + Best Time */}
      <div className="flex items-center justify-center gap-3 mb-3">
        <ConfidenceDot confidence={species.confidence0to1} />
        {species.bestTime && (
          <span className="text-xs text-slate-500">En iyi: {species.bestTime}</span>
        )}
      </div>

      {/* Techniques */}
      {(species.recommendedTechniques.length > 0 || species.avoidTechniques.length > 0) && (
        <div className="flex flex-wrap justify-center gap-1.5 mb-3">
          {species.recommendedTechniques.map((t) => (
            <TechniqueTag key={t.techniqueId} name={t.techniqueNameTR} type="recommended" hint={t.setupHintTR} />
          ))}
          {species.avoidTechniques.map((t) => (
            <TechniqueTag key={t.techniqueId} name={t.techniqueNameTR} type="avoid" reason={t.reasonTR} />
          ))}
        </div>
      )}

      {/* Breakdown — gated by seasonCfg.showBreakdown */}
      {species.breakdown && seasonCfg?.showBreakdown !== false && (
        <div
          className="grid grid-cols-5 gap-1 pt-3 text-xs"
          style={{ borderTop: "1px solid rgba(255,255,255,0.06)" }}
        >
          {[
            { label: "Basınç", value: species.breakdown.pressure },
            { label: "Rüzgar", value: species.breakdown.wind },
            { label: "Su", value: species.breakdown.seaTemp },
            { label: "Solunar", value: species.breakdown.solunar },
            { label: "Zaman", value: species.breakdown.time },
          ].map((item) => (
            <div key={item.label} className="text-center">
              <span className="text-slate-500 block text-[10px]">{item.label}</span>
              <span className="text-slate-300 font-semibold">{(item.value * 100).toFixed(0)}%</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
