import { Sparkles, CheckCircle2, ClipboardCheck, FileText, Mail } from "lucide-react";
import StatusBadge from "./StatusBadge";

const fmtMoney = (n) =>
  n == null ? "—" : `$${Number(n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export default function TenderCard({ tender, onOpen, onProcess, onAudit, busy }) {
  const lane =
    tender.origin && tender.destination ? `${tender.origin} → ${tender.destination}` : "Lane not yet parsed";

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-sm font-semibold text-slate-800">#{tender.id} · {lane}</p>
          <p className="mt-0.5 flex items-center gap-1 text-xs text-slate-400">
            {tender.source === "email" ? <Mail size={12} /> : <FileText size={12} />}
            {tender.filename || tender.source}
          </p>
        </div>
        <StatusBadge status={tender.status} />
      </div>

      {tender.equipment_type && (
        <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
          <span>{tender.equipment_type}</span>
          {tender.weight_lbs && <span>{tender.weight_lbs.toLocaleString()} lbs</span>}
          {tender.pickup_date && <span>Pickup {tender.pickup_date}</span>}
        </div>
      )}

      {tender.status === "incoming" && (
        <p className="mt-3 line-clamp-2 text-xs text-slate-400">{tender.raw_text}</p>
      )}

      {(tender.status === "parsed_quoted" || tender.status === "active" || tender.status === "audited") && (
        <div className="mt-3 flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2">
          <div>
            <p className="text-[11px] uppercase tracking-wide text-slate-400">
              {tender.status === "parsed_quoted" ? "Recommended Rate" : "Final Rate"}
            </p>
            <p className="text-base font-bold text-slate-800">
              {fmtMoney(tender.status === "parsed_quoted" ? tender.recommended_rate : tender.final_rate)}
            </p>
          </div>
          <div className="text-right">
            <p className="text-[11px] uppercase tracking-wide text-slate-400">Margin</p>
            <p className="text-sm font-semibold text-emerald-600">
              {tender.estimated_margin_pct != null ? `${(tender.estimated_margin_pct * 100).toFixed(1)}%` : "—"}
            </p>
          </div>
        </div>
      )}

      <div className="mt-4 flex gap-2">
        {tender.status === "incoming" && (
          <button
            onClick={() => onProcess(tender.id)}
            disabled={busy}
            className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
          >
            <Sparkles size={14} /> {busy ? "Parsing…" : "Run AI Parse & Quote"}
          </button>
        )}
        {tender.status === "parsed_quoted" && (
          <button
            onClick={() => onOpen(tender)}
            className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-700"
          >
            <CheckCircle2 size={14} /> Review Quote
          </button>
        )}
        {tender.status === "active" && (
          <>
            <button
              onClick={() => onOpen(tender)}
              className="flex-1 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-50"
            >
              View
            </button>
            <button
              onClick={() => onAudit(tender.id)}
              disabled={busy}
              className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-violet-700 disabled:opacity-50"
            >
              <ClipboardCheck size={14} /> Mark Audited
            </button>
          </>
        )}
        {tender.status === "audited" && (
          <button
            onClick={() => onOpen(tender)}
            className="flex-1 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-50"
          >
            View Documents
          </button>
        )}
      </div>
    </div>
  );
}
