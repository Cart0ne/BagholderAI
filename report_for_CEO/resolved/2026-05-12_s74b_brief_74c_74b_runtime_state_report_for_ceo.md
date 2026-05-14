# Sessione 74b — Brief 74c + Brief 74b + DEAD_ZONE_HOURS in dashboard

**Data:** 2026-05-12 (sera, ~3h post-S74)
**Intern:** Claude Code
**Modalità:** sessione di prosecuzione su S74 — brief 74c era stato isolato a fine S74 come mainnet-gating, sessione 74b lo chiude end-to-end + accorpa brief 74b e una decisione di esposizione parametro che era rimasta orale dal S73a.

---

## Executive summary

**4 commit pushati** in main (`02b030f`, `f278dea`, `5a29075`, `2f67533`), **bot Mac Mini restartato 2 volte** (post 74c + post 74b runtime_state), **orphan BONK 1.37M recuperato in DB** con script ad-hoc, **2 migration Supabase** (`bot_config.dead_zone_hours` + nuova table `bot_runtime_state`).

Una sessione "che non doveva essere" — il brief 74c era stato isolato a fine S74 con l'idea di aprirlo come prossima sessione; Max ha invece chiesto di proseguire subito visto che era mainnet-gating. Da lì la sessione è cresciuta naturalmente: chiuso 74c, poi il brief 74b sul dashboard, poi la decisione di esporre `DEAD_ZONE_HOURS` come parametro modificabile, poi la decisione architetturale di introdurre `bot_runtime_state` come primitiva canonical per ogni futuro fix "il dashboard non racconta la verità del bot".

**Gate mainnet €100 ora completamente chiuse lato canonical state.** Il bot non perde più partial fills; il dashboard non mente più sulla guardia stop-buy né sul trigger di buy; ogni parametro hardcoded ha il pattern per essere migrato in `bot_config` con tooltip dal sito.

---

## Cosa è stato shipped

| # | Commit | Brief | Descrizione |
|---|---|---|---|
| 1 | `02b030f` | 74c | `_normalize_order_response` spezzato in due branch — `filled<=0` no-op + alert (invariato); `status≠closed` con `filled>0` → log PARTIAL FILL, event `ORDER_PARTIAL_FILL`, procedi normalize. Mainnet-gating chiusa. Test W/X/Y nuovi (25/25 verdi). Script `scripts/insert_orphan_trade_74c.py` (dry-run + --write) recupera l'orphan BONK 21190 leggendo i dati reali via `fetch_my_trades`. |
| 2 | `f278dea` | 74b Bug 1 + admin drift fresh | /grid: badge rosso "Stop-buy active · BLOCKED · drawdown > X%" sopra la cella "Next buy if ↓" quando il bot ha la guardia attiva, con tooltip esplicativo. Logica iniziale: derivata da `bot_events_log` + recompute frontend del drawdown (per filtrare stale post-restart). /admin Drift details: ora mostra solo la run **corrente** per symbol — l'orphan BONK risolto non resta in tabella come se fosse aperto. |
| 3 | `5a29075` | 74d (interno) | Migration `bot_config.dead_zone_hours NUMERIC NOT NULL DEFAULT 4.0` (CHECK 0–168). Bot legge `self.dead_zone_hours` invece di hardcoded. Hot-reload via `_sync_config_to_bot`. /grid Safety section espone il campo con sublabel esplicativo lungo (Max ha esplicitamente chiesto la descrizione: "io non mi ricordo neanche a cosa serve"). Sherpa-ready quando andrà live. |
| 4 | `2f67533` | 74b Bug 2 + Bug 1 refactor | Nuova table `bot_runtime_state` (1 riga per symbol). Bot UPSERT ogni tick dopo `check_price_and_execute`. Espone: `buy_reference_price` (= `_pct_last_buy_price`, fix Bug 2 trigger drift), `last_sell_price` (ladder S70a), `stop_buy_active` (Bug 1 refactor pulito), `phantom_holdings`, `managed_holdings`, `last_recalibrate_at`. /grid ora anchora i suoi widget al bot's source of truth, non più ai trades. |

---

## Orphan BONK 21190 — cleanup eseguito

Pre-fix (bug 74c) Binance aveva eseguito 1,368,998 BONK reali (status='expired' partial fill, $0.00000758, $10.38 USDT) ma il bot aveva scartato la risposta come no-op → drift `DRIFT_BINANCE_ORPHAN` flaggato dal cron reconcile del 16:18 UTC.

Script `insert_orphan_trade_74c.py`:
- Dry-run: stampa i valori che inserirebbe (qty, avg_price, cost, fee_native, fee_usdt, ts)
- `--write`: applica INSERT in `trades` riusando lo stesso percorso di `TradeLogger.log_trade` (così avg_buy_price su DB replay torna corretto)
- Safety: rifiuta INSERT se trova già un trade con `exchange_order_id='21190'`

