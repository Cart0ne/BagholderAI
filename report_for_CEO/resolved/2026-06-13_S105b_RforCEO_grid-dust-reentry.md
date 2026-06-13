# Report S105b — RforCEO — grid-dust-reentry — 2026-06-13

**Brief sorgente:** `config/2026-06-13_S105b_brief_grid-dust-reentry_v2.md` (+ ADDENDUM)
**Commit:** `87eeda9` (5 file, +336 −10). **Tipo:** logica bot.
**Esito:** SHIPPED, suite **228 passed** (219 baseline + 9 nuovi). **Deploy/restart:** in attesa di Max sul Mac Mini (CC non riavvia).
**Off-limits rispettati:** nessun parametro Sherpa/Board toccato, nessuna migration, nessun restart CC, TF non toccato.

---

## Esito GATE A2 (vincolante) → **VERDE**

Filtri Binance reali (testnet+mainnet, verificati live): SOL `minNotional=$5`, BTC `$5`, BONK `$1`. Tutti ≥ $0,50. Quindi il predicato `min_sellable` **domina** il vecchio `$0,50` su tutte e tre le monete (azzera ciò che il `$0,50` azzerava **e** la fascia [$0,50, $5)). Ramo "SÌ" di A2: **il `$0,50` si elimina** dalla logica primaria. Conservato **solo** come fallback di `is_dust()` quando i filtri non sono caricati (preserva il fix BONK restart S73 nel caso degradato). Nessuna regressione BONK.

## Risposte alle domande del brief

- **DOMANDA #1 (dove vive il minimo vendibile) → (a).** I filtri sono già letti via ccxt in [utils/exchange_filters.py](utils/exchange_filters.py) (`fetch_filters`→`load_markets`→`limits`), salvati in `bot._exchange_filters` al boot ([grid_runner/__init__.py:314](bot/grid_runner/__init__.py#L314)), **prima** del replay dello stato ([:325](bot/grid_runner/__init__.py#L325)). Di più: il predicato `min_sellable = max(step, min_qty, min_notional/price)` **esisteva già inline** in [sell_pipeline.py:343-350](bot/grid/sell_pipeline.py#L343). L'ho **estratto**, non reintrodotto.
- **Rianimazione (§4 / A3) → (i).** SOL rinasce **al restart di deploy**, senza intervento manuale né SQL: la sua polvere ($0,0065) è < $0,50 → `state_manager` la azzera al replay → `managed_holdings`=0 → re-entry compra al primo tick. Il restart lo fa **Max** sul Mac Mini.

## Cosa è cambiato (logica, non valori)

**1 predicato unico** in [utils/exchange_filters.py](utils/exchange_filters.py): `is_dust(holdings, price, filters)` + `min_sellable_amount(price, filters)`. Dust = un SELL di quella quantità sarebbe rifiutato da Binance (sotto LOT_SIZE/NOTIONAL). Usato in **tutti** i gate posizione-vs-polvere (requisito §3 CRITICO):

| Punto | File | Prima → Dopo |
|---|---|---|
| Re-entry forzato | [grid_bot.py:1024](bot/grid/grid_bot.py#L1024) | `managed_holdings <= 0` → `_position_is_dust()` |
| Sell-gate | [grid_bot.py:804](bot/grid/grid_bot.py#L804) | `managed_holdings > 0` → `not _position_is_dust()` |
| First-buy gate | [grid_bot.py:930](bot/grid/grid_bot.py#L930) | idem |
| Dead-zone recalibrate | [grid_bot.py:732](bot/grid/grid_bot.py#L732) | idem |
| Idle mode/suppress | [grid_bot.py:974/992/995](bot/grid/grid_bot.py#L974) | idem |
| **No-buy-above-avg guard** | [buy_pipeline.py:61](bot/grid/buy_pipeline.py#L61) | `managed_holdings > 0` → `not is_dust(...)` |
| Boot replay write-off | [state_manager.py:156](bot/grid/state_manager.py#L156) | `$0,50` hardcoded → `is_dust(...)` |

Il metodo `GridBot._position_is_dust(price)` ([grid_bot.py:~231](bot/grid/grid_bot.py#L231)) centralizza la chiamata per il bot.

**Punto chiave scoperto in fase di codice:** la guardia no-buy-above-avg ([buy_pipeline.py:61](bot/grid/buy_pipeline.py#L61)) avrebbe **bloccato lo stesso buy di re-entry** (dust>0 + prezzo>avg) — quindi senza unificare *anche* quel punto, SOL sarebbe rimasta congelata pur "scattando" il re-entry. È la prova concreta del perché §3 esige il predicato ovunque.

## BTC/BONK invariati (verificato)

BTC ($50) e BONK ($49) hanno posizioni ≫ min_sellable ($5/$1) → `is_dust=False` → comportamento identico a prima. Coperto da test `test_real_position_*` + `test_replay_keeps_healthy_residual` + `test_is_dust_gate_a2_bonk`.

## Test (+9, suite 228 verde)

`tests/test_dust_reentry_s105b.py`: unit del predicato, GATE A2/BONK, fallback senza filtri, **re-entry-on-dust** (riproduce il freeze SOL e ne verifica lo sblocco), **real-position-unchanged** (mirror di test_j), **guard bypass** dust vs real, **replay** della fascia [$0,50,$5).

## Decisions

DECISIONE: `$0,50` eliminato dalla logica primaria, sostituito ovunque dal predicato `min_sellable`; conservato solo come fallback no-filtri.
RAZIONALE: GATE A2 verde — il predicato domina $0,50 su tutte le monete; il fallback evita di riaprire il bug BONK S73 nel caso (raro) in cui `fetch_filters` fallisca al boot.
ALTERNATIVE: (A) `max($0,50, min_sellable)` come floor permanente (scartata: ridondante, il predicato già domina); (B) eliminare $0,50 del tutto anche dal fallback (scartata: caso degradato senza filtri resterebbe scoperto).
FALLBACK SE SBAGLIATA: revert `87eeda9` (nessuna migration, nessuno stato persistente da ripulire). TF non toccato → zero rischio sui bracci esistenti.

## In sospeso (A6 — attendono Max)
- **Restart deploy** sul Mac Mini → rianima SOL automaticamente.
- Push fix NewsKeeper **S105a** (`0c4d810`/`897449c`) — commit locale.
- Commit memo Board "sol-grid-frozen-dust" + questo report.
