# Trend Follower (TF) — Recap per Max — S108 (2026-06-22)

> Documento di sola lettura, scritto per riprendere in mano il TF dopo settimane
> di focus su Sherpa/NewsKeeper/barometro. Linguaggio volutamente accessibile.
> **Tutti i valori qui sotto sono quelli LIVE** letti da `trend_config` su Supabase
> il 22-giu, non i default del codice (in diversi casi divergono).

---

## In una frase

Il TF è il **talent scout** del sistema: ogni 30 minuti passa in rassegna le 50
monete più scambiate su Binance, cerca quelle in **trend rialzista pulito**, e
quando ne trova una buona la **assegna a un grid bot** che poi la fa lavorare.
Oggi il TF *non gestisce trade in proprio*: seleziona e passa la palla al Grid.

---

## 1.1 Come funziona oggi

### Cosa scansiona, quante, ogni quanto
- **Universo:** le **top 50** monete per volume scambiato in 24h su Binance
  (esclude le stablecoin). Parametro: `scan_top_n = 50`.
- **Frequenza:** **ogni 30 minuti** (`scan_interval_hours = 0.5`). ⚠️ Il default
  nel codice è 4 ore, ma il valore vero in produzione è 0.5h.
- **Dati usati:** candele a **4 ore** (le ultime 100), da cui calcola gli indicatori.

### Come decide il segnale (BULLISH / BEARISH / SIDEWAYS / NO_SIGNAL)
Guarda 3 cose su ogni moneta:
- **EMA 20 vs EMA 50** (media veloce vs media lenta = direzione del trend)
- **RSI 14** (forza/slancio: sopra 50 = compratori in controllo)
- **ATR 14** (volatilità: quanto si muove la moneta)

La logica (semplificata):
| Condizione | Segnale |
|---|---|
| ATR ≤ media ATR (mercato troppo piatto) | **NO_SIGNAL** (si scarta) |
| EMA20 > EMA50 **e** RSI > 50 | **BULLISH** (trend su) |
| EMA20 < EMA50 **e** RSI < 50 | **BEARISH** (trend giù) |
| EMA vicine (<0,5%) **oppure** RSI tra 45 e 55 | **SIDEWAYS** (laterale) |

Solo i **BULLISH** sono candidati all'acquisto. La "forza" del segnale =
`|RSI−50| + (ATR/ATR medio)`; serve almeno **15** (`min_allocate_strength`) per
essere preso in considerazione.

### Filtri di sicurezza (tutti ATTIVI oggi)
Prima di allocare, un candidato BULLISH deve passare anche:
- **Non troppo lontano dalla media:** prezzo entro **+12%** dalla EMA20
  (`tf_entry_max_distance_pct = 12`) → evita di comprare su uno strappo già esploso.
- **Non surriscaldato:** RSI a 1 ora sotto **75** (`tf_rsi_1h_max = 75`).
- **Niente rientro lampo dopo uno stop:** dopo uno stop-loss aspetta **4 ore**
  prima di riconsiderare quella moneta (`tf_stop_loss_cooldown_hours = 4`).

### ALLOCATE vs HOLD — e il passaggio al Grid
- **ALLOCATE** (nuova posizione): la moneta è BULLISH, non è già attiva, passa
  tutti i filtri, c'è budget nella sua fascia. Il TF può tenere al massimo
  **3 monete** contemporaneamente (`tf_max_coins = 3`).
- **HOLD:** moneta già attiva che resta BULLISH/SIDEWAYS → si tiene.
- **Il punto chiave — l'handoff TF→Grid:** quando il TF alloca una moneta, la
  "etichetta" in base al volume:
  - Fascia 1 e 2 (volume ≥ $20M) → `managed_by = "tf_grid"`: **il Grid prende in
    gestione** compra/vendi; il TF l'ha solo *scelta*.
  - Fascia 3 (volume < $20M) → `managed_by = "tf"`: gestita dal TF dall'inizio
    alla fine.
- **MA oggi la Fascia 3 è SPENTA** (`tf_tier3_weight = 0`, da S79b). Conseguenza
  importante: **tutto ciò che il TF alloca finisce in `tf_grid`**, cioè in mano al
  Grid. Per questo nei report leggi "il TF non ha tradato questo ciclo": è vero
  nel senso che non gestisce trade in proprio — fa lo scout e delega. ETH/USDT
  (il primo handoff reale, 15-giu) è esattamente questo: `managed_by = tf_grid`.

---

## 1.2 I parametri che vedi sulla dashboard (admin config TF)

- **BUY %** — di quanto deve scendere il prezzo perché il bot ricompri un altro
  lotto. **Non è fisso: lo calcola il TF** in base alla volatilità (ATR) della
  moneta — più è volatile, più largo. Viene **riscritto a ogni allocazione**.
