# Report per il CEO — Reset testnet & decisione su BONK

**Da:** CC (Claude Code, Intern)
**A:** CEO (Claude, Projects) + Max (Board)
**Data:** 2026-06-04
**Sessione:** S96
**Priorità:** 🟠 Decisione richiesta (gate Max+CEO, guardia 72a)
**Commit di riferimento:** `722da6a` (fix orchestrator), `5520625` (HEAD origin/main)

---

## 0. TL;DR

Durante un riavvio del Mac Mini (update macchina), la **testnet Binance ha eseguito il suo reset mensile** azzerando lo storico dei wallet. Conseguenze:

- **SOL e BTC** sono ripartiti da soli (il reset gli ha dato *più* coin del previsto → la guardia li lascia passare e sincronizza).
- **BONK è bloccato**: il DB crede di possedere **21.596.414 BONK**, il wallet resettato ne ha **18.446** (−99,91%). La guardia 72a (decisione Max+CEO 2026-05-11) **rifiuta di avviarlo** perché ogni vendita verrebbe respinta dall'exchange.
- Indagando, ho trovato e **corretto un bug dell'orchestrator** che generava spam infinito su Telegram (ri-spawnava BONK all'infinito invece di fermarsi dopo 5 tentativi). Fix committato e live.

**La diagnosi è chiusa e benigna** (reconcile: 0 drift, 0 ordini orfani — nessun furto, nessuna corruzione, solo il reset). **Resta una sola decisione, ed è strategica, non tecnica:** come gestiamo BONK, dato che Max **non vuole** allineare il DB al valore Binance (18.446) perché cancellerebbe un mese di storia di accumulo.

---

## 1. Cosa è successo (timeline)

1. Su richiesta di Max ho fermato tutti i bot per permettere update/riavvio del Mac Mini.
2. Al riavvio, l'orchestrator è ripartito e ha rilanciato i bot. SOL/BTC/TF/Sentinel/Sherpa OK.
3. **BONK è uscito con codice 1** e la guardia di boot 72a ha rifiutato l'avvio (vedi §3).
4. L'orchestrator ha ritentato 5 volte, ha loggato *"Giving up"*, **ma poi ha ricominciato il ciclo** → spam Telegram continuo (vedi §4).
5. Indagine read-only (`reconcile_binance.py`) → **confermato reset mensile testnet** (vedi §2).
6. Fix del bug orchestrator + riavvio pulito → spam fermato in modo permanente (vedi §4).
7. Commit + push del fix e delle modifiche doc di Max; repo allineato su tutte le macchine.

---

## 2. Il reset testnet in dettaglio

La testnet Binance resetta i saldi ~1 volta al mese senza preavviso (fatto noto, lato server Binance). Stavolta è capitato durante l'update del Mac Mini — pura coincidenza, le due cose sono indipendenti.

**Wallet testnet dopo il reset** (rilevato live):

| Asset | Wallet post-reset | Note |
|-------|-------------------|------|
| USDT  | **10.000,00** | seed fresco |
| BTC   | 1,0 | baseline |
| SOL   | 6,0 | baseline |
| BONK  | 18.446 | baseline (≈ il "regalo iniziale" testnet storico) |

**Confronto con ciò che il DB credeva** (replay dei trade v3/grid):

| Coin | DB credeva | Wallet reale | Gap | Esito guardia |
|------|-----------|--------------|-----|---------------|
| SOL  | 1,59 | 6,0 | **+4,41 (surplus)** | ✅ parte, sincronizza |
| BTC  | 0,0025 | 1,0 | **+0,9975 (surplus)** | ✅ parte, sincronizza |
| BONK | 21.596.414 | 18.446 | **−21.577.968 (deficit −99,91%)** | ⛔ **bloccato** |

**L'asimmetria è voluta** (Max 2026-05-11): se il wallet ha *più* coin del previsto (surplus), è innocuo → il bot adotta il saldo reale e prosegue. Se ne ha *meno* (deficit), come BONK, ogni vendita futura verrebbe respinta → la guardia rifiuta l'avvio e chiede intervento umano.

**Verifica anti-allarme** — `reconcile_binance.py` (dry-run, read-only) su tutte le coin:

```
BTC/USDT   WARN_BINANCE_EMPTY   matched=0  drift=0  binance_orphan=0  db_legacy=18
SOL/USDT   WARN_BINANCE_EMPTY   matched=0  drift=0  binance_orphan=0  db_legacy=17
BONK/USDT  WARN_BINANCE_EMPTY   matched=0  drift=0  binance_orphan=0  db_legacy=25
```

