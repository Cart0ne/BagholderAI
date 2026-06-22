Brief S108a — haiku-fix-housekeeping — 2026-06-20

Basato su: PROJECT_STATE.md consultato via PK search 2026-06-20.
Sessione: S108 (mini sessione mobile + follow-up al PC).

---

## Contesto

Il sistema haiku genera contenuti con riferimenti a "paper trading"
nonostante il progetto sia in testnet live dal 11 giugno (S102).
La root cause è nei system prompt stali di x_poster.py e probabilmente
commentary.py. Inoltre il footer Telegram del report pubblico dice
"PAPER MODE" hardcoded. Zero logging haiku su Supabase. Duplicati in
daily_commentary.

---

## Task 1 — Fix system prompt x_poster.py

File: `utils/x_poster.py`

La variabile `SYSTEM_PROMPT` riga 1 dice:
> "You are BagHolderAI's voice on X — an AI CEO running a paper trading startup"

Cambiare "paper trading startup" con una descrizione accurata dello
stato attuale. Proposta:
> "an AI CEO running a crypto trading experiment on Binance testnet"

Anche la riga:
> "Paper trading losses get full comedy. Real stakes get respect."

Va riscritta per riflettere che siamo in testnet (non paper, non
mainnet). Proposta:
> "Testnet losses get comedy. When real money arrives, respect."

**NON toccare** la struttura del prompt, le regole NEVER, la voice
section, MAX_POST_CHARS, la logica di retry, o qualsiasi altra cosa
nel file. Solo le 2 stringhe sopra.

## Task 2 — Fix system prompt commentary.py

File: `commentary.py` (o dove vive `generate_daily_commentary`)

CC deve cercare il system prompt della daily commentary e verificare
se contiene riferimenti a "paper trading" o "paper mode". Se sì,
applicare la stessa correzione del Task 1.

Aggiungere anche un'istruzione nel prompt: usare "unrealized losses"
invece di "paper losses" quando descrive perdite non realizzate.

## Task 3 — Fix footer Telegram report pubblico

File: `utils/telegram_notifier.py`

Il metodo `send_public_daily_report` ha hardcoded:
```
text += f"\n🤖 <i>PAPER MODE · ...
```

Il report PRIVATO (metodo `send_private_daily_report`) usa già
correttamente `status.get('mode', 'paper').upper()`. Applicare la
stessa logica al report pubblico. Se il mode non è disponibile nel
contesto di send_public_daily_report, passarlo come parametro
aggiuntivo dal chiamante (daily_report.py).

Nota: exchange.py ha già il mapping corretto:
- `TradingMode.is_paper()` → "PAPER"
- `ExchangeConfig.TESTNET` → "LIVE TESTNET"
- else → "LIVE MAINNET"

## Task 4 — Pulizia duplicati daily_commentary

Eseguire su Supabase:
1. Identificare le entry duplicate per il 5 giugno e il 15 giugno
   (due righe per ciascuna data)
2. Per ogni coppia, mantenere quella con `created_at` più recente
   (presumibilmente la versione corretta post-fix)
3. Eliminare la più vecchia

**CHIEDERE A MAX** prima di eseguire il DELETE — mostrare le due
entry per ogni data e fargli scegliere quale tenere.

## Task 5 — Aggiornamento CLAUDE.md: regola numerazione sessioni

Aggiungere nella sezione appropriata di CLAUDE.md (probabilmente
vicino alle regole di sessione esistenti):

```
### Numerazione sessioni (formalizzata S108, 2026-06-20)

- **Sessioni di lavoro** (CEO + Board): prendono numero progressivo
  (S108, S109...). Hanno diary, summary Supabase, possono avere brief.
- **Sessioni marketing**: niente numero, niente diary, niente brief.
  Solo aggiornamento marketing tracker.
- **Audit automatici** (Cowork): niente numero sessione. Se producono
  brief, naming: `YYYY-MM-DD_audit[Area]_brief_SCOPE.md`.
  Esempio: `2026-06-18_auditA2_brief_remediation.md`.
```

---

## Decisioni delegate a CC

- Wording esatto dei prompt aggiornati (Task 1, 2), purché il senso
  sia "testnet live, non paper trading"
- Scelta di come passare il mode al report pubblico Telegram (Task 3)

## Decisioni che CC DEVE chiedere a Max

- Quali entry duplicate eliminare in daily_commentary (Task 4) —
  mostrare entrambe e chiedere

## Output atteso

1. x_poster.py con prompt aggiornato (Task 1)
2. commentary.py con prompt aggiornato (Task 2)
3. telegram_notifier.py con footer dinamico (Task 3)
4. daily_commentary pulita (Task 4, post conferma Max)
5. CLAUDE.md aggiornato con regola numerazione (Task 5)
6. Commit unico con messaggio che elenca tutti i fix

## Vincoli

- NON restartare il bot — il restart lo fa Max manualmente dopo
  verifica. Dopo il commit, segnalare a Max che serve restart per
  attivare i fix dei prompt (Task 1-3)
- NON toccare la logica di generazione (retry, max_tokens, model)
- NON toccare haiku_classifier.py (NewsKeeper) — quello è un
  sistema diverso con prompt corretto
- NON creare nuove tabelle Supabase in questo brief (il logging
  haiku su Supabase è un task separato, futuro)

## Auto-obiezione

I fix ai prompt (Task 1-3) si attivano solo dopo restart del bot.
Fino al restart, il sistema continua a generare con i prompt vecchi.
Max deve fare il restart PRIMA delle 21:00 (orario del daily report)
perché il fix abbia effetto sulla commentary di oggi. Se il restart
avviene dopo le 21:00, il primo effetto visibile sarà domani.
