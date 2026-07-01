# [PARKED] Isolamento DB dei test — conftest.py autouse (Opzione B di A1 MED-2)

**Data:** 2026-07-01 · **Parcheggiato:** 2026-07-01 · **Autore:** Claude Code (Intern)
**Origine:** audit A1 `20260630_audit[A1].md`, finding **MED-2**. L'Opzione A (toppa
locale) è **SHIPPED** nel commit `81d00dd` (`fix(A1)`). Questo brief è l'**Opzione B**
(rete di sicurezza sistemica), rimandata per scelta condivisa CC + CEO (2026-07-01).
**Stato:** DA FARE. Non urgente, ma da fare **bene** (vedi §"Perché un brief e non una riga").

---

## 0. TL;DR (in parole povere — per Max)

Il bot ha un "registratore" (`log_event`) che scrive gli eventi nel **database di
produzione** — serve per l'osservabilità vera. Non ha una "modalità test": quando i
test automatici passano per un codice che chiama il registratore, e chi ha scritto il
test si dimentica di **tappargli la bocca**, il test scrive eventi finti nel log reale
(è successo: 6 SELL BONK/USD fantasma, poi cancellati).

- **Opzione A (già fatta):** tappata la bocca in **quel** file di test. Buco chiuso, ma
  è una toppa locale — riapribile se un altro test se ne dimentica.
- **Opzione B (questo brief):** **una toppa maestra all'ingresso di tutti i test**
  (`tests/conftest.py`), così nessuno può più sbagliare per dimenticanza.

**Perché non l'abbiamo fatta subito:** la toppa maestra funziona solo se è messa nel
punto esatto. Fatta ingenuamente, **sembra** proteggere tutto ma lascia buchi
invisibili → **falsa sicurezza**, che è peggio di niente (smetti di stare attento
credendo di essere coperto). Analogia: è la valvola di chiusura centrale di un palazzo
che ha più linee d'acqua indipendenti — se la metti solo sulla linea principale, alcuni
appartamenti continuano ad allagarsi mentre tutti credono che il palazzo sia protetto.
Prima mappi tutte le linee, poi metti la valvola.

**La frase da ricordare:** *"I test possono sporcare il registro vero del bot. Abbiamo
tappato un buco; c'è una rete di sicurezza più grande da progettare bene prima di
installarla."* Il resto sta scritto qui sotto: non serve tenerlo a mente.

---

## 1. Il difetto strutturale (per CC)

