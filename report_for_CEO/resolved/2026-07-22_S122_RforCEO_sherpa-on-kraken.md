# Report per CEO — sherpa-on-kraken — 2026-07-22 (S122)

**Brief sorgente:** `config/2026-07-22_S122_brief_sherpa-on-kraken.md`
**SCOPE (ereditato identico):** `sherpa-on-kraken`
**Esito:** SHIPPED (codice + test), **no restart** — va live alla finestra 2b coordinata (Max, sul Mini).
**Commit:** `6c2b8bc`
**Test:** **348/348 verdi** (+8 `tests/test_sherpa_on_kraken_s122.py`; aggiornato 1 test S118 che cristallizzava il filtro rimosso).

Anti-assenso: **nessuna obiezione di merito** — il CEO ha già smontato i trade-off nelle sue auto-obiezioni. Raccolgo il suo invito sul seed (§c: non serve codice, vedi sotto).

---

## Cosa ho cambiato

### a) Filtro hands-off rimosso — [bot/sherpa/main.py](../bot/sherpa/main.py) `_fetch_active_manual_bots`
La riga che escludeva `venue='kraken'` è sostituita da `return rows`. Commento riscritto S122: documenta che **entrambe** le ragioni della Fase 1 sono risolte — (a) floor non più azzerato (fee-fix `ed1933d`: `profit_target=0` = break-even), (b) volatilità non più rotta (punto b sotto). `venue` resta nel `select` solo per telemetria.

### b) Mapping simbolo /USD → /USDT (helper condiviso) — sweep completo
- Nuovo `to_binance_symbol()` in [bot/sentinel/inputs/binance_btc.py](../bot/sentinel/inputs/binance_btc.py) — **casa unica** (entrambi i chiamanti già importano da questo modulo).
- **Lo sweep ha trovato esattamente 2 punti** (come previsto dal brief), ora entrambi sull'helper: [volatility.py:51](../bot/sherpa/volatility.py#L51) (`_to_binance_symbol` delega) e [main.py:447](../bot/sherpa/main.py#L447) (`_fetch_symbol_price`). Nessun altro punto costruisce un simbolo Binance da `bot_config.symbol` nel path Sherpa.
- Logica: `if symbol.endswith("/USD"): base+"/USDT"` poi `replace("/","")`. **Solo `/USD` è rimappato** → `/USDT` byte-identico (`BTC/USDT`→`BTCUSDT` come prima). `/USDC` NON tocca (test dedicato).
- **Caveat scritto nel codice come LIMITE NOTO** (non "risolto"): il proxy regge su BTC (vol BTC/USDT ≈ BTC/USD); su SOL e soprattutto **BONK in Fase 3** la divergenza cross-venue può essere maggiore. Ritrovabile lì.

