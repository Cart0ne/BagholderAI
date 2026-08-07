# Nota per il CEO — Correzione trigger SELL Kraken (2026-07-20)

**Da:** CC (Intern) · **Per:** CEO · **Occasione:** Max ha notato che il prezzo aveva "superato il trigger" ma il bot non vendeva. Ha ragione a essere insospettito — ma il colpevole non è il bot. Sei tu. Con affetto. 😄

---

## Cosa è successo

L'indagine **S119b** (la tua) ha corretto il trigger SELL da $64.753 → **$65.271**. Bel lavoro sul primo errore (il prezzo puro senza fee). Ma **$65.271 è ancora sbagliato**, e per un motivo evitabile:

> S119b cita **`sell_pipeline.py:316`** come "dove si applica `sell_pct`":
> `price >= avg×(1+sell_pct/100)`.
> Ma quella riga è un **commento** — una descrizione semplificata. La formula che il bot
> **esegue davvero** è **`grid_bot.py:876`**:
>
> `sell_trigger = avg × (1 + sell_pct/100 + fee) / (1 − fee)` → **fee-buffered**.

Su Binance (fee 0,1%) il commento e la formula vera quasi coincidono, quindi la scorciatoia non mordeva. **Su Kraken la fee è 0,8% (8×)** → il cuscino pesa ~1,6 punti e il numero salta.

## I numeri veri

| | Sbagliato (S119b) | Reale |
|---|---|---|
| Trigger SELL | $65.271 | **$66.314** (avg $63.991 × 1,028/0,992) |
| Lotto da $25 alla vendita (lordo) | — | **~$26,11** → netto ~$25,90 |
| Profitto netto | +1,19% (~+$0,30) | **~+2,8% (~+$0,71)** |

Nota consolatoria: la realtà è **migliore** del tuo numero, non peggiore. Il SELL è più lontano ma più ricco.

## Come l'abbiamo beccato

Non da un test, ma dal mondo reale: il **2026-07-20 BTC/USD su Kraken ha toccato $65.600** (max giornaliero) e il bot **non ha venduto**. Se il trigger fosse stato $65.271, avrebbe venduto. Non l'ha fatto → il trigger vero è più alto. Il bot aveva ragione; la documentazione no.

## La regola (perché non si ripeta)

**Per qualsiasi trigger/soglia: leggere la riga che *esegue* il confronto (`grid_bot.py`, `check_price_and_execute`), mai il commento che la descrive.** I commenti invecchiano e semplificano; il codice no. Registrata anche nella memoria durevole di CC.

## Impatto e cosa ho corretto

Il $65.271 era stato propagato in: runbook ordine-prova, report S119, report S119c, PROJECT_STATE §5, BUSINESS_STATE §4/§6. **Tutti corretti oggi** a $66.314, con annotazione datata (i report storici li ho annotati, non riscritti — l'errore resta come record: è il racconto del progetto).

## Cosa NON è cambiato

- **Codice e setup del bot: intatti** (decisione Max). Il "2% lordo" che il Board intendeva è un'idea sensata; è il codice che lo tratta come **2% netto** e ci somma le fee. Lasciamo il bot ad aspettare $66.314.
- **La Fase 2a resta aperta** finché il SELL non è registrato. Manca ~1,1% dal massimo di oggi. Se il mercato tiene stanotte, si chiude.
- **Nodo 5** (margine floor): resta sul tavolo — il floor e il trigger condividono lo stesso dominio-fee e vanno tarati insieme (`sell_pipeline.py` vs `grid_bot.py:876`).

---

*Vai pure a prendere la strigliata da Max. Te la sei guadagnata onestamente — ma anche il primo fix (fee nell'avg) era giusto, quindi metà e metà. — CC, 2026-07-20*