`WARN_BINANCE_EMPTY` = Binance restituisce 0 fill (storico azzerato). **0 drift, 0 ordini orfani** = nessun sell non tracciato, nessun trasferimento sospetto, nessuna corruzione DB. È esclusivamente il reset. I trade nel DB sono correttamente marcati *pre-reset legacy*.

---

## 3. Lo stato di BONK nel DB (cosa stiamo "perdendo")

Dallo state restore al boot:

- **Holdings:** 21.596.413,96 BONK
- **Avg buy price:** $0,00000725
- **Realized P&L storico:** $8,2622
- **Ultimo buy:** $0,00000679
- **Cash:** $150 allocati − $381,21 investiti + $233,37 venduti − $2,70 reserve = **−$0,54 disponibili**
- **Valore nozionale** di quei 21,6M BONK al prezzo attuale (~$0,00000488): **≈ $105**
- Valore del wallet resettato (18.446 BONK): **≈ $0,09**

Questo è il punto di Max: 21,6M BONK ≈ $105 sono **un mese di accumulo grid** — una *storia*. Allinearli a 18.446 ≈ $0,09 butta via quella storia.

**La verità tecnica da mettere sul tavolo, però:** quei 21,6M BONK **non esistono più sull'exchange**. Sono spariti col reset lato Binance. Il numero nel DB è ormai un *fantasma contabile*: non corrisponde a nulla di reale e non potrà mai essere venduto. Finché resta lì, la guardia bloccherà BONK a ogni avvio.

---

## 4. Il bug dell'orchestrator (trovato e risolto — per completezza)

Mentre BONK era bloccato, l'orchestrator ha iniziato a spammare Telegram con messaggi "BONK restarted (attempt X/5)" → "crashed 5 times, giving up" → **e poi ricominciava da capo all'infinito**.

**Causa:** quando un grid bot esauriva i 5 tentativi, veniva settato `gave_up=True`, ma al poll successivo il processo morto finiva nel ramo `else` che **cancellava il tracking** del bot; la sezione successiva ("avvia i symbol attivi non tracciati") lo **ri-spawnava da zero** (contatore e flag azzerati). Loop infinito + spam.

C'era anche un secondo innesco: il **reconciler orphan** riforza `is_active=True` su BONK perché ha holdings residue nel DB, contribuendo al respawn.

**Fix:** un guard che intercetta il processo morto già "arreso" *prima* dei rami di cancellazione/respawn — l'entry resta tracciata e silenziosa.

```python
if info.process.poll() is None:
    continue  # still alive
if info.gave_up:
    continue  # già arreso: resta tracciato, niente respawn/re-log, niente spam
```

**Verificato live:** dopo il fix BONK ha fatto 5 tentativi → "Giving up" → **oltre 5 minuti di silenzio totale, zero respawn**. Spam chiuso. Commit `722da6a` su `main`, già in esecuzione (PID orchestrator 11333).

> Nota: finché BONK non viene risolto (§5), ogni riavvio dell'orchestrator produrrà *un* burst da 5 messaggi e poi silenzio. È il comportamento atteso ("manual intervention needed").

---

## 5. La decisione: come gestiamo BONK

Max ha posto un vincolo chiaro: **non vuole l'Opzione A** (allineare il DB a 18.446). Riporto comunque tutte le opzioni con i trade-off, perché la scelta è Board+CEO.

### Opzione A — Rebase al wallet (allinea DB a 18.446)
*Tecnicamente la più pulita.* Si archiviano i 25 trade legacy, BONK riparte fresh su 18.446 come hanno fatto SOL/BTC. **→ Posta in veto da Max** (cancella la storia di accumulo). La cito per completezza.

### Opzione B — Ricostruire la posizione (rebuy a mercato)
Con i 10.000 USDT freschi del wallet, ricompriamo ~21,58M BONK a mercato per riportare il wallet ad allinearsi al DB (≈$105, banale). BONK riparte, la guardia passa, **l'avg-cost e la continuità sono preservati**.
- ✅ Preserva la continuità che Max vuole.
- ⚠️ **Wrinkle contabile:** è una ricostruzione *manuale*. Il buy reale entra in Binance ma non nel DB (sarebbe un orfano al prossimo reconcile) → va documentato; oppure lo si registra come trade e allora l'avg-cost si sposta verso il prezzo attuale ($0,00000488 vs $0,00000725 attuale). Da decidere QUALE versione.
- ⚠️ Resta una finzione: la posizione "vera" era stata azzerata.

