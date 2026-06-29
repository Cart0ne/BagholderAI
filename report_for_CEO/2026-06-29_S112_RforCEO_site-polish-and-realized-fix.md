# Report per il CEO — S112 (2026-06-29) — Site polish + Realized Fix A

**Sessione:** S112 (lunedì, operativa) · **Autore:** Claude Code (Intern)
**Esito:** SHIPPED · web-only, **nessun restart bot** · 7 commit (`227847c` → `c232554`)
**Origine:** chiusura del piano "prossima sessione — sito pubblico" lasciato in PROJECT_STATE §3 da S111, + un finding numerico emerso strada facendo.

---

## 0. TL;DR

Chiuse 3 delle 4 voci del piano sito S111 (footer icons, P&L per-fund in home, news linkabili). Durante la "verifica numeri" richiesta da Max è emerso un **bug public-facing**: il "Net Realized" su `/dashboard` era **gonfiato di ~$8** (mostrava +$30.6 invece di ~+$22.4). Diagnosticato, scritto report, **Fix A shippato** (CEO-approved). Fix B (bot) e Fix A2 (Today P&L) parcheggiati.

---

## 1. Cosa è stato fatto

### 1.1 — Finding + Fix A: `realized_pnl` avg-cost drift (il pezzo grosso)
Partito da una domanda di Max ("se ho net realized +30.64 e perdo −20.62, il P&L non dovrebbe essere ~+10 invece di +1.91?"). **Non era un fraintendimento suo**: due card della stessa dashboard si contraddicevano.

- **Verificato sul DB live**: il lato patrimoniale (cash, holdings, skim, fees, **Total P&L +1.91**) torna al centesimo; gli holdings del replay del sito = `bot_runtime_state.managed_holdings`. A mentire era solo `realized_pnl`.
- **Causa esatta**: il bot azzera `avg_buy_price` quando la griglia scende a polvere (`sell_pipeline.py:696`) **pur tenendo le monete-polvere** → ogni ciclo "dimentica" un pezzo di costo → realized fantasma (~+$0.5/ciclo su BTC ×~13 = ~+$9). È un comportamento **voluto** (sblocca il BONK dust-trap), con effetto collaterale contabile. Coerente con la dottrina nota "realized_pnl è fossile, Equity è canonico".
- **Fix A SHIPPED** (`0df228c`): il Net Realized è ora **calcolato dal replay avg-cost** (`revenue − avg×qty`), non letto dal campo DB. Applicato a **entrambe le copie**: `src/lib/pnl-canonical.ts` (home + /dashboard) **e** `public/lib/pnl-canonical.js` (grid/tf/admin via `window.PnL` — copia vanilla mantenuta a mano).
- **Verifica numerica**: Total P&L invariato, Net Realized +30.6 → **+22.4**, incoerenza identità da ~$8.12 → ~$0.07 (rumore float).
- **Parcheggiato** (`config/parked/PARKED_realized_pnl_avg_cost_fixB.md`): **Fix B** (rendere vero il campo DB lato bot — pre-mainnet, decisione CEO/Board) + **Fix A2** (Today P&L homepage).

### 1.2 — Piano sito S111 (3/4 voci)
- **#2 P&L per-fund in homepage** (`272a5fa`): sotto il Total P&L ora compare `Grid +$X / TF −$Y` (su due righe), gli stessi numeri canonici dell'admin (Total P&L per fondo — il numero **sano**, non il realized).
- **#1 Icone social nel footer** (`a3a9e86`): i 4 link testuali → bottoni tondi con icone SVG (Telegram, X, GitHub, Buy me a coffee).
- **#4 News linkabili** (`06a5a22`): i titoli NewsKeeper su `/dashboard` ora sono `<a href>` verso la fonte. **Drift trovato**: l'URL NON è una colonna `link` (come diceva PROJECT_STATE §3) ma sta in `raw_data->>'link'` (JSONB) — corretto in §3.
- **Ritocchi visivi** (`25b304f`, richiesti da Max): TF a capo nello split, "testnet" a capo sotto $600.

### 1.3 — NON fatto
- **#3 Strategia canale Telegram**: è la voce **strategica** del piano (più contenuti → nome al sicuro). Non è codice → territorio CEO/marketing, da impostare insieme.

---

## 2. Decisioni

**DECISIONE:** Net Realized pubblico derivato dall'avg-cost replay (Fix A), non dal campo `realized_pnl`.
**RAZIONALE:** è il "one source of truth" del progetto applicato al realized; allinea il numero pubblico alla verità del wallet a rischio zero sul trading.
**ALTERNATIVE:** (B) fix lato bot subito — scartata, tocca trading logic LIVE, va pre-mainnet con decisione Board; ("wontfix" su B) accettare che il campo DB resti una stima interna.
**FALLBACK:** modifica isolata a `replayAvgCost`; ripristino = 1 riga (`s.realized += dbPnl`), nessun dato a DB toccato.

---

## 3. Anti-assenso / note tecniche
- Il reset-su-polvere del bot **non** è un bug "da togliere e basta": è la cura del BONK dust-trap. Per questo Fix B richiede disaccoppiamento (avg operativo vs contabile), non una riga → giustamente parcheggiato.
- Il P&L per-fund in homepage usa il Total P&L per fondo (numero sano), **non** il realized → la voce #2 era pubblicabile a prescindere dal fix.
- Beccata la doppia copia di `pnl-canonical` (TS + JS vanilla): se avessi toccato solo il TS, grid/tf/admin sarebbero rimaste gonfiate. **Promemoria durevole** salvato in memoria.

---

## 4. Domande aperte per il CEO/Board
1. **Fix B** (`realized_pnl` a DB avg-cost puro): si schedula come brief pre-mainnet, o si accetta il campo come stima interna (sito già onesto via Fix A)? Collaterale: lo **skim** è calcolato sul realized → se gonfiato, skim accantonato leggermente sovra-stimato.
2. **#3 Strategia Telegram**: come vuoi impostarla (cadenza contenuti, cosa postare)?

---

## 5. Commit
`227847c` report finding (poi → parked) · `272a5fa` #2 per-fund · `a3a9e86` #1 footer · `06a5a22` #4 news · `25b304f` ritocchi wrap · `0df228c` **Fix A** · `c232554` annotazione. Tutti su `main`, pushati, Vercel deploya.
