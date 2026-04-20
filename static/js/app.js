// AubeStatus - auto refresh + interactions page API
(function () {
  const REFRESH_MS = 60 * 1000;

  function scheduleReload() {
    if (!document.querySelector(".hero")) return;
    setTimeout(function () {
      if (document.visibilityState === "visible") {
        window.location.reload();
      } else {
        document.addEventListener(
          "visibilitychange",
          function onVis() {
            if (document.visibilityState === "visible") {
              document.removeEventListener("visibilitychange", onVis);
              window.location.reload();
            }
          }
        );
      }
    }, REFRESH_MS);
  }

  function flash(btn, txt) {
    const original = btn.textContent;
    btn.textContent = txt;
    setTimeout(() => { btn.textContent = original; }, 1200);
  }

  async function copyText(text, btn) {
    try {
      await navigator.clipboard.writeText(text);
      flash(btn, "Copie !");
    } catch (e) {
      const ta = document.createElement("textarea");
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      ta.remove();
      flash(btn, "Copie !");
    }
  }

  function bindCopy() {
    document.querySelectorAll(".btn-copy[data-copy]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const sel = btn.getAttribute("data-copy");
        const el = document.querySelector(sel);
        if (!el) return;
        copyText(el.textContent.trim(), btn);
      });
    });
  }

  function prettyJson(obj) {
    return JSON.stringify(obj, null, 2);
  }

  function bindTry() {
    document.querySelectorAll(".btn-try[data-try]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const path = btn.getAttribute("data-try");
        const targetSel = btn.getAttribute("data-target");
        const type = btn.getAttribute("data-type") || "application/json";
        const out = document.querySelector(targetSel);
        if (!out) return;
        btn.setAttribute("data-loading", "1");
        out.setAttribute("data-loading", "1");
        out.classList.remove("err");
        const t0 = performance.now();
        try {
          const r = await fetch(path, { headers: { Accept: type } });
          const ms = Math.round(performance.now() - t0);
          if (type.startsWith("image/")) {
            out.textContent = `HTTP ${r.status} · ${ms} ms · ${r.headers.get("content-type") || type}\nTaille: ${r.headers.get("content-length") || "?"} octets`;
          } else {
            const data = await r.json();
            const trimmed = Object.assign({}, data);
            if (Array.isArray(trimmed.services) && trimmed.services.length > 2) {
              trimmed.services = trimmed.services.slice(0, 2).concat([{ "_note": `...${data.services.length - 2} autres services (tronque pour l'apercu)` }]);
            }
            if (Array.isArray(trimmed.history) && trimmed.history.length > 3) {
              trimmed.history = trimmed.history.slice(-3);
            }
            if (Array.isArray(trimmed.recent) && trimmed.recent.length > 3) {
              trimmed.recent = trimmed.recent.slice(0, 3);
            }
            out.textContent = `// HTTP ${r.status} · ${ms} ms\n${prettyJson(trimmed)}`;
          }
        } catch (e) {
          out.classList.add("err");
          out.textContent = "Erreur: " + e.message;
        } finally {
          btn.removeAttribute("data-loading");
          out.removeAttribute("data-loading");
        }
      });
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    bindCopy();
    bindTry();
    scheduleReload();
  });
})();
