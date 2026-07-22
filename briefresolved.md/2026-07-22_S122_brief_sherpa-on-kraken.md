Brief S122 — sherpa-on-kraken — 2026-07-22

**Da:** CEO · **Per:** CC (Intern) · **Board:** Max
**SCOPE canonico (da ereditare IDENTICO nel report):** `sherpa-on-kraken`
**Base:** nota CC `2026-07-22_sherpa-on-kraken_note_for_ceo.md` + report `2026-07-22_S122_RforCEO_kraken-2b-bundle.md` (commit `ed1933d`) + nota sequencing `2026-07-21`
**PROJECT_STATE di riferimento:** allineato a S121 (`75e59c1`) + bundle `ed1933d`. Sessione corrente confermata **S122** (Supabase: S121 COMPLETE, 21-lug).

---

## 0. Decisioni Board prese in questa sessione

| # | Decisione | Chi |
|---|---|---|
| 1 | **Opzione B CONFERMATA** — Fase 2b = $100 BTC/USD su Kraken **Sherpa-driven**, niente freeze | Max |
| 2 | **Strada 1 approvata** — questo brief è il gate pre-2b | CEO+Max |
| 3 | **Sorgente volatilità = proxy Binance /USDT** (non OHLC nativo Kraken) | CEO (delegato da Max) |
| 4 | **Fee-drag = opzione (A) osservare**, con obbligo di misura (§4) | CEO+Max |
| 5 | **Restart unico.** Kraken si accende nello stesso restart del codice nuovo | Max |

### 0bis. Revisione esplicita di una decisione precedente (per BUSINESS_STATE §4)

La decisione S119 del 2026-07-13 recitava: *"$100 sequenziale grid-only → sistema pieno SOLO dopo"*, con razionale *"accenderli sul primo denaro reale perde il segnale pulito"*.

**Questa decisione è superata dai fatti.** La Fase 2a ha già eseguito un round-trip reale completo a parametri statici (BUY $25 17-lug → SELL 21-lug, +$0,7069 netto). Ripetere lo stesso test con $100 non produce informazione nuova. Il costo accettato consapevolmente è la **diagnosticabilità**: se la 2b va male, non sapremo di primo acchito se ha sbagliato la meccanica o la scelta di Sherpa. È accettabile perché il fix del bundle `ed1933d` garantisce che **ogni singola vendita sia in utile netto** — il caso peggiore è "guadagna poco", non "perde".

*Registrare in BUSINESS_STATE §4 come revisione di S119, non come decisione scollegata.*

---

## 1. Lavoro richiesto

### a) Rimuovere il filtro hands-off venue=kraken
`bot/sherpa/main.py:408` — la riga che esclude le righe `venue='kraken'` da `_fetch_active_manual_bots`.

Delle due ragioni documentate nel commento sopra (`:397-408`):
- **(a) floor azzerato** → risolta dal fee-fix di `ed1933d` (`profit_target=0` ora significa "floor a break-even", non "floor spento"). ✅
- **(b) volatilità rotta** → risolta dal punto (b) qui sotto.

**Aggiornare anche il commento**, non solo la riga: un commento che documenta un filtro che non esiste più è debito informativo. Sostituire con una nota S122 che dica cosa è cambiato e perché.

### b) Fix mapping simbolo /USD nel path Sherpa (sweep, non una riga)
`bot/sherpa/volatility.py:51` e `bot/sherpa/main.py:447` — entrambi fanno `symbol.replace("/","")`, che trasforma `BTC/USD` in `BTCUSD`, inesistente su Binance.

**Soluzione approvata:** mappare `/USD → /USDT` per klines *e* prezzo, coerente con la decisione S112 ("funding-rate resta su Binance, dato pubblico read-only, EU-ok"). Applicato **solo ai simboli /USD** → il path /USDT resta byte-identico.

**Sweep, non due edit puntuali:** cercare ogni altro punto del path Sherpa che costruisca un simbolo Binance da `bot_config.symbol`. Se ce ne sono altri oltre a questi due, sistemarli nello stesso passaggio e elencarli nel report.

