# MEMO — Brainstorming Session
**Date:** May 11, 2026 (evening)  
**Participants:** CEO (Claude) + Board (Max)  
**Type:** No-diary organizational session — ideas only, no code, no briefs  
**Duration:** ~1 hour, casual discussion  
**Mood:** Stanco ma lucido. Max ragiona ad alta voce, il CEO ascolta più di quanto proponga.

---

## 1. The Big Decision: Testnet for Everything

**Board position:** Non andare live con €100 finché tutti e 4 i cervelli non girano insieme su testnet. Il rischio non sono i soldi — è operativo. Avere Grid live su mainnet e 3 bot in debug su testnet significa che un restart dell'orchestrator, un fix a Sentinel, o un deploy sbagliato può fermare trade reali. Con un team di 3 (di cui 2 AI) non abbiamo la bandwidth per monitorare due ambienti in parallelo.

**CEO concurs.** L'unico contro: il testnet ha limiti strutturali (order book sottile, slippage irrealistico — BONK 2.46% testnet vs ~0.1% mainnet). Ad un certo punto i dati testnet non dicono più nulla di utile. Ma quel punto è più avanti, non ora.

**Go-live target revised:** Non più 18-21 maggio. Realistico: fine maggio / inizio giugno, quando tutti e 4 i cervelli girano coordinati.

**Exit criteria from testnet (to formalize):**
- Zero ORDER_REJECTED, zero crash orchestrator, zero drift reconciliation >$0.01
- Health check 100% pass per 7 giorni consecutivi
- Sentinel produce score sensati (non binari)
- Sherpa propone adjustment ragionevoli (no flicker)
- TF entra/esce con logica coerente
- I 4 cervelli non si contraddicono tra loro
- Board reads logs + /admin dashboard and says: "this system makes sense"
- 7 days clean run resets to zero if a logic-changing fix is deployed

**Narrative concern (CEO, acknowledged as wrong):** The CEO initially worried that staying on testnet too long kills the story. But the worse story is going live unprepared and losing money to an avoidable, stupid mistake. The real product is the process, and "we tested thoroughly before going live" IS the process.

---

## 2. Sentinel/Sherpa: Collect Data, Don't Touch

**Board decision:** Leave Sentinel and Sherpa running in current state for ~14 days (until ~May 25). Use the time for non-trading work. Don't touch their code during this window — the data collection is the point.

**BUT — the 3 known calibration bugs make current data questionable:**

1. **`speed_of_fall_accelerating` fires 30% of the time.** No absolute floor — in a flat market, a 0.05% dip triggers it. Should signal panic; instead signals "very slight relative acceleration on meaningless movements." Fix: add minimum threshold (e.g., 20min drop must be ≥ -0.3% before checking the 1.5× ratio).

2. **`opportunity_score` permanently stuck at 20 (minimum).** Funding short squeeze threshold too extreme (-0.01%), actual funding oscillates between -0.0046% and -0.0038%. The alarm is set to trigger at 500°C — never fires.

3. **`risk_score` is binary (20 or 40, nothing else).** Direct consequence of bug 1: the only signal that fires is the broken speed_of_fall (+20 on top of base 20). The real drop thresholds (-3%, -5%, -10% in 1h) don't fire in normal markets.

**Open question:** Fix the 3 bugs now and restart data collection from zero with calibrated Sentinel? Or wait 14 days with broken data? CEO leans toward fixing now — collecting blind data for 2 weeks is wasted time. Board to decide.

---

## 3. Sentinel Design Gap: BTC-Only Is Not Enough

**Board insight (critical):** Sentinel today watches only BTC. But BONK did +10% yesterday while BTC was flat, generating ~€7 profit. Sentinel said "risk 20, opportunity 20" — totally blind to it.

**The problem:** BTC is a good macro crash detector (when BTC drops 15%, everything drops). But the reverse doesn't hold — individual assets can pump or dump while BTC is flat. Sentinel misses all of this.

**Proposal: multi-asset monitoring with volatility-proportional scan frequency.**

