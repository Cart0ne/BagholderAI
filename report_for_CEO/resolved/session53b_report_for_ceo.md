# Session 53b — Report for CEO (Addendum)

**Data:** 2026-05-01, pomeriggio
**Continua da:** [session53_report_for_ceo.md](session53_report_for_ceo.md)
**Esiti:** 4 commit aggiuntivi, 1 trading skill esterna installata, brainstorming archiviato

## Riepilogo executive

Dopo il report 53 della mattina (FIFO fix bot + homepage rinnovata + sito pre-HN ready) abbiamo speso il pomeriggio su tre fronti: **chiusura roadmap** (3 voci dichiarate todo erano in realtà già live), **valutazione delle skill esterne di trading** (brief CEO `evaluate_trading_skills`), **fix di un bug della dashboard scoperto guardando i numeri di oggi** (la barra del giorno corrente non appariva fino alle 20:00 Roma).

## 1. Cleanup brief + roadmap v1.37 (commit `c3abc32`)

Archiviati 3 brief deployati spostandoli da `config/` a `briefresolved.md/`:
- `brief_52a_fix_phantom_fees` → `session52a_fix_phantom_fees.md`
- `brief_ai_bots_section` → `session53a_ai_bots_section.md`
- `brief_homepage_compaction` → `session53b_homepage_compaction.md`

In `config/` restano: `brief_36h_haiku_sees_tf` (poi archiviato anche lui), `brief_DUST_writeoff_parcheggiato` (parcheggiato fino a go-live), `VISION_brains_architecture_v2` (vision document).

Roadmap aggiornata a **v1.37** con la nuova **Phase 11 ("Numbers Truth & Pre-HN Polish")** che documenta sessioni 50-53: dashboard charts, TF defaults reset, RSI 1h filter, trailing stop 51b, fix phantom fees 52a, FIFO recovery dashboards, FIFO multi-lot fix bot 53a, AI Bots cards, homepage compaction, stats-strip onesto, /admin → /grid rename. **10 nuove voci done** elencate per session.

## 2. Brief 36h già implementato (commit `425abf2`)

Durante il brainstorming è emerso che il brief "Haiku vede il TF nel commentary serale" del 16 aprile era stato già implementato nella session 48 ma non era stato archiviato. Verifica fatta su ultimi 5 row di `daily_commentary`: tutti menzionano TF esplicitamente con context su rotazioni, config changes, performance per bot. Brief spostato in archivio con nome `session48_brief_36h_haiku_sees_tf.md`.

## 3. Roadmap: 3 voci todo erano in realtà done (commit `2fb491b`)

Sweep delle voci `status: "todo"` in tutto `roadmap.html`. Trovati 3 falsi negativi nella Phase 8 backlog ("Phase 2 — Trend Follower brains"):

| Voce | Stato dichiarato | Stato reale | Commit di shipping |
|---|---|---|---|
| 36f "TF riding mode (trailing stop)" | todo | **done** | 51b in session 51 (commit `486fb09`, 2026-04-29) |
| 36h "Haiku sees TF" | todo | **done** | session 48 (2026-04-26) |
| 36i "TF idle re-entry fast for active bots" | todo | **done** | session 33 (RE-ENTRY) + session 45 (RECALIBRATE) |

Tutte e 3 corrette a `done` con commenti aggiornati che puntano alla session di shipping reale.

Voce **`Auto-clean policy for trend_decisions_log (90 days)`** verificata e lasciata `todo`: il bot ha cleanup solo per `trend_scans` (14 giorni), non per `trend_decisions_log`. Coerente con la memoria `project_db_cleanup_pending` che dice "post-HN, estendere TTL pattern a bot_events_log/snapshots/decisions".

## 4. Brief CEO "Evaluate trading skills" — verdetto onesto

Esplorate 3 repo GitHub di Claude Code skills proposti dal brief. **Solo 1 skill installata**, 2 candidate per sessione dedicata, il resto skip. Costi API aggiuntivi: **$0/mese**.

### Installato ora: `data-quality-checker` (tradermonty)

