# Audit Protocol — BagHolderAI

Protocollo unico per gli audit esterni del progetto. Consolida ciò che prima
viveva sparso tra `CLAUDE.md §[1]`, `WORKFLOW.md §G` e la prassi dei tre audit
già eseguiti. Questo file è la fonte autoritativa; CLAUDE.md e WORKFLOW.md vi
rimandano.

> Nota storica: fino al 2026-05-27 questo file conteneva per errore un vecchio
> audit *request* del 2026-05-07 ("V1 Calibration"), non un protocollo —
> nonostante CLAUDE.md/WORKFLOW.md lo citassero come tale (finding 6.1 audit
> Area 2). Riscritto in S88 (brief 88a).

---

## 1. Aree di audit

- **Area 1 — Integrità tecnica**: bot, agenti (Grid/TF/Sentinel/Sherpa/NewsKeeper), DB. I numeri tornano, le interazioni tra cervelli sono coerenti, lo schema regge.
- **Area 2 — Coerenza progetto**: narrazione pubblica (sito, roadmap, blog) ↔ codice LIVE ↔ state files (PROJECT_STATE/BUSINESS_STATE/brief). Il sito racconta la verità di cosa gira.
- **Area 3 — Strategia e marketing**: posizionamento, SEO (Google + Bing), performance social (X, Dev.to, Reddit), traffico sito + funnel di conversione (Umami), vendite (Payhip), coerenza cross-piattaforma, distribuzione. I dati si raccolgono via API con `python3.13 -m scripts.marketing_data_refresh` → `marketing_data/` (NON login manuale). Output = diagnosi **+ strategia** (target breve/medio/lungo). Template fisso: `audits/requests/audit_request_A3.md`.

---

## 2. Trigger (event-based — approvato Board 2026-05-27)

L'audit **Area 2** è obbligatorio PRIMA di:
  (a) ogni go-live mainnet;
  (b) ogni lancio di un nuovo Volume del Diary su Payhip;
  (c) ogni introduzione di un nuovo brain o macro-feature;
  (d) se un audit Area 1 o Area 3 trova ≥1 finding HIGH che tocca documentazione/state files.
**Backstop temporale:** 60 giorni se nessun trigger sopra è scattato.

- **Area 1**: dopo ogni feature significativa, oppure mensile. Backstop 30gg.
- **Area 3**: **ogni 2 settimane** (cadenza fissa) + pre-lancio prodotto. Backstop 14gg. La cadenza è frequente perché il marketing è ad alta varianza e l'audit a 2 strati (cruscotto + strategia) resta leggero da ripetere; vedi `audits/requests/audit_request_A3.md`.

Razionale del passaggio da temporale a event-based (Area 2): la regola "ogni
90gg o fine-volume" non è mai stata applicata in pratica (6 settimane di inerzia
+ primo audit Area 2 mai eseguito fino al 2026-05-27). Legarla a eventi
concreti — soldi veri, prodotto nuovo, cervello nuovo — la rende auto-innescante
invece che affidata a un conteggio di giorni che nessuno guarda.

---

## 3. Chi può essere Auditor

Una sessione **CC FRESH**: nessun task di sviluppo prima nella stessa chat. Se
la sessione è contaminata da shipping precedente (commit + restart bot +
migration), NON è un Auditor — è una sessione di sviluppo, e il suo report va
in `report_for_CEO/`, non come audit.

L'Auditor **NON shipa codice, NON tocca brief in corso, NON esegue il lavoro
che sta auditando**. Se identifica fix necessari, li flagga nel report; il fix
lo fa una sessione CC successiva, normale, con brief dedicato. Questo rimuove
il conflitto di interessi strutturale per cui chi esegue il task si
auto-certifica come Auditor.

---

## 4. Procedura

1. Il **CEO** crea `audits/requests/YYYYMMDD_audit[AX].md` (oppure usa il template evergreen `audits/requests/audit_request[AX].md`). Cartella gitignored, resta locale.
2. **Max** apre una sessione CC FRESH e le passa il file come brief.
3. **CC** esegue e produce `audits/reports/YYYYMMDD_audit[AX].md` (topic opzionale per audit one-off: `YYYYMMDD_audit[AX]_topic.md`).
4. **L'Auditor** aggiorna `PROJECT_STATE.md §9` con la sintesi (è l'unico autorizzato — vedi §5).

> La conta della cadenza/trigger si fa sui FILE `audits/reports/YYYYMMDD_audit[AX].md`, NON
> sulle righe §9 di PROJECT_STATE. Una riga §9 esiste se e solo se esiste il
> report corrispondente prodotto da un Auditor.

