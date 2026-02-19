interface BadgeProps {
  label: string;
  color?: string;
  bgColor?: string;
}

export default function Badge({ label, color = "#1E3A5F", bgColor = "#E0F2FE" }: BadgeProps) {
  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium"
      style={{ color, backgroundColor: bgColor }}
    >
      {label}
    </span>
  );
}
