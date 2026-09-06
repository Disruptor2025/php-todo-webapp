const STYLES = {
  incoming: "bg-amber-100 text-amber-700 ring-amber-600/20",
  parsed_quoted: "bg-blue-100 text-blue-700 ring-blue-600/20",
  active: "bg-emerald-100 text-emerald-700 ring-emerald-600/20",
  audited: "bg-violet-100 text-violet-700 ring-violet-600/20",
};

const LABELS = {
  incoming: "Incoming",
  parsed_quoted: "Parsed & Quoted",
  active: "Active",
  audited: "Audited",
};

export default function StatusBadge({ status }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${
        STYLES[status] || "bg-slate-100 text-slate-600 ring-slate-500/20"
      }`}
    >
      {LABELS[status] || status}
    </span>
  );
}
