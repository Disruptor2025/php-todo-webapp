// Browser checks for the built site, run by tests/test_browser.py.
// Serves dist/ locally, opens it in headless Chromium, and FAKES every backend
// call (page.route) so no real API is ever contacted.
// Prints one JSON object: { "check name": "ok" | "error message" }.
const http = require("http");
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const DIST = path.resolve(__dirname, "../../dist");
const API = process.env.PUBLIC_API_URL;
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".svg": "image/svg+xml", ".xml": "application/xml", ".txt": "text/plain" };

// Tiny static file server: /pricing -> dist/pricing/index.html
function serve() {
  const server = http.createServer((req, res) => {
    let p = path.join(DIST, decodeURIComponent(req.url.split("?")[0]));
    if (fs.existsSync(p) && fs.statSync(p).isDirectory()) p = path.join(p, "index.html");
    if (!fs.existsSync(p)) p = path.join(DIST, "404.html");
    res.writeHead(200, { "Content-Type": TYPES[path.extname(p)] || "application/octet-stream" });
    fs.createReadStream(p).pipe(res);
  });
  return new Promise((r) => server.listen(0, () => r(server)));
}

const results = {};
async function check(name, fn) {
  try { await fn(); results[name] = "ok"; } catch (e) { results[name] = String(e.message || e).split("\n")[0]; }
}
function assert(cond, msg) { if (!cond) throw new Error(msg); }

