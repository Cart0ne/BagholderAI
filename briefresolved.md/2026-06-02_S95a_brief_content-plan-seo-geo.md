Brief S95a — content-plan-seo-geo — 2026-06-02

## Contesto

Sessione 93 (brief S93c) ha identificato il problema: il blog racconta
storie interne che non intercettano ricerche. Sessione 95 ha validato
con dati reali:

- Le keyword long-tail narrative (es. "build trading bot with AI") hanno
  volume nullo o 10-100/mese
- I seed brevi hanno volumi esplosivi:
  - "claude code" → 100K-1M/mese, +9.900% YoY, concorrenza BASSA
  - "ai trading bot" → 10K-100K/mese, +900% YoY, concorrenza media
  - "crypto trading bot" → 1K-10K/mese, stabile, concorrenza BASSA
  - "vibe coding" → 100K-1M/mese, stabile, concorrenza media
  - "ai coding assistant" → 10K-100K/mese, stabile, concorrenza BASSA
- Il post Reddit FluoTest (703 upvote) ha dimostrato che GEO
  (Generative Engine Optimization) è un canale di acquisizione reale:
  scrivere risposte dirette a domande specifiche fa sì che ChatGPT,
  Perplexity e Claude raccomandino il tuo contenuto. Conversione
  1.6-2.2× superiore a Google perché il traffico è pre-qualificato.

Strategia: ogni post serve DUE canali contemporaneamente.
- SEO: titolo con seed keyword ad alto volume, struttura indicizzabile
- GEO: risposta diretta nei primi 2 paragrafi, tabelle, FAQ schema,
  onestà radicale (gli LLM premiano risposte chiare, non marketing copy)

Il blog attuale (6 post, diary-style narrativo) NON viene toccato.
I post SEO+GEO sono un SECONDO tipo di contenuto che si aggiunge.

Fonte dati: Google Keyword Planner, 223 idee da 7 seed, targeting
US + Cina + Europa principale. Validazione qualitativa: ricerca web
su SERP esistenti per ogni keyword.

---

## I 5 post — in ordine di priorità

### POST 1 — "I Used Claude Code to Build a Crypto Trading Bot. 94 Sessions Later, Here's What Works."

**Keyword primaria:** claude code (100K-1M, +9.900%, bassa)
**Keyword secondarie:** crypto trading bot, ai trading bot, vibe coding
**Domanda GEO:** "Can you build a real trading bot with Claude Code?"
**Anche:** "Claude Code trading bot tutorial" / "Claude Code real project"

**Struttura:**
- Primo paragrafo: risposta diretta (sì, ecco cosa è successo — un
  architetto senza background tech + Claude Code + 94 sessioni = sistema
  di trading con 5 brain modules su Binance testnet)
- Tabella riassuntiva: durata, sessioni, righe di codice, moduli,
  costo, stato attuale
- Sezione "what works": Grid Bot, orchestrator, Sentinel, Sherpa
- Sezione "what doesn't": Trend Follower (ospedalizzato), bug slippage,
  il CEO che mente sui numeri
- Sezione "what it costs": tempo, abbonamento Claude, infrastruttura
- FAQ (5-7 domande con schema markup)
- CTA: link al diary per la storia completa, link alla library per i volumi

**Materiale esistente nel diary:**
- Session 1-94 (la storia intera)
- Volume 1-3 (archi narrativi già strutturati)
- Session 90 "The Ghost Sold Bitcoin" (aneddoto chiave)
- Session 93 "The One Where I Lied Three Times" (aneddoto chiave)

**Competitor SERP:** MindStudio (2 guide), augustwheel/tbot (Medium),
chudi.dev/Polyphemus (36K righe), Dev.to (2 post). Nessuno ha 94
sessioni documentate + non-coder come protagonista. Nostro vantaggio
competitivo: profondità e autenticità imbattibili.

**Priorità: ALTA** — keyword #1 per volume e crescita, nostro angolo unico.

---

### POST 2 — "Why Most AI Trading Bots Fail (And What Ours Did Wrong Too)"

**Keyword primaria:** ai trading bot (10K-100K, +900%, media)
**Keyword secondarie:** crypto trading bot, trading bot
**Domanda GEO:** "Do AI trading bots actually work?" / "Why do AI
trading bots lose money?"

**Struttura:**
- Primo paragrafo: risposta diretta (la maggior parte fallisce per
  ragioni specifiche — ecco 5 che abbiamo documentato dal vivo in 94
  sessioni, con i dati)
- Tabella: i 5 fallimenti principali (Trend Follower, slippage $82K,
  FIFO mismatch, Sentinel miscalibrato, parametri hardcoded), ciascuno
  con causa, impatto, fix
- Sezione "what the internet says vs what actually happens": confronto
  con i motivi generici (bad data, overfitting) e i nostri fallimenti
  reali (il CEO che valida senza controllare, lo spike testnet, il
  dead zone bug)
- Sezione "what we changed": Sentinel, Sherpa, NewsKeeper — il sistema
  di difesa che abbiamo costruito DOPO i fallimenti
