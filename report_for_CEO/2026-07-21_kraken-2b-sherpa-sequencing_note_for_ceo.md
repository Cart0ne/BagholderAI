# Nota per il CEO — Kraken: 2a chiusa + decisione sequencing 2b (Sherpa)

**Data:** 2026-07-21 · **Autore:** CC (intern) · **Per:** CEO / Board
**Contesto:** sessione operativa 21-lug (update Mac Mini + restart flotta) + discussione tecnica con Max su come impostare la Fase 2b.

---

## 1. Stato operativo
- Mac Mini aggiornato (OS), **flotta Binance testnet riaccesa e sana** (orchestrator + 4 grid + TF + Sentinel + Sherpa + NewsKeeper v2 + listener), cron verificato attivo, repo allineato a origin (`7d5417f`).
- **Fase 2a Kraken CHIUSA** ✅ — round-trip reale completo su denaro vero:
  - BUY $25 (17-lug) → **SELL oggi 21-lug 10:11 UTC @ $66.317** · realized **+$0,7069 netto fee**.
  - Validati dal vivo: esecuzione/conferma-fill, contabilità fee 0,8% taker, trigger fee-buffered. Nessuna posizione aperta, holdings a 0.

## 2. Finding verificato — doppio-conteggio fee su Kraken (nodo 5)
Verificato sul **codice eseguibile** + numeri reali della 2a (non a memoria):
- Su Kraken l'avg-cost **include già la fee di buy** (`buy_pipeline.py:304`, fee in quote).
- Il trigger di vendita (`grid_bot.py:876`) e il floor min-profit (`sell_pipeline.py:305`) **la ri-aggiungono** → doppio conteggio.
- **Effetto**: un target "1% netto" su Kraken realizza in realtà **~1,8% netto** (margine = sell_pct + fee). Su Binance lo scarto è 0,1% (invisibile); su Kraken è 0,8% (materiale).
- **Prova**: nella 2a il trigger è scattato a $66.314; senza doppia-conta sarebbe stato ~$65.798.
- **Fix** (togliere la fee di troppo dal trigger + floor a 1× fee) già previsto nel **bundle 2b** (`config/2026-07-21_MEMO_kraken-fase2b.md` §2/§3).

## 3. Sherpa su Kraken — NON è un blocco tecnico
Domanda di Max: conviene fare la 2b con **Sherpa** che decide buy/sell (via regime Sentinel), invece che a mano?
- Il fee-buffer **vive nel trigger**, non nei valori di Sherpa: è venue-aware e indifferente a chi imposta il `sell_pct`. Sherpa dice 1% → il bot vende a >2,6% lordo su Kraken; dice 5% → >6,7%.
- Quindi i valori di Sherpa sono **intenzioni nette venue-indipendenti**: 1% netto resta 1% netto. **Nessuna "board table Kraken" da ricalibrare** (correzione: mia affermazione iniziale errata, ritirata).
- **Unico prerequisito reale**: il fix del doppio-conteggio (§2), così l'intenzione di Sherpa = margine realizzato.
- Nota data-driven (non prerequisito): lo stesso margine netto richiede un movimento **lordo** maggiore per scattare su Kraken → il grid tradera **meno spesso**, più vicino a hold. È corretto a fee alte; lo misura il collaudo (Fase 3).

## 4. Decisione richiesta al Board — sequencing 2b
La 2a ha **già** provato la meccanica su denaro reale, e il trigger protegge **ogni singola vendita** a prescindere da chi sceglie il numero. Quindi "static a $100" **non è più sicuro** di "Sherpa-driven a $100": il rischio-soldi è equivalente. La differenza è solo di leggibilità del test.

- **Opzione A (piano attuale)**: 2b con parametri statici a mano → Fase 3 collaudo BTC→SOL→BONK → *poi* Sherpa. Un gradino più semplice da isolare.
- **Opzione B (proposta Max)**: 2b già Sherpa-driven. Testa direttamente la config di produzione. Richiede prima il fix doppio-conteggio (già in bundle).

**Prerequisito comune a entrambe**: il fix nodo-5 va shippato prima in ogni caso.

👉 **Serve la decisione del Board su A vs B** (+ conferma margini/floor), perché cambia *cosa* testa la 2b. Non è una scelta tecnica di CC.
