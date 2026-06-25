# Parked Briefs

Brief parcheggiati in attesa di trigger specifici. Non sono abbandonati — hanno criteri di riapertura.

| Brief | Parcheggiato da | Trigger di sblocco |
|---|---|---|
| brief_DUST_writeoff_parcheggiato.md | 2026-04-21 (S~55) | Da eseguire PRIMA del go-live mainnet €100. **Scope ristretto 2026-06-15**: layer "logica decisionale" chiuso da S105, "write-off runtime" già in `dust_handler`; resta solo convert-to-BNB (`sapi/v1/asset/dust`) + reconciliation wallet↔DB + flag `written_off_at`. Vedi nota in testa al brief. |
| brief_evaluate_trading_skills.md | 2026-05-01 (S~59) | Post primo trimestre di TF LIVE Tier 1-2 con dati sufficienti (~90 giorni da S79b = ~metà agosto 2026) |
| PARKED_blog_voice_strategy.md | 2026-06-09 (sessione marketing) | **Quasi-chiuso** (verificato 2026-06-15): standard two-voice già applicato ai post + Dev.to sincronizzato (conferma Max). **Residuo UNICO**: revisione col formato two-voice dei 3 draft non ancora pubblicati da nessuna parte — `why-most-ai-trading-bots-fail.md`, `vibe-coding-a-real-business.md`, `ai-crypto-trading-bot-real-testnet-results.md` — prima di pubblicarli. Territorio marketing/CEO + audit Area-3. |
| PARKED_golive_experiment_design.md | 2026-06-10 (sessione strategia) | Prerequisito **pre-mainnet** — sessione di lavoro dedicata. Checklist decisioni aperte §8 (coin fisse grid, BONK→TF, stop-loss TF, cancelli rampa, criterio bug-vs-perdita per il rabbocco, trigger verdetto, telemetria attribuibile, Victory Lap). Note stato 2026-06-15: §9 "Sherpa fuori da dry-run" già ✅ (S102b); §7 allocazione è proposta ≠ config attuale (oggi BTC/SOL/BONK tutti `grid`). |
| PARKED_cmc_fear_greed_second_source.md | 2026-06-22 (sessione lavoro CEO) | Brief futuro: CMC Fear&Greed come 2ª fonte Sentinel (`cmc_fng.py` accanto a `alternative_fng.py`, API key CMC già in `.env`). Logga in `sentinel_scores.raw_signals`, nessuna modifica a `regime_analyzer`. Trigger: sessione robustezza regime / Sentinel Phase B. = domanda aperta §5 BUSINESS_STATE. |
| PARKED_marketing_research_insights_2026-06-22.md | 2026-06-22 (sessione marketing) | 3 spunti da ricognizione web: (1) SEO long-tail + intent-matching GSC, (2) backtest validation 3-test, (3) posizionamento "cosa NON siamo" + disclaimer. Trigger: prossima sessione SEO/blog SEO · Portfolio Guardian design · redesign sito/pre-mainnet legal. |
| PARKED_tf_volume_analysis_framework.md | 2026-06-22 (S108) | **Gamba 2 CHIUSA (esito negativo) in S109** (`report_for_CEO/2026-06-25_S109_RforCEO_tier-breadth-regime-signal.md`): la soglia volume $2M **discrimina il rumore** (T3-micro è rumore puro) ma **non produce segnale predittivo** sui rimbalzi T1/2. **Resta solo la gamba 3** (bibliografia volume/breadth/social = desk research), indipendente dall'analisi dati. |
| PARKED_tf_xapi_pump_detection.md | 2026-06-22 (S108) | Esploratoria: TF signal → check menzioni X API (social basso=genuino, alto=pump coordinato). Trigger: DOPO gamba 2 del volume framework + verdetto barometro. Costo X API Basic $200/mese → solo con MRR positivo. |

Last updated: 2026-06-25 (S109 — indicizzati 4 PARKED del 22-giu: cmc-fng, marketing-insights, tf-volume-framework, tf-xapi-pump)
