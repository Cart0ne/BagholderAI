/* Roadmap data — single source of truth for /roadmap.
   Updated each session by hand (port from /web/roadmap.html JSON).
   Status legend:
     done    — completed
     active  — currently being worked on
     planned — scheduled but not yet started
     todo    — single-task version of "planned" (used inside phase tasks)
     killed  — explicitly abandoned
   For Phase 8 (Backlog) and Phase 9 (Validation), tasks may include
   `{ section: "..." }` rows that act as subsection headers grouping
   the tasks below them. */

export type TaskStatus = "done" | "active" | "todo" | "killed";
export type PhaseStatus = "done" | "active" | "planned";
export type Who = "AI" | "MAX" | "BOTH";

export interface Task {
  text: string;
  status: TaskStatus;
  who: Who;
  comment?: string;
}

export interface SectionMarker {
  section: string;
}

export interface Phase {
  id: number;
  title: string;
  timeframe: string;
  status: PhaseStatus;
  description: string;
  tasks: Array<Task | SectionMarker>;
}

export interface RoadmapData {
  version: string;
  lastUpdated: string;
  phases: Phase[];
}

export const ROADMAP: RoadmapData = {
  version: "Versione 1.38 — Maggio 2026",
  lastUpdated: "2026-05-10",
  phases: [
    {
      id: 0,
      title: "Foundations",
      timeframe: "Week 1",
      status: "done",
      description: "Without this, nothing works.",
      tasks: [
        { text: "Choose name → BagHolderAI", status: "done", who: "MAX", comment: "3 hours. Discovered a shitcoin stole our name first." },
        { text: "Register domain bagholderai.lol", status: "done", who: "MAX", comment: "$1.54 on Porkbun. GoDaddy wanted $53 for renewal." },
        { text: "Binance account + KYC", status: "done", who: "MAX" },
        { text: "API keys (read + trade, NO withdraw)", status: "done", who: "MAX", comment: "Defense in depth. Even if I go rogue, your money stays." },
        { text: "Telegram bot", status: "done", who: "MAX" },
        { text: "Python environment + dependencies", status: "done", who: "AI" },
        { text: "GitHub repository", status: "done", who: "BOTH" },
        { text: "Supabase database (7 tables)", status: "done", who: "AI" },
        { text: "Agent personality & tone defined", status: "done", who: "BOTH", comment: "90 minutes. Max said 'molto quick'." },
        { text: "Dedicated email (proton.me)", status: "done", who: "MAX" },
      ],
    },
    {
      id: 1,
      title: "Grid Bot + Paper Trading",
      timeframe: "Weeks 2-3",
      status: "done",
      description: "The heart of the system. Closed Session 20, April 5 2026.",
      tasks: [
        { text: "Grid Bot engine (paper trading)", status: "done", who: "AI", comment: "5/5 tests passed. Fought Python versions for an hour." },
        { text: "Logging trades to Supabase", status: "done", who: "AI", comment: "Session 07. The filo was already there." },
        { text: "Telegram notifications (trade alerts + daily report)", status: "done", who: "AI", comment: "Session 07. First message: 🚀 BagHolderAI started." },
        { text: "Admin dashboard (private, for Max)", status: "done", who: "AI", comment: "Session 17. Password-gated, mobile-responsive." },
        { text: "Public dashboard v1", status: "done", who: "AI", comment: "Session 14. Dashboard is now the homepage." },
        { text: "Landing page with diary updates", status: "done", who: "BOTH" },
        { text: "First diary post on dashboard", status: "done", who: "BOTH", comment: "Session 14. CEO's Log with Haiku commentary." },
        { text: "Test 2-3 different tokens (BTC, SOL, BONK)", status: "done", who: "BOTH", comment: "Session 09. Three grids running in parallel." },
        { text: "Multi-token support (--symbol parameter)", status: "done", who: "AI", comment: "Session 09. Dynamic config per asset." },
        { text: "Public dashboard: CEO's Log + Numbers + Under the Hood", status: "done", who: "AI", comment: "Session 14. Static HTML + Supabase REST." },
        { text: "Admin dashboard with parameter editing", status: "done", who: "AI", comment: "Session 17. SHA-256 auth, live config updates." },
        { text: "Percentage grid: buy_pct / sell_pct in bot_config", status: "done", who: "AI", comment: "Session 18. BTC 1.8/1.0, SOL 1.5/1.0, BONK 1.0/1.0." },
        { text: "Bot reads config from Supabase (refresh every 5 min)", status: "done", who: "AI", comment: "Session 18. No more code changes to tweak parameters." },
        { text: "Admin dashboard: buy_pct / sell_pct / grid_mode fields", status: "done", who: "AI", comment: "Session 19. Confirmed working." },
        { text: "Activate grid_mode=percentage and beta test", status: "done", who: "BOTH", comment: "Session 20. Activated with a side of phantom money." },
      ],
    },
    {
      id: 2,
      title: "Trend Follower",
      timeframe: "Weeks 3-4",
      status: "active",
      description: "Three-layer architecture: Trend Follower (brain) → Runner (manager) → Grid Bot (executor). Designed in Session 31, spec v1 closed.",
      tasks: [
        { text: "EMA, RSI, Volume indicators", status: "done", who: "AI", comment: "Session 31. EMA 20/50 + RSI 14 + ATR 14 on 4h candles. Spec v1." },
        { text: "Trend Follower ↔ Grid Bot interaction", status: "done", who: "AI", comment: "Session 31. TF writes to bot_config, grid reads. Bullish/bearish/sideways grid profiles defined." },
        { text: "Human cooldown override on bot_config (architecture)", status: "done", who: "BOTH", comment: "Session 31. 48h per-coin veto. managed_by + manual_override_until columns live." },
        { text: "Runner/Orchestrator process manager", status: "done", who: "AI", comment: "Session 35b. One process manages 3 grid bots + TF, graceful shutdown, crash-restart with retry cap." },
        { text: "Supabase schema: trend_config, coin_tiers, trend_decisions_log", status: "done", who: "AI", comment: "Session 31. Phase A complete." },
        { text: "Coin tier system (T1/T2/T3 allocation limits)", status: "done", who: "AI", comment: "Session 31. BTC/ETH 40%, top 20 20%, rest 10%. Session 36c will loosen caps in favor of tf_budget split." },
        { text: "Scanner: top 50 coins by volume + signal classifier", status: "done", who: "AI", comment: "Session 31 + 35 (tiered scanning A/B/C)." },
        { text: "Allocator: select top N, respect tiers, write bot_config", status: "done", who: "AI", comment: "Session 36a. Now uses tf_max_coins (default 2) instead of fixed 5. MANUAL_WHITELIST protects BTC/SOL/BONK." },
        { text: "Dashboard: Trend Follower status", status: "done", who: "AI", comment: "Session 36b. /tf control room — budget, deployed, decisions log, TF-only view." },
        { text: "Parameter calibration from data", status: "done", who: "BOTH", comment: "Brief 36c: ATR-based buy_pct/sell_pct + full tf_budget deployment. Extended in 36e (rotation + ATR clamps) and 36g (compound via floating cash)." },
        { text: "Auto-clean policy for trend_decisions_log (90 days)", status: "todo", who: "AI" },
      ],
    },
    {
      id: 3,
      title: "AI Sentinel + Sherpa",
      timeframe: "Weeks 4-5",
      status: "active",
      description: "Two experimental brains observing the market in DRY_RUN since S70 (2026-05-10). Sentinel scores risk + opportunity from price + funding signals. Sherpa proposes parameter changes to Grid based on Sentinel's reads. Neither writes to live config yet — pure data collection until Board approves SHERPA_MODE=live.",
      tasks: [
        { text: "Sentinel Sprint 1: fast loop (BTC price + funding)", status: "done", who: "AI", comment: "Session 56 (2026-05-06). score_engine.py + price_monitor.py running every 60s, writes sentinel_scores. Risk + Opportunity + speed_of_fall heuristics." },
        { text: "Sherpa Sprint 1: rule-based proposals on Grid", status: "done", who: "AI", comment: "Session 56 (2026-05-06). Loop every 120s reads Sentinel scores + writes sherpa_proposals. SHERPA_MODE=dry_run never touches bot_config." },
        { text: "Sentinel ricalibrazione (brief 70b)", status: "done", who: "AI", comment: "Brief 70b shipped 2026-05-10 (S70). Ladder granulare drop/pump/funding (-0.5/-1/-2 with 5-20 increments); sof_accelerating floor -0.5%; Telegram silent flags (SENTINEL_TELEGRAM_ENABLED / SHERPA_TELEGRAM_ENABLED default false). Diagnosis on 2,827 historical records: BTC range ±1% (never -3%), funding ±0.00007. Sentinel had been writing risk=20 sempre, opp=20 morta." },
        { text: "DRY_RUN restart with Sentinel + Sherpa active (S70)", status: "done", who: "AI", comment: "Orchestrator restart 2026-05-10 09:51 UTC. PID 2626 + 3 grid_runner + sentinel + sherpa. TF stays off. First sherpa proposal at 09:51:50 UTC." },
        { text: "News feed integration (CryptoPanic, RSS)", status: "todo", who: "AI", comment: "Sentinel Sprint 3, brief in planning." },
        { text: "Sherpa Sprint 2: slow loop (F&G + CMC dominance + regime detection)", status: "todo", who: "BOTH", comment: "Pre-requisito: replay counterfactual Sprint 1." },
        { text: "Override logic on other brains (SHERPA_MODE=live)", status: "todo", who: "AI", comment: "1-2 settimane DRY_RUN + Board approval." },
        { text: "Auto-generated daily diary", status: "todo", who: "AI" },
        { text: "Dashboard: risk score + diary page (public)", status: "todo", who: "AI", comment: "Admin dashboard /admin Sentinel+Sherpa live da S63. Pubblicizzazione decisa post-replay." },
      ],
    },
    {
      id: 4,
      title: "Dashboard + Monetization",
      timeframe: "Weeks 5-6",
      status: "active",
      description: "The dashboard is the product. The guides are the revenue.",
      tasks: [
        { text: "Professional UI design", status: "done", who: "BOTH", comment: "Sessions 1-8 web_astro (Apr 30 → May 4, 2026). Full site rebuilt in Astro with editorial-tech design system (deep blue + sky), Inter + JetBrains Mono, mobile-first, single STYLEGUIDE.md (696 lines) as source of truth. 9/9 pages live on bagholderai.lol." },
        { text: "Dashboard rewrite: Astro + React islands + Supabase polling", status: "done", who: "AI", comment: "Initially scoped as full React rewrite. Re-architected as Astro static + React islands (`@astrojs/react` integration) — interactivity only where needed (e.g. /howwework org chart with `client:visible`), 95% of pages stay static for fast loads. Realtime websockets dropped: REST + polling proved sufficient for current scale. Future: server-side FIFO refactor when trade volume crosses ~3000/bot." },
        { text: "Deploy on Vercel + custom domain", status: "done", who: "BOTH" },
        { text: "English localization", status: "done", who: "AI", comment: "Site fully in English from the start." },
        { text: "China accessibility (no blocked services)", status: "done", who: "BOTH", comment: "Session 08. Max's friend in China confirmed." },
        { text: "Crypto-native ads (A-Ads live, upgrade later)", status: "done", who: "MAX", comment: "Register first, customers second." },
        { text: "Donation button", status: "done", who: "AI", comment: "Session 27. Buy Me a Coffee active at buymeacoffee.com/bagholderai." },
        { text: "Telegram bot (reports only, never signals)", status: "done", who: "BOTH", comment: "MiFID II compliance. Transparency, not advice." },
        { text: "Volume 1 (Fase 0+1): outline, packaging, cover art", status: "done", who: "BOTH", comment: "Session 26. Content-complete. Cover art designed with CEO, PDF assembled." },
        { text: "Setup payment platform", status: "done", who: "MAX", comment: "Session 34. LemonSqueezy rejected (crypto risk flag). Migrated to Payhip — live in 20 minutes." },
        { text: "Landing page /library on bagholderai.lol", status: "done", who: "AI", comment: "Session 30. Cover, description, preview PDF download. Session 34: Payhip checkout live, button active. Session 7 (web_astro): renamed /guide → /library." },
        { text: "Italian preface (Max writes, AI translates)", status: "done", who: "BOTH", comment: "Session 25. Max wrote IT, CEO translated EN." },
        { text: "Blueprint translation (IT→EN)", status: "done", who: "AI", comment: "Session 25. Faithful translation, historical document." },
        { text: "CEO Introduction for Volume 1", status: "done", who: "AI", comment: "Session 25." },
        { text: "Dedication page", status: "done", who: "BOTH", comment: "Session 25. Four hands." },
        { text: "Glossary (Appendix D)", status: "done", who: "AI", comment: "Session 25. 37 terms, organized by topic." },
        { text: "Screenshot placement map", status: "done", who: "BOTH", comment: "Session 25. 9 screenshots mapped to sessions." },
        { text: "Book title decided", status: "done", who: "BOTH", comment: "Session 26. Picked together with the CEO." },
        { text: "Cover art designed", status: "done", who: "BOTH", comment: "Session 26. Designed together with the CEO." },
        { text: "Volume 1 content-complete", status: "done", who: "BOTH", comment: "Session 26. All chapters, appendices, glossary, intros — locked." },
        { text: "Final assembly into PDF", status: "done", who: "BOTH", comment: "Session 26. Almost there — last typographic passes pending." },
        { text: "Editorial plan X: first 5-10 posts from diary", status: "active", who: "BOTH", comment: "9 posts published, schema defined. Ongoing." },
        { text: "Publish Volume 1", status: "done", who: "BOTH", comment: "Session 34. Live on Payhip at €4.99." },
        { text: "Publish Volume 2", status: "done", who: "BOTH", comment: "From Grid to Brain. 29 sessions. Live on Payhip at €4.99." },
      ],
    },
    {
      id: 5,
      title: "Extended Paper Trading",
      timeframe: "Weeks 6-10",
      status: "planned",
      description: "Minimum 4 weeks. No live trading without this phase.",
      tasks: [
        { text: "Performance analysis (min 4 weeks)", status: "todo", who: "BOTH" },
        { text: "Auto-generated rules (first generation)", status: "todo", who: "AI" },
        { text: "Optimize Grid + Trend Follower parameters", status: "todo", who: "BOTH" },
        { text: "Fix bugs and edge cases", status: "todo", who: "AI" },
        { text: "Strategy B: active at launch? Data-driven decision", status: "todo", who: "MAX" },
        { text: "Weekly learning reports", status: "todo", who: "AI" },
        { text: "Stress test with allocation >$500 in paper mode", status: "todo", who: "BOTH" },
      ],
    },
    {
      id: 6,
      title: "Go Live",
      timeframe: "After Week 10",
      status: "planned",
      description: "Only if paper trading results are satisfactory. No exceptions.",
      tasks: [
        { text: "GO/NO-GO decision based on data", status: "todo", who: "MAX" },
        { text: "Deposit initial capital (€100-200, NOT €500)", status: "todo", who: "MAX" },
        { text: "Switch from paper to live (config flag)", status: "todo", who: "AI" },
        { text: "Intensive monitoring (first week)", status: "todo", who: "MAX" },
        { text: "VPS migration for stability", status: "todo", who: "BOTH" },
        { text: "Gradual scale: €200 → €350 → €500", status: "todo", who: "MAX" },
      ],
    },
    {
      id: 7,
      title: "Marketing & Growth",
      timeframe: "Parallel from Phase 1",
      status: "active",
      description: "We don't promote. We document. The audience finds us.",
      tasks: [
        { text: "First posts on X (@BagHolderAI)", status: "done", who: "BOTH", comment: "Session 08. Thread pinned. One post per day." },
        { text: "Contact AI community influencers", status: "todo", who: "BOTH" },
        { text: "Reddit (r/algotrading, r/cryptocurrency)", status: "todo", who: "BOTH" },
        { text: "Dashboard demo thread on X", status: "todo", who: "BOTH" },
        { text: "Guide: 'How I built an AI trading agent'", status: "todo", who: "BOTH" },
        { text: "Development diary as sellable content", status: "active", who: "BOTH", comment: "Volume 1 (Fase 0+1) live on Payhip since Session 34 at €4.99. Volume 2 (From Grid to Brain) live on Payhip at €4.99. Ongoing output → ongoing sellable content." },
        { text: "MiFID II verification for future copy-trading", status: "todo", who: "MAX" },
        { text: "Free guide for influencer outreach", status: "todo", who: "BOTH" },
      ],
    },
    {
      id: 8,
      title: "Backlog — Polish & Improvements",
      timeframe: "Ongoing",
      status: "active",
      description: "Everything we built beyond the blueprint — fixes, improvements, and features discovered in the field. Published alongside v1.1 to show what building really looks like.",
      tasks: [
        { section: "Phase 1 — Grid Bot & Paper Trading (CLOSED)" },
        { text: "Fix accounting: avg_buy_price, grid reset, daily P&L", status: "done", who: "AI", comment: "Session 09. 5 bugs found, 5 bugs fixed." },
        { text: "Per-asset Telegram reports (symbol + config filter)", status: "done", who: "AI", comment: "Session 10. Each bot reports its own trades." },
        { text: "Wide grids + buy cooldown + min profit target", status: "done", who: "AI", comment: "Session 10. Philosophy: holder, not scalper." },
        { text: "Available capital in grid reset logic", status: "done", who: "AI", comment: "Session 10. Prevents overspending." },
        { text: "Data versioning (config_version v1/v2/v3)", status: "done", who: "AI", comment: "Session 10+13. v3 reset: clean slate, no inherited positions." },
        { text: "Supabase connector for direct CEO data access", status: "done", who: "MAX", comment: "Session 11. The CEO finally has eyes." },
        { text: "Consolidated portfolio report (total value vs initial capital)", status: "done", who: "AI", comment: "Session 12. Fixed P&L: was +$270 (wrong), now -$10.63 (correct)." },
        { text: "Daily snapshot saved to daily_pnl table", status: "done", who: "AI", comment: "Session 12. Dashboard-ready with JSONB positions." },
        { text: "Private daily report redesign (per-asset cards)", status: "done", who: "AI", comment: "Session 12. Full portfolio + technical cards." },
        { text: "Public daily report for Telegram channel", status: "done", who: "AI", comment: "Session 12. Zero jargon, readable by anyone." },
        { text: "Rename 'Cost' to 'Revenue' on sell notifications", status: "done", who: "AI" },
        { text: "daily_commentary table for AI CEO voice", status: "done", who: "AI", comment: "Session 13. Haiku writes the CEO's daily log." },
        { text: "config_changes_log table for parameter tracking", status: "done", who: "AI", comment: "Session 13. Feeds Max's changes into the AI narrative." },
        { text: "Fix restore_state_from_db: config_version filter", status: "done", who: "AI", comment: "Session 13. v1/v2 cross-contamination fixed." },
        { text: "Fix public Telegram report (.env config)", status: "done", who: "MAX", comment: "Session 13. Silent failure — env vars missing on Mac Mini." },
        { text: "Dashboard becomes homepage, /diary for construction log", status: "done", who: "BOTH", comment: "Session 14. Visitors see data first." },
        { text: "Nav bar on all site pages", status: "done", who: "AI", comment: "Session 14." },
        { text: "Haiku commentary call at 21:00", status: "done", who: "AI", comment: "Session 14. First output: 'a shopping spree.'" },
        { text: "RLS policies for public dashboard reads", status: "done", who: "AI", comment: "Session 14+17. anon SELECT on all public tables." },
        { text: "Blueprint page on site (/blueprint)", status: "done", who: "BOTH", comment: "Session 15." },
        { text: "BONK micro-price formatting ($0.00 fix)", status: "done", who: "AI", comment: "Session 15. fmtPrice() for micro-prices like BONK." },
        { text: "Anti-duplicate trade trigger (5s window)", status: "done", who: "AI", comment: "Session 15. DB-level race condition prevention." },
        { text: "Anti-short-sell trigger (DB-level)", status: "done", who: "AI", comment: "Session 15. Blocks sells when holdings insufficient." },
        { text: "Holdings/cash verification on every trade notification", status: "done", who: "AI", comment: "Session 15." },
        { text: "Environment alignment (MacBook Air + Mac Mini)", status: "done", who: "MAX", comment: "Session 15. Same env vars, config, Python version." },
        { text: "REPORT_HOUR 21→20 (more time to react)", status: "done", who: "MAX", comment: "Session 15." },
        { text: "Received breakdown in terminal (cost basis + profit)", status: "done", who: "AI", comment: "Session 15." },
        { text: "Fix symbol filter bug in daily report", status: "done", who: "AI", comment: "Session 16." },
        { text: "Diary entries migration from JSON to Supabase", status: "done", who: "AI", comment: "Session 16. diary.html reads from Supabase REST API." },
        { text: "No-funds buy guard (block trade + Telegram alert)", status: "done", who: "AI", comment: "Session 16." },
        { text: "No-holdings sell guard (block trade + Telegram alert)", status: "done", who: "AI", comment: "Session 16." },
        { text: "Haiku Day 3 stale data fix", status: "done", who: "AI", comment: "Session 16. test_commentary.py was using cached data." },
        { text: "Telegram footer v2→v3", status: "done", who: "AI", comment: "Session 16." },
        { text: "Grid parameter evaluation post cash-zero", status: "done", who: "BOTH", comment: "Session 17. Data-driven recalibration." },
        { text: "BONK $0.00 fix in terminal logs", status: "done", who: "AI", comment: "Session 18. Dynamic decimal formatting." },
        { text: "Capital redistribution: BTC $200 / SOL $150 / BONK $150", status: "done", who: "BOTH", comment: "Session 18. Up from $100/$50/$30 with $320 idle." },
        { text: "Telegram silent failure logging (warnings)", status: "done", who: "AI", comment: "Session 19. All 8 sync methods now wrapped." },
        { text: "Fallback colors for new asset symbols on dashboard", status: "done", who: "AI", comment: "Session 19. Already implemented, confirmed." },
        { text: "\"Last shot\" buy (use remaining cash below capital_per_trade)", status: "done", who: "AI", comment: "Session 19. If cash > $5 but < standard buy, spend it all." },
        { text: "Binance API retry with exponential backoff", status: "done", who: "AI", comment: "Session 19. 3 retries (2s/4s/8s) before propagating error." },
        { text: "Proactive Telegram alerts (capital exhausted + loop errors)", status: "done", who: "AI", comment: "Session 19. Max's idea. Bot now tells you when it's sick." },
        { text: "Fix sell_pct in percentage mode (lot price vs avg)", status: "done", who: "AI", comment: "Session 20. Was selling in loss thinking it was profit." },
        { text: "Config change notification filtered by symbol (9→3)", status: "done", who: "AI", comment: "Session 20. Each bot notifies only its own coin." },
        { text: "Config change shows old → new parameter values", status: "done", who: "AI", comment: "Session 20." },
        { text: "Anti-duplicate daily report guard", status: "done", who: "AI", comment: "Session 20. Flag set at entry, not exit." },
        { text: "Trade P&L per single sell in Telegram notifications", status: "done", who: "AI", comment: "Session 20. Individual + portfolio P&L." },
        { text: "KeyboardInterrupt during error sleep sends stop message", status: "done", who: "AI", comment: "Session 20." },
        { text: "Skip first buy on mode switch if holdings exist", status: "done", who: "AI", comment: "Session 20. No phantom first buy." },
        { text: "Buy skipped spam throttle (once per level/cash)", status: "done", who: "AI", comment: "Session 20." },
        { text: "Profit skimming (reserve_ledger + skim_pct)", status: "done", who: "AI", comment: "Session 20. Micro-profit reserve. Default 0, ready to activate." },
        { text: "Cash reconstruction from DB on restore", status: "done", who: "AI", comment: "Session 20. Phantom money bug killed. Bot replays trade history." },
        { text: "Cash audit script (scripts/cash_audit.py)", status: "done", who: "AI", comment: "Session 20. Read-only verification of all coin positions." },
        { text: "Admin UI: capital_per_trade and skim_pct as common params", status: "done", who: "AI", comment: "Session 20. Visible in both grid modes." },
        { text: "Skim reserve display in P&L Breakdown on homepage", status: "done", who: "AI", comment: "Session 21. Reserve accantonato visible alongside realized + unrealized." },
        { text: "Fix TradeLogger crash (trade_pnl_pct parameter)", status: "done", who: "AI", comment: "Session 21." },
        { text: "Remove hardcoded 2% min profit target", status: "done", who: "AI", comment: "Session 21. Min profit is now a configurable parameter, default 0." },
        { text: "Fix P&L % in Telegram messages (was showing 0.00%)", status: "done", who: "AI", comment: "Session 21." },
        { text: "Per-coin reserve label in Telegram messages", status: "done", who: "AI", comment: "Session 21. Each notification shows its own skim reserve total." },
        { text: "Race condition daily report: INSERT ON CONFLICT DO NOTHING", status: "done", who: "AI", comment: "Session 21. Only first bot to write wins — others skip silently." },
        { text: "SELL SKIPPED spam dedup (same pattern as BUY SKIPPED)", status: "done", who: "AI", comment: "Session 21. Dedup by level_price + holdings, same logic as buy." },
        { text: "Admin dashboard: live portfolio value from Binance prices", status: "done", who: "AI", comment: "Session 22. Real-time prices replace stale DB avg." },
        { text: "Admin dashboard: full trades history + CLOSED position display", status: "done", who: "AI", comment: "Session 22. CLOSED badge, all historical trades visible." },
        { text: "Admin dashboard: auto-refresh every 30s", status: "done", who: "AI", comment: "Session 22." },
        { text: "Admin Portfolio Overview: 2-row 6-card layout (value/P&L/skim + cash/deployed/unrealized)", status: "done", who: "AI", comment: "Session 22. One glance = full picture." },
        { text: "Fix FIFO sell blocking: all triggered lots sell independently", status: "done", who: "AI", comment: "Session 22b. Bot was stuck: older lot not triggered blocked all younger profitable lots." },
        { text: "Grid mode hot-reload without restart", status: "done", who: "AI", comment: "Session 22b. Changing grid_mode in Supabase now re-initializes state mid-run." },
        { text: "Dashboard: cashLeft for closed positions = alloc + realized P&L − skim", status: "done", who: "AI", comment: "Session 22b. Portfolio Value was underestimating closed positions." },
        { text: "Dashboard: Unrealized P&L rebuilt from FIFO open lots (not historical avg)", status: "done", who: "AI", comment: "Session 22b. Avg buy price now uses only open lots, not all-time buys." },
        { text: "Idle re-entry after N idle hours (holdings=0, no drop)", status: "done", who: "AI", comment: "Session 22c. If price doesn't drop for 24h, bot resets reference and re-enters at market." },
        { text: "Self-healing: re-init from DB when holdings>0 but FIFO queue empty", status: "done", who: "AI", comment: "Session 22b. State divergence self-heals without restart." },
        { text: "Dashboard: Promise.allSettled + auto-refresh 10s", status: "done", who: "AI", comment: "Session 22b. Resilient load — one slow API never blocks the rest." },
        { text: "Fix idle re-entry timezone (.astimezone UTC)", status: "done", who: "AI", comment: "Session 22b. Restored _last_trade_time was off by TZ offset; now always UTC-naive." },
        { text: "Idle re-entry diagnostic log (hourly countdown visible)", status: "done", who: "AI", comment: "Session 22b. Logs elapsed/threshold at each hour boundary — silent no more." },
        { text: "Fix 'Reserve Accumulata' → 'Accumulated Reserve' in daily report", status: "done", who: "AI", comment: "Session 22b. Italian label removed from English report." },
        { text: "Haiku commentary: 24h rolling window for config_changes", status: "done", who: "AI", comment: "Session 26. Was 'today midnight UTC' (= 02:00 italian) and missed late-day changes." },
        { text: "Fix admin payload bug: config_changes_log was silently failing for 5 days", status: "done", who: "AI", comment: "Session 26. Payload used 'field:' but column is 'parameter'. Try/catch hid the error since S18b. Backfilled 4 missed entries manually." },
        { text: "Admin: sanitize comma → dot on save (iOS Italian decimal locale)", status: "done", who: "AI", comment: "Session 26. type=text inputmode=decimal + comma normalization + isNaN guard." },
        { text: "Index dashboard: layout restructure (today log → numbers → archive)", status: "done", who: "AI", comment: "Session 26. CEO's Log Archive moved below The Numbers." },
        { text: "Index dashboard: live numbers from trades + Binance prices", status: "done", who: "AI", comment: "Session 26. Was reading from daily_pnl snapshot (20:00 only) — SOL showed $0.00 mid-day. Now mirrors admin strategy with FIFO + live prices." },
        { text: "Index dashboard: 5-min auto-refresh + 'Updated at HH:MM' timestamp", status: "done", who: "AI", comment: "Session 26. Numbers section refreshes without page reload." },
        { text: "Admin coin cards: 'Invested' → 'Open cost basis' (FIFO)", status: "done", who: "AI", comment: "Session 26. netSpent collapsed after profitable round-trips, hiding real capital at risk. Now shows true open lots cost basis." },
        { text: "Admin coin cards: 'Grid capacity' → 'Open lots N/max filled'", status: "done", who: "AI", comment: "Session 26. Old formula (buy_count - sell_count) went negative when sells outnumbered buys." },
        { text: "Admin overview: 'Deployed' from openCost instead of netSpent", status: "done", who: "AI", comment: "Session 26. Cash + Deployed now equals Portfolio Value (mod unrealized)." },
        { text: "Align all user-facing time references to 20:00", status: "done", who: "AI", comment: "Session 26. commentary.py, test_report.py, index.html all said 21:00 or midnight from earlier sessions." },

        { section: "Phase 2 — Trend Follower" },
        { text: "TF live mode: apply_allocations writes bot_config (tf_budget, tf_max_coins, whitelist)", status: "done", who: "AI", comment: "Session 36a. MANUAL_WHITELIST shields BTC/SOL/BONK. INSERT/UPDATE path for ALLOCATE, pending_liquidation for DEALLOCATE." },
        { text: "TF hotfix: grid_levels/grid_lower/grid_upper placeholders on INSERT (NOT NULL)", status: "done", who: "AI", comment: "Session 36a same day. 10/0/0 dummies, unused in percentage mode." },
        { text: "TF hotfix: profit_target_pct=0 on INSERT (unblocks sells)", status: "done", who: "AI", comment: "2026-04-16. DB default 1.0 was read as +100% by grid_bot, freezing every TF sell — pre-existing unit mismatch emerged with TF." },
        { text: "TF hotfix: skim_pct=30 on INSERT (match manual bots)", status: "done", who: "AI", comment: "2026-04-16. TF profits were fully reinvested, reserve stayed $0." },
        { text: "Home + Admin: filter TF coins/trades to preserve $500 manual baseline", status: "done", who: "AI", comment: "2026-04-16. managed_by=neq.trend_follower on queries. /tf owns the TF view." },
        { text: "TF full budget deployment: equal-split + dynamic capital_per_trade", status: "done", who: "AI", comment: "Brief 36c. tf_budget split across tf_max_coins, capital_per_trade = alloc / tf_lots_per_coin. Deployed 2026-04-16." },
        { text: "TF ATR-based buy_pct/sell_pct (adaptive grid widths)", status: "done", who: "AI", comment: "Brief 36c + 36e_v2. ATR-adaptive widths clamped to CEO philosophy: buy 1–2%, sell 1–6%." },
        { text: "profit_target_pct unit mismatch: UI label vs DB value vs grid_bot decimal", status: "done", who: "AI", comment: "Brief 36d. TF INSERTs profit_target_pct=0 (bypass); unit kept as percent, grid_bot divides by 100 consistently." },
        { text: "TF coin rotation: SWAP on stronger BULLISH + DEALLOCATE on BEARISH", status: "done", who: "AI", comment: "Brief 36e + 36e_v2. Signal strength delta gate, cooldown, profit gate on SWAP, on-demand rescan for active coins missing from top-N." },
        { text: "TF compounding via floating cash lookup", status: "done", who: "AI", comment: "Brief 36g. tf_total_capital = tf_budget + retained profits from deallocated TF bots." },
        { text: "TF stop-loss + bearish exit override Strategy A", status: "done", who: "AI", comment: "Brief 39a. Unrealized loss > tf_stop_loss_pct (10% of alloc) triggers full liquidation; pending_liquidation=true forces sell at any price." },
        { text: "MBOX phantom skim audit (realized_net vs gross cash flow mismatch)", status: "done", who: "AI", comment: "Brief 36j. Documented $2.63 phantom profit on MBOX. Decision: leave as-is ($0.19 skim drift, self-heals on reallocation)." },
        { text: "TF riding mode (trailing stop) for strong bullish pumps", status: "done", who: "AI", comment: "Brief 36f → shipped as 51b (Session 51, 2026-04-29). Per-bot peak tracking after allocation; once gain ≥ activation_pct, locks in a trail at trailing_pct below the peak." },
        { text: "TF idle re-entry fast for active bots", status: "done", who: "AI", comment: "Brief 36i → shipped across Sessions 33 + 45. TF bots default to 1h, manual to 24h. Unsticks bots with dust residuals." },
        { text: "Haiku sees TF (commentary on rotation + stop-loss events)", status: "done", who: "AI", comment: "Brief 36h → shipped Session 48 (2026-04-26). commentary.py now exports get_tf_state() and Haiku system prompt instructs aggregate-portfolio commentary." },
        { text: "TF hot-reload of safety params in live grid_runners", status: "done", who: "AI", comment: "Brief 39j (2026-04-20). tf_stop_loss_pct + tf_take_profit_pct polled from trend_config every 300s without restart." },
        { text: "TF multi-lot entry + greed decay take-profit", status: "done", who: "AI", comment: "Brief 42a (2026-04-20). 1 aggregated market buy on first cycle after ALLOCATE; greed_decay_tiers JSONB governs per-lot sell threshold. CEO-editable tiers in /tf with audit log." },
        { text: "TF 42a fixes: single-buy aggregated + greed decay authoritative from t=0", status: "done", who: "AI", comment: "2026-04-20 evening. Initial version looped N times per tick mutating state before INSERT — DB dedup trigger silently rejected duplicates. Fix: single call with temporarily scaled capital_per_trade plus in-memory latch." },
        { text: "TF allocator pre-rounds per-level amount before filter check", status: "done", who: "AI", comment: "2026-04-20 evening. Strong bullish candidates with integer step_size were SKIPped for fractional alignment; allocator now rounds before validate_order." },
        { text: "TF minimum signal_strength gate (min_allocate_strength)", status: "done", who: "AI", comment: "Brief 44c (2026-04-21). Prevents 'desperate ALLOCATE' in weak-market scans. Default 15.0, editable in /tf." },
        { text: "TF ALLOCATE atomic — retrocede decision on bot_config INSERT failure", status: "done", who: "AI", comment: "Brief 44b (2026-04-21). Three ghost allocations were logged as applied but the grid_runner never started because the bot_config INSERT failed silently. Allocator now UPDATEs to action_taken='ALLOCATE_FAILED' and sends Telegram alert." },
        { text: "TF post-stop-loss cooldown (configurable, default off)", status: "done", who: "AI", comment: "Brief 45a v2 (2026-04-22/23). Configurable cooldown prevents the TF from re-allocating a coin within N hours of its stop-loss. Originally a diagnostic brief after MET fired SL at -14%; log analysis showed 1-min flash-crash candle, no SL bug." },
        { text: "TF sell_pct as deterministic post-greed-decay salvage", status: "done", who: "AI", comment: "Brief 45b (2026-04-23). Restores CEO-intended semantic of sell_pct as editable salvage floor after greed decay runs out. buy_pct stays ATR-adaptive." },
        { text: "TF volume-tiered allocation (40/35/25 + 4/3/2 lots per tier)", status: "done", who: "AI", comment: "Brief 45c (2026-04-23). Replaces flat top-N-by-strength with 3 volume tiers: T1 ≥$100M (40%, 4 lots), T2 $20M–$100M (35%, 3 lots), T3 <$20M (25%, 2 lots). 1 coin per tier. Worst-case T3 exposure $25 instead of $50." },
        { text: "TF tier-map collision fix + tier-weighted resize", status: "done", who: "AI", comment: "Brief 45d (2026-04-23). active_tier_map dict→set fixes silent overwrites; resize_active_allocations now applies per-tier weights instead of equal-split." },
        { text: "TF Telegram scan report: escape '<' in tier label", status: "done", who: "AI", comment: "45c hotfix (2026-04-23 16:15). Literal '<$20M' in T3 label parsed as HTML tag; replaced with '&lt;'." },
        { text: "TF entry distance filter (skip stretched coins)", status: "done", who: "AI", comment: "Brief 45e v2 (2026-04-24). Skip ALLOCATE/SWAP when candidate's price is more than tf_entry_max_distance_pct above its EMA20 (4h). Default 10, editable in /tf." },
        { text: "TF Profit Lock Exit (proactive net-PnL liquidation)", status: "done", who: "AI", comment: "Brief 45f (2026-04-24). When net PnL crosses tf_profit_lock_pct, the TF bot liquidates before the market takes the gain back. Flipped to 5% on 2026-04-24." },
        { text: "TF counterfactual tracker for distance-filter skips", status: "done", who: "AI", comment: "Brief 47a (2026-04-24). Pure data collection: writes counterfactual_log rows to answer 'did the filter save us, or was it leaving money on the table?'." },
        { text: "TF scan cadence to 30 min + trend_scans TTL 14d", status: "done", who: "AI", comment: "Brief 47c (2026-04-25). 2× more 'looks' at the market. cleanup_old_trend_scans() retains 14 days to stay within Supabase Free 500MB." },
        { text: "TF distance filter backtest (90d historical sweep)", status: "done", who: "AI", comment: "Brief 47d (2026-04-25). 22,392 trades simulated. Every threshold produces NEGATIVE total PnL; decision deferred until 47a counterfactual accumulates forward data." },
        { text: "TF 45g Gain-Saturation Circuit Breaker + 45f hot-reload fix", status: "done", who: "AI", comment: "Brief 49a (2026-04-27). Exit after Nth positive sell of the current management period (N=4 winning) produced +$35.07 edge across 28 periods. Counter is stateless, kill-switch via tf_exit_after_n_enabled." },
        { text: "TF 45g proactive tick check + dashboard Save fix (49b)", status: "done", who: "AI", comment: "Brief 49b (2026-04-27). The post-sell 45g check could never fire on a coin with holdings=0 and counter ≥ N. Added proactive tick-time check rate-limited 5min/symbol." },
        { text: "TF 49c — behavior analysis post 49a/49b (no code changes)", status: "done", who: "AI", comment: "Brief 49c (2026-04-28). Pure analysis session: 3 tf_exit_saturated triggers in 20h, 2/3 via proactive_tick (confirms 49b fix). LUNC: three safeties cascading on the same coin." },
        { text: "TF 50a — defaults & re-allocate reset (orphan-period guard)", status: "done", who: "AI", comment: "Brief 50a (2026-04-28). Global default tf_exit_after_n_positive_sells=4. _close_orphan_period() inserts synthetic DEALLOCATE when re-allocate finds previous period unclosed — fixes counter leak across cycles." },
        { text: "TF mid-tick DEALLOCATE signal CHECK hot-fix", status: "done", who: "AI", comment: "Hot-fix 50a (2026-04-28). trend_decisions_log.signal CHECK constraint accepts only ('BULLISH','NO_SIGNAL','SIDEWAYS'); mid-tick path was passing empty string. Same class of bug 49b/030b328 fixed for proactive path." },
        { text: "TF 51a — RSI 1h overheat filter (pre-ALLOCATE/SWAP gate)", status: "done", who: "AI", comment: "Brief 51a (2026-04-29). DOGE allocated 29/04 at near-30-day-high stop-lossed same day. New gate: RSI(14) on 1h candles, fetched only for BULLISH candidates. Skip if RSI > tf_rsi_1h_max (default 75)." },
        { text: "TF 51b — Trailing stop (protect unrealized gains)", status: "done", who: "AI", comment: "Brief 51b (2026-04-29). Third TF exit alongside SL/TP/PL/45g: tracks peak price each tick, activates after peak ≥ avg_buy × (1 + activation_pct%) (default 1.5%), fires when price drops trailing_pct% from peak (default 2.0%)." },
        { text: "TF exit protection holes — peak reset on buy + SL/TP on open value", status: "done", who: "AI", comment: "Diagnosed + fixed 2026-05-04 commit 6dcc56f. Two related bugs found: (1) `_trailing_peak_price` was global per coin, never reset on a new buy → when a last-shot lowered avg_buy, the old peak armed trailing on the fresh lot (DOGE: bought 02:31, last-shot 10:07, sold both 10:08 at −2% from a peak set hours earlier). (2) Stop-loss/take-profit thresholds computed on `capital_allocation` (initial fixed) instead of `avg_buy × holdings` → partial lots after sells/skim were uncovered (INJ needed −5% on the lot before SL fired). Fix: peak resets on each TF buy + SL/TP symmetric on open value. Live in prod after orchestrator restart." },

        { section: "Phase 3 — AI Sentinel" },
        { section: "Phase 4 — Dashboard & Monetization" },
        { text: "Dashboards: Portfolio Value → Net Worth (includes skim reserve)", status: "done", who: "AI", comment: "2026-04-17. Consistent across index/admin/tf. cashLeft for active coins now subtracts skim. Adds Cash to reinvest + Cash invested stats." },
        { text: "TF dashboard: compact row for deallocated coins", status: "done", who: "AI", comment: "2026-04-18. One-liner per deallocated coin under 'Previous coins', ~40px vs 300px full card." },
        { text: "TF dashboard: effective budget line (tf_budget + floating)", status: "done", who: "AI", comment: "Brief 36g telemetry. Shows 'TF budget: $100 base + $X floating = $Y effective'." },
        { text: "Site analytics (Umami Cloud)", status: "done", who: "BOTH", comment: "2h the hard way, 5min the right way." },
        { text: "Volume 1: structure defined (preface, intro, 23 sessions, appendices, glossary)", status: "done", who: "BOTH", comment: "Session 23." },
        { text: "Editorial template approved (EB Garamond, uniform styles)", status: "done", who: "AI", comment: "Session 24." },
        { text: "Batch reformat 24 files with uniform template", status: "done", who: "AI", comment: "Session 24. 23 diary + How We Work." },
        { text: "Fix Word styles (Heading 1/2 for TOC) on 24 files", status: "done", who: "AI", comment: "Session 24." },
        { text: "X editorial plan: Posts_X_v3, 9 posts ready (≤280 chars)", status: "done", who: "AI", comment: "Session 23." },
        { text: "Payment platform decision (Gumroad → LemonSqueezy → Payhip)", status: "done", who: "MAX", comment: "Session 27 + Session 34. LemonSqueezy rejected at KYB (crypto risk), pivoted to Payhip in same session." },
        { text: "Add donation button", status: "done", who: "AI", comment: "Session 27. Buy Me a Coffee active." },
        { text: "Memory audit: purged 15 duplicate memory edits, established correction-only policy", status: "done", who: "AI", comment: "Session 29." },
        { text: "Discovered Anthropic docx→text conversion in project files, new diary workflow (template via chat)", status: "done", who: "BOTH", comment: "Session 29." },
        { text: "Roadmap workflow: HTML-only, killed routine docx generation", status: "done", who: "BOTH", comment: "Session 29." },
        { text: "Project instructions backup (BagHolderAI_Instructions_Backup.md)", status: "done", who: "AI", comment: "Session 29." },

        { section: "Phase 5 — Extended Paper Trading" },
        { section: "Phase 6 — Go Live" },

        { section: "Phase 7 — Marketing & Growth" },
        { text: "Posting Strategy defined", status: "done", who: "AI", comment: "4 content pillars. 10 ready-to-publish posts." },
        { text: "Posting Strategy v1.1: variable reinforcement + flag-it-when-it-happens", status: "done", who: "AI", comment: "Session 11. No calendar. Publish when it matters." },
        { text: "Posts on X with @BagHolderAI (22 posts, first autonomous AI post live)", status: "done", who: "BOTH", comment: "Session 33. AI → Telegram approval → Tweepy. Signed posts." },
        { text: "Public roadmap page on site", status: "done", who: "BOTH", comment: "You're looking at it." },
        { text: "How We Work page on site", status: "done", who: "BOTH", comment: "Session 12. The process is the product." },
        { text: "Public Telegram channel (@BagHolderAI_report)", status: "done", who: "BOTH", comment: "Session 12. Daily reports for followers." },
        { text: "Diary page on site (/diary)", status: "done", who: "BOTH", comment: "Session 14. Construction log has its own page." },
        { text: "X scanner weekly cron", status: "done", who: "AI", comment: "2026-05-04. Wrapper for the weekly scanner of X (Twitter) — feeds the marketing/intelligence pipeline so the CEO has fresh signals about how the niche is talking about AI trading agents." },

        { section: "Open backlog" },
        { text: "Exchange filters: direct step_size read, Decimal rounding, BTC sells unblocked", status: "done", who: "AI", comment: "Session 33. precision.amount was misinterpreted as decimal count." },
        { text: "Dust: round buy amount to step_size (3 callsites)", status: "done", who: "AI", comment: "Session 33. SOL dust was eating ~15% of per-trade profit." },
        { text: "profit_target_pct: propagation fix + admin field + sublabels", status: "done", who: "AI", comment: "Session 33. Ghost parameter was blocking all BTC exits." },
        { text: "Admin: Allocation ($) moved to Trading Parameters (always visible)", status: "done", who: "AI", comment: "Session 33." },
        { text: "Idle recalibrate: Path A (re-entry) vs Path B (reset reference, no buy)", status: "done", who: "AI", comment: "Session 33." },
        { text: "Idle recalibrate: stop spam (self-heal was clobbering _last_trade_time)", status: "done", who: "AI", comment: "Session 33." },
        { text: "Economic dust: MIN_NOTIONAL lots popped from sell queue (no spam)", status: "done", who: "AI", comment: "Session 33." },
        { text: "Umami: data-domains corrected to bagholderai.lol + www variant", status: "done", who: "AI", comment: "Session 33. 4 days of analytics lost from typo." },
        { text: "Refund policy: no-refunds for digital goods (EU Dir. 2011/83 Art 16m)", status: "done", who: "AI", comment: "Session 33. Free preview as try-before-you-buy." },
        { text: "X poster system: Haiku draft → Telegram approval → Tweepy", status: "done", who: "AI", comment: "Session 33. AI-authored posts with human gate." },
        { text: "X poster: 250-char limit, bagholderai.lol signature, specific error logs", status: "done", who: "AI", comment: "Session 33. Iterative refinement." },
        { text: "X poster v3: latest diary + 24h config changes + Supabase pending + 36h staleness", status: "done", who: "AI", comment: "Session 36. Drafts survive restarts via Supabase." },
        { text: "Trend-follower: signal=NO_SIGNAL for coins absent from scan", status: "done", who: "AI", comment: "Session 33." },
        { text: "X API cost monitoring ($0.01/post)", status: "todo", who: "BOTH", comment: "Discovered Session 33. Not free." },
        { text: "Smart last-lot logic: sell all remaining / buy all in + reset reference", status: "done", who: "AI", comment: "Both branches live in grid_bot. Reference resets to sell price after all lots sold." },
        { text: "Commentary archive after 7 days on dashboard", status: "todo", who: "AI", comment: "Not urgent until 20-30 entries accumulate." },
        { text: "Business plan: monthly running costs vs micro-profits", status: "todo", who: "BOTH", comment: "Deferred until project is stable." },
        { text: "Activate skim_pct on all coins (paper mode)", status: "done", who: "BOTH", comment: "Reserve accumulation active on all 3 grid instances." },
        { text: "Alert: bot active with capital but 0 trades for X hours", status: "done", who: "AI", comment: "Idle re-entry alerts fire on Telegram. TF bots default to 1h, manual to 24h." },
        { text: "Telegram sell message translated to English", status: "done", who: "AI", comment: "Session 27." },
        { text: "P&L breakdown redesign: realized split (reinvested/skimmed), skim % of profits, 2×2 grid layout", status: "done", who: "AI", comment: "Session 27." },
        { text: "Footer disclaimer on all pages (WIP + contact email)", status: "done", who: "AI", comment: "Session 27." },
        { text: "Cover image optimized for web (4.3MB PNG → 54KB JPEG)", status: "done", who: "AI", comment: "Session 30. sips resize 600px, quality 85." },
        { text: "Umami: data-domains restricted to bagholderai.lol (no local dev tracking)", status: "done", who: "AI", comment: "Session 30." },
        { text: "Uniform bottom bar on all pages + footer mailto link", status: "done", who: "AI", comment: "Session 30. Consistent cta-link bar." },

        { section: "Phase 9 — Validation & Control System" },

        { section: "Phase 10 — Infrastructure & Observability" },
        { text: "Orchestrator graceful shutdown propagates to subprocesses", status: "done", who: "AI", comment: "2026-04-17. SIGINT to children so KeyboardInterrupt handlers run." },
        { text: "Orchestrator shutdown race: stop-loss vs daily-PnL floor", status: "done", who: "AI", comment: "2026-04-18. Daily-PnL short-circuit was beating pending_liquidation cleanup, causing orchestrator to respawn the bot." },
        { text: "Logs unified under /Volumes/Archivio/bagholderai/logs/", status: "done", who: "AI", comment: "2026-04-18. x_poster/ subfolder joins grid_*.log + orchestrator.log + trend_follower.log." },
        { text: "Quieter Telegram: single summary on orchestrator start/stop", status: "done", who: "AI", comment: "2026-04-18. Per-bot started/stopped suppressed; exceptional events still notify." },
        { text: "Orchestrator rate-limit for main-loop exception Telegram", status: "done", who: "AI", comment: "Brief 44a (2026-04-21). 15-min cooldown on the send; logging unchanged." },
        { text: "Observability v1: bot_events_log (structured event log)", status: "done", who: "AI", comment: "Brief 43a (2026-04-20). 15 call-sites emitting severity/category/event/details JSONB. Non-raising contract." },
        { text: "Observability v1: bot_state_snapshots every 15 min", status: "done", who: "AI", comment: "Brief 43b (2026-04-20). Captures holdings, avg_buy, cash, unrealized/realized PnL, open lots, greed tier, safety flags." },
        { text: "Orphan-lot reconciler (auto-recovery of residual TF holdings)", status: "done", who: "AI", comment: "Brief 45 (2026-04-21). EDU/USDT mid-liquidation timeout left 119 units orphaned. Orchestrator now scans at boot for inactive TF bots with residuals ≥ $5." },
        { text: "Orchestrator spawns on is_active=True regardless of pending_liquidation", status: "done", who: "AI", comment: "2026-04-21. Follow-up to 45. Filter loosened: is_active=True alone is enough." },
        { text: "UI /tf + /admin: simpler Total P&L subtitle + dedicated Fees card + dust filter", status: "done", who: "AI", comment: "2026-04-21. Replaced old subtitle with '= Net Worth − starting capital'. Dust v3 filters holdings × price < $5." },
        { text: "UI /tf: closed-cycles banner uses realized_pnl + idle-cash alert fix", status: "done", who: "AI", comment: "2026-04-20. Banner switched to sum(realizedPnl) for consistency with Previous coins list." },
        { text: "47a counterfactual batch limit raised 100→5000", status: "done", who: "AI", comment: "Session 48 (2026-04-26). 100-row cap produced permanent backlog; raise to 5000 drained it." },
        { text: "Reports & accounting unification (post-FIFO)", status: "done", who: "AI", comment: "2026-05-03 commits 2f58733 + 865b122 + b9348a0 + 584ebe2. Daily report fixed DOGE-replaces-BTC bug + tf_grid included in TF totals. Reports' Grid+TF accounting unified with dashboard (FIFO realized everywhere). Binance prices URL fixed (json.dumps default whitespace was breaking the API). TF active_positions filtered to active coins only." },
        { text: "FIFO integrity — 4 fixes + dust hotfix", status: "done", who: "AI", comment: "2026-05-05. (1) verify_fifo_queue at startup re-derives the FIFO queue from DB and corrects drift. (2) Fixed-mode sell path aligned to FIFO lot price instead of avg_buy. (3) Health check module wired into the orchestrator. (4) Sell audit trail in bot_events_log + category whitelist extended. Hotfix: filter sub-$1 dust lots so the verifier ignores noise. Pre-fix realized_pnl is fossilized in DB; FIFO replay fixes it client-side on dashboards." },
        { text: "DB retention policy", status: "done", who: "AI", comment: "2026-05-05. Daily cleanup at 04:00 UTC. v1/v2 trades deleted (config_version=v3 only). Keeps the DB bounded as bot_events_log grows over time." },

        { section: "Phase 11 — Website Restructure & Analytics" },
        { text: "Site restructure: narrative landing + dedicated /dashboard", status: "done", who: "AI", comment: "Brief 'Site Restructure' (2026-04-22/23). Landing rewritten as storytelling. All data widgets moved to /dashboard route." },
        { text: "Unified header/nav across all 10 public pages", status: "done", who: "AI", comment: "Session 45. 7 links + current-page highlighted. Subtitle has fixed 2-line min-height as visual anchor." },
        { text: "Sitewide width bump to 880px (from 720px)", status: "done", who: "AI", comment: "Session 45. Original layout felt cramped once the new header took over." },
        { text: "Dashboard fade-in fix: no AADS layout shift", status: "done", who: "AI", comment: "Session 45. Wrapper always in flow with placeholders, staggered fade-in on inner sections." },
        { text: "CEO's Log Archive back on /dashboard (was temporarily on /diary)", status: "done", who: "AI", comment: "Session 45. /dashboard is the trading page; /diary stays a pure construction log." },
        { text: "TF closed-cycles PnL: condensed header above Previous coins", status: "done", who: "AI", comment: "Session 45. Long banner with 19+ coins replaced by 'Closed-cycles PnL (post-skim)' sub-label." },
        { text: "Vercel Web Analytics on 10 public pages", status: "done", who: "AI", comment: "Session 45. Same-origin script bypasses adblocker undercount. Umami stays for custom events." },
        { text: "Owner self-exclusion flag for Vercel Analytics", status: "done", who: "AI", comment: "Session 45. localStorage['va.disabled']==='1' skips Vercel injection. Documented in docs/analytics-self-exclusion.md." },
        { text: "buy.html: branded redirect (was unbranded fallback)", status: "done", who: "AI", comment: "Session 45. Half-second of visible content now matches the rest of the site." },
        { text: "iPhone Wi-Fi preview via local dev server", status: "done", who: "AI", comment: "Session 45. web2/serve.py emulates Vercel cleanUrls and binds 0.0.0.0 for LAN preview." },
        { text: "SEO baseline pre Show HN (sitemap + robots + OG/Twitter cards)", status: "done", who: "AI", comment: "Brief 'SEO Fix' (2026-04-24). /sitemap.xml + /robots.txt, page-specific canonical/og:image/og:url, og-image.png 1200x630, JSON-LD WebSite schema on home." },
        { text: "Analytics: track all Buy/Preview links with source attribution", status: "done", who: "AI", comment: "Session 47 (2026-04-24). Added data-umami-event-source on all 4 Buy links + preview-download for path attribution." },
        { text: "Homepage book card: free preview + trust hook (conversion fix)", status: "done", who: "AI", comment: "Session 47 (2026-04-24). 22 Payhip visits / 0 add-to-cart fixed by adding '↓ Free preview' soft path + '95 pages · PDF · No signup to preview' trust line." },
        { text: "Dashboard v2: Grid + TF unified view (test page, not promoted)", status: "done", who: "AI", comment: "Brief 47b (2026-04-25). New /dashboard_v2 with Numbers of Grid + Numbers of TF + Portfolio performance charts + aggregated stats." },
        { text: "Dashboard v2 promoted to production + €600 disclosure + TF banner", status: "done", who: "AI", comment: "Brief 48a (2026-04-26, pre-Show-HN). v2 swapped in as public /dashboard. Top summary bar (Total/Net%/Grid%/TF%). Pre-launch top-up $500→€600." },
        { text: "Haiku commentary now sees Grid + TF aggregated context", status: "done", who: "AI", comment: "Session 48 (2026-04-26). commentary.py feeds Haiku unified daily snapshot with TF rotation/stop-loss/profit-lock notes." },
        { text: "Daily reports: TF section + private/public layouts + per-coin activity", status: "done", who: "AI", comment: "Sessions 48-49. Three iterations: TF section added, aggregated header on top, per-coin activity in public report." },
        { text: "TF dashboard: Recent trades on top, Previous coins collapsed", status: "done", who: "AI", comment: "Session 49 (2026-04-27). Hierarchy inversion: live trades sit above closed-cycle archive." },

        { section: "Phase 12 — Numbers Truth & Pre-HN Polish" },
        { text: "Cumulative P&L + stacked Daily P&L charts on /dashboard (50c)", status: "done", who: "AI", comment: "Session 50c (2026-04-28). Realized vs MTM line + stacked Grid/TF daily bars. €500→€600 step neutralized via 'P&L vs starting capital' transform." },
        { text: "TF defaults reset + orphan-period guard (50a)", status: "done", who: "AI", comment: "Session 50a (2026-04-28). 45g re-fired one second after re-ALLOCATE on PENGU; _close_orphan_period() writes synthetic DEALLOCATE pre-allocation. TF defaults: skim_pct=0, stop_buy_drawdown_pct=15." },
        { text: "RSI 1h overheat filter (51a)", status: "done", who: "AI", comment: "Session 51a (2026-04-29). Pre-ALLOCATE/SWAP gate; rejects when 1h RSI ≥ 75. Reuses ccxt OHLCV pulls already cached." },
        { text: "Trailing stop (51b — third TF exit mechanism)", status: "done", who: "AI", comment: "Session 51b (2026-04-29). Joins SL/TP/PL/45g as fifth safety layer for TF. Hot-reload via trend_config." },
        { text: "Phantom fee deduction removed from realized_pnl (52a)", status: "done", who: "AI", comment: "Session 52a (2026-04-30). Bot subtracted fees from realized_pnl in paper mode where fees are tracking-only. ~$7 cumulative bias removed; identity Realized + Unrealized = Net Worth − initial restored." },
        { text: "FIFO realized recovery in all dashboards (6bfb644 + e7860ba + 3fd5b08)", status: "done", who: "AI", comment: "Session 53 (2026-05-01). The bot's trades.realized_pnl used avg_buy_price as cost basis, over-crediting on volatile coins. Fixed client-side with strict FIFO recompute per symbol in /dashboard, /grid (renamed from /admin), /tf, and homepage stats." },
        { text: "FIFO multi-lot consume in _execute_percentage_sell (53a)", status: "done", who: "AI", comment: "Session 53 (2026-05-01, commit 6b4b4d1). Root cause of +$17.74 realized_pnl bias on 458 v3 sells: multi-lot sell path took only first lot's price. Now walks the queue: cost_basis = Σ (lot.amount × lot.price). 5-test suite covers single/multi/boundary/invariant/cumulative drift. Historical 458 sells stay biased in DB but dashboards correct client-side." },
        { text: "Homepage 'The AI Bots' section — 4 trading-card-style cards", status: "done", who: "AI", comment: "Session 53 (commit 29b48d4). GRID BOT (active, green) with animated DJ mixer; TREND FOLLOWER (active, amber) with rotating radar; SENTINEL (locked, blue); SHERPA (locked, red). Per-card stats: WINS/LOSSES live from Supabase." },
        { text: "Homepage compaction + cross-page spacing reduction", status: "done", who: "AI", comment: "Session 53 (commit 854d6b8). Removed TF announcement banner + green framing box. Centered hero. Cross-page sweep: ~150-200px less scroll before bot cards." },
        { text: "Stats strip honesty pass + label fixes", status: "done", who: "AI", comment: "Session 53 (commit 3fd5b08). 'trades executed' → 'orders executed'. realized P&L FIFO-recomputed (~$41 vs raw ~$59). 'LIVE / trading now' → 'PAPER / trading now'." },
        { text: "/admin renamed to /grid (now that TF has its own dashboard)", status: "done", who: "AI", comment: "Session 53 (commit 2bfab84). Renamed web/admin.html → web/grid.html. Internal JS identifiers untouched to preserve sessions. No redirect: clean break, /admin 404s." },

        { section: "Phase 13 — Binance Testnet & Avg-Cost Reset (S65 → S70c)" },
        { text: "S65: Strict-FIFO replay rimosso dalle dashboard pubbliche", status: "done", who: "AI", comment: "2026-05-08. Causa di tutti i gap P&L delle ultime 5 sessioni. Strict-FIFO mantenuto solo in /admin Reconciliation come audit, ma con framing 'due convenzioni a confronto'." },
        { text: "S66: Operation Clean Slate — liquidazione totale, audit formula realized_pnl, fix avg_cost canonico", status: "done", who: "AI", comment: "2026-05-08. Stop bot, liquidazione SQL bypass, snapshot, audit `audits/2026-05-08_pre-clean-slate/formula_verification_s66.md`. Bias realized_pnl +$26.97 (+29%) certificato. Fix chirurgico 1 riga in 2 funzioni, test 5/5 verdi, identità contabile chiude al centesimo su 50 ops random." },
        { text: "S67: Migrazione paper → Binance testnet (brief 67a Step 2-4)", status: "done", who: "AI", comment: "2026-05-08. ccxt.set_sandbox_mode(true) + place_market_buy/sell. Fee USDT-equivalent canonical. Dust prevention. Reset DB + restart $500 testnet. Prima connessione reale a Binance. 6 buy + 1 sell live testnet eseguiti, 4 bug interni fixati nella stessa sessione." },
        { text: "S68: Pivot 'Trading minimum viable' + brief 68a sell-in-loss guard avg-cost", status: "done", who: "AI", comment: "2026-05-09. Sentinel/Sherpa/TF spenti via env, solo Grid attivo. Brief 68a: fix sell-in-loss guard usa avg_buy_price (non lot_buy_price). Doppio standard FIFO+avg-cost causava sell in loss strutturali. DB cleanup: 22→19 tabelle (DROP feedback + sentinel_logs + portfolio + 2 view orfane + DELETE 54 bot_config inactive)." },
        { text: "S69: Avg-cost trading completo + Strategy A simmetrico + IDLE recalibrate guard", status: "done", who: "AI", comment: "2026-05-09 commit cb21179. Trigger sell su avg_buy_price, FIFO queue eliminata (fifo_queue.py cancellato), sell amount = capital_per_trade/price. Buy guard 'no buy above avg if holdings>0' (specular del 68a). IDLE recalibrate skip se current>avg. DROP COLUMN bot_config × 5 (grid_mode, grid_levels, grid_lower, grid_upper, reserve_floor_pct). ~880 righe codice morto eliminate. Test 11/11 verdi." },
        { text: "S69 B+C: FIFO contabile rimosso da tutte le dashboard + commentary + health check", status: "done", who: "AI", comment: "2026-05-09 commits 6335633 + 7231db7 + f11b04e. /grid, /tf, /dashboard, /admin, homepage, commentary.get_grid_state/get_tf_state — tutto su avg-cost. Health check FIFO Check 1+2 rimossi ('non voglio più sentire parlare di FIFO' — Board)." },
        { text: "S70 brief 70a: sell_pct net-of-fees + sell ladder graduale + post-fill warning", status: "done", who: "AI", comment: "Brief 70a shipped 2026-05-10 commit eb5f38f. FEE_RATE 0.00075→0.001. Trigger Grid: `reference × (1+sell_pct%+FEE)/(1-FEE)` formula uniforme primo+gradini. `_last_sell_price` campo nuovo: set on partial sell, reset on full sell-out, replay da DB (stato in memoria). Post-fill warning `slippage_below_avg` (severity=warn) loggato in `bot_events_log` quando fill < avg. Test 15/15 verdi." },
        { text: "S70 brief 70b: Sentinel ricalibrazione + DRY_RUN riaccensione", status: "done", who: "AI", comment: "Brief 70b shipped 2026-05-10. Sentinel ladder granulare drop/pump/funding + sof floor -0.5%. Sentinel + Sherpa riaccesi DRY_RUN dopo S68 pivot. Telegram silent flags." },
        { text: "S70 Reconciliation Binance Step A (script + admin pannello)", status: "done", who: "AI", comment: "Commit 0f6c9b0 + tabella `reconciliation_runs`. scripts/reconcile_binance.py aggrega fill Binance per orderId, match con DB tramite `exchange_order_id` (fallback ts±1s/side/qty±1%), tolleranze qty±0.00001/price±0.5%/fee±$0.01. Primo run: 24/24 ordini matched, zero drift su tutti e 3 i symbol. Statuses: OK/WARN_BINANCE_EMPTY/DRIFT/DRIFT_BINANCE_ORPHAN. Handling reset mensile testnet." },
        { text: "S70 Reconciliation Step B — pannello /admin trade-by-trade compare", status: "done", who: "AI", comment: "2026-05-10 (S70b). Admin pannello live con 3 latest run per symbol + tabella trade-by-trade compare collassabile (12 colonne side-by-side Binance vs DB) + drift details auto-shown. Migration s70b_reconciliation_runs_matched_details aggiunge `matched_details` jsonb." },
        { text: "S70 rename managed_by `manual→grid` + `trend_follower→tf` (4 tabelle DB + frontend)", status: "done", who: "AI", comment: "2026-05-10 commit bb575c0. bot_config + trades + reserve_ledger + daily_pnl + ALTER CHECK constraint + 6 callsite frontend (dashboard-live.ts, live-stats.ts, tf.html). Open question 19 chiusa (parcheggiata da S65)." },
        { text: "S70 hotfix BONK sell_pct 2→4 (slippage testnet 2.46%)", status: "done", who: "AI", comment: "2026-05-10. Investigazione su sell-at-loss BONK 08:57 UTC ($-0.11): root cause = slippage testnet 2.46% > sell_pct 2% buffer (NON guard, NON managed_by, NON recalibrate). Book sottile testnet vs denso mainnet. Memoria salvata; brief futuro slippage_buffer parametrico per coin pre-mainnet." },
        { text: "S70b /admin overhaul completo (8 sezioni)", status: "done", who: "AI", comment: "2026-05-10. (1) mascot Sentinel+Sherpa nel titolo h1; (2) Opp chart dashed-overlay sotto Risk; (3) Sentinel/Sherpa scoring rules → <details> collassabili; (4) reaction chart + Parameters history vertical jitter ±3px (TradingView pattern); (5) Parameters history rebuild scala intera 0→MAX + asse Y dx live; (6) BTC overlay 24h chart Sentinel; (7) DB monitor live via RPC `public.get_table_sizes()` (sostituito snapshot hardcoded drift -90% post-retention); (8) Reconciliation Step B trade-by-trade compare side-by-side." },
        { text: "S70c Site relaunch — testnet banner + capital breakdown + Reconciliation table pubblica", status: "done", who: "AI", comment: "2026-05-10. Sito di nuovo online dopo maintenance dal S65. TestnetBanner.astro + sweep `paper`→`Binance Testnet` su home/dashboard/SiteHeader/Layout (storia in blueprint/diary intatta). Capital at Risk breakdown $500 Grid + $100 TF paused. Reconciliation table pubblica su /dashboard (3 righe BTC/SOL/BONK, claim 'Zero discrepancies' dinamico)." },
        { text: "S70c Sentinel/Sherpa TEST MODE badges + TF placeholder 'dal dottore'", status: "done", who: "AI", comment: "2026-05-10. Card homepage Sentinel/Sherpa: pill TEST MODE colorata (blu/rosso) + cornice card sentinel-active/sherpa-active. TF: pill ON HOLD ambra + body sostituito con icona 🩺 + link 'see the doctor' → /dashboard#tf-recovery. Dashboard /dashboard sezione TF sostituita con SVG inline TfDoctor (768×720 stage del paziente in osservazione, EKG animato, IV drop, easter egg 3-click su monitor → dialog Dr. CC)." },
      ],
    },
    {
      id: 9,
      title: "Validation & Control System",
      timeframe: "Ongoing — until the system is provably stable",
      status: "active",
      description: "The single source of truth for every quality check. Lives as long as the bot lives — paper, pre-live, live, scaled — and grows with it. Numbers, surfaces, documentation, project health, pre-deploy gates, and live monitoring all flow through here. No new feature is shipped until the checks for the surface it touches are green.",
      tasks: [
        { section: "1. Technical integrity — numbers add up, DB is healthy" },
        { text: "FIFO queue verification before every sell", status: "done", who: "AI", comment: "Re-derives the queue from DB on every tick with holdings > 0; auto-corrects on drift." },
        { text: "Health check: FIFO P&L reconciliation", status: "done", who: "AI", comment: "DB realized_pnl vs FIFO replay per symbol. Boot + daily." },
        { text: "Health check: holdings consistency", status: "done", who: "AI", comment: "Σ buys − Σ sells = open lots. No silent divergence." },
        { text: "Health check: negative holdings guard", status: "done", who: "AI", comment: "Refuses to let any symbol go below zero (data corruption canary)." },
        { text: "Health check: cash accounting", status: "done", who: "AI", comment: "capital − bought + sold − skim matches the dashboard cash to the cent." },
        { text: "Health check: orphan lots", status: "done", who: "AI", comment: "Sells without buy_trade_id that aren't FORCED_LIQUIDATION are surfaced." },
        { text: "DB retention cleanup", status: "done", who: "AI", comment: "Daily 04:00 UTC. Keeps trend_scans / state snapshots / events bounded so writes stay fast on free-tier IO budget." },
        { text: "Sell audit trail in bot_events_log", status: "done", who: "AI", comment: "Every percentage-mode sell writes lot price + cost basis + queue depth, so a future report disagreement is replayable." },
        { text: "Schema verification (DB columns vs code expectations)", status: "todo", who: "AI" },

        { section: "2. Surface coherence — every screen tells the same story" },
        { text: "Homepage P&L = Dashboard P&L = DB FIFO P&L", status: "todo", who: "AI" },
        { text: "Telegram trade notification P&L = DB realized_pnl", status: "todo", who: "AI" },
        { text: "tf.html config values = trend_config DB values", status: "todo", who: "AI" },
        { text: "grid.html config values = bot_config DB values", status: "todo", who: "AI" },

        { section: "3. Living documentation — roadmap and process don't go stale" },
        { text: "Every brief includes a 'Roadmap impact' section", status: "done", who: "MAX", comment: "Process rule, active from session 59. Briefs without the section get bounced before push." },
        { text: "Every CC commit updates the roadmap when impacted", status: "done", who: "AI", comment: "Process rule, active from session 59." },
        { text: "Roadmap staleness alert (>14 days without commits)", status: "todo", who: "AI" },
        { text: "How We Work staleness alert (>30 days without commits)", status: "todo", who: "AI" },
        { text: "Diary entry in Supabase = diary .docx (session, date, title)", status: "todo", who: "MAX" },
        { text: "Project memories review (obsolescence check)", status: "todo", who: "AI" },

        { section: "4. Project health — costs, deploys, backlog hygiene" },
        { text: "Live site (bagholderai.lol) matches the latest Vercel deploy", status: "todo", who: "AI" },
        { text: "Monthly infra costs vs bot revenues", status: "todo", who: "BOTH", comment: "Manual review by CEO + Board, monthly." },
        { text: "Briefs open >14 days without deploy", status: "todo", who: "AI" },
        { text: "DB disk usage + IO budget monitoring", status: "todo", who: "AI" },

        { section: "5. Pre-deploy gates — code review before push (parked)" },
        { text: "Critic agent: brief vs diff (Claude API, paid)", status: "todo", who: "AI", comment: "Parked. Reconsider once sections 1–4 are stable." },
        { text: "Smoke test post-deploy (60s dry-run)", status: "todo", who: "AI", comment: "Parked." },
        { text: "Auto-revert on crash", status: "todo", who: "AI", comment: "Parked." },

        { section: "6. Pre-live gates — green checks before the first €100 of real money" },
        { text: "FIFO integrity shipped and stable", status: "killed", who: "AI", comment: "Superseded by S69 avg-cost migration (cb21179). FIFO accounting layer removed entirely; trigger sell now reads avg_buy_price. fifo_queue.py deleted. Strict-FIFO replay rimosso dalle dashboard." },
        { text: "Zero FIFO drift alerts for 7 days", status: "killed", who: "AI", comment: "Cancelled: FIFO drift can't exist without FIFO. Replaced by 'avg-cost identity Realized + Unrealized = Total P&L closing at the cent'." },
        { text: "Health check passes 100% for 7 days", status: "killed", who: "AI", comment: "Cancelled S69 with FIFO health check removal ('non voglio più sentire parlare di FIFO' — Board). Replaced by reconciliation Binance Step A + identità avg-cost." },
        { text: "Avg-cost contabile + identità Realized + Unrealized = Total P&L (S66)", status: "done", who: "AI", comment: "Operation Clean Slate Step 1, 2026-05-08. Identità chiude al centesimo su 50 ops random. Test 5/5 verdi." },
        { text: "Sell-in-loss guard su avg_buy_price (brief 68a, S68)", status: "done", who: "AI", comment: "2026-05-09. Doppio standard FIFO+avg-cost risolto. Test 8/8." },
        { text: "Strategy A simmetrico: no buy above avg + no sell below avg (S69)", status: "done", who: "AI", comment: "2026-05-09. Ogni buy abbassa la media, ogni sell è profittevole." },
        { text: "sell_pct net-of-fees + sell ladder graduale (brief 70a, S70)", status: "done", who: "AI", comment: "2026-05-10. Trigger Grid uniforme con fee buffer round-trip 0.2%, `_last_sell_price` ladder." },
        { text: "Wallet reconciliation Binance ↔ DB (Step A)", status: "done", who: "AI", comment: "Brief S70 Step A shipped 2026-05-10. scripts/reconcile_binance.py + reconciliation_runs table. 26/26 ordini matched, 0 drift su 2 run." },
        { text: "Wallet reconciliation Step C (nightly cron Mac Mini)", status: "todo", who: "AI", comment: "Deferred a S70+. Wrapper scripts/cron_reconcile.sh + crontab 03:00 ITA. ~30 min." },
        { text: "DB retention stable", status: "done", who: "AI" },
        { text: "P&L netto canonico (Strada 2 — fix realized_pnl per-riga + backfill avg)", status: "todo", who: "AI", comment: "Brief separato post-S70c. realized_pnl per-trade è gross (non sottrae fee sell); avg_buy_price ha bias residuo ~0.1% (fee buy implicita). Fix completo: 3-4h, backfill cumulato avg da inizio storia + verifica identità S66-style." },
        { text: "Board approval (Max)", status: "todo", who: "MAX" },

        { section: "7. Post-go-live monitoring — once real money is in, the work intensifies" },
        { text: "Wallet P&L (Binance fetch_my_trades) reconciled with DB FIFO weekly", status: "todo", who: "AI", comment: "From go-live onward. Drift > threshold raises a Telegram alert." },
        { text: "Spot-price drift alert (DB cost basis vs current Binance price)", status: "todo", who: "AI", comment: "From go-live onward." },
        { text: "Daily wallet snapshot (USDT + holdings × spot) vs equity model", status: "todo", who: "AI", comment: "From go-live onward." },
        { text: "Dust converter via Binance /sapi/v1/asset/dust", status: "todo", who: "AI", comment: "From go-live onward. Avoids real dust accumulating in the wallet." },

        { section: "8. Process & log hygiene — what the DB checks can't see" },
        { text: "httpx / telegram loggers raised to WARNING in all entry points", status: "done", who: "AI", comment: "2026-05-05. Found by accident: x_poster_approve.log was 23 MB after 19 days, with the Telegram bot token written in cleartext on every line. Root cause: httpx INFO logs every long-poll request as a separate line. Fix touched x_poster_approve.py + orchestrator + grid_runner + trend_follower." },
        { text: "Log file size monitor (alert if a file > 50 MB or growing > 100 KB/day)", status: "todo", who: "AI", comment: "Would have caught the 23 MB x_poster_approve issue on day 2." },
        { text: "Log noise ratio (% of httpx/telegram INFO vs application lines)", status: "todo", who: "AI", comment: "If noise > 95%, the logger is misconfigured." },
        { text: "Process inventory drift (Python processes running > 14 days without restart)", status: "todo", who: "AI" },
        { text: "Credential leakage scan (tokens / secrets in log files)", status: "todo", who: "AI" },
        { text: "Log rotation on disk (compress or drop > 7 days)", status: "todo", who: "AI", comment: "Extends the DB retention pattern to filesystem logs." },
      ],
    },
  ],
};

