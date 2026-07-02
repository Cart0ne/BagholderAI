# Brief S115 — seo-hygiene-fixes — 2026-07-02

**Da:** CEO (Claude) · **A:** CC (Intern) · **Approvato da:** Max (Board)
**Contesto:** sessione S115 = verifica dell'audit A3 del 2026-07-02 (`marketing/runs/2026-07-02/20260702_audit[A3].md`). La verifica ha confermato i numeri grezzi ma ha ribaltato parte delle conclusioni: i dati Umami erano inquinati da bot (DE+FI) e self-traffic (IT). Traffico esterno reale al sito a giugno: **~3 visitatori**. Questo brief chiude i fix di igiene emersi e — punto più importante — crea il registro dei caveat dati perché nessun analista futuro rifaccia gli stessi errori.
**Base di stato:** PROJECT_STATE.md post-S114 nel repo (HEAD `f745232` al clone audit del 2026-07-02). ⚠️ Nota drift: la copia di PROJECT_STATE.md in Project Knowledge risulta ferma al 2026-06-06 (S98) — verificare la sync GitHub→PK, ma per questo brief fa fede il file nel repo.

---

## Task (in ordine di priorità)

### 1. Creare `audits/DATA_CAVEATS.md` ⭐ (il deliverable vero)

Registro delle stranezze note dei dati marketing/analytics. Va letto da QUALSIASI analista (Auditor Cowork, CEO, umano) PRIMA di toccare i numeri. Prime voci (riformulale pure, la sostanza è questa):

1. **Umami — bot ricorrenti:** Germania + Finlandia = bot noti da mesi (~420 visite/mese totali, bounce 99–100%, durata 0s, nessun referrer). FILTRARE SEMPRE prima di ogni analisi.
2. **Umami — self-traffic:** Italia ≈ visite di Max (controllo/sviluppo). Il traffico esterno reale è il residuo dopo aver escluso DE+FI+IT. A giugno 2026: ~3 visitatori.
3. **Umami — API a pagamento:** dal ~giugno 2026 le API key Umami Cloud sono riservate ai piani a pagamento → il connettore automatico riceve 401. Umami è declassato a **fonte manuale** negli audit A3 (screenshot/lettura dashboard, filtri paese applicati). Non tentare di rigenerare la chiave.
4. **Connettore Bing (`seo_bing`):** bug dedup — la stessa pagina compare su più righe nella tabella top pages (probabile mancata normalizzazione varianti URL). Vedi task 2.
5. **GSC — posizione media:** NON comparabile mese-su-mese senza confronto per-pagina (è pesata sulle impressions; un cambio di mix la sposta senza ranking reali cambiati). Le query di `/roadmap` sono ~100% anonimizzate da Google (long-tail rara): non ottimizzabile via title/meta.
6. **Payhip — views:** natura (umana/bot) non verificabile dalla dashboard. Trattare come ordine di grandezza.
7. **Vercel vs Umami:** contano in modo diverso (adblocker, definizioni). Validi solo i delta DENTRO lo stesso strumento, mai i confronti tra strumenti.

In più, nello stesso task:
- Aggiungere in `AUDIT_PROTOCOL.md` (sezione A3) l'obbligo di leggere `audits/DATA_CAVEATS.md` e la `MASTER_TASK_LIST` più recente prima dell'analisi (la seconda evita raccomandazioni doppione, es. l'audit di oggi ha ri-proposto la strategia engagement X che è già il task 2.8).

### 2. Fix dedup connettore Bing

In `scripts/marketing_data_refresh` (modulo Bing): normalizzare gli URL (schema/trailing slash/parametri) e aggregare le righe della stessa pagina prima di scrivere `seo_bing.md`. Output atteso: una riga per pagina.

### 3. Fix slug Dev.to

L'articolo "Can an AI Actually Run a Company?" è esposto con slug `...-temp-slug-9355224` (0 views). Decidere con Max (vedi sotto): pubblicarlo pulito o toglierlo. Se si pubblica: slug definitivo, canonical verso il blog se esiste il gemello `can-an-ai-run-a-company.md`.

### 4. Pulizia 4xx Bing (25 errori)

Gli URL specifici NON sono nei dati grezzi dell'audit: vanno estratti dalla dashboard Bing Webmaster (accesso di Max) o via API se il connettore lo permette. Poi: redirect 301 o fix link interni a seconda dei casi.

### 5. Title/meta description su `/blog/claude-code-crypto-trading-bot/`

Bing lo mostra in posizione 4–10 su query on-target ("claude crypto trading bot" e simili) con 0 click. Riscrivere title + meta description con l'intento di quelle query. **Etichetta onesta: è igiene, non leva** — parliamo di ~18 impressioni/mese; anche un ottimo CTR = 1–2 click. Non è il fix che cambia il traffico. NON toccare title/meta di `/roadmap` (query anonime, vedi caveat 5 — sarebbe lavoro al buio).

---

## Decisioni delegate a CC
- Struttura/wording di DATA_CAVEATS.md e punto esatto di aggancio in AUDIT_PROTOCOL.md
- Dettagli tecnici della normalizzazione URL nel connettore Bing
- Formulazione title/meta del task 5 (coerente con la voce del blog)

## Decisioni che CC DEVE chiedere (a Max)
- Task 3: pubblicare o rimuovere il draft Dev.to? (decisione editoriale)
- Task 4: farsi passare da Max l'elenco 4xx dalla dashboard Bing se non estraibile via API
- Qualsiasi cosa fuori dallo scope di questi 5 punti

## Output atteso a fine sessione
- `audits/DATA_CAVEATS.md` nel repo + riferimento in AUDIT_PROTOCOL.md
- Connettore Bing dedupato (con un test o verifica su run locale)
- Slug Dev.to risolto (in un senso o nell'altro)
- 4xx: fixati, o lista+piano se servono dati da Max
- Title/meta post Kraken-bot aggiornati e deployati
- PROJECT_STATE.md rigenerato (riga in §10), commit+push su main

## Vincoli
- NON toccare codice del bot / hot-path trading (fuori scope totale)
- NON toccare title/meta di `/roadmap`
- NON rigenerare o toccare credenziali (Umami incluso)
- Task tutti < 1h ciascuno → niente piano preventivo in italiano, MA se il dedup Bing (task 2) si rivela più profondo del previsto (>1h), fermarsi e produrre il piano prima di procedere

## Auto-obiezione (anti-assenso)
Il task 5 potrebbe essere pura vanità a questa scala: 18 impressioni/mese non muovono nulla, e si potrebbe obiettare che persino mezz'ora è mal spesa finché il sito ha ~3 visitatori esterni. Lo tengo comunque perché (a) è l'unico punto dove il ranking c'è già e manca solo lo snippet, (b) il costo è minimo, (c) stabilisce il pattern "si ottimizza dove l'intento di ricerca è noto" — che è la lezione metodologica della sessione. Se CC ritiene che anche questo sia troppo, l'obiezione è benvenuta: si discute, non si esegue in silenzio.
