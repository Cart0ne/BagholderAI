# Validation & Control System — BagHolderAI

**Created:** Session 59, May 5, 2026
**Owner:** CEO + Board
**Rule:** This document is the single source of truth for all quality checks. Update it every time a check is added, changed, or completed.

---

## Principles

1. Non fidarti della memoria di nessuno — scrivi tutto nel sistema e lascia che il sistema si controlli da solo.
2. Preferisci perdere dati consapevolmente piuttosto che rischiare che il DB non funzioni.
3. Nessuna feature nuova finché i controlli esistenti non passano tutti.
4. Ogni brief per CC include una sezione "Roadmap impact" obbligatoria.
5. Ogni commit di CC deve aggiornare roadmap.html se il brief ha impatto sulla roadmap.

---

## Regola per CC — Roadmap update obbligatorio

Da session 59 in poi, ogni brief del CEO contiene una sezione "Roadmap impact" in fondo. Se quella sezione lista dei cambiamenti (es. "Task X → done"), il commit DEVE includere l'aggiornamento corrispondente in `web_astro/src/data/roadmap.ts`. Se la sezione dice "Roadmap impact: none", non toccare la roadmap. Se il brief non ha la sezione, chiedere al CEO prima di pushare.

---

## 1. Integrità Tecnica

*I numeri tornano, il DB è sano, lo schema è coerente col codice.*

| Check | Tipo | Frequenza | Stato |
|---|---|---|---|
| FIFO queue verification before every sell | Automatico (bot) | Ogni tick con holdings > 0 | ✅ DONE (brief 57a) |
| Health check: FIFO P&L reconciliation | Automatico (bot) | Boot + giornaliero | ✅ DONE (brief 57a) |
| Health check: holdings consistency | Automatico (bot) | Boot + giornaliero | ✅ DONE (brief 57a) |
| Health check: negative holdings guard | Automatico (bot) | Boot + giornaliero | ✅ DONE (brief 57a) |
| Health check: cash accounting | Automatico (bot) | Boot + giornaliero | ✅ DONE (brief 57a) |
| Health check: orphan lots | Automatico (bot) | Boot + giornaliero | ✅ DONE (brief 57a) |
| DB retention cleanup | Automatico (orchestrator) | Giornaliero 04:00 UTC | ✅ DONE (brief 59b) |
| Sell audit trail in bot_events_log | Automatico (bot) | Ogni sell | ✅ DONE (brief 57a) |
| Schema verification (colonne DB vs codice) | 🔲 Da definire | — | 🔲 TODO |

---

## 2. Coerenza delle Superfici

*Homepage, dashboard, grid.html, tf.html, Telegram mostrano tutti la stessa verità.*

| Check | Tipo | Frequenza | Stato |
|---|---|---|---|
| Homepage P&L = Dashboard P&L = DB FIFO P&L | 🔲 Da definire | — | 🔲 TODO |
| Telegram trade notification P&L = DB realized_pnl | 🔲 Da definire | — | 🔲 TODO |
| tf.html config values = trend_config DB values | 🔲 Da definire | — | 🔲 TODO |
| grid.html config values = bot_config DB values | 🔲 Da definire | — | 🔲 TODO |

---

## 3. Documentazione Viva

*Roadmap, How We Work, memories, diary — restano aggiornati.*

| Check | Tipo | Frequenza | Stato |
|---|---|---|---|
| Roadmap staleness alert (>14 giorni senza commit) | Automatico (maintenance job) | Giornaliero | 🔲 TODO |
| How We Work staleness alert (>30 giorni senza commit) | Automatico (maintenance job) | Giornaliero | 🔲 TODO |
| Ogni brief include "Roadmap impact" section | Regola di processo (CEO) | Ogni brief | ✅ ATTIVO da session 59 |
| Ogni commit di CC aggiorna roadmap se impattata | Regola di processo (CC) | Ogni commit | ✅ ATTIVO da session 59 |
| Diary entry in Supabase = diary .docx (session, date, title) | Manuale (CEO) | Ogni sessione | 🔲 TODO |
| Project memories review (verifica obsolescenza) | 🔲 Da definire | — | 🔲 TODO |

---

## 4. Salute del Progetto

*Costi, stato del sito, tracking dei brief.*

| Check | Tipo | Frequenza | Stato |
|---|---|---|---|
| Sito live (bagholderai.lol) = ultimo deploy Vercel | 🔲 Da definire | — | 🔲 TODO |
| Costi mensili infra vs ricavi bot | Manuale (CEO + Board) | Mensile | 🔲 TODO |
| Brief aperti da >14 giorni senza deploy | 🔲 Da definire | — | 🔲 TODO |
| DB disk usage + IO budget monitoring | 🔲 Da definire | — | 🔲 TODO |

---

## 5. Pre-Deploy (Layer A — futuro)

*Code review automatico via API prima del push. Da valutare dopo che i layer 1-4 sono stabili.*

| Check | Tipo | Frequenza | Stato |
|---|---|---|---|
| Critic agent: brief vs diff | API Claude (a pagamento) | Ogni push | 🔲 PARCHEGGIATO |
| Smoke test post-deploy (dry-run 60s) | Automatico | Ogni deploy | 🔲 PARCHEGGIATO |
| Auto-revert on crash | Automatico | Ogni deploy | 🔲 PARCHEGGIATO |

---

## 6. Live Validation (€100 test)

*Stress test con soldi veri. Si fa SOLO dopo che tutti i check della sezione 1 passano per almeno 1 settimana.*

| Prerequisito | Stato |
|---|---|
| Brief 57a implementato e stabile | ✅ |
| Zero FIFO drift alerts per 7 giorni | 🔲 In osservazione dal 5 maggio |
| Health check passa al 100% per 7 giorni | 🔲 In osservazione dal 5 maggio |
| DB retention stabile (59b) | ✅ |
| Board approval (Max) | 🔲 |

---

## Changelog

| Data | Sessione | Modifica |
|---|---|---|
| 2026-05-05 | 59 | Documento creato. 57a (FIFO integrity + health check) DONE. 59b (DB retention) DONE. Osservazione 7 giorni avviata per go/no-go test €100 live. |
| 2026-05-05 | 59 | Correzione attribuzione: i check FIFO/health sono brief **57a** (non 59a). Frequenza health check: cambiata da "ogni 30 min" a "giornaliero" (eliminato spam Telegram, baseline statico non richiede polling più frequente). |
