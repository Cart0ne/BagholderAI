# PARKED — TF Signal → X API Pump Detection

**Origine:** S108 (2026-06-20, mini-sessione mobile)
**Tipo:** Caso 2 (non blocca go-live)
**Stima:** Esploratoria, richiede verdetto barometro + dati gamba 2 prima di costruire

---

## Idea strategica

Pipeline automatizzata: quando il TF genera un segnale bullish su una coin, fare un check automatico via X API sulle menzioni di quella coin.

- **Volume social basso** = segnale genuino (il mercato non ne sta ancora parlando)
- **Volume social alto** = possibile pump coordinato (Telegram groups, influencer push)

Se il segnale passa il filtro: posizione €10 testnet.

## Perché è interessante

Il TF scansiona 60-76 coin e genera segnali tecnici (EMA/RSI/ATR). Ma i segnali tecnici sulle microcap sono spesso inquinati da pump coordinati che creano pattern tecnici artificiali. Un filtro social potrebbe distinguere tra un breakout organico e uno artificiale.

## Prerequisiti

- **Verdetto barometro** — non strettamente necessario, ma il barometro usa news sentiment e questa idea usa social sentiment. Meglio avere i risultati del primo prima di costruire il secondo.
- **Dati gamba 2** (PARKED_tf_volume_analysis_framework.md) — il backtest storico darebbe una baseline per misurare se il filtro social aggiunge valore.
- **X API** — attualmente pay-per-use ~$0.04/scan. Copre: tweet write, own timeline read, user lookup. NON copre: full-archive search, realtime stream, mentions scraping (Basic $200/mese+). Il check menzioni richiederebbe almeno il tier Basic oppure un proxy (scraping, terze parti).

## Costo stimato

- Se usiamo l'X API attuale (limitata): ~$0.04 per coin per check. Con 5-10 segnali TF al giorno = $0.20-$0.40/giorno.
- Se serve il tier Basic per mentions: $200/mese — giustificabile solo con MRR positivo.
- Alternativa low-cost: usare Google Trends API o Reddit mentions come proxy (meno preciso, ma gratuito).

## Rischi

- I pump coordinati possono essere silenziosi su X ma attivi su Telegram (non misurabile senza accesso a gruppi privati).
- Il lag tra segnale TF e check social potrebbe essere troppo alto (il pump è già partito quando facciamo il check).
- Falsi negativi: coin genuinamente buone con hype social alto (es. post-listing su exchange major).

## Prossimo passo

Non costruire. Prima completare gamba 2+3 del volume analysis framework. Se i dati confermano che il volume discrimina, il filtro social diventa un raffinamento. Se il volume non discrimina, il filtro social non aiuterà.