The Board's key insight: scan frequency should be proportional to volatility, not inverse. BONK (±10%/day) needs 60-second scans. BTC (±1%/day in flat weeks) can get away with 300 seconds. This is the opposite of the CEO's initial proposal (slow-scan volatile assets to save IO).

Dynamic frequency: if BTC is flat for 3 days → scan every 5 min. If it starts moving → back to 60 seconds.

**Supabase IO mitigation:** Scan fast in memory (local buffer), write to Supabase only on significant change (score delta ≥5 points, or price moved ≥0.5% since last write). High scan frequency, low write frequency. This directly addresses the Disk IO budget warning email received today.

**For CC brief (when ready):** This is an architectural change to Sentinel. Needs a plan before code.

---

## 4. Time Horizons: The Missing Layers

**Board question that reframes the whole design:** "When BTC crashed from 100K to 65K, did it take 1 hour or 3 days?"

**Answer: both.** The October-to-February decline played out over ~4 months. But the Feb 6 flash crash was -15% in one day, and the Oct 10 liquidation cascade did 70% of its damage in 40 minutes.

**Implication for Sentinel/Sherpa:** The system needs at least three time horizons:

1. **Immediate (minutes):** The current fast loop. Detects flash crashes. Protects against "BTC is crashing RIGHT NOW." Grid bot currently has NO native macro protection — if BTC drops 15% in a day, Grid keeps buying at its levels as if nothing is happening. Only Sherpa (currently DRY_RUN) could tell it to stop. **⚠️ TO VERIFY WITH CC: does Grid have any drawdown/stop protection, or is it truly naked without Sherpa?**

2. **Medium-term (hours/days):** The missing slow loop (Sherpa Sprint 2). Fear & Greed Index, CMC dominance, volume trends. This would say "we're in a bear regime, reduce aggressiveness across the whole system." Connected to the Board's sell_pct insight: if the market is likely to go up 5%, don't sell at 2%.

3. **Sentiment (hours/days, but sometimes leading):** Sprint 3 — CryptoPanic + LLM classification. The Oct 10 crash was preceded by the Trump tariff announcement. News-watchers knew before the price moved. Without sentiment, Sentinel is blind until the price actually drops.

**Board position on go-live prerequisite:** Sprint 3 (sentiment) is NOT required for go-live. Fast loop recalibrated + slow loop base is enough. Sentiment gets added post-go-live with real money — it's an improvement, not a prerequisite. This keeps the timeline at weeks, not months.

---

## 5. Trend Follower: Needs Dedicated Brainstorming

**Not discussed in depth tonight — too tired. But key problems flagged for the dedicated session:**

**Current TF structure (from memory, verify with CC):**
- Scans top 50 coins, classifies via EMA + RSI
- 3 tiers by 24h volume: T1 (≥$100M), T2 (≥$20M), T3 (<$20M)
- 1 slot per tier, max 3 coins active
- **tf_grid handoff:** T1 and T2 coins selected by TF but managed by Grid logic (no stop-loss, no forced BEARISH exit, profit lock only)
- **TF manages T3 directly** — small caps, legacy stop-loss logic
- Distance filter 12% above EMA20 (blocks entry on stretched coins)
- RSI overheat filter
- SL cooldown prevents immediate re-entry after stop-loss

**The three structural problems:**

1. **Win/loss asymmetry:** TF wins often but loses big. MET: 75% win rate, but 12 wins averaged +$0.22, 4 losses averaged -$1.78. Net: -$4.47. Greed decay sells small profits (+1-2%), stop-loss erases everything.

2. **Death spiral / no memory:** SPK: 8 consecutive stop-losses. TF scans, sees BULLISH (signal has inertia), enters, gets stopped out, re-enters, gets stopped out. Eight times. SL cooldown delays re-entry but doesn't prevent it.

3. **Distance filter paralysis:** 12% fixed threshold works as protection (blocks 77% of would-be losses) but in bull markets blocks almost everything. Zero entries for days. 15% of blocked entries would have been profitable.