### Opzione C — Clean Slate completo (come brief 66a)
Snapshot narrativo dello stato pre-reset → reset **di tutti e 3** i bot sulla nuova baseline testnet → si riparte da zero, con la storia pre-reset archiviata nel diario/Volume come capitolo chiuso.
- ✅ Coerente e onesto: anche SOL/BTC sono in stato post-reset misto (portano surplus phantom 6 SOL / 1 BTC). Un reset uniforme chiude il cerchio per tutto il portafoglio.
- ✅ Ottimo materiale narrativo ("la testnet ci ha resettato, ripartiamo — un vero bagholder").
- ⚠️ Butta via anche la continuità di SOL/BTC, non solo BONK.

### Opzione D — Lasciare BONK fermo (status quo)
Si gira a 2 grid (SOL/BTC) + TF finché non si decide. Nessuna perdita operativa (è paper). BONK resta giù, silenzioso (grazie al fix §4).
- ✅ Zero rischi, decisione rimandabile a mente fredda.
- ⚠️ Portafoglio a 2/3 grid; il fantasma DB resta.

### Considerazione trasversale (importante)
**La testnet resetta ~ogni mese.** Qualunque cosa decidiamo è temporanea finché restiamo su testnet: al prossimo reset succederà di nuovo, potenzialmente su tutte le coin. Forse la vera domanda strategica non è "come salviamo *questo* BONK" ma **"che policy adottiamo per i reset mensili"** (es. snapshot automatico pre-reset + ripartenza standardizzata). Questo si lega a `story_is_process_not_numbers`: il prodotto è il processo, e un reset onestamente raccontato *è* processo.

---

## 6. Raccomandazione di CC (con obiezione)

**Obiezione tecnica all'istinto "preserviamo i 21,6M":** quei token non esistono più sull'exchange. Tenerli nel DB significa convivere con un fantasma che (a) blocca la guardia a ogni avvio, (b) rende i numeri di BONK non riconciliabili con la realtà, (c) verrà comunque spazzato via al prossimo reset mensile. Preservarli è preservare una finzione.

**La mia raccomandazione:** dato che il valore in gioco è simbolico ($105 paper) e che il brand stesso è "BagHolder", **l'Opzione C (clean slate raccontato)** è la più onesta e la più forte narrativamente — il reset diventa un capitolo del diario, non un problema da nascondere. Se invece la priorità è non interrompere la serie storica di BONK *adesso*, l'**Opzione B** è fattibile subito, accettando il wrinkle contabile da documentare.

**Sconsiglio** di restare a lungo in Opzione D senza decidere: il fantasma e il rischio di spam a ogni restart restano.

**Fallback se sbagliassimo:** ogni opzione è reversibile — snapshot pre-reset preservato, e comunque è paper trading. Nessun capitale reale a rischio.

---

## 7. Domande precise per il CEO

1. **Quale opzione** per BONK: A / B / C / D?
2. Se **B**: registriamo il rebuy come trade (avg-cost si sposta) o come top-up manuale documentato (avg-cost storico preservato)?
3. Vogliamo definire una **policy permanente per i reset mensili testnet** (snapshot automatico + ripartenza standard), così la prossima volta non serve una decisione ad-hoc?
4. Coinvolgiamo SOL/BTC nella decisione (sono anch'essi post-reset con surplus phantom) o li lasciamo proseguire come stanno?

---

## 8. Stato del sistema adesso

| Componente | Stato |
|---|---|
| Orchestrator (patchato, PID 11333) | ✅ attivo |
| Grid SOL / BTC | ✅ attivi |
| Grid **BONK** | ⛔ fermo (guardia 72a) — **non spamma più** |
| Trend Follower | ✅ attivo |
| Sentinel / Sherpa (dry_run) | ✅ attivi |
| NewsKeeper | ✅ attivo |
| x_poster_approve + 3 cron | ✅ attivi/schedulati |
| Repo (Mac Mini / origin / MacBook Air) | ✅ allineati su `5520625` |

---

## 9. Riferimenti

- Guardia boot: `bot/grid/state_manager.py` `_reconcile_holdings_against_exchange` (brief 72a, Max+CEO 2026-05-11)
- Fix orchestrator: `bot/orchestrator.py` sezione reconcile grid bots — commit `722da6a`
- Tool diagnosi: `scripts/reconcile_binance.py` (dry-run read-only)
- Precedente reset totale: `briefresolved.md/brief_66a_operation_clean_slate.md`
- Reset mensile testnet: nota nota (orizzonte P&L ~30 giorni)
