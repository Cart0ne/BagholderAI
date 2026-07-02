# KNOWLEDGE_MAP — dove vive la conoscenza di BagHolderAI

> **Cos'è**: indice di tutti i documenti *durevoli* (stato, playbook, runbook, convenzioni,
> architettura, archivi) sparsi nel repo. È una **mappa, non il contenuto** — punta ai file,
> non li duplica. Nasce in sessione estemporanea **2026-06-28** (Opzione A: indicizzare senza
> spostare, per non rompere i path agganciati a CLAUDE.md / cron audit / memorie / script).
>
> **REGOLA DI MANUTENZIONE**: quando crei, sposti o ritiri un doc di knowledge durevole,
> aggiorna la riga qui. Se questo file e il repo divergono, vince il repo → segnalalo (CLAUDE.md §0).
>
> **Multi-macchina**: repo di sviluppo = MBP (`/Users/max/Desktop/BagHolderAI/Repository/bagholder`);
> repo runtime = Mac Mini (`/Volumes/Archivio/bagholderai`). I `logs/` vivono sul Mini, gitignored.

---

## ★ Must-read a inizio sessione

| File | Perché |
|---|---|
| [CLAUDE.md](CLAUDE.md) | Istruzioni progetto (intern). OVERRIDE su tutto |
| [PROJECT_STATE.md](PROJECT_STATE.md) | Stato tecnico — dove eri rimasto (owner: CC) |
| [BUSINESS_STATE.md](BUSINESS_STATE.md) | Vincoli strategici / Board (owner: CEO/Max; CC scrive solo su istruzione) |
| [config/validation_and_control_system.md](config/validation_and_control_system.md) | Validation & Control System — milestone viva, aggiornare a ogni brief shipped |
| [web_astro/STYLEGUIDE.md](web_astro/STYLEGUIDE.md) | **Prima** di toccare pagine del sito — palette, pattern, lezioni dolorose |

---

## 1. Stato & Governance (root)

| File | Contenuto |
|---|---|
| [CLAUDE.md](CLAUDE.md) | Istruzioni intern: file di stato, audit, compaction (cap 50KB→40KB ±2KB), workflow git, anti-assenso, naming report |
| [PROJECT_STATE.md](PROJECT_STATE.md) | Stato tecnico canonico (10 sezioni). Cap 50KB→40KB ±2KB, archive on-compaction |
| [BUSINESS_STATE.md](BUSINESS_STATE.md) | Stato strategico/marketing/Board. Cap 50KB→40KB ±2KB |
| [WORKFLOW.md](WORKFLOW.md) | Workflow Operativo — incl. §G protocollo Auditor |
| [AUDIT_PROTOCOL.md](AUDIT_PROTOCOL.md) | Protocollo audit 3 aree (cadenze, trigger, §2 lista eventi Area 2) |
| [README.md](README.md) | Overview repo |
| [QUICKSTART.md](QUICKSTART.md) | Avvio rapido |

## 2. Playbook & Convenzioni

| File | Contenuto |
|---|---|
| [SEO_RULES.md](SEO_RULES.md) | Regole operative SEO/GEO del sito (playbook 5 step, caso GSC) |
| [config/SEO_GEO_post_checklist.md](config/SEO_GEO_post_checklist.md) | Checklist viva per ogni post SEO+GEO (FAQ schema già nel template) |
| [config/SEO_deferred.md](config/SEO_deferred.md) | Interventi SEO/performance rimandati (decisi 2026-05-29) |
| [config/refactor/REDESIGN_PATTERNS.md](config/refactor/REDESIGN_PATTERNS.md) | Pattern AS-BUILT redesign "Pastel Sticker v2" |
| [web_astro/STYLEGUIDE.md](web_astro/STYLEGUIDE.md) | Style guide sito Astro |
| [docs/sherpa-parameter-rules-guide.md](docs/sherpa-parameter-rules-guide.md) | Regole parametri Sherpa — guida operativa |
| [docs/admin-dashboard-guide.md](docs/admin-dashboard-guide.md) | Legenda & guida admin dashboard |
| [docs/analytics-stack.md](docs/analytics-stack.md) | Stack analytics Umami + Vercel |
| [docs/analytics-self-exclusion.md](docs/analytics-self-exclusion.md) | Self-exclusion owner dal tracking |
| [docs/x_signatures.md](docs/x_signatures.md) | Firme dei post su X |

## 3. Runbook (procedure operative)

| File | Contenuto |
|---|---|
| [config/BOT_RESTART_RUNBOOK.md](config/BOT_RESTART_RUNBOOK.md) | Riavvio orchestrator/bot sul Mac Mini (env flag, graceful shutdown) |
| [config/TESTNET_RESET_RUNBOOK.md](config/TESTNET_RESET_RUNBOOK.md) | Reset mensile Binance Testnet (bump CYCLE, clean slate) |

## 4. Architettura, Vision & Assessment

| File | Contenuto |
|---|---|
| [docs/grid_mainnet_tf_testnet_assessment.md](docs/grid_mainnet_tf_testnet_assessment.md) | Assessment "Grid su mainnet + TF su testnet" (S108): nessun blocco tecnico go-live |
| [docs/tf_recap_S108.md](docs/tf_recap_S108.md) | Recap Trend Follower per Max (S108) |
| [web_astro/BRIEF.md](web_astro/BRIEF.md) | Brief originale del nuovo sito Astro (parallel build) |
| `briefresolved.md/VISION_brains_architecture*.md` | Vision architettura brain (v1+v2) — archiviati tra i brief risolti |

