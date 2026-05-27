# Brief 88e — Brief Hygiene: Parked Directory + Inventory Cleanup

**Author:** CEO (Claude)
**Date:** 2026-05-27
**Baseline:** PROJECT_STATE.md aggiornato 2026-05-27 (S87 closure, commit `e1a6634`)
**Audit ref:** `audits/audit_report_20260527_area2_coherence.md` — findings 2.3, 2.4
**Estimated time:** ~30 min
**Priority:** LAST — execute after all other 88x briefs, or as add-on to another session if time permits

---

## Context

2 brief parcheggiati in `config/` da 26-36 giorni senza trigger di sblocco. Naming inconsistency in `briefresolved.md/` (cosmetico, basso ROI). Questi sono housekeeping puri — nessun impatto sul prodotto o sul pubblico.

---

## Task 1 — Organizzare brief parcheggiati (finding 2.3)

**Creare directory** `config/parked/` e spostare:
```
config/brief_DUST_writeoff_parcheggiato.md  →  config/parked/brief_DUST_writeoff_parcheggiato.md
config/brief_evaluate_trading_skills.md     →  config/parked/brief_evaluate_trading_skills.md
```

**Creare** `config/parked/README.md`:
```markdown
# Parked Briefs

Brief parcheggiati in attesa di trigger specifici. Non sono abbandonati — hanno criteri di riapertura.

| Brief | Parcheggiato da | Trigger di sblocco |
|---|---|---|
| brief_DUST_writeoff_parcheggiato.md | 2026-04-21 (S~55) | Da eseguire PRIMA del go-live mainnet €100 (serve per le fees/dust writeoff) |
| brief_evaluate_trading_skills.md | 2026-05-01 (S~59) | Post primo trimestre di TF LIVE Tier 1-2 con dati sufficienti (~90 giorni da S79b = ~metà agosto 2026) |

Last updated: 2026-05-27
```

**Citare in PROJECT_STATE §6** (domande aperte): aggiungere una riga tipo:
```
- 2 brief parcheggiati in `config/parked/` con trigger di sblocco — vedi README.
```

---

## Task 2 — Naming consistency briefresolved (finding 2.4)

**Scope limitato:** SOLO se c'è tempo residuo nella sessione. Se il tempo è finito, saltare.

Se eseguito: rinominare i file in `briefresolved.md/` per uniformare a pattern `brief_[session][lettera]_[topic].md` (tutto lowercase, underscore, niente spazi). Esempio:
- `Brief_46a_…` → `brief_46a_…`
- `BRIEF_tf_…` → `brief_tf_…`

**NON rinominare** file che non seguono il pattern ma hanno un motivo (es. `session87_business_state_update.md` — è un artifact CEO, non un brief CC).

---

## Decisioni delegate a CC

- Se rinominare i file in briefresolved (Task 2) — solo se c'è tempo
- Wording del README
- Eventuali altri brief parcheggiati trovati in config/ che non sono nei 2 listati (aggiungerli alla tabella)

## Decisioni che CC DEVE chiedere

- Nessuna — task completamente autonomo

## Output atteso

1. `config/parked/` directory creata con 2 brief + README.md
2. `config/` ripulita (i 2 brief non sono più nella root di config)
3. PROJECT_STATE.md aggiornato (§6 + §3 se serve)
4. (Opzionale) `briefresolved.md/` file rinominati
5. Commit, push origin/main

## Vincoli

- NON toccare codice bot, trading logic, tabelle Supabase
- NON toccare web_astro/
- NON modificare BUSINESS_STATE.md
- NON spostare o rinominare brief che sono referenziati direttamente in altri file (es. se PROJECT_STATE §10 cita `brief_s83_newskeeper_architecture.md`, quel nome non si tocca)

## Roadmap impact

Nessuno.
