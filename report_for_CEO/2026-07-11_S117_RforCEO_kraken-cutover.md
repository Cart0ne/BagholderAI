# Report for CEO — kraken-cutover (S117b, 2026-07-11)

**Brief sorgente:** `config/2026-07-11_S117_brief_kraken-cutover.md` (SCOPE `kraken-cutover`)
**Commit di sessione:** `9b27037` (CLAUDE.md health-sweep fix), `002fa23` (scripts/kraken_cutover_check.py)
**Restart bot:** nessuno. Nessun ordine reale piazzato. Hot-path NON toccato.
**Stato del brief:** APERTO — risequenziato da Max (Board), vedi §1. Resta in `config/` per la Fase 1.

---

## 1. ⚠️ Decisione di Board: il brief è stato risequenziato

**Max ha fermato l'implementazione del cutover in questa sessione.** Intento dichiarato
(conversazione diretta, 2026-07-11): le chiavi API sono state generate **per permettere i test
di plumbing** (lettura/scrittura/validate, con errori attesi da saldo zero), **non** come trigger
del cutover completo.

Il cutover vero — anche solo il collaudo $100 — è per Max un'**operazione coordinata**: sito in
pagina-disclaimer (come da `COLLAUDO_COMMS_GUIDELINES_v1.md` Step 1, che infatti prevede proprio
questa finestra), stop di tutti i bot, aggiornamento di grid + Sherpa + Sentinel, TF escluso
(congelato in attesa di revisione). Il brief S117 saltava questa finestra andando dritto a
cablaggio+collaudo.

**Risequenziamento concordato (K.1 spezzato in fasi):**

| Fase | Contenuto | Quando |
|---|---|---|
| **0** | Test plumbing con le chiavi (§3 del brief) — SOLO test, zero ordini | ✅ **FATTA oggi** |
| **1** | Pre-lavori senza fermo: cablaggio hot-path dietro flag, floor fee-aware, isolamento venue (orchestrator/Sherpa hands-off), ritocchi Sherpa/Sentinel, pagina-disclaimer toggle (K.3 prep), prova generale validate end-to-end | prossime sessioni, brief/piano dedicato |
| **2** | Finestra di fermo: sito→disclaimer, stop bot, flip `EXCHANGE=kraken`, restart, Max versa $100 | decide Max |
| **3** | Collaudo BTC→SOL→BONK (APPROVED §2 + comms guidelines) | dopo Fase 2 |
| **4** | Deployment $600 (APPROVED §3) | dopo verdetto collaudo |

---

## 2. FASE 0 eseguita — esito: ✅ TUTTO VERDE (18 check, 0 FAIL)

Script: `scripts/kraken_cutover_check.py` (committato, riusabile). Eseguito sul Mac Mini
(dove vivono le chiavi) alle ~13:20 CEST. Read-only + `validate=true`, nessuna esecuzione.

| Step §3 brief | Esito | Dettaglio |
|---|---|---|
| 1. Endpoint pubblici | ✅ | `Time`: drift clock **0,03s** (nonce safe). `AssetPairs`: le 3 coppie risolvono (BTC/USD→`XXBTZUSD`, SOL/USD→`SOLUSD`, BONK/USD→`BONKUSD`) |
| 2. Auth read-only | ✅ | `fetch_balance` autenticato OK, saldo zero come atteso, **nessun auth_error** → chiave e permessi corretti |
| 3. AddOrder `validate=true` | ✅ | **BUY e SELL market per quantità-base accettati su tutte e 3 le coppie** (il path primario del grid, 73c). Vedi §3 per il caveat sul cost-order |
| Extra: fee tier reale | ✅⚠️ | vedi §3, finding n.1 |
| Extra: nonce burst | ✅ | 5 call private consecutive senza errori nonce |

**Minimi d'ordine (dati reali):** BTC 0.00005 (~$3.21) · SOL 0.06 (~$4.68) · BONK 1.2M (~$4.94).
Con capital_per_trade $25 siamo 5-8× sopra i minimi → l'auto-obiezione n.1 del brief (griglia
troppo rada per ordermin) **non si verifica**: $100 su BTC regge 4 livelli da $25.

## 3. I due finding che cambiano i numeri del piano

