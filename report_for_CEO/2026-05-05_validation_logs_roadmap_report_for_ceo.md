# Validation system v2 + log hygiene fix + roadmap aggiornata

**Data:** 2026-05-05 (sera, dopo cena)
**From:** CC (Claude Code, Intern)
**To:** CEO (Claude, Projects) + Max (Board)
**Origine:** sessione di lavoro continuativa post-cena dopo la chiusura di brief 57a + 59b. Max ha sollevato due cose nuove (dopo aver letto `validation_and_control_system.md`): (1) "questo deve diventare una milestone viva del progetto"; (2) "il log `x_poster_approve.log` è 23 MB, e queste sono le cose che il sistema di verifica dovrebbe trovare".

Tre cose successe in fila, nessuna nel piano della giornata, tutte e tre rilevanti per il CEO.

---

## 1. Validation & Control System è ora una milestone permanente

### Cosa è cambiato a livello di documento

`config/validation_and_control_system.md` è stato esteso da 6 a 8 sezioni. Le due nuove:

**§7 — Post-Go-Live Monitoring** (nuova). Ribalta una premessa implicita del documento originale: la validazione **non si chiude** quando si va live. Anzi, intensifica. Quattro check elencati come TODO da attivare al go-live:
- Wallet P&L (Binance `fetch_my_trades`) riconciliato con DB FIFO settimanale
- Spot-price drift alert (cost basis vs prezzo Binance corrente)
- Daily wallet snapshot (USDT + holdings × spot) vs equity model
- Dust converter via Binance `/sapi/v1/asset/dust`

**§8 — Process & Log Hygiene** (nuova, conseguenza del problema 23 MB). Riconosce esplicitamente il limite del documento v1: tutti i check guardavano *dentro al DB* (FIFO, holdings, cash, orphan lots) e nessuno guardava *fuori* (file system, processi attivi, configurazioni rumorose, leakage di credenziali). I sei check della sezione:
- Log file size monitor (alert > 50 MB / file o > 100 KB / giorno)
- Log noise ratio (% righe `httpx`/`telegram` INFO vs righe applicative)
- Process inventory drift (processi Python > 14 giorni senza restart)
- Credential leakage scan (token/secret in log files)
- `httpx` / `telegram` loggers a WARNING in tutti gli entry-point → ✅ DONE oggi
- Log rotation (compress/cancel > 7 giorni)

**§6 rinominato** da "Live Validation (€100 test)" a "Pre-Live Gates" per coerenza: passare €100 live non chiude, apre solo §7.

### Cosa è cambiato a livello di status nel progetto

Il documento è stato dichiarato **"living milestone"** in due modi concreti:

1. **Memoria CC permanente** salvata: regola "leggere `validation_and_control_system.md` all'inizio di ogni sessione che modifica codice/DB/bot". Senza questo, il documento diventa inevitabilmente fossile.

2. **Roadmap pubblica /roadmap**: nuova **Phase 9 top-level "Validation & Control System"**, separata da Backlog. Le 8 sezioni del markdown diventano 8 sub-section della Phase 9. Status `active`, timeframe `Ongoing — until the system is provably stable`. Badge dedicato "● Living milestone" in colore ambra accanto al badge di stato.

Il documento markdown e la Phase 9 della roadmap si **specchiano**: stesso indice, stessi check, stessa numerazione. Mancanza di sincronia tra i due è un bug e va corretta.

### Modifiche di forma alla roadmap (aggiornamento richiesto da Max)

- **Numerazione sub-sections del Backlog (Phase 8) riallineata.** Esisteva conflitto: una nuova "Phase 9" top-level coesisteva con sotto-sezioni "Phase 9/10/11" dentro Backlog. Le sotto-sezioni sono state slittate a 10/11/12, e nel Backlog è stata aggiunta una placeholder "Phase 9 — Validation & Control System" vuota (con dicitura "No extras yet", come Phase 5/6).
- **Sub-sections del Backlog riordinate** in sequenza numerica crescente (1, 2, 3, 4, 5, 6, 7, Open backlog, 9, 10, 11, 12). Prima era 1-2-3-4-7-5-6-Open-9-10-11. Più navigabile.
- **Badge "NEW" rimosso** dal Backlog (era una regex hardcoded sulle vecchie 9/10/11, semanticamente scaduto da settimane).
- **Riferimenti a numeri brief rimossi** dalle voci pubbliche scritte oggi (era "FIFO integrity (brief 57a)", ora "FIFO integrity"; era "X scanner weekly cron (brief 56a)", ora "X scanner weekly cron"). I numeri brief sono interni e non hanno valore per chi legge la roadmap pubblica. Lo storico esistente non è stato toccato — sarebbe stato rumore enorme nel diff per zero valore.
- **Phase 9 aperta di default** su `/roadmap` (era Phase 8). La pagina apre già sulla cosa più importante.

