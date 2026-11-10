// Prezence chat widget: a small, dependency-free chat bubble.
//
// Usage on any web page:
//   <prezence-chat api-url="https://api.example.com" business-id="prezence"
//                  business-name="Prezence"></prezence-chat>
//   <script type="module" src="chat-widget.js"></script>
//
// It talks to the receptionist backend:
//   POST {api-url}/receptionist/chat
//   body:    { "business_id": "...", "session_id": "...", "message": "..." }
//   returns: { "reply": "..." }
//
// Other parts of the page can open it for a different business (used by the
// website's live demo) by firing a browser event:
//   window.dispatchEvent(new CustomEvent("prezence-chat:open",
//     { detail: { businessId, businessName } }));
//
// It uses "shadow DOM" so its styles never clash with the host website.

const MAX_MESSAGE_LENGTH = 1000;
const REQUEST_TIMEOUT_MS = 20000;

const STYLES = `
  :host { all: initial; font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif; }
  * { box-sizing: border-box; }
  .launcher { position: fixed; right: 16px; bottom: 16px; z-index: 2147483000; width: 56px; height: 56px;
    border-radius: 50%; border: 0; background: #1d4ed8; color: #fff; cursor: pointer;
    box-shadow: 0 6px 20px rgba(15,23,42,.25); display: grid; place-items: center; }
  .launcher:focus-visible, button:focus-visible, input:focus-visible { outline: 3px solid #fbbf24; outline-offset: 2px; }
  .panel { position: fixed; right: 16px; bottom: 84px; z-index: 2147483000; width: min(370px, calc(100vw - 32px));
    height: min(520px, calc(100vh - 120px)); background: #fff; color: #0f172a; border-radius: 16px;
    box-shadow: 0 12px 40px rgba(15,23,42,.3); display: flex; flex-direction: column; overflow: hidden; }
  .panel[hidden] { display: none; }
  header { background: #1d4ed8; color: #fff; padding: 12px 14px; display: flex; align-items: center; justify-content: space-between; gap: 8px; }
  header strong { display: block; font-size: 15px; }
  header small { font-size: 12px; opacity: .9; }
  .close { background: transparent; border: 0; color: #fff; font-size: 24px; line-height: 1; cursor: pointer; padding: 4px 8px; }
  .log { flex: 1; overflow-y: auto; padding: 14px; display: flex; flex-direction: column; gap: 8px; background: #f8fafc; }
  .msg { max-width: 85%; padding: 9px 12px; border-radius: 14px; font-size: 14px; line-height: 1.4; white-space: pre-wrap; word-wrap: break-word; }
  .bot { background: #fff; border: 1px solid #e2e8f0; align-self: flex-start; }
  .user { background: #1d4ed8; color: #fff; align-self: flex-end; }
  .typing { color: #64748b; font-style: italic; }
  form { display: flex; gap: 8px; padding: 10px; border-top: 1px solid #e2e8f0; }
  input { flex: 1; min-width: 0; font: inherit; font-size: 16px; padding: 10px 12px; border: 1px solid #cbd5e1; border-radius: 10px; }
  .send { font: inherit; font-weight: 600; background: #1d4ed8; color: #fff; border: 0; border-radius: 10px; padding: 0 14px; cursor: pointer; }
  .send:disabled { opacity: .6; cursor: default; }
  .note { font-size: 11px; color: #64748b; text-align: center; padding: 0 10px 8px; }
  .note a { color: #1d4ed8; }
`;

// Chat bubble icon (inline SVG so there's nothing extra to download).
const CHAT_ICON = `<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>`;

