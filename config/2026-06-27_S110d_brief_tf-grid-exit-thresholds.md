# Brief S110d — tf-grid-exit-thresholds — 2026-06-27

> **CORRETTO S110 (2026-06-27).** La prima stesura partiva da una premessa
> sbagliata ("oggi il TF non guarda il P&L"). Falso: verificato a DB + codice,
> esistono già meccanismi di uscita P&L-aware ATTIVI sulle coin tf_grid. Questo
> brief è stato riscritto con le decisioni Board+Max del 2026-06-27 e la
> riconciliazione con il codice esistente. **Pronto per esecuzione** (rimandata
> di qualche giorno: task impattante, non un gate per la fase collaudo €100).

## Contesto (corretto)

Le coin **tf_grid** (Tier 1-2, selezionate dal TF ma gestite dal GRID) hanno
GIÀ tre meccanismi di uscita attivi, verificati il 2026-06-27:

| Meccanismo | Stato | Comportamento | File |
|---|---|---|---|
| **DEALLOCATE su BEARISH** | attivo | esce quando il segnale gira negativo — **anche in perdita** | `allocator.py:345-375` |
| **SWAP / rotazione** | attivo | ruota verso una coin più forte (delta +25 forza, cooldown 48h) **solo se non in perdita** (`SWAP_TF_GRID_MIN_PROFIT_PCT=0.0`) | `allocator.py:389-560` |
| **Profit Lock** | attivo a **+8%** (`tf_profit_lock_enabled=true`, `tf_profit_lock_pct=8`) | take-profit secco: locka/esce a +8% | `trend_config` + `allocator.py:1207+` |