**Key observation:** All three problems are concentrated in Tier 3 (small caps). T1/T2 via tf_grid handoff don't have these issues — Grid logic handles them well. The question for the brainstorming: does Tier 3 make sense at all?

**Options to explore:**
- Keep T3 but with Sentinel as guardian (blacklist coins with repeated SL, adapt aggressiveness to regime)
- Eliminate T3 entirely — TF becomes pure "intelligent coin selector" for Grid
- Keep T3 but rethink the exit: trailing stop instead of fixed stop-loss
- Sentinel + Sherpa solve part of this naturally (regime-aware distance filter, per-asset monitoring)

**Action:** Schedule dedicated brainstorming session with full TF code structure from CC before reactivation.

---

## 6. Two Weeks of Non-Trading Work

**Board's "Cosa Vuole il Board" list (from Apple Notes):**
- Verificare messaggi Telegram
- Verifica IO disk su Supabase
- Sistemare grafico admin (manca opportunity risk)
- Sistemare label in italiano nei privati
- Aggiornare How We Work sul sito
- 2 scritti per il diario: How We Work aggiornato + andare live su testnet

**CEO additions:**
- Aggiornare roadmap sul sito (rimandato da S65)
- Blog section on the website: publish 2-3 diary entries as free content → funnel to Payhip volumes (currently 0/30 views — invisibility problem, not product problem)
- Email to dang@ycombinator.com to unblock Max's HN account (catch-22: karma 1, everything auto-flagged, can't build karma)
- Supabase IO check + optimize Sentinel/Sherpa write frequency (the Disk IO warning is real and gets worse with 14 days of data collection)

**Proposed sequence:**

*Week 1:* Quick Board fixes (CC session: Telegram, admin graph, labels, IO check) + How We Work content (CEO) + mail to dang + decide blog structure

*Week 2:* Blog section on site (CC) + 2 diary pieces + HN strategy (if unblocked) + roadmap update

*End of 2 weeks (~May 25):* Analyze Sentinel/Sherpa data, decide next steps for reactivation

**Marketing channels discussed:**
- **Blog on site = priority 1.** Zero cost, full control, content already exists. 2-3 diary entries published free = content marketing funnel
- **HN = priority 2, gated by dang unblock.** High risk/high reward. Show HN post could be huge if it lands
- **Discord = parked.** Requires constant presence. Empty server is worse than no server. Revisit when there's organic traction. (Board joke: "facciamolo gestire a Haiku" — filed under "crazy ideas that might work someday")

---

## 7. Ideas Worth Remembering

- "We're not failing if the bot loses money. We're failing if we stop telling the story." — Still true. But the story needs to be worth telling. Going live unprepared is a boring failure story.
- Sentinel scanning only BTC is like a weather station that only measures temperature in one city. BONK can have a hurricane while BTC is sunny.
- Scan frequency ∝ volatility. The most volatile asset needs the most attention, not the least.
- The Grid bot is naked without Sherpa. It buys mechanically during crashes. €100 is survivable; the design gap isn't.
- TF's problems are almost entirely in Tier 3 (small caps). The tf_grid handoff for T1/T2 was the right call.
- This brainstorming session itself could become a diary interlude: "how an AI CEO and a human Board think out loud, without code, without briefs."

---

## 8. Interlude Idea: "Anatomy of a Brainstorming"

The Board suggested this session could become a diary interlude — a peek behind the curtain at how strategic thinking happens in the project. Not a technical session report, but a narrative piece about the process of thinking together.

**Format idea:** First-person CEO voice, conversational. Show the back-and-forth. Show the moments where the Board corrects the CEO (distance filter attribution error, scan frequency logic inversion). Show that the AI doesn't always have the right answer and the human doesn't always ask the obvious question. The value is in the dynamic, not the conclusions.

**Working title candidates:**
- "The One Where Nobody Writes Code"
- "The One Where We Just Talk"
- "Brainstorm Protocol"

To develop in a future session — not tonight.

---

*Memo by CEO (Claude), BagHolderAI. Not a diary entry. Not a brief. Just thinking out loud, captured before it evaporates.*
