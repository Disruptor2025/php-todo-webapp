import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export const api = axios.create({ baseURL: API_BASE });

export const listTenders = () => api.get("/api/tenders").then((r) => r.data);

export const ingestEmail = (raw_text, filename) =>
  api.post("/api/ingest/email", { raw_text, filename }).then((r) => r.data);

export const ingestDocument = (file) => {
  const form = new FormData();
  form.append("file", file);
  return api
    .post("/api/ingest/document", form, {
      headers: { "Content-Type": "multipart/form-data" },
    })
    .then((r) => r.data);
};

export const processTender = (id) =>
  api.post(`/api/tenders/${id}/process`).then((r) => r.data);

export const decideTender = (id, action, override_rate, note) =>
  api
    .post(`/api/tenders/${id}/decision`, { action, override_rate, note })
    .then((r) => r.data);

export const auditTender = (id) =>
  api.post(`/api/tenders/${id}/audit`).then((r) => r.data);

export const getQuote = (id) =>
  api.get(`/api/tenders/${id}/quote`).then((r) => r.data);

export const pdfUrl = (id) => `${API_BASE}/api/tenders/${id}/pdf`;

export const listLanes = () => api.get("/api/lanes").then((r) => r.data);
