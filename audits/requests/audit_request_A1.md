# Audit Request — Area 1 (Integrità Tecnica) — TEMPLATE EVERGREEN

> Questo è il **template fisso** dell'audit Area 1, valido sempre. L'Auditor lo
> riceve come brief. Cadenza: **mensile (~30 giorni)**, backstop 30gg. Per un
> audit specifico, Max può duplicarlo in `audits/requests/YYYYMMDD_audit[A1].md`
> e aggiungere note; altrimenti questo file è sufficiente così com'è.
>
> **Owner del processo:** Max. **Esecutore:** una sessione CC FRESH (vedi
> `AUDIT_PROTOCOL.md §3`: nessuno sviluppo prima nella stessa chat; l'Auditor
> non shippa codice, solo diagnostica e raccomanda).
>
> ⚙️ **Nota operativa**: in produzione questo audit gira **automatizzato** via
> Claude Code Cowork scheduled sul Mac Mini — la versione operativa completa (cron,
> notifiche Gmail `[AREA-01]` + iMessage, comandi git) vive in
> `audits/requests/scheduled_task_audit_area1_prompt.md`. Questo file è il
> **gemello leggibile/archivio**, allineato al formato degli altri audit_request.

---

## 0. Cosa fa questo audit

Verifica l'**integrità tecnica** del sistema: bot + agenti (Grid / TF / Sentinel /
Sherpa / NewsKeeper) + database. Risponde a: *i numeri tornano? le interazioni tra
i cervelli sono coerenti? lo schema DB regge rispetto a ciò che il codice si
aspetta? i bot stanno scrivendo stato e non sono fermi?* Non propone strategia
(quello è Area 3): fotografa la salute tecnica e flagga ciò che è rotto o a rischio.

---

## 1. Raccolta dati / procedura (FAI QUESTO PRIMA DI GIUDICARE)

### Step 1 — Contesto
Leggi: `PROJECT_STATE.md`, `BUSINESS_STATE.md` (stato corrente), `AUDIT_PROTOCOL.md`
(protocollo completo), `config/validation_and_control_system.md` (checklist dei
controlli automatici attesi).

### Step 2 — Test suite
- Installa le dipendenze (ambiente Cowork sandbox): `pip install -r requirements.txt --break-system-packages`.
- Esegui `python -m pytest` → riporta pass/fail + ogni failure.
- Se i test non partono (dipendenza mancante, import rotto) → finding **HIGH**.

### Step 3 — Schema DB vs codice
- Via connettore Supabase (project ID `pxdhtmqfwjwjhtcoacsn`), interroga
  `information_schema.columns` per: `bot_config, trend_config, trades,
  daily_commentary, newskeeper_signals, sentinel_scores, sherpa_proposals,
  bot_events_log, bot_state_snapshots, daily_pnl, reserve_ledger`.
- Confronta le colonne reali con ciò che il codice Python si aspetta (chiamate al
  client Supabase nella dir `bot/`). Ogni mismatch → finding **HIGH**.

### Step 4 — Salute bot (via DB)
- `bot_events_log` (ultime 48h): eventi a livello ERROR.
- `bot_state_snapshots` (DISTINCT ON symbol, ultimo per coin): tutti i bot attesi scrivono stato?
- `newskeeper_signals` / `sentinel_scores` / `sherpa_proposals` (ultime 48h): ogni cervello scrive?
- Se un cervello non scrive da >24h → finding **HIGH**.

### Step 5 — Scan pattern di codice
- API key / segreti hardcoded fuori dai file `.env`.
- `print()` che dovrebbero essere chiamate `logger.`.
- Commenti TODO / FIXME / HACK (elencali).
- Import che non risolvono (rotti).
- `db_maintenance.py`: la retention policy combacia con quanto documentato in BUSINESS_STATE?

---

## 2. Domande guida

1. **I numeri tornano?** P&L, holdings, fee, reserve ledger: coerenti tra DB, codice e (dove verificabile) broker.
2. **I cervelli sono vivi e coerenti?** Ognuno scrive nei tempi attesi; le interazioni (es. Sherpa→Grid, Sentinel→TF) non si contraddicono.
3. **Lo schema regge?** Nessun mismatch colonna DB ↔ aspettativa del codice; nessuna migration mancante.
4. **Regressioni?** I test passano; nessun import rotto; nessun errore ERROR ricorrente negli ultimi 2 giorni.
5. **Debito/igiene:** segreti fuori posto, log improvvisati, TODO accumulati, retention divergente.

---

## 3. Confronto con l'audit precedente

Leggi l'ultimo `audits/reports/*audit[A1]*.md` e verifica: i finding precedenti
sono stati chiusi o sono ancora aperti? Sono comparsi nuovi problemi? Il valore
sta nel **movimento** (regressioni nuove vs debito che si trascina).

---

## 4. Struttura del report (output atteso)

File: `audits/reports/YYYYMMDD_audit[A1].md` (data SENZA trattini). Sezioni:

- **Scope** — cosa è stato auditato (codebase + DB + bot health + pattern).
- **Methodology** — gli step eseguiti (e quali saltati, con motivo — vedi Fallback).
- **Findings** — raggruppati per severity `CRITICAL > HIGH > MED > LOW`, ciascuno con `file:linea` dove applicabile e descrizione dell'impatto.
- **Verdetto** — `APPROVED` / `CON RISERVE` / `REJECTED`.
- **Recommendations** — fix proposti (NON eseguiti), prioritizzati; nota se un finding HIGH tocca documentazione/state files (→ trigger audit Area 2, vedi `AUDIT_PROTOCOL.md §2d`).
- **Riga di sintesi per PROJECT_STATE §9** (data, area, topic, verdetto, conta findings, report path).

Nota nel report che è stato prodotto da un Auditor (e, se automatico, da un Cowork scheduled task).

---

## 5. Regole

- **L'Auditor NON shippa**: niente fix, niente edit ai brief, niente migration, niente restart bot. Solo report + riga §9 (vedi `AUDIT_PROTOCOL.md §3` e §5).
- **Findings tracciabili**: severity + `file:linea` sempre, dove applicabile. Un finding senza posizione è un'opinione, non un finding.
- **Fallback** (non bloccarti): se Supabase non è accessibile → salta Step 3-4 e annotalo nel report; se i test non partono → finding HIGH; nessun accesso a uno strumento → annota il limite, non improvvisare.
- **Cadenza sui FILE, non su §9**: la conta dei 30 giorni si fa sui file `audits/reports/*audit[A1]*.md`, non sulle righe di PROJECT_STATE §9 (vedi `CLAUDE.md §[1]` regola anti-drift).
- **Aggiornamenti post-report**: PROJECT_STATE §9 + storico `AUDIT_PROTOCOL.md §7`. Solo l'Auditor scrive in §9.
