# Brief 65a — Site Fixes (public + private dashboards)

> **SHIPPED 2026-05-08 commit `4a00875` (S65)** — 5 task: navbar admin, sezione Diary in homepage,
> rimossa riga TF capital, paginazione `sb-paginated.ts`, indagine FIFO mismatch (root cause
> identificata: NON cap 1000 ma strict-FIFO ≠ FIFO-among-triggered, da cui poi è emersa la
> riconciliazione completa di S65).

**Da:** CEO (Claude)  
**Per:** CC (Claude Code)  
**Basato su:** PROJECT_STATE.md aggiornato 2026-05-07 (S63 chiusura)  
**Sessione:** 65  
**Stima totale:** ~3–4h (task 1–4 + investigazione task 5)  
**Priorità:** Alta (task 1–3 immediati, task 4 deadline tecnica ~17 maggio + causa probabile del FIFO mismatch visibile oggi, task 5 a margine)

---

## Task 1 — Fix navbar `admin.html` (~15 min)

**Problema:** La navbar di `/admin` ha i link (Home / Grid / TF / Admin) allineati a **sinistra**. Su `grid.html` e `tf.html` sono allineati a **destra**. Inoltre il font potrebbe non corrispondere — verificare.

**Cosa fare:**
1. Aprire `web_astro/public/grid.html` e individuare il CSS/HTML della navbar (è il reference)
2. In `web_astro/public/admin.html`, allineare il container dei link a destra, identico a `grid.html`
3. Verificare che il font-family e le dimensioni siano identici su tutte e 3 le pagine (`grid.html`, `tf.html`, `admin.html`)
4. Se ci sono differenze di font, allineare admin.html agli altri due

**Output atteso:** Navbar identica (posizione, font, spaziatura, active state) su tutte e 3 le dashboard private.

**Vincoli:** Non toccare la logica JS o i dati — solo CSS/HTML della navbar.

---

## Task 2 — Aggiungere diary entries in homepage (~45 min)

**Problema:** I visitatori si fermano alla homepage senza capire che il progetto è vivo. Il "SESSION 64 · IN PROGRESS" in fondo all'hero non comunica abbastanza.

**Cosa fare:**
1. In `web_astro/src/pages/index.astro`, aggiungere una nuova sezione **tra l'hero (titolo + live snapshot + CTA) e la sezione "THE AI BOTS · AT WORK"**
2. Titolo sezione in stile sito: `§ · DEVELOPMENT DIARY` (mono, uppercase, tracking wide, color `text-pos` come gli altri `§` headers — vedi `STYLEGUIDE.md`)
3. Mostrare le **ultime 3 entries** da `diary_entries` su Supabase, ordinate per `session DESC`
4. Ogni entry è una riga cliccabile con:
   - Numero sessione: `Session {session}` in mono
   - Titolo ironico: `— {title}` in text-text
   - Data: `{date}` allineata a destra, text-muted
5. **Tutto il blocco è cliccabile** — ogni riga linka a `/diary` (non a una singola entry, non abbiamo ancora il deep link)
6. Sotto le 3 entries, un link: `Read the full diary →` che porta a `/diary`
7. Fetch dati: query Supabase REST `diary_entries?select=session,title,date,status&order=session.desc&limit=3` — stessa connessione già usata da `live-stats.ts`
8. Mostrare sia entries COMPLETE che BUILDING (BUILDING = sessione in corso, se presente)

**Stile di riferimento:** font mono per numeri, Inter per titoli. Niente box decorativi — deve sembrare un log vivo, non una feature card. Spacing coerente col rest della homepage (vedi `STYLEGUIDE.md` per pattern hero ↔ section).

**Output atteso:** Sezione visibile in homepage tra hero e bot, caricata da Supabase, 3 righe linkabili + link al diary.

**Vincoli:** Non spostare né modificare il live snapshot, i CTA, o la sezione AI Bots. Solo inserire la nuova sezione nel mezzo.

---

## Task 3 — Rimuovere riga "TF capital" da `tf.html` (~5 min)

**Problema:** In fondo alla sezione "Portfolio Overview" di `tf.html`, c'è una riga:  
`TF capital: $100.00 base + −$36.57 floating = $63.43 effective (allocator budget for new ALLOCATEs)`

È un dettaglio interno dell'allocator, i numeri sono potenzialmente sbagliati (floating usa costo d'acquisto, non market value), e tutte le informazioni utili sono già nelle card sopra.

**Cosa fare:**
1. In `web_astro/public/tf.html`, individuare l'elemento HTML che contiene la riga "TF capital:"
2. Rimuovere l'intero elemento (HTML + eventuale JS che lo popola)
3. Verificare che non ci siano riferimenti orfani nel JS dopo la rimozione

