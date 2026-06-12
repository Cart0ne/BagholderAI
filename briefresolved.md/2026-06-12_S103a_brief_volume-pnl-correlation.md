Brief S103a — volume-pnl-correlation — 2026-06-12

# Analisi correlazione Volume ↔ PnL — dati paper trading + fonti esterne

## Contesto

Il CEO ha fatto una prima esplorazione dei dati paper trading (24 apr — 8 mag 2026)
contenuti in due file JSONL archiviati. Risultati preliminari su 56 coppie
ALLOCATE→DEALLOCATE:

- Win rate complessivo: 26.8%, PnL medio: +0.68%
- Tier C (shitcoin): WR 36%, PnL +0.94% — meglio di Tier B (WR 15%, PnL +0.04%)
- Pattern controintuitivo: le coin a basso volume performano meglio
  - Q1 volume (più basso): PnL +1.33%, WR 43%
  - Q4 volume (più alto): PnL +0.96%, WR 21%

Questi numeri sono suggestivi ma il campione è piccolo (14 trade per quartile).
Serve un'analisi rigorosa + validazione esterna.

## File dati

I due file JSONL sono nell'archivio locale del progetto (Max li fornirà):
- `trend_scans.jsonl` — 32.257 scan, 163 symbol, Tier A/B/C, campi: symbol,
  tier, price, volume_24h, ema_fast, ema_slow, rsi, atr, signal, signal_strength
- `trend_decisions_log.jsonl` — 1.412 decisioni, 38 symbol, azioni:
  HOLD/ALLOCATE/DEALLOCATE/ALLOCATE_FAILED, con signal e reason

Periodo: 24 aprile — 8 maggio 2026 (pre-testnet, TF operava su tutti i tier).

## Cosa deve fare CC

### Parte 1 — Analisi interna (dati nostri)

1. **Ricostruire tutte le coppie ALLOCATE→DEALLOCATE** per symbol. Matchare con
   il prezzo dallo scan più vicino (stesso symbol, timestamp ±6h max) per
   calcolare PnL teorico entry→exit.

2. **Analisi correlazione volume_24h vs PnL:**
   - Correlazione di Pearson e Spearman (volume vs PnL %)
   - Quartili di volume con breakdown PnL / WR (confermare o smentire
     l'esplorazione CEO)
   - Scatter plot volume vs PnL con regressione
   - Separare per tier (A, B, C) — la correlazione potrebbe esistere in un
     tier e non in un altro

3. **Analisi complementari:**
   - Durata media dei trade (ALLOCATE→DEALLOCATE) per tier e per esito
   - Signal strength al momento dell'ALLOCATE: correla con il PnL?
   - RSI al momento dell'ALLOCATE: correla con il PnL?
   - Distribuzione dei motivi di DEALLOCATE (STOP-LOSS vs TRAILING-STOP vs
     ORPHAN_PERIOD_CLOSE) — quale motivo correla con le perdite peggiori?

4. **Controllo condizioni di mercato nel periodo:**
   - BTC nel periodo 24 apr — 8 mag: era bull, bear, laterale?
   - I risultati sono condizionati da un regime specifico?

### Parte 2 — Validazione esterna (dati e ricerche online)

5. **Ricerca letteratura/blog/studi:**
   - Esiste ricerca (accademica, blog quantitativo, forum di trading) sulla
     relazione tra volume e rendimento per le altcoin/shitcoin?
   - Il pattern "low volume → higher returns on bullish signal" è noto?
     Ha un nome? Ha spiegazioni (es. "liquidity premium", "small cap effect")?

6. **Dati storici esterni (se accessibili):**
   - Usare API gratuite (CoinGecko, CoinMarketCap, etc.) per tirare giù
     dati storici volume + prezzo per un set di altcoin Tier C (microcap)
     e verificare se il pattern regge su un periodo più lungo (es. 6-12 mesi)
   - Se le API gratuite non bastano, documentare cosa servirebbe (costo, tier)
     e proporre alternative (dataset pubblici, Kaggle, etc.)

## Output atteso

Un **report leggibile** (`2026-06-12_S103a_RforCEO_volume-pnl-correlation.md`)
con:
- Risultati con numeri e grafici (salvati come .png, referenziati nel report)
- Conclusione: il volume è un fattore utilizzabile per filtrare i segnali
  del TF? Se sì, in quale direzione (favorire alto o basso volume)?
- Raccomandazione: vale la pena aggiungere un filtro volume allo scanner?
  Se sì, quale soglia/logica? Se no, perché?
- Sezione "Validazione esterna": cosa dice la letteratura, eventuali dati
  esterni analizzati

## Decisioni delegate a CC

- Scelta delle librerie Python per l'analisi (pandas, matplotlib, scipy ok)
- Scelta delle API esterne da usare (preferire gratuite)
- Formato e layout dei grafici

## Decisioni che CC DEVE chiedere a Max

- Se il report suggerisce di aggiungere un filtro volume al TF scanner:
  NON implementare, solo proporre. La decisione è del Board.
- Se le API gratuite richiedono registrazione o API key: chiedere prima.
- Se emergono finding inattesi (es. il pattern si inverte per Tier B):
  segnalare, non interpretare autonomamente.

## Vincoli

- **NON toccare codice del bot, dello scanner, o di Sentinel.** Questo è
  un task di ANALISI, non di sviluppo.
- **NON scrivere in Supabase.** Solo lettura dei file JSONL forniti.
- **NON restartare il bot.** (regola standard — Max restarta manualmente
  sul Mac Mini)

## Roadmap impact

Nessuno diretto. Se il report conferma che il volume è un fattore utile,
diventa un candidato per il prossimo ciclo di miglioramento dello scanner
(post-verdict barometro, ~23 giugno).

## Auto-obiezione CEO

Il campione interno è di 56 trade su 2 settimane in un singolo regime di
mercato. Anche con validazione esterna, potremmo trovarci davanti a un
pattern che vale solo in fase laterale/rialzista e si inverte in bear market.
Il rischio è costruire un filtro su un artefatto statistico. Per questo
il report DEVE includere il contesto di mercato del periodo e, se possibile,
verificare il pattern su periodi con regimi diversi usando dati esterni.