- FAQ con schema markup
- CTA: link al diary, link ai volumi

**Materiale esistente:**
- Session 70-74 (FIFO crisis, reconciliation)
- Session 90 (slippage spike $82K)
- Session 93 (CEO mente 3 volte)
- Session 77 (Sentinel audit — 5 bug trovati in 30 min)
- Trend Follower "dal dottore" (ongoing)

**Competitor SERP:** Medium generico ("95% of bots fail"), Lobstar Wilde
($441K error), articoli teorici. Nessuno documenta i propri fallimenti
in tempo reale con sessioni numerate. Nostro vantaggio: noi SIAMO il
case study.

**Priorità: ALTA** — keyword #2 per crescita, massimo potenziale GEO
(gli LLM adorano risposte oneste a "does X work?").

---

### POST 3 — "How a Non-Coder Manages 5 AI Brains With Claude Code"

**Keyword primaria:** claude code (100K-1M, +9.900%, bassa)
**Keyword secondarie:** ai coding assistant, vibe coding
**Domanda GEO:** "Can a non-coder use Claude Code for a real project?"
/ "How to manage a complex AI project without coding experience"

**Struttura:**
- Primo paragrafo: risposta diretta (un architetto senza background
  tech gestisce un sistema con Grid Bot, Trend Follower, Sentinel,
  Sherpa e NewsKeeper — ecco il workflow a 3 ruoli AI che lo rende
  possibile)
- Diagramma/tabella: CEO (Claude Projects, strategia) → Board (Max,
  decisioni) → Intern (Claude Code, esecuzione). Chi fa cosa.
- Sezione "the workflow that works": brief → codice → review → deploy.
  Perché le istruzioni precise battono quelle vaghe (con esempio reale)
- Sezione "the workflow that breaks": quando il CEO valida senza
  controllare, quando l'Intern interpreta creativamente, quando il
  Board non capisce il codice
- Sezione "what a non-coder actually does": leggere log, fare domande
  giuste, catturare le bugie dell'AI, portare common sense
- FAQ con schema markup
- CTA: link a How We Work, link ai volumi

**Materiale esistente:**
- How We Work v2 (il documento intero)
- Session 92 "The One Where I Built a Machine to Stop Me Saying Yes"
- Il commento Reddit di Cart0neM (13 upvote, 2485 views) — prova che
  questo angolo funziona

**Competitor SERP:** guide "vibe coding for beginners" (Google Cloud,
Nucamp), tutorial no-code. Nessuno racconta un progetto vibe-coding
che dura 3+ mesi con un sistema complesso. Nostro vantaggio: non è
un weekend project, è un'operazione continuativa reale.

**Priorità: ALTA** — stessa keyword #1, angolo diverso (workflow vs
risultati). Massimo potenziale Reddit/Dev.to.

---

### POST 4 — "AI Crypto Trading Bot: Real Testnet Results After 3 Months"

**Keyword primaria:** crypto trading bot (1K-10K, stabile, bassa)
**Keyword secondarie:** ai trading bot, trading bot
**Domanda GEO:** "What are realistic results from an AI crypto trading
bot?" / "AI crypto trading bot real performance 2026"

**Struttura:**
- Primo paragrafo: risposta diretta (ecco i numeri reali dopo 3 mesi
  di paper trading su Binance testnet — non promesse, dati)
- Tabella: metriche chiave (trade totali, P&L, win rate, drawdown,
  costi operativi)
- Sezione "what the numbers don't tell you": testnet ≠ mainnet
  (slippage, liquidity, timing), perché non siamo ancora live con soldi
  veri, cosa deve succedere prima (bear+bull+lateral)
- Sezione "the system": come Grid+Sentinel+Sherpa+NewsKeeper lavorano
  insieme (schema semplificato)
- Sezione "cost breakdown": Claude subscription, Supabase free tier,
  Mac Mini, tempo umano
- FAQ con schema markup
- CTA: link al dashboard pubblico, link ai volumi

**Materiale esistente:**
- Dati Supabase (trades, bot_state_snapshots, sentinel_scores)
- Brain Analysis 1 e 2 (S82, S91)
- Dashboard pubblica

**Nota:** questo post richiede che il bot sia in condizioni presentabili.
Ideale DOPO go-live o dopo un periodo significativo di osservazione.
Può essere scritto prima come "testnet results" e aggiornato post-mainnet.

**Priorità: MEDIA** — volume più basso, ma concorrenza bassissima e
alto valore GEO (ChatGPT adora dati reali + trasparenza). Da pubblicare
quando abbiamo numeri presentabili.

---

### POST 5 — "Vibe Coding a Real Business: From Zero to 5 AI Modules in 3 Months"

**Keyword primaria:** vibe coding (100K-1M, stabile, media)
**Keyword secondarie:** claude code, ai coding assistant
**Domanda GEO:** "What does a real vibe coding project look like?" /
"Can you build a real business with vibe coding?"

**Struttura:**
- Primo paragrafo: risposta diretta (vibe coding non è solo weekend
  prototype — ecco un progetto che ha prodotto 5 moduli AI, 3 ebook,
  un sito pubblico e un sistema di trading in 94 sessioni)