---

## 5. Output dell'Auditor

- **Findings** con severity (CRITICAL > HIGH > MED > LOW) e `file:linea`.
- **Verdetto**: APPROVED / CON RISERVE / REJECTED.
- File in `audits/reports/` con naming `YYYYMMDD_audit[AX].md` (X = 1, 2 o 3). Per audit one-off su scope specifico: `YYYYMMDD_audit[AX]_topic.md`.
- **Riga §9** in PROJECT_STATE.md (unico caso in cui CC scrive in §9). Una
  sessione di sviluppo che ha shippato codice scrive in §10 "Sessioni shipped",
  MAI in §9.

---

## 6. Alert in chiusura sessione CC

Quando un trigger di §2 è scattato, CC lo propone in chiusura sessione:

> "⚠️ Audit Area X dovuto (motivo: trigger Y). Brief draft disponibile.
> Vuoi che lo generi ora? [yes / no / later]"

Se Max dice **yes** → CC genera `audits/requests/YYYYMMDD_audit[AX].md` nella
stessa sessione (è un artefatto-richiesta, non l'esecuzione dell'audit: quella
resta a una sessione fresh separata, vedi §3).

---

## 7. Storico audit

| Data | Area | Topic | Verdetto | Report |
|---|---|---|---|---|
| 2026-05-07 | 1 | Phase 1 split `grid_bot.py` monolite → 6 moduli (brief 62a) | **APPROVED** (zero regressioni) | `audits/reports/20260507_audit[A1]_phase1_grid_split_review.md` |
| 2026-05-15 | 3 | Marketing + SEO/GSC + X performance pre-go-live (A3-S78) | **CON RISERVE** | `audits/reports/20260515_audit[A3].md` |
| 2026-05-27 | 2 | Coerenza narrazione pubblica ↔ codice LIVE ↔ state files (A2-S87, primo audit Area 2 mai eseguito) | **CON RISERVE** (0 CRITICAL, 6 HIGH, 12 MED) | `audits/reports/20260527_audit[A2].md` |
| 2026-05-27 | 1 | Monthly automated technical integrity (codebase + DB + bot health + code patterns) | **CON RISERVE** (0 CRITICAL, 2 HIGH, 3 MED) | `audits/reports/20260527_audit[A1].md` |
| 2026-05-31 | 3 | Cruscotto bisettimanale tutti i canali (X/Dev.to/Umami+funnel/GSC/Bing/blog/Payhip/Reddit) — Cowork scheduled automatico; refresh 5/5 OK dalla sandbox | **CON RISERVE** (0 CRITICAL, 3 HIGH, 4 MED, 2 LOW) | `audits/reports/20260531_audit[A3].md` |

---

---

## 8. Accoppiamento artefatti (cross-analisi)

L'Auditor NON vede le conversazioni: lavora SOLO sugli artefatti (brief,
report, diary, state file). La sua cross-analisi vale quanto e' accoppiabile
la catena.

CHIAVE DI ACCOPPIAMENTO: sessione (SXX) + SCOPE.
  brief:  YYYY-MM-DD_SXX[z]_brief_SCOPE.md     (scritto dal CEO)
  report: YYYY-MM-DD_SXX[z]_RforCEO_SCOPE.md   (scritto da CC, SCOPE ereditato)
Stesso SXX + stesso SCOPE = brief e report sono la stessa unita' di lavoro.

MANDATO: trova le incoerenze tra
  (a) cio' che il brief ha DECISO,
  (b) cio' che il report dice sia stato IMPLEMENTATO,
  (c) cio' che lo stato reale (codice / DB / sito live) mostra DAVVERO.
Un report senza brief accoppiabile, o un brief senza report, e' esso stesso
un finding.

GRANDFATHER — pre-S88
Gli audit Area 1 e Area 2 del 2026-05-27 (S87) hanno certificato la coerenza
fino a S87. La convenzione di naming vale da S88 in poi. I file pre-S88 hanno
naming storico disordinato: accoppiamento best-effort, e il disordine di
naming pre-S88 NON e' un finding (accettato consapevolmente, non rilevarlo
di nuovo — chiude il finding 2.4 dell'audit del 27/05).

NOTA FORMATO DATA: i file audit (reports/ e requests/) usano la data SENZA trattini
(`YYYYMMDD_audit[AX].md`); brief e report CEO usano la data CON trattini (`YYYY-MM-DD`).
L'Auditor gestisce entrambi i formati.

---

*Last updated: 2026-06-01 (S96) — Area 2 backstop 120→60 giorni; Area 3 cadenza bisettimanale→mensile.*