Eseguito da Mac Mini (testnet credentials). Trade `e6d2b782-2b18-40d5-973b-150482951b78` inserito. Run successiva `reconcile_binance.py --write` su BONK: **24/24 matched, drift 0, orphan 0**. Gate chiusa.

Post-restart bot 19:09 UTC: BONK boot reconcile mostra `replayed=14,813,917.25 vs Binance=14,813,918.05` gap +0.8 BONK ($0.000006), praticamente zero. Pre-72a il drift era ~12 BONK; il recovery del partial fill + S72 fee unification hanno chiuso il gap canonical.

---

## Brief 74b — i due bug del dashboard

**Bug 1 (stop-buy badge invisibile):** widget "Next buy if ↓" mostrava colore verde mentre il bot non comprava da 4h per via della guardia drawdown > 2%. Frustrazione concreta del Board nello scoprire questo durante l'audit S74 ("se siamo sotto il trigger, perché non compriamo?").

**Bug 2 (trigger drift widget vs bot):** widget calcolava il trigger dal prezzo dell'ultimo buy nei trades (`a.lastBuyPrice × (1 − buy_pct/100)`); il bot internamente usava `_pct_last_buy_price`, che diverge dai trades dopo IDLE_RECALIBRATE (S69) o DEAD_ZONE_RECALIBRATE (S73). Misurato ~1.5% su BONK durante l'audit. Differenza invisibile all'utente: dashboard dice "compro a $X", bot compra a $Y.

**Strada scelta (B):** invece di Strada A (events-based + recompute frontend, che funziona per Bug 1 ma non risolve Bug 2), **introduciamo una primitiva canonical**: la table `bot_runtime_state`. Una riga per symbol, UPSERTed dal bot ad ogni tick. Espone i campi in-memory che il dashboard pubblico vuole leggere. Niente più derivazioni fragili, niente più euristiche.

Schema:
```sql
symbol PK, buy_reference_price, last_sell_price, stop_buy_active,
phantom_holdings, managed_holdings, last_recalibrate_at, updated_at
```

RLS service-role write + anon SELECT. Seed rows inseriti per BTC/SOL/BONK così il dashboard ha dati anche prima del primo tick post-deploy.

**Effetto immediato post-deploy** (verificato live):
- BONK card → badge rosso "Stop-buy active" (latch effettivamente vivo dal bot)
- BTC/SOL card → trigger normale (latch False, niente falsi positivi)
- BTC `nextBuyTrigger` ora calcolato su `$80,477.73` (bot reference post-boot) invece di `$80,296` (trades) → Δ ~$180 corretti

**Bug 1 refactorato** sulla stessa primitiva: tolto il pattern events-based + recompute, sostituito da una singola lettura `rtState.stop_buy_active`. Codice frontend più semplice e correttezza migliore (no edge case post-restart).

---

## DEAD_ZONE_HOURS per-coin (Brief 74d interno)

Da S73a la guardia "dopo 4h di inattività in dead zone, resetta il ladder" era hardcoded a 4.0 in `grid_bot.py:615`. Promemoria: il bot Grid, dopo una sell-run, lascia il prezzo di sell ancorato a `_last_sell_price` (ladder S70a). Se il rally stalla, tre guardie additive S69 freezano il bot per ore. S73a sblocca via reset dopo N ore.

Migration: `ALTER TABLE bot_config ADD COLUMN dead_zone_hours NUMERIC NOT NULL DEFAULT 4.0` con CHECK (0, 168]. Tutti e 3 i symbol partono a 4.0 → comportamento identico al pre-fix.

Wiring: `SupabaseConfigReader._CONFIG_FIELDS` lo seleziona, `grid_runner` lo passa al costruttore + hot-reload, `grid_bot` legge `self.dead_zone_hours` ad ogni check. Niente restart necessario per modifiche.

UI `/grid`: campo nuovo nella sezione "⚠️ Safety" sotto "Stop-buy drawdown %", con sublabel lunga che spiega cosa fa il meccanismo. Max ha esplicitamente chiesto questa descrizione perché "io non mi ricordo neanche a cosa serve". La sublabel è in stile self-explanatory:
> *"After a partial sell run, residual holdings stay anchored to the last-sell price ladder. If the rally stalls and price stays above avg cost without any trade for this many hours, the bot resets the ladder so a new sell trigger can fire. Prevents the bot from sitting frozen. Default 4h; higher for thin books (BONK), lower for liquid pairs (BTC)."*

Sherpa quando andrà live troverà una colonna già pronta in `bot_config` da scriverci sopra (pattern identico a `buy_pct`, `sell_pct`, ecc.).

---

## Decisioni della sessione (DECISION LOG)

