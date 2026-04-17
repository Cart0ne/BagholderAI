# BRIEF — Session 36g: TF compounding / floating cash

**Date:** 2026-04-16
**Priority:** MEDIUM — non blocca operazioni, ma risolve un buco contabile + abilita compounding organico
**CC working machine:** MacBook Air (locale)
**Production machine:** Mac Mini (deploy via git pull SSH)
**Prerequisito:** 36c deployato ✅
**Scope rule:** SOLO logica budget effettivo del TF. Skim, rotazione coin, step adattivi → brief separati.

---

## Problema osservato

Oggi il TF ha un **bucket fantasma**: il 70% dei profitti che non finisce in `reserve_ledger` resta come USDT su Binance ma non viene letto da nessuno.

Esempio concreto (16 apr 2026, 06:34 UTC):

```
BIO/USDT  sell → pnl +$5.34 (skim NON applicato per bug pre-36c)
ORDI/USDT sell → pnl +$3.47 (skim NON applicato per bug pre-36c)
Totale pnl: $8.81
```

Con skim correttamente configurato (30%):
- $2.64 sarebbero andati in `reserve_ledger` ✅ (questo è stato inserito retroattivamente in sessione 36c)
- **$6.17 sarebbero rimasti nel bucket `received` di BIO/ORDI** → available_cash del bot aumenta → ri-comprava se signal ancora BULLISH

Quando BIO/ORDI sono stati liquidati e `is_active=false`:
- Nessun bot legge più BIO/ORDI
- Quei $6.17 restano come USDT su Binance, "floating"
- Il prossimo scan TF NON li vede: `tf_total_capital = float(config.get("tf_budget", 100))` — **costante dal DB**
- Risultato: TF splitta sempre $100, mai $106.17

**Effetto cumulativo**: ogni ciclo di rotazione TF perde il 70% dei profitti alla contabilità. Zero compounding.

## Causa radice

In `bot/trend_follower/trend_follower.py:368`:

```python
tf_total_capital = float(config.get("tf_budget", 100))
```

`tf_budget` nel DB (`trend_config.tf_budget`) è un valore nominale fisso. Non viene mai aggiornato quando i bot TF generano profitto, e non c'è un meccanismo di "reclaim" del cash floating quando i bot vengono killati.

## Obiettivo

Il TF deve usare come base di allocazione:
- il `tf_budget` nominale
- **+ il cash floating** (profitti non skimmati di bot TF morti o USDT sparsi nel bucket TF non allocati)

Così il compounding avviene naturalmente: ogni sell profittevole → 30% skim + 70% riassorbito nel prossimo ciclo di allocation.

## Opzioni considerate (ranking)

### Opzione A — skim_pct=100 (pulita ma zero compound)

Tutto il profitto TF va in `reserve_ledger`. `tf_budget` resta fisso. Contabilità banale, nessuna complessità, ma elimina la crescita organica del TF. **Scartata** perché annulla il senso del compounding.

### Opzione B — compounding vero via floating cash lookup (raccomandata)

Modifica `tf_total_capital` per includere il floating:

```python
tf_floating = compute_tf_floating_cash(supabase, exchange)
tf_total_capital = float(config.get("tf_budget", 100)) + tf_floating
```

Dove `tf_floating` = USDT sul bucket TF non allocati ad alcun bot TF attivo.

Due modi di calcolarlo:

**B1 — Ledger-based** (preferito, no dipendenza exchange):
```
tf_floating = SUM, su tutti i bot TF storici,
              di (total_received - total_invested - skim_total)
              - SUM, sui bot TF attivi, di available_cash_corrente
```
In pratica: "quanto profitto TF è stato generato complessivamente, meno quello che sta già dentro bot vivi, meno quello già skimmato".

**B2 — Exchange-based** (più preciso ma frágil):
```
tf_floating = USDT_totale_on_exchange
              - capital_allocation_manuali
              - capital_allocation_TF_attivi
              - reserve_totale
```
Richiede una fonte affidabile per "quanto USDT appartiene al bucket TF vs. manuale". Rischio: in paper trading l'exchange non distingue i bucket.

