# S78 fase 2 — SWEEP/LAST SHOT slippage buffer + banner fix SHIPPED + LIVE

**Da:** Claude Code (Intern)
**Per:** CEO + Board (Max)
**Data:** 2026-05-16 sera
**Brief di riferimento:** [config/brief_78b_sweep_slippage_buffer.md](../config/brief_78b_sweep_slippage_buffer.md) (tracked in `config/`)
**Modalità:** diagnosi 3-step su sintomi dashboard `/grid` → 2 ipotesi smentite empiricamente → root cause vera → fix mirato
**Test suite:** 4/4 nuovi (`test_sweep_slippage_buffer.py`) + 30/30 non-regression (`test_accounting_avg_cost.py`)
**Restart bot:** **FATTO** — Mac Mini PID parent 33579, log `/Users/max/orchestrator_20260516_214616.log`

---

## 0. TL;DR

Board ha notato sul `/grid`:
- **Q1**: BONK non flaggato "tapped out" come BTC/SOL nonostante allocazione satura
- **Q2**: "Cash to reinvest" = -$0.39

Diagnosi profonda ha smentito **due** ipotesi iniziali:
1. ❌ "bot capital guard ignora skim_reserve" → smentita: [`grid_bot._available_cash()`](../bot/grid/grid_bot.py#L210-L224) **già** sottrae `reserve_ledger.get_reserve_total()`. Funziona da sempre.
2. ❌ "drift inventory BONK vs fetch_balance" → smentita: 33.898 BONK delta ma sono attribuibili al fantasma testnet S72, non al bot.

**Root cause vera**: SWEEP/LAST SHOT path manda base_order su `cost = cash_before`. Binance esegue con slippage positivo (+1.19% sul trade BONK del 2026-05-15 05:39: check $0.00000671 → fill $0.00000679), quindi `res["cost"]` reale è $46.10 mentre cash_before era $45.66. **Drift singolo trade: +$0.44 over cassa attesa.**

**Decisione Board**: SWEEP/LAST SHOT è **by design** ("no cash morto non investibile"). Drift sub-dollar accettabile su testnet. Ma:
- In **mainnet**, Binance rifiuta `-2010 INSUFFICIENT_FUNDS` quando `base × fill_price > USDT free`. Il pattern attuale rischia REJECT sistematico.

**Fix**: `HardcodedRules.SLIPPAGE_BUFFER_PCT = 0.03` (3% uniforme). Applicato a SWEEP + LAST SHOT cost. Calibrato su slippage testnet BONK osservata (2.46%). Per-coin scartato perché mainnet coin mix non ancora deciso (premature).

**Side effect**: il banner top `grid.html` `=== 0` ora `<= 0`, con testo "swept, $X over by slippage" per `buysLeft < 0` (caso fisiologico post-SWEEP, non patch).

---

## 1. Cosa è stato fatto

**Codice (4 file)**:
| File | Δ | Cambio |
|---|---:|---|
| [config/settings.py](../config/settings.py) | +9 | `SLIPPAGE_BUFFER_PCT = 0.03` in `HardcodedRules` con commento esteso |
| [bot/grid/buy_pipeline.py](../bot/grid/buy_pipeline.py) | +6 −4 | Buffer applicato a SWEEP (L100) e LAST SHOT (L110); log riga aggiornata con `cost` post-buffer |
| [web_astro/public/grid.html](../web_astro/public/grid.html) | +5 −1 | Branch `buysLeft < 0` con testo "swept, $X over by slippage" |
| [tests/test_sweep_slippage_buffer.py](../tests/test_sweep_slippage_buffer.py) | +192 | NEW. 4 scenari: normal/SWEEP/LAST SHOT/below MIN_LAST_SHOT |

**Commit pushati su `main`**:
- `dcc4372` — blog post 2 "The Day Our Bot Ran Out of Money" + fix `.gitignore` anchored (collaterale: scoperto che `blog/` matchava ricorsivamente anche `web_astro/src/content/blog/`)
- `afd97ce` — brief 78b implementation (codice + test)
- `64d6c89` — docs: PROJECT_STATE S78 fase 2 commit hash

**Verifica empirica restart Mac Mini (21:46 CET 2026-05-16)**:
- Graceful kill PID 90540 (15s wait → 0 processi) → relaunch caffeinate
- 6 processi nuovi (PID parent 33579) attesi e presenti
- Brain flags: TF=False, SENTINEL=True, SHERPA=True
- Telegram messages sent (orchestrator started)

---

## 2. Cronologia diagnostica (perché il primo brief era sbagliato)

Storia onesta perché credo serva al CEO sapere come è andato il percorso, non solo il risultato.

**Step 1 — Ipotesi iniziale "skim-aware guard mancante"**:
Vedendo `cashLeft = alloc − netSpent − skim ≈ −$0.50 BONK`, ho dedotto che il bot facesse buy basandosi solo su `alloc − netSpent` (ignorando skim) mentre dashboard sottraeva skim. Brief 78b v1 proponeva guard skim-aware + replay byte-identical.
CEO ha approvato con 2 note (no-silent-fallback + byte-identity formula).
**Smentita**: prima di toccare codice, ho verificato `_available_cash()` e ho trovato che già sottrae `reserve_ledger.get_reserve_total()`. Ipotesi falsa.

**Step 2 — Ipotesi "drift inventory BONK"**:
`fetch_balance()` mostrava 21.596.414 BONK vs DB raw 21.630.313 BONK → drift +33.898 BONK. Sospettato fee-in-base-coin che non viene sottratto al DB.
**Smentita**: il dashboard JS `grid.html` già sottrae `feeNativeEst = feeUsdt/price` nel calcolo holdings (line 610-611). Il drift osservato è il fantasma testnet S72 (memoria `project_s72_fee_unification_diagnosis`).

**Step 3 — Root cause vero, verificato sui dati**:
Ricostruita cronologia BONK trade-per-trade via SQL window function. Il trade incriminato è **2026-05-15 05:39:17**:

| | valore |
|---|---:|
| cum_invested pre-trade | $335.11 |
| cum_received | $233.37 |
| cum_skim | $2.60 |
| cash_before (formula skim-aware) | **$45.66** |
| path attivato | SWEEP (remaining $20.66 < standard $25) |
| cost richiesto | $45.66 |
| base_order qty | 6.8M BONK = $45.66 / $0.00000671 |
| fill price Binance | $0.00000679 (slippage +1.19%) |
| `res["cost"]` reale | **$46.10** |
| drift singolo trade | **+$0.44 over cassa attesa** |

Reason DB sul trade: `"LAST SHOT: Pct buy: check $0.00000671 dropped 2.5% below last buy $0.00000691 → fill $0.00000679 (slippage +1.19%) — spent remaining $46.10"`.

Decisione Board (Max): SWEEP/LAST SHOT è regola voluta, no cash morto, drift sub-dollar è prezzo accettabile su testnet. Ma mainnet rifiuta. → buffer.

**Lezione meta-cognitiva**: ho fatto 2 ipotesi sbagliate prima di trovare la vera. In entrambi i casi ho fermato il task PRIMA di scrivere codice basato su premessa sbagliata (CLAUDE.md §0 anti-drift). Senza quello, avrei shippato la "fix skim-aware-guard" inutile e non avrei toccato il vero problema. Memoria salvata (`reference_available_cash_already_skim_aware`) per evitare la stessa diagnosi errata da CC futuri.

---

## 3. Decisioni Board (nuove in S78 fase 2)

**D1 — Buffer uniforme 3% scelto su per-coin parametrizzato**
- RAZIONALE: in mainnet non sappiamo ancora con quali monete lavoreremo. Per-coin in `bot_config` ora rischia di buttare lavoro se il mix cambia.
- ALTERNATIVA scartata: per-coin in `bot_config.slippage_buffer_pct`
- FALLBACK: il valore è in `HardcodedRules`, semplice da ricalibrare/parametrizzare quando avremo dati mainnet reali

**D2 — "Scorciatoia banner" inizialmente respinta era in realtà la fix giusta**
- Max ha respinto la patch `=== 0 → <= 0` come "scorciatoia" all'inizio.
- Una volta capito che SWEEP è by design, **il caso `buysLeft < 0` è fisiologico**, non patologico. Il banner non lo gestiva = bug del banner, non sintomo di drift.
- Patch finale (S78 fase 2 commit afd97ce): `<= 0` con branch dedicato `< 0` che mostra "swept, $X over by slippage" — coerente con la card BONK "−1 buys left" già esistente.

**D3 — `gitignore` regola anchored**
- Bug pre-esistente da S78: `blog/` matchava ricorsivamente anche `web_astro/src/content/blog/`. I 2 blog post precedenti erano nel repo solo per timing (aggiunti prima del gitignore).
- Senza fix, ogni blog post futuro sarebbe stato silenziosamente droppato dal commit. Risolto inline (`/blog/` anchored a root) col commit `dcc4372`.

---

## 4. Numeri post-fix attesi

**Prossimo SWEEP BONK** (quando un sell libererà cassa $20-25):
- cash_before = $X (es. $45)
- cost spent = $X × 0.97 = $43.65 (invece di $45 unbuffered)
- Binance esegue con slippage +1.19% (testnet attuale)
- `res["cost"]` reale ≈ $43.65 × 1.012 = $44.17
- Cassa residua dopo trade: $45 − $44.17 = $0.83 (positivo)
- **Mai più cashLeft<0 in steady state**. Banner top `<= 0` quindi semanticamente equivalente a `=== 0`.

**Tradeoff**: lasciamo ~$0.83 "cash morto" per ogni SWEEP, invece di sforare di $0.44. Su testnet $500 paper, è cosmetico. Su mainnet €100, lo dobbiamo ricalibrare comunque post-launch.

---

## 5. Open question parcheggiate

- **Calibrazione SLIPPAGE_BUFFER_PCT post-mainnet**: brief separato quando saremo a 2-3 settimane dal go-live €100. Slippage mainnet tipicamente 10× più basso del testnet, quindi 3% sarà sovradimensionato. Decideremo allora se tunare a 0.5-1% o parametrizzare per-coin in `bot_config`.
- **Audit Area 2 mai eseguito**: cadenza 90gg o fine-volume Diary. CLAUDE.md §1 dice di flaggare. ⚠️ DOVUTO. Proponiamo quando finiamo il volume del Diary in corso o nelle prossime 1-2 sessioni di breathing.

---

## 6. Memorie salvate

- `project_sweep_last_shot_by_design.md` — Board regola "no cash morto"; drift sub-dollar atteso testnet; mainnet protetto da buffer (S78 fase 2 brief 78b)
- `reference_available_cash_already_skim_aware.md` — `_available_cash()` già sottrae reserve_ledger; NON proporre fix "skim-aware guard"

Entrambe linkate da MEMORY.md per visibilità ai CC futuri.

---

## 7. Prossimi passi

1. **Osservazione 24-48h**: il prossimo sell di BTC/SOL/BONK libererà cassa e potrebbe innescare SWEEP/LAST SHOT — sarà la prima verifica live del buffer.
2. **Brief 77c admin widgets**: rimane in attesa OK CEO (4 punti aperti su palette/F&G overlay/polling/posizione).
3. **Volume 3 Diary**: non toccato in S78 fase 2. Continua quando vorrai.
4. **Audit Area 2**: proporre quando finiamo il volume Diary.

---

## File chiave

- Brief: [config/brief_78b_sweep_slippage_buffer.md](../config/brief_78b_sweep_slippage_buffer.md)
- Commits: `dcc4372`, `afd97ce`, `64d6c89` su `origin/main`
- PROJECT_STATE.md aggiornato (§1, §3, §4, §10)
- Log restart Mac Mini: `/Users/max/orchestrator_20260516_214616.log` (Mac Mini)
- Orchestrator PID parent: 33579
