import type { SpeciesScoreType } from "@/lib/types";
import ScoreGauge from "@/components/ui/ScoreGauge";
import ModeBadge from "@/components/ui/ModeBadge";
import ConfidenceDot from "@/components/ui/ConfidenceDot";
import TechniqueTag from "@/components/decision/TechniqueTag";

interface SpeciesScoreProps {
  species: SpeciesScoreType;
}

export default function SpeciesScoreRow({ species }: SpeciesScoreProps) {
  const isClosed = species.seasonStatus === "closed";

  return (
    <div className={`border rounded-lg p-3 ${isClosed ? "opacity-50 bg-gray-50" : "bg-white"}`}>
      <div className="flex items-center gap-3">
        <ScoreGauge score={species.score0to100} size="sm" noGo={species.suppressedByNoGo} />
        <div className="flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-gray-800">{species.speciesNameTR}</span>
            <ModeBadge mode={species.mode} />
            {species.seasonStatus === "peak" && (
              <span className="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded">Pik Sezon</span>
            )}
            {isClosed && (
              <span className="text-xs bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">Sezon Dışı</span>
            )}
          </div>
          <div className="flex items-center gap-2 mt-1">
            <ConfidenceDot confidence={species.confidence0to1} />
            {species.bestTime && (
              <span className="text-xs text-gray-400">En iyi: {species.bestTime}</span>
            )}
          </div>
        </div>
      </div>

      {/* Techniques */}
      {(species.recommendedTechniques.length > 0 || species.avoidTechniques.length > 0) && (
        <div className="flex flex-wrap gap-1 mt-2">
          {species.recommendedTechniques.map((t) => (
            <TechniqueTag key={t.techniqueId} name={t.techniqueNameTR} type="recommended" hint={t.setupHintTR} />
          ))}
          {species.avoidTechniques.map((t) => (
            <TechniqueTag key={t.techniqueId} name={t.techniqueNameTR} type="avoid" reason={t.reasonTR} />
          ))}
        </div>
      )}

      {/* Breakdown */}
      {species.breakdown && !isClosed && (
        <div className="grid grid-cols-5 gap-1 mt-2 text-xs text-gray-400">
          <div>Basınç: {(species.breakdown.pressure * 100).toFixed(0)}%</div>
          <div>Rüzgar: {(species.breakdown.wind * 100).toFixed(0)}%</div>
          <div>Su: {(species.breakdown.seaTemp * 100).toFixed(0)}%</div>
          <div>Solunar: {(species.breakdown.solunar * 100).toFixed(0)}%</div>
          <div>Zaman: {(species.breakdown.time * 100).toFixed(0)}%</div>
        </div>
      )}
    </div>
  );
}
