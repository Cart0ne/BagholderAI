# NewsKeeper — Monitoraggio Feed Macro (S94a quality watch)

Periodo: 2026-06-01 → 2026-06-08 (T+7 dalla correzione BBC→CNBC+MarketWatch)
Obiettivo: verificare stabilità feed macro dopo S94a. La quality review dell'8 giugno
sblocca la decisione "timing Sentinel Phase B vs accelerare NewsKeeper".

Controlli giornalieri (query Supabase, ultime 24h):
- HEARTBEAT: ultimo segnale < 2h fa? (bot scrive ogni 15 min)
- FALLBACK: righe con classifier_version='regex_fallback' = ANOMALIA (Haiku failing)
- FEED MACRO: cnbc_economy e marketwatch presenti tra i feed_source?

---

- 2026-06-03: OK | tot 105 segnali/24h | feed: cnbc_economy=23 marketwatch=3 coindesk=29 cointelegraph=24 decrypt=26 | classifier: haiku_s2=105 regex_fallback=0 | ultimo segnale: 05:57 UTC
- 2026-06-04: OK | tot 111 segnali/24h | feed: cnbc_economy=20 marketwatch=5 coindesk=28 cointelegraph=32 decrypt=26 | classifier: haiku_s2=111 regex_fallback=0 | ultimo segnale: 06:03 UTC
- 2026-06-05: OK | tot 126 segnali/24h | feed: cnbc_economy=23 marketwatch=6 coindesk=36 cointelegraph=31 decrypt=30 | classifier: haiku_s2=126 regex_fallback=0 | ultimo segnale: 05:08 UTC
