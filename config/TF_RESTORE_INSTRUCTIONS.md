# TF Restore Instructions — when Trend Follower comes back online

**Created:** 2026-05-10 (S70c, brief Claude Design TF card sizing).
**Author:** Claude Code (Intern).
**Status:** Parked. Apply when Board green-lights TF revival.

---

## Context

During S68 (2026-05-09) the Board pivoted to "Trading minimum viable":
Sentinel + Sherpa + TF spent down to env-disabled. S70c (2026-05-10)
rebuilt the public dashboard around the new minimum-viable state:

- TF "dal dottore" placeholder ([TfDoctor.astro](../web_astro/src/components/TfDoctor.astro)) replaces the
  original TF dashboard article with statistics (Net worth, Unrealized,
  Fees, Skim, Cash bar) — TF doesn't trade, no live numbers.
- `tf-natives` row in the 3-col grid (under TF, col 1 row 2) was removed
  — TF doesn't have live coins to display.
- Shared center "I tried, your turn" arrow + "picked by TF managed by
  Grid" caption KEPT in place (still semantically valid for when TF
  returns; currently sits between a paused TF and a live Grid).

When TF comes back online (`ENABLE_TF=true` + bot logic re-enabled), the
dashboard needs to revert from "patient at the doctor" mode to "active
bot with stats" mode.

---

## Reference commits

- **`6100caf`** (S65, 2026-05-08): last commit where `dashboard.astro` had
  the full original TF article + shared center + tf-natives + grid-natives.
  Snapshot of the desired post-restore state for the TF column.
- **`f12f013`** (same S65 closing snapshot, identical content): used as
  the restore source during S70c.
- **`77d4090`** (S70c, 2026-05-10): introduced `<TfDoctor />` in place of
  the TF article, removed `tf-natives` row, kept shared center + grid-natives.
  Diff `77d4090^..77d4090 -- web_astro/src/pages/dashboard.astro` shows
  exactly what was removed.

Recover the original TF block with:
```bash
git show 6100caf:web_astro/src/pages/dashboard.astro | less
```
or
```bash
git diff 77d4090^..77d4090 -- web_astro/src/pages/dashboard.astro
```

---

## Restore steps

### 1. dashboard.astro — replace `<TfDoctor>` wrapper with the TF article

In [web_astro/src/pages/dashboard.astro](../web_astro/src/pages/dashboard.astro) find the block:

```astro
{/* === TF "dal dottore" (left) — Claude Design wrapper, no aspect lock,
    stretches to row height via grid items-stretch. */}
<div class="rounded-2xl border border-white/[0.06] bg-[#0d1626] overflow-hidden">
  <TfDoctor class="h-full w-full" />
</div>
```

Replace with the original TF article (from `6100caf` — paste the block
below verbatim, or copy from `git show 6100caf:web_astro/src/pages/dashboard.astro`
lines ~162-213):

```astro
{/* === TF CARD (left) === */}
<article class="rounded-lg border border-border bg-surface p-6">
  <div class="flex items-center gap-3 mb-4 flex-wrap">
    <div class="w-[3px] h-[22px] rounded-sm" style="background:#f59e0b"></div>
    <div class="font-mono text-[14px] text-text uppercase tracking-[0.05em] font-semibold">
      Trend Follower
    </div>
    <div class="font-mono text-[10px] text-text-muted">— <span id="tf-budget">…</span> · beta</div>
  </div>
  <div class="font-sans text-[12px] text-text-muted italic mb-2">{tfSubtitle}</div>

  {/* Day + Cash to reinvest — populated by JS */}
  <div class="font-mono text-[10px] text-text-muted mb-3 flex flex-wrap gap-x-3 gap-y-1">
    <span>Day <span id="tf-day">…</span></span>
    <span class="text-border">·</span>
    <span>Cash to reinvest: <span id="tf-cash-reinvest" class="text-text">…</span></span>
  </div>

  <div class="font-mono text-[11px] text-text-muted">Net worth</div>
  <div class="flex items-baseline gap-2 flex-wrap mt-1">
    <span id="tf-nw"
          class="text-[clamp(28px,5vw,38px)] font-bold tracking-tight text-text leading-none">
      —
    </span>
    <span id="tf-pnl-pct" class="font-mono text-[12px] text-text-muted">
      —
    </span>
  </div>

  <div class="my-4 border-t border-border-soft"></div>
  <div class="grid grid-cols-3 gap-y-3 gap-x-4 font-mono">
    <div>
      <div class="text-[10px] text-text-muted">Unrealized</div>
      <div id="tf-unrealized" class="text-[14px] font-medium text-text-muted">—</div>
    </div>
    <div>
      <div class="text-[10px] text-text-muted">Fees paid</div>
      <div id="tf-fees" class="text-[14px] font-medium text-text-muted">—</div>
    </div>
    <div>
      <div class="text-[10px] text-text-muted">Skim</div>
      <div id="tf-skim" class="text-[14px] font-medium text-text-muted">—</div>
    </div>
  </div>

  <div class="my-4 border-t border-border-soft"></div>
  <div class="flex justify-between font-mono mb-2">
    <span class="text-[10px] text-text-muted">Cash</span>
    <span id="tf-cash-pct" class="text-[10px] text-text">—</span>
  </div>
  <div id="tf-cash-bar" class="h-2 bg-border rounded-md overflow-hidden flex"></div>
</article>
```

