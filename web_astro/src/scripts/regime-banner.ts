/* Regime watch banner (brief 88d Task 2).

   Explains to a visitor WHY the dashboard shows zero trades: when the
   slow-loop regime is fear / extreme_fear AND the bot has not traded
   today, the operation is "watching, not trading". The banner is
   server-rendered hidden; this script unhides it only when both
   conditions hold, and fills in last-trade date + days observing.

   It disappears on its own: the moment a trade lands today, or the
   regime shifts out of fear, the conditions fail and the banner stays
   hidden on the next page load (the day's trade rows take its place).

   Best-effort: any fetch error leaves the banner hidden. No sensitive
   figures are exposed — only last-trade date, current regime, and the
   number of days since the last trade. Same anon-key pattern as
   watchtower-live.ts (anon is public, RLS enforces read-only). */

const SB_URL = "https://pxdhtmqfwjwjhtcoacsn.supabase.co";
const SB_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InB4ZGh0bXFmd2p3amh0Y29hY3NuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM4NDI1OTIsImV4cCI6MjA4OTQxODU5Mn0." +
  "G76lvYWrqlM0z2RoSkU1uAglfMBKN_rXvBGOQhb4kdg";

const headers = { apikey: SB_KEY, Authorization: `Bearer ${SB_KEY}` };

const FEAR_REGIMES = new Set(["fear", "extreme_fear"]);
const REGIME_LABEL: Record<string, string> = {
  fear: "Fear regime active",
  extreme_fear: "Extreme fear regime active",
};

const sbGet = async <T>(table: string, params: string): Promise<T[]> => {
  const r = await fetch(`${SB_URL}/rest/v1/${table}?${params}`, { headers });
  if (!r.ok) return [];
  return (await r.json()) as T[];
};

(async () => {
  try {
    const banner = document.getElementById("regime-watch-banner");
    if (!banner) return;

    /* UTC midnight — same daily boundary used by dashboard-live.ts. */
    const now = new Date();
    const todayStartIso = new Date(
      Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()),
    ).toISOString();

    const [regimeRows, lastTradeRows, todayRows] = await Promise.all([
      sbGet<{ regime: string | null }>(
        "sentinel_scores",
        "select=regime:raw_signals->>regime&score_type=eq.slow" +
          "&order=created_at.desc&limit=1",
      ),
      sbGet<{ created_at: string }>(
        "trades",
        "select=created_at&config_version=eq.v3&order=created_at.desc&limit=1",
      ),
      sbGet<{ id: string }>(
        "trades",
        `select=id&config_version=eq.v3&created_at=gte.${todayStartIso}&limit=1`,
      ),
    ]);

    /* Condition 1: regime must be fear / extreme_fear. */
    const regime = regimeRows?.[0]?.regime;
    if (!regime || !FEAR_REGIMES.has(regime)) return;

    /* Condition 2: no trade today. */
    if (todayRows && todayRows.length > 0) return;

    const lastTradeIso = lastTradeRows?.[0]?.created_at;
    if (!lastTradeIso) return;

    const lastTrade = new Date(lastTradeIso);
    const lastTradeLabel = lastTrade.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    });
    const daysObserving = Math.max(
      0,
      Math.floor((now.getTime() - lastTrade.getTime()) / 86_400_000),
    );

    const setText = (id: string, value: string) => {
      const el = document.getElementById(id);
      if (el) el.textContent = value;
    };
    setText("regime-watch-lasttrade", lastTradeLabel);
    setText("regime-watch-regime", REGIME_LABEL[regime] ?? "Fear regime active");
    setText(
      "regime-watch-days",
      `${daysObserving} day${daysObserving === 1 ? "" : "s"} observing`,
    );

    banner.classList.remove("hidden");
  } catch {
    /* leave the banner hidden */
  }
})();
