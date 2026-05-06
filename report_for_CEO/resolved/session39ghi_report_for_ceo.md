# Report per il CEO — Sessioni 39g + 39h + 39i (19 aprile 2026)

Caro CEO,

tre commit, tre classi di bug che si erano nascoste dentro il sistema aspettando di mordere in produzione. Due li hai scovati tu: "il TST ha venduto tutto in perdita, poi ha ri-comprato un lotto, poi lo ha rivenduto in perdita di nuovo, poi liquidato il nulla", e "continua a non modificare il parametro". Per uno dei due, ti avevo anche detto che era risolto — e mi sbagliavo. Occhio allenato, ti dovevo credere prima. Ti racconto cosa è successo e cosa abbiamo messo a posto.

---

## Commit 1 — `6675b75` feat(tf): audit log trend_config + Telegram sui safety params

**Il sintomo che hai segnalato:** apri `/tf`, modifichi `tf_stop_loss_pct`, salvi, il campo torna al valore di default. Cliccavi su "Save TF params" e vedevi lo status diventare giallo con "Saved (audit log failed)". Ti sembrava che la modifica non si fosse salvata.

**Cosa succedeva davvero:** la modifica **SI SALVAVA** su `trend_config`. Il PATCH andava a buon fine, il valore nel DB era corretto. Lo status giallo era perché l'INSERT collaterale su `config_changes_log` falliva con HTTP 400.

**Perché falliva:** la colonna `symbol` in `config_changes_log` era `NOT NULL`. Quando l'UI provava a salvare un cambio su `trend_config` (che è una tabella globale, senza simbolo), mandava `symbol: null`. Il DB rifiutava l'INSERT con il classico errore `23502 null value in column "symbol" of relation "config_changes_log" violates not-null constraint`. 

**La seconda parte del problema — e qui è più interessante:** per i parametri dei bot manuali (buy_pct, sell_pct, skim_pct) tu ricevi sempre un messaggio Telegram "⚙️ CONFIG CHANGE DETECTED — BTC/USDT". Per i safety TF non arrivava niente. Come mai?

Perché la notifica Telegram dei parametri normali non passa da `config_changes_log` (quella è solo audit). Passa da un **poller dedicato** in `config/supabase_config.py` che confronta lo stato corrente vs quello precedente ogni 300 secondi e, se cambia qualcosa, invia il messaggio. Quel poller monitora solo `bot_config`, non `trend_config`. Nessuno aveva mai osservato i cambi su `trend_config`, semplicemente perché fino a una settimana fa non c'era UI per modificarli.

**Cosa ho fatto:**
1. **Migration DB** — `ALTER TABLE config_changes_log ALTER COLUMN symbol DROP NOT NULL`. Applicata da te via Supabase SQL editor. Verificata con un INSERT di prova che ora passa. Dopo questa, l'audit funziona e lo status torna verde "Saved ✓".
2. **Polling `trend_config`** — Aggiunto nel main loop del Trend Follower (`bot/trend_follower/trend_follower.py`). Ad ogni scan (una volta ogni ora di default), se `tf_stop_loss_pct` / `tf_take_profit_pct` / `scan_interval_hours` sono cambiati rispetto al ciclo precedente, parte un Telegram `⚙️ CONFIG CHANGE DETECTED — trend_config` con il diff. Stesso formato di quelli che già ricevi per i manual.
3. **Latenza nota:** fino a 1 ora tra il save e la notifica (quando sarà il prossimo scan TF). Se vorrai notifiche istantanee, serve un thread dedicato come quello di `supabase_config.py`, ma è roba da brief dedicato. Per ora questa è l'ambizione minima che fa parità con admin.

**Da testare la prossima volta che salvi:** stato verde + Telegram (entro 1h) + audit row visibile in `config_changes_log` con `symbol=NULL`.

---

## Commit 2 — `65d3712` fix(grid-bot): eliminate TF thrash from dust residuals (39h)

Qui mi tocca spiegare bene perché è il commit che va davvero vicino al cuore del sistema, e perché hai fatto benissimo a chiedere "ma se andiamo live su Binance, questi sono cerotti o fix veri?".

