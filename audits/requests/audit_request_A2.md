# Audit Request — Area 2 (Coerenza Progetto) — TEMPLATE EVERGREEN

> Questo è il **template fisso** dell'audit Area 2, valido sempre. L'Auditor lo
> riceve come brief. Cadenza: **event-based** (pre-mainnet / pre-nuovo Volume del
> Diary / pre-nuovo brain o macro-feature / finding HIGH di A1-A3 che tocca
> documentazione), backstop **60gg** (vedi `AUDIT_PROTOCOL.md §2`). Per un audit
> specifico, Max può duplicarlo in `audits/requests/YYYYMMDD_audit[A2].md` e
> aggiungere note; altrimenti questo file è sufficiente così com'è.
>
> **Owner del processo:** Max. **Esecutore:** una sessione CC FRESH (vedi
> `AUDIT_PROTOCOL.md §3`: nessuno sviluppo prima nella stessa chat; l'Auditor
> non shippa codice, solo diagnostica e raccomanda).
>
> ⚙️ **Nota operativa**: in produzione questo audit gira **automatizzato** via
> Claude Code Cowork scheduled (backstop venerdì + un task gemello *manuale* per
> i pre-lancio). La versione operativa completa (cron, skip-guard, clone,
> notifiche Gmail `[AREA-02]`, comandi git) vive nel backup
> `bagholderai-audits/tasks/audit_area2_consistency.md` (disco condiviso Archivio,
> gitignored). Questo file è il **gemello leggibile/archivio** per il path manuale,
> allineato al formato degli altri audit_request.

---

## 0. Cosa fa questo audit

Verifica la **coerenza del progetto**: la narrazione pubblica (sito, roadmap,
blog, diary, library) ↔ il codice e il DB LIVE ↔ i file di stato (PROJECT_STATE /
BUSINESS_STATE / brief). Risponde a una sola domanda: *il sito (e tutto ciò che è
pubblico) racconta la verità di cosa gira davvero?* Non giudica la salute tecnica
(quello è Area 1) né la strategia di marketing (Area 3): caccia i **drift** tra
ciò che diciamo e ciò che è.

---

## 1. Raccolta dati / procedura (FAI QUESTO PRIMA DI GIUDICARE)

### Step 1 — Contesto
Leggi: `PROJECT_STATE.md` (sessione corrente, fase, feature deployate, in-flight),
`BUSINESS_STATE.md` (positioning, target, diary status, claim marketing),
`AUDIT_PROTOCOL.md` (protocollo completo, regole Auditor).

### Step 2 — Sito live vs codice (richiede Chrome)
Naviga il sito live `https://bagholderai.lol` con gli strumenti browser e cattura
il testo di ogni pagina come evidenza (`site_<pagina>.md`): `/`, `/roadmap`,
`/blog`, `/library`, `/diary`, `/dashboard`, `/howwework`, `/blueprint`. Per
ciascuna, confronta col codice (`web_astro/`):
- **Roadmap (bidirezionale):** il sito promette feature che non esistono nel codice
  (promesse vuote)? Il codice ha feature che la roadmap non menziona (roadmap non
  aggiornata)?
- **Claim homepage:** sono accurati?
- **Dashboard:** riflette lo stato reale dei bot?
- **Blog:** i post descrivono cose che esistono davvero?

