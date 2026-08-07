# Report S125 — kraken-fase3-execution — 2026-08-07

**Da:** CC · **A:** CEO
**Brief sorgente:** `briefresolved.md/2026-08-07_S125_brief_kraken-fase3-execution.md`
**Commit:** `fff8cc7` → `c63b829` (esecuzione bot) · rollback in `config/2026-08-07_S125_rollback_pre-cutover.md`
**Esito:** ✅ **ESEGUITO**, tutte le verifiche §5 passate. Due restart (13:00 e 20:10 UTC).

---

## 1. In due righe

Il sistema gira **solo su denaro reale**. BTC/USD a $250, SOL/USD nuovo a $150, i quattro grid Binance spenti, il Trend Follower fermo. Capitale sul conto verificato prima di scrivere: **$452,47 liberi su $551,15 di equity**, contro $302,23 necessari — cuscino di $150.

Nessuna modifica al comportamento dei bot, come chiedeva il §0 del brief. L'unica variabile cambiata è l'exchange.

---

## 2. Verifiche del §5

| Verifica | Esito |
|---|---|
| 2 grid Kraken + Sentinel + Sherpa, niente TF né Binance | ✅ `Brain flags: TF=False` |
| ETH non resuscitato | ✅ `[RECONCILER] No TF orphans detected` — filtro `managed_by='tf'` riconfermato prima di procedere |
| Primo tick di entrambi i grid | ✅ stato ricostruito da DB |
| BTC/USD cassa ~$152 | ✅ **$151,44** (`$250 − $98,56`) |
| BTC/USD holdings e costo medio invariati | ✅ `0,00152221` · avg **$64.745,65** |
| Nessun ordine su Binance dopo lo spegnimento | ✅ zero trade a DB |
| Report serale coerente | ⚠️ **no — vedi §5** |
| Sherpa a T+24h | ⏳ 8 agosto |

---

## 3. Il fatto nuovo: SOL ha comprato prima del riavvio

**10:55:47 UTC** — 90 secondi dopo l'inserimento della riga, prima del restart previsto dal Passo 4:

> BUY **0,272183 SOL @ $73,48**, costo $20,00, fee **$0,1600**, ordine `OJWTJ4-JGLUJ-OX7UKT`

Era la prima entrata, libera per disegno. Il brief metteva il Passo 3 prima del riavvio e l'orchestratore rilegge le righe ogni 30 secondi: il bot ha fatto quello che doveva. **Ma il primo dollaro reale su SOL è uscito su codice vecchio**, e il "primo tick su codice pulito" che il brief immaginava di osservare non è mai esistito. Nessuna conseguenza — lo stato è stato ricostruito correttamente al restart — ma va detto invece che lasciato intendere.

**Il dato che vale**: fee $0,1600 su $20,00 = **0,8001%**. Lo 0,80% tier-0 è confermato al centesimo su una **seconda moneta**, indipendentemente da BTC.

---

## 4. Risposta anticipata alla tua auto-obiezione su SOL

Scrivevi: *"SOL parte con parametri mai testati su questo venue… è il punto del piano con meno evidenza sotto. Chiedo che il primo ciclo venga guardato con attenzione."*

In sei ore Sherpa ha risposto da solo, tre volte (15:05, 16:06, 17:07):

| | all'inserimento | a fine giornata |
|---|---|---|
| `buy_pct` | 2,25 | **2,45** |
| `sell_pct` | 1,50 | **1,63** |
| `stop_buy_drawdown_pct` | 3 | **4** |
| `dead_zone_hours` | 2 | **1** |

**BTC/USD è rimasto fermo su 1,80 / 1,20.** Sherpa sta dicendo che i parametri copiati da Binance erano **troppo stretti per SOL** e li sta allargando in entrambe le direzioni. Non è una prova che abbia ragione; è il sistema che fa il suo mestiere invece di stare fermo.

**Da tenere d'occhio**: con `sell_pct` a 1,63 e lo 0,80% di commissione, SOL deve salire **~2,5% sopra il costo medio** per vendere. Se Sherpa continua ad allargare, il primo ciclo si allontana — che è il contrario di quello che serve per avere dati.

---

## 5. Il difetto che il §6 del tuo brief non poteva prevedere

Segnalavi `last_trade_at` negli snapshot come "cosmetico, da mettere in coda". Corretto, ed è in coda. Ma nella stessa area c'era qualcosa di peggio, trovato solo perché Max ha guardato un grafico:

**Il report serale delle 20:00 ha misurato il portafoglio testnet MORTO** — `initial_capital $500`, `total_value $539,54` — e lo ha archiviato come snapshot del giorno. Tre cause a catena, tutte figlie dello stesso pin `venue='binance'` che a luglio era la scelta giusta.

E una quarta, indipendente: `daily_pnl` ha `UNIQUE(date)`, cioè **una riga al giorno per tutto il sistema**. Dal 22 luglio al 6 agosto un grid Binance arrivava sempre primo e lo snapshot del bot Kraken veniva scartato in silenzio. **Ventun giorni di storia del denaro reale non sono mai stati registrati e non tornano.**

Tutto corretto in giornata (commit `265e8eb`, `520a637`), restart, report rimandato coi numeri veri, prima riga `daily_pnl` Kraken scritta. Dettaglio nel report `real-money-reveal`.

---

## 6. Decisions

**DECISIONE:** eseguire il cutover in finestra unica, con `disclaimer_mode=true` acceso *prima* di spegnere i grid Binance.
**RAZIONALE:** le superfici pubbliche filtravano su `venue='binance' AND is_active=true`; spegnendo le righe quella query torna zero e il sito sarebbe rimasto congelato sul ciclo testnet — 255 ordini di denaro simulato sotto etichetta "denaro reale". Non una vetrina vuota: una piena con la targa sbagliata.
**ALTERNATIVE:** spegnere prima e sistemare il sito dopo (scartata: finestra di incoerenza pubblica non controllata).
**FALLBACK:** `config/2026-08-07_S125_rollback_pre-cutover.md` — snapshot + query inverse; accendere/spegnere righe non richiede restart.

**DECISIONE:** lasciare `SHERPA_TELEGRAM_ENABLED=true` a entrambi i restart.
**RAZIONALE:** PROJECT_STATE lo dava "da togliere a un restart futuro" e questi lo erano, ma il §0 del tuo brief impone che l'unica variabile della finestra sia l'exchange. Segnalato, non fatto.
**FALLBACK:** un flag in meno al prossimo restart.

---

## 7. Obiezione preventiva, per la prossima volta

Il brief diceva *"capitale su Kraken ≥ $400"*. È ambiguo: $400 **in aggiunta** ai $100 già investiti, o saldo portato **a** $400? Con $97,77 già dentro BTC servivano ~$302 di **USD liberi**, cioè ~$400 di equity totale. Max aveva versato abbondantemente e il punto è rimasto teorico — ma se avesse portato il saldo *a* $400 saremmo stati esatti al centesimo, e il primo ordine che sfora si prende un rifiuto dall'exchange.

Nei prossimi brief con soglie di capitale: specificare se la cifra è **equity totale** o **cassa libera**. Sono due numeri diversi e la differenza è esattamente quanto c'è già dentro il mercato.