export class PrezenceChat extends HTMLElement {
  connectedCallback() {
    if (this.shadowRoot) return; // already set up
    this.apiUrl = (this.getAttribute("api-url") || "").replace(/\/$/, "");
    this.defaultBusiness = {
      id: this.getAttribute("business-id") || "prezence",
      name: this.getAttribute("business-name") || "Prezence",
    };
    this.privacyUrl = this.getAttribute("privacy-url") || "";
    this.business = { ...this.defaultBusiness };

    const root = this.attachShadow({ mode: "open" });
    root.innerHTML = `
      <style>${STYLES}</style>
      <button class="launcher" type="button" aria-label="Open chat" aria-expanded="false">${CHAT_ICON}</button>
      <section class="panel" role="dialog" aria-label="Chat" hidden>
        <header>
          <div><strong class="title"></strong><small>AI assistant · replies instantly</small></div>
          <button class="close" type="button" aria-label="Close chat">&times;</button>
        </header>
        <div class="log" role="log" aria-live="polite"></div>
        <form>
          <input name="message" type="text" autocomplete="off" maxlength="${MAX_MESSAGE_LENGTH}"
                 placeholder="Type your message..." aria-label="Your message" required />
          <button class="send" type="submit">Send</button>
        </form>
        <p class="note"></p>
      </section>`;

    this.el = {
      launcher: root.querySelector(".launcher"),
      panel: root.querySelector(".panel"),
      title: root.querySelector(".title"),
      log: root.querySelector(".log"),
      form: root.querySelector("form"),
      input: root.querySelector("input"),
      send: root.querySelector(".send"),
      note: root.querySelector(".note"),
    };

    this.el.launcher.addEventListener("click", () => (this.isOpen() ? this.close() : this.open()));
    this.el.panel.querySelector(".close").addEventListener("click", () => this.close());
    this.el.form.addEventListener("submit", (e) => {
      e.preventDefault();
      this.sendMessage(this.el.input.value);
    });
    // Escape key closes the chat.
    this.el.panel.addEventListener("keydown", (e) => e.key === "Escape" && this.close());

    // Let the page open the chat for another business (the live demo).
    this.onOpenEvent = (e) => {
      const d = (e && e.detail) || {};
      this.open(d.businessId ? { id: d.businessId, name: d.businessName || d.businessId } : this.defaultBusiness);
    };
    window.addEventListener("prezence-chat:open", this.onOpenEvent);
  }

  disconnectedCallback() {
    window.removeEventListener("prezence-chat:open", this.onOpenEvent);
  }

  isOpen() {
    return !this.el.panel.hidden;
  }

  // Opens the panel. If a different business is given, start a fresh conversation with it.
  open(business) {
    if (business && business.id !== this.business.id) {
      this.business = { ...business };
      this.el.log.textContent = "";
    }
    if (!this.el.log.childElementCount) this.greet();
    this.el.title.textContent = this.business.name;
    this.el.panel.hidden = false;
    this.el.launcher.setAttribute("aria-expanded", "true");
    this.el.launcher.setAttribute("aria-label", "Close chat");
    this.el.input.focus();
  }

  close() {
    this.el.panel.hidden = true;
    this.el.launcher.setAttribute("aria-expanded", "false");
    this.el.launcher.setAttribute("aria-label", "Open chat");
    this.el.launcher.focus();
  }

  greet() {
    // We always say up front that this is an AI.
    this.addMessage("bot", `Hi! I'm the AI assistant for ${this.business.name}. How can I help you today?`);
    const privacy = this.privacyUrl ? ` <a href="${this.privacyUrl}" target="_blank" rel="noopener">How we use chat data</a>` : "";
    this.el.note.innerHTML = `You're chatting with an AI. Don't share card details or passwords.${privacy}`;
  }

  // A random id per browser tab + business, so the backend can keep the conversation together.
  sessionId() {
    const key = `prezence-chat-session:${this.business.id}`;
    try {
      let id = sessionStorage.getItem(key);
      if (!id) {
        id = crypto.randomUUID();
        sessionStorage.setItem(key, id);
      }
      return id;
    } catch {
      // Private browsing can block sessionStorage; fall back to an in-memory id.
      this.memoryIds = this.memoryIds || {};
      return (this.memoryIds[key] = this.memoryIds[key] || crypto.randomUUID());
    }
  }

  // Adds a chat bubble. We use textContent (never innerHTML) so messages can't inject code.
  addMessage(who, text, extraClass = "") {
    const div = document.createElement("div");
    div.className = `msg ${who} ${extraClass}`.trim();
    div.textContent = text;
    this.el.log.appendChild(div);
    this.el.log.scrollTop = this.el.log.scrollHeight;
    return div;
  }

  async sendMessage(raw) {
    const message = (raw || "").trim().slice(0, MAX_MESSAGE_LENGTH);
    if (!message) return;
    this.el.input.value = "";
    this.addMessage("user", message);
    const typing = this.addMessage("bot", "Typing...", "typing");
    this.el.send.disabled = true;

    // Give up if the server takes too long, so the user isn't left waiting forever.
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
    try {
      const res = await fetch(`${this.apiUrl}/receptionist/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ business_id: this.business.id, session_id: this.sessionId(), message }),
        signal: controller.signal,
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      typing.remove();
      this.addMessage("bot", data.reply || "Sorry, I didn't catch that. Could you say it another way?");
    } catch {
      typing.remove();
      this.addMessage("bot", "Sorry, I can't connect right now. Please try again in a minute.");
    } finally {
      clearTimeout(timer);
      this.el.send.disabled = false;
      this.el.input.focus();
    }
  }
}

if (!customElements.get("prezence-chat")) {
  customElements.define("prezence-chat", PrezenceChat);
}
