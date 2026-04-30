# Brief 48a — Dashboard v2 Go-Live + Homepage Updates

**From:** CEO
**To:** CC (Intern)
**Date:** April 26, 2026
**Priority:** High — must be live before HN launch Tuesday April 28

---

## Overview

Dashboard v2 (Grid + Trend Follower unified) is ready at `/dashboard_v2`. This brief makes it the production dashboard, updates the homepage to reflect €600 total capital, and adds a TF announcement banner.

---

## Task 1 — Dashboard swap

1. Rename `web/dashboard.html` → `web/dashboard_v1_archive.html`
2. Rename `web/dashboard_v2.html` → `web/dashboard.html`
3. Verify the nav link "Dashboard" across all pages still resolves correctly (it points to `/dashboard`, Vercel cleanUrls handles the rest)

**No other file references should break** — all internal links use `/dashboard`, not the filename.

---

## Task 2 — Dashboard summary bar

Add a **summary bar** at the top of the dashboard, above the CEO's Log section. Single row, compact, monospace font. Structure:

```
Total portfolio: $XXX.XX | Net: +X.XX% | Grid: +Y.YY% | TF: +Z.ZZ%
```

- Total portfolio = Grid net worth + TF net worth
- Net % = total portfolio vs $600 starting capital
- Grid % = Grid net worth vs $500
- TF % = TF net worth vs $100
- All values fetched from the existing data sources already used in the two separate sections
- Color: green if positive, red if negative, dim if zero
- Font: `var(--mono)`, size 12px, color `var(--text-dim)` for labels, white for values

This is a **read-at-a-glance** bar. Keep it one line on desktop, wrapping allowed on mobile.

---

## Task 3 — Subtitle update (all pages)

The sitewide subtitle currently reads:

```
An AI trading agent. €500 budget. Paper trading. Full transparency.
```

Change to:

```
An AI trading agent. €500 Grid + €100 Trend Follower. Paper trading. Full transparency.
```

This subtitle appears in:
- `web/index.html` (homepage header)
- `web/dashboard.html` (dashboard header — already updated in v2? verify)
- Every other page that uses the shared header pattern

**Search for "€500 budget" across all files in `web/`** to catch every instance. The second line ("Holding bags so you don't have to — actually, I do too.") stays unchanged.

Also update the `<meta name="description">` tag in `index.html` if it still references €500.

---

## Task 4 — TF announcement banner on homepage

Add a **second banner** on the homepage, directly below the existing Volume 1 banner. Structure:

```html
<div class="announcement tf-announce">
  🟢 New: Trend Follower is now public — $100 paper capital, live on the dashboard.
  <a href="/dashboard">See it →</a>
</div>
```

Style: same `.announcement` class as the Volume 1 banner, but with a subtle differentiation:
- Use the existing green accent color (`var(--green)`) for the dot and link
- Slightly dimmer background than the Volume 1 banner to establish visual hierarchy (Volume 1 = primary CTA, TF = news)

**The Volume 1 banner stays.** Do not remove or replace it.

---

## Task 5 — Haiku prompt update

The Haiku daily commentary prompt needs to reflect that the dashboard now shows both Grid and TF. Find where the Haiku prompt is defined (likely in the bot code or a config file — check `bot/` directory for references to `daily_commentary` or `claude-haiku` or the Anthropic API call).

Update the prompt to instruct Haiku to:
- Comment on **aggregated portfolio performance** (Grid + TF combined)
- Mention TF separately when it has notable activity (new positions, stop-losses, profit locks)
- Reference total capital as $600 (not $500)

Do NOT change the Haiku model, API key, or any other parameter — only the prompt text.

---

## Files likely affected

| File | Action |
|------|--------|
| `web/dashboard.html` | RENAME from dashboard_v2.html |
| `web/dashboard_v1_archive.html` | RENAME from dashboard.html |
| `web/index.html` | Subtitle + TF banner + meta description |
| `web/diary.html` | Subtitle |
| `web/blueprint.html` | Subtitle |
| `web/howwework.html` | Subtitle |
| `web/roadmap.html` | Subtitle |
| `web/guide.html` | Subtitle |
| `web/terms.html` | Subtitle (if present) |
| `web/privacy.html` | Subtitle (if present) |
| `web/refund.html` | Subtitle (if present) |
| `bot/` (Haiku prompt file) | Prompt text update |

---

## Test checklist

- [ ] `/dashboard` loads the new unified dashboard (Grid + TF sections visible)
- [ ] Summary bar shows at the top with correct totals
- [ ] Old dashboard is archived but still accessible at `/dashboard_v1_archive` (just in case)
- [ ] Homepage shows **two banners**: Volume 1 (top) + TF announcement (below)
- [ ] Subtitle reads "€500 Grid + €100 Trend Follower" on homepage
- [ ] Subtitle reads the same on ALL other pages (spot-check at least 3)
- [ ] `<meta description>` on homepage no longer says "€500 budget"
- [ ] Haiku prompt references $600 total and mentions TF
- [ ] No console errors on homepage or dashboard
- [ ] Mobile responsive — both banners stack properly

---

## Git

```
feat(dashboard): v2 go-live — unified Grid+TF, summary bar, €600 disclosure, TF banner
```

Push directly to main. Stop when done.
