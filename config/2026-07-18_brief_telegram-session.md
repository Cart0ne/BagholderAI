# Brief — Sessione Telegram (consolidato)

**Data:** 2026-07-18 · **Autore:** Claude Code (Intern) · **Per:** la prossima sessione dedicata **solo** a Telegram (Max apre quando vuole).
**Natura:** documento-indice che mette in UN posto tutto ciò che serve per lavorare sul canale Telegram — finora sparso tra MTL (T.1/T.2/T.3), la proposta contenuti S116, e il codice. **Non è un piano di implementazione**: i tre item hanno maturità diversa (T.1 aspetta decisioni strategiche; T.2/T.3 sono fix con brief tecnico da scrivere). Materiale raccolto e **verificato nel codice** (workflow `wf_61d6bbad-26d`).

---

## 0. Come usare questo brief

Tre cose vivono sotto "Telegram", di natura diversa:
- **T.1 — Contenuti del canale** (strategico, owner CEO/marketing): richiede che Max/CEO **chiudano 4 decisioni** prima di qualsiasi codice. → §2.1
- **T.2 — Bug daily report: unrealized non mostrato** (tecnico, CC): il report sembra sempre positivo perché conta solo i realized delle vendite. → §2.2
- **T.3 — Bug daily report: fantasma $25 Kraken** (tecnico, CC, **lato bot → restart**): stessa fix del parked `daily_pnl` Fase 2b (una riga sana entrambi). → §2.3

**Ordine consigliato**: prima chiudere le 4 decisioni di T.1 (sblocca tutto il filone contenuti); T.2 e T.3 sono indipendenti e si possono fare al primo restart utile (idealmente **insieme, alla Fase 2b**, essendo entrambi lato bot). Dettaglio dipendenze in §6.

---

## 1. Infrastruttura (com'è fatto oggi)

**Due bot, due destinazioni** (chiavi in `config/.env`, mai hardcoded; classe `TelegramConfig` in `config/settings.py:78-84`):