**B1 è preferito** perché tutto il calcolo resta in Supabase, nessuna query all'exchange.

### Opzione C — reclaim al kill (semplice ma discreto)

Quando un bot TF viene deallocato (`pending_liquidation=true` → grid_runner self-stop), subito prima di uscire il grid_runner fa:

```sql
UPDATE trend_config SET tf_budget = tf_budget + $leftover_cash
WHERE ... -- assumendo una sola riga
```

Dove `$leftover_cash = received - invested - reserve_totale` del bot.

**Vantaggi**: implementazione localizzata (una UPDATE nel self-stop hook).
**Svantaggi**: aggiornamento discreto, non continuo. Profitti di bot VIVI restano nel bucket bot finché non muore. Se un bot TF profittevole resta attivo per settimane, il suo cash non è mai disponibile al TF per nuove allocation.

C funziona come ripiego se B risulta troppo complesso.

## Raccomandazione

**Opzione B1** (ledger-based floating). Motivi:
- Continuo, non discreto — il TF vede sempre il quadro aggiornato
- Zero dipendenza dall'exchange (funziona in paper e live)
- Testabile con dati SQL puri

## Propagazione del compound al `capital_per_trade` dei bot vivi

Il compound a livello TF budget non basta: se AXL è stata allocata a `$50 / capital_per_trade $12.50` alle 13:19, e poi il TF accumula $20 di profitto, AXL continuerà a fare buy da **$12.50** anche se il TF avrebbe $70 da allocarle in virtù del compound. Il bot vivo non vede mai crescere la sua size finché non viene deallocato e ri-allocato da zero.

Esempio concreto (numeri stupidi per capirsi):

```
T0:
  budget TF = $500, max_coins = 3
  allocate: ANCHOR-A $200 (cpt $50, 4 buys), ANCHOR-B $150 (cpt $38), ANCHOR-C $150 (cpt $38)

T1 (dopo 1 settimana di profitti non skimmati riassorbiti nel budget):
  budget TF effettivo = $600
  Senza propagazione: A/B/C restano a $200/$150/$150 e cpt $50/$38/$38 → compound dormiente
  Con propagazione: A $240 (cpt $60 → 4 lot) oppure (cpt $80 → 3 lot), B/C $180 ciascuna
```

