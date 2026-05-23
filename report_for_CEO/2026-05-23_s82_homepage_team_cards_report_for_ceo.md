# S82 — Homepage redesign: Blog section + Diary swap + Watchtower & Sherpa cards LIVE-WIRED

**Data:** 2026-05-23
**Esito:** SHIPPED LOCAL ONLY (no push, in attesa del brief newskeeper Board)
**Branch:** `main` (1 commit avanti rispetto a `origin/main` post-S82)
**Build:** verde, 14 pagine
**Restart bot:** non necessario (zero modifiche codice Python)

---

## 1. Cosa è stato fatto

Sessione interamente sito Astro, in iterazione fluida con Max. Tre blocchi:

### A. Layout home — Blog section + Diary swap

- **Nuova sezione Blog** subito sotto hero, con i 3 post più recenti pubblicati (filtrati `draft=false`, ordinati DESC by date). Stesso pattern UX del Diary: tutto il blocco linka a `/blog`, "Read the blog →" in fondo. Solo titoli + data ("May 19, 2026"), niente subtitle/summary.
- **Sezione Diary spostata** sotto le AI Bots (era subito dopo hero). Markup intatto, niente regressioni.
- **`hello-world.md` eliminato** — placeholder `draft=true` visibile solo in dev. Restano 3 post reali pubblicati: An AI That Can't Trade, The Day Our Bot Ran Out of Money, When Your AI CEO Lies About the Numbers.

### B. Card Sentinel/Sherpa rifatte → `WatchtowerCard` + `SherpaLockedCard`

Grid e TF **intoccati** (continuano a usare `BotCardOriginal`). Per Sentinel/Sherpa, 2 nuove card che riusano le stesse classi CSS shell (`bot-card`, `bot-frame`, `bot-stat-row`) → allineamento pixel automatico con le altre 2 card, niente nuovo CSS sulla shell.

**THE WATCHTOWER** (duo Sentinel × NewsKeeper, LOCKED):
- Pill "TEST" allineata con LIVE/ACTIVE
- Sub: "Sentinel × NewsKeeper · early warning"
- Frame contiene 2 mascot affiancati con glow blu+viola, label "SENTINEL"/"NEWSKEEPER" sotto, watermark "?" dim sullo sfondo
- Footer quote: "▸ One reads charts. One reads news. Together they see it coming."
- **Primo cameo pubblico di NewsKeeper** sul sito (dim/locked, palette `#a855f7` ridotta a `#2a153d/#4c266f/#82679a` tramite gradient bakato)

**SHERPA** (Parameter Tuner, LOCKED):
- Pill "TEST", sub "Parameter Tuner"
- Frame con mascot Sherpa (flag dorato + mappa aperta), glow rosso, watermark "?"
- Footer quote: "▸ Reads the regime. Adjusts the grid. One parameter at a time."

### C. 3 mascot Astro estratti da SVG flat Claude Design

- `SentinelMascot.astro` — antenna + cyclops eye, palette dim
- `NewsKeeperMascot.astro` — giornale "THE TAPE" + reader glasses, palette dim viola
- `SherpaMascotV2.astro` — flag dorato + mappa aperta, palette dim rossa (suffix `V2` per non collidere con `BotMascot.astro` esistente)

Statici, niente React. SVG path estratti verbatim dal file `team-cards-locked-2.svg` di Claude Design — niente conversione JSX→Astro, niente `shadeC()` runtime: la palette dim è già **bakata** nei gradient. I 2 JSX originali (`bots-sentinel-sherpa.jsx`, `bots-newskeeper.jsx`) restano riferimento per i variant futuri (watch/lock/alert per Sentinel; lead/direct/plan/summit per Sherpa; read/flash/brief/stack per NewsKeeper).

### D. Stat-row compattate a 1 riga — 3 LIVE-WIRED via Supabase REST