**Finding 1 — LA FEE REALE È IL DOPPIO DI QUELLA ASSUNTA NEL BRIEF.**
Il brief assume taker 0,40%. La risposta live di Kraken per questo account (volume 30gg = 0):
**taker 0,80% / maker 0,40%** → un ciclo buy+sell a mercato costa **1,6%**, non 0,8%.
La fee scende a 0,60% taker oltre $2.500 di volume/30gg, poi a scalare.
Implicazioni:
- Conferma definitiva del principio del brief (§2d): **fee letta live, mai hardcodata** — col
  valore assunto avremmo perso ~0,8% a ciclo "vincendo" nominalmente.
- **Il Modello B (ladder maker 0,40%) dimezza il costo per giro rispetto al Modello A (0,80%
  taker).** La decisione Board "A per il collaudo, B rimandato a deployment" resta valida, ma
  merita ri-esame Board con questi numeri PRIMA del deployment $600. Non decido io: segnalo.
- La ricalibrazione passi griglia va fatta su 1,6% round-trip (tier-0), con adattamento
  automatico man mano che il tier migliora.

**Finding 2 — auto-obiezione n.2 del CEO: FONDATA.**
`create_market_buy_order_with_cost` (BUY per importo quote, il fallback del grid) su Kraken
è schizzinoso vicino ai minimi: rifiutato su BTC e SOL con margine +5% sull'ordermin
(`volume minimum not met`), accettato su BONK. Il path primario del grid (BUY per quantità
base, lot-rounded) è verde ovunque. Per la Fase 1: fallback cost-order con margine ≥20% sul
minimo, oppure fail-esplicito. Nessun impatto sugli ordini standard da $25.

## 4. Obiezione tecnica emersa (anti-assenso, da chiudere in Fase 1)

Il §2d del brief chiede il floor min-profit come "parametro gestito da Sherpa". Il param
esiste già end-to-end (`bot_config.profit_target_pct` → guard in sell_pipeline), **ma** la
BOARD_TABLE di Sherpa ha `profit_target_pct = 0` in tutte le celle
(`bot/sherpa/board_parameter_rules.py`): se Sherpa gestisse live la riga Kraken oggi,
**azzererebbe il floor a ogni ciclo**. In più la volatilità di Sherpa legge klines Binance con
naming `BTC/USD→"BTCUSD"` (inesistente su Binance).
Proposta CC (validata da Max in conversazione): durante il collaudo le righe Kraken sono
hands-off per Sherpa/orchestrator (colonna `venue` in bot_config, Fase 1); l'attivazione
Sherpa-live su Kraken (valori non-zero in BOARD_TABLE + fix sorgente volatilità) è decisione
Board post-collaudo. Se il CEO intendeva "Sherpa live da subito" → non converge, arbitra Max
(che intanto ha già indicato la direzione hands-off).

## 5. Cosa serve al CEO ora

1. **Prendere atto del risequenziamento** (K.1 → Fasi 0-4; Fase 0 chiusa oggi).
2. **BUSINESS_STATE**: se vuoi registrare risequenziamento + finding fee, l'update lo fai tu
   (CC non tocca BUSINESS_STATE di iniziativa). In coda c'è anche la riga "decisione Kraken"
   già prevista da `COLLAUDO_COMMS_GUIDELINES_v1.md` §7.
3. **Brief Fase 1** quando vuoi: il piano tecnico dettagliato è già pronto (proposto a Max in
   questa sessione: cablaggio call-site gated, `bot.fee_rate` dinamico da `fee_tier()`,
   floor `avg × (1 + 2×fee + margine)`, colonna `venue`, fix contabile buy-fee-in-quote → avg,
   disclaimer-toggle). Parametri collaudo (passi prudenti vs vivaci, margine floor) da chiudere
   col piano.
4. **Valutare ri-esame Modello B** al deployment, coi numeri fee veri (Finding 1).

## Decisions (log di sessione)

- **DECISIONE:** eseguire solo la Fase 0 (test), rinviando cablaggio/floor/isolamento a Fase 1.
  **RAZIONALE:** intento Board esplicito (chiavi = test, cutover = operazione coordinata).
  **ALTERNATIVE:** implementare il brief com'era (scartata da Max).
  **FALLBACK:** nessuno necessario — zero modifiche a codice bot, nulla da annullare.
- **DECISIONE:** test `validate=true` a taglia `ordermin` (non $25) per disaccoppiarli dal saldo.
  **RAZIONALE:** saldo zero; il minimo esercita anche i filtri di taglia.
  **ALTERNATIVE:** aspettare il funding (posticipava tutto).
  **FALLBACK:** rieseguire lo script post-funding (riusabile as-is).
