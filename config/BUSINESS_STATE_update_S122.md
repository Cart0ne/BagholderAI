# Aggiornamento BUSINESS_STATE.md — S122 (2026-07-22)

Aggiornare SOLO le sezioni sotto. Le altre restano invariate.

---

## §4 — Decisioni strategiche recenti

Aggiungere in testa (formato: data — decisione — why):

| Data | Decisione | Why |
|---|---|---|
| 2026-07-22 (S122) | **Opzione B CONFERMATA — Fase 2b = $100 BTC/USD su Kraken Sherpa-driven.** ⚠️ **Revisione esplicita della decisione S119 del 2026-07-13** ("$100 sequenziale grid-only → sistema pieno SOLO dopo") | La 2a ha già eseguito un round-trip reale completo a parametri statici (BUY $25 17-lug → SELL 21-lug, +$0,7069 netto). Ripetere lo stesso test con $100 non produce informazione nuova. Costo accettato consapevolmente: **diagnosticabilità** — se la 2b va male non sapremo di primo acchito se ha sbagliato la meccanica o la scelta di Sherpa. Accettabile perché il fix `ed1933d` garantisce che ogni singola vendita sia in utile netto: il caso peggiore è "guadagna poco", non "perde" |
| 2026-07-22 (S122) | **Sorgente volatilità Sherpa su Kraken = proxy Binance /USDT** (non OHLC nativo Kraken) | BTC/USD e BTC/USDT hanno volatilità realizzata praticamente sovrapponibile; riusa infra Binance esistente, zero superficie API nuova su un path che gira di continuo sui 4 grid vivi. Coerente con S112 (funding-rate resta su Binance, dato pubblico read-only EU-ok). **Limite noto registrato**: su SOL/BONK in Fase 3 la divergenza tra venue può essere maggiore — non blocca la 2b, va ritrovato quando ci arriviamo |
| 2026-07-22 (S122) | **Fee-drag: opzione (A) osservare**, NON minimo `sell_pct` Kraken-aware adesso — ma con **obbligo di misura** (4 numeri a fine 2b: n° trade, fee totale, P&L lordo vs netto, `sell_pct` medio Sherpa) | Fissare ora una tara significherebbe inventare un numero senza dati e poi difenderlo. Il collaudo serve a produrlo. Ma "osservare" senza strumenti equivale a non fare niente: la misura è nello scope del brief `sherpa-on-kraken` |
| 2026-07-22 (S122) | **Restart unico** per la finestra 2b — il codice nuovo e l'accensione Kraken vanno live insieme. Proposta CEO di restart in due tempi **ritirata dal CEO stesso** dopo obiezione del Board | Il CEO proponeva una notte di osservazione sui soli grid testnet prima di mettere denaro vero. Max ha chiesto perché. Motivo del ritiro: in T0 la riga Kraken sarebbe stata `is_active=false`, quindi il codice davvero nuovo (Sherpa che legge la riga Kraken + fix volatilità) **non sarebbe stato esercitato**. Si sarebbero spese 24h per osservare la parte già coperta dai 340 test, accendendo comunque al buio il giorno dopo. **Obiezione del Board superiore alla proposta del CEO** |
| 2026-07-22 (S122) | **CoinMarketCap Pro API (piano free) scartata come sorgente volatilità** | Il free dà prezzo live aggiornato ogni minuto, non serie storica (lo storico è a pagamento). Costruirsi la serie campionando richiederebbe codice nuovo + giorni di accumulo + gestione buchi, per ottenere ciò che Binance dà già pronto e gratis. **Parcheggiata** invece come possibile sorgente per il Sentinel (dominance, market cap, breadth) — vedi §5 |

---

## §5 — Domande aperte per CC (idee non ancora pronte per brief)

Aggiungere:

- **CoinMarketCap free API come sorgente dati Sentinel** — dominance BTC, market cap totale, dati di ampiezza su molte monete. Account già attivo (15.000 crediti/mese, 50 req/min, 40+ endpoint). Vicino al segnale **Breadth Tier 3 parcheggiato in S109**. *Prerequisito prima di progettare qualsiasi cosa: verificare cosa copre davvero il piano free.* Parcheggiata in S122, non è un gate del go-live.
- **`tf.html:1459`** — formula trigger grid applicata ai bot TF (incoerenza pre-esistente, verificata da CC in S122, fuori scope). Micro-brief dedicato, priorità bassa (TF non trada in v3).
- **Orchestrator: rilegge `is_active` di continuo o solo all'avvio?** — domanda posta a CC nel brief `sherpa-on-kraken`. Determina se accendere/spegnere una riga Kraken costerà sempre un restart della flotta.

---

## §3 — Diary status

- Volume 4 "From Eyes to Live" — in corso. S122 = `The One Where the Board Just Asked Why`, status **BUILDING** su Supabase (S121 chiusa COMPLETE).
