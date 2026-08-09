# Report per il CEO — recap S123/S124 + le prime 48h di Kraken a regime

**Da:** CC · **A:** CEO · **Data:** 2026-08-09
**Natura:** ricostruzione richiesta da Max (*"cosa abbiamo fatto in S123 e S124"*) + le prime osservazioni sul sistema dopo il cutover del 7 agosto.
**Non nasce da un brief**, quindi non ha uno SCOPE da accoppiare.

---

## 0. La notizia, prima del recap

**SOL ha chiuso il suo primo ciclo completo a denaro reale. In 27 ore.**

| Quando | Cosa |
|---|---|
| 7 ago 10:55 UTC | BUY 0,272183 SOL @ **$73,48** — prima entrata, 90 secondi dopo l'apertura della riga |
| 8 ago 14:35 UTC | **SELL @ $76,00** → **+$0,36 netto di commissioni** |
| 8 ago 16:35 UTC | Rientrata @ $76,22, due ore dopo |

È il **secondo giro completo** mai chiuso con soldi veri, dopo quello di BTC in Fase 2a (+$0,71 il 21 luglio).

Nel tuo brief S125b avevi scritto: *"se il reveal esce e la prima settimana di denaro reale non produce un ciclo, il sito lo mostrerà. Va detto in faccia a chi decide."* Era l'obiezione giusta da fare. **La risposta è arrivata il giorno dopo il reveal**, e il sito mostra un ciclo chiuso invece di una posizione ferma.

E la serie giornaliera, che fino al 7 agosto non esisteva: **7 ago $400,68 → 8 ago $401,43**. Il grafico §2 della dashboard non è più una scala a tre gradini.

---

## 1. Verifica T+24h su Sherpa — dovuta l'8 agosto, la faccio ora

Il brief chiedeva di controllare che Sherpa non riscrivesse i parametri delle righe Kraken "in modo inatteso". Il dato, dal registro delle modifiche:

| Parametro (SOL/USD) | Riscritture in 48h | All'apertura | Adesso |
|---|---|---|---|
| `buy_pct` | **21** | 2,25 | **2,67** |
| `sell_pct` | **18** | 1,50 | **1,78** |
| `stop_buy_drawdown_pct` | 2 | 3 | 5 |
| `dead_zone_hours` | 1 | 2 | 1 |

**BTC/USD è rimasto fermo su 1,80 / 1,20** per buy e sell — Sherpa gli ha toccato solo le protezioni.

**Lettura.** Non è "inatteso" nel senso di rotto: ogni singola riscrittura è piccola (il tetto del ±30% per tick rende ogni transizione graduale) ed è il comportamento previsto dal disegno. Ma **39 riscritture in due giorni su una moneta sola, tutte nella stessa direzione**, dicono una cosa precisa: Sherpa considera i parametri copiati da Binance **troppo stretti per SOL su questo venue**, e continua ad allargarli.

**La tua auto-obiezione era fondata** (*"SOL parte con parametri mai testati su questo venue, è il punto del piano con meno evidenza sotto"*), e la macchina ti ha dato ragione da sola in 48 ore.

**Il rischio che segnalo.** Con `sell_pct` a 1,78 più lo 0,80% di commissione, SOL deve ora salire **~2,68% sopra il costo medio** per vendere — contro il ~2,3% di due giorni fa. Se l'allargamento continua, il prossimo ciclo si allontana. Non è un guasto: è un ago che si muove e va guardato. Se fra una settimana `sell_pct` è a 2,2 senza che sia arrivato un ciclo, vale la pena chiedersi se il tetto del clamp Sherpa sia tarato per un venue allo 0,80%.

---

## 2. Recap S123 (23-24 luglio) — non era una sessione di micro-fix

Max chiedeva se in PROJECT_STATE ci fosse una riga per S123. **Non c'è mai stata come riga propria**: S123 è sempre stata dentro una riga cumulativa `2026-07-22 → 07-24` insieme a S122, e oggi ho compattato anche quella in archivio. Ma la sessione ha prodotto lavoro sostanziale, non ritocchi.

**Cosa ha fatto** (commit `0a9d21b`, `d76a4bf`, `74cc240`):

- **Post evergreen sul costo di costruzione del progetto**, pubblicato. È il pezzo che risponde alla domanda che la gente cerca davvero ("quanto costa costruirsi un bot con Claude") invece di quella che ci piacerebbe le facessero.
- **Infrastruttura `liveFigures`**: le cifre dentro quel post **si leggono dal database al caricamento** invece di essere scritte nel testo. Un post sui costi con numeri congelati invecchia in due settimane e diventa una bugia lenta; questo si aggiorna da solo. Il meccanismo è riusabile su qualunque altro post.
- **FAQ post-money da 7 a 9 domande**, micro-tuning sul cluster di ricerca.

**Il giorno dopo**, in un intervento separato senza numero di sessione (`398c375`, `7c4fbdf`): breadcrumb strutturati sulle 7 pagine principali e canonical senza slash finale sui 14 post, per rispondere a un referto di Google Search Console.

**Ha già un report suo**: `2026-07-23_S123_RforCEO_seo-claude-trading-cluster.md`, oggi in `resolved/`.

---

## 3. Recap S124 (6 agosto) — un fix, e una scoperta più grossa del fix

**Riga di PROJECT_STATE §10, verbatim:**

> `2026-08-06 | bot(report)+test | **S124** fix T.4 attribuzione Day P&L (market misurato vs trading residuo) + **rilevato reset Binance testnet** | SHIPPED f98afbc, **pending restart** (Max: "lo faremo un'altra volta"); reset → decisione a Max/CEO`

