# Brief 71a — Pending Task Cleanup + P&L Hero Unification

**Da:** CEO  
**Per:** CC (Claude Code)  
**Data:** 2026-05-11 (Sessione 71)  
**Basato su:** PROJECT_STATE.md commit `77d4090` (S70c chiusura, 2026-05-10)  
**Stima:** ~2-3h totali  
**Priorità:** ALTA — gating per go-live

---

## Contesto

Il Board ha deciso una micro-roadmap sequenziale: (1) chiudere tutti i pending task, (2) affrontare fee/P&L netto, (3) Sentinel/Sherpa analisi, (4) TF. Il go-live €100 slitterà oltre il 21-24 maggio — accettato.

Questo brief copre solo la Fase 1: cleanup pending + unificazione numeri P&L sulle dashboard.

---

## 🔴 TASK 1 — P&L Hero Unification (PRIORITÀ MASSIMA)

### Problema

Tre pagine mostrano tre numeri diversi per la stessa metrica:

| Pagina | Numero hero | Valore attuale |
|--------|-------------|----------------|
| grid.html (privata) | Total P&L | **+$10.24** |
| /dashboard (pubblica) | Total P&L | **+$11.42** |
| Home (pubblica) | Total P&L | **+$11.39** |

### Root cause (ipotesi CEO da verificare)

- **grid.html** calcola: `Stato Attuale = cash + holdings + skim − fees`. Risultato: $510.24 → P&L = $510.24 − $500 = **$10.24**
- **/dashboard** calcola: `Net worth = cash + holdings + skim` (SENZA sottrarre fees). Risultato: $511.42 → P&L = $511.42 − $500 = **$11.42**
- **Home** usa una query diversa o timing diverso → **$11.39**

Prova: $510.24 + $1.19 (fees grid.html) = $511.43 ≈ $511.42 (dashboard). Il centesimo è arrotondamento.

### Fix richiesto

1. **Decidere la formula canonica** — la mia raccomandazione: `Total P&L = cash + holdings_market_value + skim − fees − budget`. Ovvero: grid.html ha ragione, le fee vanno sottratte. Il P&L deve essere NET.
2. **Applicare la stessa formula su tutte e 3 le pagine** — home, /dashboard, grid.html devono leggere dagli stessi dati con la stessa logica.
3. **Il numero che il visitatore vede in grande deve essere identico ovunque** — zero discrepanze, zero arrotondamenti diversi.

### Verifica

Dopo il fix, ricaricare le 3 pagine e verificare che il numero hero sia identico (tolleranza: $0.00).

### Decisioni delegate a CC

- Scelta implementativa (query unificata vs funzione condivisa vs altro)
- Ordine dei file da modificare

### Decisioni che CC DEVE chiedere

- Se la root cause NON è fees incluse/escluse ma qualcosa di diverso → fermarsi e reportare al CEO prima di fixare
- Se il fix richiede di cambiare la formula di grid.html (che sembra corretta) → chiedere

---

## 🟡 TASK 2 — Reconciliation Step C (cron notturno)

Schema già definito in PROJECT_STATE §3:

1. Creare `scripts/cron_reconcile.sh`: `cd /Volumes/Archivio/bagholderai && source venv/bin/activate && python3.13 scripts/reconcile_binance.py --write`
2. Log output su `$HOME/cron_reconcile.log`
3. Crontab: `0 3 * * *` (03:00 ITA = 01:00 UTC, prima della retention bot 04:00 UTC)
4. Test: eseguire il wrapper manualmente una volta e verificare output
5. Verificare TCC Full Disk Access per cron su macOS

Stima: ~30 min.

### Decisioni delegate a CC

- Dettagli dello script (error handling, log rotation)

### Decisioni che CC DEVE chiedere

- Nessuna — schema già approvato

---

## 🟡 TASK 3 — Sito mobile review

Smoke test su iPhone/Android delle seguenti pagine:

- Home (bot cards + testnet banner)
- /dashboard (Reconciliation table + TF dottore SVG)
- /roadmap

Cosa cercare: overflow orizzontale, testo troncato, tabelle che escono dallo schermo, SVG che non scala.

Se trovati problemi: fix CSS inline, niente refactor.

### Decisioni delegate a CC

- Fix CSS specifici

### Decisioni che CC DEVE chiedere

- Se un fix richiede ristrutturare un componente → chiedere

---

## 🟡 TASK 4 — LAST SHOT lot_step_size fix

Bug: BUY BONK LAST SHOT path non arrotonda l'amount a `lot_step_size` → primo tentativo rejected da Binance (`-2010`), retry ha successo. Cosmetico ma genera rumore (1 Telegram + warn).

Fix: arrotondare `amount` a `lot_step_size` anche nel path LAST SHOT, stesso pattern del path normale.

Stima: ~15 min.

### Decisioni delegate a CC

- Tutto — fix chirurgico

### Decisioni che CC DEVE chiedere

- Niente

---

## 🟡 TASK 5 — Reason bugiardo (cosmetico)

Bug: quando un market order ha `fill_price ≠ check_price` (slippage), il campo `reason` del trade riporta il fill_price come se fosse il trigger price. La stringa mente.

Fix: includere `check_price` E `fill_price` + `slippage %` nel reason. Esempio: `"check $0.00000755 → fill $0.00000735 (slippage -2.6%), dropped 1.5% below last buy"`.

Stima: ~20 min.

### Decisioni delegate a CC

- Formato esatto della stringa

### Decisioni che CC DEVE chiedere

- Niente

---

## ⬜ TASK ESCLUSI DA QUESTO BRIEF (Fase 2+)

NON toccare:

- **Strada 2 P&L netto** (realized_pnl gross → net) — Fase 2 fee
- **BNB-discount fee** — Fase 2 fee
- **Slippage buffer parametrico per coin** — Fase 2 fee
- **Sentinel/Sherpa analisi** — Fase 3
- **TF** — Fase 4
- **Phase 2 grid_runner split** — post go-live
- **exchange_order_id null** — debt cosmetico, non gating

---

## Output atteso a fine sessione

1. ✅ P&L hero identico su home, /dashboard, grid.html
2. ✅ Cron reconciliation attivo su Mac Mini
3. ✅ Smoke test mobile completato (eventuali fix CSS applicati)
4. ✅ LAST SHOT lot_step_size arrotondato
5. ✅ Reason stringa corretta con check_price + slippage
6. ✅ Report per CEO con dettagli root cause P&L + eventuali sorprese

## Vincoli

- **NON modificare** la logica di trading (buy_pipeline, sell_pipeline, grid_bot) al di fuori del reason fix
- **NON modificare** Sentinel, Sherpa, TF — sono off-limits in questa fase
- **NON toccare** tabelle DB schema — solo frontend/display logic

## Roadmap impact

Se il Task 1 (P&L unification) rivela che la formula canonica richiede cambiamenti anche nel bot (non solo frontend), fermarsi e reportare — potrebbe impattare Strada 2.
