# Drafts

Cartella delle bozze in revisione prima di essere applicate ai file di
produzione (sito, diary, brief). Esiste per separare il **work in
progress** dal codice/contenuto live.

## A cosa serve

Quando l'auditor esterno, il CEO Claude.ai, Claude Code o Max stesso
producono testi/modifiche significative che richiedono revisione prima
del deploy (pagine del sito, blocchi diary, brief lunghi), il draft
vive qui finché non viene approvato.

Tipico ciclo di vita di un draft:

1. **Created** — qualcuno genera il file qui, naming convention sotto
2. **Review** — Max (e/o CEO) lo leggono, eventualmente lo modificano
3. **Applied** — il contenuto viene spostato/copiato nella posizione
   di produzione (es. `web_astro/src/pages/howwework.astro`, una
   diary entry su Supabase, un brief in `config/`)
4. **Archived or deleted** — quando applicato, il draft può essere
   cancellato oppure spostato a `drafts/applied/` per audit trail

## Cosa NON va qui

- Bozze brevi che possono vivere in chat (non vale la pena committarle)
- Documenti di stato vivi (PROJECT_STATE.md, BUSINESS_STATE.md) — quelli
  sono *current*, non draft
- Brief operativi per CC — quelli vivono in `config/brief_*.md`
- Report al CEO — quelli vivono in `report_for_CEO/`
- Audit report — quelli vivono in `audits/` (gitignored)

## Naming convention

```
YYYY-MM-DD_topic_short-description.md
```

Esempi:
- `2026-05-07_howwework_v3.md`
- `2026-05-07_diary_vol3_state_files.md`
- `2026-06-15_blueprint_phase2_update.md`

## Stato attuale (snapshot)

Vedi i file presenti in questa cartella. Quando un draft è applicato,
considera se cancellarlo o spostarlo in `drafts/applied/YYYY-MM/`.

## Convenzione lingua

- File di bozza in **italiano** (di lavoro) se servono solo a Max/CEO
  per la revisione
- Bozza di contenuto destinato a essere pubblicato in **inglese**
  (sito, diary, post X) se contiene direttamente il testo finale
- Mai mescolare le due lingue dentro lo stesso documento se non
  giustificato (es. "ecco la traduzione di...")

## Owner

Max è il proprietario operativo (decide cosa applicare e quando).
I file possono essere creati da qualsiasi entità (CEO, CC, auditor)
ma l'approvazione finale è sempre umana.