`db/event_logger.log_event()` risolve `get_client()` **a runtime** dentro il corpo
([db/event_logger.py:45](../../db/event_logger.py#L45)) e quel client è la Supabase di
**produzione** ([db/client.py:11](../../db/client.py#L11)). Non esiste override per i
test. Qualsiasi path esercitato da un test che raggiunge `log_event` (o
`_alert_rejection`, che lo chiama + fa un alert Telegram) scrive su prod, a meno che il
singolo test non lo stubbi a mano.

Oggi i test si difendono **uno per uno** (fragile):
- `tests/test_sherpa_write_gate.py:41` → `sherpa_main.log_event = lambda *a, **k: None`
- `tests/test_accounting_avg_cost.py:1282+` → swap di `log_event` **e** `_alert_rejection`
- `tests/test_exchange_adapter_s112.py` → fixture autouse (Opzione A, `81d00dd`)

Il difetto: se un test nuovo tocca il path e **si dimentica** lo stub, il buco si
riapre in silenzio. È esattamente quello che è successo con l'adapter Kraken.

---

## 2. Perché un brief e non una riga — la trappola patch-location

In Python, `from db.event_logger import log_event` **a livello di modulo** crea un
**binding proprio**: il modulo tiene il proprio riferimento alla funzione. Se un
`conftest.py` patcha l'originale `db.event_logger.log_event`, quei moduli continuano a
usare la **loro copia** → il patch **non li raggiunge**. Un conftest scritto così dà
falsa sicurezza.

### Passo 0 — la mappa (già fatta il 2026-07-01, da riverificare al momento del brief)

**Import a livello di modulo (binding proprio — un patch su `db.event_logger.log_event`
NON li cattura):** ~20 moduli live —
`bot/orchestrator.py`, `bot/health_check.py`, `bot/dust_converter.py`,
`bot/newskeeper/{haiku_classifier,signal_writer,main}.py`,
`bot/newskeeper_v2/{classifier,store,main}.py`,
`bot/trend_follower/{counterfactual,trend_follower,allocator}.py`,
`bot/grid_runner/{liquidation,__init__}.py`, `bot/sentinel/main.py`,
`bot/grid/{dust_handler,sell_pipeline,grid_bot}.py`, `bot/sherpa/main.py`,
`config/supabase_config.py`.
(Esclusi: `review/phase1/**` = codice di riferimento archiviato, non live.)

**Import dentro funzione (import locale — un patch su `db.event_logger.log_event` LI
cattura, perché re-importano al call time):**
`bot/exchange_orders.py:53,221`, `bot/grid/buy_pipeline.py:78`,
`bot/grid/state_manager.py:324,356,426`.

Comando per rigenerare la mappa:
```
grep -rn "from db.event_logger import log_event" --include="*.py" . | grep -v /venv/ | grep -v /tests/
```

---

## 3. Due design candidati (da valutare nel brief)

### Design 1 — patch per-binding (fragile, sconsigliato)
Il conftest patcha il `log_event` bindato in **ogni** modulo della mappa §Passo 0
(`sherpa.main.log_event`, `bot.trend_follower.allocator.log_event`, …). Contro: la lista
va tenuta aggiornata a mano; un modulo nuovo che dimentica di essere aggiunto riapre il
buco → riproduce lo stesso rischio che vogliamo eliminare.

### Design 2 — patch alla sorgente (RACCOMANDATO da valutare)
Il corpo di `log_event` risolve **a runtime** il suo `get_client` (nota:
`event_logger.py:27` importa `get_client` a livello di modulo → tiene la **sua** copia,
quindi si patcha `db.event_logger.get_client`, non `db.client.get_client`). Un unico
patch di **`db.event_logger.get_client` → MagicMock** neutralizza la scrittura DB per
**tutti** i chiamanti di `log_event`, indipendentemente da come l'hanno importato — un
solo punto, nessuna lista da mantenere.

**Da coprire in aggiunta** (il patch su get_client NON basta da solo):
1. **Telegram**: `_alert_rejection` e altri path fanno alert Telegram con un notifier
   separato → va no-oppato anch'esso (censire il notifier usato).
2. **Altre scritture DB non-via-log_event**: `db/client.py` (`TradeLogger`,
   `runtime_state`, snapshot, ecc.) usano `get_client()` per conto proprio → valutare se
   il conftest debba mockare anche `db.client.get_client` per una "suite ermetica"
   completa, o solo il canale eventi/alert.

---

## 4. Vincolo di correttezza — non rompere i test legittimi

Alcuni test **iniettano di proposito** un fake client (es. `test_sherpa_write_gate.py`
usa un `FakeSupabase`) o vogliono **asserire** che `log_event` sia stato chiamato. Una
toppa maestra troppo larga potrebbe interferire. Il brief deve:
- verificare che un `get_client` mockato globale non rompa i test che passano il proprio
  fake esplicitamente (dovrebbe andare: quei test iniettano il client nel codice sotto
  test, `get_client` è solo il fallback);
- lasciare un modo per **opt-out** ai test che vogliono spiare `log_event` (re-patch con
  un proprio spy dentro il test);
- decidere se i guard per-test esistenti (§1) si **rimuovono** (ridondanti) o si
  **tengono** come belt-and-suspenders.

---

## 5. Verifica di accettazione
1. Run completo della suite → **0 nuove righe** in `bot_events_log` di prod (query
   before/after, come nel fix MED-2-A del 2026-07-01: contare eventi con la firma di test
   prima e dopo il run).
2. Tutti i test **verdi** (baseline attuale: 271).
3. Nessun alert Telegram reale durante la suite (canale report pulito).
4. Un test "canarino" scritto apposta che chiama `log_event` senza stub locale →
   **non** deve produrre righe su prod (prova che la rete regge).

---

## 6. Trigger di sblocco
**Prossima sessione che tocca la test-suite / infrastruttura di test**, **oppure
pre-cutover Kraken** (al cutover l'adapter Kraken passa dal dormiente al vivo e la suite
gira di più → conviene avere la rete prima). Non è un gate di mainnet: l'Opzione A ha già
chiuso il buco reale noto.

---

## 7. Decision log / anti-assenso
- **Perché rimandata e non fatta con MED-1/MED-2-A:** una toppa maestra fatta male dà
  **falsa sicurezza** (Design 1 lascia ~20 buchi; un Design 2 incompleto lascia il canale
  Telegram e le scritture non-log_event). Peggio di non averla. Richiede il Passo 0 + il
  vincolo §4, non una riga infilata in un commit sotto la fretta di chiuderne due insieme.
  (Concordato CC + CEO, 2026-07-01.)
- **Cosa copre già l'Opzione A (`81d00dd`):** il singolo path reale del leak (adapter
  Kraken). Il rischio concreto noto è chiuso; questo brief è **hardening preventivo**.
- **Fallback se il conftest si rivelasse sbagliato:** è un file additivo isolato
  (`tests/conftest.py`); rimuoverlo ripristina lo stato attuale (guard per-test). Zero
  impatto sul runtime del bot.