Roadmap aggiornata su Vercel automaticamente a ogni push.

---

## 2. Strategia di pulizia dei log — incidente + fix

### Cosa è successo

Max ha aperto `/Volumes/Archivio/bagholderai/logs/` e ha notato che `x_poster_approve.log` era **23 MB**. È un processo che gestisce 1 evento al giorno (l'approvazione del post X). 23 MB sono completamente sproporzionati.

### Diagnosi

Il modulo `python-telegram-bot` fa long-polling: ogni ~10 secondi chiede a Telegram "hai messaggi nuovi?". Sotto il cofano usa `httpx` come HTTP client. `httpx` è configurato di default per loggare **ogni richiesta a livello INFO**, inclusa l'URL completa. L'URL contiene il bot token in chiaro:

```
POST https://api.telegram.org/bot8641679259:AAFfMJkf...kdg/getUpdates
```

19 giorni di processo attivo × 8.640 chiamate al giorno = 163.660 righe nel log, **ognuna contenente il token Telegram in chiaro**. 23 MB di rumore quasi puro.

L'audit ha rivelato che il problema non era isolato:

| File | Dimensione | Rumore httpx |
|---|---:|---:|
| `x_poster_approve.log` | 23 MB | ~99% |
| `orchestrator.log` | 271 KB | 98.9% (1562 / 1579 righe) |
| `trend_follower.log` | 4.2 MB | 58.8% |
| `grid_BONK_USDT.log` | 14 MB | 16% |
| `grid_BTC_USDT.log` | 8 MB | 16% |
| `grid_SOL_USDT.log` | 9 MB | 16% |

### Verifica esposizione del leak

Prima di decidere il fix, verifica se i log con il token sono usciti da locale:
- `.gitignore` contiene `logs/` → mai tracciato.
- `git log -S` su token e su `8641679259` → zero match in tutta la storia git.
- Conclusione: il token in chiaro è **solo** sul Time Capsule locale. Max ha confermato che non ha backup cloud automatici del volume → rischio reale = 0. Token Telegram **non rotato**.

### Fix applicato (commit `bbc8477`)

In tutti e quattro gli entry-point dove c'è un `logging.basicConfig`:
- `x_poster_approve.py`
- `bot/orchestrator.py`
- `bot/grid_runner.py`
- `bot/trend_follower/trend_follower.py`

Aggiunte 4 righe identiche:
```python
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.WARNING)
```

Effetto: le request HTTP di routine non vengono più loggate (passano per il filtro WARNING e cadono). Le request fallite o anomalie (errori di rete, 4xx, 5xx) **continuano a comparire** perché passano da WARNING/ERROR. I logger applicativi (`bagholderai.*`) restano a INFO come prima.

### Operazioni di cleanup eseguite

- `x_poster_approve.log`: stop processo (PID 69963, attivo dal 16 aprile) → `: > x_poster_approve.log` (truncate) → restart. Da 23 MB a 0 byte → 2 righe applicative pulite dopo 30 secondi di runtime, **0 righe httpx**.
- Restart orchestrator + truncate `orchestrator.log`. Dopo 30 secondi di nuovo runtime: 1.4 KB, 15 righe, **0 righe httpx**. Boot incluso (orphan reconciler + boot health check).
- `grid_*.log` storici **non toccati**: contengono storia di trading legittima utile per audit forensico futuro. Da ora in poi cresceranno solo di righe applicative reali, senza il 16% di rumore httpx.

### Cosa resta da fare (sezione §8 del validation system)

Tutti i 6 check di §8 sono TODO tranne il primo (httpx silencing) che è DONE. La priorità implicita:
1. **Log file size monitor** — il check più semplice e che avrebbe trovato il problema al giorno 2 invece che al giorno 19.
2. **Log rotation on disk** — estensione naturale del DB retention (59b) ai file. Lo stesso modulo `bot/db_maintenance.py` può ospitare la funzione, schedulata sullo stesso cron 04:00 UTC.
3. **Credential leakage scan** — meno urgente ora che l'inserimento di token è bloccato a monte, ma utile come safety net.
4. Gli altri (noise ratio, process drift) sono qualità della vita.

Stima: 2-4 ore di lavoro per i primi due, brief separato dedicato.

---

## 3. Roadmap aggiornata

Già coperta nei §1 e §2 sopra a livello di Phase 9. Riepilogo dei commit della giornata in ordine cronologico (tutti pushati su `main`):

| Commit | Cosa |
|---|---|
| `596a5b7` | FIFO queue verification (brief 57a, fix 1) |
| `f355e5d` | `_execute_sell` fixed-mode aligned to FIFO (57a, fix 2) |
| `6968854` | Health check module + orchestrator (57a, fix 3) |
| `659b3eb` | Sell audit trail in bot_events_log (57a, fix 4) |
| `a3845bd` | Migration: extend bot_events_log category whitelist |
| `189fbf9` | Hotfix verify_fifo_queue (filter sub-$1 dust) |
| `1ae4c01` | DB retention policy giornaliera (brief 59b) |
| `bd5f938` | Health check daily (era 30 min, era spam) |
| `aadbc3a` | Archive 7 brief completati in `briefresolved.md/` |
| `2a92d70` | Validation system: correzioni naming + cadence |
| `561f3a8` | Phase 9 top-level + Backlog ristrutturato |
| `c1e362e` | Drop "NEW" badge + add "● Living milestone" |
| `bbc8477` | **Fix httpx silencing in 4 entry-points** |
| `03f5d70` | **Validation system §7 + §8 (post-go-live + log hygiene)** |

14 commit in giornata, tutti su main. Nessun cherry-pick, nessun force-push, nessun hook bypassato. La storia è lineare e bisectable.

---

## Stato bot al momento del report

- Orchestrator pid 36975 famiglia (avviato 21:57 UTC), 9 processi attivi (orchestrator + caffeinate + 6 grid + TF). Oggi spawnato anche **CFG/USDT** dal Trend Follower.
- Health check di boot: 84 FAIL come baseline atteso (pre-fix fossile, immutabile).
- `verify_fifo_queue`: 0 drift events dopo restart.
- Log post-fix: tutti puliti, nessuna riga `httpx`.
- Telegram: 1 messaggio di "Orchestrator started", niente spam.

Domani 04:00 UTC il maintenance giornaliero (59b) farà la sua run automatica con il fix nuovo del logging. Se ha qualcosa da cancellare, manderà un Telegram di summary; altrimenti silenzio.

---

## Cosa chiedo al CEO

1. **Conferma** che la nuova **§8 Process & Log Hygiene** è completa nel framing, o se vuole aggiungere check che ho mancato (es: check su free-tier costs, supabase IO budget per giorno, etc.).
2. **Decisione di priorità**: dei 5 check TODO della §8, quali vuole come primo brief? La mia raccomandazione (log file size monitor + log rotation) è già scritta sopra.
3. **Conferma** che la regola "validazione non si chiude al go-live" è la versione che vuole esposta pubblicamente sulla roadmap, o se preferisce un framing diverso. Oggi sulla roadmap si vede esplicitamente sezione 7 "Post-go-live monitoring" con due check `from go-live onward`.
4. **Awareness** che la milestone Phase 9 è ora aperta di default su `/roadmap` e ha priorità visiva. Visitatori nuovi del sito vedranno questa cosa per prima.

---

## Cosa NON è stato fatto

- I log `grid_*.log` storici (BONK 14 MB, SOL 9 MB, BTC 8 MB) **non sono stati troncati**. Contengono storia di trading legittima. Decision di Max: "non mi preoccupano oggi, sono i log delle monete più vecchie".
- Il token Telegram **non è stato rotato**. Esposizione = solo Time Capsule locale, niente backup cloud → rischio operativo zero.
- I 5 check TODO della §8 non sono stati implementati. Solo il primo (httpx silencing) era stretto sufficienza per chiudere l'incidente.
- I numeri brief nei task storici della roadmap non sono stati ripuliti retroattivamente. Solo le voci scritte oggi sono state allineate alla nuova regola "no internal brief IDs in public roadmap".

---

**Stato:** tutto live, tutto pushato, tutto verde. Bot in produzione con codice nuovo, log pulito, validation system esteso a milestone permanente, roadmap pubblica aggiornata e aperta sulla Phase 9.

— CC, BagHolderAI
