# Report for CEO — S109: Tier-breadth regime signal (analisi dati)

**Data:** 2026-06-25
**Sessione:** S109
**Brief sorgente:** `config/2026-06-18_brief_tier-breadth-regime-signal.md` + **nota integrativa `_bis`** (`config/2026-06-25_S109_nota-integrativa_breadth-signal_bis.md`, che assorbe la gamba 2 di `PARKED_tf_volume_analysis_framework.md`).
**Script:** `scripts/breadth_analysis_s109.py` (read-only, API pubblica Binance + alternative.me).
**Asset:** `report_for_CEO/assets/breadth_s109_series.png`, `breadth_s109_scatter.png`.

---

## Verdetto in una riga

> **PARCHEGGIA.** Nel campione disponibile la breadth Tier 3 **non anticipa** i rimbalzi di Tier 1/2 — semmai mostra un debole pattern **contrarian** (froth → top locale). Ma il semestre è stato dominato dal *fear*, quindi manca il regime risk-on in cui l'ipotesi dovrebbe valere: il caso pro-ciclico **non è falsificabile** con questi dati. Da **ri-testare dopo un cambio di regime risk-on sostenuto**. **Non cablare nulla in Sentinel ora.**

---

## Metodo (survivorship-safe, come da indicazione CEO)

- **Universo completo**: 427 USDT pair su Binance (status TRADING), meno stablecoin e leveraged token → **422 usabili** (≥60 candele). NON i "top-N di oggi".
- **Klines 4h**, finestra **2025-12-25 → 2026-06-24** (182 giorni) + warmup. **74.053 coin-giorni**.
- **Tier per-data**: il volume 24h è ricalcolato ogni giorno dalle candele di quel giorno (`quote_asset_volume`). Coin delistate/nuove gestite naturalmente (no candele fuori dal loro periodo). Soglie 100M / 20M. T3-micro <$2M, T3-mid $2–20M.
- **Classificazione**: riusato **il classifier LIVE del bot** (`classify_signal`, EMA20/50, RSI14, ATR14) — "BULLISH" significa esattamente ciò che intende il bot.
- Copertura media: **T1 ≈6, T2 ≈17, T3 ≈384 coin/giorno** (micro ≈283, mid ≈101).

**Contesto di mercato del campione:** F&G medio **21.9** (range 5–61 = *fear/extreme fear*); solo **43%** dei giorni ha un forward T1/7g positivo (media **−1.87%**). Semestre risk-off → poche transizioni reali.

---

## Risultati — risposta alle 5 domande della nota `_bis`

**1. Lead/lag — la breadth T3 anticipa i rimbalzi T1/2?** → **NO.**
Correlazione breadth T3[t] vs forward return:
| orizzonte | vs T1 | vs T2 |
|---|---|---|
| 24h | −0.04 | −0.09 |
| 3g | −0.06 | −0.11 |
| 7g | −0.03 | −0.11 |

Tutte ≈0 o leggermente negative. Forward **condizionato** (T3 breadth alta vs bassa): quando T3 si accende il forward è **peggiore**, non migliore — es. T1 24h **−0.47%** (T3 alta) vs **+0.26%** (T3 bassa); T2 7g **−3.13%** vs **−1.90%**.

**2. Volume come filtro (T3-mid vs T3-micro)?** → **direzione giusta, magnitudo nulla.**
corr vs forward T1: **T3-mid −0.004 / −0.014 / +0.02** vs **T3-micro −0.057 / −0.068 / −0.041**. Il **mid è meno rumoroso del micro** (conferma che sotto $2M è rumore, coerente con l'analisi S108), ma **nessuno dei due predice** un rimbalzo. La soglia $2M separa il rumore, non crea segnale.

**3. F&G ci arriva prima o dopo?** → **F&G domina, e la breadth T3 è ridondante.**
corr F&G vs forward T1: **−0.10 / −0.19 / −0.29** — più forte (in senso contrarian) della breadth T3. E `corr(F&G, breadth_t3) = 0.395`: la breadth T3 si muove **con** F&G. Quindi **non aggiunge informazione** oltre F&G → l'obiezione anti-assenso §6.1 del brief originale **resta aperta**.

**4. Falsi positivi?** → **alti.** Solo **4** giorni di spike T3 (breadth ≥20% dopo ≤10%) in 6 mesi; **50%** sono falsi positivi (forward T1/7g ≤ 0). Il caso da manuale: **13-gen** breadth T3 22.5% → T1 **−9.3%**, T2 **−14.6%** a 7g (froth pre-crollo).

**5. Direzione?** → **contrarian debole**, non pro-ciclico. Quando la T3 si "accende" il rischio è di essere a un **top locale**, non all'inizio di un rialzo. Ma magnitudo piccola + soli 4 episodi → non operativizzabile.

---

## Perché "parcheggia" e non "boccia"

L'ipotesi del Board è **pro-ciclica** ("quando l'appetito al rischio torna, il denaro rientra prima nelle small-cap e poi sale ai blue chip"). Per testarla servono **episodi di risk-on reale**. Il campione 6 mesi è stato monotonamente *fear* (F&G medio 21.9): non c'è stato il regime in cui il segnale dovrebbe accendersi per la ragione giusta. Quanto osserviamo (froth contrarian) è coerente con un mercato che rimbalza tecnicamente dentro un bear, non con un risk-on strutturale.

→ **Parcheggia**, ri-testa dopo ≥ qualche settimana di F&G > 50 / bull confermato. Questo allinea con la tua auto-obiezione ("se monotono bear → parcheggia") e con la mia (direzione + pochi episodi).

## Limiti dichiarati (credibilità)
- **Classifier è un proxy** (EMA20/50 4h): se troppo grossolano potrebbe mascherare un segnale fine. L'assenza di segnale qui non prova l'assenza in assoluto.
- **Survivorship residuo**: l'universo parte dai simboli *attualmente* quotati; le coin **delistate prima di oggi** non hanno klines e mancano del tutto (Binance non espone la lista storica dei delisting via API pubblica). Mitigato (non i top-di-oggi, ma l'intero universo per tutto il loro periodo di quotazione), non azzerato.

## Effetto collaterale: gamba 2 del volume framework → CHIUSA
La nota `_bis` assorbiva la **gamba 2** di `PARKED_tf_volume_analysis_framework.md` (soglia volume 2M). Risultato: **la soglia $2M discrimina il rumore (T3-micro) ma non produce segnale predittivo**. Gamba 2 si considera chiusa con esito negativo. Resta parcheggiata solo la **gamba 3** (bibliografia, desk research).

---

## Raccomandazione operativa
1. **Nessun cablaggio** breadth→Sentinel ora.
2. **Re-run dello stesso script** (è deterministico e cache-based) **dopo il prossimo regime risk-on** — basterà rilanciarlo, l'analisi si aggiorna sola.
3. Se mai si volesse un segnale di "froth contrarian" T3 come **protezione** (alza guardia quando T3 si surriscalda in greed), quello ha un accenno di evidenza qui — ma è materiale per un brief separato, non per questo.

*Roadmap impact: none (analisi read-only, nessun codice bot/DB/restart).*
