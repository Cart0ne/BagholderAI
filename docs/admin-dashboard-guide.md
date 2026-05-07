# Admin Dashboard — Legenda & Guida Operativa

**Audience:** Max (Board) — non tecnica, leggibile a freddo.
**Scope:** spiegare cosa significa ogni pannello, ogni numero, ogni regola sulla
dashboard `/admin` (Sentinel + Sherpa + DB Monitor).
**Data:** 2026-05-07 — sessione 63.

---

## 1. Cosa è ogni cervello

### Sentinel — il "termometro del mercato"
Sentinel è un processo Python che gira sul Mac Mini (managed dall'orchestrator,
loop ogni 60 secondi). Non fa trading. Si limita a osservare BTC/USDT su Binance
mainnet (prezzi reali, non testnet) e il funding rate dei futures, e ogni minuto
scrive una "fotografia" del mercato in DB:

- un **risk score** da 0 a 100 (quanto è pericoloso)
- un **opportunity score** da 0 a 100 (quanta opportunità c'è)

Tabella DB: `sentinel_scores` — una riga ogni 60s.

### Sherpa — il "consigliere di parametri"
Sherpa legge il risk score di Sentinel e propone parametri Grid (buy_pct,
sell_pct, idle_reentry_hours) coerenti col regime di mercato. Loop ogni 120s,
per ognuno dei 3 simboli (BTC/SOL/BONK) → fino a 3 proposte ogni 2 minuti.

In Sprint 1 Sherpa è in **DRY_RUN**: scrive le proposte in DB ma non aggiorna
mai `bot_config`. È in osservazione fino al 13-14 maggio. Tabella DB:
`sherpa_proposals`.

### Grid (i 3 bot esistenti)
Sono i bot di paper trading che fanno davvero buy/sell su Binance testnet.
Non sono visibili in `/admin` (li vedi su `/grid`). Quello che `/admin` ti
mostra è cosa **Sherpa avrebbe voluto dirgli** (ma in DRY_RUN non glielo dice).

---

## 2. Sezione SENTINEL — pannello "Last Scan"

### BTC PRICE
Il prezzo di BTC/USDT live, preso da Binance mainnet (`api.binance.com`).
Sotto in piccolo: `24h ±X%` con colore verde/rosso.

### BTC 1h
Variazione percentuale di BTC nell'ultima ora. Calcolata confrontando il prezzo
attuale con quello esattamente 1h fa nel buffer rolling di Sentinel. Verde se
positivo, rosso se negativo.

### Funding
Funding rate dei futures perpetuali BTC/USDT. È la commissione che long e short
si pagano ogni 8 ore. Lo prendiamo da `fapi.binance.com`.

- **Positivo** = i long pagano gli short → mercato sbilanciato a long → leverage
  pericoloso (rischio liquidazioni a cascata se il prezzo scende)
- **Negativo** = gli short pagano i long → potenziale short squeeze (= short
  costretti a chiudere comprando → spinta al rialzo)
- **Vicino a zero** (entro ±0.01%) = mercato bilanciato

Il valore è in formato decimale: `-0.0046%` significa che ogni 8h gli short
pagano lo 0.0046% della loro posizione ai long. È piccolo ma indicativo della
direzione del leverage.

Aggiornato ogni 8h dal Binance funding endpoint (cache 8h).

### Speed of fall (con pallino + counter)

Vedi 3 cose insieme:
- **Pallino**: rosso e luminoso quando il flag è ATTIVO ora, grigio spento
  quando è OFF
- **Label**: "ACCELERATING" o "stable"
- **Counter**: quante volte è scattato oggi (dalle 00:00 UTC)

#### Cosa significa veramente

Il flag scatta quando **la velocità di caduta sta accelerando**. Non è "BTC
sta crollando" — è "il calo dell'ultimo terzo dell'ora è almeno il 50% più
ripido della media oraria".

Formula esatta (da `bot/sentinel/price_monitor.py`):
```
ABS(calo_ultimi_20min) >= 1.5 * ABS(calo_intera_ora / 3)
AND calo_20min < 0  (cioè il movimento dev'essere ribassista)
```

#### Esempio concreto

BTC ha perso 0.3% in 1 ora.
- Media oraria attesa per ogni segmento di 20min: -0.1%
- Soglia di "accelerazione": 1.5 × 0.1% = 0.15%
- Se negli ultimi 20 minuti BTC ha perso >= 0.15% → **flag scatta**
- Se ha perso meno (es. 0.08%) → flag non scatta

#### Perché oggi scatta SO SPESSO (~30% del tempo)

In un mercato lateralizzato (BTC oscilla ±0.5% in poche ore), bastano fluttuazioni
di centesimi per soddisfare la disuguaglianza. **Il flag non ha una soglia
minima di "calo significativo"** — è puramente relativo. È un bug di calibrazione
noto, da rivedere post-replay counterfactual (~13 maggio). Per ora **ignoralo
come segnale di panico**: oggi non significa "BTC sta crashando".

---

## 3. Sezione SENTINEL — Risk score & Opportunity score

Sono due numeri da 0 a 100, calcolati da `bot/sentinel/score_engine.py`.

### Come si calcolano

Si parte da una **base** di 20 (sia per risk che per opp) e si applicano regole
che aggiungono punti.

```
risk_score = 20 (base)
            + 80 se BTC scende ≥10% in 1h         (drop ladder, solo 1 fires)
            + 50 se BTC scende ≥5%  in 1h
            + 30 se BTC scende ≥3%  in 1h
            + 20 se speed_of_fall_accelerating
            + 25 se funding > 0.05%               (long over-leveraged forte)
            + 15 se funding > 0.03%               (long over-leveraged debole)
            clampato a 100 max
```

```
opportunity_score = 20 (base)
                  + 40 se BTC sale ≥5% in 1h     (pump ladder, solo 1 fires)
                  + 25 se BTC sale ≥3% in 1h
                  + 25 se funding < -0.03%       (short squeeze forte)
                  + 15 se funding < -0.01%       (short squeeze debole)
                  clampato a 100 max
```

### Drop ladder vs Pump ladder = mutuamente esclusivi
Se BTC scende dell'8% in 1h, scatta solo `btc_drop_5pct_1h` (+50), non
`btc_drop_3pct_1h` (+30). Si applica **solo la regola più forte** che matcha.
Stessa cosa per i pump.

### Funding ladders = indipendenti dalle drop/pump
Funding può aggiungere risk (se positivo alto) O opportunity (se negativo
abbastanza), in parallelo ai drop/pump. Quindi un mercato che sale del 4% con
funding -0.04% darà sia `+25` opp da pump che `+25` opp da short squeeze =
opp 70.

### Perché oggi `risk = 40` e `opp = 20` quasi sempre

- BTC sta lateralizzando ±1% in 1h → niente drop ladder, niente pump ladder
- Funding tra -0.0046% e -0.0038% → mai sotto -0.01%, mai sopra 0.03% → niente
  funding ladder che scatti
- L'unica regola attiva è `speed_of_fall_accelerating` (+20 risk) che però è
  miscalibrata e scatta il 30% del tempo

→ risk_score si muove tra 20 (base) e 40 (base + speed flag). Niente sfumature
intermedie. Opportunity resta sempre a 20 per mancanza di trigger sufficienti.

**Conclusione operativa**: in regime di mercato attuale, Sentinel non discrimina
nulla di utile. È pronto a reagire ma non c'è materia per reagire. Se BTC
crollerà del 5% in un'ora, lo vedrai (risk salirà a 90+). Per ora è un
termometro su una giornata mite.

---

## 4. Sezione SENTINEL — 24h trend chart

Tre tracce sovrapposte:

1. **Linea rossa**: risk_score nel tempo (asse sinistro 0-100)
2. **Linea verde**: opportunity_score nel tempo (asse sinistro)
3. **Linea blu**: prezzo BTC nel tempo (asse **destro**, scalato dinamicamente
   per mostrare bene le oscillazioni)

Linee orizzontali tratteggiate sui threshold:
- Gialla a 50 = "rischio elevato"
- Rossa a 70 = "rischio alto, sistema dovrebbe reagire"

Linee verticali gialle tratteggiate = ogni volta che `speed_of_fall_accelerating`
è scattato (transizione da OFF a ON). Oggi ne vedi tante, sono il bug di cui
sopra.

### Come usarlo per cacciare bug
- Quando vedi un picco rosso ma BTC blu è piatto → sospetta calibrazione
- Quando BTC blu fa un picco lampo (wick) e Sentinel non reagisce → smoothing
  noto (Sentinel legge close 1m, non i wick)
- Se opp verde non si muove mai → soglie funding troppo larghe per il regime
  attuale (è il caso di oggi)

---

## 5. Sezione SHERPA — Last Proposals

Tabella con 3 righe (BTC, SOL, BONK) che mostra **per ogni bot**:

| Colonna | Cosa contiene |
|---|---|
| **Bot** | nome simbolo colorato (blu BTC, verde SOL, arancio BONK) |
| **Tu (current)** | parametri ATTUALI in `bot_config` (quelli che il Grid sta usando ora). Formato: `buy / sell / idle_h` |
| **Sherpa (proposed)** | parametri che Sherpa proporrebbe se fosse in `live` mode |
| **Regime** | regime attivo (oggi sempre `neutral`) |
| **Status** | badge con stato della proposta |

### Formato `buy / sell / idle_h`

- **buy** = `buy_pct`: percentuale di drop dal prezzo di riferimento per
  far scattare un acquisto. Es. `0.5` = compra quando BTC scende dell'0.5%.
- **sell** = `sell_pct`: percentuale di rialzo dal costo medio per far scattare
  una vendita. Es. `1.5` = vendi quando il lotto sale dell'1.5% sul prezzo
  d'acquisto.
- **idle_h** = `idle_reentry_hours`: dopo una vendita, quanto Grid aspetta
  prima di riconsiderare un nuovo buy sulla stessa coin. Es. `4.0h` = 4 ore.

### Status badges

- **⚠ diff (blu)**: Sherpa proporrebbe parametri DIVERSI da quelli attuali. In
  DRY_RUN non scrive nulla, ma sta segnalando "se fossi vivo cambierei". Oggi
  vedi questo su tutti e 3 i bot perché la `BASE_TABLE.neutral` di Sherpa
  (`buy=1.0 / sell=1.5 / idle=1.0h`) è diversa dai parametri Board fissi in
  `bot_config`.
- **🔒 cooldown (giallo)**: Sherpa è bloccato per evitare flicker
  (cambi continui troppo ravvicinati). Quando vedi questo, accanto vedi quali
  parametri sono lockati, es. `(buy_pct, sell_pct)`.
- **✓ aligned (verde)**: tutto in linea, niente da fare. Oggi non lo vedrai
  mai (vedi sopra).

### Perché tutti `⚠ diff`?
Vedi sezione 7 su `BASE_TABLE` per il dettaglio delle 5 voci. La calibrazione
"neutral" di Sherpa diverge dai parametri Board fissi → diff perpetuo. Se vuoi
che si allineino, o (a) cambi `bot_config` ai valori `neutral`, o (b) cambi
la `BASE_TABLE.neutral` ai valori `bot_config`. Decisione di design pendente.

---

## 6. Sezione SHERPA — Reaction chart

Stesso impianto del chart Sentinel ma incrocia DUE assi diversi:

- **Asse sinistro 0-100**: risk_score Sentinel (linea rossa)
- **Asse destro 0.3-3.0**: `proposed_buy_pct` di Sherpa, una linea per simbolo
  (BTC blu, SOL verde, BONK arancio)

### Cosa devi vedere

Quando il risk rosso sale, le 3 linee colorate **dovrebbero** muoversi (Sherpa
sta reagendo). Quando il risk è piatto, le 3 linee **dovrebbero** essere piatte.

Oggi (mercato calmo): tutto piatto = comportamento corretto. Quando BTC farà un
movimento vero (-3% in 1h), vedrai il risk rosso schizzare e le 3 linee
colorate salire/scendere in risposta.

È la **storia visibile della catena causale stimolo→risposta** del sistema.

---

## 7. Sezione SHERPA — Parameter rules (statiche)

Tre tabelle che spiegano **come Sherpa decide i parametri** (sono regole codate
in `bot/sherpa/parameter_rules.py`).

### Tabella 1: BASE_TABLE — i 5 regimi

```
extreme_fear:   buy 2.5  sell 1.0  idle 4.0h
fear:           buy 1.8  sell 1.2  idle 2.0h
neutral:        buy 1.0  sell 1.5  idle 1.0h    ← ATTIVO Sprint 1
greed:          buy 0.8  sell 2.0  idle 0.75h
extreme_greed:  buy 0.5  sell 3.0  idle 0.5h
```

Logica: in fear (mercato giù, paura) compri molto e con poca pretesa di profitto
per accumulare; in greed (mercato su, euforia) compri poco e vendi a profitto
alto. Sprint 1 usa **solo neutral** perché non abbiamo ancora il regime detector
(viene in Sprint 2 con F&G index + CMC dominance).

### Tabella 2: Adjustment ladders — deltas dinamici

Sono **modifiche additive** sopra la base, in funzione dei segnali fast (gli
stessi che usa Sentinel: drop, pump, speed_of_fall, funding). Esempio:

```
regime = neutral → base = buy 1.0 / sell 1.5 / idle 1.0h
+ btc_drop_5pct_1h scatta → +1.0 buy / -0.5 sell / +2.0 idle
= proposed: buy 2.0 / sell 1.0 / idle 3.0h
```

Logica: se BTC sta crollando, alzi `buy_pct` (compri solo se scende molto, sei
più cauto), abbassi `sell_pct` (vendi appena risale, prendi i soldi e scappi),
alzi `idle_reentry_hours` (aspetti prima di rientrare).

I 10 ladder sono nelle tabelle che vedi in dashboard. Drop e pump sono
mutuamente esclusivi (il più forte vince). Funding e speed_of_fall sono
indipendenti (si sommano agli altri).

### Tabella 3: RANGES — clamp assoluti

```
buy_pct:            min 0.3   max 3.0
sell_pct:           min 0.8   max 4.0
idle_reentry_hours: min 0.5   max 6.0
```

Anche se base + delta dovesse uscire dal range, viene tagliato a min/max. È
una rete di sicurezza per evitare valori impossibili in caso di bug nei delta.

---

## 8. Sezione SHERPA — Parameters history

3 mini-grafici impilati, ciascuno con la stessa scala temporale (24h) ma un
parametro diverso:

1. **buy_pct** (range 0.3-3.0)
2. **sell_pct** (range 0.8-4.0)
3. **idle_reentry_hours** (range 0.5-6.0)

Per ognuno, 3 linee colorate (BTC/SOL/BONK).

### Come usarlo

- Tracce piatte = Sherpa sta proponendo gli stessi parametri da 24h. Coerente
  con regime stabile.
- Trace che si separano improvvisamente = un signal ladder è scattato (drop o
  pump) e ha shiftato i parametri di un coin specifico
- Trace che oscillano nervosamente = flicker, possibile bug del cooldown
  manager (problema noto, da rivedere)

In Sprint 1 con regime sempre neutral e zero ladder che scatta, le tracce
sono perfettamente piatte. Quando Sprint 2 partirà col detector di regime, qui
vedrai i salti di buy_pct quando passi da neutral → fear → greed.

---

## 9. Sezione DB MONITOR

### Barra di utilizzo Supabase

Mostra MB usati su 500 MB del free tier. Colore della barra:
- **Verde** sotto 60%
- **Giallo** tra 60-90%
- **Rosso** oltre 90%

Oggi ~3.4% — siamo molto sotto. Il vincolo non sarà raggiunto a breve.

### Tabella "Top 8 tabelle per dimensione"

Per ogni tabella:
- **Rows** = quante righe contiene (count exact via Supabase REST)
- **Size** = quanti MB occupa (con indici)
- **Last activity** = quanto tempo fa l'ultima INSERT/UPDATE (es. "8s ago")

### Retention attiva (in nota sotto)

- Sentinel: 30 giorni (poi le righe vecchie vengono cancellate)
- Sherpa: 60 giorni
- Events log: 14 giorni
- Snapshots: 7 giorni

Cleanup automatico ogni notte alle 04:00 UTC via `db_maintenance.py`.

### Note importanti
- Le size sono uno **snapshot statico** preso da CC durante la pre-validation
  di stasera. Si aggiornano a ogni redeploy del sito (build time). Per averle
  realmente live serve creare una RPC Supabase custom — non fatto, basso
  beneficio.
- Le row counts invece sono live — chiamano l'endpoint REST con `Prefer:
  count=exact` ad ogni caricamento pagina.

### TODO futuro: sezione "Growth & Retention"
Da aggiungere in una sessione futura come miglioria di DB Monitor (~30 min).
Estende il pannello con:

- **Tasso di scrittura**: righe/min × tabella (calcolato sui `created_at`
  ultime 1h / 24h / 7gg)
- **Estrapolazione di crescita**: "se continuiamo così, satureremo 500 MB
  tra ~3 anni"
- **Salute retention**: confronto `rows attese vs rows reali` per ogni tabella
  con retention attiva (es. "Sentinel 30gg → atteso ~43.200 rows, attuale 1.534
  ✅"). Se discrepanza > 10%, marker `⚠ over` o `⚠ under`.

Costo zero (calcoli client-side). Beneficio: early warning se la retention
smette di funzionare (cleanup `db_maintenance.py` rotto), o se una tabella
inizia a esplodere senza retention configurata.

**Non collegato** a Supabase metrics IO/CPU/egress — quelle vivono nel pannello
supabase.com (Pro plan only $25/mese per Prometheus). Le ricostruiremmo solo
se diventeranno critiche e nessun alert email basta più.

---

## 10. Bug noti rilevati durante l'apertura della dashboard (sessione 63)

Conservati qui per memoria, formalizzati anche in `PROJECT_STATE.md` §5.

1. **`speed_of_fall_accelerating` miscalibrato**: scatta ~30% del tempo. Soglia
   relativa senza floor assoluto. Da rivedere post-replay (~13 maggio).
2. **Risk score binario (solo 20 o 40)**: conseguenza del #1. Niente sfumature
   intermedie in regime calmo.
3. **Opportunity score morta a 20**: soglie funding (-0.01%) troppo larghe per
   il regime attuale (-0.005%). Sentinel non vede mai opportunità.
4. **Grid polling rate troppo lento per BTC**: `check_interval_seconds = 60`
   per BTC (45 SOL, 20 BONK). Picchi wick sub-60s vengono persi. Soluzione
   eventuale: WebSocket Binance, parcheggiata "per quando guadagneremo
   milioni".

---

## 11. Per cosa NON serve la dashboard

- **Trading decision real-time**: i Grid bot non passano da qui. La dashboard
  è osservazione.
- **Modifica parametri**: read-only. Per cambiare costanti Sentinel/Sherpa
  serve edit codice + push + restart orchestrator (il workflow standard).
- **P&L del bot**: per quello c'è `/grid` e `/tf`. Qui non si parla mai di
  soldi guadagnati o persi.
- **Storia di tutti i trades**: per quello c'è il diary + dashboard pubblica
  `/dashboard`.

---

## 12. Quando consultarla

- Una volta al giorno per "vedere il termometro": è coerente con quello che
  vedo su Binance? Sentinel sta vedendo la realtà?
- Quando un bot Grid prende una decisione che ti sorprende: la dashboard ti
  dice cosa pensava Sherpa in quel momento → contesto utile.
- Prima di decidere `SHERPA_MODE → live` (target ~13-14 maggio): verifica che
  i 4 bug calibrazione siano stati risolti. Se non lo sono, **non promuovere
  Sherpa a live**.
- Quando il Board (tu) vuole "vedere l'AI vedere il mercato" senza chiedere a
  CC di fare query SQL.

---

*Generato 2026-05-07 — sessione 63. Aggiornare quando le rules cambiano o
quando aggiungiamo sezioni alla dashboard.*
