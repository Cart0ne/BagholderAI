# Audit Area 2 — Remediation Briefs: Guida all'esecuzione

**Prodotti da:** CEO (Claude), sessione 2026-05-27
**Audit di riferimento:** `audits/audit_report_20260527_area2_coherence.md`
**Verdetto audit:** CON RISERVE (0 CRITICAL · 6 HIGH · 12 MED · 12 LOW)

---

## Ordine consigliato

| # | Brief | File | Stima | Dipendenze | Findings coperti |
|---|---|---|---|---|---|
| 1 | **88b** — Public Site Catch-Up | `brief_88b_public_site_catchup.md` | 2-3h | Nessuna | 1.1, 3.1, 3.2, 3.3, 4.1, 4.2, 4.3, 4.4 |
| 2 | **88c** — State Files Cleanup | `brief_88c_state_files_cleanup.md` | ~1h | Nessuna (ma se fatto dopo 88b, PROJECT_STATE è più pulito) | 5.1, 5.2, 5.3, 5.5, 5.7, 1.6 |
| 3 | **88d** — UI Debts | `brief_88d_ui_debts.md` | 1-2h | 88b deve essere fatto (dashboard.astro cambiato) | 1.2, 1.3, 1.4, 1.5 |
| 4 | **88a** — Audit Meta-Decisions | `brief_88a_audit_meta_decisions.md` | ~45min | Nessuna (ma logicamente va dopo i fix tecnici) | 6.1, 6.2, 2.1, 2.2 |
| 5 | **88e** — Brief Hygiene | `brief_88e_brief_hygiene.md` | ~30min | Nessuna | 2.3, 2.4 |

**Tempo totale stimato:** ~5-7 ore di CC distribuite su 3-5 sessioni.

---

## Note operative per Max

1. **Ogni brief è una sessione CC separata.** Non combinare 88b + 88c nella stessa sessione — sono troppo grandi insieme e il context si degrada.

2. **88b è il più urgente** perché il drift è visibile al pubblico. Se devi fare solo un brief questa settimana, fai quello.

3. **88d dipende da 88b** perché entrambi toccano `dashboard.astro`. Fare 88d prima di 88b creerebbe conflitti merge.

4. **88a e 88e possono essere eseguiti in qualsiasi ordine** e anche nella stessa sessione (sono brevi e non si sovrappongono).

5. **88c è autonomo** ma meglio dopo 88b — così la compaction di PROJECT_STATE riflette già il catch-up del sito.

6. **Findings NON coperti da brief** (per design):
   - 3.4 MED (blog post sicurezza mainnet) → parcheggiato in Blog Pipeline come idea futura
   - 3.5 LOW (blog calendario) → parcheggiato, opportunità non urgente
   - 4.5 LOW (site-match-deploy) → parcheggiato, basso ROI
   - 2.4 LOW (naming) → incluso in 88e come opzionale
   - 5.4 LOW (positive observation) → nessun fix necessario
   - 5.6 LOW (uncommitted tree) → risolto dall'auditor stesso
   - 6.3 MED (BUSINESS_STATE stale) → risolto dal CEO con aggiornamento BUSINESS_STATE a fine sessione audit
   - 6.4 LOW (positive observation) → nessun fix necessario
   - 6.5 LOW (git pull exception) → nessun fix necessario

7. **Dopo l'ultimo brief eseguito**, il CEO emetterà un aggiornamento BUSINESS_STATE con:
   - §5: Audit Area 2 → COMPLETATO + remediation in corso
   - §7: rimuovere "Audit Area 2 non eseguito"
   - Qualsiasi altra sezione impattata

---

## Tracking (Max compila a mano)

| Brief | Sessione CC | Data esecuzione | Commit | Note |
|---|---|---|---|---|
| 88b | | | | |
| 88c | | | | |
| 88d | | | | |
| 88a | | | | |
| 88e | | | | |
