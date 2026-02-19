import { MODE_CONFIG } from "@/lib/constants";

interface ModeBadgeProps {
  mode: string;
}

export default function ModeBadge({ mode }: ModeBadgeProps) {
  const config = MODE_CONFIG[mode] || MODE_CONFIG.chasing;
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium"
      style={{
        backgroundColor: `${config.color}20`,
        color: config.color,
      }}
    >
      {config.emoji} {config.label}
    </span>
  );
}
