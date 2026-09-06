import { useCallback, useEffect, useState } from "react";
import { Plus, RefreshCw, Truck } from "lucide-react";
import KanbanBoard from "./components/KanbanBoard";
import IngestModal from "./components/IngestModal";
import TenderDetailModal from "./components/TenderDetailModal";
import { listTenders, ingestEmail, ingestDocument, processTender, decideTender, auditTender } from "./api";

const POLL_MS = 5000;

export default function App() {
  const [tenders, setTenders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showIngest, setShowIngest] = useState(false);
  const [ingestBusy, setIngestBusy] = useState(false);
  const [selected, setSelected] = useState(null);
  const [busyId, setBusyId] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const data = await listTenders();
      setTenders(data);
      setError(null);
    } catch (e) {
      setError("Cannot reach FreightFlow AI backend. Is it running on port 8000?");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, POLL_MS);
    return () => clearInterval(id);
  }, [refresh]);

  const handleSubmitEmail = async (text, filename) => {
    setIngestBusy(true);
    try {
      await ingestEmail(text, filename);
      setShowIngest(false);
      await refresh();
    } catch (e) {
      alert(e?.response?.data?.detail || "Failed to ingest tender");
    } finally {
      setIngestBusy(false);
    }
  };

  const handleSubmitFile = async (file) => {
    setIngestBusy(true);
    try {
      await ingestDocument(file);
      setShowIngest(false);
      await refresh();
    } catch (e) {
      alert(e?.response?.data?.detail || "Failed to upload document");
    } finally {
      setIngestBusy(false);
    }
  };

  const handleProcess = async (id) => {
    setBusyId(id);
    try {
      await processTender(id);
      await refresh();
    } catch (e) {
      alert(e?.response?.data?.detail || "Failed to process tender");
    } finally {
      setBusyId(null);
    }
  };

  const handleAudit = async (id) => {
    setBusyId(id);
    try {
      await auditTender(id);
      await refresh();
    } catch (e) {
      alert(e?.response?.data?.detail || "Failed to mark audited");
    } finally {
      setBusyId(null);
    }
  };

  const handleDecide = async (id, action, overrideRate, note) => {
    setBusyId(id);
    try {
      const updated = await decideTender(id, action, overrideRate, note);
      await refresh();
      setSelected(updated);
      setTimeout(() => setSelected(null), 400);
    } catch (e) {
      alert(e?.response?.data?.detail || "Failed to record decision");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="min-h-screen bg-slate-100">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600 text-white">
              <Truck size={18} />
            </div>
            <div>
              <h1 className="text-lg font-bold text-slate-800">FreightFlow AI</h1>
              <p className="text-xs text-slate-400">Broker Operations Dashboard</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={refresh}
              className="flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-500 hover:bg-slate-50"
            >
              <RefreshCw size={14} /> Refresh
            </button>
            <button
              onClick={() => setShowIngest(true)}
              className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-2 text-sm font-semibold text-white hover:bg-blue-700"
            >
              <Plus size={16} /> Simulate Inbound Tender
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-6">
        {error && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
            {error}
          </div>
        )}
        {loading ? (
          <p className="text-sm text-slate-400">Loading tenders…</p>
        ) : (
          <KanbanBoard
            tenders={tenders}
            onOpen={setSelected}
            onProcess={handleProcess}
            onAudit={handleAudit}
            busyId={busyId}
          />
        )}
      </main>

      {showIngest && (
        <IngestModal
          onClose={() => setShowIngest(false)}
          onSubmitEmail={handleSubmitEmail}
          onSubmitFile={handleSubmitFile}
          loading={ingestBusy}
        />
      )}

      {selected && (
        <TenderDetailModal
          tender={tenders.find((t) => t.id === selected.id) || selected}
          onClose={() => setSelected(null)}
          onDecide={handleDecide}
          busy={busyId === selected.id}
        />
      )}
    </div>
  );
}
