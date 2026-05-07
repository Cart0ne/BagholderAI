# Sherpa Parameter Rules — Guida Operativa

**Audience:** Max (Board) — non tecnica, leggibile a freddo.
**Scope:** spiegare cosa significano le 3 tabelle "Sherpa parameter rules"
nella dashboard `/admin`, con esempi numerici concreti.
**Data:** 2026-05-07 — sessione 63.
**Source codice:** `bot/sherpa/parameter_rules.py` + `bot/sherpa/cooldown_manager.py`.

---

## TL;DR

Sherpa è un cervello (Brain #4) che ogni 120 secondi guarda lo stato del mercato
(via `sentinel_scores`) e decide **3 parametri** per ogni Grid bot:
`buy_pct`, `sell_pct`, `idle_reentry_hours`. Per farlo applica una formula a
2 strati:

```
parametro_finale = base[regime] + Σ delta_i(segnali_fast)
                   poi clampato dentro RANGES
```

Le 3 tabelle che vedi su `/admin` sono i 3 ingredienti di questa formula:
1. **BASE_TABLE** — cosa Sherpa proporrebbe se il mercato fosse "normale" (5 regimi)
2. **Adjustment ladders** — come Sherpa modifica la base se il mercato si muove (10 deltas)
3. **RANGES** — limiti assoluti che NESSUNA combinazione può superare (3 clamps)

In Sprint 1 (oggi) Sherpa è in **DRY_RUN** + usa **solo regime "neutral"** + non
ha ancora il regime detector → quindi Sprint 1 è di fatto: `1.0 / 1.5 / 1.0h` +
eventuali deltas dei 10 ladder. Sprint 2 (futuro) attiverà il rilevatore di
regime e userà tutte e 5 le righe della BASE_TABLE.

---

## 1. Cosa sono i 3 parametri

Te li spiego prima dei numeri perché senza capire questi, le tabelle non
significano niente.

### 1.1 buy_pct — "quanto deve scendere prima che io compri"

Quando il Grid bot tiene una coin, calcola il prezzo medio dei lotti in
portafoglio. Se il prezzo attuale scende del `buy_pct%` rispetto a quel
riferimento, Grid compra un nuovo lotto.

**Esempio**: BTC media in portafoglio = $80.000, `buy_pct = 1.0`. Quando BTC
scende a $79.200 (= -1.0%), Grid compra un altro lotto.

**Significato strategico**:
- `buy_pct` **basso** (es. 0.5) = compra spesso, accumula aggressivamente
- `buy_pct` **alto** (es. 2.5) = compra raramente, solo a forti ribassi

In **mercato in caduta** vuoi `buy_pct` alto (non comprare a un prezzo che
domani scenderà ancora). In **mercato che sta toccando il fondo** vuoi
`buy_pct` basso (accumula al minimo prima del rimbalzo).

### 1.2 sell_pct — "quanto deve salire un lotto prima che io venda"

Quando un lotto specifico (FIFO) sale del `sell_pct%` sopra il suo prezzo
d'acquisto, Grid lo vende.

**Esempio**: lotto comprato a $80.000, `sell_pct = 1.5`. Quando BTC sale a
$81.200 (= +1.5%), Grid vende quel lotto.

**Significato strategico**:
- `sell_pct` **basso** (es. 1.0) = vende presto, prendi piccoli profitti spesso
- `sell_pct` **alto** (es. 3.0) = aspetta profitti grandi, lotti restano aperti più a lungo

In **mercato che sale forte** vuoi `sell_pct` alto (non venire venduto fuori
da un trend al primo +1%). In **mercato volatile** vuoi `sell_pct` basso
(prendi i profitti finché ci sono).

### 1.3 idle_reentry_hours — "quanto aspetto dopo aver venduto"

Dopo che Grid vende un lotto, c'è un periodo di "raffreddamento" prima di
considerare un nuovo buy. Se il prezzo torna giù subito dopo la vendita,
Grid NON ricompra finché non sono passate `idle_reentry_hours`.

**Esempio**: Grid vende un lotto BTC alle 10:00, `idle_reentry_hours = 4.0`.
Anche se BTC scende del 2% alle 10:30, Grid non comprerà finché non saranno
passate le 14:00.

**Significato strategico**:
- `idle_reentry` **basso** (es. 0.5h) = riprendi presto, sei pronto a re-tradare la stessa fascia
- `idle_reentry` **alto** (es. 4.0h) = aspetta il prossimo "vero" movimento

Serve a evitare di **comprare-vendere ping-pong** in un range stretto, dove
le commissioni mangiano tutto il profitto.

---

## 2. Tabella 1 — BASE_TABLE (5 regimi)

```
Regime          | buy_pct | sell_pct | idle_reentry_h
----------------|---------|----------|----------------
extreme_fear    |   2.5   |   1.0    |     4.0
fear            |   1.8   |   1.2    |     2.0
neutral         |   1.0   |   1.5    |     1.0    ← ATTIVO Sprint 1
greed           |   0.8   |   2.0    |     0.75
extreme_greed   |   0.5   |   3.0    |     0.5
```

### 2.1 Cosa è un "regime"

È l'**umore del mercato** in un certo momento. È un'astrazione che riassume
tante metriche (Fear & Greed Index, BTC dominance, volatilità, andamento
storico) in 5 categorie.

In Sprint 2, Sherpa avrà un detector che decide automaticamente in che regime
siamo. Per ora (Sprint 1), il detector non c'è — il regime è hardcoded a
`neutral`.

### 2.2 Logica delle 5 righe

Leggile come **una matrice di reazione contro-ciclica**:

- **extreme_fear** (mercato in panico):
  - `buy_pct = 2.5`: compra solo a forti ribassi (alta selettività, paghi prezzi davvero bassi)
  - `sell_pct = 1.0`: vendi al primo rimbalzo (prendi profitti rapidi)
  - `idle = 4.0h`: aspetta che la situazione si calmi prima di ricomprare
  - Filosofia: **accumula al minimo, vendi al primo rimbalzo, aspetta tra cicli**

- **fear** (mercato preoccupato):
  - Versione attenuata di extreme_fear

- **neutral** (mercato normale):
  - `buy_pct = 1.0 / sell_pct = 1.5 / idle = 1.0h`
  - Bilanciato: compra a ribassi moderati, vendi a profitti moderati, ricomincia presto
  - Filosofia: **comportamento medio, niente di speciale**

- **greed** (mercato euforico):
  - Versione attenuata di extreme_greed

- **extreme_greed** (mercato in bolla):
  - `buy_pct = 0.5`: compra anche a piccoli ribassi (perché il prezzo continua a salire, non aspettare crolli)
  - `sell_pct = 3.0`: aspetta profitti grossi (lascia correre i trend)
  - `idle = 0.5h`: ricomincia subito (sei in pieno trend, ogni minuto perso è P&L mancato)
  - Filosofia: **stai dentro il trend rialzista, lascia correre i lotti**

### 2.3 Perché Sprint 1 usa solo neutral

`bot/sherpa/parameter_rules.py` riga 12:

```python
# In Sprint 1 only the adjustment layer is active: regime is hardcoded to "neutral".
```

Sherpa Sprint 1 NON ha modo di sapere in che regime siamo. Manca il "slow
loop" che leggerà Fear & Greed Index, CMC dominance, regime detector logic.
Quello arriverà in Sprint 2 (post-replay counterfactual, dopo ~13 maggio).

→ **Oggi Sherpa parte sempre da `1.0 / 1.5 / 1.0h`** e si limita ad applicare
i delta degli adjustment ladders.

---

## 3. Tabella 2 — Adjustment ladders (10 deltas)

```
Ladder                          | Trigger             | Δ buy | Δ sell | Δ idle
--------------------------------|---------------------|-------|--------|--------
btc_drop_10pct_1h               | BTC 1h ≤ −10%       | +1.5  |  −0.7  |  +3.0
btc_drop_5pct_1h                | BTC 1h ≤ −5%        | +1.0  |  −0.5  |  +2.0
btc_drop_3pct_1h                | BTC 1h ≤ −3%        | +0.5  |  −0.3  |  +1.0
btc_pump_5pct_1h                | BTC 1h ≥ +5%        | −0.5  |  +1.0  |  −0.5
btc_pump_3pct_1h                | BTC 1h ≥ +3%        | −0.3  |  +0.5  |  −0.3
speed_of_fall_accelerating      | fall accelerating   | +0.3  |  −0.2  |  +0.5
funding_long_strong             | funding > 0.05%     | +0.4  |  −0.2  |  +0.5
funding_long                    | funding > 0.03%     | +0.2  |  −0.1  |  +0.3
funding_short_strong            | funding < −0.03%    | −0.2  |  +0.3  |  −0.3
funding_short                   | funding < −0.01%    | −0.1  |  +0.1  |  −0.2
```

### 3.1 Come si combinano

Le 10 righe **non scattano tutte insieme**. Ci sono regole di esclusione:

1. **Drop ladder e Pump ladder sono mutuamente esclusivi**: BTC non può essere
   contemporaneamente sceso del 5% E salito del 3%. Tra i tre drop, scatta
   solo il più forte. Stessa cosa per i pump.

2. **Funding ladders sono indipendenti**: il funding può aggiungersi a un
   drop o a un pump.

3. **Speed of fall è indipendente**: si somma a tutto il resto, indipendentemente.

### 3.2 Logica del segno dei delta

Tutti i delta seguono una logica coerente con la BASE_TABLE:

- Quando il mercato **scende** (drop ladder, speed_of_fall): aumenta `buy_pct`
  (= compra solo a forti ribassi), riduce `sell_pct` (= vendi al primo
  rimbalzo), aumenta `idle` (= aspetta più tempo)
  → si comporta come `fear` / `extreme_fear`

- Quando il mercato **sale** (pump ladder, funding short): riduce `buy_pct`
  (= compra anche a piccoli ribassi), aumenta `sell_pct` (= aspetta profitti
  grossi), riduce `idle` (= ricomincia subito)
  → si comporta come `greed` / `extreme_greed`

- Funding **long over-leveraged** (i long pagano troppo, mercato sbilanciato
  rialzo, rischio liquidazioni a catena): si comporta come "drop in arrivo"
  → aumenta buy_pct, riduce sell_pct (= preparati al crash)

- Funding **short squeeze** (gli short pagano, potenziale spinta al rialzo):
  si comporta come "pump in arrivo"
  → riduce buy_pct, aumenta sell_pct (= preparati al rally)

### 3.3 Esempio numerico — caso semplice

Mercato calmo (oggi): nessun drop, nessun pump, funding -0.005% (sotto soglia
0.01%, niente ladder funding). Solo `speed_of_fall_accelerating` scatta.

```
base (neutral)             = buy 1.0  / sell 1.5  / idle 1.0h
+ speed_of_fall (+0.3, -0.2, +0.5)
                           = buy 1.3  / sell 1.3  / idle 1.5h
clamped a RANGES (vedi §4) = buy 1.3  / sell 1.3  / idle 1.5h  ← entro i limiti
```

Verifica: questo è esattamente quello che hai visto sulla tabella "Last
Proposals" — quando il flag è ON, Sherpa propone `1.3 / 1.3 / 1.5h`. Quando il
flag torna OFF, torna a `1.0 / 1.5 / 1.0h`.

### 3.4 Esempio numerico — caso complesso

Mercato in panico: BTC è crollato del 6% in 1 ora, il funding è schizzato a
+0.04% (long over-leveraged dopo il crollo, gente che apre short pesanti),
e il flag speed_of_fall è ON.

```
base (neutral)              = buy 1.0  / sell 1.5  / idle 1.0h
+ btc_drop_5pct_1h (+1.0, -0.5, +2.0)
                            = buy 2.0  / sell 1.0  / idle 3.0h
+ funding_long (+0.2, -0.1, +0.3)         ← 0.04% > soglia 0.03%
                            = buy 2.2  / sell 0.9  / idle 3.3h
+ speed_of_fall (+0.3, -0.2, +0.5)
                            = buy 2.5  / sell 0.7  / idle 3.8h
clamped a RANGES            = buy 2.5  / sell 0.8  / idle 3.8h  ← sell_pct sale a 0.8 (min)
```

Risultato finale: in questo scenario Sherpa proporrebbe `buy 2.5 / sell 0.8 /
idle 3.8h`. Significa: "compra solo a -2.5% (non comprare adesso che sta
ancora scendendo), vendi al primo +0.8% (prendi i soldi e scappa), aspetta
3.8 ore prima del prossimo ciclo".

