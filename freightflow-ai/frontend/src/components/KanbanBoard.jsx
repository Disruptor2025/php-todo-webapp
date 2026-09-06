import TenderCard from "./TenderCard";

const COLUMNS = [
  { key: "incoming", title: "Incoming Tenders", accent: "border-t-amber-400" },
  { key: "parsed_quoted", title: "AI Parsed & Quoted", accent: "border-t-blue-500" },
  { key: "active", title: "Active Loads", accent: "border-t-emerald-500" },
  { key: "audited", title: "Audited Documents", accent: "border-t-violet-500" },
];

export default function KanbanBoard({ tenders, onOpen, onProcess, onAudit, busyId }) {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
      {COLUMNS.map((col) => {
        const items = tenders.filter((t) => t.status === col.key);
        return (
          <div key={col.key} className={`rounded-xl border-t-4 bg-slate-100/60 p-3 ${col.accent}`}>
            <div className="mb-3 flex items-center justify-between px-1">
              <h2 className="text-sm font-bold text-slate-700">{col.title}</h2>
              <span className="rounded-full bg-white px-2 py-0.5 text-xs font-semibold text-slate-500 shadow-sm">
                {items.length}
              </span>
            </div>
            <div className="flex flex-col gap-3">
              {items.length === 0 && (
                <p className="rounded-lg border border-dashed border-slate-300 p-4 text-center text-xs text-slate-400">
                  No tenders here
                </p>
              )}
              {items.map((t) => (
                <TenderCard
                  key={t.id}
                  tender={t}
                  onOpen={onOpen}
                  onProcess={onProcess}
                  onAudit={onAudit}
                  busy={busyId === t.id}
                />
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
