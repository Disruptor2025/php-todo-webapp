// Sends a form to the backend as JSON and shows a success or error message.
// Used by the free preview form and the founders waitlist.

type Options = {
  form: HTMLFormElement;
  url: string;                       // where to POST
  source: string;                    // tells the backend which form this came from
  validate?: (data: Record<string, string>) => string | null; // return an error message, or null if OK
};

export function wireForm({ form, url, source, validate }: Options) {
  const status = form.querySelector<HTMLElement>("[data-status]")!;
  const button = form.querySelector<HTMLButtonElement>("button[type=submit]")!;
  const success = document.getElementById(form.dataset.successId || "");

  const show = (msg: string, isError: boolean) => {
    status.textContent = msg;
    status.className = isError ? "text-sm font-medium text-red-700" : "text-sm text-ink-700";
  };

  form.addEventListener("submit", async (e) => {
    e.preventDefault(); // we send it with JavaScript instead of a full page reload

    // Collect all fields into a simple object, trimming extra spaces.
    const data: Record<string, string> = {};
    new FormData(form).forEach((v, k) => (data[k] = String(v).trim()));

    // "website" is a hidden trap field. People can't see it, but spam bots fill it in.
    // If it's filled, pretend it worked and send nothing.
    if (data.website) {
      form.hidden = true;
      success?.removeAttribute("hidden");
      return;
    }
    delete data.website;

    const problem = validate?.(data);
    if (problem) return show(problem, true);

    button.disabled = true;
    show("Sending...", false);
    try {
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...data, source }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      form.hidden = true;
      success?.removeAttribute("hidden");
      success?.focus();
    } catch {
      show("Sorry, something went wrong sending your details. Please try again, or email us instead.", true);
    } finally {
      button.disabled = false;
    }
  });
}

// Accepts the usual Google Maps link formats, e.g.
// https://maps.app.goo.gl/abc, https://goo.gl/maps/abc, https://www.google.com/maps/place/...
export function isGoogleMapsLink(value: string): boolean {
  try {
    const u = new URL(value);
    const host = u.hostname.replace(/^www\./, "");
    return (
      host === "maps.app.goo.gl" ||
      (host === "goo.gl" && u.pathname.startsWith("/maps")) ||
      host === "maps.google.com" ||
      (/^google\.[a-z.]+$/.test(host) && u.pathname.startsWith("/maps"))
    );
  } catch {
    return false;
  }
}
