# BRIEF 74b — Grid public dashboard: stop-buy guard + trigger reference visibility

**Scoperto:** 2026-05-12 durante audit S74
**Priorità:** Media-alta — non bloccante (bot lavora correttamente), ma operativamente confonde l'utente
**Stima effort:** 30-60 min (a seconda dello scope scelto)

---

## Contesto

Durante l'audit S74 (Telegram + sito), Max ha guardato il card BONK su `/grid` e ha chiesto: "se il widget dice next buy a $0.00000718 e siamo a $0.00000700, perché non compriamo?".

Il widget mostrava in verde "Next buy if ↓ $0.00000718" — il colore verde indica "prezzo già sotto trigger, scatta a breve". Il prezzo era effettivamente $0.00000700, quindi 2.5% sotto il trigger mostrato. Ma il bot **non comprava da 4h**.

Investigazione sul log live BONK ha mostrato che il bot ha attivato una guardia hardcoded che il dashboard non racconta:

```
17:28:25 [bagholderai.grid] INFO: [BONK/USDT] BUY BLOCKED: stop-buy active
   (drawdown > 2.0% of allocation). Waiting for profitable sell to reset.
```

Stato BONK al momento della scoperta:
- Allocation: $100 (open cost basis)
- Holdings: 14.81M BONK
- Avg buy: $0.00000744
- Current price: $0.00000700-0.00000718 (drawdown 6.3%)
- Realized P&L: +$8.26 (cycle precedente)
- Unrealized P&L: −$6.33
- Drawdown > 2% threshold → stop-buy attivo

Quindi il bot fa il suo lavoro per design (rete di sicurezza anti-pile-up), ma l'utente non lo capisce dal sito.

---

## Bug 1 (priorità alta) — Stop-buy guard invisibile sul dashboard

**Sintomo:** widget "Next buy if ↓" mostra colore verde (= già sotto trigger, sta per comprare) mentre il bot ha disattivato i buy via guardia stop-buy. L'utente pensa che il bot sia rotto.

**Root cause:** `web_astro/public/grid.html` riga 916-919 calcola `nextBuyColor` solo da `nextBuyDistance` (distanza prezzo vs trigger). Non legge lo stato `stop_buy_active` del bot. Il widget non sa che esiste questa guardia.

**Dove vive la guardia nel bot:** cercare in `bot/grid/grid_bot.py` o simili — pattern `stop-buy active` (vedi log riga 17:28:25). Probabile flag come `state.stop_buy_active` o `state.drawdown_lock` letto dal DB.

**Fix proposto:**
- Aggiungere campo `stopBuyActive` nello stato letto da Supabase per il widget grid (probabile fonte: `bot_state` o tabella simile dove il bot scrive il drawdown lock)
- Quando `stopBuyActive == true`, sostituire (o sovrapporre) il widget "Next buy if ↓" con un badge rosso "STOP-BUY ACTIVE" + tooltip "Drawdown > 2% — waiting for profitable sell to reset"
- In alternativa: mostrare il trigger normale ma in rosso con annotazione `(blocked: drawdown)`

**Stima:** ~30-45 min se il flag è già esposto via Supabase, +30 min se va aggiunto al schema.

---

## Bug 2 (priorità media) — Trigger price disallineato widget vs bot

**Sintomo:** widget mostra "Next buy if ↓ $0.00000718", bot internamente usa $0.00000707. Differenza ~1.5%.

**Root cause:** divergenza tra due nozioni di "last buy reference":
- Widget (`grid.html` riga 905): `nextBuyTrigger = a.lastBuyPrice × (1 − buyPct/100)` dove `lastBuyPrice` viene dalla tabella trades (= prezzo dell'ultimo buy effettivo registrato, $0.00000737 in questo caso)
- Bot internamente: usa la reference price post-IDLE_RECALIBRATE ($0.00000725 in questo caso), che è diversa quando il bot ha resettato la reference dopo un periodo di inattività

Quindi la formula del widget è "matematicamente corretta" rispetto ai trades, ma "operativamente sbagliata" rispetto a cosa il bot guarda davvero.

**Fix proposto:**
- Esporre dal bot la reference price corrente (`buy_reference_price` o simile) nel `bot_state` table
- Widget deve leggere quella, non `lastBuyPrice` dai trades
- Mostrare sotto il widget una nota: "reference reset Xh ago" se IDLE_RECALIBRATE è scattato, per giustificare la differenza tra last actual buy e current reference

**Stima:** ~45-60 min — richiede di mappare dove il bot scrive (o NON scrive) la reference price corrente.

---

## Vincoli

- **NON toccare** la logica del bot (`grid_bot.py`, `grid_runner.py`) — il bot lavora correttamente, è solo il dashboard cieco
- **NON toccare** la formula del bot per calcolare la reference (non cambiare il comportamento di trading)
- Il bot gira su testnet, low risk

---

## Decisioni delegate a CC

- Stile UI del badge "STOP-BUY ACTIVE" (rosso pieno vs outline, dove si posiziona)
- Esatto wording del tooltip
- Se Bug 2 si rivela complesso (reference price non esposta), parcheggiare in brief 74c separato

## Decisioni che CC DEVE chiedere

- Se la guardia stop-buy ha altre varianti oltre al drawdown (es. daily P&L limit, capital exhausted) — verificare se conviene un unico badge generico "BUY BLOCKED: {reason}" che copre tutti i casi
- Se il flag `stop_buy_active` esiste già in Supabase o va aggiunto

---

## Domanda strategica aperta (Max, 2026-05-12)

Indipendentemente dalla visibilità sul dashboard, ha senso bloccare i buy a tempo indefinito? Proposta Max: aggiungere un **time-limit allo stop-buy**, es. dopo 24h di stallo, il bot compra comunque per abbassare l'avg cost. Logica: se il drawdown persiste senza nuovi sell che resettino la guardia, restare bloccati significa subire passivamente il calo invece di mediare. È una proposta da valutare separatamente — **non è in scope per il fix dashboard**, ma è una decisione di trading logic che riguarda la stessa area.

Trattare come decisione strategica aperta nel PROJECT_STATE (sezione 6 "Domande aperte per CEO"). Non implementare senza brief dedicato.

## Roadmap impact

Nessuno — fix UX sul sito pubblico, nessuna logica di trading toccata. Non blocca il go-live mainnet, ma è gating per **la fiducia dell'utente nel dashboard** (= gating per "siti come vetrina pubblica raccontano la verità").

---

## Riferimenti

- Log live evidence: `/Volumes/Archivio/bagholderai/logs/grid_BONK_USDT.log` (Mac Mini), pattern `BUY BLOCKED: stop-buy active`
- Widget code: `web_astro/public/grid.html:894-925`
- Memoria correlata: `feedback_one_source_of_truth.md` — questo bug è un caso scuola di sources of truth divergenti tra bot e dashboard