### c) Seed della riga Kraken — **NESSUN CODICE (raccolgo l'offerta del CEO)**
Il seed (buy 1,8 / sell 1,2 / floor 0) vive nella riga `bot_config` che **Max inserisce alla finestra 2b** (§5 OFF-LIMITS: nessun insert riga da parte mia). Sherpa lo riscrive al primo tick. Il fallback cadence esiste già in `settings.KRAKEN_GRID_INSTANCES`. → È un **valore di runbook**, non codice. Confermo la lettura del CEO: come default difensivo non richiede nulla da parte mia. *(Se vuoi che allinei anche il fallback `settings` sell_pct 1,00→1,20, è una riga — ma è fallback-only e Sherpa sovrascrive, quindi l'ho lasciato.)*

---

## §1d — Domanda tecnica (risposta con file:linea, non a memoria)

**L'orchestrator rilegge `is_active` in CONTINUO, ogni 30 secondi.** Il poll loop [orchestrator.py:376](../bot/orchestrator.py#L376) (`while not shutting_down`) rilegge `bot_config` a ogni iterazione [orchestrator.py:382](../bot/orchestrator.py#L382) (`select(...).eq("is_active",True)`), con `POLL_INTERVAL = 30` ([:33](../bot/orchestrator.py#L33)). Spawna qualsiasi riga `is_active=true`, uccide quelle che passano a false.

**Implicazione:** in futuro accendere/spegnere una riga Kraken **non richiederà mai un restart della flotta** — l'orchestrator la prende (o la molla) entro 30s. Il restart della 2b serve **solo** per (1) caricare il codice nuovo e (2) passare `ALLOW_REAL_MONEY=true` all'orchestrator (env di lancio). Dopo, il grid Kraken si gestisce a colpi di `is_active`.

---

## §4 — Misurazione fee-drag (obbligatoria) — SHIPPED

**Cosa esisteva già:** `daily_report` somma le fee del giorno, ma **non** produce i 4 numeri richiesti come readout unico del collaudo (né lordo-vs-netto, né sell_pct medio Sherpa). → Ho scritto uno **script di lettura** (no infra nuova).

`scripts/kraken_fee_drag_report.py` (read-only) produce i 4 numeri: **(1)** trade count, **(2)** fee totale, **(3)** P&L lordo vs netto (la differenza = costo fee), **(4)** sell_pct medio proposto da Sherpa nel periodo. Filtra le righe Kraken sul suffisso `/USD` (la tabella `trades` non ha colonna `venue`).

**Girato sui dati 2a reali** (prova che funziona):
```
1) TRADE: 2  (1 buy · 1 sell)
2) FEE totale: $0.4089
3) P&L: lordo $1.1158 / netto $0.7069 → fee = 36.6% del lordo · fee/turnover 0.80%
4) sell_pct medio Sherpa: nessuna proposta (Sherpa era hands-off — sarà popolato in 2b)
```
Il "36,6% del lordo" è **il fee-drag reso visibile**: su un lotto piccolo la fee si mangia un terzo del guadagno lordo. A fine 2b questo readout dice se il drag è accettabile o se serve l'opzione (B) (minimo sell_pct Kraken-aware).

---

## §3 — Superfici da controllare: **1 finding, flaggato NON fixato** (come da brief)

Ora che Sherpa scrive proposte anche per `BTC/USD`, **due superfici pubbliche** leggono `sherpa_proposals` con `limit=N` **senza filtro symbol/venue**:
- [sherpa-live.ts:63-73](../web_astro/src/scripts/sherpa-live.ts#L63) — lampada STOP BUY, `limit=3` (commento "3 rows = 1 per coin"; ora i coin driven sono 4).
- [dashboard-live.ts:1784-1786](../web_astro/src/scripts/dashboard-live.ts#L1784) — badge regime da `rows[0].proposed_regime`, `limit=30`. *(La lista per-coin sotto è invece SICURA: whitelist esplicita `["BTC/USDT","SOL/USDT","BONK/USDT"]` → BTC/USD non appare.)*
- Minore: la ADJUST count ([sherpa-live.ts:88+](../web_astro/src/scripts/sherpa-live.ts#L88)) conta i write Sherpa `changed_by='sherpa'` senza filtro venue → includerà i write sulla riga Kraken (gonfia un contatore pubblico).

**Perché NON blocca la 2b:** regime e `stop_buy_active` sono **identici su tutti i simboli** nello stesso tick (derivano da F&G/klines globali) → il valore mostrato non cambia. È un leak **semantico** (una superficie binance-pinned che vede una riga in più) + assunzioni `limit` stale, non un errore visibile. **Non l'ho fixato** (fuori scope, non bloccante). **Raccomando follow-up:** aggiungere `&symbol=in.(BTC/USDT,SOL/USDT,BONK/USDT)` (o filtro venue) a quelle 2-3 query. Micro-brief separato.

---

## Test — 348/348

Nuovi (`tests/test_sherpa_on_kraken_s122.py`, 8): **invariante Binance byte-identico** su /USDT (il test che conta, il file gira sui 4 grid vivi) · mapping /USD→/USDT · edge /USDC non toccato · delega volatility · `_fetch_stdev` usa il gemello /USDT e ritorna valore reale (non 0.0) · `_fetch_symbol_price` mappa · **Sherpa ora vede la riga Kraken** (prima no) · empty-safe.

Aggiornato: `test_kraken_fase1_s118.py::test_sherpa_skips_kraken_rows_null_safe` → `test_sherpa_now_drives_kraken_rows` (cristallizzava il filtro rimosso; ora asserisce il comportamento nuovo, con nota S122 e rimando alla suite S122). Nessuna regressione sugli altri 340.

---

## Off-limits rispettati
Nessun flip `is_active`, insert, restart. Nessun valore di trading Kraken oltre al seed-di-runbook. `tf.html:1459` non toccato. Calibrazione TF, floor Binance, formula trigger/floor (`ed1933d`), ancora-buy-dopo-sell: non toccati.

## Roadmap impact
Chiude l'item **S117** "fix sorgente volatilità Sherpa su Kraken". È **plumbing interno** (nessuna Phase pubblica nuova) → **nota, non version bump** su `roadmap.ts` (confermo la previsione del brief).

## Decision log
- **Casa dell'helper = `binance_btc.py`** (non un nuovo util): è il modulo del data-source Binance che entrambi i chiamanti già importano → zero nuove dipendenze cross-modulo. ALTERNATIVA: util condiviso separato (scartata, più superficie). FALLBACK: spostarlo se un terzo chiamante non-binance lo richiedesse.
- **Seed (c) senza codice** (vedi sopra) — raccolta l'offerta esplicita del CEO.

---

*Cita: brief `2026-07-22_S122_brief_sherpa-on-kraken.md`, nota `2026-07-22_sherpa-on-kraken_note_for_ceo.md`, bundle `kraken-2b-bundle` (`ed1933d`), item S117 (chiuso da questo brief). Commit `6c2b8bc`.*
