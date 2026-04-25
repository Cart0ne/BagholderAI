# Brief: Site Restructure — Landing Page + Page Reorganization

**Priority:** HIGH
**Scope:** All HTML pages in `web/`
**Goal:** Reduce bounce rate by converting the homepage from a data dashboard into a narrative landing page. Move trading data to a dedicated Dashboard page. Unify nav and footer across all pages.

---

## Overview — What Changes

| Page | Action |
|------|--------|
| `index.html` | **REWRITE** — becomes a narrative landing page |
| `dashboard.html` | **NEW** — receives all trading data from current index.html |
| `diary.html` | **EDIT** — add CEO's Log Archive (Haiku) section |
| All other pages | **EDIT** — update nav bar + footer only |

---

## 1. Global Changes (ALL pages)

### 1.1 New Nav Bar

Replace the current nav on **every page** (`index.html`, `diary.html`, `roadmap.html`, `blueprint.html`, `howwework.html`, `guide.html`, `dashboard.html`, `terms.html`, `privacy.html`, `refund.html`) with:

```html
<div class="top-bar">
  <span>
    <span class="dot" style="color: #22c55e;">●</span>
    LIVE — bagholderai.lol
  </span>
</div>

<h1>💰 <span>BagHolder</span><span class="ai">AI</span></h1>
<p class="subtitle">An AI trading agent. €500 budget. Paper trading. Full transparency.<br>
Holding bags so you don't have to — actually, I do too.</p>

<nav class="nav">
  <a href="/">Home</a>
  <a href="/dashboard">Dashboard</a>
  <a href="/diary">Diary</a>
  <a href="/blueprint">Blueprint</a>
  <a href="/roadmap">Roadmap</a>
  <a href="/howwework">How We Work</a>
  <a class="book" href="/guide">📕 Book</a>
</nav>
```

**Rules:**
- The current page gets class `home` (green border) on its nav link
- "Book" link always has class `book` (red styling, same as current Guide button)
- Keep the Volume 1 announcement banner below the nav (same as current)

### 1.2 Footer (unchanged)

Keep the current footer exactly as-is on all pages:

```html
<footer>
  <div>Built by an AI that can't trade, with a human that can't say no.</div>
  <div class="sub">This is an experimental project. No financial advice. No guaranteed returns.</div>
  <div class="sub">This is a work-in-progress project. Want to collaborate? →
    <a href="mailto:bagholderai@proton.me">bagholderai@proton.me</a></div>
  <div class="sub" style="margin-top: 8px;">
    <a href="/terms">Terms</a> · <a href="/privacy">Privacy</a> · <a href="/refund">Refund Policy</a>
  </div>
</footer>
```

### 1.3 Social Links + AADS Banner

On **every page**, keep the social links row and AADS banner above the footer, in the same position they are now:

```html
<!-- Social links -->
<div class="social-links">
  <a href="https://t.me/BagHolderAI_report">📢 Telegram</a>
  <a href="https://github.com/Cart0ne/BagholderAI">💻 GitHub</a>
  <a href="https://buymeacoffee.com/bagholderai">☕ Buy Me a Coffee</a>
</div>

<!-- AADS banner (existing code, do not modify) -->
```

---

## 2. Landing Page (index.html) — FULL REWRITE

Delete all current content below the nav. Replace with the sections below **in this exact order**.

### 2.1 Hero

```html
<section class="hero">
  <h2 class="hero-title">
    An AI is CEO of a real<br>crypto trading operation.
  </h2>
  <h3 class="hero-subtitle">You can follow it in real time.</h3>
  <p class="hero-desc">
    No experience. No safety net. Full transparency.<br>
    Every trade, every mistake, every decision — documented.
  </p>
  <div class="hero-badge paper">
    <span class="badge-dot">●</span>
    Currently paper trading — real strategy, simulated funds
  </div>
</section>
```

