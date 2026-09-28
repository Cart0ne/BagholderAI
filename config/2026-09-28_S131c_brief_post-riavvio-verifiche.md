Brief S131c — post-riavvio-verifiche — 2026-09-28

**Da:** CEO · **Per:** CC · **Board:** Max (S131, 28-set, coda rapida)
**Basato su:** riavvio delle 19:15 UTC del 28-set (regola zona morta `a2a8028` live); report S132 `zona-morta-regola` e `a1-addendum`.
**Report atteso:** `report_for_CEO/YYYY-MM-DD_SXXX_RforCEO_post-riavvio-verifiche.md` — SCOPE identico: `post-riavvio-verifiche`. Tre punti, solo lettura salvo il punto 2. Stima 45 min.

---

## 1. "TF on" nel log di avvio (verifica, denaro reale)

`bot_events_log` 19:15:09 UTC: *"Orchestrator started with 2 grid bot(s), TF on"*. Da MASTER_TASK_LIST il Trend Follower è **spento dal 7-ago e non ha mai operato su Kraken**.

**Dire nero su bianco:** cosa significa "TF on" in quel messaggio; quanti slot ha il TF oggi e con quale capitale; se può aprire posizioni su Kraken con soldi veri in questo stato; da quando è così; se è coerente con la decisione del 7-ago. Se il TF può operare, **STOP e flag a Max** prima di qualunque cosa: non spegnerlo di iniziativa, ma dirlo subito.

## 2. Test che scrivono nel database di produzione (fix)

`bot_events_log` 19:11:56–59 UTC (tre minuti prima del riavvio): ~15 righe con simboli `TEST/USD`, `TEST/USDT`, `BTC/USDT` (vendite fittizie a $100, `dead_zone_recalibrate` a $81.853, `profit_lock_triggered`, `trailing_stop_triggered`). Sembra la suite di test lanciata sul Mini con il logger eventi collegato a Supabase vero. Nessuna riga in `trades`.

**Fare:** confermare che sono i test; mockare il logger eventi (e qualunque altro scrittore Supabase) nella suite, così i test non toccano mai il database di produzione; verificare che `trades`, `config_changes_log`, `bot_runtime_state`, `bot_state_snapshots` non abbiano righe di test; cancellare le ~15 righe `TEST/*` e `BTC/USDT` del 28-set dal registro (elencarle nel report prima di cancellare). Se in passato è già successo (altre date con `TEST/`), contarle e dirlo, non cancellarle senza ok.

## 3. Riconciliazione dei conteggi (lettura)

A.1 dice **62 operazioni** nei 2 mesi; R.1 (27-set) **65 ordini su 65**; l'addendum Q2 **64 ordini + 2 di prova** di luglio. Una tabella che spieghi le tre cifre (finestra, ordini di prova, ordini dopo il 27-set, eventuali doppi). Nessuna correzione: serve solo che i tre numeri si parlino, perché la riconciliazione è la base di fiducia dei report.

---

**Decisioni delegate:** come mockare (fixture, variabile d'ambiente, altro), purché il default della suite sia "nessuna scrittura remota".
**Da chiedere:** qualunque azione sul TF; cancellazioni oltre le righe del 28-set.

**Auto-obiezione:** nessuna. Punti 1 e 3 sono verifiche di lettura, il punto 2 è un fix meccanico con scope ovvio.
