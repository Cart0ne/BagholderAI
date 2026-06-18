# BUSINESS_STATE.md — Aggiornamento S107 (2026-06-18)

**Istruzioni per CC:** applicare le modifiche sotto al file `BUSINESS_STATE.md`. Ogni sezione indica DOVE intervenire e COSA cambiare.

---

## §2 — SEO: AGGIUNGERE sotto "SEO — Semrush (S99 NEW)"

### SEO — Keyword Repositioning (S107)
- **Bing Webmaster Tools audit S107** (16 giugno 2026): 13 impression in 3 mesi, 0 click, 7 keyword — TUTTE varianti "crypto trading bot with Claude." Zero keyword su AI autonomy, AI CEO, one-person company, non-coder.
- **Gap identificato:** sito classificato dai motori come "crypto trading bot project." L'angolo differenziante (AI-as-CEO, autonomous AI, non-coder) viveva nei meta tag di alcune pagine ma non aveva massa critica di contenuto.
- **4 cluster keyword mappati:** (1) AI-as-CEO / AI running a business — differenziazione massima, (2) one-person company / solo founder + AI agents — topic caldo 2026, (3) non-coder / vibe coding — volume alto, (4) Claude + crypto trading bot — già rankiamo qui.
- **Brief S107 SEO implementato** (commit `c1ee2df`): meta tag + micro-contenuto aggiornati su 7 pagine (Homepage, Blog, Diary, Dashboard, Blueprint, Roadmap, Library). Principio: nessuna keyword nel meta che il contenuto della pagina non supporti — per ogni meta tag modificato, aggiunta una riga di contenuto visibile.
- **Invariate:** How We Work (già allineata cluster 1), Income/The Experiment (appena pubblicata, meta già forte).

---

## §2 — Frontend/Sito: AGGIORNARE la sezione sito

### Site v2 (S106a batch 1 + S107)

**Homepage v2 (S107, locale → push 18 giugno):**
- Scena ufficio (`LabRoom.jsx`) come hero — sostituisce il vecchio text hero
- Bot cliccabili nella scena: click → sezione dashboard corrispondente (anchor ID)
- Live snapshot (4 label) + Today (2 label) sotto la scena
- Manifesto block con H2: "This is not a crypto project."
- Bot card reinserite tra snapshot e manifesto (testo leggibile dai crawler)
- Rimossi: pill "Volume 3 is live", sezione "The team"
- /office eliminata come pagina standalone (redirect 301 → /)

**Dashboard v2 (S107):**
- Plate per-bot vestiti con colori e scenografie (Grid=mixer, TF=radar, NK=?, Sentinel=pulse, Sherpa=gear)
- Bordi tratteggiati + tint soft per-bot
- Colori bot ripristinati ai vivaci della scena (annullato pastel override S103b)
- Unrealized/fees/skim da 3 colonne → 3 righe; micro-prezzi in notazione scientifica

**Board scena ufficio (S107):**
- Include coin TF (ETH visibile)
- Label "unrealized" sulle coin + "TOTAL P&L"
- Net worth sotto il grafico
- Cornice flash adattiva

**Batch 1 S106a (15 giugno, online):**
- Grafici onesti `tension:0` (dashboard + /income)
- /income pubblicata (noindex off, sitemap, dropdown "The experiment")
- Nav dropdown "Under the hood ▾" (7→5 voci)
- Dashboard riordinata (Brains prima di Traders, CEO log in fondo)
- Anchor ID dashboard (#grid, #trendfollower, #sentinel, #sherpa, #newskeeper)
- Fix H1 diary "Development diary"

---

## §3 — Diary Status: SOSTITUIRE il blocco

**Sessione corrente: S107 COMPLETE** (SEO keyword analysis + meta+content proposals + site v2 redesign).
**Interludio scritto:** "Thirteen Impressions" (copre S106-S107, arco: visual identity per umani + SEO identity per macchine).

- Volume corrente pubblico: V3 "From Brain to Eyes" (live). V4 in lavorazione (arc: NewsKeeper → go-live → results).
- Ultima entry diary: **S107** "The One Where Thirteen Strangers Said Who We Are"
- Blog post pubblicati: **9** (ultimo: "How a Non-Coder Manages 5 AI Brains", S104)
- **Draft blog in coda: 3** — `vibe-coding-a-real-business.md` (pronto, serve intro umana + ritocco SEO), `why-most-ai-trading-bots-fail.md` (pronto, serve intro umana + reframe closing), `ai-crypto-trading-bot-real-testnet-results.md` (parcheggiato, pieno di TODO, post-mainnet)

---

## §4 — Decisioni: AGGIUNGERE IN CIMA alla tabella

| Data | Decisione | Perché |
|---|---|---|
| 2026-06-18 (S107) | **SEO meta + content su 7 pagine** — shift da "crypto bot" a "AI runs a business, crypto is the context" | 13 impression Bing tutte crypto. Principio: niente keyword senza contenuto che la supporti → per ogni meta tag, aggiunta riga contenuto visibile |
| 2026-06-18 (S107) | **Manifesto block con H2** "This is not a crypto project" | Senza heading tag, il testo era invisibile ai crawler. H2 dà peso semantico |
| 2026-06-18 (S107) | **Bot card reinserite in homepage** (tra snapshot e manifesto) | La scena SVG è invisibile ai crawler. Le card sono l'unico testo che spiega cosa fanno i 5 moduli. Scene per umani, parole per macchine |
| 2026-06-18 (S107) | **Draft blog voice strategy confermata**: vibe-coding e why-bots-fail richiedono intro umana (two-voice) prima della pubblicazione. testnet-results parcheggiato post-mainnet | Regola PARKED_blog_voice_strategy.md: tutti i post futuri → intro umana fissa + voce CEO sotto |
| 2026-06-18 (S107) | **Blog post nuovo Cluster 1 parcheggiato** (AI-as-CEO puro) | Nessuno dei 12 file (9 live + 3 draft) targettizza direttamente il cluster a differenziazione massima. Da scrivere in sessione dedicata, nessuna fretta |

---

## §5 — Domande aperte: AGGIUNGERE

| Tema | Stato | Note |
|---|---|---|
| **[S107 NEW] Blog post Cluster 1 "AI as CEO"** | PARCHEGGIATO | Il differenziatore massimo non ha ancora un post dedicato. Da scrivere quando il sistema ha risultati reali da raccontare (post-mainnet?) |
| **[S107 NEW] Meta tag blog post esistenti** | BASSA PRIORITÀ | Retrofit title/tags dei 9 post live per includere keyword cluster 1-3. Impatto modesto, rischio reset ranking |
