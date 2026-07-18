Brief S119c — business-state-update — 2026-07-17

**Tipo:** aggiornamento `BUSINESS_STATE.md` su **istruzione esplicita del CEO** (CLAUDE.md §2b).
**Scope:** solo `BUSINESS_STATE.md`. Nessun codice, nessun restart, nessun ordine, nessun DB.
**Push:** diretto su main.

> **Prima di scrivere:** se il file è oltre **50KB** (tolleranza ±2KB), **NON compattare di iniziativa** — segnalalo a Max e aspetta. Regola CLAUDE.md §2b.

---

## §1 Header

`Last updated:` 2026-07-17 — S119 chiusura (primo ordine reale su Kraken; indagine S119b; nodo 5 rinviato a pre-2b)
`Basato su:` PROJECT_STATE.md corrente + `config/2026-07-16_S119_RforCEO_kraken-fase2a.md` + `config/2026-07-17_S119b_RforCEO_kraken-replay-avg-reconcile.md`

## §2 Marketing in-flight — aggiungi

- **Primo click organico da Google (17-lug).** GSC 3 mesi: **1 click · 417 impressioni · posizione media 15,1 · CTR 0,2%**. È il primo in assoluto. Lettura onesta: da pagina 2 lo 0,2% è il CTR atteso — il click dice più di chi ha scrollato che di noi. **Ma è il secondo strumento indipendente** che conferma la diagnosi S116: Payhip 247 view / 0 checkout, Google 417 impressioni / 1 click. Due misure, una diagnosi: **non arriva nessuno**. Il buco è a monte, non nel prodotto.
- **Nessun annuncio del test da $25** (vedi §4). Deroga alla regola no-post-ven/sab/dom: **valutata e non usata**.

## §3 Diary status — aggiorna

- **S119 COMPLETE** — *"The One Where Everyone's Numbers Were Wrong"* (13–17 luglio). `.docx` prodotto, `diary_entries` aggiornata dal CEO via MCP.
- Volume 4 "From Eyes to Live": l'arco è passato dalla porta. S119 è il primo denaro reale.

## §4 Decisioni strategiche recenti — aggiungi in cima (formato data — decisione — why)

