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
- **Area 3 — Strategia e marketing**: posizionamento, SEO/GSC, performance social (X, Dev.to, Reddit), funnel, distribuzione.

---

## 2. Trigger (event-based — approvato Board 2026-05-27)

L'audit **Area 2** è obbligatorio PRIMA di:
  (a) ogni go-live mainnet;
  (b) ogni lancio di un nuovo Volume del Diary su Payhip;
  (c) ogni introduzione di un nuovo brain o macro-feature;
  (d) se un audit Area 1 o Area 3 trova ≥1 finding HIGH che tocca documentazione/state files.
**Backstop temporale:** 120 giorni se nessun trigger sopra è scattato.

- **Area 1**: dopo ogni feature significativa, oppure mensile. Backstop 30gg.
- **Area 3**: trimestrale + pre-lancio prodotto. Backstop 90gg.

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

1. Il **CEO** crea `audits/audit_request_YYYYMMDD_topic.md` (cartella gitignored, resta locale).
2. **Max** apre una sessione CC FRESH e le passa il file come brief.
3. **CC** crea `audits/audit_in_flight_YYYYMMDD_topic.md` — stage intermedio con ETA e scope confermato (segnala che un audit è in corso, evita doppioni).
4. **CC** esegue e produce `audits/audit_report_YYYYMMDD_topic.md`.
5. **L'Auditor** aggiorna `PROJECT_STATE.md §9` con la sintesi (è l'unico autorizzato — vedi §5).
6. **CC** cancella `audits/audit_in_flight_*.md` (stage chiuso).

> La conta della cadenza/trigger si fa sui FILE `audits/audit_report_*.md`, NON
> sulle righe §9 di PROJECT_STATE. Una riga §9 esiste se e solo se esiste il
> report corrispondente prodotto da un Auditor.

---

## 5. Output dell'Auditor

- **Findings** con severity (CRITICAL > HIGH > MED > LOW) e `file:linea`.
- **Verdetto**: APPROVED / CON RISERVE / REJECTED.
- File `audits/audit_report_YYYYMMDD_topic.md`.
- **Riga §9** in PROJECT_STATE.md (unico caso in cui CC scrive in §9). Una
  sessione di sviluppo che ha shippato codice scrive in §10 "Sessioni shipped",
  MAI in §9.

---

## 6. Alert in chiusura sessione CC

Quando un trigger di §2 è scattato, CC lo propone in chiusura sessione:

> "⚠️ Audit Area X dovuto (motivo: trigger Y). Brief draft disponibile.
> Vuoi che lo generi ora? [yes / no / later]"

Se Max dice **yes** → CC genera `audits/audit_request_YYYYMMDD_topic.md` nella
stessa sessione (è un artefatto-richiesta, non l'esecuzione dell'audit: quella
resta a una sessione fresh separata, vedi §3).

---

## 7. Storico audit

| Data | Area | Topic | Verdetto | Report |
|---|---|---|---|---|
| 2026-05-07 | 1 | Phase 1 split `grid_bot.py` monolite → 6 moduli (brief 62a) | **APPROVED** (zero regressioni) | `audits/audit_report_20260507_phase1_grid_split_review.md` |
| 2026-05-15 | 3 | Marketing + SEO/GSC + X performance pre-go-live (A3-S78) | **CON RISERVE** | `audits/audit_report_20260515_marketing_seo_x.md` |
| 2026-05-27 | 2 | Coerenza narrazione pubblica ↔ codice LIVE ↔ state files (A2-S87, primo audit Area 2 mai eseguito) | **CON RISERVE** (0 CRITICAL, 6 HIGH, 12 MED) | `audits/audit_report_20260527_area2_coherence.md` |

---

*Last updated: 2026-05-27 (S88, brief 88a) — riscrittura completa post audit Area 2: da audit-request fossile a protocollo vero, trigger Area 2 event-based, stage `audit_in_flight`.*