**Il sintomo che hai segnalato:** alle 11:41 italiane (09:41 UTC) TST ha fatto uno stop-loss cascade: 4 lotti venduti in un colpo, perdita di circa $5.18. Fino a qui, comportamento atteso: `_stop_loss_triggered` si accende quando l'unrealized supera il 10% dell'allocation, il bot vende tutto. **Ma poi un minuto dopo, alle 11:42, il bot ha COMPRATO un nuovo lotto**. Poi alle 11:43 ha fatto un altro stop-loss su quel lotto appena comprato (altra piccola perdita). Poi per quasi due ore non ha fatto più nulla. Alle 13:28, finalmente, è arrivato il SWAP dal TF che ha chiuso tutto con un messaggio "LIQUIDATED (BEARISH EXIT)" su 0.1 TST di dust.

Il tuo commento — testuale: *"non mi sembra un comportamento normale e non coincide con quanto avevamo discusso nei brief precedenti"*. Hai ragione al 100%. Il brief 39f Section B diceva chiaramente: stop-loss deve chiudere il ciclo, il bot deve diventare `is_active=false`, il TF alloca altrove. Non doveva accadere il re-buy. E avevamo anche deployato il fix. Perché non ha funzionato?

**La catena di bug (tre, non uno):**

### Bug C — `round_to_step` creava dust tramite imprecisione float

La funzione che rounda l'amount al multiplo esatto del `step_size` di Binance (per TST è 0.1, per BTC è 0.00001, per BONK è 1.0) usava `Decimal(str(float))` + `ROUND_DOWN`. Sembra corretto, ma c'è un trabocchetto: Python a volte memorizza il numero 807.4 internamente come `807.39999999999994`. Se quella conversione passa per `str()`, Decimal preserva quella imprecisione → `ROUND_DOWN` lo snappa a `807.3` invece che a `807.4`. Risultato: ogni ciclo buy→sell "perdeva" 0.1 TST nel passaggio. Non perché Binance se li tenesse — era un bug di contabilità interna del bot.

Guardando il database storico di TST: **ogni volta che il bot chiudeva un ciclo, rimanevano 0.1 TST residui**. Succede dal 17 aprile. Tu non l'hai visto perché:
- Su TST il dust ha valore monetario ridicolo (0.1 × $0.011 ≈ $0.001)
- Su BTC e BONK il dust per-trade è ordini di grandezza più piccolo perché il `step_size` è molto fine
- La homepage e l'admin dashboard già hanno un contatore "Dust v3" ma nessuno guardava quella colonna su TST

**Il fix:** aggiungo un epsilon assoluto di 1e-9 prima del `ROUND_DOWN`. `807.39999999999994 + 0.000000001 = 807.4` → round_down → 807.4 pulito. Testato su 17 casi edge (TST, BTC, SOL, BONK, zero, valori molto piccoli, valori realmente sotto-step, halfway values). Nessuna regressione. In particolare, `24231428.99 BONK con step=1` resta correttamente `24231428` (la parte 0.99 è valore reale, non epsilon).

### Bug B — il dust-removal non sincronizzava lo stato in memoria

Quando il dust veniva individuato e "rimosso" (il codice faceva `_pct_open_positions.pop(0)`), **non toccava `state.holdings`**. Quindi lo stato in memoria rimaneva "holdings=0.1 TST, ma il lotto corrispondente non esiste più nella queue FIFO". Questo stato incoerente attivava il **self-heal**: il bot, vedendo holdings>0 e queue vuota, ri-faceva il replay dal DB e ri-creava il lotto fantasma. Loop infinito. La prossima volta che arrivava un sell, il dust si ricreava e così via.

**Il fix:** quando il codice pop-pa un dust lot, ora decrementa `state.holdings -= lot.amount` e resetta `avg_buy_price` a zero se arriva a zero. Stato coerente, self-heal non resuscita più nulla.

### Bug A — il cleanup post-stop-loss guardava la condizione sbagliata

Il codice che doveva dire "stop-loss ha finito di vendere tutto, ora chiudi il ciclo" usava `if holdings <= 1e-10`. Cioè: sostanzialmente solo quando gli holdings erano esattamente zero (a parte errori di virgola mobile infinitesimali). Ma grazie al Bug B, gli holdings restavano a **0.1 TST**. Quella soglia 1e-10 non scattava mai. `pending_liquidation` rimaneva `False`. Il bot restava `is_active=True`, il grid_runner continuava a girare il loop, e dopo un minuto — il tempo che il prezzo scendesse dello 0.8% — scattava il trigger di buy normale e il bot comprava un nuovo lotto. Che poi triggerava un altro stop-loss. E così via.