| Data | Decisione | Perché |
|---|---|---|
| 2026-07-17 (S119) | **Primo ordine reale eseguito** — $25 BTC/USD su Kraken, riga isolata `is_active=false` + `KRAKEN_TEST_MODE`, sorvegliato. `OCILGP-2GRMI-D3WSNK`: 0,00039379 BTC @ $63.483,50, costo $24,99917, fee $0,19999 USD | `fill confirmed via fetch_order after 3.1s` = **il fix critico S119 in azione**: un solo BUY, nessun loop. Kraken non ha testnet → il fix poteva essere certificato **solo** da denaro vero; 297 test verdi non bastavano. Tripla conferma incrociata log / API Kraken / DB. **Fee live 0,7999% = tier EU 0,80% confermata** (chiude l'errore CEO di S117). **Fase 2a resta APERTA**: un buy è mezzo ciclo, serve un SELL registrato |
| 2026-07-17 (S119) | **Funding path corretto: deposito EUR → conversione manuale EUR→USD → trading /USD** | I "$100" caricati erano **€97,80**. Le coppie `/USD` si tradano solo con USD reali sul conto: il toggle EUR/USD dell'interfaccia Kraken è una **vista**, non converte l'asset. Scoperto sul campo, non nel design. Costo: spread di conversione ad ogni rabbocco. **Va nel runbook Fase 2b** |
| 2026-07-17 (S119) | **Nessun annuncio pubblico del test da $25 — la carta "primo denaro reale" resta per il collaudo** | `COLLAUDO_COMMS_GUIDELINES` §1: la milestone si gioca **una volta sola**. Il test è Fase 2a su una riga che il sito pubblico non vede; il collaudo è Fase 3 ($100, K.3 shippato, badge "real money, real Kraken"). Annunciare ora brucia la carta e contraddice una homepage pinnata a `venue=binance` → incoerenza narrazione↔codice (territorio audit Area 2) |
| 2026-07-17 (S119) | **Status line pubblica corretta** (non "aggiornata"): da *"Phase 1 wired, still asleep · before any real trade"* a *"One supervised $25 order on Kraken · real money, real fill, no loop · the sell hasn't come yet"* 🔬 | Alle 18:45 la riga precedente è diventata **falsa** sulla superficie più pubblica del progetto. Il post è opzionale, la verità del badge no. Distinzione: **push** (annuncio, rivendica) vs **cronaca** (dice dove siamo). **Nessuna automazione**: quando il SELL arriva la riga torna falsa, va rifatta a mano |
| 2026-07-17 (S119) | **Trigger SELL reale = ~$65.271** (avg fee-inclusive × 1,02), **non $64.753**. Margine netto a target ≈ **+1,19% ≈ $0,30** su $25 | Il codice include la fee di buy nell'avg (`buy_pipeline.py:304`, `cost_for_avg = cost + fee`). Il **report S119 di CC** citava il prezzo puro → sbagliato; il **runbook §4** era corretto. Trovato dal cross-check del CEO; risolto dall'indagine S119b — che ha poi demolito anche il calcolo del CEO (0,39% ≈ $0,10). **Il SELL è più lontano di quanto si credeva**, non più vicino |
| 2026-07-17 (S119) | **Nodo 5 (margine floor) rinviato a PRIMA della Fase 2b, non durante** | CC ha trovato che il floor **doppia-conta la fee di buy**: `min_price = avg × (1 + min_profit + 2×fee)` mentre l'avg include già 1× fee → floor a avg×1,016 contro un break-even reale di avg×1,008. **Sovra-protettivo di ~0,8%**, non pericoloso, ma blocca vendite già in utile netto. Il margine si sceglie **sopra il break-even vero**: la formula va corretta prima di tararlo |
| 2026-07-17 (S119) | **Riavvio del processo di test: sicuro INCONDIZIONATAMENTE** (non prezzo-dipendente) | Tre gate indipendenti: replay sano (trova il trade su `symbol`+`v3`+`cycle`) · reconcile Kraken corretto (interroga Kraken, "Binance" è solo un'etichetta hardcoded) · **capitale esaurito** (`_available_cash` clampato a $0 < $5 min) → nessun DCA a nessun prezzo. Il caveat "$63.293" del corpo del report S119b è **superato per concessione di CC** dopo obiezione del CEO |

## §5 Domande aperte per CC — aggiungi

| Tema | Stato | Note |
|---|---|---|
| **[S119 NEW] `trades` non ha colonna `venue`** | 🆕 Da valutare — fase sistema-pieno | La separazione Kraken ↔ testnet regge **solo** su `cycle` (`kraken_test` vs `testnet_2`) + il simbolo (`BTC/USD` vs `BTC/USDT`). Funziona oggi. Ma è **accoppiamento implicito**, ed è la stessa famiglia dei bug che ci hanno già morso due volte: cycle-fetch (S118 🟠) e superfici sito non-venue-robuste (S119 🟠). Valutare colonna `venue` esplicita quando Kraken passa a 3 monete. **Non blocca la 2b** |

## §6 Vincoli / deadline — aggiungi

- **Fase 2a APERTA** finché un SELL reale non è registrato correttamente. Trigger ~$65.271. Nessuna vendita forzata: vendere a mano su Kraken **non** valida il criterio (il test è "il bot registra", non "esiste una vendita").
- **Non cancellare** la riga `bot_config` `BTC/USD`/`kraken` finché il ciclo è aperto (il runbook §7.3 lo propone: **sospeso**). Cancellarla con $25 di BTC in pancia orfaneggia la posizione.

## §7 Cosa NON sta succedendo e perché — aggiungi

- **Nessun post pubblico sul primo ordine reale.** Non è prudenza: è che la milestone si annuncia al collaudo, con il sito allineato. Oggi diventerà la **prova di rigore** dentro quel post ("prima dei $100 ne abbiamo messi 25, uno solo, guardato a mano"), non una notizia autonoma.
- **Fase 2b ferma** in attesa del SELL + nodo 5.

---

## Brief separati pending (NON eseguirli qui — solo annotali dove serve)

1. **Correzione del report S119** — il numero del trigger ($64.753 → ~$65.271).
2. **Revisione del floor** — la formula che doppia-conta la fee (dentro il nodo 5).
3. **Micro-fix etichetta reconcile** — `state_manager.py:339` e `:417` dicono "Binance" su venue kraken. LOW cosmetico, PROJECT_STATE §5.

## Auto-obiezione del CEO (anti-assenso)

Sette voci in §4 per una sessione sola sono tante, e il rischio è **inflazione del log**: se ogni sessione ne scrive sette, la sezione va in compaction ogni tre settimane e le decisioni che contano affogano nel rumore. Le due che pesano davvero sono il **funding EUR→USD** (cambia una procedura) e il **nodo 5 anticipato** (cambia una sequenza). Le altre cinque sono cronaca.

**Perché le tengo lo stesso:** questa è la sessione del **primo denaro reale**. Se c'è una sessione che merita una traccia sovradimensionata, è quella in cui il progetto ha smesso di essere una simulazione. La compaction avrà il buon gusto di riconoscerlo.

**Se non sei d'accordo, dillo prima di scrivere** — non dopo.

## Obbligo di obiezione (CC)

Almeno una obiezione reale prima di applicare. Se una voce è imprecisa, ridondante o va in una sezione diversa da quella che ho scelto, argomentala. "Nessuna obiezione" è accettabile **solo** se motivata (è un update di documentazione, non di codice: la branca "scope ovvio" è ammessa).

## Output

`config/2026-07-17_S119c_RforCEO_business-state-update.md` — SCOPE identico, push diretto su main.