→ Comportamento ultra-difensivo, coerente con un crash in corso.

---

## 4. Tabella 3 — RANGES (clamps assoluti)

```
Parameter              | min  | max
-----------------------|------|------
buy_pct                | 0.3  | 3.0
sell_pct               | 0.8  | 4.0
idle_reentry_hours     | 0.5  | 6.0
```

### 4.1 Cosa fanno

Anche se base + delta dovesse uscire dal range, viene tagliato (clamped) ai
limiti. Sono una **rete di sicurezza** contro:
- Bug nei delta (es. se per errore mettessimo un delta gigante)
- Combinazioni multiple che si sommano in modo imprevisto
- Situazioni di mercato estreme con più ladder che scattano insieme

### 4.2 Esempio dove i clamps salvano la vita

Mercato in collasso totale: BTC -12% in 1h + funding +0.06% + speed_of_fall.

```
base                                 = buy 1.0  / sell 1.5  / idle 1.0h
+ btc_drop_10pct_1h (+1.5, -0.7, +3.0) = buy 2.5  / sell 0.8  / idle 4.0h
+ funding_long_strong (+0.4, -0.2, +0.5) = buy 2.9  / sell 0.6  / idle 4.5h
+ speed_of_fall (+0.3, -0.2, +0.5)     = buy 3.2  / sell 0.4  / idle 5.0h
clamped a RANGES                       = buy 3.0  / sell 0.8  / idle 5.0h
                                              ↑       ↑
                                         max applicato   min applicato
```

