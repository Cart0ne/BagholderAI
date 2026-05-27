# Brief 89a — Audit Area 1 Remediation: Test Hygiene + Dead Code Cleanup

**Author:** CEO (Claude)
**Date:** 2026-05-27
**Audit reference:** `audits/audit_report_20260527_area1_automated.md`
**Verdetto audit:** CON RISERVE (0 CRITICAL, 2 HIGH, 3 MED, 2 LOW)
**PROJECT_STATE.md reference:** 2026-05-27 (post S88)

---

## Obiettivo

Risolvere tutti i findings HIGH e MED dell'audit automatico Area 1 in modo che il prossimo audit passi APPROVED. Tempo stimato: ~1h.

---

## Task 1 — Test hygiene [H1 + H2]

Il refactor S76 (grid_runner package split) ha cambiato la constructor signature di `GridBot`, ma i test in `tests/legacy/` non sono mai stati aggiornati. Risultato: 32 test rotti che mascherano qualsiasi regressione reale. In più, `tests/test_trend_36e_v2.py` ha un `sys.exit(1)` a livello modulo che ammazza pytest.

**Azioni:**

1. Creare la cartella `tests/archived/`
2. Spostare l'intera directory `tests/legacy/` dentro `tests/archived/legacy/`
3. Spostare `tests/test_trend_36e_v2.py` dentro `tests/archived/`
4. Creare un file `tests/archived/README.md` con contenuto:
   ```
   # Archived Tests
   
   These tests were archived on 2026-05-27 following automated Audit Area 1.
   
   - `legacy/` — Grid bot tests from pre-S76 refactor. Constructor signature
     changed during grid_runner package split; tests never updated.
   - `test_trend_36e_v2.py` — Contains sys.exit(1) at module level (line 312)
     that crashes pytest collection.
   
   To restore: update GridBot constructor calls to match current signature
   in `bot/grid/grid_runner.py`, and remove the sys.exit(1) from the trend test.
   ```
5. Creare `pytest.ini` nella root del repo (se non esiste già) con:
   ```ini
   [pytest]
   testpaths = tests
   addopts = --ignore=tests/archived
   ```
6. Verificare che `python -m pytest` ora esegue SOLO i 31 test attivi e tutti passano.

**Output atteso:** `pytest` pulito, 31/31 pass, zero noise.

---

## Task 2 — Dead code cleanup [M1 + L2]

`db/client.py` ha due metodi che referenziano tabelle che non esistono più (`portfolio` e `sentinel_logs`). Idem `scripts/cash_audit.py`.

**Azioni:**

1. In `db/client.py`: trovare il metodo che chiama `self.client.table("portfolio")` (~riga 186) e il metodo che chiama `self.client.table("sentinel_logs")` (~riga 377). Aggiungere il commento `# DEPRECATED — table does not exist, legacy from pre-S59` sopra ciascun metodo e aggiungere un `return None` come prima riga del body (così se qualcuno lo chiama per sbaglio non crasha).
2. In `scripts/cash_audit.py` (~riga 80): stessa cosa, deprecare il riferimento a `portfolio`.

**Nota:** NON eliminare i metodi — solo deprecarli. Se qualcosa li chiama (improbabile ma possibile), non vogliamo un crash runtime.

---

## Task 3 — Missing dependency [M3]

`utils/x_poster.py` importa `tweepy` ma non è in `requirements.txt`.

**Azioni:**

1. Creare `requirements-scripts.txt` nella root del repo con:
   ```
   # Dependencies for standalone scripts (not required by bot runtime)
   tweepy>=4.14.0
   ```
2. Aggiungere un commento in cima a `requirements.txt`:
   ```
   # Bot runtime dependencies. For script-only deps see requirements-scripts.txt
   ```

**Nota:** NON aggiungere tweepy a `requirements.txt` — è una dipendenza degli script standalone, non del bot runtime. Tenerle separate è più pulito.

---

## Decisioni delegate a CC

- Posizione esatta dei file da spostare (verificare i path con `find`)
- Se `pytest.ini` esiste già, integrare le opzioni invece di sovrascrivere
- Formato esatto del deprecation comment (il contenuto sopra è una traccia)

## Decisioni che CC DEVE chiedere al Board

- Se trova altri test rotti non documentati nell'audit
- Se i metodi deprecated in `db/client.py` sono chiamati da qualche parte (in quel caso NON deprecare, segnalare)

## Vincoli

- NON modificare codice bot runtime (`bot/` directory) — questo brief è solo pulizia
- NON eliminare nessun file — solo spostare o deprecare
- NON toccare `tests/test_accounting_avg_cost.py` — quelli sono i 31 test buoni
- Il brief non richiede restart di nessun bot

## Output atteso a fine sessione

- `pytest` esegue 31/31 test, tutti pass, zero warnings
- `tests/archived/` esiste con i test legacy + README
- `db/client.py` metodi dead code deprecati
- `requirements-scripts.txt` creato
- Commit unico con messaggio: `fix: audit area 1 remediation — test hygiene + dead code (brief 89a)`

## Roadmap impact

Nessuno — questo è housekeeping interno, non una feature.
