Proposta contenuti canale Telegram — 2026-07-07

> **Nota sul tipo di documento:** questo NON è un brief CEO→CC nel formato standard
> (`YYYY-MM-DD_SXX_brief_SCOPE.md`). È una proposta scritta da CC su richiesta diretta
> di Max, che consolida: (a) il task **T.1** della Master Task List
> (`config/MASTER_TASK_LIST_2026-07-03.md`), (b) la lista di 4 idee dettate da Max in
> conversazione, (c) la ricerca di fattibilità fatta da CC su codice esistente.
> Non contiene ancora un piano di implementazione formale — quello arriva DOPO che
> Max/CEO chiudono le 4 decisioni aperte in fondo a ogni sezione (§5 protocollo
> CLAUDE.md: task >1h → piano prima del codice, quindi ogni item qui sotto avrà il
> suo brief separato una volta deciso il taglio).

---

## 0. Contesto

Il canale Telegram report è privato ma aperto al pubblico (anti-squat — dopo che
`@bagholderai_report` è stato squattato quando il vecchio canale pubblico è rimasto
vuoto). Il listener `/approve` è stato riparato l'1 luglio dopo essere stato morto
da inizio giugno. Oggi il canale pubblica solo il daily report (20:00) + il CEO's
Log serale generato da Haiku. Max vuole altri 4 tipi di contenuto per tenerlo vivo
e dare valore agli iscritti.

---

## 1. Selezione 5 top news/giorno, processate da Haiku, con link

**Cosa esiste già:** NewsKeeper gira in due generazioni parallele (`bot/newskeeper/`
v1 e `bot/newskeeper_v2/`), entrambe scrivono su Supabase (`newskeeper_signals`)
con classificazione Haiku per-articolo:
- v1: `theme`, `market_impact`, `severity`, `direction`
- v2 (il "barometro"): `relevance` (high/medium/discard), `polarity`, `event_key`
  (dedup articoli sulla stessa notizia), `confidence`

Il link (`raw_data.link`) è presente in entrambe. **Cosa manca:** nessuna logica di
ranking "top N" — oggi è solo classificazione per-articolo, mai un digest.

**Lavoro da fare:** query sulla finestra 24h, filtro `relevance=high`, dedup per
`event_key`, poi un layer Haiku che scrive il digest leggibile (stesso pattern di
`commentary.py::generate_daily_commentary`, ma nuovo — oggi NewsKeeper non parla
mai con Telegram). Sforzo: medio.

**Obiezione tecnica:** v2 è la fonte più adatta (ha il dedup by `event_key`) ma è
ancora in **SHADOW mode** — il suo segnale non è promosso a produzione. v1 è più
maturo ma senza dedup (rischio di mandare 3 articoli sulla stessa notizia).

**Decisione aperta:** usare v2 (shadow) o v1 (maturo, meno pulito) come fonte del
digest?

---

## 2. Messaggio buy/sell minimale ("we buy 1 lot of XXXX")

**Cosa esiste già:** un alert per-trade **esiste già** (`send_trade_alert()`,
`utils/telegram_notifier.py:48-114`, chiamato da `bot/grid_runner/__init__.py:659`
e `bot/grid_runner/liquidation.py:174`) ma è l'opposto di minimale: prezzo, costo,
fee, P&L realizzato, P&L portfolio, cash/holdings — un mini-report ad ogni fill.

**Lavoro da fare:** nuovo metodo leggero (`"🟢 BUY 1 lot BTC/USDT"`), da affiancare
alle chiamate esistenti, non da sostituirle (quelle restano per il canale privato
dettagliato). Sforzo: medio.

**Obiezione tecnica:** frequenza. 3 grid instance sempre attive (BTC/SOL/BONK) +
TF che può aprirne altre, cooldown 5-30 min per simbolo → nei giorni volatili
possono essere decine di trade/giorno. **Precedente reale:** sessione 21 ha avuto
uno spam Telegram (notifiche "BUY SKIPPED" ogni ~20s) che ha richiesto un guard di
dedup (`_last_skip_notification` in `bot/grid_runner/__init__.py:418-419`).