Path: `~/.claude/skills/data-quality-checker/`. Lint pre-publication su markdown (price scale consistency, instrument notation, date/weekday match, allocation totals, unit usage). Zero API esterne. Asset-agnostic. Utile per validare i `report_for_CEO/*.md` e il daily commentary prima di pubblicare.

### Candidati per sessione dedicata (post-HN)

- **`signal-postmortem`** (tradermonty): schema "predicted vs realized" + classificazione TP/FP/missed/regime-mismatch. Logica asset-agnostic ottima; va rimosso il pezzo FMP e collegato a ccxt + Supabase `bot_events_log`. Adattamento ~4-6h. Diventerebbe l'audit automatico delle rotazioni TF e dei sell Grid.
- **Markov regime + Donchian breakout** da `trading-signals-skill` (scientiacapital): cherry-pick utile per Sentinel Phase 3 (regime detection automatica). Non installare il skill intero (60% sono options/Greeks irrilevanti).

### Skip motivati

- **Market Top Detector** + **FTD Detector** + **Downtrend Duration Analyzer** (tradermonty): tutti equity-only, riconosciuti dal repo stesso come "non per crypto". O'Neil distribution days non esiste in mercato 24/7.
- **`finance_skills/wealth-management`** (JoelLewis): premessa del brief sbagliata — non c'è ATR né portfolio heat lì dentro, è risk academic (Kelly, GARCH, drawdown retrospettivo). Skip.

### Nota di memoria

Salvato `project_tradermonty_full_scan.md` per ricordare che **abbiamo valutato solo 5 skill su 15+** del repo tradermonty. Quando torneremo a parlare di trading skills (es. per Sentinel) faremo un full scan per scovare candidati che ci erano sfuggiti.

## 5. Bar chart Daily P&L — fix "buco serale" (commit `9c44ca4`)

Bug scoperto guardando il chart: la barra del giorno corrente **non appariva** fino alle 20:00 Roma, anche se il bot aveva già fatto sell durante la giornata.

### Root cause

Il bar chart Daily P&L usava come asse X le date della tabella `daily_pnl`, che il bot scrive **una sola volta al giorno alle 20:00 Roma**. Risultato: dalle 02:00 Roma di ogni giorno (inizio del nuovo giorno UTC) fino alle 20:00 Roma c'era una finestra di **18 ore** in cui i sell della giornata non avevano una "barra" sul chart, anche se erano correttamente nel DB `trades`.

Il line chart Cumulative ha lo stesso vincolo (lui ha bisogno del `total_value` mark-to-market che è nello snapshot daily_pnl), quindi è rimasto com'è.

### Fix opzione C (la meno invasiva)

Slegato il bar chart da `daily_pnl`: l'asse X è ora l'union delle date in `daily_pnl` ∪ date che hanno sell in `gridDailyRealized` o `tfDailyRealized`. La barra di oggi appare appena il primo sell del giorno UTC viene scritto e cresce in tempo reale ad ogni nuovo sell.

### Footer captions aggiornate

Sotto i due chart ora c'è la nota onesta:
- **Cumulative chart**: "Snapshot 20:00 ora di Roma — il punto di 'oggi' appare quando il bot scrive il daily snapshot serale."
- **Daily bars**: "Live — la barra del giorno corrente cresce in tempo reale ad ogni nuovo sell. Giorno = UTC 00→24."

### Limite del fix

Per valori molto piccoli (la barra di oggi era −$0.24 quando deployato, su una scala −$20/+$20) la barra è visivamente invisibile. Discusso opzioni di scala/zoom/toggle ma deciso di lasciare così — onestà visiva ("poco è successo finora oggi") + tooltip al hover funziona già.

## 6. Workflow visivo via Chrome headless

Durante il pomeriggio sperimentato un workflow nuovo: Chrome headless di sistema (zero plugin Claude Code) per fare screenshot del sito a 3 viewport (desktop 1440px, laptop 1024px, mobile 375px) e verificare il rendering dell'AI direttamente dall'output, non chiedendo all'utente di descrivere cosa vede.

