# BRIEF: Update Refund Policy Page

**Priority:** MEDIUM — needed before LemonSqueezy goes live
**File:** `web/refund.html`

---

## Context

The current refund policy offers a 14-day "no questions asked" refund on a €4.99 PDF ebook that has no DRM and a free preview. This invites abuse: download, save, request refund. EU law (Directive 2011/83, Article 16(m)) allows waiving the 14-day withdrawal right for digital content when the consumer consents to immediate delivery and acknowledges loss of withdrawal rights. LemonSqueezy's Buyer Terms already implement this waiver at checkout. We can legally have a no-refunds policy.

---

## New refund policy text

Replace the entire policy content in `web/refund.html` with this:

---

**REFUND POLICY**

*Last updated: April 13, 2026*

**Digital Products — No Refunds**

All products sold by BagHolderAI are digital goods (ebooks in PDF format) delivered instantly upon purchase. By completing your purchase, you consent to immediate delivery and acknowledge that you lose your right of withdrawal once the download becomes available, in accordance with EU Directive 2011/83/EU, Article 16(m).

Because digital files cannot be "returned" once delivered, all sales are final.

**We make this fair with a free preview.**

Every volume includes a free preview (15+ pages) available on our [Guide page](/guide) — no signup, no payment. Read it first. If you like what you see, buy it. If not, you've lost nothing.

**Exceptions**

If you experience a technical issue that prevents you from accessing your purchase (corrupted file, download failure, or you were charged but never received the file), contact us at bagholderai@proton.me within 14 days and we will either resolve the issue or issue a full refund.

We do not offer refunds for change of mind, accidental purchases, or dissatisfaction with the content — that's what the free preview is for.

**Chargebacks**

Purchases are processed by LemonSqueezy as merchant of record. If you initiate a chargeback instead of contacting us, LemonSqueezy will handle the dispute. Please reach out to us first — we're a small project and happy to help with any real issue.

**Contact**

bagholderai@proton.me

---

## Implementation notes

- Keep the existing page structure, styling, header, nav, and footer — only replace the policy text content
- Make sure the link to `/guide` works (the free preview reference)
- The email `bagholderai@proton.me` should be a clickable `mailto:` link
- Update `Last updated` date to match deployment date if different from April 13

## What NOT to touch

- Page layout, CSS, nav bar, footer — leave as-is
- `terms.html` and `privacy.html` — separate pages, not part of this brief
