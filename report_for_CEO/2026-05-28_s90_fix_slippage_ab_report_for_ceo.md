# Report sessione 90 — Fix slippage spike (brief fix_slippage_AB)

**Data**: 2026-05-28
**Brief**: `briefresolved.md/brief_fix_slippage_AB_s90.md` (+ `brief_slippage_investigation_s90.md`)
**Esito**: SHIPPED — 3 commit pushati su `origin/main`, bot LIVE ripartito sul Mac Mini con il fix attivo.

---

## TL;DR

Il 27/05 alle 21:44 UTC il grid BTC ha venduto in perdita realized −$1.31 con uno slippage check→fill del −5.83%. La sell ha violato l'intent di Strategy A.

Investigazione → root cause: spike testnet single-tick a $82,143 (mainnet stabile $74,500), cristallizzato da `dead_zone_recalibrate` come buy reference, immediatamente consumato dal SELL CHECK nello stesso `check_price_and_execute` → market order su orderbook vuoto.

Board ha approvato A+B (varianti). Implementato, testato (129/129), pushato, restartato il bot.

---

## Cosa è cambiato (1 livello sopra il codice)

**Opzione A — spike guard sul fetch del prezzo**
Quando il bot legge il prezzo, se questo si scosta più del 4% dal tick precedente, NON usa subito quel valore: aspetta 5 secondi, lo rilegge, e procede solo se il movimento si conferma per almeno il 50%. Se è uno spike (book sottile testnet o flash crash mainnet), il ciclo viene saltato e il bot riprova al tick successivo. Logica auto-adattiva: funziona uguale su BTC e BONK (un pump BONK +12% reale passa il filtro, uno spike testnet +10% che ritraccia subito no).

**Opzione B — cooldown post dead-zone recalibrate**
Quando il bot "riallinea" lo stato dopo 4+ ore di inattività (`dead_zone_recalibrate`, brief 73a/74b), NON deve usare lo stesso tick di prezzo per decidere subito una sell/buy. Doppio gate aggiunto: skip della decisione nel tick corrente (la causa esatta del 27/05) + skip anche nel tick successivo come defense in depth.

**Cosa NON è cambiato**: logica di dead_zone in sé, soglie sell/buy/fee, codice TF/Sentinel/Sherpa, qualunque path non-grid.

---

## Verifica empirica del root cause

Klines mainnet vs testnet al minuto del trade:

| Candle 21:43-21:44 UTC | Mainnet (api.binance.com) | Testnet (testnet.binance.vision) |
|------------------------|---------------------------|----------------------------------|
| Range BTC               | $74,428 – $74,776 (~$700) | **$64,714 – $88,000** ($23K range) |

Il bot ha letto $82,143 come "ultimo prezzo" — era un trade testnet reale ma totalmente non rappresentativo. Su mainnet questo episodio sarebbe stato fisicamente impossibile in quei termini, ma uno scenario simile a scala ridotta (flash crash su pair illiquidi, evento news, exchange outage) è plausibile → vale la pena chiudere il rischio pre go-live €100.

---

## Stato dopo la sessione

- **Bot LIVE**: PID parent 93187 sul Mac Mini, runtime commit `673c941` (allineato a HEAD). Restart 09:15 CET, tutti e 5 i brain operativi entro 6s. Health check 4 OK / 0 FAIL.
- **Suite test**: 129/129 verde (8 nuovi test in `tests/test_spike_guard.py`).
- **Bot già "protetto"** sui 3 coin (BTC/SOL/BONK tutti in stop_buy da pre-restart per drawdown sopra soglia) — il fix attiverà la sua utilità appena il ciclo riprenderà normalmente.

---

## Aperti / Follow-up

1. **Opzione C — pre-trade SLIPPAGE_BUFFER esteso al path percentage sell**: parcheggiata, brief separato pre-mainnet. Già nei TODO di PROJECT_STATE §8 come "slippage_buffer parametrico per coin".
2. **Calibrazione parametri post-osservazione**: oggi i 3 parametri (threshold 4% / confirm 50% / pause 5s) sono default argument della funzione. Se servono tunable per-coin via `bot_config`, brief separato. Voto di tenerli fissi finché osservazione 7-14gg post-deploy non suggerisce altrimenti.
3. **`stop_buy_activated_at` UI countdown**: drift cosmetico già tracciato, non legato a questa sessione.

---

## Decision log (per archivio)

**DECISIONE**: Opzione A variante Board (doppio fetch con conferma) + Opzione B con doppio gate (within-tick e next-tick).
**RAZIONALE**: la soglia fissa proposta in fase investigativa era impossibile da calibrare cross-coin (BTC ≠ BONK volatilità); il doppio fetch è auto-adattivo. Il doppio gate B nasce dall'osservazione che `dead_zone_recalibrate` e SELL CHECK vivono nella stessa funzione → un singolo flag in cima alla funzione protegge solo il tick N+1, lasciando scoperto il tick N (lo scenario 27/05).
**FALLBACK SE SBAGLIATA**: la nuova funzione `fetch_price_with_spike_guard` è opt-in chirurgico (i 3 call sites sono espliciti); rollback = revert dei 2 commit + restart. Zero impatto sui dati persistiti.

---

## Riferimenti

- Investigazione root cause: [investigations/slippage_btc_20260527.md](../investigations/slippage_btc_20260527.md)
- Brief originali (CEO → CC): [briefresolved.md/brief_slippage_investigation_s90.md](../briefresolved.md/brief_slippage_investigation_s90.md), [briefresolved.md/brief_fix_slippage_AB_s90.md](../briefresolved.md/brief_fix_slippage_AB_s90.md)
- Commit: `06a6c7c` (fix), `673c941` (docs PROJECT_STATE), `3c4c812` (runtime ref post-restart)
