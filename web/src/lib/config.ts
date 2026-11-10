// One place to read the site's public settings (from .env / Cloudflare Pages env vars).
// Defaults keep local builds working even without a .env file.
export const API_URL = (import.meta.env.PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");
export const DEMO_PHONE = import.meta.env.PUBLIC_DEMO_PHONE || "";
export const CONTACT_EMAIL = import.meta.env.PUBLIC_CONTACT_EMAIL || "hello@prezence.example";

// Formats a price from pricing.json, e.g. 49 -> "$49"
import pricing from "../data/pricing.json";
export const money = (n: number) => `${pricing.currency}${n.toLocaleString("en-US")}`;
