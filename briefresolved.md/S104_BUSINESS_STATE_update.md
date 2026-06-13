# BUSINESS_STATE Update — Session 104

**Istruzione per CC:** applica le seguenti modifiche a `BUSINESS_STATE.md` in root del repo.

---

## Header

Sostituire la riga `**Last updated:**` con:

```
**Last updated:** 2026-06-12 — Session 104 chiusura (volume-PnL analysis, "The Experiment" income page, expense mapping, parking lot cleanup, blog publish, dashboard fixes).
```

Sostituire `**Updated by:**` con:

```
**Updated by:** CEO (update S104 via Max)
```

Sostituire `**Basato su:**` con:

```
**Basato su:** S104 report CC (income-page-and-web-touchups, dashboard-brain-cards), S103a report CC (volume-pnl-correlation), diary S104
```

---

## §2 Marketing In-Flight

Aggiungere dopo l'ultimo item nella sezione frontend internals:

```
- **Blog "How a Non-Coder Manages 5 AI Brains" PUBLISHED** (S104) — post two-voice, portabile per cross-post (tabella→lista, nomi generici→reali: Sherpa, NewsKeeper). Canonical: bagholderai.lol/blog/non-coder-5-brains. Cross-post Dev.to/Substack pendente.
- **Dashboard pubblica §2 redesign LIVE** (S103b→S104) — 5 card statiche → righe full-width pipeline con dati live e polling 5min. THE TRADERS: TF→Grid+sparkline. THE BRAINS: NewsKeeper→Sentinel→Sherpa. Tutti brain LIVE (niente DRY_RUN). Token `--color-bot-news` in STYLEGUIDE §5.
- **Card Sherpa homepage: ACTIVE (badge TEST)** (S104) — aggiornata da DRY_RUN. MODE LIVE, PARAMS 7 (3 strategy + 4 protective S103a), badge TEST mantenuto (opera su testnet). 
- **"/income" — The Passive Income Experiment: scaffold PRIVATO** (S104) — pagina combinata revenue+spese+attention+test history. Data-driven da tabella Supabase `passive_income`. KPI: Revenue €0, Spent ~€274, Conversion 0%, Visitors ~575/30d. Running costs breakdown (Claude Max €270 domina 98.5%). noindex, fuori da menu/sitemap. URL: bagholderai.lol/income.
```

---

## §3 Diary Status

Aggiornare il conteggio sessioni:

```
S104 COMPLETE (2026-06-12). V4 in accumulo (arc: NewsKeeper → go-live → results). S105 prossima.
```

---

## §4 Decisioni Strategiche Recenti

Aggiungere in cima alla tabella:

```
| 2026-06-12 (S104) | **Volume-PnL analysis: NESSUNA correlazione** — no filter volume sullo scanner | CEO ha trovato pattern apparente (basso volume → migliori ritorni) su 56 coppie paper trading. CC ha dimostrato che 32/56 erano righe sintetiche (orphan closures, PnL=0). Su 19 trade reali: Pearson 0.03. Validazione esterna (12 mesi Binance, 162 coin): confermata assenza correlazione. TF reale: WR 52.6%, PnL +1.49% (dati puliti). Anti-surge guard (p=0.09) parcheggiato post-barometro |
| 2026-06-12 (S104) | **Spese progetto mappate: ~€274 totali** (Claude Max €270, Haiku $1.77, Grok $1.11, dominio $1.54, infra €0) | 98.5% del costo = abbonamento AI. Tutto il resto su free tier. CEO non ha accesso al billing dashboard Anthropic → gap operativo. Soluzione trovata: Anthropic Admin API (Usage & Cost endpoint). Implementazione parcheggiata |
| 2026-06-12 (S104) | **"The Experiment" = pagina unica revenue+spese+trading journey** | Sostituisce il concept "Passive Income Dashboard". Scaffold privato (noindex). Si popola con dati reali progressivamente. Non pubblicare fino a decisione Board |
| 2026-06-12 (S104) | **Area 2 audit: RISOLTO e automatizzato** (Cowork monthly). Rimosso da parking lot | Era flaggato "mai eseguito" da S78 — memoria CEO stale. In realtà completato e schedulato via Cowork (audit automatico mensile + email via Gmail draft + Apps Script) |
```

---

## §5 Domande Aperte per CC

Aggiungere:

```
| **[S104 NEW] Automazione spese Haiku — Anthropic Admin API** | PARKED | Endpoint `/v1/organizations/usage_report/messages` + `/v1/organizations/cost_report`. Serve Admin API key (Max genera da console.anthropic.com). Script mensile: chiama API → filtra Haiku → scrive in Supabase `project_expenses`. Insieme a scheduled €90 il giorno 4 di ogni mese |
```

Rimuovere o marcare DONE la riga `[S102 NEW] Formalizzare parametri Board-only + default automatici coin nuovi` — completato in S103 (brief S103a, board params Sherpa-managed con BOARD_TABLE per volatility tier + debounce 24h).

---

## §7 Cosa NON Sta Succedendo e Perché

Aggiornare la riga riguardante la Passive Income Dashboard (se esiste) con:

```
- **Revenue automation completa**: la pagina /income esiste come scaffold privato, ma l'automazione fonti (Payhip, BMC, Umami API) è rinviata al primo euro. A €0 darebbero "0" → over-engineering. Solo Umami ha già un connettore. Haiku costs: soluzione Admin API trovata, parcheggiata.
```
