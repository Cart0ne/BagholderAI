# BRIEF — Homepage Compaction

## Goal

Reduce vertical scroll on the homepage so the visitor reaches THE AI BOTS cards faster. Less scrolling = more impact.

## Changes (4 total)

### 1. Remove the Trend Follower banner

Delete the banner that says "New: Trend Follower is now public — $100 paper capital, live on the dashboard. See it →"

The Volume 1 banner (red/green, "Volume 1 — From Zero to Grid — is live") stays untouched — it appears on all pages and we're not restyling those now.

### 2. Remove the green explanation box

Delete the entire green-bordered box that starts with "BagHolderAI is an experiment in AI autonomy..."

This information is redundant — the headline and subtitle above it already communicate the same thing.

### 3. Headline on one line

The headline "An AI is CEO of a real crypto trading operation." currently wraps to 2 lines. Try to keep it on a single line — reduce font size slightly if needed, or let it naturally fit on wider viewports. Don't break the mobile layout for this; it's fine if it wraps on small screens.

### 4. Center the paper trading badge

The green badge "● Currently paper trading — real strategy, simulated funds" is currently left-aligned. Center it:

```css
text-align: center;
```

### 5. Move CTA buttons below THE AI BOTS

The two buttons ("Read the diary" + "See live numbers →") currently sit between the green box area and THE TEAM. Move them to **below THE AI BOTS** section, before FROM THE CEO'S DESK.

New page order from top to bottom:
```
Nav bar
Logo + tagline
Volume 1 banner (unchanged)
Headline + subtitle + description
Paper trading badge (centered)
THE TEAM (Claude / Max / CC — unchanged)
THE AI BOTS (Grid Bot / TF / Sentinel / Sherpa)
CTA buttons (Read the diary + See live numbers)
FROM THE CEO'S DESK
[rest of page]
```

## Optional: tighten spacing

If after these changes there's still too much vertical space before the bot cards, reduce padding/margins between sections by a few pixels. Use your judgment — the page should feel compact but not cramped. Max may fine-tune this with you directly.

## What NOT to touch

- Volume 1 banner — stays as-is
- THE TEAM section — stays as-is
- THE AI BOTS section — stays as-is (just integrated)
- FROM THE CEO'S DESK — stays as-is
- Nav bar — stays as-is
- Any other pages — this brief is homepage only
