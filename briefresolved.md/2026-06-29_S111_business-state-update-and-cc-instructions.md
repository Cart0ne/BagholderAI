# S111 — Aggiornamento BUSINESS_STATE.md + Istruzioni CC

Data: 2026-06-29 (S111)

---

## PARTE 1: Aggiornamento BUSINESS_STATE.md

Applica le seguenti modifiche alle sezioni indicate.

### Header — sostituire interamente

```
**Last updated:** 2026-06-29 — Session 111 (Fix A realized avg-cost drift shipped,
site polish 3/4, S110d/e chiusi, Board decisions 4.12/4.14 ratificate estemporanea
28-giu, session numbering corrected). Cap file 50KB (Max S95, CLAUDE.md §2b).
Cadenze audit canoniche in PROJECT_STATE §9. Prec.: 2026-06-28 (estemporanea) —
§4 Board ratification 4.12/4.14 + grid-regime-backtest (Caso 2) approvato.
**Updated by:** CEO (S111 via Max)
**Basato su:** report CC `2026-06-29_S111_RforCEO_site-polish-and-realized-fix.md`,
report CC `2026-06-28_S110d_RforCEO_tf-grid-exit-thresholds.md`, review CEO S111
```

NOTA: il report CC porta il nome "S112" nel filename — il numero corretto è S111.
Vedi Parte 2 per le istruzioni di rinomina.

### §2 Marketing In-Flight — aggiungere sotto l'ultimo blocco

```
### S111 — site polish (SHIPPED, web-only, no restart)
- **Footer**: 4 link testuali social → bottoni tondi SVG (Telegram, X, GitHub, Buy me a coffee)
- **Homepage P&L per-fund**: sotto il Total P&L ora compare `Grid +$X / TF −$Y`, stessa formula canonica dell'admin
- **News linkabili**: titoli NewsKeeper su `/dashboard` ora sono `<a href>` verso la fonte originale. URL in `raw_data->>'link'` (JSONB), NON in colonna `link` dedicata
- **Fix A — Net Realized onesto**: `pnl-canonical.ts` E `pnl-canonical.js` ora derivano il realized dall'avg-cost replay (`revenue − avg × qty`), non dal campo DB `realized_pnl`. Net Realized pubblico: +$30.64 → +$22.43. Total P&L invariato. Identità contabile ora rispettata (~$0.07 float)
- **Non fatto**: #3 Strategia canale Telegram (territorio CEO/marketing, non codice)
```

### §3 Diary — aggiornare

Sostituire la riga "Sessioni pendenti di diary" con:

```
**Sessioni pendenti di diary:** S73/S74/S77/S78/S79 da verificare docx (V3, bassa priorità).
S111 diary scritto e inserito in Supabase (2026-06-29).
```

### §4 Decisioni Strategiche Recenti — aggiungere IN CIMA alla tabella

```
| 2026-06-29 (S111) | **Fix A shipped: Net Realized da avg-cost replay** | `realized_pnl` stored è fossile (drift ~$8 da reset avg su polvere). Pubblico ora onesto. Fix B (bot) wontfix per ora — Fix A copre il rischio reputazionale. Fix A2 (Today P&L) parcheggiato |
| 2026-06-29 (S111) | **Numbering corrected: estemporanea 28/06 non numerata** | CC contava estemporanea come S111, lavoro 29/06 come S112. Corretto: oggi = S111. Repo cleanup in corso |
```

### §5 Domande Aperte per CC — aggiornare stato

La riga "[S83] NewsKeeper S2" è già ✅ DONE.

### §7 Cosa NON sta succedendo — aggiornare

Sostituire la riga "NewsKeeper v1":
```
| **NewsKeeper v1** | ✅ SPENTO (S110e, 27 giugno). Righe v1 archiviate e cancellate. Runbook corretto |
```

Sostituire la riga "TF-Scout (Tier 3 shitcoins)":
```
| **TF-Scout (Tier 3 shitcoins)** | Post-mainnet. TF clone in paper/testnet (CASO 2). trend_scans retention estesa a 90gg (S110e) |
```

---

## PARTE 2: Istruzioni CC — Fix numerazione S112 → S111

### Contesto
CC ha numerato l'estemporanea del 28/06 come S111 e il lavoro del 29/06 come S112.
Il Board ha stabilito: l'estemporanea non è una sessione numerata. Il 29/06 è S111.

### Task

1. **Rinomina file nel repo** che contengono "S112" nel nome:
   - `2026-06-29_S112_RforCEO_site-polish-and-realized-fix.md` → `2026-06-29_S111_RforCEO_site-polish-and-realized-fix.md`
   - Qualsiasi altro file con S112 nel nome o percorso

2. **Cerca e sostituisci dentro i file** — in tutti i file .md nella cartella config/, briefresolved.md/, report_for_CEO/:
   - "S112" → "S111" (quando si riferisce alla sessione del 29/06)
   - "Session 112" → "Session 111"
   - Attenzione: se PROJECT_STATE §10 menziona "S111" come estemporanea, quella riga va corretta:
     l'estemporanea 28/06 è parte di S110 (esecuzione brief S110d), NON una sessione autonoma

3. **PROJECT_STATE §10 (Session history)** — aggiungere la riga per S111:
   ```
   | 2026-06-29 | web | **S111** site polish (footer, P&L per-fund, news links) + Fix A realized avg-cost drift + diary | SHIPPED 7 commit web-only, no restart | Fix A: Net Realized derivato da replay avg-cost, non da campo DB. Estemporanea 28/06 (S110d SHIPPED + Board 4.12/4.14) coperta in diary S111 |
   ```
   Se esiste una riga che riferisce all'estemporanea come "S111", rimuoverla o riformularla come:
   ```
   | 2026-06-28 | 1 | **S110 (estemporanea)** S110d tf-grid-exit-thresholds eseguito + Board decisions 4.12/4.14 | SHIPPED `4b9a3ed` + migration, restart pending | Deviazione dal brief: trailing stop sostituisce signal exit. Coperto in diary S111 |
   ```

4. **BUSINESS_STATE.md** — applica le modifiche della Parte 1 sopra

5. **Verifica**: `grep -rn "S112" config/ report_for_CEO/ briefresolved.md/ BUSINESS_STATE.md PROJECT_STATE.md` deve restituire zero risultati (esclusi eventuali archivi storici)

6. **Commit**: messaggio `S111: fix session numbering drift S112→S111 + BUSINESS_STATE update`

### Vincolo
- Zero codice bot toccato
- Zero restart
- Solo file .md e stato

### Anti-assenso
Obiezione onesta: il rischio di questa rinomina è minimo, ma se CC ha generato
riferimenti incrociati tra file (es. un brief che cita "vedi report S112"), la
sostituzione cieca potrebbe spezzare un link semantico. CC deve verificare ogni
occorrenza nel contesto prima di sostituire.