**DECISIONE:** brief 74c partial fill prima di tutto (mainnet-gating)
**RAZIONALE:** Max ha indicato 74c come priorità immediata appena aperto S74b. Il bug perdeva trade reali su book sottile testnet, e su mainnet pulito avrebbe causato divergenza DB↔broker → bot vende a un avg_buy stale → perdita reale.
**ALTERNATIVE:** affrontare brief 74b prima (UX, già aperto) — scartato perché 74b non è mainnet-gating.
**FALLBACK:** revert commit `02b030f` se il fix introduce regressioni inattese (rischio basso, callsite isolati a 3 wrapper interni, contratto esterno invariato).

**DECISIONE:** cleanup orphan via script ad-hoc, non SQL diretto
**RAZIONALE:** post-72a il bot ricostruisce `avg_buy_price` da DB replay. Un INSERT con valori approssimati (sapendo solo qty/price del brief) avrebbe biased l'avg. Lo script fa `fetch_my_trades` per leggere il vero `avg_price`/`fee_native`/`fee_currency` dall'ordine 21190 e riusa la stessa logica di USDT-conversion di `_normalize_order_response`.
**ALTERNATIVE:** SQL INSERT manuale stimato (rifiutato per la ragione sopra); pulizia via SQL ma con valori reali fetchati a mano (più fragile).
**FALLBACK:** UPDATE/DELETE sulla riga `e6d2b782` se i numeri non coincidessero alla prossima reconcile (non è successo).

**DECISIONE:** introdurre `bot_runtime_state` (Strada B) invece di derivare dal `bot_events_log` (Strada A)
**RAZIONALE:** Strada A (events log + recompute frontend) risolve Bug 1 ma non Bug 2 (trigger drift). E ha un caso edge fragile post-restart. Strada B introduce una primitiva canonical riusabile per ogni futuro "il dashboard vuole leggere lo stato del bot". Costo: 1 migration + 1 UPSERT in main loop. Beneficio: pattern stabile per i prossimi brief simili.
**ALTERNATIVE:** Strada A più rapida — rifiutata perché lascia Bug 2 aperto.
**FALLBACK:** se il write load è troppo (improbabile: 3 symbol × tick ogni 5-30s = trascurabile), si può rallentare a "scrivi solo se cambia" tramite stato in memoria del runner.

**DECISIONE:** DEAD_ZONE_HOURS per-coin in `bot_config`, non globale in nuova `system_config`
**RAZIONALE:** stesso pattern di `buy_pct`, `sell_pct`, `stop_buy_drawdown_pct`. Sherpa già scrive per-coin in `bot_config`. Zero schema nuovo. Differenziabile per coin senza migration aggiuntiva (BONK book sottile può volere 8h, BTC liquido 2h).
**ALTERNATIVE:** globale in `system_config` (rifiutata per: schema nuovo + migrazione futura se differenziabile per coin).
**FALLBACK:** nessuno, la migration è additiva e default = comportamento attuale.

**DECISIONE:** vincolo brief 74b "NON toccare grid_bot.py" sbloccato per Bug 2
**RAZIONALE:** richiesta esplicita Max. Bug 2 senza modificare il bot richiederebbe duplicare la logica di reference in frontend → viola memoria `feedback_one_source_of_truth`. Una write addizionale dal bot non cambia comportamento di trading.
**ALTERNATIVE:** scrivere `_pct_last_buy_price` come effetto collaterale (es. dentro buy_pipeline al posto di in un helper dedicato) — rifiutata per chiarezza.

---

## Pulizia di chiusura sessione

- 3 brief archiviati: `session65b_mascots.md`, `session72_fee_unification.md`, `session74b_grid_dashboard_stop_buy_visibility.md` → `briefresolved.md/`
- 4 vecchi CEO report archiviati in `report_for_CEO/resolved/` (S71, S72 × 2, S73c); restano solo gli S74 nella radice
- Roadmap aggiornata: aggiunte voci S71/S72/S73/S73b/S73c/S74/S74b in Phase 13. Aggiornato Step C cron Mac Mini da `todo` a `done` in Phase 9 §6
- Apple Notes "BagHolderAI — Todo" letta (sola lettura). Riepilogo a Max via chat dei 4 item TODO già shipped da spostare in DONE + 4 nuovi item S74b da aggiungere

---

## Stato live post-sessione

**Bot Mac Mini** PID 40642 (orchestrator), 5 figli (caffeinate + 3 grid + sentinel + sherpa). Restart 19:44 UTC.

**Boot reconcile:**
- BONK: replayed 14,813,917.25 vs Binance 14,813,918.05 → gap +0.8 BONK ($0.000006, |0.0000%|)
- SOL: gap +4.999 SOL (phantom testnet noto, WARN come da asymmetric reconcile S72)
- BTC: gap +1.000 BTC (idem)
Zero ORDER_REJECTED.

