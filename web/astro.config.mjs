// Astro config for the Prezence marketing site.
// Builds a fully static site into ./dist, which Cloudflare Pages serves.
import { defineConfig } from "astro/config";
import sitemap from "@astrojs/sitemap";
import tailwindcss from "@tailwindcss/vite";

// The public URL of the site. Used for canonical links and the sitemap.
// Set PUBLIC_SITE_URL in .env (or in Cloudflare Pages settings).
const SITE_URL = process.env.PUBLIC_SITE_URL || "https://prezence.example";

// Pages we don't want search engines to list (yet).
const HIDDEN_PAGES = ["/founders"];

export default defineConfig({
  site: SITE_URL,
  trailingSlash: "ignore",
  build: {
    // Put CSS straight into each page instead of a separate file.
    // One fewer network request = faster first paint on phones.
    inlineStylesheets: "always",
  },
  integrations: [
    sitemap({
      filter: (page) => !HIDDEN_PAGES.some((p) => new URL(page).pathname.startsWith(p)),
    }),
  ],
  vite: {
    plugins: [tailwindcss()],
    server: {
      // The chat widget lives in /receptionist (one level up), so let Vite read it.
      fs: { allow: [".."] },
    },
  },
});