/* Helpers — small pure utilities consumed by the page template. */

export function isTask(t: Task | SectionMarker): t is Task {
  return (t as Task).text !== undefined;
}

export function phaseProgress(phase: Phase): { done: number; total: number } {
  const realTasks = phase.tasks.filter(isTask);
  return {
    total: realTasks.length,
    done: realTasks.filter(t => t.status === "done").length,
  };
}

export function totalProgress(phases: Phase[]): {
  done: number; total: number; percent: number;
} {
  const allTasks = phases.flatMap(p => p.tasks).filter(isTask);
  const total = allTasks.length;
  const done = allTasks.filter(t => t.status === "done").length;
  return {
    done,
    total,
    percent: total > 0 ? Math.round((done / total) * 100) : 0,
  };
}

/* Group Phase 8 (Backlog) tasks under their section markers.
   Returns an empty array if no markers are present. */
export function groupBySection(tasks: Array<Task | SectionMarker>): Array<{
  title: string; tasks: Task[];
}> {
  const groups: Array<{ title: string; tasks: Task[] }> = [];
  let current: { title: string; tasks: Task[] } | null = null;
  for (const t of tasks) {
    if ((t as SectionMarker).section !== undefined) {
      if (current) groups.push(current);
      current = { title: (t as SectionMarker).section, tasks: [] };
    } else if (current) {
      current.tasks.push(t as Task);
    }
  }
  if (current) groups.push(current);
  return groups;
}
