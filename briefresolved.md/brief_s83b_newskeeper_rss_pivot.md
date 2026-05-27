# Brief S83b — NewsKeeper Sprint 1: RSS Pivot

**Author:** CEO (Claude)
**Date:** 2026-05-27 (documentato retroattivamente, brief 88a)
**Decision date:** 2026-05-23 (S83, durante implementazione brief S83 NewsKeeper Architecture)
**Status:** SHIPPED (S83)

## Decision

CryptoPanic free tier discontinued (2026-04-01). Paid tier (~$30/month) fuori budget.
Dopo ricerca alternative, Board+CEO decidono: RSS feeds zero-auth come fonte primaria per NewsKeeper Sprint 1.

## What changed vs original brief (brief_s83_newskeeper_architecture.md)

- `bot/newskeeper/readers/cryptopanic.py` → NON implementato (API morta)
- `bot/newskeeper/readers/etf_flows.py` → deferito a Sprint 2+
- `bot/newskeeper/readers/macro_calendar.py` → deferito a Sprint 2+
- `bot/newskeeper/readers/rss_feeds.py` → UNICA fonte Sprint 1
- NewsKeeper è standalone (PID 78098), NON orchestrator-managed
- 3 RSS feeds: CoinDesk, CoinTelegraph, Decrypt
- Classificatore regex (non Haiku) — ~60% false positives, sufficiente per Sprint 1 observation

## References

- BUSINESS_STATE §4 voce 2026-05-24
- PROJECT_STATE §10 voce S83
- Audit Area 2 finding 2.2

## Roadmap impact

Nessuno (Sprint 1 era già "todo" nel roadmap; il cambio è nella fonte, non nello scope pubblico). Riflesso nel roadmap pubblico in S88/brief 88b: Phase 14 "NewsKeeper — Brain #5", task "Sprint 1: RSS feed collection + regex classifier" done.
