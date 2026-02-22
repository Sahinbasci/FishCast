import { MODE_CONFIG } from "@/lib/constants";

interface ModeBadgeProps {
  mode: string;
}

export default function ModeBadge({ mode }: ModeBadgeProps) {
  const config = MODE_CONFIG[mode] || MODE_CONFIG.chasing;
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold backdrop-blur-md"
      style={{
        backgroundColor: `${config.color}15`,
        color: config.color,
        border: `1px solid ${config.color}25`,
        boxShadow: "inset 0 1px 0 rgba(255,255,255,0.05)",
      }}
    >
      <span
        className="w-1.5 h-1.5 rounded-full"
        style={{
          backgroundColor: config.color,
          boxShadow: `0 0 4px ${config.color}60`,
        }}
      />
      {config.label}
    </span>
  );
}