| Card | Stat | Valore oggi | Tipo |
|---|---|---|---|
| Watchtower | SOURCES | `4` | statico (4 pip: 3 sentinel-blue + 1 newskeeper-violet, telegrafa quale source porta NewsKeeper) |
| Watchtower | SCAN FREQ | `60s · 4h` | statico (bar dim, da raffinare) |
| Watchtower | **REGIME** | **`FEAR`** | **LIVE** — 5 pip discreti (extreme_fear→extreme_greed), illuminato il corrente. Fetch `sentinel_scores?score_type=slow&order=desc&limit=1`, regime estratto da `raw_signals->>regime` JSONB |
| Watchtower | ACCURACY | `TBD` | placeholder (no meccanismo accuracy oggi) |
| Watchtower | ALERTS | `—` | placeholder (arriva con NewsKeeper) |
| Sherpa | **BOTS** | **`3`** | **LIVE** — pip rossi 26px gap 6px, count via `bot_config?managed_by=in.(grid,tf)&is_active=eq.true`. Auto-adatta a futuri scenari grid+tf / tf-only |
| Sherpa | PARAMS | `3` | statico (buy_pct · sell_pct · idle_reentry_hours) |
| Sherpa | MODE | `DRY_RUN` | statico (2 pip toggle dry_run/live, sx attivo) |
| Sherpa | ADJUST | `—/7d` | placeholder — metrica LAG distinct-changes saturerebbe oggi su dati pre-Sprint-2. Rivisitare ~5-7gg post-S81 quando slow-gate + amplitude cap stabilizzano |
| Sherpa | **STOP BUY** | **`OFF`** | **LIVE** — 1 pip rosso opacity 0.25, OR di `proposed_stop_buy_active` su ultime 3 righe `sherpa_proposals` (1 per coin). Oggi OFF (regime=fear, non extreme_fear) |

Live wiring in 2 nuovi script: [watchtower-live.ts](web_astro/src/scripts/watchtower-live.ts) + [sherpa-live.ts](web_astro/src/scripts/sherpa-live.ts). Fallback graceful: se la fetch fallisce, il valore server-rendered resta in place.

---

## 2. Decisioni del Board durante la sessione

1. **Grid e TF non si toccano** (decisione 1 — vincolo iniziale). Forza l'uso della stessa shell CSS per le 2 nuove card invece di reinventare layout.
2. **Astro puro, niente React Island** (decisione 2 — quando Max ha visto il primo mockup). Allineamento pixel con Grid/TF garantito, niente bundle React per 2 card statiche.
3. **Pill `SOON` → `TEST` allineata con LIVE/ACTIVE** (correzione visiva).
4. **Footer quote stile TF** (con `▸` colored), non italic-only.
5. **Numero pip BOTS dinamico**, "che si adatterà in base alle monete gestite" — query con filtro `managed_by IN ('grid','tf')` per coprire i 3 scenari futuri possibili.
6. **STOP BUY al posto di COOLDOWN** — Max ha respinto `COOLDOWN 24h` perché statico, e `MAX Δ 30%` per stessa ragione. STOP BUY è LIVE per design (boolean cambia con regime).
7. **Push deferito al brief newskeeper Board** — il sito non rivela NewsKeeper pubblicamente finché il codice Python e la roadmap non sono compatibili. Coerenza visiva ↔ runtime.

---

## 3. Decisioni di CC (DECISIONI)

**DECISIONE 1:** SVG flat di Claude Design come fonte mascot, non i 2 JSX.
**RAZIONALE:** SVG ha già la palette dim bakata nei gradient (`shadeC(color, -0.55)` pre-applicato), niente conversione `React.useId()` → Astro, niente import shared. Porting < 1h vs stimato 2-3h.
**ALTERNATIVE CONSIDERATE:** (a) portare i JSX in `.astro` con tutti gli helper; (b) React Island con `client:visible`.
**FALLBACK SE SBAGLIATA:** i 2 JSX sono conservati nello scope, riprendibili quando servirà far esplodere i variant (alert/lock/summit).

**DECISIONE 2:** Suffisso `V2` per `SherpaMascotV2.astro`.
**RAZIONALE:** evitare collisione con `BotMascot.astro` parametrico usato da Grid/TF, mantenere quello come fonte di verità per i bot già live.
**ALTERNATIVE CONSIDERATE:** rinominare l'originale a `BotMascotLegacy.astro` (rischio di rottura su Grid/TF).
**FALLBACK SE SBAGLIATA:** rename `SherpaMascotV2` → qualcosa di più descrittivo se mai dovessimo avere altre versioni Sherpa.

