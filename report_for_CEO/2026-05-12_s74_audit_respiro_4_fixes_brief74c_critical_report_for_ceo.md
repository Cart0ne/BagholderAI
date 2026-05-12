# Sessione 74 — Audit "respiro" + 4 fix + 1 bug critico isolato

**Data:** 2026-05-12 (pomeriggio-sera, ~5h)
**Intern:** Claude Code (sessione condotta via walkthrough Max)
**Modalità:** audit guidato item-by-item — Max chiede, CC spiega 1 cosa alla volta, Max decide, CC applica in batch alla fine.

---

## Executive summary

Sessione di "respiro" (no nuova logica di trading) come da brief 74a. **6 commit pushati** in main, **bot Mac Mini restartato** con i fix Telegram live, **TCC cron Mac Mini risolto** (test 18:18 verde, stanotte 03:00 girerà pulito). **2 nuovi brief aperti** durante l'audit, uno dei quali **mainnet-gating** (brief 74c, partial fills lost). HWW v3 (brief 74a Task 1) **non eseguito** — Max ha redirezzato la sessione a privato-only, HWW deferred a sessione separata "sito pubblico".

---

## Cosa è stato shipped

| # | Commit | Brief | Descrizione |
|---|---|---|---|
| 1 | `3f3e349` | 74a Task 4 (invertito) | Grid public IT→EN — 10 stringhe tradotte (project budget, current state, live price, ecc). Scope cresciuto da 3 a 10 in audit |
| 2 | `d289a8a` | 74a Task 2 | Telegram: rimossa "Buying at market..." dalla IDLE RE-ENTRY alert. Il messaggio implicava un buy che poteva poi essere skippato (lot_size, dust, guard) |
| 3 | `93dc00d` | 74a Task 4 (re-scope) | Telegram privato unificato a inglese (9 stringhe IT residue: Servono, Motivo, Capitale esaurito/ripristinato, Loop ripristinato, Errori consecutivi, Cash disponibile, Posizioni). Decisione Max: tutto EN era più veloce di tradurre tutto IT |
| 4 | `a4674e6` | (post-audit S74) | Admin dashboard polish — 6 item batch: Opp da linea tratteggiata spessa a thin offset ±2px sul Sentinel chart; range selector globale (12h/24h/7g/1m) sincronizzato sui 5 chart; overlay BTC top-center; linea Opportunity aggiunta al reaction chart Sherpa; titoli/legenda/footnote allineati; footnote drift "pending S71+" corretto |
| 5 | `3535184` | (cleanup post-S74) | Drop hardcoded "24h" da chart titles (selettore globale ora dinamico) |
| 6 | `165b08e` | docs | briefs 74a/b/c + memo + drafts + PROJECT_STATE refresh |

**Bot Mac Mini restart 18:32 UTC** dopo i commit Telegram. 5 processi vivi (orchestrator + caffeinate + 3 grid runner). Task 16+17 ora attivi al prossimo evento idle_recalibrate / skipped_buy.

---

## TCC cron Mac Mini — fix shipped manualmente

**Diagnosi:** il cron reconcile 03:00 fallisce stamattina con `PermissionError [Errno 1]: '/Volumes/Archivio/bagholderai/venv/pyvenv.cfg'`. Inizialmente sembrava TCC su `/usr/sbin/cron`, ma quel toggle era già ON da mesi. **Root cause vera:** TCC su Apple Silicon tratta i child binari come "responsible processes" separati. Cron aveva FDA, ma quando spawnava `python3.13` (Homebrew, /opt/homebrew/bin/python3.13), il child non ereditava → bloccato sul read di pyvenv.cfg.

**Fix Max:** abilitato toggle `python3.13` in System Settings → Privacy & Security → Full Disk Access.

**Test:** crontab temporaneamente modificato a `18 18 * * *`, rimasto in piedi 3 min, test cron 18:18:01 UTC ha eseguito reconcile pulito (exit=1 dovuto a drift detection, non Python error). Crontab ripristinato a `0 3 * * *` originale.

**Effetto laterale del test:** il reconcile ha trovato un **drift nuovo** che è diventato il brief 74c (sotto).

---

## Brief aperti per le prossime sessioni

### 🔴 Brief 74c — Partial fills lost (mainnet-gating)

**Smoking gun isolato durante il test cron:** ordine BONK 21190 a 2026-05-12T10:30:11Z, 1,368,998 BONK (~$10), arriva da Binance con `status='expired', filled=1368998.0` (partial fill su book sottile). Il bot lo logga come "Treating as no-op" e **non scrive in DB**. Risultato: Binance ha le coin, DB no, reconciliation flagga `DRIFT_BINANCE_ORPHAN`.

