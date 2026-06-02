## Aggiornamento BUSINESS_STATE.md — S95 (2 giugno 2026)

Sezioni impattate: §2, §3, §4, §6. Copia-incolla le parti rilevanti.

---

### §2 Marketing in-flight — AGGIUNTE

Aggiungere sotto la sezione blog esistente:

#### Strategia SEO+GEO (S95)
- **Dual-channel content strategy adottata:** ogni post blog serve SEO (keyword head-term nel titolo) + GEO (risposta diretta nei primi 2 paragrafi per citazione LLM)
- **Keyword validate (Google Keyword Planner, US+CN+EU):** "claude code" 100K–1M/mese +9.900% YoY bassa concorrenza, "ai trading bot" 10K–100K +900% media, "vibe coding" 100K–1M stabile media, "crypto trading bot" 1K–10K stabile bassa
- **Brief S95a:** piano 5 post SEO+GEO. Sequenza: POST 1 (claude code) → POST 2 (ai bot fails) → POST 3 (non-coder workflow) → POST 4 (vibe coding) → POST 5 (real results, quando dati pronti)
- **POST 1 SEO+GEO LIVE** (2 giugno 2026, commit `78483dc`): "I Used Claude Code to Build a Crypto Trading Bot. 94 Sessions Later, Here's What Works." URL: `/blog/claude-code-crypto-trading-bot`. FAQPage schema attivo (6 FAQ). Pubblicato su `main`, look dark attuale, erediterà pastello al merge redesign.

#### Canali distribuzione attivi (aggiornamento S95)
- **Medium (@BagHolderAI):** attivo da giugno 2026, 2 post pubblicati. Cross-post con canonical URL.
- **Reddit (Cart0neM):** karma building completato. Best comment su r/AIAgents: 13 upvote, 2485 views (1 giugno 2026).

#### LinkedIn (parcheggiato, post-redesign)
- **Decisione S95:** creare company page BagHolderAI + profilo personale "Max Cartone" (bagholderai@proton.me)
- **Ricognizione Claude in Chrome:** 1 solo competitor diretto (Bassam Fahmy, "AI CEO of Homains", 30 reazioni). Campo vuoto.
- **Strategia:** doppio canale (profilo per reach, company page per identità/GEO). Voce CEO. Timing: dopo merge redesign.

---

### §3 Diary Status — MODIFICA

Cambiare/aggiungere:

**Blog post pubblicati: 7** (ultimo: POST 1 SEO+GEO, 2 giugno 2026)
**Post SEO+GEO in coda: 4** (POST 2–5, cadenza 1 ogni 1-2 settimane)

---

### §4 Decisioni Strategiche Recenti — AGGIUNGERE IN TESTA

| Data | Decisione | Perché |
|---|---|---|
| 2026-06-02 (S95) | **Dual-channel SEO+GEO content strategy adottata.** Brief S95a: 5 post con keyword validate. POST 1 live in produzione | Keyword data: "claude code" 100K–1M +9.900%, "ai trading bot" 10K–100K +900%. Le long-tail narrative proposte dal CEO avevano volume zero. Post Reddit FluoTest (703 upvote) ha validato GEO come canale acquisizione (ChatGPT cita risposte dirette → 131 signups zero ad spend) |
| 2026-06-02 (S95) | **LinkedIn company page + profilo "Max Cartone" approvati, timing post-redesign** | Ricognizione Claude in Chrome: 1 solo "AI CEO" dichiarato al mondo (Homains). Campo vuoto. LinkedIn ha alta autorità dominio per GEO (35% citazioni ChatGPT da LinkedIn). Profilo separato da quello reale di Max |
| 2026-06-02 (S95) | **Medium (@BagHolderAI) confermato attivo** con 2 post. Aggiunto ai canali distribuzione | Cross-post con canonical URL. Audience più ampia e meno tecnica di Dev.to |

---

### §6 Vincoli/Deadline — MODIFICHE

Aggiornare la riga "Site redesign light theme":

| **Site redesign "Pastel Sticker v2"** | branch pronto, review pendente | CC report S95b: tutte le pagine pubbliche convertite. Branch `redesign/pastel-sticker-v2` (commit `4a6f047`), anteprima Vercel READY. Merge a discrezione Max post-review desktop+mobile |

Aggiungere riga:

| **SEO+GEO POST 2 drafting** | ~metà giugno | "Why Most AI Trading Bots Fail (And What Ours Did Wrong Too)" — keyword: ai trading bot. Cadenza 1 post ogni 1-2 settimane |
