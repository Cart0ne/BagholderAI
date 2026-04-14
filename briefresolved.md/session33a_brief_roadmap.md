# BRIEF: Roadmap Update — Session 33

**File:** `web/roadmap.html`  
**Priority:** MEDIUM  
**Estimated effort:** 15 min  

---

## What to do

Update the ROADMAP JavaScript constant in `web/roadmap.html` with Session 33 deliverables.

---

## Changes

### 1. Open backlog section — ADD these items as `status: "done"`

Add BEFORE the existing "Smart last-lot logic" todo item:

```javascript
{ text: "Exchange filters: direct step_size read, Decimal rounding, BTC sells unblocked", status: "done", who: "AI", comment: "Session 33. precision.amount was misinterpreted as decimal count." },
{ text: "Dust: round buy amount to step_size (3 callsites)", status: "done", who: "AI", comment: "Session 33. SOL dust was eating ~15% of per-trade profit." },
{ text: "profit_target_pct: propagation fix + admin field + sublabels", status: "done", who: "AI", comment: "Session 33. Ghost parameter was blocking all BTC exits." },
{ text: "Idle recalibrate: Path A (re-entry) vs Path B (reset reference, no buy)", status: "done", who: "AI", comment: "Session 33. Differentiated alerts on Telegram." },
{ text: "Economic dust: MIN_NOTIONAL lots popped from sell queue (no spam)", status: "done", who: "AI", comment: "Session 33. Same pattern as math dust fix." },
{ text: "Umami: data-domains corrected to bagholderai.lol + www variant", status: "done", who: "AI", comment: "Session 33. 4 days of analytics lost from typo." },
{ text: "Telegram: idle spam fix (dust-aware holdings check)", status: "done", who: "AI", comment: "Session 33." },
{ text: "Refund policy: no-refunds for digital goods (EU Dir. 2011/83 Art 16m)", status: "done", who: "AI", comment: "Session 33. Free preview as try-before-you-buy." },
```

### 2. Open backlog — ADD new todo item

```javascript
{ text: "X API cost monitoring ($0.01/post)", status: "todo", who: "BOTH", comment: "Discovered Session 33. Not free." },
```

### 3. Phase 7 (Marketing & Growth) — UPDATE existing items

Find the line:
```javascript
{ text: "Posts on X with @BagHolderAI (9 published, 9 ready)", status: "done", who: "BOTH", comment: "Session 23." },
```
Replace with:
```javascript
{ text: "Posts on X with @BagHolderAI (22 posts, first autonomous AI post live)", status: "done", who: "BOTH", comment: "Session 33. AI → Telegram approval → Tweepy. Signed posts." },
```

Find the line:
```javascript
{ text: "Setup payment platform (Gumroad or LemonSqueezy)", status: "done", who: "MAX", comment: "Session 27. LemonSqueezy chosen. Account pending full activation." },
```
Replace with:
```javascript
{ text: "Setup payment platform (Gumroad or LemonSqueezy)", status: "done", who: "MAX", comment: "Session 33. LemonSqueezy chosen. KYB response sent, pending approval." },
```

---

## Validation

After editing, run:
```bash
node -e "const fs = require('fs'); const html = fs.readFileSync('web/roadmap.html','utf8'); const match = html.match(/const ROADMAP = ({[\s\S]*?});/); if (!match) { console.error('NO MATCH'); process.exit(1); } try { eval('(' + match[1] + ')'); console.log('ROADMAP valid'); } catch(e) { console.error('INVALID:', e.message); process.exit(1); }"
```

## Deploy

```bash
git add web/roadmap.html
git commit -m "roadmap: session 33 — 8 bugs fixed, first AI post, LemonSqueezy KYB"
git push
```
