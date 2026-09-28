# S131c — Verifiche dopo il riavvio: "TF on", test nel database, conteggi

**Per:** CEO e Board · **Da:** CC (S132, 2026-09-28)
**Brief sorgente:** [`config/2026-09-28_S131c_brief_post-riavvio-verifiche.md`](../config/2026-09-28_S131c_brief_post-riavvio-verifiche.md)
**Commit:** vedi il commit S132 che aggiunge questo report, `tests/conftest.py` e `tests/test_conftest_isolation_s132.py`. Nessun codice dei bot toccato, nessun riavvio.

---

## In breve

1. **"TF on" è un'etichetta sbagliata, non un TF acceso.** Il messaggio riporta l'interruttore nel database, acceso dal 18-mag. Il TF parte solo se sono accesi sia quello sia la variabile `ENABLE_TF`, che è spenta. **Il TF non gira e non può operare su Kraken**, per tre motivi indipendenti (§1). Nessuno STOP. Resta una decisione per Max: spegnere anche l'interruttore nel database, così i due segnali tornano coerenti.
2. **Le righe di test erano molte di più di ~15: 213 oggi**, da tre giri della suite (15:04, 18:00 e 19:11 UTC, 71 righe ciascuno), più 142 del 26-set. Solo nel registro eventi: nessuna riga in `trades`, `config_changes_log`, `bot_runtime_state`, `bot_state_snapshots` né nelle altre 11 tabelle con simboli. Il giro delle 19:11 l'ho lanciato io tre minuti prima del riavvio, per verificare la correzione dei log.
3. **Corretto:** ora la suite non raggiunge mai il database vero né internet. 369 test su 369 passano, e dopo un giro di prova il database non ha ricevuto nessuna riga. Le 213 righe del 28-set sono cancellate, con una copia di riserva; quelle del 26-set restano in attesa di ok.
4. **I tre conteggi si parlano, senza doppioni.** 65 = riconciliazione del 27-set, prova di luglio inclusa. 64 = ordini del ciclo fino al 28-set. 62 = non sono operazioni ma i punti di prova della simulazione (§3).

---

## 1. "TF on" nel messaggio d'avvio

**Cosa significa.** Il messaggio `Orchestrator started with 2 grid bot(s), TF on` viene da `bot/orchestrator.py:586` e stampa il valore di `trend_config.trend_follower_enabled`, l'interruttore nel database. Ma l'orchestrator avvia il TF solo se `tf_enabled and ENABLE_TF` (`bot/orchestrator.py:479`). Dal S67 la variabile d'ambiente prevale sul database, e il messaggio non è mai stato aggiornato di conseguenza. Il log dell'orchestrator, alla stessa ora, riporta correttamente `Brain flags: TF=False`.

| | Valore oggi | Da quando |
|---|---|---|
| Interruttore nel database (`trend_follower_enabled`) | **acceso** | `trend_config` non è stato modificato dal 18-mag (epoca testnet, quando il TF girava davvero) |
| Variabile `ENABLE_TF` dell'orchestrator | **spenta** (`false`) | S125, 7-ago; confermato col `ps eww` del riavvio di oggi |
| Processo TF | **non esiste** | nessun `trend_follower` nei processi del Mini |
| Configurazione TF | budget $100, massimo 3 monete, 4 lotti per moneta, `dry_run=false` | 18-mag |
| Righe gestite dal TF in `bot_config` | solo ETH/USDT (`tf_grid`), **inattiva**, venue Binance | 7-ago |

**Può aprire posizioni su Kraken con soldi veri? No**, per tre motivi indipendenti:
- **Non parte:** con `ENABLE_TF=false` l'orchestrator non lo lancia. `scripts/start_bots.py`, usato anche dall'avvio automatico, imposta sempre `false`.
- **Anche se partisse, non parla con Kraken:** il codice del TF usa solo Binance (`bot/exchange.py`, `ccxt.binance`), e sul Mini `BINANCE_TESTNET=true`, cioè soldi finti.
- **Il riconciliatore degli orfani** (che a ogni avvio può riattivare righe TF con monete residue) tocca solo righe `managed_by='tf'` inattive. Oggi non ce n'è nessuna, e il log dice `No TF orphans detected`.