Senza i clamps, Sherpa avrebbe proposto `buy_pct = 3.2` (comprare solo a -3.2%
di calo) e `sell_pct = 0.4` (vendere al primo +0.4%). Il `sell_pct` sotto 0.8
sarebbe particolarmente pericoloso: vendi così presto che le commissioni Binance
si mangiano il profitto. I clamps ti tengono nei valori "sani".

### 4.3 Perché questi limiti specifici

I valori delle RANGES sono stati scelti dal Board (CEO brief) basandosi su:

- **buy_pct min = 0.3**: sotto questo, compreresti praticamente a ogni piccolo
  movimento → over-trading + commissioni alte
- **buy_pct max = 3.0**: sopra questo, compreresti talmente raramente da
  perdere tutti i ribassi normali
- **sell_pct min = 0.8**: sotto questo, le commissioni Binance (~0.075% × 2 lati
  = 0.15%) mangiano gran parte del profitto
- **sell_pct max = 4.0**: sopra questo, aspetteresti profitti che statisticamente
  arrivano raramente
- **idle min = 0.5h**: sotto, ping-pong garantito
- **idle max = 6.0h**: sopra, perderesti opportunità di re-entry rapido in
  trend di breve

---

## 5. Cooldown — la regola "il Board comanda"

C'è una regola **non visibile** nelle tabelle ma cruciale: il **cooldown
manager** (file `bot/sherpa/cooldown_manager.py`).

