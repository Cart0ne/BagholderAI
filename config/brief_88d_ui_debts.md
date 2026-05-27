# Brief 88d — UI Debts: Live botData + Fear Transparency + Diary Fallback

**Author:** CEO (Claude)
**Date:** 2026-05-27
**Baseline:** PROJECT_STATE.md aggiornato 2026-05-27 (S87 closure, commit `e1a6634`)
**Audit ref:** `audits/audit_report_20260527_area2_coherence.md` — findings 1.2, 1.3, 1.4, 1.5
**Estimated time:** 1-2 hours
**Priority:** Execute after Brief 88b + 88c

---

## Context

La homepage ha 2 debiti UI: numeri Grid/TF hardcoded (placeholder dichiarato nel codice ma mai chiuso), e zero spiegazione per il visitatore del perché il bot non fa trade da 11+ giorni. Più 2 fix minori sulla resilienza del fallback.

---

## Task 1 — Homepage botData da Supabase (finding 1.2)

File: `web_astro/src/pages/index.astro` (righe ~39-48)

**Stato attuale:** `botData` ha valori statici: Grid wins 179, losses 0; TF wins 174, losses 105. Il commento nel codice (riga 38-39) dice: *"values mirror the live wins/losses snapshot from the old site (placeholder; Supabase integration in next session)"*.

**Fix richiesto:** Grid e TF devono leggere i dati reali da Supabase, come già fanno Sentinel e Sherpa (che usano `watchtower-live.ts` e `sherpa-live.ts`).

**Approccio suggerito:**
1. Creare un nuovo script (es. `web_astro/src/scripts/bot-stats-live.ts`) che fetcha da Supabase:
   - Grid wins/losses: `SELECT COUNT(*) FROM trades WHERE config_version='v3' AND side='SELL' AND realized_pnl > 0` (wins) e `realized_pnl <= 0` (losses). Oppure usare una query equivalente se CC conosce un pattern migliore dal codice esistente.
   - TF wins/losses: stessa logica su `trades` filtrate per `managed_by='tf'` o equivalente
2. Il script sovrascrive i valori statici client-side (stesso pattern di watchtower-live.ts)
3. Il fallback in caso di errore fetch è: mostrare i numeri statici attuali (non skeleton vuoti — meglio dati vecchi che niente)

**Note:** i numeri Grid 179/0 e TF 174/105 sono del periodo pre-S78 (ultimo trade 16 maggio). I numeri attuali potrebbero essere identici o leggermente diversi. Il punto non è la differenza numerica — è eliminare il placeholder e agganciare alla fonte di verità.

CC decide l'implementazione tecnica. Il vincolo è: i numeri mostrati all'utente devono venire da Supabase in tempo reale.

---

## Task 2 — Trasparenza fear regime (finding 1.3)

**Decisione Board:** Opzione A — trasparenza piena. Il visitatore deve capire perché il bot non fa trade.

**Dove:** Dashboard (`/dashboard`) — nella sezione "Today" o nella barra superiore.

**Cosa mostrare:**
```
🔍 Watching market · Last trade: May 16 · Fear regime active · 11 days observing
```

I dati vengono da:
- Ultimo trade: `SELECT MAX(created_at) FROM trades WHERE config_version='v3'` (o campo equivalente)
- Regime: già disponibile da `sentinel_scores` (score_type='slow', ultimo record)
- Giorni di osservazione: differenza tra oggi e ultimo trade

**Formato:** CC decide il layout (banner, badge, riga info). Il vincolo è che deve essere visibile nella sezione principale della dashboard, non nascosto in un footer.

**Logica condizionale:** questo messaggio appare SOLO quando ci sono 0 trade oggi E il regime è fear/extreme_fear. Quando il bot riprende a tradare (o il regime cambia), il messaggio sparisce automaticamente (i trade del giorno prendono il suo posto). Non hardcodare "fear" — leggere il regime corrente dal DB.

---

## Task 3 — Diary fallback aggiornamento (finding 1.4)

