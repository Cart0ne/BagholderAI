/* Watchtower card live wiring.
   Reads the most recent slow-loop regime from sentinel_scores
   (Sprint 2, post-S77) and lights the matching REGIME pip on the
   homepage Watchtower card. Best-effort: if the fetch fails the
   pips stay dim and the value remains "—". */

const SB_URL = "https://pxdhtmqfwjwjhtcoacsn.supabase.co";
const SB_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InB4ZGh0bXFmd2p3amh0Y29hY3NuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM4NDI1OTIsImV4cCI6MjA4OTQxODU5Mn0." +
  "G76lvYWrqlM0z2RoSkU1uAglfMBKN_rXvBGOQhb4kdg";

const headers = { apikey: SB_KEY, Authorization: `Bearer ${SB_KEY}` };

/* regime lives inside raw_signals JSONB — PostgREST alias pulls it
   out as a plain string column called "regime". */
type SlowRow = { regime: string | null };

const REGIME_LABEL: Record<string, string> = {
  extreme_fear: "EXTREME FEAR",
  fear: "FEAR",
  neutral: "NEUTRAL",
  greed: "GREED",
  extreme_greed: "EXTREME GREED",
};

(async () => {
  try {
    const r = await fetch(
      `${SB_URL}/rest/v1/sentinel_scores` +
        `?select=regime:raw_signals->>regime` +
        `&score_type=eq.slow` +
        `&order=created_at.desc` +
        `&limit=1`,
      { headers },
    );
    if (!r.ok) return;
    const rows = (await r.json()) as SlowRow[];
    const regime = rows?.[0]?.regime;
    if (!regime || !REGIME_LABEL[regime]) return;

    /* Light the active pip */
    const pip = document.querySelector<HTMLElement>(
      `.wt-regime-pip[data-regime="${regime}"]`,
    );
    if (pip) pip.classList.add("active");

    /* Set the value text + color it like the pip */
    const valueEl = document.getElementById("wt-regime-value");
    if (valueEl) {
      valueEl.textContent = REGIME_LABEL[regime];
      const pipColor = pip?.style.background || "rgba(255,255,255,0.85)";
      valueEl.style.color = pipColor;
      valueEl.style.opacity = "0.95";
    }
  } catch {
    /* leave dim fallback in place */
  }
})();