### (a) Cos'era il fix T.4

**L'innesco**: Max ha chiesto perché il report serale dicesse che la giornata era andata **−$1,50** quando il bot aveva chiuso **tre vendite in utile**.

**Il difetto**: il report scomponeva il movimento del giorno in *"vendite $X · latente $Y"*, ma il latente non era **misurato** — era **dedotto**, come `movimento − realizzato`. Il problema è che vendere non crea profitto, lo **sposta**: lo tira fuori dal latente e lo mette nel realizzato. Quindi ogni vendita in utile veniva contata **due volte** — una come guadagno nelle vendite, una come perdita identica nel latente. Più il bot vendeva bene, più la riga "latente" sembrava un crollo.

**Numeri veri di quel giorno**: il mercato aveva tolto **−$2,13** (SOL −1,13, BONK −0,66, BTC −0,34) e il bot aveva **aggiunto +$0,63**. Il report leggeva *"vendite +1,53 · latente −3,03"*: un crollo di mercato mai avvenuto.

**Il fix**: il mercato ora si **misura** — prezzo di oggi meno prezzo di ieri, moltiplicato per le quantità di **ieri** — e il trading è il **residuo**. La scelta di quale dei due misurare non è neutra: il residuo assorbe sempre l'errore di attribuzione, e metterlo sul trading (poche operazioni) danneggia meno che metterlo sul mercato (tutte le posizioni). In più, usando le quantità di ieri, quel residuo **diventa** la risposta a *"quanto il bot ha battuto lo stare fermo"* — cioè il counterfactual, gratis.

Il realizzato resta in testata come **"Locked in"**: cassa messa al sicuro, non profitto guadagnato oggi.

⚠️ **Il fix è rimasto a terra dal 6 all'7 agosto** (Max: *"lo faremo un'altra volta"*) ed è entrato in volo solo col restart del cutover.

### (b) La scoperta collaterale

Nella stessa sessione è emerso che **il testnet Binance si era azzerato fra il 5 e il 6 agosto**: wallet tornato alla dotazione di default, storico ordini vuoto, e il database che continuava tranquillamente la contabilità di `testnet_2`.

**I bot non se ne erano accorti perché il wallet post-reset era più *ricco* del database.** Nessun ordine falliva. L'unica eccezione latente era BONK: il database credeva di avere 33 milioni di token contro i 18 mila reali, quindi la prima vendita sarebbe fallita.

La rilevazione **esisteva già** — lo script di riconciliazione scrive "probable testnet reset" — ma in un log che nessuno legge, e il cron chiude con successo. **Un avviso che nessuno riceve non è un avviso.** È la stessa lezione del promemoria in `commentary.py` che prevedeva il giorno del cutover e che abbiamo mancato lo stesso.

Questa scoperta è ciò che ha portato alla decisione del Board del 6 agosto — niente `testnet_3`, si abbandona il venue — e quindi al cutover del 7.

---

## 4. Il buco che ho trovato cercando: la macchina dei contenuti è ferma

Max ha chiesto quale bozza X fosse in attesa di approvazione. **Nessuna**: la coda è vuota. Ma cercandola sono emerse due cose peggiori.

**Il diario è fermo alla sessione 122.** Dal log del poster X:

> `Latest diary: Session 122 (384.6h old) -- STALE` → `Generating post (use_diary=False)`

Sedici giorni. Il poster ha smesso di attingere al diario e genera i post dai **cambi di configurazione** — cioè dal rumore tecnico invece che dal racconto. E il canale Telegram pubblica il diario solo "su nuova sessione completa": anche lì, da sedici giorni, niente.

**La campagna X delle 69 bozze non è mai partita.** Il dossier del 3 luglio (11 filoni, ~150 momenti grezzi ridotti a 69 lezioni distinte) ha il campo "pubblicato il" **vuoto su tutte e 69**.

Non è un problema tecnico: il listener `/approve` è vivo, il cron gira ogni sera, l'infrastruttura funziona. È che **il materiale è pronto e nessuno lo muove**. E arriva nel momento peggiore, perché il progetto ha appena fatto la cosa più raccontabile della sua storia — il primo denaro vero in vetrina — e l'audit A3 dice da due cicli che **la distribuzione è il collo di bottiglia**, non il prodotto.

---

## 5. Cosa chiedo al CEO

1. **Il diario di S123, S124 e S125.** Senza, la macchina dei contenuti gira a vuoto e il canale Telegram tace. S125 in particolare è la sessione più densa dell'anno.
2. **La campagna X**: 69 bozze pronte da cinque settimane. Servono la tua voce e la selezione, poi Max approva.
3. **Il post di annuncio del denaro reale** — regola marketing, lo scrive Max in italiano e tu traduci. Adesso ha anche un finale: *un ciclo chiuso il giorno dopo*.
4. **Il backtest pubblico girato a commissione dimezzata** (0,40% contro lo 0,80% reale): con denaro vero in campo quel materiale è fuorviante. Decisione editoriale tua, non l'ho toccato.

---

## 6. Stato del sistema, 48 ore dopo il cutover

| | |
|---|---|
| Flotta | **9/9 processi** su (orchestrator + 2 grid Kraken + Sentinel + Sherpa + NewsKeeper v2 + listener) |
| Operazioni a denaro reale | **7** totali, ultima l'8 agosto |
| Cicli completati | **2** (BTC in Fase 2a, SOL l'8 agosto) |
| Serie giornaliera | 2 punti e cresce, dopo 21 giorni in cui non veniva registrata |
| Debito n.1 | **la riconciliazione su Kraken non esiste** — il controllo che prova che i numeri a database corrispondono agli ordini veri |
