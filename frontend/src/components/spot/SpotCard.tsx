import Link from "next/link";
import type { SpotType } from "@/lib/types";
import { REGION_COLORS, REGION_NAMES_TR } from "@/lib/constants";
import Badge from "@/components/ui/Badge";

interface SpotCardProps {
  spot: SpotType;
  score?: number;
}

export default function SpotCard({ spot, score }: SpotCardProps) {
  const regionColor = REGION_COLORS[spot.regionId] || "#3b82f6";
  const regionName = REGION_NAMES_TR[spot.regionId] || spot.regionId;

  return (
    <Link href={`/spot/${spot.id}`} className="block">
      <div className="card-interactive p-3.5">
        <div className="flex items-center justify-between mb-1.5">
          <span className="font-semibold text-white text-sm">{spot.name}</span>
          {score !== undefined && (
            <span className="text-sm font-bold text-blue-400">{score}</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Badge label={regionName} color={regionColor} />
          {spot.pelagicCorridor && (
            <Badge label="Pelajik" color="#8b5cf6" />
          )}
        </div>
      </div>
    </Link>
  );
}