**Coerente con la decisione del 7-ago?** Negli effetti sì: il TF è fermo. Nella forma no: due segnali su tre dicono "acceso", l'interruttore nel database e il valore predefinito della variabile (`true` se manca). Oggi basta `start_bots.py` a tenerlo spento. Chi lanciasse l'orchestrator a mano, dimenticando la variabile, farebbe ripartire il TF, anche se solo su Binance testnet.

**Proposte per Max (non eseguite: il brief chiede di non toccare il TF senza ok):**
- **A (consigliata): spegnere l'interruttore nel database** (`trend_follower_enabled = false`). Si fa con una modifica al database, reversibile in un secondo, senza riavvio. Da quel momento il messaggio dice "TF off" e le due protezioni sono entrambe chiuse.
- **B: correggere il messaggio** perché mostri lo stato effettivo, per esempio "TF off (database on, ENABLE_TF=false)". È una riga nell'orchestrator e diventa attiva al prossimo riavvio. Può affiancare A.

## 2. Test che scrivevano nel database di produzione

**Confermato:** sono i test. Non c'era nessun `tests/conftest.py`, e ogni modulo del bot scrive tramite `db.client.get_client()` (`db/client.py:12-18`), che crea il client Supabase vero con le chiavi di `config/.env`. La suite gira sul Mini in una copia temporanea del repo, che include quelle chiavi.

**Quante righe e dove** (verificate tutte le 15 tabelle con una colonna simbolo):

| Tabella | Righe di test |
|---|---|
| `bot_events_log` | **355**: 213 del 28-set + 142 del 26-set |
| `trades`, `config_changes_log`, `bot_runtime_state`, `bot_state_snapshots` e le altre 10 | **0** |

Più indietro del 26-set non si vede nulla: il registro eventi si pulisce da solo dopo 7 giorni.

**Le 213 righe del 28-set (cancellate):**

| Giro della suite (UTC) | Righe | Simboli |
|---|---|---|
| 15:04:54 – 15:05:14 | 71 | `TEST/USDT`, `TEST/USD`, `BTC/USDT` |
| 18:00:51 – 18:01:07 | 71 | idem |
| 19:11:46 – 19:11:59 | 71 | idem |

Ogni giro scrive le stesse 71 righe. Tipi di evento nel giro delle 19:11:
- 48 `sell_avg_cost_detail` TEST/USDT e 6 TEST/USD (vendite finte, alcune a $100);
- 2 `stop_buy_activated`, 2 `stop_buy_unlock_reset`, 1 `stop_buy_cleared`;
- 2 `buy_blocked_above_avg`, 2 `idle_recalibrate_skipped`;
- 1 `dead_zone_recalibrate` TEST/USDT e 1 `dead_zone_recalibrate` BTC/USDT a $81.853 (più 1 `post_recalibrate_cooldown`);
- 1 ciascuno di `profit_lock_triggered`, `trailing_stop_triggered`, `sell_penalty_reset`, `idle_recalibrate_suppressed_no_cash`, `idle_reentry_suppressed_no_cash`.

