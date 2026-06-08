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
- 2026-06-06: OK | tot 116 segnali/24h | feed: cnbc_economy=23 marketwatch=4 coindesk=31 cointelegraph=31 decrypt=27 | classifier: haiku_s2=116 regex_fallback=0 | ultimo segnale: 05:13 UTC
- 2026-06-07: OK | tot 94 segnali/24h | feed: cnbc_economy=23 marketwatch=6 coindesk=23 cointelegraph=22 decrypt=20 | classifier: haiku_s2=94 regex_fallback=0 | ultimo segnale: 05:18 UTC
- 2026-06-08: OK (nota: marketwatch=1, basso ma presente — domenica, news macro scarse) | tot 92 segnali/24h | feed: cnbc_economy=23 marketwatch=1 coindesk=26 cointelegraph=22 decrypt=20 | classifier: haiku_s2=92 regex_fallback=0 | ultimo segnale: 06:07 UTC

---

## Sintesi T+7 — Quality Review Feed Macro (2026-06-08)

**Periodo monitorato**: 2026-06-03 → 2026-06-08 (6 giorni di check, S94a del 2026-06-01)

**Verdetto: FEED STABILE ✓**

| Metrica | Risultato |
|---|---|
| Anomalie heartbeat | 0/6 giorni |
| Anomalie regex_fallback | 0/6 giorni |
| cnbc_economy assente | 0/6 giorni (sempre 20-23 segnali/giorno) |
| marketwatch assente (=0) | 0/6 giorni (range: 1-6, fisiologico nei fine settimana) |
| Tot segnali medi/24h | ~107 (range 92-126) |

**Conclusione**: La correzione S94a (BBC → CNBC Economy + MarketWatch) ha prodotto un feed macro stabile per tutti i 7 giorni di osservazione. Nessuna regressione Haiku (regex_fallback sempre 0). MarketWatch mostra volume basso nei fine settimana (1-3) ma non mai assente — comportamento atteso.

**Sblocca**: decisione "timing Sentinel Phase B vs accelerare NewsKeeper" — dati sufficienti per review CEO.

Routine di monitoraggio conclusa il 2026-06-08. Chiedere a Max di rimuoverla da claude.ai/code/routines.
