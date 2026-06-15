# Parked Briefs

Brief parcheggiati in attesa di trigger specifici. Non sono abbandonati — hanno criteri di riapertura.

| Brief | Parcheggiato da | Trigger di sblocco |
|---|---|---|
| brief_DUST_writeoff_parcheggiato.md | 2026-04-21 (S~55) | Da eseguire PRIMA del go-live mainnet €100. **Scope ristretto 2026-06-15**: layer "logica decisionale" chiuso da S105, "write-off runtime" già in `dust_handler`; resta solo convert-to-BNB (`sapi/v1/asset/dust`) + reconciliation wallet↔DB + flag `written_off_at`. Vedi nota in testa al brief. |
| brief_evaluate_trading_skills.md | 2026-05-01 (S~59) | Post primo trimestre di TF LIVE Tier 1-2 con dati sufficienti (~90 giorni da S79b = ~metà agosto 2026) |
| PARKED_blog_voice_strategy.md | 2026-06-09 (sessione marketing) | **Quasi-chiuso** (verificato 2026-06-15): standard two-voice già applicato ai post + Dev.to sincronizzato (conferma Max). **Residuo UNICO**: revisione col formato two-voice dei 3 draft non ancora pubblicati da nessuna parte — `why-most-ai-trading-bots-fail.md`, `vibe-coding-a-real-business.md`, `ai-crypto-trading-bot-real-testnet-results.md` — prima di pubblicarli. Territorio marketing/CEO + audit Area-3. |
| PARKED_golive_experiment_design.md | 2026-06-10 (sessione strategia) | Prerequisito **pre-mainnet** — sessione di lavoro dedicata. Checklist decisioni aperte §8 (coin fisse grid, BONK→TF, stop-loss TF, cancelli rampa, criterio bug-vs-perdita per il rabbocco, trigger verdetto, telemetria attribuibile, Victory Lap). Note stato 2026-06-15: §9 "Sherpa fuori da dry-run" già ✅ (S102b); §7 allocazione è proposta ≠ config attuale (oggi BTC/SOL/BONK tutti `grid`). |

Last updated: 2026-06-15 (DUST re-scopato post-S105 + indicizzati i 2 PARKED blog-voice/go-live)