| Ruolo | Bot | Destinazione | Var .env |
|---|---|---|---|
| **Privato** (alert operativi + `/approve` X) | bot privato | **DM 1:1 di Max** | `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` (`.env:15-16`) |
| **Pubblico** (daily report + CEO's Log) | `@BagHolderAI_rep_bot` | **canale "BagHolderAI Daily Report"** | `TELEGRAM_PUBLIC_BOT_TOKEN` / `TELEGRAM_PUBLIC_CHAT_ID` (`.env:19-20`) |

- Il canale report è **PRIVATO-ma-condiviso** (invite `t.me/+di3JKEUHYvQ5NDM0`, id **`-1003755518217`**). Il bot posta per **ID numerico**, non per username. **Perché**: `@bagholderai_report` è stato **squattato** quando il canale era pubblico e vuoto (memoria `reference_telegram_channel_squat`). **Regola**: username pubblico solo con canale attivo+iscritti, altrimenti resta privato. Questo è **il "perché" di T.1** (contenuti = tenere il canale vivo = anti-squat).
- **Vincolo di design** (memoria `feedback_no_telegram_alerts`): monitoring/health vanno su **/admin**, NON in nuove notifiche Telegram (Max si è rotto degli avvisi). Paletto per T.2 (fix di un report esistente, non un nuovo alert) e per l'idea "ticker trade" (rischio spam).
- Oggi il canale pubblica **solo**: daily report (≥20:00) + CEO's Log serale (Haiku).

**Listener `/approve`** (`x_poster_approve.py`): long-polling sul bot privato, comandi `/approve` `/discard` `/rewrite` `/xstatus` gated `is_max()`. Bozze in Supabase (`pending_x_posts`). Lanciato da **LaunchAgent `com.bagholderai.xposter-approve`** (always-on, KeepAlive). Lezione "morto 1 mese": era lanciato a mano con `nohup` senza supervisor → dopo un reboot non tornava su e le bozze morivano non consumate. **Vincolo**: un solo consumer `getUpdates` per token (mai agent + nohup insieme → 409).

**Schedule** (nessuno di questi è il daily report):
| Job | Meccanismo | Orario |
|---|---|---|
| Daily report (priv+pub+CEO's Log) | **in-process nel grid loop** (NON cron) | ≥20:00 Rome, 1×/giorno |
| Generatore bozza X `x_poster.py --cron` | crontab | 20:30 Rome |
| Listener `/approve` | LaunchAgent | continuo |
| Reconcile Binance | crontab | 03:00 Rome |
| DB maintenance | in-process orchestrator | 04:00 UTC |

---

## 2. Le tre cose da fare

### 2.1 — T.1 · Contenuti del canale (strategico — 4 decisioni da chiudere)

Fonte: `config/2026-07-07_telegram-content-proposal.md` (proposta S116). **4 idee di Max**, con feasibility già valutata:

| # | Idea | Esiste già? | Sforzo | Nota |
|---|---|---|---|---|
| 1 | **Digest 5 top-news/giorno** (Haiku, con link) | NewsKeeper classifica per-articolo su `newskeeper_signals`, ma **nessun ranking "top N" e NewsKeeper non parla mai con Telegram** | MEDIO | v2 ha il dedup (`event_key`) ma è **shadow** |
| 2 | **Ticker buy/sell minimale** ("BUY 1 lot BTC") | esiste `send_trade_alert()` ma è l'opposto di minimale (mini-report per fill) | MEDIO | **rischio spam**: decine di trade/giorno; precedente S21 (spam BUY SKIPPED → guard) |
| 3 | **Alert cambio regime** (Sentinel + NewsKeeper) | **v2 flip-detection GIÀ logga** `BAROMETER FLIP` (`bot/newskeeper_v2/main.py:111-131`) → aggiungere la call è **~one-liner (BASSO)**; **Sentinel NON confronta prev-vs-current** → da costruire (MEDIO, pattern in `bot/sherpa/main.py:475-508`) | BASSO/MEDIO | v2 shadow |
| 4 | **Post auto su nuova sessione diary** | il CEO scrive `diary_entries` via MCP, **fuori dal codice repo**; **nessuna infra observe-Supabase-table** esiste | **ALTO** | serve infra nuova (cron polling o Supabase webhook) |

**Ranking sforzo** (dal più facile): v2 regime-flip → (Sentinel detection + ticker + digest) → diary (nuova infra).

**⚠️ LE 4 DECISIONI APERTE** (da chiudere PRIMA di ogni codice — `PROJECT_STATE §6` + proposta §6):
1. Digest news da NewsKeeper **v1 (maturo)** o **v2 (shadow, con dedup)**?
2. Ticker trade su canale **pubblico o privato**? **Serve throttle?** (CC propende pubblico + throttle obbligatorio)
3. Ok pubblicare il segnale **v2 shadow**, o **solo Sentinel** per ora?
4. Trigger diary: **cron Python** o **webhook Supabase**? E: **riassunto completo** o **ping "nuova sessione" + link** al sito?

**🚩 DRIFT da risolvere all'apertura**: la proposta tratta **NewsKeeper v1 come vivo/maturo**, ma `PROJECT_STATE §1/§3` dice **v1 RITIRATO S110e (spento + righe cancellate)**. Se v1 è davvero morto, le Decisioni **1 e 3 vanno riformulate** (non "v1 vs v2" ma "usiamo v2-shadow o aspettiamo che v2 esca da shadow"). **Verificare v1 prima di decidere.**

### 2.2 — T.2 · [BUG] Daily report: unrealized non mostrato

**Sintomo**: la riga "Today · Realized 🟢 $+X" somma **solo i `realized_pnl` delle vendite di oggi**, ignora la variazione **unrealized** delle posizioni aperte → quadro **falsamente positivo** (es. 01/07: Today +$1.05 mentre BTC −2.1%, BONK −7.3%, ETH −8.9%; in una giornata di soli BUY con prezzo che sale, la riga resta $0.00 anche se l'equity è cambiata).

**Codice**:
- Calcolo (solo-realized): `bot/grid_runner/daily_report.py:63-66` (`day_realized`) + path manuale `scripts/send_daily_reports_now.py:48` + quota TF `commentary.py:445`.
- Render riga "Today ... Realized": `utils/telegram_notifier.py:290` (`tr_grid`), `:295-296` (`tr_combined`), `:301-305` (privato); `:463/467/478` (pubblico).

**Fix (direzione)**: aggiungere il **P&L mark-to-market del giorno** = `Δ = total_value_oggi − total_value(snapshot daily_pnl di ieri)`. L'infra c'è già: `daily_pnl.total_value` è scritta (`db/client.py:269`) e c'è un helper che legge la riga di ieri (`get_yesterday_pnl_pct`, `commentary.py:101-133`). Affiancare una riga "Today (equity): Δ$…" o sostituire `tr_combined` con `realized + Δunrealized`. **Onestà / one-source-of-truth.** → brief tecnico da scrivere.

### 2.3 — T.3 · [BUG] Daily report: fantasma $25 Kraken (lato bot)

**Causa (verificata)**: `commentary.py:503-514` `get_grid_state` somma `capital_allocation` di **tutte** le righe `managed_by=grid` **senza filtro venue/is_active** (il commento in-code dice pure *"Inactive coins still contribute their slice"*) → con la riga collaudo Kraken `BTC/USD` ($25, `venue=kraken`, `is_active=false`, `cycle=kraken_test`) → **`grid_budget = 525`** invece di 500. I trade sono filtrati per cycle (Kraken escluso).

**Cosa sbaglia esattamente** (importante, corregge una mia imprecisione): i $25 gonfiano **`initial_capital` ("Started with $525"), `total_value` (valore portafoglio), `cash`, e il denominatore della % di P&L** (525 invece di 500). Il **P&L in $ resta CORRETTO** perché `total_pnl = total_value − grid_budget` (`commentary.py:619`) → il +25 si cancella da entrambi i lati. Stesso identico comportamento del sito (dov'era il *net worth* a essere gonfiato di $25, non il P&L in $).

**Superfici colpite** (get_grid_state è CONDIVISO):
1. **Report Telegram** (via `_build_portfolio_summary → get_grid_state`, `bot/grid_runner/lifecycle.py:122`) → questo T.3.
2. **Snapshot `daily_pnl`** (via `daily_report.py:147-159`) → grafico §3 dashboard pubblica → **parked `PARKED_daily_pnl_canonical_fase2b.md`**.

**Fix = 1 riga**: aggiungere `.eq("venue","binance")` alla query `bot_config` (`commentary.py:506`) — **stesso identico fix già fatto sul sito** (`GRID_BUDGET` venue-filtered, commit `f6388b6`, S119b). Il cycle è **già a posto** (`get_current_cycle` globale pinnato `venue=binance`, `db/client.py:45`, S119). **Una riga sana ENTRAMBE le superfici** (Telegram + daily_pnl).

**È lato bot → serve restart.** Decisione Max 2026-07-18: non si tocca il bot testnet ora → **farlo al restart della Fase 2b** insieme al parked (stessa riga; il ciclo nuovo azzera pure la deriva dust-reset storica ~$8, niente backfill). Se il report letto ogni giorno dà troppo fastidio prima, è comunque "1 riga + restart".

---

## 3. Drift / stale da sistemare (emersi dalla ricognizione)

- **`config/.env:20` locale**: `TELEGRAM_PUBLIC_CHAT_ID=@BagHolderAI_report` (username morto/squattato). La fonte di verità (Mac Mini + memoria `reference_telegram_channel_squat`) è l'**ID numerico `-1003755518217`**. La `.env` locale è probabilmente stale vs quella del Mini. **Verificare/allineare prima di un restart** (o il report pubblico fallirebbe di nuovo).
- **`BUSINESS_STATE.md §1`**: cita ancora "@BagHolderAI_report (canale pubblico)" → terminologia superata (è privato). Aggiornare **richiede ok Max/CEO** (territorio BUSINESS_STATE).
- **Riferimenti a NewsKeeper v1** nella proposta contenuti (vedi drift §2.1).

---

## 4. Mappa codice del daily report (per orientarsi)

**Path LIVE** (in-process, NON cron): grid main loop `bot/grid_runner/__init__.py:840` → `maybe_send_daily_report` (`daily_report.py:20`, gate `now.hour >= REPORT_HOUR=20`, flag anti-doppio-invio settato prima dell'invio) → `build_portfolio_summary` → **`_build_portfolio_summary` (`lifecycle.py:108-128`) → `commentary.get_grid_state`**. Coordinamento multi-bot: INSERT atomico `daily_pnl` `ON CONFLICT DO NOTHING` (`db/client.py:285-290`) → solo il **primo** dei 4 grid bot invia.

**Renderer** (assemblano il testo dal dict `report_data`): `utils/telegram_notifier.py` — privato `:242-423`, pubblico `:425-556`, CEO's Log `:558-593`. (C'è un `send_daily_report` legacy `:116-204` **non usato** dal path 20:00.)

**Numeri**: tutti da `commentary.get_grid_state` (`:470-636`) + `get_tf_state` (`:249-467`), stesso replay avg-cost `_analyze_coin_avg_cost` (`:187-246`), identità `total_value = budget + realized + unrealized`.

**Trigger manuale** (per ri-firare dopo un cambio formato, senza aspettare le 20:00 e **saltando** lo snapshot `daily_pnl`): `scripts/send_daily_reports_now.py`. Anch'esso passa da `get_grid_state` → **qualunque fix a get_grid_state vale per entrambi i path**.

---

## 5. Riferimenti

**Doc**:
- `config/2026-07-07_telegram-content-proposal.md` — proposta contenuti S116 (T.1) + 4 decisioni aperte.
- `config/parked/PARKED_daily_pnl_canonical_fase2b.md` — fix condivisa T.3 + daily_pnl (§3 punto A), trigger Fase 2b.
- `config/parked/PARKED_realized_pnl_avg_cost_fixB.md` — famiglia dust-reset, superficie `trades.realized_pnl`, trigger pre-mainnet.
- `config/MASTER_TASK_LIST_2026-07-18.md` (§ CANALE TELEGRAM + BUG APERTI) — T.1/T.2/T.3 (aggiornati a S120: T.1 SHIPPED+LIVE, T.2/T.3 coded-pending-restart).
- `PROJECT_STATE.md §5/§6` (residuo $25 + 4 decisioni contenuti).

**Memorie**: `reference_telegram_channel_squat` (canale privato, ID, anti-squat), `feedback_no_telegram_alerts` (no nuovi alert, monitoring→/admin), `reference_newskeeper_standalone_launch` (v1 ritirato, come lanciare v2), `project_realized_pnl_dust_drift` (famiglia $25/dust-drift, gemello Python `get_grid_state`).

**Brief Telegram già chiusi** (`briefresolved.md/`, tutti aprile 2026, **altri temi** — NON coprono T.1/T.2/T.3): `session15_reporthour`, `session16a_TelegramVerify`, `session21_telegramspam`, `session22c/d_bugfixtelegram`.

**Codice chiave**: `commentary.py:470-636` (get_grid_state, fix T.3 a :506) · `utils/telegram_notifier.py:242-593` (renderer, riga Today :296/301-305 per T.2) · `bot/grid_runner/daily_report.py:20-177` (path live) · `bot/grid_runner/lifecycle.py:122` (catena condivisa) · `scripts/send_daily_reports_now.py:48` (trigger manuale) · `db/client.py:45` (cycle già pinnato) · `x_poster_approve.py` + `config/launchd/com.bagholderai.xposter-approve.plist` (listener).

---

## 6. Sequenza suggerita / dipendenze

1. **All'apertura**: risolvere il drift v1 (verificare se NewsKeeper v1 è davvero spento) → riformulare Decisioni 1/3 se serve.
2. **T.1**: Max/CEO chiudono le 4 decisioni → poi 1 brief tecnico per idea (partendo dal più facile: v2 regime-flip → Telegram).
3. **T.2 + T.3**: indipendenti dal contenuto. Entrambi lato bot → **conviene farli insieme al primo restart** (idealmente Fase 2b). T.3 è 1 riga; T.2 è un fix medio (MTM del giorno).
4. **Prima di qualsiasi restart**: allineare `config/.env` TELEGRAM_PUBLIC_CHAT_ID all'ID numerico (§3), o il report pubblico si rompe.