(async () => {
  const server = await serve();
  const base = `http://localhost:${server.address().port}`;
  const browser = await chromium.launch();

  // Opens a page with the backend faked. `reply` decides what each API call returns.
  async function open(url, reply = () => ({ status: 200, body: "{}" }), viewport) {
    const ctx = await browser.newContext({ viewport: viewport || { width: 390, height: 844 } });
    const page = await ctx.newPage();
    const calls = [];
    await page.route(`${API}/**`, async (route) => {
      const req = route.request();
      calls.push({ url: req.url(), body: req.postDataJSON() });
      const r = reply(req);
      await route.fulfill({ status: r.status, contentType: "application/json", body: r.body });
    });
    await page.goto(base + url);
    return { page, calls, ctx };
  }

  await check("preview form sends lead", async () => {
    const { page, calls, ctx } = await open("/preview");
    await page.fill("#business_name", "Test Bakery");
    await page.fill("#city", "Elmsworth");
    await page.fill("#phone", "555 0100");
    await page.fill("#email", "owner@test.example");
    await page.fill("#google_maps_url", "https://maps.app.goo.gl/abc123");
    await page.click("#preview-form button[type=submit]");
    await page.waitForSelector("#preview-success:not([hidden])");
    assert(calls.length === 1, `expected 1 call, got ${calls.length}`);
    assert(calls[0].url === `${API}/leads/inbound`, calls[0].url);
    const b = calls[0].body;
    assert(b.business_name === "Test Bakery" && b.city === "Elmsworth" && b.email === "owner@test.example", JSON.stringify(b));
    assert(b.source === "website_preview_form", "missing source");
    assert(!("website" in b), "honeypot field should not be sent");
    await ctx.close();
  });

  await check("preview form rejects non-maps link", async () => {
    const { page, calls, ctx } = await open("/preview");
    await page.fill("#business_name", "X"); await page.fill("#city", "Y");
    await page.fill("#phone", "1"); await page.fill("#email", "a@b.co");
    await page.fill("#google_maps_url", "https://example.com/not-maps");
    await page.click("#preview-form button[type=submit]");
    await page.waitForFunction(() => document.querySelector("[data-status]").textContent.includes("Google Maps"));
    assert(calls.length === 0, "should not send");
    await ctx.close();
  });

  await check("preview form shows error when backend fails", async () => {
    const { page, ctx } = await open("/preview", () => ({ status: 500, body: "{}" }));
    await page.fill("#business_name", "X"); await page.fill("#city", "Y");
    await page.fill("#phone", "1"); await page.fill("#email", "a@b.co");
    await page.click("#preview-form button[type=submit]");
    await page.waitForFunction(() => document.querySelector("[data-status]").textContent.includes("went wrong"));
    assert(await page.isVisible("#preview-form"), "form should stay visible");
    await ctx.close();
  });

  await check("spam bots are ignored", async () => {
    const { page, calls, ctx } = await open("/preview");
    await page.fill("#business_name", "X"); await page.fill("#city", "Y");
    await page.fill("#phone", "1"); await page.fill("#email", "a@b.co");
    await page.evaluate(() => (document.getElementById("website").value = "spam"));
    await page.click("#preview-form button[type=submit]");
    await page.waitForSelector("#preview-success:not([hidden])");
    assert(calls.length === 0, "bot submission should not be sent");
    await ctx.close();
  });

  await check("waitlist form sends signup", async () => {
    const { page, calls, ctx } = await open("/founders");
    await page.fill("#name", "Ada"); await page.fill("#email", "ada@test.example");
    await page.click("#waitlist-form button[type=submit]");
    await page.waitForSelector("#waitlist-success:not([hidden])");
    assert(calls[0].url === `${API}/leads/waitlist` && calls[0].body.source === "founders_waitlist", JSON.stringify(calls[0]));
    await ctx.close();
  });

  await check("chat widget answers as Prezence", async () => {
    const { page, calls, ctx } = await open("/pricing", () => ({ status: 200, body: JSON.stringify({ reply: "Happy to help!" }) }));
    const w = page.locator("prezence-chat");
    await w.locator(".launcher").click();
    const greeting = await w.locator(".msg.bot").first().textContent();
    assert(greeting.includes("AI assistant for Prezence"), greeting);
    await w.locator("input").fill("How much is a website?");
    await w.locator(".send").click();
    await w.locator(".msg.bot", { hasText: "Happy to help!" }).waitFor();
    const b = calls[0].body;
    assert(calls[0].url === `${API}/receptionist/chat`, calls[0].url);
    assert(b.business_id === "prezence" && b.message === "How much is a website?" && b.session_id, JSON.stringify(b));
    await ctx.close();
  });

  await check("chat widget shows friendly error when offline", async () => {
    const { page, ctx } = await open("/", () => ({ status: 503, body: "{}" }));
    const w = page.locator("prezence-chat");
    await w.locator(".launcher").click();
    await w.locator("input").fill("hello");
    await w.locator(".send").click();
    await w.locator(".msg.bot", { hasText: "can't connect" }).waitFor();
    await ctx.close();
  });

  await check("chat messages are shown as text, not HTML", async () => {
    const { page, ctx } = await open("/", () => ({ status: 200, body: JSON.stringify({ reply: "<img src=x onerror=alert(1)>" }) }));
    const w = page.locator("prezence-chat");
    await w.locator(".launcher").click();
    await w.locator("input").fill("hi");
    await w.locator(".send").click();
    await w.locator(".msg.bot", { hasText: "<img" }).waitFor();
    assert((await w.locator(".log img").count()) === 0, "reply was rendered as HTML");
    await ctx.close();
  });

  await check("live demo opens chat for demo business", async () => {
    const { page, calls, ctx } = await open("/", () => ({ status: 200, body: JSON.stringify({ reply: "We open at 7am." }) }));
    await page.click("#demo-chat");
    const w = page.locator("prezence-chat");
    const title = await w.locator(".title").textContent();
    assert(title === "Copperline Plumbing", title);
    await w.locator("input").fill("When do you open?");
    await w.locator(".send").click();
    await w.locator(".msg.bot", { hasText: "7am" }).waitFor();
    assert(calls[0].body.business_id === "demo-copperline-plumbing", calls[0].body.business_id);
    await ctx.close();
  });

  await check("no sideways scrolling on a small phone", async () => {
    const pages = ["/", "/examples", "/examples/copperline-plumbing", "/pricing", "/preview", "/founders", "/legal/privacy", "/legal/terms", "/legal/ai-receptionist"];
    for (const url of pages) {
      const { page, ctx } = await open(url, undefined, { width: 360, height: 740 });
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      assert(overflow <= 0, `${url} overflows by ${overflow}px`);
      await ctx.close();
    }
  });

  await browser.close();
  server.close();
  console.log(JSON.stringify(results));
})();
