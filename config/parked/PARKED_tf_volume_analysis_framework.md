# PARKED — TF Volume Analysis Framework (Gambe 2+3)

**Origine:** S108 (2026-06-22), analisi barometro
**Tipo:** Caso 2 (non blocca go-live)
**Stima:** Brief CC medio, 2-3 sessioni di lavoro

---

## Contesto

In S108 (mini-sessione mobile) l'analisi dei segnali TF ha mostrato che il volume non discrimina tra vincitori e perdenti sotto 2M (BICO +100% a 0.67M, HMSTR -53% a 0.61M). Sopra 2M le perdite si comprimono (-1% a -5%) ma i moonshot spariscono. La soglia ~2M potrebbe essere più utile del range 10-20M ipotizzato inizialmente.

## Le tre gambe

**Gamba 1 (FATTA in S108):** Dati interni — validazione chiamate barometro vs market, latenza, cross-ref TF breadth per tier. Risultato: Tier B è l'indicatore di regime più pulito (0% = extreme fear confermato, >15% = possibile cambio regime).

**Gamba 2 (DA FARE):** Dati storici Binance — backtest EMA/RSI su dati storici via API Binance, verifica soglia 2M volume, performance per tier. Richiede: script Python che scarica candele storiche + calcola gli stessi indicatori del TF live + confronta con i risultati reali.

**Gamba 3 (DA FARE):** Bibliografia — volume come filtro (quali paper accademici o industry report trattano il volume come discriminante?), market breadth (l'idea di usare % bullish per tier come leading indicator ha precedenti?), social sentiment su microcap (validazione dell'idea TF → X API).

## Prerequisiti

- Nessuno per gamba 2 (API Binance pubblica, dati storici gratuiti)
- Nessuno per gamba 3 (ricerca desk)
- NON dipende dal verdetto barometro
- NON dipende dal go-live

## Note

Gamba 2 e 3 possono essere parallelizzate. Il brief per CC dovrebbe separare le due gambe in task indipendenti.