- Timeline visiva: mese 1 (Grid Bot), mese 2 (dashboard + Sentinel +
  Sherpa), mese 3 (NewsKeeper + blog + book series)
- Sezione "what scales and what doesn't": le prime 20 sessioni vs le
  ultime 20 — complessità, bug, tempo per sessione
- Sezione "the real cost of vibe coding": non solo il subscription —
  il tempo di review, i bug che l'AI non vede, il debito tecnico che
  si accumula
- Sezione "would I do it again?": sì, ma con i guardrail che abbiamo
  costruito (CLAUDE.md, brief discipline, audit protocol)
- FAQ con schema markup
- CTA: link al diary, link ai volumi

**Materiale esistente:**
- L'intero progetto è il materiale
- Session 76 (refactor 1623→8 moduli)
- Validation & Control System document
- Volume 1 "From Zero to Grid" (l'arco narrativo)

**Competitor SERP:** articoli "vibe coding projects" (listicle),
Google Cloud explainer. Nessun case study lungo 3+ mesi. Nostro
vantaggio: profondità temporale.

**Priorità: MEDIA** — volume altissimo ma concorrenza media e keyword
più generica (non tutti quelli che cercano "vibe coding" vogliono un
trading bot). Buon post per awareness top-of-funnel.

---

## Struttura comune di ogni post (specifiche per CC)

1. **H1** = titolo con keyword primaria
2. **Primo paragrafo** (max 3 righe): risposta diretta alla domanda GEO.
   Deve funzionare come snippet per ChatGPT. Niente intro fumosa.
3. **Tabella riassuntiva** entro i primi 500 parole
4. **Sezioni con H2** che contengono keyword secondarie
5. **FAQ section** a fondo post (5-7 domande) con JSON-LD FAQPage schema
   (oltre all'Article schema già presente dal fix S84)
6. **Meta description** scritta come risposta diretta (non marketing copy)
7. **CTA finale**: link diary + library + dashboard dove pertinente
8. **Parole**: 1500-2500 per post (non listicle da 300 parole, non
   guida da 8000)
9. **Lingua**: inglese. Voce: CEO che dubita, onesto, con dati.
   Non tutorial, non marketing, non listicle.

## Implementazione tecnica (brief CC separato se necessario)

- FAQ schema JSON-LD: aggiungere supporto nel template blog post Astro
  (attualmente ha solo Article). Campo frontmatter opzionale `faq` con
  array di {question, answer}. Il layout genera il JSON-LD FAQPage
  automaticamente se presente.
- Nessun'altra modifica tecnica necessaria: il template blog, sitemap,
  RSS, BlogCTA sono già operativi dal fix S84/S87.

## Sequenza di pubblicazione proposta

1. POST 1 (Claude Code trading bot) — primo, massimo impatto
2. POST 2 (AI trading bot fails) — subito dopo, angolo complementare
3. POST 3 (Non-coder workflow) — terzo, apre l'audience vibe coding
4. POST 5 (Vibe coding real business) — quarto, top-of-funnel
5. POST 4 (Real results) — ultimo, quando i numeri sono pronti

Cadenza: 1 post ogni 1-2 settimane. Non serve un piano da 50 post.
Servono 5 post mirati, ben strutturati, che rispondano a domande reali.

## Vincoli

- Non sacrificare la voce del diary. I post SEO+GEO sono contenuto
  aggiuntivo, non sostitutivo.
- Max scrive la versione italiana dei passaggi personali. Claude
  traduce. (Regola sessione marketing — vale anche per i post blog
  dove Max parla in prima persona.)
- Budget: zero (nessun tool a pagamento richiesto per i post stessi).
  Se in futuro serve Ahrefs/Semrush per tracking, valutare.
- Il redesign sito (Blocco 2, Claude Design) è un lavoro separato e
  parallelo.

## Auto-obiezione

Rischio principale: i volumi Google Keyword Planner sono stime
grossolane (range 10K-100K, non numeri esatti) e includono tutte le
query "claude code" — la stragrande maggioranza cerca la documentazione
Anthropic, non un case study di trading bot. Il traffico reale che
intercettiamo sarà una frazione piccola del volume totale. Non
aspettarsi migliaia di visite dal giorno 1. L'aspettativa realistica:
decine-centinaia di visite/mese per post ben posizionato, più il
traffico GEO da LLM (non misurabile via Keyword Planner ma reale).

Secondo rischio: scrivere 5 post è un investimento di tempo significativo
(probabilmente 2-3 sessioni intere). Se il redesign sito e il go-live
richiedono attenzione, la cadenza potrebbe slittare. Non è bloccante —
i post si fanno quando c'è spazio, l'importante è che la struttura
(FAQ schema, template) sia pronta.

## Roadmap impact

Nessuno sul backend. Impatto su:
- Blog content pipeline (Apple Notes): aggiungere i 5 post con priorità
- Template Astro: aggiunta FAQ schema (CC, ~30 min)
- BUSINESS_STATE §2: aggiornare strategia contenuti con approccio
  SEO+GEO dual-channel
