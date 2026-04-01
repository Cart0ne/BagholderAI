# INTERN BRIEF — Session 16: Navigation Fix + Blueprint Page

## Objective

Two tasks:
1. Add `blueprint.html` to the repo (file already created, in `web/blueprint.html`)
2. Fix navigation on ALL pages so "Dashboard" is a visible button, and "Blueprint" is added everywhere

## Task 1: Add blueprint.html

Copy the provided `blueprint.html` into `web/blueprint.html`. No modifications needed.

## Task 2: Fix navigation on ALL subpages

The problem: the "← Dashboard" link is hidden in the top-bar (tiny, dim text). It should be a visible pill-button in the nav, consistent with the other links.

### Changes for `web/diary.html`:

1. **Remove** the `← Dashboard` link from the top-bar div
2. **Replace** the nav section with:
```html
<nav class="nav">
  <a href="/" class="home">Dashboard</a>
  <a href="/blueprint">Blueprint</a>
  <a href="/roadmap">Roadmap</a>
  <a href="/howwework">How We Work</a>
</nav>
```
3. **Add** this CSS rule alongside the existing `.nav a` styles:
```css
.nav a.home { border-color: rgba(34, 197, 94, 0.4); color: #22c55e; }
.nav a.home:hover { border-color: #22c55e; }
```

### Changes for `web/roadmap.html`:

Same pattern:
1. Remove `← Dashboard` from top-bar
2. Replace nav with:
```html
<nav class="nav">
  <a href="/" class="home">Dashboard</a>
  <a href="/blueprint">Blueprint</a>
  <a href="/diary">Diary</a>
  <a href="/howwework">How We Work</a>
</nav>
```
3. Add the `.nav a.home` CSS rules (same as above)

### Changes for `web/howwework.html`:

1. Remove the `← Dashboard` back-link (wherever it is)
2. Add a nav section (if it doesn't have one) or update existing:
```html
<nav class="nav">
  <a href="/" class="home">Dashboard</a>
  <a href="/blueprint">Blueprint</a>
  <a href="/diary">Diary</a>
  <a href="/roadmap">Roadmap</a>
</nav>
```
3. Add the `.nav a.home` CSS rules
4. Make sure the nav CSS exists (copy from diary.html if needed):
```css
.nav { display: flex; gap: 6px; flex-wrap: wrap; margin: 20px 0 0; }
.nav a { font-family: var(--mono); font-size: 12px; padding: 6px 14px; border-radius: 6px; background: var(--surface); border: 1px solid var(--border); color: var(--text-dim); text-decoration: none; transition: all 0.2s ease; }
.nav a:hover { border-color: #22c55e; color: #22c55e; }
.nav a.home { border-color: rgba(34, 197, 94, 0.4); color: #22c55e; }
.nav a.home:hover { border-color: #22c55e; }
```

### Changes for `web/index.html` (dashboard):

Add "Blueprint" to the existing nav:
```html
<nav class="nav">
  <a href="/blueprint">Blueprint</a>
  <a href="/diary">Diary</a>
  <a href="/roadmap">Roadmap</a>
  <a href="/howwework">How We Work</a>
</nav>
```
No "Dashboard" button needed here — we're already on the dashboard.

## Navigation pattern summary

Every page should have ALL other pages in its nav. The current page is NOT in the nav. "Dashboard" is always first with green styling (class="home").

| Page | Nav buttons (in order) |
|------|----------------------|
| Dashboard (index) | Blueprint, Diary, Roadmap, How We Work |
| Blueprint | Dashboard*, Diary, Roadmap, How We Work |
| Diary | Dashboard*, Blueprint, Roadmap, How We Work |
| Roadmap | Dashboard*, Blueprint, Diary, How We Work |
| How We Work | Dashboard*, Blueprint, Diary, Roadmap |

*Dashboard has class="home" for green styling

## Commit message

```
feat: add blueprint page + fix navigation across all pages
```

## Rules

No external connections. No launching the bot. Stop when done.