Cartella standardizzata: `/Users/max/Desktop/BagHolderAI/dev-screenshots/` (persistente, fuori repo). Memoria salvata in `reference_screenshots_dir.md`.

Utile per fix futuri: verifica visiva senza ping-pong utente. Limite: gli screenshot a bassa risoluzione non leggono valori piccoli — funziona bene per "ci sono 4 carte allineate" o "la label May 1 c'è" (verifica `--dump-dom` + grep), meno bene per "il bar è verde acceso #22c55e o spento". Per audit pixel-precise serve Playwright vero.

## 7. Stato finale (2026-05-01 12:30 CET)

- **Bot**: pid 80138 attivo da 09:34, fix 53a in produzione, monitoring drift FIFO da fare nei prossimi giorni
- **Sito**: tutte le pagine pubbliche con homepage rinnovata, bar chart live, FIFO recovery client-side, /grid + /tf separati
- **Brief in `config/`**: solo `DUST_writeoff_parcheggiato` (parcheggiato) e `VISION_brains_architecture_v2` (vision)
- **Roadmap**: v1.37, Phase 11 documentata, 13 voci nuove `done`
- **Memoria salvata**: 4 nuovi pointer (53a fix, screenshots dir, data-quality skill, tradermonty full scan)

## 8. Cosa NON è stato fatto (consapevolmente)

- **Fix scala Y bar chart**: discusso 5 opzioni, deciso di non toccare (compromesso storia narrativa vs visibilità barra di oggi). Tooltip al hover sufficiente.
- **Refactoring mobile completo**: identificati 5 problemi reali via screenshot Chrome (overflow text header, banner Volume 1 tagliato, AI Bots cards troppo larghe a 375px) ma rinviato — il CEO ha detto "il refactoring mobile non mi interessa, mi interessa rifare tutto il sito come da roadmap, più bello, ma lo vedremo poi".
- **Backfill realized_pnl storici**: i 458 sell pre-fix 53a restano biased nel DB. Le dashboard correggono client-side. Convergenza naturale, niente UPDATE invasivo.
- **Restart `record_daily` ogni ora** (opzione B della discussione bar chart): non fatto. Rimane il limite del cumulative chart che attende le 20:00 Roma per aggiornarsi. Footer text esplicita.

## 9. Domande aperte per il CEO

1. **A2 — verifica drift FIFO zero**: nei prossimi 5-7 giorni, monitorare se i nuovi sell scritti dal bot post-fix 53a hanno `realized_pnl` esattamente == FIFO ground truth. Se ok → fix verificato.
2. **A3 — OG image refresh**: l'`og-image.png` per HN/Twitter share non mostra le AI Bots cards. Vale 30 min per ricrearla. Pre-HN o pull request post-HN?
3. **D1 — Diary entry sessione 53 (Opus)**: la storia umana del fix FIFO ("CEO che non capisce i numeri, intern che mente sui numeri pur di farli tornare") è materiale narrativo forte. Stoccarla per Volume 2 o pubblicarla come diary entry?
4. **C1 — MiniTF brief**: il "tuner dei parametri anchor" del documento VISION. Scrivere il brief? Implementazione 5-10h dopo HN.
5. **Restart cumulative chart hourly**: fixare la latenza delle 18 ore anche sul cumulative chart richiede modificare il bot per scrivere `daily_pnl` più spesso (o un cron una volta l'ora). Vale lo sforzo o aspettiamo?

## Numeri attuali (2026-05-01 ~12:30 CET)

- Net Worth: ~$630 (allineato col mattino, nessun grosso movimento)
- May 1 sells finora (TF): LUNC −$0.63, DOGE +$0.39 → netto **−$0.24** sul TF
- May 1 sells finora (Grid): 0 (siamo in finestra calma BTC/SOL/BONK)
- Bot attivi: 3 manual (BONK/BTC/SOL) + 3 TF (LUNC/DOGE/POL)

---

**Commit di sessione 53b**: 4 (`c3abc32`, `425abf2`, `2fb491b`, `9c44ca4`).
**Commit totali della giornata 2026-05-01**: 10 (sessione 53 + 53b).