Poi per fortuna c'è il `_stop_buy_active` (39b per i manuali) — ma per i bot TF il gate del buy non era bloccato, perché la logica 39b è `managed_by != 'trend_follower'`. I TF erano liberi di ri-comprare.

**Il fix:** il cleanup ora fa partire `pending_liquidation=True` se UNA di queste condizioni è vera:
- `_pct_open_positions` è vuoto (il vecchio comportamento)
- residual holdings × current_price < `min_notional` di Binance (cioè il residuo è dust economico non sellable anche se ha valore nominale > 0)
- `holdings <= 1e-10` (fallback legacy)

In pratica, dopo uno stop-loss cascade il ciclo si chiude sempre entro un tick, indipendentemente dal fatto che resti o meno dust sub-step.

---

## Perché tutti e tre insieme, e perché ora

Tu mi hai chiesto testualmente: *"se ci portiamo dentro solo cerotti estetici, quando poi vado live è un'ecatombe, o sbaglio?"*. Non sbagliavi. In paper trading il dust è invisibile perché i fill sono simulati. In live su Binance:

- Bug C causerebbe `LOT_SIZE rejected` quando il bot prova a vendere 807.3999... e Binance accetta solo multipli esatti di 0.1
- Bug B causerebbe divergenze tra bot state e wallet reale (il bot pensa di avere 0.1 TST che invece è stato venduto veramente in uno stop-loss precedente)
- Bug A riapparirebbe e in live il bot brucerebbe fee reali ogni minuto di thrash

Sono tre fix ready-for-live, non cerotti. Il commit è atomico perché Fix A+B+C risolvono lo stesso bug-family: B e C generano dust, A gestisce il dust quando c'è. Testandoli separatamente c'è il rischio che uno risolva un sintomo ma nasconda un altro bug sotto. Messi insieme, la catena di causa-effetto si interrompe in ogni punto.

---

## Cosa osservare nei prossimi giorni

Il bot è già stato riavviato alle 15:59 italiane di oggi con entrambi i commit live. Cose da guardare:

1. **Nessuna riga di log** del tipo `WARN: holdings=0.X ma _pct_open_positions è vuota. Re-init dal DB...` sui bot TF (PHB, BLUR, futuri). Se la vedi, il Bug B è tornato o c'è un nuovo edge case.

2. **Se scatta un altro stop-loss**, deve esserci **UN SOLO** messaggio Telegram `🔴 DEALLOCATED (STOP-LOSS)` con il cycle summary, **nessun re-buy successivo**, e al prossimo scan TF (entro 1 ora) il budget deve tornare al pool per allocare altrove.

3. **Se modifichi un safety param via /tf**, entro 1 ora arriva `⚙️ CONFIG CHANGE DETECTED — trend_config` su Telegram. Se cambi `scan_interval_hours` stesso, la latenza della PRIMA notifica è calcolata sul vecchio interval (potrebbe volerci fino al vecchio 1h, poi il nuovo interval si applica).

4. **I bot manuali (BTC/SOL/BONK)** non sono stati toccati dai fix ma il Bug C era generico. Dopo qualche giorno, il contatore "Dust v3" nella dashboard dovrebbe restare piatto o diminuire (il dust storico pregresso è nei trade vecchi, il codice nuovo non ne produce di nuovo).

---

## Quanto siamo vicini al live

Più di ieri. Dei tre fix, C è quello che pesa di più sulla live-readiness: era un bug latente che non si manifestava in paper. Quando apriremo su Binance reale:

- Gli ordini avranno amount validi al primo tentativo
- Gli stop-loss saranno eventi puliti, non thrash bleeders
- Lo stato in memoria del bot sarà consistente col wallet exchange

Rimane ancora la serie di "out-of-scope" che avevamo parcheggiato: i due brief `36f` (trailing stop) e `36h` (Haiku vede TF) sono ancora LOW priority in `config/`. Non sono blocker per andare live, sono feature da aggiungere dopo, quando avremo più dati sul comportamento del TF in produzione.

Per oggi, direi che abbiamo chiuso bene. TST ha pagato il prezzo del debug — circa 5 dollari di perdita realizzata. Considerando che era paper, è un costo accettabile per aver scoperto tre bug prima del deploy live.

---

## Errata corrige — Commit 3 (39i): il save di /tf era una bugia, ma non era colpa nostra