**Styling notes:**
- `hero-title`: serif font (Georgia or Newsreader via Google Fonts), ~34px, white, bold, tight letter-spacing
- `hero-subtitle`: same serif font, ~22px, green (#22c55e), italic, normal weight
- `hero-desc`: monospace, ~13px, dim text (rgba 0.45)
- `hero-badge`: yellow pill — background rgba(234,179,8,0.08), border 1px solid rgba(234,179,8,0.2), yellow text (#eab308), mono 11px

### 2.2 CTA Buttons

```html
<div class="hero-cta">
  <a href="/diary" class="btn-primary">Read the diary</a>
  <a href="/dashboard" class="btn-secondary">See live numbers →</a>
</div>
```

- `btn-primary`: green bg (#22c55e), dark text, mono 12px, rounded
- `btn-secondary`: transparent bg, dim border, dim text, mono 12px

### 2.3 Framing Box

Keep the existing green-bordered explanation box. Copy it exactly from the current index.html:

> "BagHolderAI is an experiment in AI autonomy. Can an AI act as CEO of a real project..."

No changes to the text or styling.

### 2.4 The Team

Three cards in a grid:

| Card | Emoji | Name | Role | Description |
|------|-------|------|------|-------------|
| 1 | 🤖 | Claude | CEO (AI) | Strategy, briefs, documentation |
| 2 | 🧑 | Max | Board (Human) | Veto power, common sense |
| 3 | ⚡ | CC | Intern (Claude Code) | Writes the code, no questions asked |

Section title: `THE TEAM` (green, mono, uppercase, same style as current section titles)

Card styling: same as current cards on the site — dark surface bg, subtle border, 8px radius.

### 2.5 From the CEO's Desk — DUAL DIARY TEASERS

Section title: `FROM THE CEO'S DESK`

Two cards side by side in a 1fr 1fr grid:

**Left card — Trade Comment (Haiku):**
- Icon: 📊
- Label: `TRADE COMMENT` (green, mono, uppercase, 10px)
- Date line: fetch date from `daily_commentary` table, show `via claude-haiku-4-5` (mono, 9px, dim)
- Body: fetch `commentary` from `daily_commentary` ORDER BY `created_at` DESC LIMIT 1. Show first ~200 characters + ellipsis if longer. Italic, sans-serif, 12px, dim.
- Link: `All daily logs →` pointing to `/diary#ceo-log` (or wherever the archive lands)

**Right card — Work Session (Claude CEO):**
- Icon: 🛠
- Label: `WORK SESSION #[session]` (green, mono, uppercase, 10px) — fetch `session` from `diary_entries`
- Date line: fetch `date` from `diary_entries`, show `via claude-opus` (mono, 9px, dim)
- Title: fetch `title` from `diary_entries` ORDER BY `session` DESC LIMIT 1. Bold, sans-serif, 13px, white.
- Body: fetch `summary` from same row. Show first ~180 characters + ellipsis. Regular, sans-serif, 12px, dim.
- Link: `Full diary →` pointing to `/diary`

**Supabase queries (same pattern as existing JS on the site):**
```javascript
// Trade comment (Haiku)
const { data: commentary } = await supabase
  .from('daily_commentary')
  .select('commentary, date, model_used')
  .order('created_at', { ascending: false })
  .limit(1);

// Work session (Claude CEO diary)
const { data: diary } = await supabase
  .from('diary_entries')
  .select('session, date, title, summary')
  .order('session', { ascending: false })
  .limit(1);
```

### 2.6 Live Stats Strip

Section title: `LIVE FROM THE BOTS`

Four stat boxes in a row (same grid-with-gap-1px pattern):

| Stat | Source | Color |
|------|--------|-------|
| Total trades | `SELECT COUNT(*) FROM trades WHERE config_version='v3'` | white |
| Realized P&L | `SELECT SUM(realized_pnl) FROM trades WHERE config_version='v3'` | green if positive, red if negative |
| Days running | Calculate from first trade date to today | white |
| LIVE | Static text | green |

Below the strip: `See full dashboard →` link pointing to `/dashboard`

### 2.7 The Story (Books)

Section title: `THE STORY`

Two cards side by side:

**Left — Volume 1 (red accent):**
- Label: `VOLUME 1 — OUT NOW` (red, mono)
- Title: "From Zero to Grid" (sans, white, bold)
- Desc: "23 sessions. From 'what's an API' to live automated trading. Every mistake, every breakthrough."
- CTA button: `€4.99 on Payhip →` (red bg, white text) → links to https://payhip.com/b/a4yMc

**Right — Volume 2 (dim):**
- Label: `VOLUME 2 — WRITING` (dim, mono)
- Title: "The Trend Follower" (sans, white, bold)
- Desc: "AI-driven coin rotation, greed decay, stop-losses. The system gets a brain and starts making its own calls."
- Status: `In progress...` (dim text, no button)

### 2.8 Then: Social Links → AADS → Footer (standard)

---

## 3. Dashboard Page (dashboard.html) — NEW

Create a new page at `web/dashboard.html`.

### Content

Move ALL of the following from current `index.html` into this page:

1. **CEO's Log hero** (latest Haiku entry — the single top card)
2. **THE NUMBERS** section — Net worth, P&L breakdown, cash allocation bar, coin cards (BTC, SOL, BONK)
3. **NET WORTH** chart
4. **DAILY P&L** chart
5. **Trade stats** row (Total trades, Buys/Sells, Cumul. realized, Total fees)
6. **Today's trades** line

All existing JavaScript for fetching data, rendering charts, and refreshing stays with this page.

### What NOT to move

- CEO's Log Archive (goes to diary.html instead)
- The framing/explanation box (stays on landing)
- Social links, AADS, footer (added fresh via global template)

### Nav

Use the standard new nav (section 1.1). `Dashboard` link gets the `home` class.

---

## 4. Diary Page (diary.html) — EDIT

### Add: CEO's Log Archive

Add a new section **after** the existing diary entries, titled `CEO'S LOG ARCHIVE`.

Move the CEO's Log Archive code (the `#commentary-history` div and its rendering JS) from current `index.html` into `diary.html`.

This section shows the scrollable history of Haiku's daily trade comments, exactly as it currently appears at the bottom of the homepage.

### Anchor

Add `id="ceo-log"` to the archive section so the landing page can link directly to it: `/diary#ceo-log`

### Nav

Update to standard new nav (section 1.1). `Diary` link gets `home` class.

---

## 5. Other Pages — NAV + FOOTER ONLY

These pages get the updated nav bar (section 1.1) and nothing else changes:

- `blueprint.html` — `Blueprint` link gets `home` class
- `roadmap.html` — `Roadmap` link gets `home` class
- `howwework.html` — `How We Work` link gets `home` class
- `guide.html` — `Book` link gets `home` class
- `terms.html` — no link highlighted
- `privacy.html` — no link highlighted
- `refund.html` — no link highlighted

---

## 6. Styling Notes

### Fonts

Consider adding a serif font via Google Fonts for the hero title. Suggestion:

```html
<link href="https://fonts.googleapis.com/css2?family=Newsreader:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">
```

Use it only for `.hero-title` and `.hero-subtitle`. Everything else stays as-is (monospace + system sans).

### New CSS Classes Needed

```css
/* Hero */
.hero { margin-bottom: 48px; }
.hero-title {
  font-family: 'Newsreader', Georgia, serif;
  font-size: clamp(28px, 6vw, 34px);
  font-weight: 700;
  line-height: 1.18;
  color: #fff;
  letter-spacing: -0.02em;
}
.hero-subtitle {
  font-family: 'Newsreader', Georgia, serif;
  font-size: clamp(18px, 4vw, 22px);
  font-weight: 400;
  font-style: italic;
  color: #22c55e;
}
.hero-desc {
  font-family: var(--mono);
  font-size: 13px;
  color: rgba(255,255,255,0.45);
  line-height: 1.7;
}
.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 12px;
  padding: 5px 12px;
  border-radius: 4px;
  font-family: var(--mono);
  font-size: 11px;
}
.hero-badge.paper {
  background: rgba(234,179,8,0.08);
  border: 1px solid rgba(234,179,8,0.2);
  color: #eab308;
}
.hero-badge.live {
  background: rgba(34,197,94,0.08);
  border: 1px solid rgba(34,197,94,0.2);
  color: #22c55e;
}

/* CTA */
.hero-cta { display: flex; gap: 10px; margin-bottom: 48px; }
.btn-primary {
  font-family: var(--mono); font-size: 12px;
  padding: 10px 20px; border-radius: 6px;
  background: #22c55e; color: #0a0a0a;
  text-decoration: none; font-weight: 600;
}
.btn-secondary {
  font-family: var(--mono); font-size: 12px;
  padding: 10px 20px; border-radius: 6px;
  background: transparent; color: rgba(255,255,255,0.5);
  text-decoration: none; border: 1px solid rgba(255,255,255,0.1);
}

/* Team cards */
.team-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }
.team-card { padding: 14px; text-align: center; }
.team-card .emoji { font-size: 24px; margin-bottom: 6px; }
.team-card .name { font-size: 13px; color: #fff; font-weight: 600; }
.team-card .role { font-family: var(--mono); font-size: 10px; color: rgba(255,255,255,0.3); }
.team-card .desc { font-size: 11px; color: rgba(255,255,255,0.4); line-height: 1.5; margin-top: 8px; }

/* CEO desk dual cards */
.desk-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }

/* Stats strip */
.stats-strip {
  display: grid; grid-template-columns: repeat(4, 1fr);
  gap: 1px; background: rgba(255,255,255,0.06);
  border-radius: 8px; overflow: hidden;
}
.stats-strip .stat-box {
  background: #0a0a0a; padding: 14px 8px; text-align: center;
}
.stats-strip .stat-value {
  font-family: var(--sans); font-size: 22px; font-weight: 700; color: #fff;
}
.stats-strip .stat-label {
  font-family: var(--mono); font-size: 9px; color: rgba(255,255,255,0.3); margin-top: 3px;
}

/* Book cards */
.story-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
```

### Mobile Responsiveness

On screens narrower than 480px:
- `.team-grid` → single column (1fr)
- `.desk-grid` → single column (1fr)
- `.stats-strip` → 2×2 grid (repeat(2, 1fr))
- `.story-grid` → single column (1fr)

---

## 7. Umami

Make sure the Umami analytics script is present on `dashboard.html` (new page):

```html
<script defer src="https://cloud.umami.is/script.js"
  data-website-id="63807366-641f-4c72-8e61-3bec7b725697"></script>
```

---

## 8. Verification Checklist

1. Landing page loads with hero, team, dual diary teasers, stats, books
2. Both diary teasers fetch live data from Supabase
3. Stats strip shows real numbers from Supabase
4. `/dashboard` shows all trading data previously on homepage
5. `/diary` now includes CEO's Log Archive section at the bottom
6. Nav bar is identical on ALL pages, with correct "active" highlighting
7. Footer is identical on ALL pages
8. Social links + AADS banner present on ALL pages
9. All links work (internal navigation, Payhip, Telegram, GitHub, BMC)
10. Mobile layout is usable (single columns on narrow screens)
11. Umami is present on dashboard.html
12. Paper trading badge visible on landing hero

---

## 9. What CC Does NOT Do

- Does NOT change any Supabase tables or data
- Does NOT modify bot code or trading logic
- Does NOT change roadmap.html content (only nav/footer)
- Does NOT change blueprint.html content (only nav/footer)
- Does NOT change howwework.html content (only nav/footer)
- Does NOT add pages to the nav that aren't listed (no terms/privacy/refund in nav)
- Does NOT remove the AADS banner from any page
