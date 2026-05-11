# BRIEF 73a — Dead Zone: ultimo lotto bloccato dopo sell run

**Basato su:** PROJECT_STATE.md 2026-05-11 (S72)  
**Priorità:** Alta — il bot è attualmente fermo su tutti e 3 i simboli  
**Stima effort:** Breve (< 1h)

---

## Problema

Dopo una sell run (es. BONK ieri, 4 sell consecutivi), il bot rimane con 1 solo lotto e si blocca in una "dead zone":

- **Non vende** perché il sell target è ricalibrato sull'ultima vendita (+2.5% da lì), e il prezzo si è fermato
- **Non compra** perché il reference di buy è ancorato alla media bassa, e il prezzo è troppo sopra (BONK +5.6% sopra avg)
- **Non ricalibra** perché `idle_recalibrate_skipped` scatta solo quando prezzo < avg

Stato attuale (21:06 UTC 11 maggio):
- BTC: 1 lotto, stop_buy attivo, fermo da ~19h
- SOL: 1 lotto, +2.8% sopra avg, fermo da ~5h
- BONK: 1 lotto, +5.6% sopra avg, fermo da ~21h

## Causa probabile

Effetto collaterale della regola "non vendere tutti i lotti insieme". Ogni sell ricalibra il target più in alto. Quando il rally si ferma, l'ultimo lotto resta orfano: troppo alto per buy, troppo basso per il prossimo sell.

## Soluzioni da valutare (CC decide implementazione)

**Opzione A:** Quando resta 1 solo lotto e il bot è idle da X ore → forza ricalibrazione al prezzo corrente (reset del ciclo).

**Opzione B:** L'ultimo lotto si vende sempre tutto (il divieto "non vendere tutti i lotti" si applica solo con 2+ lotti). Così la posizione si azzera e il prossimo ciclo riparte pulito.

**Opzione C:** Altra soluzione proposta da CC.

## Decisioni delegate a CC
- Scelta tra opzione A, B, o C
- Valore di X ore per opzione A (se scelta)
- Dove nel codice intervenire (grid_runner? sell logic?)

## Decisioni che CC DEVE chiedere
- Se la soluzione cambia la logica di sell in modo significativo → conferma Board

## Bug collaterale da investigare
BTC stop_buy attivato alle 14:09 con "unrealized $-5,308.99" ma lo snapshot mostra unrealized +$969. La contraddizione potrebbe essere legata al bug Brief 60b (avg_buy_price bias). Da verificare se il calcolo unrealized nel trigger stop_buy usa un path diverso dallo snapshot.

## Output atteso
- Fix deployato e bot che riprende a tradare
- Nota nel commit se la logica di sell è cambiata
- Aggiornare roadmap se impattata

## Vincoli
- NON toccare la logica Sentinel/Sherpa
- NON cambiare buy_pct / sell_pct nei config
- Il fix deve funzionare su testnet (ordini reali via ccxt)