**Caveat da scrivere nel codice come limite noto, non come "risolto":** il proxy regge bene su BTC (BTC/USDT e BTC/USD hanno volatilità realizzata praticamente sovrapponibile). Su SOL e soprattutto BONK in Fase 3 la divergenza tra venue può essere maggiore. Non blocca la 2b; deve essere ritrovabile quando arriveremo lì.

### c) Seed della riga Kraken
Valori correnti fear/LOW: buy 1,8 / sell 1,2 / floor 0.

**Nota onesta sul valore di questo punto:** con Sherpa live, questi numeri durano fino al primo tick. Il seed serve solo a evitare che la riga esista con valori nulli o incoerenti nella finestra fra il flip e il primo ciclo Sherpa. Non è un parametro di trading, è un default difensivo — trattarlo come tale, senza dedicarci tempo.

### d) Domanda tecnica da verificare e riportare (non è lavoro di codice)
**L'orchestrator rilegge le righe `is_active` di continuo, o solo all'avvio?**

Non è un gate di questo brief — la decisione Board è restart unico. Serve saperlo per il futuro: se rilegge di continuo, spegnere o accendere una riga Kraken non richiederà mai un restart della flotta. Se legge solo al boot, ogni cambio di stato costa un restart e va pianificato. Rispondere nel report con il riferimento file:linea, non a memoria.

---

## 2. Test richiesti

1. **Invariante Binance byte-identico sul path /USDT.** Questo è il test che conta: il file toccato gira sui 4 grid vivi. Deve essere provato, non assunto.
2. **Sherpa vede la riga Kraken** dopo la rimozione del filtro (e non la vedeva prima).
3. **Mapping /USD** produce il simbolo Binance corretto e `_fetch_stdev` restituisce un valore reale, non 0.0/fallback.
4. Nessuna regressione sui 340 test esistenti.

---

## 3. Superfici da controllare (rischio noto, stessa famiglia dei bug S118/S119)

Con la riga Kraken dentro il loop Sherpa, verificare che nessun'altra superficie "binance-only" la peschi indebitamente: report, reconcile, aggregati, snapshot `daily_pnl`. Il pattern che ci ha già morso due volte è esattamente questo — una query senza filtro `venue` che improvvisamente vede una riga in più.

Se trovi una superficie scoperta: **flaggala nel report, non fixarla d'iniziativa**. Se è bloccante per la 2b, escalation immediata.

---

## 4. Misurazione fee-drag — obbligatoria, non opzionale

Abbiamo scelto di *osservare* invece di aggiungere un minimo `sell_pct` Kraken-aware. "Osservare" senza strumenti equivale a non fare niente. A fine 2b devono essere leggibili **quattro numeri**:

1. numero di trade eseguiti
2. fee totale pagata
3. P&L lordo vs P&L netto
4. `sell_pct` medio proposto da Sherpa nel periodo

**Se questi non escono già dai log o dal daily report, produrli fa parte di questo brief** (uno script di lettura basta, non serve infrastruttura). Verifica cosa esiste già prima di scrivere codice nuovo e dichiaralo nel report.

Ordine di grandezza per capirsi: con lotti da $33,33 e fee 1,6% a giro, un margine netto piccolo produce un utile per trade nell'ordine dei centesimi mentre le fee pagate sono nell'ordine del mezzo dollaro. L'utile resta reale e positivo (il trigger lo garantisce), ma l'efficienza è quello che vogliamo misurare.

---

## 5. OFF-LIMITS

- **Nessun flip `is_active`**, nessun insert riga, nessun restart. Il go-live è finestra coordinata di Max sul Mini.
- **Nessun valore di parametro di trading Kraken** oltre al seed (c). Allocazione, $/trade, skim → tabella con Max al setup 2b.
- **`tf.html:1459`** — flag corretto nel report `kraken-2b-bundle`, resta fuori scope. Micro-brief separato, priorità bassa (TF non trada in v3).
- **Calibrazione TF** — non toccare.
- **Floor Binance** — resta byte-identico, dormiente. Non era rotto.
- **Formula trigger/floor** — chiusa da `ed1933d`. Non riaprire.
- **Ancora-buy-dopo-sell** — chiusa. Confermata la tua lettura del 22-lug.

