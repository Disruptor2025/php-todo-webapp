# Prezence website (`/web`)

The public marketing site. Static [Astro](https://astro.build) + Tailwind, hosted on Cloudflare Pages.

## Run it locally

```bash
cd web
cp .env.example .env     # then edit the values
npm install
npm run dev              # http://localhost:4321
```

## Where to change things

| What | File |
|---|---|
| **All prices** (plans, one-time option, add-ons, comparison table) | `src/data/pricing.json` |
| FAQ | `src/data/faq.json` |
| Example (fictional) businesses | `src/data/examples.json` |
| Real customer results (hidden while empty) | `src/data/results.json` |
| Menu links, live-demo business | `src/data/site.json` |
| Privacy / terms / AI receptionist text | `src/pages/legal/*.astro` |
| Chat widget | `../receptionist/widget/chat-widget.js` |

**Results section:** add entries like
`{ "quote": "...", "name": "Jane", "business": "Jane's Salon", "permission": true }`.
Only entries with `"permission": true` are shown, so nothing goes live without the customer's consent.

**Founders page** (`/founders`) is hidden: it isn't in the menu or sitemap, and it's marked noindex. To launch it, add it to `nav` in `site.json` and remove it from `HIDDEN_PAGES` in `astro.config.mjs` and from `robots.txt.ts`.

## What the backend needs to provide

| Endpoint | Sent by | JSON body |
|---|---|---|
| `POST /leads/inbound` | Free preview form | `business_name, city, phone, email, google_maps_url, source` |
| `POST /leads/waitlist` | Founders waitlist | `name, email, linkedin_url, source` |
| `POST /receptionist/chat` | Chat widget | `business_id, session_id, message` → returns `{ "reply": "..." }` |

The backend must allow CORS from the website's domain. Without JavaScript the forms
fall back to a normal form-encoded POST, so `/leads/*` should accept that too.

## Tests

```bash
pip install -r requirements-test.txt
python -m pytest            # builds the site, checks the HTML, then runs browser checks
```

Browser checks use Node Playwright and fake every backend call. They're skipped if Playwright isn't installed.

## Deploy to Cloudflare Pages

1. Cloudflare dashboard → Workers & Pages → Create → Pages → connect this GitHub repo.
2. Build settings:
   - Root directory: `web`
   - Build command: `npm run build`
   - Output directory: `dist`
   - Environment variable: `NODE_VERSION=22`
3. Add the `PUBLIC_*` variables from `.env.example` under Settings → Environment variables.
4. Add your custom domain under Custom domains.

Pages hosting is free, so deploying doesn't need an approval. Buying the domain does, and that goes through `/domains` with an approval row.
