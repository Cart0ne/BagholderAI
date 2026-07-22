# Brief S121 — kraken-2b-bundle — 2026-07-21

**Tipo:** IMPLEMENTAZIONE — codice + test. **Gate DURO** per aprire la finestra Fase 2b.
**Da:** CEO · **Per:** CC (Intern) · **Esegue:** CC
**Contesto:** Fase 2a Kraken **CHIUSA** (round-trip reale $25 BTC completo, realized +$0,707). Il Board ha deciso la 2b = **$100 Sherpa-driven su BTC** (Opzione B, BUSINESS_STATE §4 2026-07-21). Prima di aprire la finestra 2b va shippato questo bundle. Fonti: `config/2026-07-21_MEMO_kraken-fase2b.md` §2/§3/§5, PROJECT_STATE §5, memoria `reference_grid_sell_trigger_fee_buffered`, BUSINESS_STATE §4.

---

## Regola d'ingaggio
- **Anti-assenso:** smonta questo brief PRIMA di codare — ≥1 obiezione tecnica reale, oppure dichiara "nessuna" in una riga motivata.
- Ogni claim ancorato a `file:riga`. Se qualcosa è "undeterminato", scrivilo, non inferire.
- **NIENTE restart d'iniziativa.** Tu shippi codice + test. Il restart è una finestra coordinata separata che lancia Max (CLAUDE.md §5). Questo bundle va live *a quel* restart.
- **Invariante Binance:** la flotta (4 grid testnet) è viva. Occhio agli effetti dell'intervento #1 (vedi auto-obiezione).

---

## I 3 interventi

### 1. Fix doppio-conteggio fee (floor + trigger) 🔴
Da S118 l'avg-cost **include già 1× fee di buy** (`buy_pipeline.py:304`, fee in quote). Ma:
- il **floor** min-profit (`sell_pipeline.py:305`) fa `min_price = avg × (1 + min_profit/100 + 2×fee)`
- il **trigger** di vendita (`grid_bot.py:876`) fa `avg × (1 + sell_pct/100 + fee) / (1 − fee)`

→ entrambi **ri-aggiungono** la fee di buy che l'avg contiene già. Break-even netto vero = `avg × (1+fee)` (≈ `avg/(1−fee)`), NON `avg × (1+2×fee)`. Effetto reale (memo §2): un "1% netto" su Kraken realizza ~1,8%; nella 2a il trigger è scattato a $66.314 invece di ~$65.798.

**Obiettivo:** floor e trigger devono partire dal break-even vero (**1× fee**), non doppiarla. Deriva TU la formula corretta e provala numericamente (hai già l'analisi in S119b + memo §2 — non fidarti di questo brief, verifica). Trigger e floor **condividono `fee_rate`**: devono restare coerenti. Verifica esplicitamente che il trigger non chieda una vendita che il floor blocca (= stallo silenzioso) per nessun `sell_pct`/`fee` plausibile.

### 2. Un helper unico del trigger + fix display/log 🟡
L'**esecuzione** usa il fee-buffered (`grid_bot.py:876`). Il **display** mostra il numero ingenuo `avg × (1 + sell_pct/100)`: `get_status` (`grid_bot.py:1179-1180`) e Range print (`:342`), etichetta "(+X% above avg)". → terminale/dashboard/Telegram **mentono** sul target (test 2a: dicevano $65.271, il bot vendeva a $66.317; Max 21-lug: prezzo ha sfiorato senza vendere).

**Obiettivo:** estrai **un solo helper** del trigger (branch grid vs TF, identico a `:876`), chiamato sia dall'esecuzione sia da **tutti** i display. Correggi l'etichetta ("net, fee-buffered"). Verifica anche daily_report + sito + Telegram. È **display-only** (nessun cambio del path di esecuzione), effetto al restart. Copri con test che **display == esecuzione**.

### 3. Processo grid Kraken daemonizzato pulito 🔴
Il babysitter 2a era: foreground in un Terminal, loop di respawn ad-hoc, **senza log**, **non riparte al reboot** (memo §5). Per la 2b:
- **orchestrator-managed** (mia preferenza) *oppure* `nohup caffeinate` daemonizzato pulito — **scegli tu e motiva** il trade-off (orchestrator = supervisione/restart uniforme ma va cablato un 5° runner venue=kraken; nohup = più rapido ma standalone, da ri-agganciare al reboot).
- **file di log** (`logs/grid_BTC_USD.log`).
- niente loop-terminale ad-hoc.
- **verifica che il loop/babysitter 2a sia morto** (nessun Terminal con quel respawn aperto) prima di predisporre il 2b.

---

## Auto-obiezione del CEO (dovuta)
**Obiezione reale al mio stesso brief:** il fix #1 **NON è isolato a Kraken**. Correggere il doppio-conteggio cambia trigger/floor **anche su Binance** (fee 0,1% → scarto ~0,1-0,2% sul prezzo di vendita): i 4 grid testnet live venderanno a un target leggermente diverso dopo il restart. È una *correzione* (erano sovra-protettivi anche lì), ma è un **diff osservabile sulla flotta viva**, e questo progetto tratta l'invariante-Binance come sacro.
Due strade — **decidi tu e argomenta**:
- **(A)** fix corretto ovunque, accettando/documentando il micro-diff Binance come genuinamente giusto (mio lean). Se scegli A: **dimostra** che il diff Binance è nell'ordine di grandezza atteso (~0,1-0,2%) e non rompe test/invarianti.
- **(B)** gate venue-aware: Binance resta byte-identico, solo Kraken usa la formula corretta. Se scegli B: giustifica il debito tecnico (due formule per la stessa cosa) e come lo si ripaga quando Binance esce di scena.

**Seconda, minore:** il refactor #2 tocca una funzione chiamata da molte superfici → è lì che si annidano le regressioni. L'helper dev'essere puro/equivalente e coperto da test display==esecuzione.

---

## Cosa NON fare (scope creep)
- ❌ Non toccare i **valori** dei parametri Kraken (margine/floor delle righe, `sell_pct`): li decide Sherpa (venue-independent, memo §3) + tabella con Max al setup 2b. Qui fixi solo la **matematica** del trigger/floor, non i numeri.
- ❌ Non aprire la finestra 2b: niente insert righe Kraken, niente flip `is_active`, niente restart.
- ❌ Non riaffrontare l'ancora-buy-dopo-sell (Blocco 2, **CHIUSO a zero codice** dal CEO dopo lettura del codice: il replay usa il last-buy legittimo `state_manager.py:202`, idle recalibrate/re-entry si ri-ancorano da soli `grid_bot.py:997-1129`, direzione sicura). Se leggendo il codice trovi una prova che **contraddice** questa chiusura, **fermati e segnala** — non fixare d'iniziativa.

---

## Consegna
Report `report_for_CEO/2026-07-21_S121_RforCEO_kraken-2b-bundle.md` con:
- cosa hai cambiato (`file:riga` + commit hash)
- la formula corretta del #1 con la **prova numerica**
- il **diff-Binance del #1 quantificato** + strada A/B scelta e perché
- esito test (+ eventuale review avversaria)
- la scelta di daemonizzazione motivata
- la tua **obiezione tecnica** al brief

Cita il brief sorgente (`2026-07-21_S121_brief_kraken-2b-bundle.md`) + commit hash. Lo SCOPE del report deve ereditare **identico**: `kraken-2b-bundle`.
