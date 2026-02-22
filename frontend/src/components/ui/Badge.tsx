interface BadgeProps {
  label: string;
  color?: string;
  bgColor?: string;
}

export default function Badge({ label, color = "#3b82f6" }: BadgeProps) {
  return (
    <span
      className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold backdrop-blur-sm"
      style={{
        color,
        backgroundColor: `${color}12`,
        border: `1px solid ${color}20`,
        boxShadow: "inset 0 1px 0 rgba(255,255,255,0.04)",
      }}
    >
      {label}
    </span>
  );
}