**Output atteso:** La sezione Portfolio Overview finisce dopo le card (Fees Paid / Dust V3), nessuna riga in fondo.

**Vincoli:** Non toccare le card sopra né nessun'altra sezione. Solo rimuovere quella riga.

---

## Task 4 — Brief 60e: Paginazione home + dashboard pubblica (~1h)

**Problema:** `dashboard-live.ts` e `live-stats.ts` usano il workaround "split per managed_by" per le query Supabase su `trades`. Il bucket TF è a ~700 righe oggi e sfonderà il cap 1000 di Supabase REST entro ~17 maggio. Dopo quel punto, **i numeri in homepage e /dashboard mentiranno silenziosamente** (mostreranno solo le prime 1000 trade ordinate ASC, troncando i recenti).

**Soluzione concordata (S63, CEO + Board):** Implementare `sbqAll()` con paginazione tramite Range header. Il pattern è **già implementato e funzionante** in `web_astro/public/admin.html` — va portato nei file pubblici.

**Cosa fare:**
1. Estrarre la funzione `sbFetchAll()` (o `sbqAll()`) da `admin.html` e renderla riusabile (o copiarla inline — decisione delegate a CC, vedi sotto)
2. In `web_astro/src/scripts/live-stats.ts` (homepage): sostituire le query Supabase REST singole con `sbFetchAll()` per la tabella `trades`
3. In `web_astro/src/scripts/dashboard-live.ts` (pagina /dashboard): stessa sostituzione
4. Testare con una query che restituisce >1000 righe (chiedere a CEO/Board se serve un mock o se bastano i dati live TF)

**Output atteso:** Homepage e /dashboard continuano a mostrare numeri corretti anche quando `trades` supera 1000 righe per bucket.

**Vincoli:** 
- NON toccare `admin.html` — funziona già
- NON toccare `grid.html` o `tf.html` — usano query diverse
- Il pattern di paginazione deve essere identico a quello di admin.html (Range header, accumulate, sort client-side)

---

---

## Task 5 — Investigazione: FIFO mismatch dashboard vs DB (~30 min)

**Problema riscontrato dal Board durante S65:**

Due sell di oggi (ZEC e BONK) mostrano P&L **negativo** nella dashboard tf.html/grid.html, ma nel DB il `realized_pnl` è **positivo**. La dashboard sta assegnando il lotto d'acquisto sbagliato nel FIFO replay client-side.

Dati concreti:
- **ZEC sell 10:27 UTC**: DB dice buy@$555.22 → P&L +$0.097. Dashboard mostra buy@$573.91 → P&L -$0.11
- **BONK sell 04:24 UTC**: DB dice buy@$0.00000672 → P&L +$0.52. Dashboard mostra buy@$0.00000687 → P&L -$0.03

**Ipotesi CEO:** il cap 1000 righe Supabase REST tronca i buy più vecchi → il replay FIFO parte da un punto sbagliato → le associazioni buy↔sell si disallineano. Se confermato, il Task 4 (paginazione 60e) è anche la cura di questo bug.

**Cosa fare:**
1. Verificare quante righe `trades` restituisce la query REST attuale in tf.html e grid.html (è sotto o sopra 1000?)
2. Confrontare il FIFO replay della dashboard con i dati DB per le due sell sopra — quale buy lot viene assegnato e perché?
3. Confermare o smentire che la paginazione (Task 4) risolve il problema
4. Se la causa è diversa dal cap 1000, documentare la root cause e segnalare

**Output atteso:** Un commento nel commit o una nota nel report CC che dica "FIFO mismatch caused by X, fixed by Task 4" oppure "root cause diversa, serve intervento aggiuntivo".

---

## Decisioni delegate a CC

- Task 4: `sbFetchAll()` come funzione condivisa in un file utility `.ts` vs copia inline nei due file. Scegliere l'approccio che minimizza il rischio di regressione.
- Task 2: Layout esatto della riga diary (flex con gap vs grid) — usare il pattern più coerente con la homepage esistente.

## Decisioni che CC DEVE chiedere

- Se durante Task 4 scopre che il workaround "split per managed_by" ha altri bug oltre al cap 1000 → fermarsi e segnalare
- Se la query `diary_entries` in Task 2 richiede una nuova policy RLS → segnalare (non creare policy autonomamente)
- Se la navbar di `admin.html` (Task 1) ha differenze strutturali oltre all'allineamento (es. link diversi, hash diverso) → segnalare

## Roadmap impact

Nessun impatto su Phase 9 V&C o roadmap pubblica. Task 4 chiude un item in BUSINESS_STATE §5 (#15).

## Git

Push diretto su main. 1 commit per task o 1 unico commit se tutti completati insieme — a discrezione CC. Messaggio formato: `S65: [cosa]`.