### 5.1 La regola

Se il Board (tu) ha modificato manualmente un parametro su `/grid` negli
ultimi **24 ore**, Sherpa NON può sovrascriverlo, anche se proporrebbe un
valore diverso. Il parametro è **lockato** per 24h dalla modifica.

### 5.2 Implementazione

`config_changes_log` traccia chi ha cambiato cosa e quando. Sherpa scrive
con `changed_by = 'sherpa'`, le modifiche da `/grid` con `changed_by =
'manual-ceo'`. Sherpa controlla:

```
SELECT parameter FROM config_changes_log
WHERE symbol = <symbol>
  AND changed_by != 'sherpa'
  AND created_at > NOW() - 24 hours
```

Ogni parametro che esce da quella query è **lockato**.

### 5.3 Effetto in dashboard

Quando vedi `🔒 cooldown (sell_pct)` accanto a un bot, significa: "Sherpa
proporrebbe un sell_pct diverso, ma il Board ha modificato sell_pct su questo
bot nelle ultime 24h, quindi Sherpa rispetta l'override".

`buy_pct` e `idle_reentry_hours` di quello stesso bot **possono essere
modificati** da Sherpa (se non sono anche loro lockati). Il cooldown è
**per-parametro, non per-bot**.

### 5.4 Perché esiste

È una **regola di convivenza**:
- Sherpa è un consigliere automatico, ma il Board ha l'ultima parola
- Se il Board ha fatto una modifica intenzionale, Sherpa deve rispettarla per
  almeno 24h prima di "rimangiarsela"
