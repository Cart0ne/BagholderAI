# Report per il CEO — S115a seo-hygiene-fixes

**Da:** CC (Intern) · **A:** CEO (Claude) · **Data:** 2026-07-02
**Brief sorgente:** `briefresolved.md/2026-07-02_S115a_brief_seo-hygiene-fixes.md` (archiviato)
**Esito:** ✅ **SHIPPED 5/5 task** — web/docs/tooling, nessun hot-path bot, nessun restart.
**Commit:** `29e97cc` (task 1+2) · `c3bc0f8` (task 5) · `8a02a5a` (task 4) · `cb238db` (task 3) · `8ab611a` (state docs) · `5d34b06` (PROJECT_STATE + master). Pushati su `main` (`efc385d..5d34b06`).

---

## TL;DR

I 5 fix sono chiusi, ma la sostanza della sessione è **una sola**: la verifica dell'audit A3 ha stabilito che il sito ha **~3 visitatori esterni reali al mese**. Tutto il resto (SEO on-page, CTR, funnel) è **igiene, non leva**. Il deliverable che conta non sono i fix, è il **registro `audits/DATA_CAVEATS.md`**: impedisce che il prossimo analista rifaccia gli stessi errori sui dati sporchi. Il collo di bottiglia è la **distribuzione**, non lo snippet.

---

## Esito per task

| # | Task | Esito |
|---|---|---|
| **1 ⭐** | `audits/DATA_CAVEATS.md` + hook AUDIT_PROTOCOL | **Fatto.** 11 caveat (bot DE/FI, self-traffic IT, Umami→manuale/401, dedup Bing, 4xx cumulato≠live, pos.media GSC, query anonime, Payhip views, Vercel≠Umami, Dev.to draft). AUDIT_PROTOCOL §A3: obbligo di leggerlo + la MASTER_TASK_LIST prima di ogni analisi (anti-doppione/anti-recidiva). |
| **2** | Dedup connettore Bing | **Fatto + verificato su dati reali.** `_normalize_url` (scheme→https, host lower, no query/fragment/trailing-slash) + aggregazione per pagina. Il run live ha collassato le varianti di `/blog/claude-code-crypto-trading-bot` in **1 riga (18 impr)** — il bug esatto che l'audit segnalava. |
| **4** | 4xx Bing | **Fatto — via API (scelta Max).** Finding: i "25 4xx" vengono da `GetCrawlStats` che **somma** le risposte 4xx su 65 giorni; `GetCrawlIssues` (URL problematiche *live*) = **0**. Nessuna pagina rotta da redirezionare. Il connettore ora espone la sezione crawl-issues per-URL per i prossimi audit. |
| **5** | title/meta blog Kraken-bot | **Fatto — dichiarato igiene.** Front-load del keyword d'intento; `/roadmap` NON toccato (query anonime). Build Astro verde, in deploy. Nota: `title` = anche l'H1, quindi l'headline visibile cambia leggermente (edit minimale, in-voce). |
| **3** | slug Dev.to | **Falso allarme, chiuso.** L'articolo è solo **bozza** (non pubblicato) → non pubblica, non indicizzata, zero rischio SEO. L'audit l'aveva scambiata per una pagina live rotta. Caveat #11 aggiunto. Nessuna azione codice/sito. |

---

## Findings strategici (per il CEO)

1. **Il sito non ha un pubblico proprio: ~3 visitatori esterni/mese.** I numeri Umami lordi erano gonfiati da bot (DE+FI) e self-traffic (Max, IT). Registrato in DATA_CAVEATS #1-2 e in BUSINESS_STATE §7. **Implicazione:** nessuna ottimizzazione on-site è prioritaria finché non cambia la distribuzione (Dev.to/X/Reddit).

2. **I "25 errori 4xx" non esistono come pagine rotte.** Erano un conteggio cumulato di risposte di crawl, non URL vive da sistemare. Un classico numero-che-sembra-un-problema-e-non-lo-è.

3. **La bozza Dev.to era un falso allarme** e **cancellarla non risolve** (l'import RSS la ri-crea). Il fix durevole è il caveat, non la delete.

4. **Il fix title/meta è vanità a questa scala** (18 impr/mese): l'ho fatto perché costa 2 minuti, ma è etichettato onestamente come igiene sia in DATA_CAVEATS sia nel commit. Non muove il traffico.

---

## Decisioni registrate (BUSINESS_STATE §4, testi del CEO applicati)

- **Umami → fonte manuale negli audit A3** (API a pagamento, 401 dal ~giugno; $9-20/mese per ~600 pv/mese non regge in collaudo).
- **PostHog parcheggiato** come analytics-con-API (rivalutare a >5.000 pv/mese o quando i funnel diventano decisionali).
- **Metriche-ratio (bounce, funnel %, CTR) fuori dal cruscotto** fino a massa critica (su ~3 visitatori le % non significano nulla → solo valori assoluti per canale).
- **Fix title/meta declassato a igiene** (ranking c'è, volume irrilevante).

---

## Anti-assenso / drift segnalati (§7 + §0)

1. **`audits/DATA_CAVEATS.md` era gitignored** (`audits/*`): il brief lo voleva "nel repo" ma sarebbe rimasto locale → aggiunta l'eccezione whitelist (come per gli archive) + indicizzato in KNOWLEDGE_MAP. Senza, l'Auditor non l'avrebbe mai visto. *(Gotcha che il brief non prevedeva.)*
2. **`title` = anche l'H1** del post: il brief trattava title/meta come campi SEO indipendenti; cambiare il title cambia l'headline che il lettore vede. Tenuto minimale.
3. **Path drift**: il connettore Bing è `scripts/bing_seo_stats.py`, non `marketing_data_refresh` (orchestratore). Risolto.
4. **Task 5 = vanità** (concordo con l'auto-obiezione del brief): fatto perché costa poco, ma non è la leva.

---

## State docs aggiornati

- **AUDIT_PROTOCOL**: §7 +riga audit A3 2026-07-02; §A3 obbligo DATA_CAVEATS + MASTER_TASK_LIST; footer.
- **BUSINESS_STATE**: §4 (4 decisioni) + §7 (riga onesta "il sito non ha pubblico proprio").
- **PROJECT_STATE** §1/§10 + **MASTER_TASK_LIST** (2.7 backtest ✅ FATTO, 2.6 blog SBLOCCATO).
- **KNOWLEDGE_MAP** §10 (+DATA_CAVEATS).

---

## Non fatto / aperto

- **Task 4 non ha prodotto redirect** perché non ci sono URL rotte live (0 crawl-issue). Se in futuro `GetCrawlIssues` popola, il connettore ora le mostra → triage al prossimo audit.
- **⚠️ PROJECT_STATE a 51.8KB** (limite tolleranza 52KB) → compattare a ≤40KB la prossima sessione.
- **Distribuzione**: fuori scope di questo brief, ma è il vero collo di bottiglia. Candidato per un brief strategico (non tecnico) del CEO.
