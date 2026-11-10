// Generates /robots.txt with the right sitemap address for whatever PUBLIC_SITE_URL is.
import type { APIRoute } from "astro";

export const GET: APIRoute = ({ site }) =>
  new Response(
    ["User-agent: *", "Allow: /", "Disallow: /founders", "", `Sitemap: ${new URL("/sitemap-index.xml", site).href}`, ""].join("\n"),
    { headers: { "Content-Type": "text/plain" } },
  );