Il **problema reale** (non "manca la logica P&L", ma "la logica esistente è
mal calibrata"):
1. Il `DEALLOCATE-on-BEARISH` esce **anche in perdita** → vende coin Tier 1-2
   in rosso senza necessità (il grid potrebbe aspettare il recupero).
2. Il Profit Lock secco a +8% **non lascia correre** i trend forti e si
   sovrappone alla logica di rotazione.
3. Lo SWAP ruota anche con profitto ~0 → churning su micro-upgrade.

## Scope

Riconciliare i meccanismi esistenti in **un'unica logica di uscita P&L-aware**
per le coin tf_grid, secondo la tabella Board sotto. **Nessuna riscrittura**:
sono modifiche mirate ai gate esistenti + disattivazione del Profit Lock.

## Decisioni Board + Max (2026-06-27)

- **D1 — Profit Lock: SOSTITUITO.** Disattivare `tf_profit_lock_enabled` (→ false
  in `trend_config`). Le regole sotto diventano l'**unico** sistema di uscita
  P&L-aware per le tf_grid. (Niente più take-profit secco a +8%.)
- **D2 — Soglia "in verde" = NETTA.** "Verde" significa profitto che copre già
  le fee di round-trip (~0.2% testnet) + margine slippage → soglia parametrica
  `~+0.3–0.5%`, **non** il +0.1% lordo della prima stesura (a +0.1% lordo si è
  in perdita netta). Rende onesto il principio "mai uscire in perdita".
- **D3 — "Mai uscire in perdita" = ASSOLUTO.** Nessun paracadute / stop
  catastrofico. Se in perdita, la coin si TIENE qualunque sia il segnale; il
  grid lavora e aspetta. Il rischio coin-zombie (declino strutturale tipo LUNA)
  è **accettato** e sarà coperto dal Portfolio Guardian (post-mainnet).
- **D4 — Rotazione = "let winners run".** Sopra +5% NON si vende sempre: la coin
  diventa **candidata a rotazione** e si vende **solo se** c'è un upgrade di
  trend vero (riusa la soglia SWAP `+25` forza). Altrimenti TIENE e lascia
  correre. Niente hard take-profit a +5%.
- **D5 — RUOTA e SWAP UNIFICATI.** Un solo meccanismo di rotazione (lo SWAP
  esistente), non due. Anti-churning: si **riusa** il cooldown 48h già presente
  + si **esclude la coin appena venduta** per la durata del cooldown.
- **D6 — Soglie TUNABILI A CALDO (parametri, non costanti).** La soglia di
  rotazione (default **+5%**) e la soglia-verde (default ~**+0.3%**) vivono in
  `trend_config` (come `tf_profit_lock_pct` & co.), **non** come costanti
  hardcoded. Il TF rilegge `trend_config` a ogni scan → cambiarle in test
  (es. rotazione 5%→8%) = **UPDATE al DB, hot-reload, nessun restart**.
  Costo: 2 colonne nuove in `trend_config` (migration). Motivo: vogliamo poter
  sperimentare le soglie a caldo durante il collaudo, senza toccare il codice.

## Regole riconciliate (Board-approved)

P&L = P&L **netto fee** della posizione tf_grid (vedi "Calcolo" sotto).

| P&L posizione (netto) | Segnale trend | Azione | reason log |
|---|---|---|---|
| in perdita **o** ≤ soglia-verde | qualsiasi | **TIENE** (mai uscire in perdita) | `held_in_loss` |
| > soglia-verde, ≤ +5% | negativo | **ESCI** (blocca il profitto) | `signal_exit_green` |
| > soglia-verde, ≤ +5% | positivo | **TIENE** | `trend_positive_hold` |
| > +5% | positivo | **TIENE + candidata SWAP** (ruota solo se +25 forza) | `profit_rotation` (se ruota) / `trend_positive_hold` (se tiene) |
| > +5% | negativo | **ESCI** (incassa il profitto prima che evapori) | `signal_exit_green` |

**Principio:** si esce SOLO in verde netto. In perdita non si esce mai. Sopra
+5% in trend positivo si lascia correre, ruotando solo per un upgrade reale.

## Cosa fare (implementazione riconciliata — minimale)

### 1. Calcolo P&L netto per coin tf_grid
- P&L = (valore mercato holdings + realized da sell, già al netto delle fee
  pagate) − costo totale acquisti. Percentuale = P&L / costo acquisti × 100.
- I dati ci sono già nel grid (avg_cost, managed_holdings, realized_pnl per
  coin — gli stessi delle dashboard S110a/b). Riusare, non ricalcolare.
- **Verde netto**: confrontare il P&L% con `soglia-verde` = fee round-trip +
  margine. Parametrizzare (`tf_grid_exit_min_green_pct`, default ~0.3%); su
  mainnet rivedere col fee reale (eventuale sconto BNB).

### 2. DEALLOCATE-on-BEARISH → aggiungere il gate "verde netto"
- Oggi (`allocator.py:345-375`): segnale BEARISH → DEALLOCATE incondizionato.
- Nuovo: DEALLOCATE su BEARISH **solo se** P&L netto > soglia-verde. Se in
  perdita/≤soglia → NON dealloca, log `held_in_loss`. (Questo è il fix #1.)

### 3. SWAP → min-profit gate a +5%, come PARAMETRO di config (non costante)
- Oggi `SWAP_TF_GRID_MIN_PROFIT_PCT = 0.0` è una **costante hardcoded**
  (`allocator.py:54`, "CEO-locked constants" — cambiarla = codice + restart).
- Nuovo: introdurre `trend_config.tf_grid_rotation_min_profit_pct` (default
  **5.0**), letto a runtime al posto della costante per le tf_grid → tunabile a
  caldo (D6: 5→8 = UPDATE DB, hot-reload, zero restart). Resto invariato:
  `SWAP_TF_GRID_STRENGTH_DELTA=25`, `SWAP_TF_GRID_COOLDOWN_HOURS=48`,
  esclusione coin venduta (verificare che il cooldown già la escluda; se no,
  aggiungere l'esclusione esplicita per 48h).

### 4. Profit Lock → disattivare
- `trend_config.tf_profit_lock_enabled = false`. Verificare che il path
  `allocator.py:1207+` non lasci comportamenti residui quando off.

### 5. Logging esplicito
- Ogni decisione tf_grid scrive il `reason` della tabella sopra in
  `trend_decisions_log` (`profit_rotation`, `signal_exit_green`,
  `held_in_loss`, `trend_positive_hold`). Serve per classificare bug-vs-perdita
  nel go-live experiment (telemetria attribuibile, vedi APPROVED golive §5).

## Test checklist

- [ ] P&L > +5%, trend positivo, esiste coin +25 più forte → **ruota** (`profit_rotation`)
- [ ] P&L > +5%, trend positivo, nessun upgrade → **tiene** (let winners run, `trend_positive_hold`)
- [ ] P&L > +5%, trend negativo → **esce** (`signal_exit_green`)
- [ ] P&L +2% (verde netto), trend negativo → **esce** (`signal_exit_green`)
- [ ] P&L +2%, trend positivo → **tiene** (`trend_positive_hold`)
- [ ] P&L +0.1% (sotto soglia-verde netta, in perdita netta) → **tiene** (`held_in_loss`)
- [ ] P&L −3%, trend negativo → **tiene** (mai uscire in perdita, `held_in_loss`)
- [ ] Dopo rotazione: coin venduta esclusa dal riscan per 48h; nuova coin allocata
- [ ] Profit Lock OFF: nessuna uscita a +8% non spiegata dalle regole sopra
- [ ] reason corretto loggato per ogni scenario

## File OFF-LIMITS

- `bot/grid_runner/` — la logica grid non cambia, cambia solo QUANDO il TF
  chiede la deallocation.
- `bot/sentinel/`, `bot/sherpa/` — non coinvolti.

## Auto-obiezioni (aggiornate)

1. **Soglia +5% arbitraria + churning.** Con "let winners run" (D4) il rischio
   di vendere-presto è risolto (sopra +5% si tiene, non si vende). Il churning
   residuo (ruota A→B, A poi vola) è mitigato dal cooldown 48h + esclusione
   della coin venduta (D5). Resta il caso "ruoti verso B e B scende": accettato,
   è il costo di qualsiasi rotazione trend-following.
2. **"Mai uscire in perdita" tiene una coin in declino strutturale (LUNA).**
   Rischio accettato (D3). Le Tier 1-2 tendono a recuperare; il caso patologico
   lo coprirà il Portfolio Guardian (post-mainnet, livello portafoglio).
3. **Soglia-verde netta dipende dal fee reale.** Su testnet fee 0.1%/lato; su
   mainnet può cambiare (sconto BNB). Parametrizzata (§1) e da rivedere
   pre-mainnet col fee effettivo, per non vendere "in verde" ciò che è in
   pareggio netto.
4. **Pochi dati live oggi.** C'è 1 sola coin tf_grid (ETH, peraltro
   capital-exhausted). La logica gira su pochissimi casi reali finché il TF non
   alloca dinamicamente nel deployment €600. Collaudare con scenari simulati.

## Sequenza

Indipendente da S110c. Da completare **PRIMA del deployment €600** (quando il TF
sarà attivo con coin dinamiche). **NON è un gate per la fase collaudo €100.**
Esecuzione rimandata di qualche giorno (decisione Max, 2026-06-27).