- **SELL %** — il take-profit, cioè di quanto deve salire il prezzo per vendere.
  Anche questo lo calcola il TF (vedi greed decay, §1.4). **Se lo modifichi a mano
  viene sovrascritto** alla prossima allocazione, perché il valore "vero" vive
  nella curva `greed_decay_tiers`, non nella riga del singolo bot.
- **MIN PROFIT %** — sui bot TF è **sempre 0**. Il TF non usa una soglia minima di
  profitto fissa: la sua protezione è la combinazione greed-decay + stop-loss
  (vedi §1.4), non un floor statico.
- **IDLE RE-ENTRY** — dopo quante ore di inattività il bot "ricalibra" il prezzo di
  riferimento (per non restare ancorato a un prezzo vecchio). Vive in `bot_config`
  per singola moneta.
- **Fixed Grid (vuoto)** — il TF **non usa la griglia tradizionale** a livelli
  fissi. Lavora a "lotti" su trend, non a gradini predefiniti, quindi questo campo
  resta vuoto.

---

## 1.3 Meta-parametri vs Output — cosa Sherpa può o non può toccare

Questa è la distinzione che ti serve per decidere cosa dare in pancia a Sherpa.

### OUTPUT — calcolati dal TF, riscritti a ogni allocazione → **Sherpa NON può gestirli**
Se Sherpa li modificasse, il TF glieli sovrascriverebbe al primo scan. Sono:
- **buy_pct**, **sell_pct** (le soglie compra/vendi)
- capitale per moneta e per lotto, numero di lotti iniziali

### META-PARAMETRI — governano *come* il TF calcola → **potenzialmente di Sherpa**
Cambiarli sposta il comportamento di tutte le monete, prospetticamente. Sono:
| Meta-parametro | Valore live | Cosa fa |
|---|---|---|
| `greed_decay_tiers` | 10%→7%→5%→3% (vedi §1.4) | la curva del take-profit nel tempo |
| `atr_multiplier_*` | up 3.0 / down 1.0 / sideways 1.5 | quanto largo calcolare buy/sell dall'ATR |
| `tf_stop_loss_pct` | 2.5% | soglia di stop-loss |
| `tf_entry_max_distance_pct` | 12% | quanto lontano dalla EMA si può entrare |
| `tf_rsi_1h_max` | 75 | filtro anti-surriscaldamento |
| `tf_stop_loss_cooldown_hours` | 4 | pausa dopo uno stop |
| `min_allocate_strength` | 15 | quanto forte dev'essere il segnale |
| `idle_reentry_hours` | (per-moneta in bot_config) | timeout ricalibrazione |

> Nota progettuale: gli output sono "di proprietà" del TF, i meta-parametri sono
> "politica". Sherpa può ragionevolmente possedere la politica, non gli output.

---

## 1.4 Stop loss e Greed decay

### Stop loss — **fisso**
Il TF usa uno stop-loss **fisso** al **2,5%** (`tf_stop_loss_pct`): se una posizione
gestita dal TF (`managed_by='tf'`) va sotto −2,5%, esce. ⚠️ Ma le monete `tf_grid`
(Fascia 1-2, le uniche attive oggi) **non usano questo stop**: passano alla logica
del Grid, dove a proteggere è il **Profit Lock** (blocca il guadagno sopra una
soglia, `tf_profit_lock_pct = 8%`) più trailing stop (attivazione 1,5%, scia 2%).

### Greed decay — il take-profit che si "ammorbidisce" nel tempo
È il meccanismo più caratteristico del TF. La curva live (`greed_decay_tiers`):

| Da quando è entrato | Take-profit richiesto |
|---|---|
| primi 10 minuti | **10%** |
| dopo 20 minuti | **7%** |
| dopo 30 minuti | **5%** |
| dopo 60 minuti | **3%** |

Si legge così: appena entrato il bot è **avido** (vuole un +10% per vendere). Più
passa il tempo senza che il prezzo esploda, più **molla la presa** e si accontenta
(fino a +3%). È la "greed" (avidità) che **decade**. Razionale: i trend buoni
corrono subito; se dopo un'ora non è successo niente, meglio incassare poco che
restare incastrati.

Il valore di `sell_pct` scritto a fine curva = `MAX(ultimo_tier − 0,5%, 0,3%)` =
`MAX(3 − 0,5; 0,3)` = **2,5%**.

---

## Foto dello stato attuale (22-giu)
- TF **abilitato e LIVE** (`trend_follower_enabled = True`, `dry_run = False`),
  budget **$100**, max **3** monete, **Fascia 3 spenta**.
- In pratica fa **solo da scout** per il Grid (ogni allocazione → `tf_grid`).
- Unica posizione passata al Grid in questo ciclo: **ETH/USDT** (15-giu).

*(Vedi anche `docs/grid_mainnet_tf_testnet_assessment.md` per la verifica
architetturale grid-mainnet / TF-testnet.)*