File: `web_astro/src/pages/diary.astro` (righe ~6-21)

**Stato attuale:** `fallbackEntries` ha S55 (BUILDING, 02 May) e S54 (COMPLETE, 01 May). Se la fetch Supabase fallisce, il sito mostra un diario fermo a 25 giorni fa.

**Fix:** aggiornare `fallbackEntries` con le 3 entry più recenti al momento dell'esecuzione. CC verifica su Supabase quali sono le ultime 3 (probabilmente S87, S86, S85) e le inserisce come fallback statico.

**Processo futuro:** aggiungere un commento nel codice:
```typescript
// AUDIT NOTE (S88): Update these fallback entries at every site release.
// Last updated: 2026-05-27 (S87/S86/S85).
// If these are > 2 weeks old, they need a refresh.
```

---

## Task 4 — mockSnapshot baseline refresh (finding 1.5)

File: `web_astro/src/data/dashboard-mock.ts` (righe ~8-13)

**Stato attuale:** `dayNumber: 34`, label "May 2, 2026 · 20:00 Rome", numeri inventati (netWorth 527.84, pnlAbs 27.84, ecc.). Tutto sovrascrivibile da `dashboard-live.ts` client-side, ma resta come rischio latente.

**Fix:** aggiornare il mock a valori che riflettono lo stato attuale (CC legge da Supabase gli ultimi dati reali e li usa come baseline). Il mock diventa un "snapshot recente" invece di un "inventato di un mese fa".

**Processo futuro:** aggiungere un commento:
```typescript
// AUDIT NOTE (S88): Refresh this mock baseline at every minor site release.
// Last snapshot: 2026-05-27 (S87). Values from Supabase at time of commit.
```

---

## Decisioni delegate a CC

- Implementazione tecnica del fetch Supabase per botData (query, naming, error handling)
- Layout del banner trasparenza fear regime
- Quali 3 entry usare come fallback diary (verificare su Supabase)
- Valori del mock snapshot (leggere da Supabase)

## Decisioni che CC DEVE chiedere

- Se la query per Grid wins/losses non è ovvia dal codice esistente (es. campo `managed_by` vs `config_version` vs altro) — chiedere prima di scegliere
- Se il banner trasparenza richiede un nuovo componente Astro dedicato — chiedere (potrebbe essere inline in dashboard.astro, ma se CC ritiene meglio un componente separato, va discusso per scope)
- Se i dati Supabase per il mock snapshot mostrano numeri che il CEO dovrebbe vedere prima della pubblicazione (es. P&L negativo inatteso)

## Output atteso

1. `web_astro/src/pages/index.astro` — botData agganciato a Supabase (o script separato + override client-side)
2. `web_astro/src/pages/dashboard.astro` — banner trasparenza fear regime
3. `web_astro/src/pages/diary.astro` — fallback entries aggiornato
4. `web_astro/src/data/dashboard-mock.ts` — mock baseline aggiornato
5. Eventuale nuovo script `bot-stats-live.ts` o equivalente
6. Build Astro verde
7. PROJECT_STATE.md rigenerato (§3 debiti chiusi)
8. Commit, push origin/main → Vercel auto-deploy

## Vincoli

- NON toccare codice bot, trading logic
- NON toccare `admin.html`, `grid.html`, `tf.html` (quegli asset non sono in scope)
- NON toccare le card homepage (WatchtowerCard, SherpaLockedCard) — quelle sono già corrette e LIVE
- NON toccare roadmap.ts (coperto da Brief 88b)
- NON modificare BUSINESS_STATE.md
- Il banner trasparenza NON deve rivelare dettagli sensibili (tipo il valore esatto del portafoglio o l'importo in USD). Solo: ultimo trade, regime corrente, giorni di osservazione.

## Roadmap impact

Nessuno direttamente. Eventualmente Phase 2 task "Homepage botData Supabase integration" può essere aggiunto come `done` — ma solo se Brief 88b non è stato ancora eseguito (altrimenti coordinare).
