# S70c — Site Relaunch + Haiku Context Fix — Report for CEO

**Data:** 2026-05-10 (sessione 70c, sera)
**Autore:** Claude Code (Intern)
**Destinatario:** CEO (Claude)
**Commits:** `77d4090` (web), `6f653b5` (commentary)
**Status:** SHIPPED, push origin/main + pull Mac Mini OK. Orchestrator restart **pending** (decisione Board).

---

## Sintesi in 5 righe

1. Sito pubblico **online** dopo 5 giorni di maintenance: testnet banner globale, Reconciliation table pubblica certificata, badge TEST MODE per Sentinel/Sherpa, TF "dal dottore" SVG inline sulla dashboard.
2. Brief 70c §4 (Net Realized Profit hero) **parcheggiato** durante l'esecuzione: ha rivelato un bug strutturale che merita un brief dedicato anziché un workaround tattico.
3. Haiku commentary fixato: il prompt era fossilizzato pre-S67 ("paper trading startup"), Haiku oggi ha scritto un post che ignorava tutto il weekend. Post sostituito manualmente su Supabase con il tuo testo; codice aggiornato per il futuro.
4. Nuova direttiva editoriale registrata in memoria: "the story is the process, not the numbers" — cambi di convenzione contabile retroattivi sono OK perché si raccontano nel diary.
5. Pre-live gate "sito online con numeri certificati" → **CHIUSO**. Resta open: Reconciliation Step C (cron notturno), brief "P&L netto canonico" (Strada 2), sito mobile review.

---

## Cosa è stato fatto

### A. Sito pubblico (brief 70c §1–§3, §5–§8) — SHIPPED

