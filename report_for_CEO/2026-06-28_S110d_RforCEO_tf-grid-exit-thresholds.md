# RforCEO — tf-grid-exit-thresholds — 2026-06-28 (sessione estemporanea)

**Brief sorgente:** `config/2026-06-27_S110d_brief_tf-grid-exit-thresholds.md`
**Commit:** `4b9a3ed` (codice + test) · **Migration:** applicata a prod `trend_config` (3 colonne)
**Stato:** SHIPPED in repo · ⚠️ **RESTART PENDING** (non live finché non si riavvia il Mac Mini)
**Autorizzazione:** Board (Max). CEO informato con questo report (decisione Max).

---

## 1. In una riga
Le coin **tf_grid** ora hanno come uscite automatiche **solo** un **trailing stop** (protezione sul prezzo, al minuto) + la **rotazione** SWAP. Il **Profit Lock +8% è rimosso** per le tf_grid. **Nessuna uscita su segnale bearish.** "Mai uscire in perdita" resta assoluto.

## 2. ⚠️ Deviazione dal brief — da leggere
Il brief chiedeva un'uscita **su segnale** (`signal_exit_green`: esci sul bearish quando sei in verde-netto) + rimozione Profit Lock + rotazione tunabile. **Abbiamo deviato** dopo il brainstorming con Max:

- **Sostituito `signal_exit_green` con un TRAILING STOP** (protezione sul prezzo, non sul segnale).
- **Rimossa del tutto la logica di uscita su bearish.**

**Perché.** In sede di verifica del codice sono emerse **3 discrepanze brief↔repo** (il brief, pur già corretto una volta, partiva ancora da premesse sbagliate):

1. **La premessa #1 del brief era invertita.** Il brief diceva che oggi il `DEALLOCATE-on-BEARISH` vende le tf_grid *anche in perdita* e che serviva "frenarlo". **Falso:** il codice (`allocator.py:362-377`) **ignora** il bearish per le tf_grid (le tiene, il grid lavora). Non c'era una vendita da frenare — semmai una da introdurre.
2. **Profit Lock non era dove diceva il brief** (`allocator.py:1207+`): vive in `grid_bot.py`.
3. **L'interruttore per spegnerlo non funzionava** per le tf_grid: una clausola `or managed_by=='tf_grid'` lo forzava sempre ON, ignorando `tf_profit_lock_enabled`.

Su questa base Max ha scelto la **protezione sul prezzo** perché *il segnale bearish è strutturalmente lento* (medie mobili/RSI confermano il ribaltone con ore di ritardo): "esci ASAP sul bearish" non è davvero rapido. Il trailing reagisce al minuto e batte sempre il segnale → l'uscita su bearish diventa ridondante. Risultato: **più semplice e più reattivo** del brief.

## 3. Decisioni (formato decision-log)

**DECISIONE:** Trailing stop (price-based) al posto dell'uscita su segnale per le tf_grid; nessuna uscita su bearish.
**RAZIONALE:** Il bearish è laggy; il trailing protegge i guadagni al minuto senza tappare l'upside (let winners run). Coerente con lo scopo del TF (cavalcare i winner) e con "mai uscire in perdita".
**ALTERNATIVE:** (A) `signal_exit_green` come da brief — scartata (lenta); (C) tenere il Profit Lock alzandolo a +15-20% — scartata (resta un tetto).
**FALLBACK:** Soglie tunabili a caldo (vedi sotto); se il trailing si rivela troppo stretto/largo, si cambia da DB senza restart. Se servisse ripristinare il Profit Lock per le tf_grid, è un revert mirato di 3 righe in `grid_bot.py`.

**DECISIONE:** Soglie del trailing: **arma a +5%, esce a −4% dal picco**.
**RAZIONALE:** Caso peggiore (arma esatto a +5% e gira subito) → uscita a ~+0.6% netto, **ancora verde** (rispetta "mai in perdita"). +4% lascia respiro al trend senza farsi scuotere dal rumore.
**ALTERNATIVE:** trail 3% (più stretto, più whipsaw); >4.8% rischia l'uscita in rosso (vietato).
**FALLBACK:** entrambe le soglie tunabili a caldo da `trend_config`.