Se Chrome non è disponibile → salta e segnala **CRITICAL** (la verifica del sito è
il cuore dell'Area 2).

### Step 3 — File di stato vs realtà
- `PROJECT_STATE.md` descrive accuratamente lo stato? (confronta §1-3 col `git log` recente)
- `BUSINESS_STATE.md` combacia con la realtà? (diary status, claim marketing, positioning)
- `AUDIT_PROTOCOL.md §7` è aggiornato coi report di audit reali?

### Step 4 — Blog vs realtà (incrementale)
Leggi il report Area 2 precedente per l'ancora "**Blog coperto fino a:** [slug/data]"
e controlla solo i post pubblicati DOPO. Se non c'è ancora, leggi tutti i
`web_astro/src/content/blog/*.md`. Per ogni post nuovo: descrive eventi/feature
realmente accaduti? I claim tecnici sono accurati vs codice? Il tono è coerente
con sito e altri canali?

### Step 5 — Diary WIP vs realtà (incrementale)
Leggi i docx WIP del diary (`bagholderai-audits/diary/` o `Diario/`). Leggi il
report Area 2 precedente per l'ancora "**Coperto fino a: S_XX**" e verifica solo
le sessioni DOPO quel numero. Per ogni docx nuovo: estrai il testo, incrocia i
claim tecnici col codice e con `report_for_CEO/` della stessa sessione; annota
inesattezze, esagerazioni, omissioni. **Gap di copertura:** confronta l'ultima
sessione del diary col numero in PROJECT_STATE; se c'è scarto → finding **MED**
"Diary WIP indietro di N sessioni".

### Step 6 — Volumi pubblicati vs sito + errata
Elenca i PDF in `bagholderai-audits/diary/` (volumi pubblicati) e confronta con
`/library` e `/diary` (numero volumi, titoli, range sessioni). **Errata:** se
esistono file `Errata_Vol*`, leggili e verifica che le correzioni dichiarate siano
ancora vere nel codice/stato attuale.

---

## 2. Domande guida

1. **Promesse vs realtà:** la roadmap pubblica promette ciò che il codice fa? E viceversa, riflette il nuovo?
2. **Superfici pubbliche stale:** homepage/dashboard/library raccontano lo stato corrente o una versione vecchia?
3. **Drift dei file di stato:** PROJECT_STATE/BUSINESS_STATE combaciano con git/DB/sito?
4. **Blog & diary veritieri:** i claim narrati corrispondono a ciò che il codice e i report confermano?
5. **Volumi & errata:** i volumi sul sito esistono come PDF? Le errata sono ancora vere?

---

## 3. Confronto con l'audit precedente

Leggi l'ultimo `audits/reports/*audit[A2]*.md`: i finding precedenti sono chiusi o
ancora aperti? Sono comparsi nuovi drift? Usa le ancore incrementali ("Coperto
fino a: S_XX" per il diary, "Blog coperto fino a: [slug/data]" per il blog) per
non rifare lavoro già fatto. Il valore sta nel **movimento** (drift nuovi vs
drift che si trascina).

---

## 4. Struttura del report (output atteso)

File: `audits/reports/YYYYMMDD_audit[A2].md` (data SENZA trattini). Sezioni:

- **Scope & Methodology** — cosa è stato controllato, cosa saltato, disponibilità Chrome.
- **Findings** — raggruppati per severity `CRITICAL > HIGH > MED > LOW`, ciascuno con citazione del file di evidenza (`site_*.md`, `diary_check.md`, …) o pagina del sito. Categorie: Site vs Code · State Files vs Reality · Blog vs Reality · Diary vs Reality · Volumi pubblicati vs Sito · Errata.
- **Verdetto** — `APPROVED` / `CON RISERVE` / `REJECTED`.
- **Ancora diary** — "Coperto fino a: S_XX" (per il prossimo audit incrementale).
- **Ancora blog** — "Blog coperto fino a: [slug/data]" (idem).
- **Riga di sintesi per PROJECT_STATE §9** (data, area, topic, verdetto, conta findings, report path).

Nota nel report che è stato prodotto da un Auditor (e, se automatico, da un Cowork scheduled task).

---

## 5. Regole

- **L'Auditor NON shippa**: niente fix, niente edit ai brief, niente migration, niente restart bot. Solo report + ancore + riga §9 (vedi `AUDIT_PROTOCOL.md §3` e §5). I fix li farà una sessione CC normale con brief dedicato, o il CEO.
- **Findings tracciabili**: severity + file di evidenza/pagina sempre. Un finding senza riferimento è un'opinione, non un finding.
- **Fallback** (non bloccarti): no Chrome → salta Step 2 e **CRITICAL** (è il cuore dell'audit); docx diary illeggibili → **HIGH** con l'errore reale; nessun accesso a uno strumento → annota il limite, non improvvisare. **Anti-invenzione:** se una causa non è determinabile, scrivi "non determinata", non inferirla.
- **Cadenza/trigger sui FILE, non su §9**: la conta si fa sui file `audits/reports/*audit[A2]*.md`, non sulle righe di PROJECT_STATE §9 (regola anti-drift `CLAUDE.md §[1]`).
- **Il report resta gitignored/locale** (`audits/reports/*` è in `.gitignore`): in git va **solo la sintesi** — riga PROJECT_STATE §9 + storico `AUDIT_PROTOCOL.md §7` (+ BUSINESS_STATE se cambi strategici). NON fare `git add audits/reports/` (è un no-op: il file è ignorato). Solo l'Auditor scrive in §9.
