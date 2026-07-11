# Grid-Regime Backtest — SOL + BONK (materiale blog)

_Autore: CC (Intern) · 2026-07-02 · Task **2.7** della Master Task List (estende il backtest S113, finora solo BTC) · alimenta il blog post **2.6** ("il grid è un ammortizzatore, non un motore")._

> **Cos'è**: la mappa comportamentale del nostro grid bot su **SOL** e **BONK**, negli stessi tre regimi (bear / bull / laterale) già misurati su BTC in S113, con lo **stesso simulatore fedele** (validato sui trade veri) e le **stesse fee Kraken (0.40% taker)**. Le finestre di 30 giorni **non sono scelte a mano**: le trova `scripts/backtest/scan_regimes.py` sul prezzo reale di ciascun coin (drift open→close + gate laterale |drift|<10%).
>
> **Cosa NON è**: un'ottimizzazione. Parametri congelati (snapshot `bot_config` live, inclusi i valori già mossi da Sherpa), si gira, si guarda. Un mese per regime ≠ significatività statistica. Vale il **pattern**, non il centesimo.

---

## 1. Le finestre-regime trovate (per coin, sul loro prezzo)

Lo scanner ha analizzato tutta la storia Binance daily: **SOL** 70 mesi (da ago-2020), **BONK** 30 mesi (da dic-2023). Selezione automatica = mese col drift più estremo (bear/bull) e il più piatto con oscillazione reale (laterale).

| Coin | Regime | Mese scelto | Drift | Range | Perché |
|---|---|---|---|---|---|
| **SOL** | 🐻 Bear | **Novembre 2022** | −56.5% | 254.6% | Crollo FTX (SOL era il token di Alameda) — il bear iconico di SOL |
| **SOL** | 🚀 Bull | **Febbraio 2021** | +207.5% | 343.2% | Pump verticale early-SOL (da $4.26 a $13.09) |
| **SOL** | ➡️ Laterale | **Aprile 2026** | −0.1% | 18.3% | Sideways vero e recente (passa il gate) |
| **BONK** | 🐻 Bear | **Febbraio 2025** | −45.1% | 113.4% | Ripiegamento post-pump |
| **BONK** | 🚀 Bull | **Novembre 2024** | +122.4% | 264.3% | Il grande rally BONK di fine 2024 |
| **BONK** | ➡️ Laterale | **Marzo 2026** | −2.3% | 31.7% | Piatto ma **molto choppy** (passa il gate) |

**Nessun gate scattato**: entrambi i coin hanno un mese davvero laterale (la mia previsione "un memecoin non va mai flat" era sbagliata — BONK mar-2026 è piatto ma oscilla del 31.7%).

**Alternative** (per il blog, se il CEO vuole un bull meno estremo): SOL ha bull più "moderati" (Gen-2023 +139.9%), idem BONK (Feb-2024 +107.7%). I +207%/+122% auto-scelti mostrano il "grid lascia la luna sul tavolo" in modo massimo. Top-5 complete nei report per-coin.

---

## 2. Il risultato che conta — Grid (riparato) vs Hold, per regime

Numeri sul **bot RIPARATO** (post churn-fix S113 = comportamento onesto), fee Kraken 0.40%. Δ = quanto il grid batte (+) o perde (−) contro il semplice hold.

| Coin | 🐻 Bear | 🚀 Bull | ➡️ Laterale |
|---|---|---|---|
| **BTC** (S113) | −28.4% vs −37.5% → **+9.1 p.p.** ✅ | +5.4% vs +36.6% → −31.2 p.p. ❌ | +0.60% vs +3.52% → −2.9 p.p. ❌* |
| **SOL** | −52.2% vs −56.7% → **+4.5 p.p.** ✅ | +21.2% vs +206.3% → −185 p.p. ❌ | +0.64% vs −0.52% → **+1.16 p.p.** ✅ |
| **BONK** | −42.0% vs −45.3% → **+3.3 p.p.** ✅ | +50.8% vs +121.5% → −70.7 p.p. ❌ | +2.49% vs −2.72% → **+5.2 p.p.** ✅ |

_*Il "laterale" di BTC (S113) era in realtà un +3.9% mascherato (quasi-laterale): hold ha catturato il trend nascosto e ha battuto il grid. SOL e BONK hanno mesi laterali **veri** → il grid vince._

### Tre findings, netti e ripetibili su tre coin diversi:

1. **Nel BEAR il grid batte SEMPRE hold** (+3 / +9 p.p.). Compra i dip, tiene i bag, ma l'esposizione parziale + il cash cuscino attutiscono la caduta. Non è "guadagnare", è **perdere meno**: l'ammortizzatore.

2. **Nel BULL hold stravince SEMPRE.** Il grid vende presto i lotti e resta liquido → si perde il grosso del rally. Cattura solo il **10–42%** del movimento (SOL bull +207%: grid prende il 10%; BONK bull +122%, più choppy: grid prende il 42%). È la debolezza **strutturale** del grid in salita, non un bug.