## 4. Modello finale — uscite di una coin tf_grid
Sopra al normale lavoro del grid (compra dip, vende ai suoi trigger):

| Situazione | Azione |
|---|---|
| In perdita (netto) | TIENE sempre — mai uscire in rosso |
| In verde + coin nettamente più forte (+25, 48h, stesso tier) | RUOTA (SWAP) |
| Picco ≥ +5%, poi −4% dal picco | TRAILING EXIT (a cassa, al minuto) |
| In verde, sale/tiene, nessun upgrade | TIENE e lascia correre |

## 5. Cosa è cambiato nel codice (commit `4b9a3ed`)
- **`grid_bot.py`** — trailing stop esteso a `tf_grid` (era `managed_by=='tf'`); Profit Lock ora **pure-TF only** (gate `managed_by=='tf'`, tf_grid mai).
- **`grid_runner/__init__.py` + `config_sync.py`** — le tf_grid leggono soglie trailing **proprie** (più larghe) da `trend_config`; i TF puri restano sulle colonne `tf_trailing_*` (invariati).
- **`allocator.py`** — soglia profitto della rotazione: da costante `0.0` a parametro `trend_config.tf_grid_rotation_min_profit_pct` (default 0.5%, proxy "verde netto"). +25 forza / 48h cooldown invariati.
- **`config/supabase_config.py`** — **fix latente:** aggiunte le colonne trailing alla whitelist `_TREND_CONFIG_FIELDS` (senza, l'hot-reload del trailing era di fatto morto). Ora le soglie sono **tunabili a caldo** (D6 del brief).

**Migration prod `trend_config`** (+3 colonne, default = comportamento sicuro):
`tf_grid_trailing_activation_pct=5.0`, `tf_grid_trailing_stop_pct=4.0`, `tf_grid_rotation_min_profit_pct=0.5`.

## 6. Cosa NON è cambiato
- Ramo "segnale BEARISH" dell'allocator per le tf_grid → resta "ignora/tieni".
- Comportamento dei **TF puri** (stop-loss, take-profit, trailing 1.5/2, Profit Lock) → **intatto** (verificato: per `managed_by=='tf'` il gate è identico a prima).
- Trading normale del grid e `grid_runner` core.
- Il *gain-saturation breaker* (esci-dopo-N-vendite): è `managed_by=='tf'` → **non tocca le tf_grid** (verificato; era un dubbio del piano, chiuso).

## 7. Test
**257/257 verdi** (250 baseline + **7 nuovi** in `tests/test_tf_grid_exit_s111.py`): routing colonne tf_grid vs TF puro; trailing arma a +5% ed esce a −4% in verde; Profit Lock OFF per tf_grid ma ON per TF puro; mai uscita in perdita (gate di armamento). `py_compile` OK su tutti i file.

## 8. Caveat / aperti
- **Pochi dati live:** 1 sola tf_grid oggi (ETH, capital-exhausted) → collaudo su unit test + scenari simulati finché il TF non alloca dinamicamente nel deployment €600.
- **Picco in memoria:** il trailing dimentica il picco a un restart e si ri-arma dal prezzo corrente (conservativo, accettato).
- **Verde-netto approssimato** sulla rotazione: soglia 0.5% sull'unrealized lordo come proxy del netto (semplice, tunabile). L'opzione precisa (unrealized+realized−fee) è più codice; rimandata se i dati lo richiederanno.
- **Restart:** non live finché il Mac Mini non viene riavviato (regola §5 — solo su richiesta di Max).

## 9. Sequenza
Indipendente da S110c (USDC). **Non gate per il collaudo €100.** Da completare prima del deployment €600 (fatto). Restart a discrezione di Max.