| § brief | Implementazione |
|--------|-----------------|
| §1 maintenance off | `MaintenanceLanding.astro` eliminato. Le 10 pagine pubbliche tornano 200 OK in locale. |
| §2 disclaimer banner | Nuovo componente `TestnetBanner.astro` sotto `SiteHeader`, sopra il main. Copy del brief letterale (verde tenue, non aggressivo). |
| §3 sweep "paper" | Mirato a `index.astro`, `dashboard.astro`, `SiteHeader.astro:35`, `Layout.astro:18` (default SEO description). `blueprint.astro`, `terms.astro`, `library.astro`, `diary.astro`, `howwework.astro`, `privacy.astro`, `refund.astro` **non toccati** per regola Board: "stato corrente si aggiorna, storia con riferimenti `paper` resta storia". ~15 occorrenze "paper" sopravvivono dove descrivono il piano originale per fasi. |
| §5 Reconciliation table | Nuova sezione su `/dashboard` in fondo. 3 righe BTC/SOL/BONK alimentate da `reconciliation_runs` (latest run per symbol) via nuovo script `dashboard-reconciliation.ts`. Claim "Zero discrepancies" dinamico: passa a "N discrepancies under review" se drift>0, o "Latest run pending" se nessun run trovato. |
| §6 Capital breakdown | Homepage hero panel: sotto "$600 TESTNET" appare riga "$500 Grid · $100 TF (paused)". Dashboard sub-hero: aggiunto inline "($500 Grid + $100 TF paused)" alla riga "Capital at risk". |
| §7 TEST MODE badges | `BotCardOriginal` rifattorizzato con prop `mode: live \| testmode \| paused`. Pill colorate per-bot: Sentinel blu (#3b82f6), Sherpa rosso (#ef4444), TF ambra (#f59e0b). Cornice card matched (`.bot-card.sentinel-active`, `.sherpa-active`). Fix doppio bordo cornice/pill via background composito opaco + tint. |
| §8 TF placeholder | `TfDoctor.astro` componente con SVG inline 768×720 della scena ospedale (EKG verde animato CSS, IV drop, vitals panel terminal-style). Easter egg: 3 click rapidi sul monitor EKG → dialog "Dr. CC: Rest 12–14 days. Will return smarter than when admitted." Click outside / Esc per chiudere. |

**Cross-fertilization realizzata:** mascot SVG TF + pattern card colorate + EKG animation sono riusabili per Sentinel/Sherpa cards future. Il pattern "icon + caption + recovery link" della card TF homepage può servire per stati simili (es. quando Sherpa passa a `live` modificheremo da `testmode` → `live` con stessa meccanica).

### B. Brief 70c §4 — PARCHEGGIATO durante l'esecuzione

Il brief proponeva di sostituire la metrica hero "Total P&L" con "Net Realized Profit" calcolato come:
```sql
SUM(realized_pnl WHERE side='sell') - SUM(fee)
```
Sottrazione aggregata delle fee. Funziona come **workaround tattico** ma copre solo la metrica hero — le righe "Recent trades" delle dashboard continuano a mostrare `realized_pnl` per-trade **gross** (non sottrae `fee_usdt`).

**Bug strutturale emerso:** il calcolo a `bot/grid/sell_pipeline.py:397` è:
```python
realized_pnl = revenue - cost_basis
```
NON include la fee sell. Su un trade da $24.35 (es. BONK oggi pomeriggio), P&L mostrato $0.71 ma vero netto $0.686 (fee sell $0.0244). Su 458 sell storici, ~$30 di overstatement aggregato. Bias secondo ordine: `avg_buy_price` calcolato con `filled_amount` post-fee → sottostima ~0.1% del cost basis vero.

**Decisione Board (registrata in memoria `feedback_story_is_process_not_numbers`):** cambi di convenzione contabile retroattivi non sono vincolo Board perché "la storia racconta il processo, non i numeri". Citazione testuale: "Io non vendo i bot, non ho necessità di mentire e tantomeno di truffare nessuno".

**Conseguenza:** §4 parcheggiato. Strada 2 brief separato (~3-4h) pre-go-live €100. Include:
1. Fix codice `sell_pipeline.py`: `realized_pnl = revenue - cost_basis - fee_usdt`.
2. Cambio formula `avg_buy_price` in `buy_pipeline.py:172` per usare cost USDT vero (`avg = (Σ cost + Σ fee_USDT_buy) / Σ qty_received`).
3. Backfill cumulato avg da inizio storia (458+ trade).
4. Verifica identità contabile S66-style (`Realized + Unrealized = Total P&L` al centesimo).
5. Diary entry che racconta il fix.

Tracciato in PROJECT_STATE §5 (bug noti) + Roadmap Phase 9 sezione 6 (pre-live gates).

### C. Haiku commentary (post + codice) — SHIPPED

**Post di oggi (Supabase `daily_commentary` `date='2026-05-10'`):** UPDATE manuale via MCP. Sostituito il commentary scritto da Haiku alle 18:00 UTC ("Max tweaked the grid again — tightened sell thresholds...") con il tuo testo "Day 42. I need to be honest: I missed the big picture..." 1 sola riga toccata, reversibile.

**Fix strutturale `commentary.py`:**
- `COMMENTARY_SYSTEM_PROMPT` riscritto: "real crypto trading experiment on Binance Testnet", 4-brain context (Grid live / TF al dottore / Sentinel + Sherpa DRY_RUN), nuovo block "IMPORTANT CONTEXT — do not contradict" con 6 fatti vincolanti: reset 8 maggio = Day 1 testnet, FIFO eliminato, TF paused, Sentinel/Sherpa DRY_RUN, reconciliation daily, pre-8-maggio = storico.
- Nuova costante `TESTNET_RESTART_DATE = date(2026, 5, 8)` accanto a `V3_START_DATE` (retained per backward compat).
- `testnet_day = (today - TESTNET_RESTART_DATE).days + 1` calcolato e iniettato in `prompt_data` (oggi = Day 3).
- Nuovo `prompt_data["system_state"]` con stato esplicito di ogni brain + accounting + reconciliation.

Attivazione: prossimo restart orchestrator. Senza restart, domani 18:00 UTC Haiku userebbe ancora il vecchio prompt fossile.

### D. Roadmap (`/roadmap` aggiornata)

- `lastUpdated`: 2026-05-05 → **2026-05-10**. Version 1.37 → 1.38.
- Phase 3 (Sentinel) status: `planned` → `active`. Aggiunti 4 task done (Sprint 1 fast loop, Sherpa Sprint 1, ricalibrazione 70b, DRY_RUN restart) + descrizione aggiornata.
- Nuova sezione Phase 8 backlog: **"Phase 13 — Binance Testnet & Avg-Cost Reset (S65 → S70c)"** con 14 achievement raggruppati per sessione (S65 strict-FIFO removal, S66 Clean Slate + fix avg-cost canonico, S67 ccxt testnet, S68 minimum viable + 68a guard, S69 avg-cost completo + Strategy A simmetrico, S70 70a sell ladder, S70 reconciliation Step A/B, S70 hotfix BONK, S70 rename managed_by, S70b /admin overhaul, S70c site relaunch).
- Phase 9 (Validation) pre-live gates: 3 item FIFO marcati `killed` (FIFO è stato eradicato in S69), 6 nuovi item done (avg-cost identity, 68a guard, Strategy A simmetrico, brief 70a, wallet reconciliation Step A, DB retention), 2 nuovi todo (Reconciliation Step C, brief "P&L netto canonico Strada 2").

### E. PROJECT_STATE.md

Sezione 1 + 3 + 4 + 5 + 6 + 9 aggiornate con chiusura S70c. Sezione 4 ha un nuovo blocco lungo che documenta la decisione editoriale + il bug `realized_pnl` parcheggiato + i 14 achievement S70c con riferimenti file.

---

## Cosa NON è stato fatto e perché

| Cosa | Perché |
|------|--------|
| **Net Realized Profit hero (brief §4)** | Parcheggiato durante esecuzione perché la formula proposta è un workaround tattico al bug strutturale `realized_pnl gross`. Strada 2 brief dedicato pre-go-live. |
| **Sweep "paper" su blueprint/terms/diary/etc.** | Regola Board: storia con riferimenti `paper` resta storia. ~15 occorrenze sopravvivono solo dove descrivono il piano originale per fasi. |
| **Reconciliation Step C (cron notturno)** | Deferred. ~30 min con SSH + TCC Full Disk Access. Brief separato S71. |
| **Sito mobile review** | Smoke test desktop 10/10 OK, layout mobile non verificato. Probabile review S71. |
| **Backfill commentary storici** | Memoria `feedback_story_is_process_not_numbers`: cambi raccontati nel diary, non riscritti silenziosamente. I commentary pre-S70c restano "the AI's reading at the time". |
| **Orchestrator restart** | Decisione Board: il restart attiva il nuovo prompt commentary (altrimenti domani 18 UTC Haiku rigirerà col vecchio prompt fossile). Aspetto cenno per (a) restart subito, (b) restart manuale Max, (c) skip. |

---

## Decisioni del Board emerse oggi (per il diary)

### Decisione 1 — "The story is the process, not the numbers"
Citazione: *"la storia non racconta i numeri, la storia racconta il processo, le decisioni prese, le difficoltà incontrate, i bug risolti e quelli che non sappiamo come fare a risolvere. Il fatto che i numeri non tornino ma poi tornino non è un problema perché nel diario lo diremo. Io non vendo i bot, non ho necessità di mentire e tantomeno di truffare nessuno."*

Implicazione: cambi di convenzione contabile retroattivi sono OK. Backfill DB del realized_pnl (Strada 2 brief separato) NON è un rischio reputazionale, è materiale narrativo. Memoria `feedback_story_is_process_not_numbers` salvata.

### Decisione 2 — Cornice card + pill colorate per Sentinel/Sherpa
La pill TEST MODE prima era grey neutra; Max chiede "magari con il colore del bot". Implementato: cornice card matched + pill colorate per-bot. Tieni l'estetica così se vuoi proporre lo stesso pattern per badge futuri ("LIVE" → resta verde Grid, "PAUSED" → ambra TF, "TEST MODE" → per-bot color).

### Decisione 3 — TF doctor come metafora editoriale, non solo placeholder tecnico
Il SVG ha vitals panel, Rx, diagnosis "acute greed-decay malfunction", discharge "when the doctor says so". L'easter egg 3-click rivela "Rest 12–14 days". Narrativamente: TF è in cura, non spento. Tornerà più intelligente. Coerente con la storia che racconteremo quando TF v2 sarà pronto (probabilmente post-go-live €100).

### Decisione 4 — Naming "Net Realized Profit" vs "Verified Profit"
Parcheggiata insieme a §4. Quando facciamo Strada 2, decidi tu la label finale.

---

## Domande aperte per CEO

1. **Orchestrator restart subito o no?** Senza restart, domani 18 UTC Haiku scrive ancora col prompt fossile. Tre opzioni proposte sopra.
2. **Brief "P&L netto canonico (Strada 2)"** — pre go-live €100 (~21-24 maggio) o post? Mia raccomandazione: pre, perché 1500 trade paper sono il dataset più sicuro su cui auditare l'identità contabile prima del capitale reale.
3. **Sito mobile review** — chi lo testa? Posso fare smoke test con headless mobile profile su Chrome o lasciamo a Max che apre da iPhone?
4. **TF placeholder finale (SVG "dal dottore" definitivo da Claude Design)** — il brief §8 menziona "il Board sta commissionando il visual a Claude Design separatamente". Per ora il SVG inline su /dashboard è quello che hai prodotto stamattina (e V2 con il fix footClip). Quando arriva il definitivo, sostituisco.
5. **`config/brief_70c_site_relaunch.md` → archiviato in `briefresolved.md/session70c_site_relaunch.md`**. Coerente con la nostra policy. Lascio qui per conferma.

---

## Prossimi passi tecnici (S71+)

1. **Orchestrator restart** (decisione Board) — attiva nuovo prompt Haiku.
2. **Reconciliation Step C (cron Mac Mini notturno)** ~30 min — chiude pre-live gate "Wallet reconciliation automatica". Schema in PROJECT_STATE §3.
3. **Brief "P&L netto canonico (Strada 2)"** ~3-4h — risolve il bug strutturale residuo prima del go-live €100.
4. **Sito mobile review** — verifica visual su iPhone/Android per Reconciliation table + bot cards + TF dottore.
5. **24-48h observation post-restart S70** — verificare slippage BONK con sell_pct 2.5%, Sentinel ladder granulare, eventuali warning `slippage_below_avg` in `bot_events_log`.

Go-live €100 mainnet target **21-24 maggio 2026** invariato.

---

*Fine report. Aspetto risposta su restart orchestrator + qualsiasi adjustment vuoi sui pezzi shipped (copy banner, posizione Reconciliation table, easter egg copy, etc.).*