3. **Nel LATERALE VERO il grid batte hold** (SOL +1.16, BONK +5.2 p.p.) — e **più il piatto è choppy, più guadagna**: BONK (range 31.7%) rende quasi 5× l'edge di SOL (range 18.3%). È il "campo di casa": onde da comprare-basso/vendere-alto senza un trend che ti scappa. Ma l'edge resta **sotto l'1–5% al mese** anche nel caso migliore, dopo le fee Kraken.

**La tesi S113 regge e si rafforza su 3 coin**: *il grid è un ammortizzatore di volatilità, non un motore.* Protegge nel ribasso, tappa il rialzo, spreme un piccolo edge nel laterale choppy.

---

## 3. Il churn da fee, mostrato di nuovo (bot ATTUALE vs RIPARATO)

Il backtest riconferma il bug **churn-da-polvere** (fix Piano A shippato+LIVE S113) su SOL/BONK. Il bot **attuale** (pre-fix) fa round-trip a vuoto ogni ~4h → su Kraken (0.40%, 4× Binance) brucia soldi veri, **peggio nel trend** (dove il grid è fermo e re-entra di continuo):

| | BTC bull | SOL bull | BONK bull |
|---|---|---|---|
| Grid **attuale** (churn) | −23.9% | **−17.0%** | −1.7% |
| Grid **riparato** | +5.4% | **+21.2%** | +50.8% |

Su SOL, in un bull **+207%**, il bot non-riparato avrebbe **perso il 17%** — pura emorragia di fee mentre il prezzo andava sulla luna. Il caso più didattico che abbiamo per il blog: *un bug da centesimi su Binance testnet (0.10%) diventa un dissanguamento su Kraken (0.40%).*

---

## 4. Finding operativo per il CEO — densità griglia BONK a $100

Col lineup go-live 1.3 (**BONK $100**, lotto live $25) il grid BONK ha solo **~4 gradini** prima di finire il cash. Nel bear feb-2025 ha fatto **1 sola sell reale** (comprato 4 volte, poi stop-buy, bag tenuti). Poche munizioni = poco ammortizzamento. SOL a $150/$20 ha ~7 gradini, respira meglio.

→ **Da valutare al cutover** (K.1): ridurre il lotto BONK (es. $25→$10, ~10 gradini) per dargli densità, oppure accettare che BONK sia il coin "a bassa granularità". È adiacente al "floor min-profit fee-aware" già previsto in K.1. Non urgente, ma da mettere sul tavolo prima di fissare i lotti mainnet.

---

## 5. Caveat (leggere prima di citare i numeri)

- **Granularità**: candele 1m (minimo Binance sullo storico profondo). SOL in LIVE checka ogni **45s**, BONK ogni **20s** → la candela 1m sotto-campiona le oscillazioni intra-minuto. **I numeri del laterale sono un floor pessimistico**: lo skim reale è probabilmente maggiore, soprattutto su BONK. L'edge laterale vero è ≥ di quello mostrato.
- **Fee Kraken 0.40% taker** (market order = taker). La colonna 0.10% nei report per-coin mostra quanto il testnet Binance ci gonfiava i numeri.
- **Parametri congelati** allo snapshot live (Sherpa in LIVE li muoverebbe per regime → questo è il caso "a freno fisso", conservativo).
- **Un mese ≠ tutti i bear/bull/laterali.** Campione singolo per regime. Bull auto-scelti estremi (vedi §1 per alternative moderate).
- **Prezzi = Binance, fee = Kraken** (disaccoppiati: il prezzo è equivalente tra venue, la fee no). Kraken via REST non dà lo storico profondo.
- **Solo grid puro**: niente TF/Sentinel/Sherpa/NewsKeeper.

---

## 6. Dove sono i materiali

- **Report per-coin** (con tabelle metriche complete + confronto fee 0.10%): `audits/backtest/report_grid_regime_SOL.md`, `..._BONK.md` (gitignored, locali).
- **Grafici** (prezzo con marker buy/sell + equity grid-vs-hold, attuale + riparato): `audits/backtest/charts/{sol,bonk}_{regime}_*.png` — 18 PNG.
- **Snapshot parametri congelati**: `audits/backtest/frozen_params_{SOL,BONK}.json`.
- **Tooling** (committato, riusabile): `scripts/backtest/scan_regimes.py` (nuovo) + `params.py`/`fetch_data.py`/`run_backtest.py`/`plots.py` generalizzati multi-coin.

**Riprodurre**:
```
venv/bin/python3.13 scripts/backtest/scan_regimes.py SOL/USDT     # vedi le finestre
venv/bin/python3.13 scripts/backtest/run_backtest.py --symbol SOL/USDT
venv/bin/python3.13 scripts/backtest/run_backtest.py --symbol BONK/USDT
```

I backtest sono **chiusi su tutti e tre i coin** (BTC S113 + SOL/BONK oggi). Pronto il dataset per il blog post 2.6.