Dopo il deploy di 39g/39h ti ho detto "ora /tf dovrebbe funzionare". Tu hai provato a cambiare `tf_stop_loss_pct` da 10 a 5, lo status è diventato verde "Saved ✓", e dopo il reload il campo è tornato a 10. Mi hai giustamente detto: *"continua a non modificare il parametro"*.

Non ti ho creduto subito. Ho verificato il backend con tre operazioni in sequenza: PATCH diretto dal Python → valore persiste. Nessun cron che sovrascrive, nessun TF poller che scrive. Ti ho fatto rifare il test (7 → 8, click Save), status verde, reload, torna a 7. Audit log dice `7 → 8`.

**A quel punto avevo la soluzione in mano senza saperlo: l'audit log è loggato correttamente con `7 → 8`, MA il DB resta a 7.** Due scritture diverse, due destini diversi. Ho riprodotto il PATCH esatto che fa la UI usando la stessa chiave anonima che sta nel bundle JS:

```
PATCH /rest/v1/trend_config?id=eq.04b4...
→ HTTP 200
→ body: [] (array vuoto, zero righe aggiornate)
```

**Ecco il bug.** La tabella `trend_config` su Supabase ha Row Level Security attiva con policy che consentono `SELECT` alla chiave anon, ma **non `UPDATE`**. PostgREST, quando riceve una PATCH con una chiave senza permessi di mutation, non lancia un 403 né un 400: risponde **200 con body vuoto**. Silenziosamente. Senza errore. La UI, vedendo `r.ok === true`, assume che il save sia andato → status verde.

L'audit su `config_changes_log` invece funziona perché quella tabella ha policy `INSERT` aperta per anon (l'abbiamo sistemata noi col commit 39g che ha reso nullable la colonna symbol). Così l'audit log registra `7 → 8` anche se l'UPDATE reale non è mai avvenuto.

**Perché admin.html funziona e /tf no?** Perché `bot_config` ha policy anon UPDATE aperta fin dalla nascita della dashboard admin (sessione 18b). `trend_config` invece è rimasta read-only per anon perché fino a una settimana fa nessuno cercava di modificarla da UI — era modificata solo dal TF backend che usa service key.

Quando abbiamo aggiunto la sezione "⚠️ TF Safety parameters" a tf.html (commit 39b), abbiamo creato l'endpoint UI ma non ci siamo ricordati della policy. La UI scriveva, il DB ascoltava per finta. Ho lasciato un bug silenzioso in produzione per quasi una settimana; nessuno l'aveva testato perché nessuno aveva provato a modificare i safety params da UI prima di te.

**Doppio fix:**

1. **Migration DB** — `db/migration_20260419_trend_config_anon_update.sql` aggiunge policy `UPDATE` per anon su `trend_config`. Limitato a UPDATE (SELECT già aperto, INSERT/DELETE restano chiusi, la tabella è una singleton). Da applicare via Supabase SQL editor come le altre migration.

2. **Hardening `sbPatch`** in `admin.html` + `tf.html` — la funzione che fa il PATCH ora controlla la risposta: se è 200 ma il body è un array vuoto, lancia `Error: no rows updated (RLS policy?)`. La UI allora mostra status rosso con l'errore esplicito invece del falso "Saved ✓" verde. Così se in futuro una policy cambia o una migration non viene applicata, il bug emerge subito invece di nascondersi.

**Lezione architetturale:** quando aggiungiamo una UI che scrive su una tabella nuova, **controllare prima le policy RLS**. Non basta che la migration dello schema sia applicata; serve anche che la chiave anon abbia i permessi giusti sulla tabella. Aggiungo un promemoria nel brief template per le prossime sessioni.

**Sequenza operativa per te:**
1. Applica la migration RLS via Supabase SQL editor
2. Dimmi quando è fatta, verifico che il PATCH con anon ora funzioni
3. Io pusho il fix della UI e dei commenti 39i. **Non serve restart orchestrator**: il bug è puramente browser-side + DB policy, nessun processo Python è coinvolto.

Dopo questo, il save su /tf farà quello che dice. Finalmente.

---

Se hai domande o qualcosa non ti è chiaro, fammi sapere. La prossima sessione è libera da impegni grossi: potremmo guardare 36h (Haiku che commenta anche il TF) o 36f (trailing stop) oppure semplicemente monitorare per qualche giorno prima di toccare altro codice.

A presto,
CC
