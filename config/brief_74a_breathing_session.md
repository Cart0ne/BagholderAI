# BRIEF 74a — Sessione respiro: How We Work v3 + mini fix sito/Telegram

**Basato su:** PROJECT_STATE.md 2026-05-12 (S73c, commit `5061a29`)  
**Priorità:** Media — nessun bug bloccante, pulizia e contenuto  
**Stima effort:** ~2-3h totali (4 task indipendenti)

---

## Contesto

S73 è stata una maratona di bug fix (dead zone, dust trap, phantom holdings, LOT_SIZE). S74 è una sessione di respiro: zero logica di trading, solo miglioramenti al sito e a Telegram. Il bot continua a girare su testnet senza modifiche.

---

## Task 1 — How We Work v3 sul sito (priorità 1)

**File target:** `web_astro/src/pages/howwework.astro`  
**Fonte:** `drafts/2026-05-07_howwework_v3.md` (nella repo, cartella `drafts/`)

Applicare i 5 blocchi descritti nel draft, in ordine:

1. **Hero update** — `v2.0 · march 2026` → `v3.0 · may 2026`, `3 entities` → `4 entities`
2. **§3 Lessons learned** — aggiungere voce "Stale instructions fail silently" (il codice Astro esatto è nel draft, blocco 2)
3. **§5 riscritta** — sostituire interamente "How memory actually works" con "How state actually works" (blocco 3 del draft)
4. **§6 nuova** — inserire "Verification & Control" tra la §5 riscritta e l'attuale "Want to replicate" (blocco 4)
5. **§7 ex §6** — rinominare "Want to replicate" da §6 a §7, aggiungere step 5 "Add state files before you need them" (blocco 5)

**NON toccare** `HowWeWorkInteractive.jsx` — il quarto attore nel diagramma React è un brief separato.

**Commit:** `feat(site): howwework v3 — state files + V&C section`

Dopo il deploy Vercel (~1-2 min), spostare `drafts/2026-05-07_howwework_v3.md` in `drafts/applied/2026-05/` (creare la cartella se non esiste).

### Decisioni delegate a CC
- Nessuna — il draft contiene il codice Astro esatto da copiare

### Decisioni che CC DEVE chiedere
- Se la struttura attuale di howwework.astro è cambiata rispetto alla v2.0 (es. qualcuno l'ha toccata tra S63 e S74), fermarsi e chiedere al Board prima di applicare

---

## Task 2 — Telegram: fix branching cosmetico (priorità 2)

**Problema:** quando il bot skippa un buy (es. `idle_recalibrate_skipped`, `buy_blocked_above_avg`), il messaggio Telegram successivo dice "Buying at market..." anche se il buy non avviene. Il branching nel codice Telegram mostra il messaggio di acquisto prima di sapere se l'acquisto è stato effettivamente eseguito.

**Fonte:** report S73c, sezione "Cosa NON è stato fatto", punto 1.

**Fix atteso:** il messaggio Telegram "Buying at market" deve apparire SOLO dopo che il buy è stato confermato (fill ricevuto), non prima. Se il buy viene skippato, nessun messaggio o messaggio diverso.

**Stima:** ~10-15 min.

**Commit:** `fix(telegram): buy message only after confirmed fill`

### Decisioni delegate a CC
- Dove esattamente intervenire nel codice (probabilmente `grid_runner.py` o `buy_pipeline.py` nel punto dove viene chiamato il notifier Telegram)
- Se servono altri branching fix simili (es. sell messages)

### Decisioni che CC DEVE chiedere
- Niente — è cosmetico, non cambia logica di trading

---

## Task 3 — Admin graph: aggiungere opportunity score (priorità 3)

**Problema:** il grafico Sentinel nella pagina `/grid` (ex `/admin`) mostra solo il risk score. Manca l'opportunity score.

**Fonte:** Apple Notes todo "Sistemare grafico admin (manca opportunity risk)"

**Fix atteso:** aggiungere la linea opportunity_score al grafico Sentinel esistente, con colore diverso e legenda.

**Stima:** ~30-45 min.

**Commit:** `feat(admin): add opportunity score to Sentinel chart`

### Decisioni delegate a CC
- Colore e stile della linea opportunity
- Se usare asse Y condiviso o separato (entrambi sono 0-100, quindi condiviso ha senso)

### Decisioni che CC DEVE chiedere
- Niente — è display only

---

## Task 4 — Telegram: label in italiano nei report privati (priorità 4)

**Problema:** i report Telegram privati (daily summary) hanno label in inglese. Il Board vuole label in italiano per il canale privato.

**Fonte:** Apple Notes todo "Sistemare label in italiano nei privati"

**Fix atteso:** tradurre le label principali nei report Telegram privati (es. "Holdings" → "Posizioni", "Realized P&L" → "P&L Realizzato", etc.). Solo il canale privato — il canale pubblico `@BagHolderAI_report` resta in inglese.

**Stima:** ~20-30 min.

**Commit:** `feat(telegram): italian labels for private reports`

### Decisioni delegate a CC
- Quali label tradurre (tutte quelle visibili nel report privato)
- Come distinguere privato vs pubblico nel codice (probabilmente già esiste un flag `is_public` o `channel_id`)

### Decisioni che CC DEVE chiedere
- Se una traduzione specifica non è chiara (es. termini tecnici di trading)

---

## Ordine di esecuzione

1. Task 1 (How We Work) — il più lungo, fallo per primo
2. Task 2 (Telegram branching) — rapido, indipendente
3. Task 3 (Admin graph) — indipendente
4. Task 4 (Label italiano) — indipendente

Ogni task ha il suo commit separato. Push dopo ogni task (non accumulare).

---

## Output atteso a fine sessione

- howwework.astro aggiornata a v3, live su Vercel
- Draft spostato in `drafts/applied/`
- Messaggio Telegram "Buying at market" solo dopo fill confermato
- Grafico Sentinel con opportunity score visibile
- Report privato Telegram con label in italiano
- PROJECT_STATE.md aggiornato (CC lo rigenera come ultimo step)

---

## Vincoli

- **NON toccare** logica di trading (grid_bot, buy_pipeline, sell_pipeline, state_manager)
- **NON toccare** Sentinel/Sherpa code (stanno raccogliendo dati)
- **NON toccare** HowWeWorkInteractive.jsx (brief separato)
- **NON riavviare** il bot sul Mac Mini a meno che il Task 2 non lo richieda (in quel caso: `source venv/bin/activate && python3.13 -m bot.orchestrator`)
- Il bot gira su testnet — nessun rischio mainnet

---

## Roadmap impact

Nessuno — tutti task cosmetici/contenuto. Il go-live target (fine maggio/inizio giugno) non è impattato.
