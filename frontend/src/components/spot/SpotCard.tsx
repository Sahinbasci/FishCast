import Link from "next/link";
import type { SpotType } from "@/lib/types";
import { REGION_COLORS, REGION_NAMES_TR } from "@/lib/constants";
import Badge from "@/components/ui/Badge";

interface SpotCardProps {
  spot: SpotType;
  score?: number;
}

export default function SpotCard({ spot, score }: SpotCardProps) {
  const regionColor = REGION_COLORS[spot.regionId] || "#3B82F6";
  const regionName = REGION_NAMES_TR[spot.regionId] || spot.regionId;

  return (
    <Link href={`/spot/${spot.id}`} className="block">
      <div className="bg-white rounded-lg shadow-sm border border-gray-100 p-3 hover:shadow-md transition">
        <div className="flex items-center justify-between mb-1">
          <span className="font-semibold text-gray-800">{spot.name}</span>
          {score !== undefined && (
            <span className="text-sm font-bold text-blue-600">{score}</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Badge label={regionName} color={regionColor} bgColor={`${regionColor}20`} />
          {spot.pelagicCorridor && (
            <Badge label="Pelajik" color="#6366F1" bgColor="#EEF2FF" />
          )}
        </div>
      </div>
    </Link>
  );
}
