# RforCEO — avg-cost dilution incident + testnet fees (S96b)

**Da:** CC (Claude Code) · **A:** CEO + Max (Board) · **Data:** 2026-06-05 · **Sessione:** S96b
**Origine:** osservazioni di Max in chat ("perché non compra?" → "abbiamo rotto tutto" → fee)
**Commit:** `32bfef4` (first-buy) · `009265e` (avg-cost) · `2167c37` (fee opzione B)
**Esito:** ✅ RISOLTO & verificato live · **Segue:** `2026-06-05_S96b_RforCEO_phantom-first-buy-fix.md`

> ⚠️ Questo report **aggiorna** quello sul first-buy: quel fix era corretto nell'intento ma ha **innescato** un secondo bug più grave. Racconto la catena intera, onestamente, incluso un mio errore di metodo.

---

## La catena (cosa è successo davvero)

**1. Fix first-buy (`32bfef4`).** Dopo il clean slate i grid non compravano: il gate del primo acquisto guardava gli holdings *totali* (incluso il regalo testnet) → "skipping first buy". Corretto → usa `managed_holdings`. I bot hanno ripreso a comprare. **Sembrava risolto.**

**2. Il bug grave che ho esposto (`009265e`).** Abilitando gli acquisti è emerso che **anche il calcolo dell'avg-cost** usava gli holdings totali ([buy_pipeline.py:237](bot/grid/buy_pipeline.py#L237)). Il phantom (1 BTC / 6 SOL a costo $0) **diluiva la media a ~$49 invece di $62.780** → ogni sell calcolava un **profitto finto enorme**:
- BTC: +$49.59 su un guadagno reale di ~$0.04
- SOL: +$19.04 su ~$0.04
- Totale **$68.63 di realized inventato** + **$20.59 di skim finto** scritto in reserve.

Max l'ha notato ("abbiamo rotto tutto"). **Fix:** avg-cost su `managed_holdings` (esclude il phantom). Verificato: il sell trigger è passato da $50.30 (avg diluito) a ~$64.440 (avg reale $62.737). Insieme al first-buy, ora **tutta la macchina avg-cost è phantom-safe**.

**3. Pulizia.** Cancellati gli artefatti del bug da testnet_2 (trade finti, skim finto, snapshot polluti). Il ciclo è ripartito davvero pulito.

**4. Fee opzione B (`2167c37`).** Max ha notato fee=0. Causa: il testnet **post-reset non addebita commissioni** (prima sì, 0,1%). Decisione Max+CC: **sintetizzare** la `FEE_RATE` (0,1%) quando il fill torna 0, così i numeri testnet raccontano un mondo con costi reali (mainnet-honest). Lato buy la fee entra nell'avg (`cost_for_avg`), lato sell nel realized → round-trip ~0,2% come mainnet. Mainnet intatto (fee vera passa). `reconcile_binance` reso consapevole (niente falsi DRIFT). **Verificato live:** i 3 buy registrano fee a esattamente 0,1%.

---

## Stato finale

I 3 grid girano puliti con: gate primo-acquisto + avg-cost + fee tutti su base *managed*/realistica. testnet_2 pulito, P&L corretto, fee 0,1% sintetiche.

## Lezione di metodo (mia)

Ho shippato il first-buy fix e l'ho dichiarato "verificato" basandomi sulla **costruzione** (il bot comprava), senza controllare un trade reale. Il trade reale avrebbe mostrato subito il realized finto. **Nuova regola operativa che mi do:** su modifiche al core P&L/avg-cost, verifico un **round-trip reale** (o i numeri di un sell vero) prima di dire "fatto". Applicata già su opzione B (ho aspettato i buy veri per confermare 0,1%).

## Nota anti-assenso

L'obiezione su opzione B l'ho fatta io stesso prima di implementare: il trade-off è una piccola divergenza tra ledger logico (che sottrae la fee) e wallet testnet reale (che non la addebita) — coerente col design esistente (cash è già un ledger logico) e con `story_is_process_not_numbers`. Fallback: tutto reversibile, è paper.

## Riferimenti

- `bot/grid/buy_pipeline.py` (avg-cost managed + synth fee), `bot/grid/sell_pipeline.py` (synth fee sell), `scripts/reconcile_binance.py` (fee-drift skip su fee=0)
- Catena: S96a clean slate → S96b first-buy → S96b avg-cost+fees (questo)
