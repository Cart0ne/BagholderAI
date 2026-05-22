# Aggiornamento BUSINESS_STATE.md — Session 81

**Da aggiornare nel file:** solo le sezioni cambiate.

---

## §1 Brand & Messaging

Nessuna modifica.

---

## §2 Marketing In-Flight

### Dev.to (cart0ne)
- **Post 2 LIVE:** "The Day Our Bot Ran Out of Money" — cross-posted 2026-05-22 ✅ (già registrato)
- **Engagement S81:** commento dettagliato su "AI Agent Failure Modes Beyond Hallucination" (Maxim Saplin) — 6 failure modes mappati all'esperienza BagHolderAI con link UTM al blog. Pubblicato 2026-05-22.
- **Canale potenziale:** Indie Hackers in fase di esplorazione (Max, 2026-05-22). Decisione rimandata al weekend. Possibile target: cross-post automation Dev.to + IH + sito.

---

## §4 Decisioni Strategiche Recenti

| Data | Decisione | Perché |
|------|-----------|--------|
| 2026-05-22 (S81) | Brief 81a Sherpa Sprint 2 SHIPPED: per-coin volatility + slow-loop gate + amplitude cap 30% | Brain Analysis S80a NO-GO step 4 — root cause "Sherpa non coin-aware". Tre blocchi architetturali chiudono i 3 pre-requisiti minimi. BONK ora riceve sell_pct ~2× di BTC. Proposte cambiano max ogni 4h (non più ogni 2min). |
| 2026-05-22 (S81) | Brief 81b Haiku commentary SHIPPED: `vs_yesterday.direction` pre-calcolato + prompt stretto 80w/100w max | Audit 60 entry found 1 error (direzione sbagliata sui negativi Day 15). Fix strutturale: Python calcola la direzione, Haiku la legge. Prompt ridotto da ~104 parole mediana a target 80. |
| 2026-05-22 (S81) | Fast ladder (DROP/PUMP/FUNDING/SPEED_OF_FALL) cancellate da Sherpa | Phase B le sposterà in Sentinel. Codice morto rimosso, git history preserva. |
| 2026-05-22 (S81) | `proposed_stop_buy_active` legato a `regime == "extreme_fear"` (non più a `risk_score > 90`) | De-coupling dal fast loop. Stop-buy telemetria ON solo nei regimi più gravi. |

---

## §5 Domande Aperte per CC

Aggiungere:
- **[S81 NEW] Cross-post automation Dev.to + Indie Hackers**: quando un post va live su `web_astro/src/content/blog/`, script che pubblica automaticamente su Dev.to via API (canonical URL, tags, serie) + prepara testo adattato per IH. Decisione rimandata post-weekend. ~2-3h stimato.
- **[S81 NEW] Audit Area 2 durante osservazione Sherpa**: CC propone di eseguirlo nei 7-10gg DRY_RUN. ~30-45min con CC fresh + audit brief.

---

## §6 Vincoli / Deadline Non-Tecnici

Aggiornare:
- **DRY_RUN Sherpa Sprint 2**: osservazione 7-10 giorni a partire da 2026-05-22 (restart PID 28217). Deadline seconda Brain Analysis: ~2026-05-29/06-01. Board decide step 4 dopo analisi.
- **Restart S81 copre anche UTM signatures S80**: x_poster.py + telegram_notifier.py ora attivi.

---

## §7 Cosa NON Sta Succedendo e Perché

Aggiungere riga:
| **Nessun cross-post automatico** | Dev.to e IH sono manuali. Automazione in valutazione, decisione post-weekend |