### 2. dashboard.astro — re-add `tf-natives` row

In the BOTTOM ROW section (currently `<div></div><div></div><div id="grid-natives">`),
replace the first `<div></div>` (col 1 placeholder) with the tf-natives
container:

**Before:**
```astro
{/* === BOTTOM ROW (inside same grid):
    col 1 (sotto TF) + col 2 (centro) = vuoti, col 3 = grid natives.
    TF natives intentionally NOT here while TF is paused; see
    TF_RESTORE_INSTRUCTIONS.md for the revival step. */}
<div></div>
<div></div>
<div id="grid-natives" class="grid grid-cols-3 gap-2 h-full"></div>
```

**After:**
```astro
{/* === BOTTOM ROW: native coins under each parent card.
    Populated by JS from bot_config:
    - tf-natives:   managed_by='tf' AND is_active=true
    - grid-natives: managed_by='grid' AND is_active=true */}
<div id="tf-natives" class="grid grid-cols-3 gap-2 h-full"></div>
<div></div>
<div id="grid-natives" class="grid grid-cols-3 gap-2 h-full"></div>
```

### 3. dashboard-live.ts — already populates `#tf-natives` if present

[web_astro/src/scripts/dashboard-live.ts](../web_astro/src/scripts/dashboard-live.ts) already queries
`bot_config WHERE managed_by='tf' AND is_active=true` and populates
`#tf-natives` if the element exists in the DOM. After restoring the
element (step 2), the live data wiring works automatically — no JS
changes needed.

Verify: open `/dashboard`, the tf-natives row should populate with cards
for each TF-managed coin within ~2s after page load. If not, check the
browser console for "tf-natives" errors and that the DB has rows
matching the filter.

### 4. TfDoctor.astro — delete or archive

[web_astro/src/components/TfDoctor.astro](../web_astro/src/components/TfDoctor.astro) is no longer
referenced after step 1. Options:

- **Delete it** — clean break, the component is preserved in git history.
- **Archive it** — move to `web_astro/src/components/_archived/TfDoctor.astro`
  if you want to keep it inline as design reference.

The SVG asset files in `public/`:
- `public/tf-maintenance-dottore.svg` (V1)
- `public/tf-maintenance-dottore_V2.svg` (V2 with footClip fix)

These can stay as design archive or be deleted. They are NOT referenced
by the live code (the SVG is inline inside `TfDoctor.astro`).

### 5. dashboard.astro layout comment

Update the header comment from:
```
Hybrid: TF doctor (left) keeps Claude Design look ...
See config/TF_RESTORE_INSTRUCTIONS.md for the future TF revival.
```

Back to the pre-S70c version:
```
TF (left) + shared coins (center) + GRID (right) on top row.
Native coins under each parent on the bottom row.
```

### 6. Homepage `index.astro` — restore TF card to live mode

In [web_astro/src/pages/index.astro](../web_astro/src/pages/index.astro), the `botData` array currently has:
```ts
{ variant: "tf" as const, mode: "paused" as const, ...,
  recoveryHref: "/dashboard#tf-recovery",
  description: "Trend Follower is undergoing maintenance. Will return smarter." },
```

Revert to:
```ts
{ variant: "tf" as const, mode: "live" as const, patience: 25, speed: 90,
  capital: 100, wins: <live>, losses: <live>,
  description: "rotates capital into trending coins" },
```

`BotCardOriginal.astro` already supports `mode: "live"` — it'll render
the normal "LIVE" pill + frame + stats + footer description, no
"see the doctor" link.

### 7. PROJECT_STATE.md & roadmap.ts

Update:
- PROJECT_STATE.md §1: remove "TF paused" / "Trend Follower at the
  doctor", restore TF as active.
- roadmap.ts: Phase 2 (Trend Follower) description updated, eventual new
  achievements added under Phase 13 sub-section
  "Phase 14 — TF revival" or similar.

### 8. Final verification

- `/dashboard`: TF column shows the live article with real numbers
  (Net worth, Unrealized, Fees, Skim, Cash bar). tf-natives row
  populates with TF coins. Grid column unchanged.
- `/`: TF homepage card shows LIVE pill, normal stats, no "see the doctor".
- Smoke test 10 pages 200 OK.

---

## Notes on memory + decisions

- **Memory `feedback_story_is_process_not_numbers`**: restoring TF is a
  narrative event. Write a diary entry explaining what was fixed in TF
  during the maintenance period and what changed. The dashboard numbers
  will jump (TF starts trading again, P&L variations resume).
- **Memory `project_exit_mechanisms_roadmap`**: TF revival should
  coincide with the trailing-stop priority discussion (45f Profit Lock
  vs 36f trailing). Verify which exit mechanism is active before
  re-enabling TF.
- The SVG `tf-maintenance-dottore.svg` + `_V2.svg` were created by Max
  via Claude Design on 2026-05-10. They are part of the project's visual
  history — keep at minimum the V2 file archived even if unused, as
  reference for any future "patient" placeholders (Sentinel/Sherpa maint
  could reuse the visual pattern).

---

*End of restore instructions. When TF comes back, follow steps 1-8 in
order. The whole revert should take ~30 minutes if no schema or
bot_config columns have changed in the meantime.*
