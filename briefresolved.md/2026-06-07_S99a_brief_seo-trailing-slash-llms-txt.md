Brief S99a — seo-trailing-slash-llms-txt — 2026-06-07

## Contesto

Primo audit Semrush su bagholderai.lol (7 giugno 2026). Risultato: 97% site health,
0 errori, 13 warning, 54 notice. L'audit gonfia i warning perché conta come pagine
distinte `/path` e `/path/` (trailing slash). Inoltre segnala `llms.txt not found`.

Riferimento: PROJECT_STATE.md aggiornato al 2026-06-06 (S98).

## Task 1 — Trailing slash: canonical senza slash

**Problema:** Semrush (e potenzialmente Google) vede `/diary` e `/diary/` come due URL
distinti con lo stesso contenuto. Questo raddoppia artificialmente i warning e crea
rischio di contenuto duplicato in SERP.

**Cosa fare:**

1. In `web_astro/astro.config.mjs`, impostare `trailingSlash: 'never'`.
   Astro 5+ con questa opzione genera URL senza trailing slash e fa redirect
   301 da `/path/` a `/path`.

2. Verificare che `vercel.json` abbia già `"cleanUrls": true` (CONFERMATO — non toccare).

3. Verificare il build: `npm run build` deve essere verde. Nessuna pagina deve
   rompersi. Controllare in particolare:
   - Homepage, `/diary`, `/dashboard`, `/library`, `/blog`, `/roadmap`, `/blueprint`
   - I link interni nel Layout e nella nav non devono avere trailing slash
   - Il canonical URL generato in `Layout.astro` (se usa `Astro.url.pathname`)
     deve risultare senza trailing slash

4. Verificare che la sitemap generata (`sitemap-0.xml`) non contenga URL con
   trailing slash.

5. Se qualche link interno nel codebase ha trailing slash esplicito (es. `href="/diary/"`),
   rimuovere lo slash finale. Fare una ricerca grep su `web_astro/src/` per `href="/`
   e controllare.

**Vincoli:**
- NON toccare `vercel.json` redirects esistenti
- NON toccare robots.txt
- NON cambiare slug dei blog post

## Task 2 — Creare llms.txt

**Problema:** Semrush segnala `llms.txt not found`. Il file è uno standard emergente
(proposto da Jeremy Howard, Answer.AI, 2024) che fornisce agli LLM un riassunto
strutturato del sito in Markdown. Allineato con la nostra strategia GEO.

**Cosa fare:**

1. Creare `web_astro/public/llms.txt` con formato Markdown. Contenuto:

```markdown
# BagHolderAI

> BagHolderAI is an experimental crypto trading startup where an AI (Claude)
> acts as CEO, a human co-founder provides oversight, and Claude Code serves
> as technical intern. Every decision, bug, and loss is documented publicly
> in a live development diary.

## Key Pages

- [Homepage](https://bagholderai.lol): Project overview, bot status, and latest updates
- [Development Diary](https://bagholderai.lol/diary): 95+ sessions of AI CEO decisions documented live
- [Live Dashboard](https://bagholderai.lol/dashboard): Real-time trading bot performance and P&L
- [Blog](https://bagholderai.lol/blog): Technical posts, lessons learned, and behind-the-scenes
- [Library](https://bagholderai.lol/library): The AI CEO Diary book series (3 volumes)
- [Roadmap](https://bagholderai.lol/roadmap): What we're building, what's done, what's next
- [Blueprint](https://bagholderai.lol/blueprint): Full technical architecture and trading rules
- [About](https://bagholderai.lol/about): Team structure and project philosophy

## What Makes This Project Different

- Radical transparency: every trade, every bug, every loss is public
- AI CEO writes a development diary after each work session
- Three-Claude architecture: CEO (strategy), Claude Code (implementation), Haiku (automation)
- Five trading brains: Grid Bots, Trend Follower, Sentinel, Sherpa, NewsKeeper
- Currently on Binance testnet; mainnet go-live requires multi-regime validation

## Topics Covered

- AI-assisted software development with Claude Code
- Crypto trading bot architecture and grid trading strategies
- Human-AI collaboration and AI governance
- Transparent startup building and radical documentation
- Vibe coding and non-coder technical management
```

2. Opzionalmente, creare anche `web_astro/public/llms-full.txt` con un contenuto
   più esteso (pagine principali in markdown). NON obbligatorio per questo brief —
   parcheggiato per dopo se utile.

**Vincoli:**
- Il file va in `web_astro/public/` (servito come statico da Vercel)
- NON aggiungere riferimenti a llms.txt in robots.txt (non è lo standard)
- NON toccare il sitemap

## Output atteso

A fine task devono esistere:
- `astro.config.mjs` con `trailingSlash: 'never'`
- `web_astro/public/llms.txt` con il contenuto sopra (CC può aggiustare
  le descrizioni se trova formulazioni migliori, ma la struttura resta)
- Build verde (`npm run build`)
- Nessuna regressione visiva sulle pagine esistenti
- Commit + push su main

## Decisioni delegate a CC

- Se durante il grep trova link interni con trailing slash, fixarli tutti
- Se la sitemap richiede una config aggiuntiva per rispettare trailingSlash, applicarla
- Micro-aggiustamenti al testo di llms.txt (formulazioni, ordine)

## Decisioni che CC DEVE chiedere a Max

- Se trailingSlash 'never' causa un breaking change imprevisto (pagine 404, redirect loop)
- Se emergono altri file da toccare non previsti nel brief

## Roadmap impact

Nessuno. Questo è un fix infrastrutturale SEO, non una feature. La roadmap non cambia.

## Auto-obiezione CEO

L'impatto reale di llms.txt è incerto. Semrush stessa ha documentato che i crawler AI
(GPTbot, ClaudeBot, PerplexityBot) non visitano attivamente il file — almeno non nel 2025.
Potrebbe essere teatro GEO senza valore pratico. Lo facciamo lo stesso perché: (a) costo
quasi zero, (b) allineato con il nostro posizionamento "AI-native project", (c) se/quando
i crawler lo adotteranno, saremo già lì. Ma non ci illudiamo che cambi qualcosa domani.
