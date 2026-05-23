/* Sherpa card live wiring.
   Reads active bot count from bot_config (managed_by IN ('grid','tf'),
   is_active=true) and rewrites the BOTS row pip count + value text.
   Auto-adapts to whichever bots Sherpa coordinates today:
     · only grid (current state, 3 coins)
     · grid + tf (future, when TF gets per-asset rows in bot_config)
     · only tf
   Best-effort fetch: on failure the 3 server-rendered pips stay. */

const SB_URL = "https://pxdhtmqfwjwjhtcoacsn.supabase.co";
const SB_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InB4ZGh0bXFmd2p3amh0Y29hY3NuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM4NDI1OTIsImV4cCI6MjA4OTQxODU5Mn0." +
  "G76lvYWrqlM0z2RoSkU1uAglfMBKN_rXvBGOQhb4kdg";

const headers = { apikey: SB_KEY, Authorization: `Bearer ${SB_KEY}` };
const SHERPA_RED = "#ef4444";

type GridBotRow = { symbol: string };

(async () => {
  try {
    const r = await fetch(
      `${SB_URL}/rest/v1/bot_config` +
        `?select=symbol,managed_by` +
        `&managed_by=in.(grid,tf)` +
        `&is_active=eq.true`,
      { headers },
    );
    if (!r.ok) return;
    const rows = (await r.json()) as GridBotRow[];
    const count = rows?.length ?? 0;

    /* Rewrite the pip count to match the live number of coordinated bots.
       Even count=0 is a valid state (all bots disabled) — show empty bar. */
    const bar = document.getElementById("sherpa-bots-bar");
    if (bar) {
      bar.innerHTML = "";
      for (let i = 0; i < count; i++) {
        const pip = document.createElement("div");
        pip.className = "sherpa-bot-pip";
        pip.style.background = SHERPA_RED;
        bar.appendChild(pip);
      }
    }

    /* Update the value text */
    const valueEl = document.getElementById("sherpa-bots-count");
    if (valueEl) valueEl.textContent = String(count);
  } catch {
    /* leave the 3-pip fallback in place */
  }
})();

/* STOP BUY lock — read the most recent sherpa_proposals (3 rows = 1 per
   coin per tick). OR the proposed_stop_buy_active across them: if ANY
   coin has stop_buy=true, the global lamp is ON (regime=extreme_fear).
   Today's expectation: OFF (regime=fear). */
type StopRow = { proposed_stop_buy_active: boolean | null };

(async () => {
  try {
    const r = await fetch(
      `${SB_URL}/rest/v1/sherpa_proposals` +
        `?select=proposed_stop_buy_active` +
        `&order=created_at.desc` +
        `&limit=3`,
      { headers },
    );
    if (!r.ok) return;
    const rows = (await r.json()) as StopRow[];
    if (!rows?.length) return;
    const on = rows.some((row) => row.proposed_stop_buy_active === true);

    const pip = document.getElementById("sherpa-stop-pip");
    const val = document.getElementById("sherpa-stop-value");
    if (pip && on) pip.classList.add("active");
    if (val) {
      val.textContent = on ? "ON" : "OFF";
      val.style.color = on ? SHERPA_RED : "rgba(255,255,255,0.4)";
      val.style.opacity = on ? "0.95" : "1";
    }
  } catch {
    /* leave OFF fallback in place */
  }
})();
