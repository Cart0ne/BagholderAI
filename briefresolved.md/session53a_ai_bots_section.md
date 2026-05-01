# BRIEF — Integrate "THE AI BOTS" Section into Homepage

## Overview

Add a new section **"THE AI BOTS"** to the homepage, positioned **below the existing "THE TEAM" section**. The existing THE TEAM section (Claude / Max / CC) stays untouched.

This new section displays 4 trading-card-style character cards representing our trading bots, with live wins/losses data from Supabase.

## Files Included

This brief comes with a **design handoff bundle from Claude Design**:

- `team-cards.jsx` — The complete section component + Supabase hook + card frames + stat bars
- `mascots.jsx` — SVG mascot components (`GridBotSVG`, `TrendFollowerSVG`)
- `preview.html` — Working visual preview (open in browser to see animations)
- `README.md` — Full design spec with pixel-level details

**These files are design references, not production code to copy verbatim.** Recreate the section using the site's existing patterns (static HTML/CSS/JS, matching fonts, colors, layout conventions). Use the JSX as the source of truth for **visual design, animation behavior, and Supabase query shape**.

## Critical Fixes Before Implementation

### FIX 1 — `managed_by` mapping is WRONG in the handoff

The handoff code assumes:
```js
const BOT_KEY = {
  grid: 'grid_bot',          // ← WRONG
  trend: 'trend_follower',   // ← correct
};
```

**Correct mapping:**
```js
const BOT_KEY = {
  grid: 'manual',            // ← Grid bots use 'manual' in our DB
  trend: 'trend_follower',
};
```

### FIX 2 — Fallback values are wrong

The handoff uses placeholder fallbacks. Use these real-ish values instead:
```js
const FALLBACK = {
  grid:  { wins: 179, losses: 0 },
  trend: { wins: 173, losses: 103 },
};
```

### FIX 3 — Sherpa subtitle

The handoff says `"Bot Coordinator"` as subtitle for Sherpa. Keep it, but the footer ability text should say:
```
▸ coordinates all active bots
```
(This is already correct in the handoff — just confirming it should stay vague.)

## Supabase Integration

### Environment Variables Needed

```
SUPABASE_URL=https://pxdhtmqfwjwjhtcoacsn.supabase.co
SUPABASE_ANON_KEY=<the public anon key from the project settings>
```

The anon key is safe for client-side use. Max will provide it. RLS is already configured on the `trades` table with a `SELECT` policy for anonymous access.

### Query (client-side aggregation)

```
GET {SUPABASE_URL}/rest/v1/trades
  ?select=managed_by,side,realized_pnl
  &config_version=eq.v3
  &side=eq.sell
Headers:
  apikey: {SUPABASE_ANON_KEY}
  Authorization: Bearer {SUPABASE_ANON_KEY}
```

Then in JS:
```js
const agg = { grid: { wins: 0, losses: 0 }, trend: { wins: 0, losses: 0 } };
for (const row of rows) {
  const key = row.managed_by === 'manual' ? 'grid'
            : row.managed_by === 'trend_follower' ? 'trend'
            : null;
  if (!key) continue;
  if (row.realized_pnl > 0) agg[key].wins++;
  else if (row.realized_pnl < 0) agg[key].losses++;
}
```

### Future optimization

When trades table grows large, create an RPC function:
```sql
CREATE OR REPLACE FUNCTION bot_stats_v3()
RETURNS TABLE(managed_by text, wins int, losses int) AS $$
  SELECT managed_by,
    COUNT(*) FILTER (WHERE realized_pnl > 0)::int AS wins,
    COUNT(*) FILTER (WHERE realized_pnl < 0)::int AS losses
  FROM trades
  WHERE config_version='v3' AND side='sell'
  GROUP BY managed_by;
$$ LANGUAGE sql STABLE;
```
Then call via `POST /rest/v1/rpc/bot_stats_v3`. Not needed now — we have ~930 rows.

## Section Placement

In `index.html` (or wherever the homepage lives):

```
[existing content]
[THE TEAM section — Claude / Max / CC]    ← KEEP AS-IS
[THE AI BOTS section — Grid / TF / Sentinel / Sherpa]  ← ADD HERE
[rest of page]
```

Section header: `THE AI BOTS` (uppercase, monospace, green accent like existing headers)

Right side of header: status indicator showing data source
- `● live · supabase` when fetch succeeds
- `◌ fallback data` when fetch fails or key missing

## The 4 Cards

| # | Name | Color | Status | Subtitle | Footer |
|---|------|-------|--------|----------|--------|
| 1 | GRID BOT | #22c55e (green) | LIVE / ACTIVE · v3 | Methodical Trader | — |
| 2 | TREND FOLLOWER | #f59e0b (amber) | LIVE / ACTIVE · v3 | Market Scanner | — |
| 3 | SENTINEL | #3b82f6 (blue) | SOON / LOCKED | Risk Watcher | ▸ monitors positions, halts on drawdown |
| 4 | SHERPA | #ef4444 (red) | SOON / LOCKED | Bot Coordinator | ▸ coordinates all active bots |

### Static stats per card

| Bot | Patience | Speed | Capital |
|-----|----------|-------|---------|
| Grid Bot | 95 | 30 | $500 |
| Trend Follower | 25 | 90 | $100 |
| Sentinel | 0 | 0 | $0 |
| Sherpa | 0 | 0 | $0 |

WINS and LOSSES come from Supabase (live) or fallback values.

## Animations

All CSS-only, no JS animation loops:

1. **Grid Bot frame:** Mixer faders animate up/down (5s ease-in-out infinite, staggered delays)
2. **TF frame:** Radar sweep rotates (4s linear infinite), coin dots blink (SMIL animate)
3. **Stat bars:** Width transitions on data load (600ms ease-out)
4. **Coming soon cards:** Slightly dimmed (opacity 0.78), dashed border

See `README.md` in the handoff bundle for exact keyframe definitions and timing.

## Testing Checklist

- [ ] Section appears below THE TEAM, above whatever follows
- [ ] All 4 cards render with correct colors and labels
- [ ] Mixer faders animate on Grid Bot card
- [ ] Radar sweeps on TF card
- [ ] Sentinel and Sherpa show as silhouettes with "?" watermark
- [ ] With valid anon key: stats show live data, indicator says "live · supabase"
- [ ] Without anon key: stats show fallback values, indicator says "fallback data"
- [ ] `managed_by = 'manual'` maps to Grid Bot (NOT 'grid_bot')
- [ ] Page looks good on mobile (cards may need to wrap or scroll horizontally)

## Note

The mascot SVGs in `mascots.jsx` use a `shade()` helper function for color manipulation. Make sure to include it — it's at the bottom of the file.
