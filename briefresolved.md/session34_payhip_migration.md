# INTERN BRIEF — Session 34: Payhip Migration

**Priority: HIGH**
**Date: April 14, 2026**

---

## Context

LemonSqueezy rejected our store application (crypto risk flag). We migrated to Payhip. The store is live, product is uploaded, Stripe is connected. This brief updates all site references.

**New checkout URL:** `https://payhip.com/b/a4yMc`
**New store URL:** `https://payhip.com/BagHolderAI`

---

## Task 1 — Update `web/guide.html` (CRITICAL)

The guide page currently has a disabled buy button with "coming soon" and an announcement saying "Volume 1 coming soon." The book is live. Fix this.

### 1a. Announcement banner

**Find:**
```html
<div class="announcement">📦 Volume 1 coming soon. Free preview available now — no signup required.</div>
```

**Replace with:**
```html
<div class="announcement">📦 Volume 1 is live! <a href="https://payhip.com/b/a4yMc">Get it now — €4.99</a> · Free preview also available below.</div>
```

### 1b. Buy button (CTA)

The `.btn-primary` class currently has `cursor: not-allowed`, greyed-out colors, and a "coming soon" span. Replace the entire buy button with a working link.

**Find the `.btn-primary` element** (it's inside `.cta-group`) — looks like:
```html
<a class="btn-primary" ...>Buy Volume 1 <span class="coming-soon">coming soon</span></a>
```

**Replace with:**
```html
<a class="btn-primary" href="https://payhip.com/b/a4yMc" target="_blank" rel="noopener">Buy Volume 1 — €4.99</a>
```

### 1c. Update `.btn-primary` CSS

**Find the `.btn-primary` CSS block** and replace it entirely:

```css
.btn-primary {
  font-family: var(--mono);
  font-size: 13px;
  font-weight: 600;
  padding: 10px 22px;
  border-radius: 6px;
  border: 1px solid var(--green);
  background: rgba(34, 197, 94, 0.1);
  color: var(--green);
  text-decoration: none;
  transition: all 0.2s ease;
  display: inline-block;
}
.btn-primary:hover {
  background: rgba(34, 197, 94, 0.2);
  border-color: #22c55e;
}
```

**Delete the `.btn-primary .coming-soon` CSS block entirely** (no longer needed).

### 1d. Top bar domain reference

**Find:**
```html
<span><span class="dot">●</span> VOLUME 1 — bagholder.lol</span>
```

**Replace with:**
```html
<span><span class="dot">●</span> VOLUME 1 — bagholderai.lol</span>
```

---

## Task 2 — `/buy` Redirect

Add a redirect so `bagholderai.lol/buy` goes to the Payhip checkout. This is for social sharing (clean URL).

**If `vercel.json` exists in the repo root**, add this to the `redirects` array:

```json
{
  "source": "/buy",
  "destination": "https://payhip.com/b/a4yMc",
  "permanent": false
}
```

**If `vercel.json` does NOT exist**, create it:

```json
{
  "redirects": [
    {
      "source": "/buy",
      "destination": "https://payhip.com/b/a4yMc",
      "permanent": false
    }
  ]
}
```

Use `permanent: false` (302) so we can change the destination later without cache issues.

---

## Task 3 — Update `web/refund.html`

The refund page currently mentions LemonSqueezy. Update the refund processing reference.

**Find any mention of "LemonSqueezy" or "Lemon Squeezy"** in `web/refund.html` and replace with "Payhip".

Specifically, find:
```
Refunds are processed through LemonSqueezy back to your original payment method.
```

**Replace with:**
```
Refunds are processed through Payhip back to your original payment method.
```

Check the entire file for any other LemonSqueezy references and replace them all.

---

## Task 4 — Update `web/roadmap.html`

In the ROADMAP JavaScript const, find the task about payment platform setup.

**Find:**
```javascript
{ text: "Setup payment platform (Gumroad or LemonSqueezy)", status: "done", who: "MAX", comment: "Session 33. LemonSqueezy chosen. KYB response sent, pending approval." },
```

**Replace with:**
```javascript
{ text: "Setup payment platform", status: "done", who: "MAX", comment: "Session 34. LemonSqueezy rejected (crypto risk flag). Migrated to Payhip — live in 20 minutes." },
```

Also find the "Publish Volume 1" task and update it:

**Find:**
```javascript
{ text: "Publish Volume 1", status: "todo", who: "BOTH" },
```

**Replace with:**
```javascript
{ text: "Publish Volume 1", status: "done", who: "BOTH", comment: "Session 34. Live on Payhip at €4.99. payhip.com/b/a4yMc" },
```

---

## Task 5 — Global LemonSqueezy Sweep

Search ALL files in `web/` for any remaining references to "LemonSqueezy", "Lemon Squeezy", or "lemonsqueezy.com". Replace or remove as appropriate. The old checkout URL `https://bagholderai.lemonsqueezy.com/checkout/buy/de31e991-761d-4644-9889-cd8db6dac845` is dead — replace with `https://payhip.com/b/a4yMc` wherever found.

---

## Testing Checklist

- [ ] `bagholderai.lol/guide` — buy button is green, clickable, opens Payhip checkout
- [ ] `bagholderai.lol/guide` — announcement says "Volume 1 is live"
- [ ] `bagholderai.lol/guide` — free preview PDF download still works
- [ ] `bagholderai.lol/buy` — redirects to `https://payhip.com/b/a4yMc`
- [ ] `bagholderai.lol/refund` — no mention of LemonSqueezy
- [ ] `bagholderai.lol/roadmap` — payment platform task shows Payhip
- [ ] `bagholderai.lol/roadmap` — "Publish Volume 1" shows as done
- [ ] `grep -r "lemonsqueezy\|LemonSqueezy\|lemon.squeezy" web/` returns zero results
- [ ] All pages still load correctly, no broken links
- [ ] Deploy to Vercel and confirm live

---

## What CC Does NOT Do

- Does NOT modify any bot code, config, or trading logic
- Does NOT touch the admin dashboard
- Does NOT create new pages — only edits existing ones + vercel.json
- Does NOT change the nav bar structure
- Does NOT modify the free preview PDF or its download link
