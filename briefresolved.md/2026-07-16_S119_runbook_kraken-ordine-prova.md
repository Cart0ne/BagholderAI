# Runbook — Ordine-prova reale Kraken ($25 BTC/USD, sorvegliato)

**Sessione:** S119 (Fase 2a) · **Data:** 2026-07-16 · **Autore:** CC · **Esegue:** Max
**Brief sorgente:** `config/2026-07-13_S119_brief_kraken-fase2a.md` · **Commit fix:** vedi git log S119

> **A cosa serve.** Kraken non ha testnet: il fix critico (il bot ora *chiede a
> Kraken l'esito reale dell'ordine* invece di leggere la ricevuta cieca) può
> essere certificato **solo** da un ordine vero, guardato a mano. Questo è quel
> test. Lo **lanci tu**; io ho solo preparato il codice e questa sequenza.
>
> **Criterio di successo (brief §3):** un **ciclo completo** — un BUY **e** un
> SELL reali — con in `trades` le righe giuste, avg/cash aggiornati, **nessun
> loop di ri-ordino**, **nessun Telegram fuorviante**. *Il SELL arriva quando il
> mercato sale del 2%: nessuna vendita forzata.* Non si passa ai $100 finché non
> si è vista registrare bene **anche** una vendita.

---

## 0. Isolamento (perché è sicuro) — §5 del brief

La riga Kraken di test vive a **`is_active=false`**. L'orchestrator sul Mac Mini
spawna **solo** le righe `is_active=true`, quindi **non la vede** e non ci
litiga: la flotta testnet continua indisturbata. Tu lanci **a mano** un
grid_runner dedicato con il flag `KRAKEN_TEST_MODE=1` che è l'unico modo di far
girare quella riga (senza il flag, il bot si spegne da solo su `is_active=false`).

→ I due processi non "possiedono" mai la stessa riga. Il sito pubblico intanto
resta pinnato a `venue=binance` (fix 2a.2), quindi non mostra nulla di Kraken.

---

## 1. Prerequisiti (una volta)

1. **Codice aggiornato sul Mac Mini** — sul Mini, nella repo runtime
   `/Volumes/Archivio/bagholderai`:
   ```
   git pull        # porta i fix S119 (poll fill + halt + venue filter)
   ```
   (Se stai già facendo l'aggiornamento del PC + restart, il `git pull` prima
   di rilanciare la flotta copre anche questo — vedi nota in fondo.)

2. **Chiavi Kraken** in `config/.env` (già presenti da Fase 0):
   `KRAKEN_API_KEY=…` e `KRAKEN_API_SECRET=…` (permesso **Withdraw OFF**).

3. **Fondi**: i **$100 già sul conto Kraken** bastano. Il test usa **$25** (BUY
   $25 + ~0,8% fee ≈ $25,20 impegnati; resto disponibile).

---

## 2. Inserire la riga Kraken di test (a DB, `is_active=false`)

Da admin Supabase → SQL, oppure dal pannello. Riga BTC/USD, spenta, isolata su
un cycle suo (`kraken_test`) così le sue trade non si mescolano col testnet:

```sql
INSERT INTO bot_config
  (symbol, venue, managed_by, is_active, pending_liquidation,
   capital_allocation, capital_per_trade, buy_pct, sell_pct,
   profit_target_pct, skim_pct, idle_reentry_hours, cycle)
VALUES
  ('BTC/USD', 'kraken', 'grid', false, false,
   25, 25, 0.3, 2.0,
   0, 0, 24, 'kraken_test');
```

Parametri (Board, brief §4):
- `sell_pct = 2.0` → vende a +2% sopra l'avg (copre il round-trip fee 1,6% +
  cuscino slippage). **Deciso da Max.**
- `profit_target_pct = 0` → floor a break-even-post-fee: **non vende mai in
  perdita**. Non si tocca.
- `buy_pct = 0.3` → compra al primo calo dello 0,3% sotto il riferimento del
  boot (di solito pochi minuti; abbassalo se lo vuoi più rapido, ma stai a
  guardare). Sherpa è **hands-off** sulle righe Kraken (S118): i parametri
  restano statici, come voluto per il test.

> Se l'INSERT si lamenta di una colonna NOT NULL mancante, la via più sicura è
> **duplicare la riga `BTC/USDT` esistente** e cambiare solo:
> `symbol='BTC/USD'`, `venue='kraken'`, `cycle='kraken_test'`,
> `capital_allocation=25`, `capital_per_trade=25`, `sell_pct=2.0`,
> `buy_pct=0.3`, `is_active=false`.

---

## 3. Lanciare il bot di test (da terminale sul Mac Mini)

Nella repo runtime, con il venv py3.13. **Una riga**, tutti i flag in linea:

```
cd /Volumes/Archivio/bagholderai
TRADING_MODE=live ALLOW_REAL_MONEY=true KRAKEN_TEST_MODE=1 \
  venv/bin/python3.13 -m bot.grid_runner --symbol BTC/USD
```

Cosa significano i flag:
- `TRADING_MODE=live` → ordini reali (non paper).
- `ALLOW_REAL_MONEY=true` → cancello soldi-veri Kraken (senza, il bot si rifiuta
  di partire: Kraken non ha testnet, le chiavi da sole non sono consenso).