Copia completa prima della cancellazione: `audits/backtest/s131c_test_rows_deleted_20260928.json` sul Mini (213 righe, non in git). **Le 142 righe del 26-set non le ho cancellate** (serve l'ok di Max). Se nessuno fa niente, spariscono da sole il 4-ott con la pulizia dei 7 giorni.

**La correzione** (`tests/conftest.py`, solo codice dei test, nessuna modifica ai bot):
- **Primo strato:** prima che i test importino qualunque modulo del bot, la fabbrica del client viene sostituita da un finto database in memoria. Registra le scritture e restituisce risultati vuoti alle letture. Il momento conta: 23 moduli importano `log_event` direttamente all'avvio. È per questo che in S114 il problema era stato giudicato "non banale": una sostituzione fatta più tardi non li raggiunge.
- **Secondo strato:** durante i test ogni connessione verso internet viene bloccata (Supabase, Telegram, Kraken, Binance, Anthropic). Un test che provasse a uscire fallirebbe subito, invece di scrivere in produzione.
- **Uscita esplicita** per un'eventuale prova d'integrazione voluta: `BAGHOLDER_TESTS_ALLOW_REMOTE=1`.
- **Test della protezione stessa** (`tests/test_conftest_isolation_s132.py`): verifica che il client sia quello finto, che un evento resti in memoria e che la rete sia bloccata.

**Verifica:** 369 test su 369 passano. Dopo il giro di prova delle 19:24 UTC il registro eventi non ha ricevuto nessuna riga. La suite è scesa da 14 secondi a 1,5: il tempo in più era quello delle chiamate al database vero.

## 3. I tre conteggi

| Numero | Fonte | Cosa conta | BTC | SOL | Totale |
|---|---|---|---|---|---|
| **65** | Riconciliazione R.1, 27-set 19:51 UTC | ordini nel database e su Kraken fino a quel momento, **inclusi i 2 di prova di luglio** | 26 = 24 + 2 di prova | 39 | 65, tutti abbinati uno a uno, 0 differenze |
| **64** | Addendum A.1, Q2 (registro Kraken dal 22-lug) | ordini del ciclo `kraken_2b` fino al 28-set | 24 | **40** | 64 |
| +2 | Ordini di prova 17 e 21-lug (ciclo `kraken_test`) | fuori dal ciclo | 2 | — | 2 |
| **62** | A.1, prova ancorata | **punti di prova**, non operazioni: ogni prova parte da un'operazione vera e guarda la successiva, quindi l'ultima di ogni moneta non fa da punto di partenza | 24 − 1 = 23 | 40 − 1 = 39 | 62 |

**Come si parlano:** oggi il database ha 66 ordini Kraken (24 + 2 + 40). R.1 ne ha visti 65 perché l'acquisto SOL del 28-set alle 14:29 UTC (a $118,26) è arrivato dopo, e sarà nel controllo notturno delle 03:00. A.1 ha usato gli stessi 64 del ciclo, meno uno per moneta. Nessun doppione: R.1 ha abbinato ogni ordine uno a uno, con 0 ordini orfani e 0 differenze. Il controllo notturno ignora anche 1 cambio EUR→USD fatto a mano, che non è un ordine dei bot.

**Da correggere solo nella formulazione:** nel report A.1 "rifà 54 operazioni reali su 62" andrebbe letto come "54 punti di prova su 62".

## Decisions

DECISIONE: isolamento dei test con `tests/conftest.py` (client finto + blocco della rete), senza modifiche al codice dei bot.
RAZIONALE: sostituire la fabbrica del client prima di ogni import raggiunge anche i 23 moduli con import diretti, che era il nodo di S114. Il blocco della rete copre qualunque altro scrittore remoto, Telegram compreso.
ALTERNATIVE CONSIDERATE: un controllo dentro `log_event` basato su una variabile d'ambiente (tocca codice che gira coi soldi veri e copre solo il registro eventi); un database di test separato (costo e manutenzione).
FALLBACK SE SBAGLIATA: cancellare `tests/conftest.py`, e la suite torna com'era.

DECISIONE: cancellate solo le 213 righe del 28-set; le 142 del 26-set restano.
RAZIONALE: è il perimetro del brief. Oltre serve l'ok di Max, e comunque la pulizia automatica le toglie il 4-ott.
ALTERNATIVE CONSIDERATE: cancellare anche il 26-set subito.
FALLBACK SE SBAGLIATA: le righe cancellate sono nella copia JSON sul Mini e si possono reinserire.

DECISIONE: nessuna azione sul TF; due proposte a Max (interruttore nel database spento, messaggio corretto).
RAZIONALE: il brief chiede di non toccare il TF senza ok, e il TF non può operare su Kraken, quindi non c'è urgenza.
ALTERNATIVE CONSIDERATE: correggere subito il messaggio (è solo un'etichetta, ma sta nell'orchestrator e andrebbe live al riavvio).
FALLBACK SE SBAGLIATA: nessuno necessario.