Il CEO ha anche ipotizzato che al crescere della per-trade si possa **ridurre il numero di lot** (es. 3 × $70 invece di 4 × $50 su allocazione $240 che era $200). È una scelta di policy: 4 lot = più granularità e più reazioni ai dip, 3 lot = meno trade ma più materiali. Lasciare configurabile via parametro `tf_lots_per_coin` (default 4, oggi hardcoded nel `max($6, capital/4)` dell'allocator).

### Meccanismo proposto

A ogni scan TF, oltre a calcolare `tf_total_capital` (budget + floating), **ri-valutare anche le allocation attive**:

```python
for active in tf_active_bots:
    target_allocation = tf_total_capital / tf_max_coins  # equal split base
    target_cpt = max(MIN_CPT, round(target_allocation / tf_lots_per_coin, 2))

    if abs(active.capital_allocation - target_allocation) >= RESIZE_THRESHOLD_USD:
        UPDATE bot_config
           SET capital_allocation = target_allocation,
               capital_per_trade  = target_cpt
         WHERE symbol = active.symbol
```

Dove `RESIZE_THRESHOLD_USD` (es. $5) evita UPDATE continui per fluttuazioni piccole (un sell da $0.30 di profit non deve triggerare UPDATE).

Il grid_runner già ricarica `bot_config` a ogni ciclo (check interval 20-60s), quindi vede la nuova `capital_per_trade` al buy successivo.

### Edge cases da considerare

1. **Resize che riduce `capital_per_trade` mentre c'è un lot pending**: se capital_per_trade scende da $50 a $40, il prossimo buy sarà $40 — OK. Nessun problema retroattivo.
2. **Resize che aumenta `capital_allocation` oltre il cash disponibile**: il bot prova a comprare $60 ma ha solo $30 cash → la sweep/last-shot logic attuale gestisce (buy ridotto o skip). OK.
3. **Resize mentre un bot sta per essere deallocato (pending_liquidation=true)**: skip resize in quel caso — il bot sta morendo, non ha senso ridargli size.
4. **Resize durante swap (36e)**: il bot in uscita non ha bisogno di resize (sta morendo). Il nuovo in entrata riceve la size corretta dal codice di ALLOCATE normale.
5. **Oscillazione**: con floating che cambia ad ogni trade, il resize potrebbe triggerare troppo spesso. Il `RESIZE_THRESHOLD_USD` è il bumper.

### Decisioni aperte (da chiarire col CEO)

1. **`tf_lots_per_coin`**: 4 (default attuale) o 3 (meno granulare, trade più sostanziosi)? Configurabile in `trend_config`. Io propenderei per **4 quando budget < $1000, 3 quando budget > $1000** (regola adattiva) ma è una micro-policy.
2. **`RESIZE_THRESHOLD_USD`**: $5 è prudente, $10 più conservativo. Dipende da quanto vogliamo che il sistema "respiri" col compound. Più basso → più reattivo, più UPDATE su bot_config.
3. **Sanity cap sul per-trade**: oltre una certa soglia (es. $200 per trade su paper trading con $500 iniziali) è indice di over-concentration? Probabilmente utile cap assoluto su `capital_per_trade` per evitare che un compound esplosivo porti a trade singoli troppo grossi rispetto al capitale totale.

### Files extra da modificare (oltre a quelli già elencati sopra)

| File | Azione |
|---|---|
| `bot/trend_follower/allocator.py` | Helper `resize_active_allocations`, chiamata a ogni scan |
| DB | Aggiungere colonna `trend_config.tf_lots_per_coin` (default 4) |

### Integrazione con 36e

Il resize va applicato **dopo** la logica rotation/DEALLOCATE (36e), così non si spreca un UPDATE su un bot che sta per morire. Ordine di operazioni nel main loop TF:

1. Scan + classify
2. On-demand rescan active fuori-top (36e Fix 1b)
3. Rotation decisions (BEARISH/SWAP/HOLD — 36e Fix 1)
4. **Resize active allocations** (36g estensione) ← nuovo
5. Nuove ALLOCATE per slot rimasti vuoti

## Files da modificare

| File | Azione |
|---|---|
| `bot/trend_follower/trend_follower.py` | Aggiungere helper `compute_tf_floating_cash(supabase)`; sommare al `tf_total_capital` |
| Eventualmente `bot/trend_follower/allocator.py` | Nessuna modifica diretta; riceve già `total_capital` che ora include floating |

## Files da NON toccare

- `bot/strategies/grid_bot.py` (la sua nozione di `available_cash` resta per-bot, corretta)
- `db/client.py` (ReserveLedger resta invariata)
- `coin_tiers`, `trend_config` (a parte letture)
- Bot manuali (BTC/SOL/BONK) — il loro cash NON va conteggiato nel floating TF
- `reserve_ledger` (solo lettura)

## Algoritmo proposto per `compute_tf_floating_cash`

```python
def compute_tf_floating_cash(supabase) -> float:
    """
    Floating cash disponibile al TF = profitti realizzati storici
    dai bot TF, meno quello che già sta dentro bot TF attivi,
    meno il totale skimmato.
    """
    # 1. Totale ricevuto e investito da TUTTI i bot TF (attivi + passati)
    #    Filtro: trades.managed_by = 'trend_follower'
    rows = supabase.table("trades").select(
        "symbol, side, cost"
    ).eq("managed_by", "trend_follower").execute()

    # 2. Available cash ancora dentro bot TF vivi
    #    (capital_allocation - invested + received - reserve) per ogni symbol
    active_tf = supabase.table("bot_config").select(
        "symbol, capital_allocation"
    ).eq("is_active", True).eq("managed_by", "trend_follower").execute()

    # 3. Reserve totale di symbol TF (storici + attivi)
    #    Da reserve_ledger, filtrando per symbol in universo TF

    # Floating TF = profitto netto storico TF - cash attivo nei bot TF - reserve TF
    return floating
```

Da rifinire nell'implementazione — l'idea è: contabilità TF-only, ignora manuali, non tocca l'exchange.

## Edge cases da coprire nei test

- [ ] Floating=0 (stato iniziale, nessun profitto) → `tf_total_capital = tf_budget`
- [ ] Un bot TF vivo con cash interno positivo → NON contato in floating (è del bot)
- [ ] Un bot TF morto con received > invested + skim → delta in floating
- [ ] Reserve manuali (BONK/BTC/SOL) NON entrano nel conteggio TF
- [ ] Sanity cap: `tf_total_capital` non deve superare X (proposta: `tf_budget * 3`? da decidere col CEO)
- [ ] Race condition scan ↔ sell: scan legge budget → bot vende → floating cambia. Accettabile, prossimo scan correggerà.

## Test pre-deploy

Lanciare con `dry_run=true`:

- [ ] Query manuale su `trades` per calcolare floating a mano → confronto con output helper
- [ ] Scan mostra `tf_total_capital` nei log, include floating
- [ ] `WOULD ALLOCATE` usa il budget esteso (es: 2 coin → $53+$53 invece di $50+$50)
- [ ] Nessun impatto sui bot manuali (log non menziona BTC/SOL/BONK)

## Test post-deploy

- [ ] Dopo un ciclo completo (sell profitto → deallocate → nuovo scan), verificare che `tf_total_capital` logged sia aumentato
- [ ] `reserve_ledger` non perde entries (non doppia contabilizzazione)
- [ ] Telegram report su `/tf` dashboard mostra "TF budget: $100 base + $X floating = $Y effective"

## Telemetria continua

Aggiungere al `/tf` dashboard (brief micro separato se preferisci):
- `TF budget effective: $Y = $100 base + $X floating`
- `Floating history: latest 7 days`

## Rollback plan

Se rompe qualcosa (da MacBook Air):

```bash
git revert <commit_hash>
git push origin main
ssh max@<mac_mini_ip>:/Volumes/Archivio/bagholderai 'git pull'
# Restart orchestrator via SSH detached come in 36c
```

Rollback riporta `tf_total_capital` al valore fisso `tf_budget`. Nessun dato perso (reserve_ledger intatto).

## Decisioni aperte (da chiarire prima del deploy)

1. **Sanity cap del compound**: c'è un massimo a cui può crescere `tf_total_capital`? Proposta: `tf_budget * 3` = $300 come hard cap (altrimenti a fronte di un run folle il TF alloca $500/coin e intasa).
2. **Skim sui floating riassorbiti**: se riassorbiamo $6 di profitto e poi quel $6 produce altro profitto nel prossimo buy-sell, il nuovo profitto va skimmato al 30%? **Sì** (stessa logica, non c'è distinzione di origine). Già gestito dal grid_bot.
3. **Reset del floating**: esiste un caso in cui vogliamo azzerare manualmente il floating? Probabilmente sì, come emergency reset. Come implementarlo? Forse un campo `tf_floating_reset_at` in `trend_config` che scarta trades precedenti.

## Commit format

```
feat(trend-follower): compound profits via floating cash lookup

tf_total_capital now = tf_budget + floating, where floating is net TF
profit (received - invested - skim) not currently held by live TF bots.
Enables organic compounding: the 70% of each sell profit not skimmed
becomes available to the next allocation cycle instead of floating
untracked on the exchange.
```

## Push

Push diretto su `main` quando done. Niente PR.

---

## Out of scope

- **36d**: profit_target_pct + step adattivi (scritto, da deployare)
- **36e**: rotazione coin + buy_pct/sell_pct via ATR
- **36f**: trailing stop pump
- Skim di valore != 30% (va toccata `coin_tiers` o `allocator.py`, fuori scope)
