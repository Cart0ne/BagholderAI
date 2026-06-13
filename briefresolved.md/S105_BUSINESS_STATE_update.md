# Aggiornamento BUSINESS_STATE.md — S105 (2026-06-13)

> Da incollare nel file. Aggiorno SOLO le sezioni cambiate.
> ⚠️ Allineamento: BUSINESS_STATE in PK era fermo a S103; in DB S104 è già COMPLETE.
> Aggiornare l'header a S105 e recuperare l'eventuale buco S104 (vedi nota in fondo).

---

## Header (sostituire)

**Last updated:** 2026-06-13 — Session 105 (SOL grid frozen by dust → grid re-entry logic fix, commit `87eeda9`). Cap file 50KB. Prec.: S104 (Volume-PnL debunking + "The Experiment" income page).
**Updated by:** CEO (update S105) — da applicare da CC
**Basato su:** PROJECT_STATE.md (verificare allineamento: era S103, DB a S104+)

---

## §4 — Decisioni strategiche recenti (aggiungere in cima, formato: data — decisione — why)

- **2026-06-13 (S105) — dust write-off de-parcheggiato + soglia = minimo vendibile Binance, non epsilon arbitrario**.
  DECISIONE: la logica "posizione vs polvere" passa da un confronto col letterale `0` / soglia `$0,50` hardcoded a un predicato unico `is_dust(holdings, price, filters)` basato sul minimo vendibile reale di Binance (`LOT_SIZE`/`NOTIONAL`), usato a TUTTI i gate posizione-vs-polvere della griglia (~6 punti). Il `$0,50` di `state_manager` è eliminato dalla logica primaria e tenuto solo come fallback no-filtri. Commit `87eeda9`, 228 test verdi, reversibile (no migration). TF fuori scope.
  RAZIONALE: una polvere di 0,000096 SOL (~$0,006) ha congelato la griglia SOL per ~5 giorni disinnescando il re-entry forzato, in silenzio (nessun ERROR/alert), durante la finestra di osservazione Sherpa che ci serve pulita. Il fix era parcheggiato come "pre-mainnet, bassa priorità" — classificazione smentita dai fatti. GATE A2 (copertura BONK del fix S73) verificato VERDE prima di rimuovere il `$0,50`.
  ALTERNATIVE SCARTATE: (C iniziale CEO) epsilon arbitrario + write-off + difesa in profondità → sovra-ingegnerizzata; (floor `max($0,50, min_sellable)` permanente) → ridondante, il predicato già domina. FALLBACK: revert `87eeda9`.
  ANTI-ASSENSO §4: CC ha contestato il brief CEO su 3 punti (predicato già esistente / incoerenza soglie `$0,50` vs `$5` non vista dal CEO / ~6+6 punti non 3). CEO ha accettato tutte e 3, addendum prodotto. Nodo di sintesi: nessuna escalation, convergenza raggiunta.

---

## §3 — Diary status (sostituire la riga corrente)

- Volume corrente pubblico: V3 "From Brain to Eyes" (live). V4 in lavorazione.
- Ultima entry diary: **S105** "The One Where the Bot Held Out for SOL at $52,000" (dust/SOL grid freeze).
- Prossimo check di congruenza diary: invariato.

---

## §5 — Domande aperte per CC (idee tech non ancora pronte per brief)

- **Monitor "griglia silenziosa"** (candidato brief): alert quando una griglia non registra trade da X ore. Nasce dal buco di osservabilità S105 — un bot fermo non emette ERROR né Telegram, SOL è rimasta morta 5 giorni invisibile. Il fix dust impedisce *questo* freeze, non la classe generale. Trigger: prossima sessione di lavoro o pre-mainnet. (DA DECIDERE con Max se parcheggiare in Apple Notes o aprire brief.)
- **Caso degradato no-filtri**: se `fetch_filters` fallisce al boot, il bot gira col fallback `$0,50` < minNotional reale → un residuo in [$0,50, $5) potrebbe ri-congelarsi in quella finestra. Valutare se in quel caso il bot debba allertare invece di operare con soglia errata. (Collegato al monitor sopra.)

---

## NOTA allineamento state file (azione richiesta)

BUSINESS_STATE.md in PK risultava "Last updated S103", ma in DB `diary_entries` S104 è già COMPLETE.
→ Verificare se l'update BUSINESS_STATE di S104 (Volume-PnL debunking + "The Experiment" + expense mapping €274 + Substack active) è stato applicato al file. Se NO, recuperarlo PRIMA di applicare questo blocco S105, altrimenti la storia S104 resta solo in DB e diary, non nello state file.
