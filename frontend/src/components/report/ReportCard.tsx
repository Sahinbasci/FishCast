import { SPECIES_NAMES_TR, TECHNIQUE_NAMES_TR } from "@/lib/constants";

interface Report {
  species: string;
  technique: string;
  quantity: number;
  avgSize: string;
  timestamp: string;
  notes?: string;
}

interface ReportCardProps {
  report: Report;
}

export default function ReportCard({ report }: ReportCardProps) {
  const speciesName = SPECIES_NAMES_TR[report.species] || report.species;
  const techniqueName = TECHNIQUE_NAMES_TR[report.technique] || report.technique;
  const date = new Date(report.timestamp);
  const timeStr = date.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" });

  return (
    <div
      className="rounded-2xl p-3.5"
      style={{
        background: "var(--glass-bg-strong)",
        border: "1px solid var(--border-subtle)",
      }}
    >
      <div className="flex items-center justify-between">
        <span className="font-semibold text-white text-sm">
          {speciesName} x{report.quantity}
        </span>
        <span className="text-xs text-slate-500">{timeStr}</span>
      </div>
      <div className="text-xs text-slate-400 mt-1">
        {techniqueName} &middot; {report.avgSize}
      </div>
      {report.notes && (
        <p className="text-xs text-slate-500 mt-1">{report.notes}</p>
      )}
    </div>
  );
}
