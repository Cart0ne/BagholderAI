# Report for CEO — S109: pulizia task list + bug cleanup + infra pre-mainnet

**Data:** 2026-06-25
**Sessione:** S109
**Brief sorgente:** nessuno singolo — esecuzione dei task **CC-only** dal `config/MASTER_TASK_LIST_2026-06-18.md` (mentre il CEO valida Sherpa + breadth tier 1.2b, lavoro indipendente).
**Commit:** `96bbb38` (housekeeping) → `95f8f17` `9042e03` `2552110` `f818654` `e38fdf0` `0609183` `ce8a9b8`
**Test:** 228 → **250 verdi** (+22 nuovi). Deprecation warning datetime: **409 → 0**.

---

## In una riga

Chiusi **tutti i task CC-only eseguibili senza dati mainnet**: i 4 bug aperti + i 3 pre-mainnet CC (1.4 dust parziale, 1.5 slippage infra, 1.6 config-test). Niente di bloccato da te o dal mercato è stato toccato. **I fix che toccano `bot/` sono committati ma NON ancora live — serve un restart** (regola §5: lo lancia Max).

---

## Cosa è stato fatto

**Housekeeping (richiesta iniziale Max)** — `96bbb38`
- 4 PARKED del 22-giu git-trackati + indicizzati nel README parked.
- `memo_brainstorming_2026-05-11` → `briefresolved.md/`; report S108a 19-giu → `resolved/`.
- Apple Note Todo lasciata intatta (scelta Max).

**Bug aperti (MASTER §BUG) — tutti chiusi**
| Bug | Fix | Commit |
|---|---|---|
| Integration test config reader chain (gap S76, era 1.6) | 8 test end-to-end sulla catena `bot_config`→bot; copre i 6 punti dove si rompeva in silenzio (incl. rename `profit_target_pct`→`min_profit_pct`, sticky `pending_liquidation`) | `95f8f17` |
| PortfolioManager istanziato mai usato | Rimosso (istanziazione + classe orfana 100% no-op) | `9042e03` |
| `datetime.utcnow()` deprecato (409 warning) | Helper `utils/timeutils.utcnow()` **naive-preserving** (vedi decisione sotto) | `2552110` |
| `exchange_order_id` null sul sell | Fallback a `info.orderId` grezzo di Binance + warning; era `str(id or "")` → vuoto | `e38fdf0` |
| `validation_and_control_system.md` §2 stale | §2 aggiornata (coerenza superfici = presidiata da Audit A2 + test config-chain); termine morto "FIFO"→"avg-cost equity" | `f818654` |

**Pre-mainnet CC (MASTER FASE 1)**
- **1.6** config-chain test → vedi sopra.
- **1.5 slippage_buffer per-coin — INFRA** `0609183`: nuova colonna `bot_config.slippage_buffer_pct` (migration **applicata** al DB prod, additiva, NULL su tutte le coin → comportamento **identico a oggi**) + hot-reload + uso in buy_pipeline. Default = costante 0.03. Taratura per-coin → mainnet con dati reali.
- **1.4 dust — EVENTO + STUB** `ce8a9b8` (scope deciso da Max): il write-off ora è un **evento persistito** `DUST_WRITEOFF` (con `written_off_at`), non più solo una riga di log; + `bot/dust_converter.py` con `convert_dust_to_bnb()` **guarded mainnet-only** (no-op su testnet). Reconcile wallet↔DB → go-live.

---

## Decision log

**DECISIONE: `datetime.utcnow()` → helper *naive-preserving*, non `datetime.now(timezone.utc)`.**
RAZIONALE: il codebase è deliberatamente naive-UTC (i timer del bot sono senza fuso; `state_manager` strippa il fuso dalle date DB apposta). Passare ad "aware" avrebbe rotto i confronti naive-vs-aware con `TypeError` — un bug che le date dei trade nascondono bene.
ALTERNATIVE: migrazione completa ad aware (refactor ampio, tocca tutto il replay DB).
FALLBACK: l'helper è l'unico punto da cambiare se un giorno si vuole davvero migrare ad aware.

**DECISIONE: dust scope = "evento + stub", reconcile rimandato a mainnet.**
RAZIONALE: il brief DUST dice testualmente "non creare la tabella in paper, aspetta il live"; il convert-to-BNB non è testabile su testnet. Costruire il reconcile ora = over-engineering che il brief stesso avverte. Max ha confermato lo scope ristretto.
FALLBACK: il modulo `dust_converter` e il punto di estensione sono già lì; a go-live si aggiunge solo la chiamata API + reconcile.

**DECISIONE: `slippage_buffer_pct` memorizzato come FRAZIONE (0.03), non percent-points.**
RAZIONALE: coerente con la costante esistente e con la matematica `cost = cash × (1 − x)`; evitato di toccare il calcolo del trading. Incoerente con le altre `_pct` (che sono percent-points) — annotato nel commento di colonna.
FALLBACK: reversibile (colonna droppabile, default codice resta la costante).

---

## Cosa NON è stato fatto (e perché)

- **T8 — Monitor "griglia silenziosa"**: parcheggiato. La soglia (distinguere "rotta" da "mercato laterale") è una scelta che Max vuole valutare. Va in /admin (non Telegram).
- **Dust reconcile wallet↔DB (punto 3)**: → go-live (non testabile su testnet).
- **Slippage taratura per-coin**: → mainnet (servono dati di slippage reali, ≠ testnet).

---

## ⚠️ Follow-up per Max

1. **Restart pending**: i fix `bot/` (PortfolioManager, datetime, exchange_order_id, dust evento, slippage infra) diventano LIVE solo al prossimo restart dell'orchestrator. Comportamento atteso identico (sono cleanup/infra), ma il dato pulito arriva solo dopo. **Dimmi quando**.
2. **Drift path segnalato** (regola §0): `validation_and_control_system.md` vive in `briefresolved.md/` ma 3 riferimenti + una memoria lo cercano in `config/` (link rotto). Propongo `git mv` → `config/` (ripara i link). Tuo OK?

---

## Roadmap impact

**None.** Lavoro interno (bug cleanup + infra pre-mainnet + test). Verificato `git diff --name-only`: nessun `web_astro/src/data/roadmap.ts` toccato; i temi slippage/dust in roadmap.ts sono commenti storici di task già DONE, non task aperti.

## Audit — cadenze al 2026-06-25
- Area 1: ultimo 2026-06-01 (24gg) ✅ entro 30gg. Area 2: 2026-06-19 (6gg) ✅. Area 3: 2026-05-31 (25gg) ✅ ma prossimo ~30-giu.
