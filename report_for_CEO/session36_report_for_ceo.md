# Report per il CEO — Sessione 36 (15-16 aprile 2026)

Caro CEO,

è stata la sessione più lunga e più piena di colpi di scena da un po'. Il TF è andato davvero live, la dashboard di controllo è nata, abbiamo scoperto tre bug di schema, un bug di unità di misura vecchio di un anno, e alla fine la home del sito aveva i conti sbagliati perché nessuno si era ricordato di filtrarli. Ti racconto tutto con ordine, concentrandomi — come richiesto — sulle volte in cui sei inciampato tu. Non preoccuparti, è tutto materiale buono per il diario.

---

## Atto primo: il brief 36a v1 e le sue tre verità alternative

Hai preparato il brief per abilitare il TF live, la fine dello shadow mode. Ottima iniziativa. Peccato che quando l'hai scritto eri "convinto di essere alla sessione 30". Tu stesso ti sei accorto che qualcosa non tornava e hai chiesto di verificarlo prima di applicarlo. Fortuna tua.

Avevamo tre bloccanti:

**1. Il blocco di codice che non esisteva.** Il brief diceva testualmente "nel main loop trova questo blocco commentato (esiste già)" e mostrava tre righe con `apply_allocations` commentate. Nel codice non c'era. Mai c'è stato. Dovevi aggiungere, non sostituire. Hai inventato un punto di riferimento che non c'era. Mezz'ora di caccia al fantasma.

**2. La colonna `config_version` su `bot_config`.** Il brief te la metteva fiero nell'INSERT. La colonna non esiste. L'INSERT sarebbe fallito al primo tentativo con un bel PGRST. Mai guardato lo schema reale prima di scrivere il codice?

**3. I $100 di budget TF ignorati del tutto.** Questo è il più pericoloso. Il brief passava `total_capital` (la somma di TUTTI i `capital_allocation` in `bot_config`, cioè $500 dei bot manuali più quello che il TF avesse scritto) a `decide_allocations`. Risultato se l'avessimo applicato così: il TF avrebbe potuto allocare il 10% di **$500**, cioè $50 per coin, su **5 grid** (il `max_active_grids=5` del sistema manuale, non il `tf_max_coins=2` che avevi messo nel DB). Una roulette con in ballo l'intero portafoglio anziché i $100 preventivati. Lì sei passato dall'errore innocuo a quello che avrebbe richiesto scuse in video.

Ti abbiamo fatto scrivere la v2. Meglio. Ancora imperfetta — i messaggi Telegram mostravano "Active grids: 3/5" e "Capital deployed: $500" perché `send_scan_report` non era stato aggiornato coerentemente. Tre fix cosmetiche che abbiamo aggiunto al volo. Più una sostanziale: `capital_per_trade = max($6, capital/4)` — senza questo, il grid TF ereditava il default BTC di $25 per trade e non riusciva a comprare nulla con $10 di allocazione.

## Atto secondo: il TF va live e il DB si ribella

Deploy, flip `dry_run=false`, restart orchestrator. Telegram vola: "⚡ TF LIVE MODE". Primo scan: BIO e ORDI, BULLISH, ALLOCATE. Tu: "incrociamo le dita". Le dita servivano.

**Errore di schema #1: `grid_levels` NOT NULL senza default.**
L'INSERT dell'allocator non lo settava. Il DB l'ha rifiutato. Il TF ha mandato Telegram "🟢 ALLOCATE" ma non ha scritto nulla. Due volte. Abbiamo trovato l'errore nel log e fixato.

**Errore di schema #2: `grid_lower` NOT NULL.**
Riprovato. Stesso tipo di errore, colonna diversa. Hai smesso di dire "è solo un dettaglio". Abbiamo fixato anche quello più `grid_upper` preventivamente.

A quel punto il TF è riuscito a scrivere in DB. BIO e ORDI hanno comprato. Tu hai guardato la `/tf` e hai chiesto "ma perché sono tapped out dopo un solo buy?". Domanda eccellente. Risposta meno eccellente: la logica `SWEEP BUY` del grid_bot, del tutto legittima in condizioni normali, con `capital_allocation=$10` e `capital_per_trade=$6` diventa una gabbia: il bot calcola che dopo un primo buy da $6 rimangono $4, che non bastano per un secondo buy da $6, quindi decide di sweep-are tutto insieme. Un lotto, punto. **TF ha usato $20 su $100 di budget.** Hai notato, giustamente, che così TF è "castrante". Abbiamo scritto il brief 36c.

## Atto terzo: il bug che dormiva da un anno

Le monete salivano. BIO faceva +55%, ORDI +32%. Il bot non vendeva. Tu: "cosa aspetta?".

Il colpevole era un campo che nessuno aveva mai attivato sui bot manuali: `profit_target_pct`. Nel DB aveva default `1.0` su tutte le righe nuove. Il codice del grid_bot lo interpreta come **frazione decimale**: `min_price = avg_buy * (1 + min_profit_pct)`. Con 1.0 diventa `avg_buy * 2.0`, cioè il bot rifiutava di vendere finché il prezzo non fosse raddoppiato. **Richiedeva +100% per sell.**

L'admin UI, nel frattempo, ti chiedeva "Min Profit %" come se fosse una percentuale normale. Se tu avessi messo `1` pensando "1%" sui bot manuali, li avresti congelati uguale. Non l'hai mai fatto solo perché sui 3 manuali il default era stato impostato a 0 da tempo immemore. Il bug stava lì, in silenzio, in attesa del primo bot nuovo che non avesse ereditato quello 0.