- `KRAKEN_TEST_MODE=1` → gira la riga `is_active=false` (isolamento §0).
- `--symbol BTC/USD` → sceglie la riga; il `venue=kraken` lo legge dalla riga.

All'avvio nei log devi vedere: `Venue: kraken`, `Mode: LIVE`, e il warning
`KRAKEN — REAL MONEY, REAL ORDERS`. Se vedi `REAL MONEY gate closed` → manca
`ALLOW_REAL_MONEY=true`. Se si spegne subito con `is_active=false` → manca
`KRAKEN_TEST_MODE=1`.

**Tienilo in primo piano e non staccarti.** Non serve `nohup`/`caffeinate`: è un
test sorvegliato, lo fermi tu con **Ctrl+C**.

---

## 4. Cosa guardare — il BUY

Quando BTC scende ~0,3% sotto il riferimento, il bot manda un market BUY da $25.
Verifica su **tre fronti** che combacino:

1. **Log terminale**: riga `[kraken] BUY BTC/USD … fill confirmed via fetch_order
   after N.Ns` → è il **fix critico in azione** (ha chiesto a Kraken l'esito
   reale e l'ha letto). NON deve comparire un loop di BUY ripetuti.
2. **Telegram**: un solo alert di BUY, coerente.
3. **Kraken (app/web)** → **DB**: la quantità BTC e il prezzo sul conto Kraken
   devono coincidere con la riga in `trades` (symbol `BTC/USD`, side `buy`,
   `cycle='kraken_test'`), e l'avg del bot deve riflettere prezzo **+ fee reale
   in USD**.

Se invece parte il messaggio **🛑🔴 "FILL NON CONFERMATO — HALT"** → vai a §6.

---

## 5. Cosa guardare — il SELL (quando BTC ≈ $66.314, +2% NETTO post-fee)

Il SELL **non si forza**: parte da solo quando BTC supera il trigger **fee-buffered ≈ $66.314** (= avg $63.991 × (1+sell_pct/100+fee)/(1−fee), fee Kraken 0,8% — *non* avg×1,02: la formula è `grid_bot.py:876`, aggiornato 2026-07-20). A quel prezzo il lotto da $25 vale **~$26,11 lordi**. Può
volerci ore o giorni — è previsto (brief §3). Lascia il bot su, sorvegliato.
Quando scatta:

- Log `[kraken] SELL BTC/USD … fill confirmed via fetch_order …` (stesso fix).
- In `trades`: riga `sell`, `revenue` **netto della fee USD**, `realized_pnl` > 0.
- `cash` / avg aggiornati; holdings BTC → ~0.
- Un solo Telegram, coerente (niente "rejected" fuorvianti).

**Solo dopo aver visto un SELL registrato bene** il test è passato → si può
pianificare la Fase 2b ($100).

---

## 6. Se scatta l'HALT (fill non confermato)

È la rete di sicurezza che hai scelto ("Halt + chiama Max, mai retry"). Vuol
dire: ordine partito ma Kraken non ha confermato l'esito entro ~15s. Il bot:
- **si ferma** (nessun nuovo ordine, nessun retry),
- porta la riga a `is_active=false` (già così nel test),
- ti manda l'alert.

**Cosa fai:** apri Kraken (app/web) → **Ordini / Storico trade** e controlla a
mano se quell'ordine BTC/USD è **davvero** stato eseguito:
- Se **sì** (c'è il fill): il trade non è a DB. Annotalo, decidi con me come
  riconciliare (inserire la riga a mano) prima di ripartire.
- Se **no** (nessun fill): nessun soldo mosso, puoi rilanciare.

**Non rilanciare il bot prima di aver chiarito lo stato su Kraken.**

---

## 7. Chiusura del test (teardown)

1. Ferma il bot: **Ctrl+C** nel terminale (spegnimento pulito).
2. Non ri-esportare `ALLOW_REAL_MONEY` / `KRAKEN_TEST_MODE` (valgono solo per
   quel comando: chiuso il terminale, spariscono).
3. La riga di test: puoi **lasciarla** `is_active=false` (innocua, l'orchestrator
   la ignora) o cancellarla:
   ```sql
   DELETE FROM bot_config WHERE symbol='BTC/USD' AND venue='kraken';
   ```
4. **Se hai fermato a metà ciclo** (BUY fatto, SELL no): resti con ~$25 di BTC
   sul conto Kraken — **sono tuoi, nessun problema**. O aspetti il +2% per
   chiudere il ciclo, o vendi a mano su Kraken.

---

## Nota — aggiornamento PC + restart flotta

Questi fix S119 vivono **tutti sul percorso Kraken dormiente**: su `venue=binance`
sono un **no-op** (297 test verdi, invariante intatto). Quindi:
- Non impongono un restart della flotta testnet.
- Quando spegni tutto per l'aggiornamento del PC e riavvii, fai `git pull` sul
  Mini **prima** di rilanciare l'orchestrator: porti il Mini sul codice più
  recente (S118 + S119) senza alcun cambio di comportamento su Binance.
- Inventario da riavviare (health-sweep): orchestrator + 4 grid + TF + Sentinel
  + Sherpa · standalone NewsKeeper v2 + listener `x_poster_approve` · cron
  x_poster 20:30 + reconcile 03:00. (Rilancio orchestrator: `nohup caffeinate …`
  con gli env flag catturati dal processo vivo — chiedimi la sequenza se serve.)