## 5. Piani & Decisioni attive (evolvono — non sono stato né brief one-shot)

| File | Contenuto |
|---|---|
| [config/MASTER_TASK_LIST_2026-07-01.md](config/MASTER_TASK_LIST_2026-07-01.md) | Master Task List — fonte dei task (item 4.12/4.13/4.14, 1.x pre-mainnet…) |
| [config/APPROVED_golive_experiment_design.md](config/APPROVED_golive_experiment_design.md) | Design dell'esperimento go-live APPROVED (collaudo €100 → €600) |

## 6. Brief attivi / in coda (`config/`) — transient, qui per non perderli

| File | Stato |
|---|---|
| [config/2026-06-14_brief_sentinel-regime-technical-fallback.md](config/2026-06-14_brief_sentinel-regime-technical-fallback.md) | Proposta CC, attende CEO/Board |
| [config/2026-06-27_S110c_brief_usdt-to-usdc.md](config/2026-06-27_S110c_brief_usdt-to-usdc.md) | USDT→USDC (MiCA), rimandato |
| [config/2026-06-28_S111_brief_grid-regime-backtest.md](config/2026-06-28_S111_brief_grid-regime-backtest.md) | Backtest grid vs hold, in coda (S110d implementato 28-giu → `briefresolved.md/`) |

> A brief chiuso → spostare in `briefresolved.md/` (memoria *completed-briefs*).

## 7. Brief parcheggiati (`config/parked/`) — con trigger di sblocco

Vedi [config/parked/README.md](config/parked/README.md) per i trigger. File:
`PARKED_blog_voice_strategy` · `PARKED_cmc_fear_greed_second_source` ·
`PARKED_marketing_research_insights_2026-06-22` · `PARKED_tf_volume_analysis_framework` ·
`PARKED_tf_xapi_pump_detection` · `brief_DUST_writeoff_parcheggiato` ·
`brief_evaluate_trading_skills`.

## 8. Investigazioni / forensics

| File | Contenuto |
|---|---|
| [investigations/slippage_btc_20260527.md](investigations/slippage_btc_20260527.md) | Slippage anomalo BTC 2026-05-27 — **referenziato nei commenti di `grid_bot.py`** |

## 9. Archivi & storico (consultazione on-demand)

| Percorso | Contenuto |
|---|---|
| [audits/PROJECT_STATE_archive.md](audits/PROJECT_STATE_archive.md) | Sezioni PROJECT_STATE rimosse in compaction (growing, mai cancellato) |
| [audits/BUSINESS_STATE_archive.md](audits/BUSINESS_STATE_archive.md) | Sezioni BUSINESS_STATE rimosse in compaction |
| `briefresolved.md/` | ~250 brief/spec risolti (session*, brief_*, vision, business_state updates). Già organizzato |
| `report_for_CEO/` + `report_for_CEO/resolved/` | Report per il CEO (naming `YYYY-MM-DD_SXX_RforCEO_SCOPE.md`); resolved = archivio |
| `drafts/` + `drafts/applied/` | Bozze ([drafts/cover_evolution_memo.md](drafts/cover_evolution_memo.md) = idea blog futura) |
| `audits/*.jsonl` + `*_manifest.json` | Archivio NewsKeeper v1 (3.182 righe, ritirato S110e) |

## 10. Audit — template (in git) vs report (locali)

| Percorso | Note |
|---|---|
| [audits/DATA_CAVEATS.md](audits/DATA_CAVEATS.md) | **Trappole note dei dati marketing/analytics** — leggere PRIMA di ogni analisi Area 3 (whitelisted in `.gitignore`, in git). Creato S115a. |
| [audits/requests/audit_request_A1.md](audits/requests/audit_request_A1.md) · [A2](audits/requests/audit_request_A2.md) · [A3](audits/requests/audit_request_A3.md) | Template **evergreen** (whitelisted in `.gitignore`, in git) |
| `audits/requests/2026*_audit[*]_*.md` | Request/follow-up specifici — **gitignored/locali** |
| `audits/reports/YYYYMMDD_audit[AX].md` | **I report veri sono GITIGNORED/locali.** In git solo la sintesi → PROJECT_STATE §9 |
| `audits/snapshots/`, `audits/reddit_stats_tracker.xlsx` | Locali (xlsx whitelisted) |

---

## ⚠️ Cosa NON è in git (locale-only) — non assumerlo committato

- **Segreti**: `config/.env`, `config/.env.marketing`, `config/gsc_service_account.json`
- **Audit report**: `audits/reports/`, `audits/snapshots/` (in git solo la sintesi §9)
- **Canale CEO→CC**: `/blog/` (inbox/done/, memoria *blog-inbox-workflow* — NON cancellare)
- **Marketing/output**: `marketing_data/`, `post_x/`, `scripts/office/`, `scripts/output/.ohlcv_cache/`, `scripts/output/backtest_trades.csv`
- **Workflow CC**: `config/.mdcompletati/`, `.instructions.md`
- **Runtime**: `logs/` (sul Mac Mini sotto `/Volumes/Archivio/bagholderai/logs/`), `venv/`, `venv_office/`
- **Vecchi build**: `web_old/`, `web/`, `web_proto/`, `analysis/`, `*_old*`

> Memorie correlate: convenzioni e gotcha vivono nella *auto-memory* di CC
> (`~/.claude/.../memory/MEMORY.md`), non nel repo — complementare a questa mappa.