**`bot_runtime_state` popolata** (verificato 17:44 UTC):
- BONK: `buy_reference_price=$0.00000758`, `stop_buy_active=true`, `phantom_holdings=0.80`, `managed_holdings=14,813,917.25`
- BTC: `buy_reference_price=$80,477.73`, `stop_buy_active=false`, `phantom_holdings=1.0000`, `managed_holdings=0.001229`
- SOL: `buy_reference_price=$93.65`, `last_sell_price=$97.64`, `stop_buy_active=false`, `phantom_holdings=5.0`, `managed_holdings=1.59`

**Vercel deploys** (auto da push GitHub):
- `dpl_BsjtJUe7KpVNDwR2X6gXVyZLV1cF` (02b030f) → READY (74c)
- `dpl_DadVnUFKyDgAM7KB1GqGcP8Gbc7A` (f278dea) → READY (74b Bug 1 + drift fresh)
- Successivi (5a29075, 2f67533) → in coda, READY entro 1-2 min

---

## Cosa NON è stato fatto (e perché)

| Cosa | Perché no |
|---|---|
| **Brief 74b Bug 2 strada A (bot_state_snapshots o derive)** | Decisa strada B (canonical mirror). Strada A sarebbe stata più rapida ma con tech-debt — la primitiva nuova paga dividendi |
| **Stop-buy time-limit (24h then buy anyway)** | Decisione strategica Max in attesa: lui stesso ha detto "devo ancora discutere se è una buona idea o no". Parcheggiato in PROJECT_STATE §6 |
| **Bot-side fix per `stop_buy_active` post-restart latch** | Reso superfluo da Strada B (bot_runtime_state). Il bot al primo tick post-restart riapplica il check e scrive `True` o `False` in DB → niente più stale events |
| **Aggiornare validation_and_control_system.md** | Richiede sessione dedicata. Apple Notes todo lo cita esplicitamente. Da fare prima del go-live €100 |
| **BUSINESS_STATE.md** | Owner = CEO (Claude su claude.ai). In attesa update post-S74b da parte tua |
| **Update HOW WE WORK pubblico** | Brief 74a Task 1 deferred da S74 ("sito pubblico" session separata) |

---

## Vincoli e impegni residui pre-go-live €100

Pre-live gates (aggiornamento post-S74b):
- ✅ Contabilità avg-cost + fee unification + holdings golden source (S66/S67/S72)
- ✅ Wallet reconciliation Binance Step A+B+C cron (S70-S72)
- ✅ FIFO contabile via dashboard (S69)
- ✅ sell_pct net-of-fees (S70a)
- ✅ Sentinel ricalibrazione (S70b)
- ✅ Sito online disclaimer testnet (S70c)
- ✅ P&L hero unificato (S71)
- ✅ Fee Unification + frontend canonical refactor + TF removal (S72)
- ✅ Dead Zone recalibrate (S73a) + dust trap (S73b) + BONK lot_size + BTC phantom (S73c)
- ✅ TCC python3.13 FDA + cron reconcile produzione (S74)
- ✅ **Partial fills recovery (S74b brief 74c) — mainnet-gating chiusa**
- ✅ **Stop-buy badge + trigger drift fix (S74b brief 74b) — dashboard ↔ bot coherence**
- ✅ **DEAD_ZONE_HOURS per-coin parametrico (S74b brief 74d) — Sherpa-ready**
- ⬜ Mobile smoke test reale (su device fisico)
- ⬜ Sentinel/Sherpa analisi 7gg DRY_RUN (deferred)
- ⬜ Board approval finale

**Target go-live**: 18–21 maggio invariato. Le gate canonical state sono ora tutte chiuse — restano solo verifiche operative + decisione Board.

---

## Audit dovuti (check da CLAUDE.md §1)

Area 1 (tecnica, 30gg): ultimo audit 2026-05-09. Prossimo dovuto **2026-06-08**. Non dovuto stasera.
Area 2 (coerenza progetto, 90gg): ultimo audit 2026-04-22. Prossimo dovuto **2026-07-22**. Non dovuto.
Area 3 (strategy & marketing, 90gg): ultimo audit 2026-04-19. Prossimo dovuto **2026-07-19**. Non dovuto.

---

## Per il CEO — cosa decidere/aggiornare adesso

1. **BUSINESS_STATE.md refresh** post-S74b: 4 nuovi shipped (brief 74c, 74b Bug 1+2, DEAD_ZONE_HOURS in dashboard) + chiusura gate canonical state pre-go-live.
2. **Eventuale conferma** che bot_runtime_state come pattern canonical va bene per i futuri brief simili (es. Bug 2 sui Telegram messages potrebbe usarlo anche).
3. **Stop-buy time-limit (parcheggio §6)** quando vuoi riaprirlo: è una decisione di trading, non infrastrutturale. Va con un brief dedicato.
