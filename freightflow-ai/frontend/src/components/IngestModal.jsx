import { useState } from "react";
import { X, Mail, Upload } from "lucide-react";

const SAMPLE = `Load Tender - Rate Confirmation Request

Origin: Dallas, TX
Destination: Atlanta, GA
Equipment: Dry Van
Weight: 38,000 lbs
Pickup Date: 09/10/2026
Commodity: Packaged Foods

Please confirm rate at your earliest convenience.`;

export default function IngestModal({ onClose, onSubmitEmail, onSubmitFile, loading }) {
  const [tab, setTab] = useState("email");
  const [text, setText] = useState(SAMPLE);
  const [filename, setFilename] = useState("inbound-tender.txt");
  const [file, setFile] = useState(null);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4">
      <div className="w-full max-w-xl rounded-2xl bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          <h3 className="text-base font-bold text-slate-800">Simulate Inbound Tender</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <X size={18} />
          </button>
        </div>

        <div className="flex gap-2 px-5 pt-4">
          <button
            onClick={() => setTab("email")}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold ${
              tab === "email" ? "bg-blue-600 text-white" : "bg-slate-100 text-slate-600"
            }`}
          >
            <Mail size={14} /> Email / Text
          </button>
          <button
            onClick={() => setTab("pdf")}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold ${
              tab === "pdf" ? "bg-blue-600 text-white" : "bg-slate-100 text-slate-600"
            }`}
          >
            <Upload size={14} /> PDF Document
          </button>
        </div>

        <div className="p-5">
          {tab === "email" ? (
            <>
              <label className="mb-1 block text-xs font-semibold text-slate-500">Filename (optional)</label>
              <input
                value={filename}
                onChange={(e) => setFilename(e.target.value)}
                className="mb-3 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              />
              <label className="mb-1 block text-xs font-semibold text-slate-500">Raw email / tender text</label>
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                rows={10}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 font-mono text-xs focus:border-blue-500 focus:outline-none"
              />
            </>
          ) : (
            <>
              <label className="mb-1 block text-xs font-semibold text-slate-500">
                Upload a PDF (rate confirmation, BOL, load tender)
              </label>
              <input
                type="file"
                accept="application/pdf"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                className="w-full rounded-lg border border-dashed border-slate-300 px-3 py-6 text-sm"
              />
            </>
          )}
        </div>

        <div className="flex justify-end gap-2 border-t border-slate-100 px-5 py-4">
          <button onClick={onClose} className="rounded-lg px-4 py-2 text-sm font-semibold text-slate-500 hover:bg-slate-50">
            Cancel
          </button>
          {tab === "email" ? (
            <button
              onClick={() => onSubmitEmail(text, filename)}
              disabled={loading || !text.trim()}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? "Submitting…" : "Submit Tender"}
            </button>
          ) : (
            <button
              onClick={() => file && onSubmitFile(file)}
              disabled={loading || !file}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? "Uploading…" : "Upload PDF"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
