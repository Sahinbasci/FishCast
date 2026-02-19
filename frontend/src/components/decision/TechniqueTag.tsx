interface TechniqueTagProps {
  name: string;
  type: "recommended" | "avoid";
  hint?: string | null;
  reason?: string;
}

export default function TechniqueTag({ name, type, hint, reason }: TechniqueTagProps) {
  const isRecommended = type === "recommended";
  return (
    <div
      className={`inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium ${
        isRecommended
          ? "bg-green-50 text-green-700 border border-green-200"
          : "bg-red-50 text-red-700 border border-red-200"
      }`}
      title={hint || reason || ""}
    >
      <span>{isRecommended ? "+" : "-"}</span>
      <span>{name}</span>
    </div>
  );
}