---

## 6. Delegato a CC / da chiedere a Max

**Delegato a CC (decidi tu, riporta nel report):**
- Come implementare il mapping (helper, costante, dove vive)
- Struttura dei test
- Se lo sweep trova altri punti da sistemare, sistemali
- Come produrre i quattro numeri del §4

**DEVE chiedere a Max:**
- Qualsiasi cosa tocchi valori di trading o stato delle righe
- Se lo sweep rivela che il fix non è additivo come previsto (cioè: se tocca il path /USDT)
- Se emerge una superficie scoperta (§3) che blocca la 2b

**Protocollo:** stima > 1h o > 50 righe → piano in italiano a Max prima del codice. Sotto quella soglia procedi.

---

## 7. Output atteso

- Codice + test shippati su `main` (push diretto, no PR), **no restart**
- Report `2026-07-22_S122_RforCEO_sherpa-on-kraken.md` — SCOPE identico
- Risposta esplicita alla domanda §1d
- Decision log inline se prendi decisioni non previste qui
- Roadmap: probabile nota, non version bump (è plumbing interno) — confermare nel report

---

## 8. Runbook finestra 2b (per Max, sul Mini — NON in questo brief)

Da eseguire come checklist scritta, non a memoria:

1. ☐ Babysitter 2a standalone (**pid 46585**) verificato **morto**. Se vive, due processi sulla stessa riga comprano gli stessi soldi.
2. ☐ Solo la riga Kraken voluta ha `is_active=true`. ⚠️ Il BUY reale **non** è gatato da `is_active` — una riga di prova dimenticata accesa può comprare denaro vero.
3. ☐ Orchestrator rilanciato con `ALLOW_REAL_MONEY=true` (ereditato dai figli via `Popen`).
4. ☐ Verificato dopo il restart: i 4 grid Binance vendono ~0,1% prima di prima (effetto atteso e quantificato del fix trigger). Se cambia altro, è un segnale.

**Nota reboot:** dopo un riavvio del Mini l'orchestrator va rilanciato a mano. Vale anche per il grid Kraken.

---

## 9. Auto-obiezioni del CEO a questo brief

**1. Il seed (c) dà un'illusione di controllo.** Sto chiedendo di impostare parametri che Sherpa riscriverà entro minuti. Se il punto è "Sherpa guida", il seed è quasi decorativo — l'ho tenuto solo come default difensivo e l'ho dichiarato tale. Se CC ritiene che non serva affatto, che lo dica: lo tolgo volentieri.

**2. Sto approvando un patch a un file live sui 4 grid alla vigilia del primo denaro vero.** L'ho mitigato pretendendo il test di invarianza (§2.1), ma resta il fatto che il momento non è ideale. La ragione per cui procedo comunque: senza questo fix, "Sherpa guida" significa "Sherpa guida leggendo volatilità zero", che è peggio di non accenderlo.

**3. Ho proposto un restart in due tempi e l'ho ritirato quando Max ha chiesto perché.** Aveva ragione lui: in T0 la riga Kraken sarebbe stata ferma, quindi il codice davvero nuovo non sarebbe stato esercitato. Avrei speso 24h per osservare la parte già coperta dai test. Lo scrivo perché resti agli atti che l'obiezione del Board era migliore della proposta del CEO.

**4. Il caveat sul proxy per BONK potrebbe essere un problema più grosso di come l'ho scritto.** Non ho dati sulla divergenza di volatilità BONK/USDT vs BONK/USD tra i due venue. L'ho classificato come "limite noto, non blocca" per intuizione, non per misura. Se in Fase 3 salta fuori, la responsabilità è di questa riga.

---

*Cita: nota `2026-07-22_sherpa-on-kraken_note_for_ceo.md`, bundle `kraken-2b-bundle` (`ed1933d`), item S117 "fix sorgente volatilità Sherpa su Kraken" (che questo brief chiude), decisione Opzione B (BUSINESS_STATE §4, 2026-07-21, confermata S122).*
