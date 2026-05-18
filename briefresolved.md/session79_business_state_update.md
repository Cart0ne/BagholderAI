# Aggiornamento BUSINESS_STATE.md — Session 79

**Last updated:** 2026-05-18 — Session 79 (CEO session: 3 brief shipped da CC, drawdown strategy, Supabase IO warning, FIFO ghost sanato).
**Updated by:** CEO
**Basato su:** PROJECT_STATE.md aggiornato 2026-05-18 (S79 chiusura, ultimo commit `fe8fca9`)

---

## Sezioni modificate:

### §2. Marketing In-Flight

Aggiungere dopo "Blog infrastructure pronta":

> **⚠️ STALE:** Sito mostra TF "dal dottore" — TF è LIVE dal 2026-05-18 21:14 CET (Tier 1-2 only, Tier 3 off). Narrativa pubblica da aggiornare prossima sessione.

Aggiungere dopo riga blog:

> - **Blog post 2:** "The Day Our Bot Ran Out of Money" (highlight V1 S16, standalone). Scritto e approvato S78, in attesa di commit+deploy CC. **Blog post 3:** piece strategico "why not live yet" — pianificato per S80 (blog day).

### §3. Diary Status

Aggiornare:

> **Diari completi:** fino a S78.
> **Backlog diary:** S79 BUILDING, ~3-4 sessioni backlog.

### §4. Decisioni Strategiche Recenti

Aggiungere in cima (le più vecchie da tagliare: S72 "Holdings = fetch_balance()" e "Frontend canonical refactor" possono uscire, vivono nel git):

| Data | Decisione | Perché |
|---|---|---|
| 2026-05-18 (S79 CEO) | **TF riattivato Tier 1-2, Tier 3 weight=0** | Board reverse della decisione "park" di S78. Regime "fear" + distance filter 12% → TF scansiona senza allocare, counterfactual data a costo zero. Se mercato stabilizza, tf_grid handoff pronto |
| 2026-05-18 (S79 CEO) | **Idle recalibration soppresso quando cash esaurito** | Board proposal. Guard in grid_bot.py: skip idle quando available < $5. Riduce rumore operativo durante drawdown |
| 2026-05-18 (S79 CEO) | **Write-on-change pattern su Supabase** | Supabase warning IO Budget. Sentinel/Sherpa/snapshots scrivono solo su cambiamento o heartbeat (10min/10min/5min). Riduzione ~80% write in mercato piatto |
| 2026-05-18 (S79 CEO+CC) | **FIFO dichiarato morto, avg-cost canonical** | Bug S70c era già chiuso in S72. "Strada 2 ~3-4h" ridotto a verifica identità ~30min. Frame: avg-cost + Equity P&L broker-comparable |
| 2026-05-18 (S79 CEO) | **Haiku daily commentary resta attivo anche senza trade** | "The silence is the story." Drawdown documentato > drawdown ignorato. Day 10 senza trade = contenuto migliore di metà dei giorni con trade |
| 2026-05-18 (S79 CEO) | **State files: Project Knowledge prima, GitHub fallback** | Memory #22 aggiunta. GitHub stale a S63 mentre PK aveva S78 |

### §5. Domande Aperte per CC

Aggiungere:

| Tema | Stato | Note |
|---|---|---|
| **Counterfactual tracker: aggiungere regime Sentinel** | Nice-to-have | counterfactual.py non logga regime. Utile per correlare skip ↔ regime. ~30-45min. Post-osservazione |
| **Sito TF narrativa update** | Prossima sessione | "dal dottore" → "on Tier 1-2". SVG + badge. ~30-45min |
| **Audit Area 2 (coerenza progetto)** | Mai eseguito, proposta CC | Roadmap vs PROJECT_STATE vs BUSINESS_STATE consistency check |

### §7. Cosa NON sta succedendo e perché

Aggiornare:

> - **Sherpa LIVE** — ancora in DRY_RUN. Osservazione Sprint 2 in corso (scadenza naturale 21-22 maggio). Proposte visibili ma non applicate.
> - **Mainnet €100** — target fine giugno / inizio luglio. Sequenza Sentinel-first rispettata.
> - **Blog post 2 + 3** — pronti nel backlog, pianificati per S80 (blog day).
> - **Retention cron jobs** — deliberatamente rimandati: prima analizzare dati Sentinel/Sherpa, poi pulire.
> - **X reply strategy** — definita ma non ancora testata con costanza (0 reply sistematiche fatte dal 15 maggio).
