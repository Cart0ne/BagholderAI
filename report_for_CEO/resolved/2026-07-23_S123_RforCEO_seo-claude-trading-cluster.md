# Report per CEO — S123 — seo-claude-trading-cluster — 2026-07-23

**Brief sorgente:** `config/2026-07-23_S123_brief_seo-claude-trading-cluster.md`
**Commit:** `0a9d21b` (Task 1) + `d76a4bf` (Task 2) — pushati su `main`.
**Esito:** Task 1 SHIPPED (live). Task 2 DEPOSITATO `draft: true` — **il flip a `draft: false` attende l'ok esplicito di Max** (regola brief + weekend rule; oggi giovedì = ok per il weekend).

---

## Cosa è stato fatto

### Task 1 — micro-tuning FAQ post-money (`claude-code-crypto-trading-bot.md`) — LIVE
Toccato **solo il blocco `faq:`** (title/slug/subtitle/corpo invariati, come da brief):
- **FAQ costo**: da vaga ("recurring costs are small…") a **mensile-first**: *"about $100 a month — almost entirely a single Claude Max subscription… €368 spent to earn €0 so far, all public on /income."*
- **+2 FAQ** dalle query Bing scoperte: *"Which Claude plan do you need…"* e *"Can Claude Code connect a trading bot to Binance?"*
- FAQ passa da **7 → 9** (FAQPage JSON-LD verificato nel build).

### Task 2 — post nuovo sul costo (`cost-to-build-crypto-trading-bot-with-claude.md`) — DRAFT
- **6 FAQ** (checklist chiede 5-7; la bozza ne aveva 4 → +2: *"What does it cost per month…"*, *"Is a crypto trading bot built with AI profitable?"*).
- **Title/summary/corpo riframati sul costo MENSILE ~$100** (evergreen) invece del cumulativo.

---

## Due decisioni prese in sessione con Max (deviazioni migliorative dal brief)

**1. Framing evergreen sul mensile.** Il cumulativo (€368 in 4 mesi) **invecchia** — cresce ~$100/mese, tra 6 mesi sarebbe ~$900 e il post statico contraddirebbe /income (che il post linka). Deciso con Max: la cifra portante del post è il **costo mensile ~$100** (evergreen, è la risposta che rankiamo), il cumulativo passa in secondo piano.

**2. Cifre cumulative LIVE dal DB (idea di Max).** Invece di incidere "€368", le cifre cumulative (spent / €0 revenue) sono `<span data-live-spend>` / `<span data-live-revenue>` **lette live da `passive_income`** — stessa fonte e stessi totali della pagina /income. Quando Max aggiorna i costi da /admin, **il post segue da solo** e non può più contraddire /income. Riusa il pattern già in casa (`income.ts` fa lo stesso su `income-cost-prose`).
- **Infra riusabile**: flag frontmatter `liveFigures` + `<script is:inline>` condizionale in `[...slug].astro`. Carica **solo** sul post che lo dichiara (zero JS sugli altri 15 post, verificato nel dist). Il testo dentro lo span è il **fallback** per crawler senza JS / fetch fallito.
- **Nota SEO onesta**: un answer-engine che non esegue JS legge il fallback statico, non il live. Per questo il valore **SEO-target è il mensile evergreen** (hardcoded); il live è solo per l'onestà del lettore + coerenza con /income. Longevità e SEO non confliggono.

---

## Drift risolto (FAQ4 — flag `[⚠️ DRIFT — MAX DECIDE]` del brief)
Deciso con Max: **frase neutra**, niente rivelazione Kraken (reveal resta a Fase 3).
Rimossa da tutte le superfici toccate l'affermazione *"going live with real funds is a deliberate step we haven't taken"* (ora **falsa** dopo Kraken 2b), sostituita con *"Moving to real money is deliberate and slow, gated on observation."* — vera sia in ottica testnet sia post-2b, non rivela nulla.

## Numeri verificati (fonte: Supabase `passive_income`, live 2026-07-23)
- **Spent to date** = somma blocco `cost` non-status = **€367,54 → €368** (Claude Max 360 + Haiku 5,07 + Grok 1,07 + dominio 1,40 + infra 0).
- **Revenue to date** = **€0**. Invariati rispetto all'11/07 del brief. Query REST testata a mano: entrambi combaciano col fallback statico.

## Checklist SEO/GEO
- [x] `npm run build` verde (frontmatter + `faq` + `liveFigures` validi).
- [x] Anti-collisione: cross-link reciproci con money-post; tag condivisi (`claude-code`, `crypto-trading-bot`, `ai-trading-bot`, `build-in-public`) → "Keep reading" accoppia i due post.
- [x] Slug keyword front-loaded (`cost-to-build-crypto-trading-bot-with-claude`, invariato).
- [x] `summary` ≤ 220 char, scritta come risposta.
- [x] JSON-LD Article + FAQPage (6 domande) generato.
- [ ] `draft: false` — **in attesa ok Max**.

---

## Da segnalare a Max (fuori scope S123)

1. **Drift residuo su 4 post pubblicati** che dicono ancora *"not live with real money"* (ora falso post-2b): `why-most-ai-trading-bots-fail`, `an-ai-that-cant-trade`, `ai-crypto-trading-bot-real-testnet-results` (×2). Sono "linea pubblica testnet" → aggiornamento legato al **reveal di Fase 3** (decisione CEO). Non toccati. Le frasi neutre dei 2 post S123 non li contraddicono.
2. **Audit Area 2 (coerenza) event-based**: ultimo 2026-06-19 (34gg, sotto il backstop 60gg per cadenza). Ma il go-live **denaro reale Kraken (2b)** è un trigger event-based per A2 — valuta se pianificarlo ora che gira denaro vero.

## Cosa NON è stato fatto e perché
- Tag `binance`/`claude-max` (Task 1c opzionale): **saltati** — creerebbero tag-page orfane (nessun altro post li usa); i tag esistenti già accoppiano i post. Coerente con "se crea rumore, saltare".
- Home invariata (Decisione A). Nessuno slug live modificato.