**DECISIONE 3:** `ADJUST` lasciato placeholder, non LIVE-WIRED oggi.
**RAZIONALE:** la metrica corretta (distinct value-changes via LAG()) richiede query complessa lato browser; i dati 7d attuali includono 5gg pre-Sprint-2 inquinati. Rinvio di ~5-7gg al primo dataset post-S81 pulito.
**ALTERNATIVE CONSIDERATE:** (a) `4802/7d` live ma rumoroso/gonfio; (b) RPC Postgres dedicata.
**FALLBACK SE SBAGLIATA:** wiring fattibile con un'unica query LAG quando i numeri sono onesti.

**DECISIONE 4:** `<style is:global>` su `SherpaLockedCard.astro`.
**RAZIONALE:** lo script `sherpa-live.ts` ricostruisce dinamicamente i pip BOTS. Elementi creati con `createElement` non ereditano `data-astro-cid` → CSS scoped li ignora → pip invisibili. `is:global` risolve, classi prefissate (`sherpa-bot-pip`, `sherpa-pip-row`) evitano collisioni.
**ALTERNATIVE CONSIDERATE:** spostare le classi in `global.css` (più dispersione del codice del componente).
**FALLBACK SE SBAGLIATA:** spostare le classi in `global.css` quando il componente cresce.

---

## 4. File modificati / creati

```
modified: web_astro/src/pages/index.astro
deleted:  web_astro/src/content/blog/hello-world.md
new:      web_astro/src/components/WatchtowerCard.astro
new:      web_astro/src/components/SherpaLockedCard.astro
new:      web_astro/src/components/SentinelMascot.astro
new:      web_astro/src/components/NewsKeeperMascot.astro
new:      web_astro/src/components/SherpaMascotV2.astro
new:      web_astro/src/scripts/watchtower-live.ts
new:      web_astro/src/scripts/sherpa-live.ts
```

**Fuori scope del commit S82** (lasciati untracked, in attesa Max):
- `config/brief_newskeeper_architecture.md` (brief Board)
- `web_astro/public/newskeeper.svg` (asset)

---

## 5. Audit reminder

⚠️ **Audit Area 2 (coerenza progetto) dovuto**: ultimo audit Area 2 = **mai eseguito**. Flaggato in S78f2/S79/S80/S80a/S81/S82 senza follow-up. Cadenza 90gg superata da sempre. Proposta CC ricorrente: eseguirlo nei 7-10gg di osservazione Sherpa Sprint 2 (scadenza naturale ~29 maggio - 1 giugno) con fresh CC + brief `audits/audit_request_*.md`.

Area 1 (tecnica): ultimo 2026-05-07 (16gg) — entro cadenza 30gg ✅
Area 3 (strategy & marketing): ultimo 2026-05-15 (8gg) — entro 90gg ✅

---

## 6. Cosa NON è stato fatto e perché

- **Polish visuale Watchtower/Sherpa**: posizionamento mascot duo, intensità glow, lunghezza footer quote, allineamento min-width value text. Iterabile alla prossima sessione sito.
- **Push S82**: deferito al brief newskeeper Board. Il sito **non** rivela NewsKeeper pubblicamente finché Python+roadmap non sono compatibili.
- **Aggiunta token CSS `--color-bot-news`**: rimandato — la palette viola è inline nei mascot e nelle card, niente uso di Tailwind utility per ora. Quando NewsKeeper avrà la sua card LIVE (post brief), si formalizza il token.
- **`MAX Δ 30%` come stat statica Sherpa**: scartato (Max — "è un valore che non cambia, sarebbe info statica"). Stesso vincolo applicato a `COOLDOWN 24h` originario.
- **Wire-up SCAN FREQ con segmenti per Sentinel/NewsKeeper** (split 60s blu + 4h viola): Max "ci devo pensare". Iterabile.

---

## 7. Prossimi step suggeriti

| Priorità | Step |
|---|---|
| 🔴 | Lettura brief newskeeper Board (`config/brief_newskeeper_architecture.md`, untracked) — sblocca il push S82 |
| 🟡 | Polish visuale Watchtower/Sherpa con Max al browser |
| 🟡 | Eseguire **audit Area 2** durante 7-10gg DRY_RUN Sherpa Sprint 2 |
| 🟢 | Tornare su `ADJUST` ~28-30 maggio quando dataset post-Sprint-2 è pulito |
| 🟢 | Seconda Brain Analysis (~29 maggio - 1 giugno) — verifica per-coin proposals, slow gate, distribution cap |
