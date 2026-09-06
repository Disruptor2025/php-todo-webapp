import { useEffect, useState } from "react";
import { X, Download, CheckCircle2, PenLine } from "lucide-react";
import StatusBadge from "./StatusBadge";
import { getQuote, pdfUrl } from "../api";

const fmtMoney = (n) =>
  n == null ? "—" : `$${Number(n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const Field = ({ label, value }) => (
  <div>
    <p className="text-[11px] uppercase tracking-wide text-slate-400">{label}</p>
    <p className="text-sm font-medium text-slate-700">{value ?? "—"}</p>
  </div>
);

export default function TenderDetailModal({ tender, onClose, onDecide, busy }) {
  const [quote, setQuote] = useState(null);
  const [overrideMode, setOverrideMode] = useState(false);
  const [overrideRate, setOverrideRate] = useState(tender.recommended_rate || "");
  const [note, setNote] = useState("");

  useEffect(() => {
    if (["parsed_quoted", "active", "audited"].includes(tender.status)) {
      getQuote(tender.id).then(setQuote).catch(() => setQuote(null));
    }
  }, [tender.id, tender.status]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4">
      <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          <div className="flex items-center gap-2">
            <h3 className="text-base font-bold text-slate-800">Tender #{tender.id}</h3>
            <StatusBadge status={tender.status} />
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <X size={18} />
          </button>
        </div>

        <div className="space-y-5 p-5">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            <Field label="Origin" value={tender.origin} />
            <Field label="Destination" value={tender.destination} />
            <Field label="Equipment" value={tender.equipment_type} />
            <Field label="Weight" value={tender.weight_lbs ? `${tender.weight_lbs.toLocaleString()} lbs` : null} />
            <Field label="Pickup Date" value={tender.pickup_date} />
            <Field label="Commodity" value={tender.commodity} />
            <Field label="Est. Miles" value={tender.miles} />
            <Field
              label="Parser"
              value={tender.parser_used ? `${tender.parser_used} (${Math.round((tender.parse_confidence || 0) * 100)}% conf.)` : null}
            />
            <Field label="Lane Match" value={tender.lane_match_type} />
          </div>

          {tender.recommended_rate != null && (
            <div className="rounded-xl bg-slate-50 p-4">
              <p className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">Rate Engine Breakdown</p>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <Field label="Carrier Cost" value={fmtMoney(tender.carrier_cost_estimate)} />
                <Field label="Fuel Surcharge" value={fmtMoney(tender.fuel_surcharge_amount)} />
                <Field label="Recommended Rate" value={fmtMoney(tender.recommended_rate)} />
                <Field
                  label="Est. Margin"
                  value={tender.estimated_margin_pct != null ? `${(tender.estimated_margin_pct * 100).toFixed(1)}%` : null}
                />
              </div>
              {tender.final_rate != null && (
                <div className="mt-3 flex items-center justify-between rounded-lg bg-white px-3 py-2">
                  <span className="text-xs font-semibold text-slate-500">
                    Final Rate ({tender.decision || "pending"})
                  </span>
                  <span className="text-base font-bold text-slate-800">{fmtMoney(tender.final_rate)}</span>
                </div>
              )}
            </div>
          )}

          <div>
            <p className="mb-1 text-xs font-bold uppercase tracking-wide text-slate-500">Raw Source Text</p>
            <pre className="max-h-32 overflow-y-auto whitespace-pre-wrap rounded-lg bg-slate-900 p-3 text-[11px] leading-relaxed text-slate-200">
              {tender.raw_text}
            </pre>
          </div>

          {quote?.email_draft && (
            <div>
              <p className="mb-1 text-xs font-bold uppercase tracking-wide text-slate-500">AI-Drafted Client Email</p>
              <pre className="max-h-40 overflow-y-auto whitespace-pre-wrap rounded-lg border border-slate-200 p-3 text-xs leading-relaxed text-slate-600">
                {quote.email_draft}
              </pre>
            </div>
          )}

          {quote?.pdf_path && (
            <a
              href={pdfUrl(tender.id)}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-50"
            >
              <Download size={14} /> Download Rate Confirmation PDF
            </a>
          )}

          {tender.status === "parsed_quoted" && (
            <div className="rounded-xl border border-blue-100 bg-blue-50/50 p-4">
              {!overrideMode ? (
                <div className="flex gap-2">
                  <button
                    onClick={() => onDecide(tender.id, "approve")}
                    disabled={busy}
                    className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
                  >
                    <CheckCircle2 size={16} /> Approve AI Quote
                  </button>
                  <button
                    onClick={() => setOverrideMode(true)}
                    className="flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50"
                  >
                    <PenLine size={16} /> Override Rate
                  </button>
                </div>
              ) : (
                <div className="space-y-2">
                  <label className="block text-xs font-semibold text-slate-500">Override Rate ($)</label>
                  <input
                    type="number"
                    value={overrideRate}
                    onChange={(e) => setOverrideRate(e.target.value)}
                    className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                  />
                  <input
                    placeholder="Note (optional)"
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                  />
                  <div className="flex gap-2 pt-1">
                    <button
                      onClick={() => onDecide(tender.id, "override", Number(overrideRate), note)}
                      disabled={busy || !overrideRate}
                      className="flex-1 rounded-lg bg-blue-600 px-3 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
                    >
                      Confirm Override
                    </button>
                    <button
                      onClick={() => setOverrideMode(false)}
                      className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-500 hover:bg-slate-50"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