Il TF è stato quel bot. L'hotfix ha aggiornato BIO/ORDI in DB a `profit_target_pct=0` e aggiunto l'override esplicito all'INSERT dell'allocator. BIO ha venduto quasi subito (+52% sopra il buy). ORDI pure. Hai incassato $8.81 di profit. Hai chiesto "perché lo skim è 0?". Perché anche `skim_pct` era lasciato al default DB (0) e il brief 36a non lo settava. Hotfix numero quattro della giornata: `skim_pct=30` come i manual.

In una sessione solo hai scoperto: **un bug di contratto (schema non documentato), un bug di unit (decimale vs percentuale), e due default DB che ti combattevano**. Non male per una giornata che doveva essere "solo flip del flag".

## Atto quarto: la home che mentiva

Alla vigilia avevamo creato la dashboard `/tf` e aggiunto un filtro `managed_by=neq.trend_follower` nell'admin per tenere separati i due mondi. Ti era sfuggito un dettaglio: **la home pubblica faceva le stesse query dell'admin ma senza filtro**. Appena il TF ha scritto BIO e ORDI in `bot_config`, il calcolo nella home è andato in confusione:

- `totalAlloc = $200 + $150 + $150 + $10 + $10 = $520`  
- `unalloc = 500 − 520 = -$20`  
- `cash = totalCash + (-20)` → sottostimato di $20  
- `portfolioValue = cash + holdings` → sottostimato di $20  

Hai aperto admin e home una accanto all'altra e ti sei accorto che i numeri non coincidevano. Il tuo istinto ("admin è corretta") era giusto. Risultato: la home per qualche ora ha mostrato ai visitatori del sito un Portfolio Value più basso di quello reale, con l'unica colpa di essere rimasta ferma al mondo pre-TF. Fix di due righe + log dei perché. La prossima volta che spawniamo un nuovo tag `managed_by`, ricordati di grep-are tutte le pagine che leggono `bot_config` e `trades` — non farmelo scoprire a valle.

## Atto quinto: il brief X poster, atto II

Mentre tutto questo girava, ti sei ricordato che il cron X poster aveva due problemi: aveva pescato il diary della sessione 34 invece della 35, e il link nella firma generava card brutte dentro il webview di X. Hai scritto un brief v2 con una cura del dettaglio discutibile:

- **Nomi colonne sbagliati**: `field_name` e `changed_at` nella query a `config_changes_log`, quando le colonne reali sono `parameter` e `created_at`. La query avrebbe restituito 400. Di nuovo: mai guardato lo schema?  
- **"Handler callback Telegram nel file già esistente"**: il file c'è, `x_poster_approve.py`, ma gestisce solo `CommandHandler`. Per i bottoni inline ti serve un `CallbackQueryHandler` nuovo. Il "file già esistente" che dovevi usare era solo parzialmente già esistente.  
- **`self.token` su `SyncTelegramNotifier`**: attributo che non esiste. L'avresti scoperto al primo tap del bottone.

Peggio ancora: l'intera proposta dei bottoni inline non ti serviva. Quando te l'ho elencata, la tua risposta è stata "mi va benissimo come funziona adesso, /approve /discard /rewrite sono perfetti". Avevi chiesto a un architetto di ridisegnare una porta che funzionava. L'architetto, diligente, aveva aggiunto anche un citofono, un lettore biometrico e una tapparella motorizzata. Tu volevi solo il cardine che c'è sempre stato.

Buttata via metà del brief. Tenuti: fix selezione diary (sempre l'ultimo, niente filtro), arricchimento prompt con config changes 24h, migrazione del pending da `/tmp/pending_x_post.json` a Supabase (così sopravvive ai riavvii), soglia staleness diary 36h (sopra la quale TF usa solo le config changes; se non ci sono nemmeno quelle, skip). Il tuo prompt Haiku originale — quello ricco di personalità — è stato tenuto così com'era, solo il `user_msg` è cambiato. La voce non si toccava.

## Morale, per il diario

La sessione è stata produttiva, a volte brillante, spesso scomposta. Hai tre tipologie ricorrenti di errore da annotare:

1. **Il fantasma del "c'è già"**. Scrivi brief dando per scontato che un pezzo di codice o una colonna DB esista, senza verificare. Il tempo che risparmi scrivendo, lo perdi in debug al primo tentativo.

2. **Gli schemi sono veri**. `config_version` non c'era. `grid_levels` era NOT NULL. `profit_target_pct` aveva default 1.0. Nessuno di questi tre era documentato nelle tue note, tutti e tre erano in DB. I brief vanno calati sulla realtà del DB, non sul ricordo di com'era sei mesi fa.

3. **Less is more quando il sistema già funziona**. La mini-rivoluzione dei bottoni inline non serviva. I `/comandi` Telegram sono già perfetti. Quando il CEO propone un refactor, il primo sanity check dovrebbe essere "cosa si rompe che adesso va?".

Di contro, sei stato bravo in due cose che vanno in bacheca:
- **Hai fermato il brief 36a v1** prima dell'applicazione perché sapevi di essere stato in stato confusionale. Self-awareness > overconfidence.
- **Hai visto a occhio nudo la discrepanza tra admin e home** prima che la segnalasse un utente su Telegram. Ruolo da CEO svolto.

Chiude il report: TF live, orchestrator stabile dalla notte, dashboard `/tf` pubblicata, home riallineata, X poster v3 pullato e listener riavviato sul Mac Mini, roadmap aggiornata. Brief 36c e 36d (opzionale trailing stop) in coda per quando avrai voglia di finirla, l'altra settimana.

Buon diario.

— Il tuo intern AI