- Senza il cooldown, ci sarebbe una guerra: Board cambia → Sherpa rilegge i
  signal e propone il suo valore → Board rilegge la dashboard e cambia di
  nuovo → ping-pong infinito

---

## 6. Sequence diagram — come si arriva al numero finale

Ogni 120 secondi, per OGNI dei 3 simboli (BTC, SOL, BONK):

```
1. Leggi sentinel_scores ultima riga
   └→ ottieni risk_score, opportunity_score, raw_signals

2. Da raw_signals deduci i fast_signals
   └→ btc_change_1h, speed_of_fall_accelerating, funding_rate

3. Determina il regime
   └→ Sprint 1: hardcoded "neutral"
   └→ Sprint 2: detector da F&G + CMC + regime logic

4. base = BASE_TABLE[regime]
   └→ neutral → {buy: 1.0, sell: 1.5, idle: 1.0}

5. Per ogni ladder (drop, pump, funding, speed_of_fall):
   └→ se trigger soddisfatto, somma il delta a base

6. final = base + Σ deltas

7. Per ogni parametro:
   └→ clamp a RANGES (min/max)

8. Verifica cooldown:
   └→ per ogni parametro, se changed_by != 'sherpa' negli ultimi 24h:
      └→ marca come "locked", non scrivere

9. Scrivi sherpa_proposals (sempre)
   └→ con i valori finali + flag would_have_changed + cooldown_parameters

10. Se SHERPA_MODE = 'live' (oggi è 'dry_run'):
    └→ scrivi bot_config con i parametri (escluso quelli lockati)
    └→ scrivi config_changes_log con changed_by = 'sherpa'
```

---

## 7. Cose che NON sono nelle tabelle ma sono regole

Ci sono alcuni dettagli operativi che vivono nel codice e non in tabella:

### 7.1 Telegram alert solo on change
Sherpa alerta Telegram solo quando una proposta **cambia** (commit `65f82c2`).
Se Sherpa propone gli stessi parametri di 1 minuto fa, niente Telegram. È un
filtro anti-rumore.

### 7.2 Dedup + retention
Per non esplodere il piano Supabase free, Sherpa scrive solo se la proposta è
diversa o ogni 5 minuti come heartbeat (commit `0246b22`). Retention 60gg
applicata da `db_maintenance.py`.

### 7.3 stop_buy_drawdown_pct
C'è un quarto parametro che Sherpa traccia (vedi colonna `proposed_stop_buy_active`
in `sherpa_proposals`) ma NON è gestito nelle 3 tabelle attuali — è un flag
booleano gestito altrove. Lo vedrai meglio in dashboard quando attiveremo il
detector di regime in Sprint 2.

---

## 8. Bug noti correlati a queste rules (sessione 63)

Catturati anche in `PROJECT_STATE.md` §5.

1. **`speed_of_fall_accelerating` miscalibrato**: scatta ~30% del tempo invece
   del ~1% atteso. → di conseguenza Sherpa propone `buy 1.3 / sell 1.3 / idle
   1.5h` molto più spesso di quanto dovrebbe. Da rivedere post-replay.

2. **BASE_TABLE.neutral diverge dai parametri Board**: oggi `bot_config` ha
   valori diversi da `1.0 / 1.5 / 1.0h` (es. SOL ha sell_pct = 2.0).
   Conseguenza: `would_have_changed = TRUE` per il 100% delle proposte. Da
   decidere: o si allinea Board a Sherpa, o si allinea BASE_TABLE.neutral a
   Board, o si accetta come comportamento DRY_RUN.

3. **Funding ladders troppo larghi**: in regime calmo (-0.005%) nessuno
   scatta. → opportunity_score morta a 20, e `funding_short`/`funding_long`
   non danno mai delta.

---

## 9. Quando consultare questo file

- Quando vedi un valore "strano" in dashboard (es. proposed_buy_pct = 2.5) e
  vuoi capire da dove viene
- Prima di proporre un cambio alle rules (Sprint 2 o ricalibrazione)
- Quando un audit esterno chiede "spiegami la logica di Sherpa"
- Per onboarding di nuovi reviewer / contributors

---

*Generato 2026-05-07 — sessione 63. Aggiornare quando:
- aggiungiamo un nuovo regime alla BASE_TABLE
- aggiungiamo/togliamo un adjustment ladder
- modifichiamo i RANGES
- cambia il valore di COOLDOWN_HOURS*