**Decisioni aperte:**
- Canale pubblico o privato? (CC propende pubblico — è già pensato "sobrio, senza
  cifre in $", coerente con l'obiettivo anti-squat)
- Serve un throttle/rate-limit, o si accetta il volume as-is?

---

## 3. Avviso cambio di regime — Sentinel + NewsKeeper

Due situazioni molto diverse, da trattare separate:

**NewsKeeper v2 (barometro):** il flip-detection **esiste già** e logga
`"BAROMETER FLIP X -> Y"` (`bot/newskeeper_v2/main.py:111-131`) — semplicemente non
manda nulla su Telegram oggi. Aggiungere la call al notifier è quasi un one-liner.
Sforzo: basso. **Stesso caveat del punto 1: è ancora SHADOW mode** — pubblicare un
segnale non ancora promosso a produzione è una scelta, non un dettaglio tecnico.

**Sentinel:** qui NON esiste alcun confronto "regime di oggi vs regime di ieri" — il
regime (5 stati da Fear&Greed: extreme_fear/fear/neutral/greed/extreme_greed) viene
scritto ogni tick ma mai comparato. Va costruito da zero, seguendo il pattern già
usato da Sherpa per un altro scopo (`bot/sherpa/main.py:475-508`, confronto
prev-vs-current). Sforzo: medio, ma pattern chiaro da copiare.

**Decisione aperta:** pubblicare anche il segnale NewsKeeper v2 (shadow, non
verificato) insieme a quello Sentinel, o solo Sentinel per ora e NewsKeeper quando
esce da shadow?

---

## 4. Post automatico quando il CEO chiude una sessione diary su Supabase

**Il pezzo più impegnativo dei 4.** Il CEO scrive il diario (`diary_entries` su
Supabase) direttamente via i suoi tool MCP — non passa MAI per il codice di questo
repo (nessun `.insert()` su `diary_entries` esiste in `db/client.py` o altrove, solo
`.select`/`.update` in `utils/x_poster.py`). Non esiste nel repo nessun meccanismo
che osserva una tabella Supabase e reagisce a nuove righe — né cron, né webhook, né
trigger Postgres, né Edge Function, per nessuna tabella. Il CEO's Log serale che già
va su Telegram è una pipeline completamente separata e in-process (Haiku genera il
testo dallo stato live del bot dentro `bot/grid_runner/daily_report.py`, non legge
mai `diary_entries`).

**Lavoro da fare:** infrastruttura nuova, due strade:
- (a) un cron/polling nel repo che controlla periodicamente l'ultima sessione vista
  in `diary_entries` — dipende dall'orchestrator essere vivo.
- (b) un Supabase Database Webhook / Edge Function su INSERT che chiama
  direttamente l'API Telegram — indipendente da questo repo, funziona anche a
  orchestrator giù, ma è infrastruttura fuori dal codice Python che gestiamo qui.

Sforzo: alto (nuova infrastruttura, non wiring di qualcosa che già esiste).

**Decisione aperta:** (a) cron Python dentro il repo o (b) webhook/Edge Function
Supabase indipendente? E: si posta il riassunto completo o solo un ping "nuova
sessione disponibile" con link al sito?

---

## 5. Ranking per sforzo (dal più facile)

1. **NewsKeeper v2 regime-flip → Telegram** (quasi gratis, codice già logga il flip)
2. **Sentinel regime-change detection** + **ticker buy/sell** + **digest top-5 news**
   (sforzo medio, pattern chiari da riusare)
3. **Diary → Telegram on session close** (nuova infrastruttura, decisione
   architetturale prima ancora del codice)

## 6. Decisioni da chiudere prima di scrivere i brief di implementazione

1. Punto 1 — dati da NewsKeeper v1 (maturo) o v2 (shadow, con dedup)?
2. Punto 2 — canale pubblico o privato per il ticker trade? Serve throttle?
3. Punto 3 — ok pubblicare anche il segnale NewsKeeper v2 pur essendo shadow, o
   solo Sentinel per ora?
4. Punto 4 — cron Python nel repo o webhook Supabase indipendente? Riassunto
   completo o solo ping+link?