**File:linea bug:** [`bot/exchange_orders.py:191`](bot/exchange_orders.py#L191). Condizione `status != "closed" OR filled <= 0` è troppo aggressiva.

**Fix concettuale (~3 righe):** se `filled <= 0` → no-op (corretto). Se `filled > 0` ma `status != "closed"` → partial fill REALE, va loggato come trade.

**Impatto mainnet:** raro ma critico. In flash crash o liquidation cascade, partial fill è possibile anche su BTC. Se non logato, holdings DB diverge da Binance reale → P&L sbagliato, avg sbagliato, decisioni sell-side compromesse. **❌ NON ship mainnet senza questo fix.** Decisione Max: nuova sessione dedicata.

### 🟡 Brief 74b — Grid dashboard cieco su stop-buy guard

Durante audit, Max ha notato che il widget "Next buy if ↓" su `/grid` mostra il trigger in verde (= "sta per comprare") mentre il bot internamente ha attivato `stop-buy active (drawdown > 2.0% of allocation)` e tutti i buy sono bloccati. Dashboard non mostra lo stato della guardia. Frustrazione utente: "perché non compriamo?".

**Bug secondario:** trigger price mostrato dal widget disallineato da quello reale del bot (~1.5% di scarto). Widget legge `lastBuyPrice` dai trades, bot usa reference post-IDLE_RECALIBRATE.

**Fix proposto:** badge "STOP-BUY ACTIVE" sul card BONK + esporre reference reale dal bot state.

**Domanda strategica embedded:** ha senso bloccare i buy a tempo indefinito? Max propone time-limit (es. dopo 24h di stallo, il bot compra comunque per abbassare avg cost). Decisione di trading logic, brief separato.

---

## Decisioni strategiche aperte (parcheggiate in PROJECT_STATE §6)

1. **Buy trigger anchor** (A=last_buy attuale / B=avg / C=hybrid). Origine: frustrazione "perché non compriamo" su BONK al −4.4% sotto avg. Simulazione 4-buy in downtrend ha mostrato A spread 10% vs B compresso 5%. Proposta CC: opzione C ibrida `max(avg × (1−buy_pct), last_buy × (1−min_gap))` — intuitivo di B + safety floor di A. **Aperta**, riguarda trading logic.

2. **Stop-buy time-limit** (vedi brief 74b sopra). Proposta Max. **Aperta**.

3. **HWW v3 "3 entities" inconsistency**: il draft v3 aggiorna solo il badge "3 entities → 4 entities" ma non la prose hero + meta description ("A CEO, a Co-Founder, and an Intern walk into a terminal. Three entities collaborate..."). Da decidere se aggiornare anche prose o no. **Aperta**, da affrontare in sessione "sito pubblico".

---

## Cosa NON è stato fatto in S74 (e perché)

- **HWW v3 sul sito (brief 74a Task 1)** — Max ha redirezzato la sessione a "tutto ciò che vedo solo io" (privato Telegram + admin.html). HWW è pubblico, va in nuova sessione dedicata "sito pubblico".
- **Memo Brainstorming items strategici (multi-asset Sentinel, time horizons, TF tier 3 rethink)** — sono argomenti di sessione strategica con CEO, non lavoro CC. Memorizzati nel memo `config/Memo_Brainstorming_2026-05-11.md`.

---

## Audit cadenza (CLAUDE.md §1)

- **Area 1 (tecnica)**: ultimo 2026-05-12 (S73c) — ✅ entro cadenza 30 giorni
- **Area 2 (coerenza progetto)**: audit visivo Max 2026-05-11 — ✅ entro cadenza 90 giorni
- **Area 3 (strategy & marketing)**: nessun audit formale registrato. **⚠️ Da pianificare** se CEO ritiene applicabile in fase pre-go-live. Non urgente.

---

## Stato Mac Mini fine sessione

- Bot: 5 processi vivi (orchestrator PID 38772, caffeinate, 3 grid runner) restartati 18:32 UTC
- Sentinel/Sherpa: DRY_RUN, Telegram silent (env flags)
- TF: disabilitato (ENABLE_TF=false)
- Cron reconcile: schedulato 03:00 Europe/Rome, TCC ora funzionante
- Volume Archivio: montato

---

## Per la prossima sessione

**Priorità 1: brief 74c (partial fills mainnet-gating).** Fix + test plan + cleanup orphan esistente in DB. Stima ~30-60 min.

**Priorità 2-N: a discrezione CEO.** Candidati:
- Brief 74b (dashboard stop-buy visibility) — UX, ~30-60 min
- Decisione buy trigger anchor (strategica)
- HWW v3 sito pubblico (brief 74a Task 1 deferred)
- Brief separato `managed_holdings` (famiglia bug fantasma, ~3-4h, mainnet-safe)
- Decisione stop-buy time-limit (strategica)

Lo stato del repo è pulito, ogni brief aperto è documentato, ogni decisione parcheggiata è in PROJECT_STATE §6.

---

*Sessione completata. Buon riposo.*
