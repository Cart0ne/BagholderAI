# Aggiornamento BUSINESS_STATE.md — Sessione S98 (2026-06-06)

Aggiornare SOLO le sezioni sotto. Il resto resta invariato.

---

## §3 Diary Status — SOSTITUIRE il paragrafo "Sessione corrente"

**Sessione corrente: 98 BUILDING** (adaptive sell penalty v1→v2 + tbot competitive analysis + blog pipeline update). S97 → COMPLETE.

**Blog post pubblicati: 8** (ultimo: Post 8 "Thirty-Two Hours", 5 giugno 2026)
**Post SEO+GEO in coda: 4** (POST 2–5, cadenza 1 ogni 1-2 settimane)

---

## §4 Decisioni Strategiche Recenti — AGGIUNGERE in testa alla tabella

| Data | Decisione | Perché |
|---|---|---|
| 2026-06-06 (S98) | **Adaptive Sell Penalty SHIPPED** (brief S98a, commit `507ebd6` + `a7d644d`) — guardia post-fill: se un sell Strategy A filla sotto avg_cost, il bot alza sell_pct dell'ultimo slippage osservato; sell profittevole resetta a base | Incidente BONK: 7 sell in 6 min, tutti in perdita per slippage testnet (ticker ok, fill −4/−14%). Strategy A checkava pre-fill, non post-fill. Guardia proporzionale, adattiva, auto-guarigione |
| 2026-06-06 (S98) | **Board override: penalty da cumulativa a ultima perdita** | Design v1 (CEO) sommava tutte le perdite → BONK congelato a 31.3%. Max ha identificato il freeze: le 7 perdite non sarebbero mai accadute con la guardia attiva, il cumulativo bootstrappava da storia non guardata. Design v2 (Board): penalty = ultimo slippage osservato. Più semplice, auto-guaribile, nessun deadlock |
| 2026-06-06 (S98) | **tbot competitive analysis completata** (report S93b, read-only). Conferma moat: accounting onesto + multi-brain + news classificata. Tre mosse proposte: /news pubblica PARKED (serve Haiku classifier), tabella regime PARKED (serve più dati), blog accounting trap IN PIPELINE | L'analisi conferma: il competitor ha architettura più stretta (solo trend-follower), numeri rotti (nostro bug S96b), stesso slippage BONK al quadrato (−52% su microcap). Nessun contatto, nessuna modifica al sito |

---

## §5 Bug noti — AGGIUNGERE in "Risolti recenti"

- **S98a**: Adaptive Sell Penalty — guardia post-fill per Strategy A. Design v2 (ultima perdita, non cumulativa). Commit `507ebd6`+`a7d644d`. BONK soglia effettiva 6.46%. Primo sell profittevole → reset a base. Suite 157/157.

---

## §7 Cosa NON sta succedendo — AGGIUNGERE/AGGIORNARE

- **Pagina /news pubblica**: parked fino a post-sprint Haiku classifier (falsi positivi regex 60% non espongibili). Fonte: analisi tbot S98.
- **Tabella performance per regime su dashboard**: parked fino a profondità dati sufficiente (testnet_2 ha 2 giorni). Fonte: analisi tbot S98.
