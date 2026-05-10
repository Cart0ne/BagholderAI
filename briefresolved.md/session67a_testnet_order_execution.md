# Brief 67a — Step 3: Testnet Order Execution Layer

**Sessione:** 67 · May 8, 2026  
**Basato su:** PROJECT_STATE.md aggiornato 2026-05-08 (S66 chiusura)  
**Priorità:** 🔴 CRITICA — gating per restart bot su testnet  
**Stima:** 4-6h (codice nuovo, non "togli un commento")

---

## Contesto

Il bot oggi è 100% paper trading: legge prezzi reali da Binance, calcola buy/sell, scrive nel DB interno. Nessun ordine viene mai inviato a Binance. In `grid_runner.py:484` c'è letteralmente un blocco `if mode == "live": print("LIVE TRADING NON ANCORA IMPLEMENTATO"); exit()`.

Per passare a testnet (= Binance vero, soldi finti), serve un **layer di esecuzione ordini completo**. Il brief 65c stimava "1-2h" — era sbagliato. Serve codice nuovo per: invio ordini, lettura fill, gestione fee reali, gestione errori.

**Decisione Board:** NON scrivere da zero. Usare la libreria `python-binance` (sammchardy, 9k+ GitHub stars, supporto testnet nativo). La libreria gestisce auth, signing, rate limiting, error parsing. CC wrappa la libreria dentro `exchange.py`.

---

## Credenziali Testnet

```
BINANCE_TESTNET_API_KEY=O65Ei5uBusEbuBxSfopAR6HtokqU2nLcXXyrr1PykomqAZOfQQM2zDyyxj6gOtQd
BINANCE_TESTNET_API_SECRET=bZmQ4EZjBbWDBlFb07savjmeOwW82W3OmICcZEft423UxN3XmJZIhbWFYhvjZAFZ
```

Queste vanno nel `.env` sul Mac Mini (`/Volumes/Archivio/bagholderai/.env`). Sono chiavi testnet (soldi finti, zero rischio).

**Coppie verificate disponibili su testnet:** BTCUSDT ✅, SOLUSDT ✅, BONKUSDT ✅ — tutte le nostre monete Grid ci sono. Anche la maggior parte delle altcoin TF.

---

## Decisioni architetturali (CEO + Board)

### 1. Libreria: `python-binance`

```bash
pip install python-binance
```

Client con testnet nativo:
```python
from binance.client import Client
client = Client(api_key, api_secret, testnet=True)
```

La libreria gestisce: autenticazione HMAC-SHA256, URL rewriting (api.binance.com → testnet.binance.vision), rate limiting, error codes.

### 2. Tipo ordine: MARKET

Per questa fase usiamo **market orders** — il bot oggi simula market (buy/sell al prezzo di mercato). Market è il più semplice: invii, Binance esegue subito, ricevi il fill con prezzo e fee reali. Non complicare con limit orders finché market non funziona end-to-end.

### 3. Fee: leggere dal fill, scrivere in DB

Binance ritorna i fee nel response del fill. Ogni trade nel fill ha:
```json
{
  "price": "50000.00",
  "qty": "0.001",
  "commission": "0.00001",
  "commissionAsset": "BNB"
}
```

**Decisione:** aggiungere colonna `fee` e `fee_asset` alla tabella `trades` in Supabase (migration). Il bot scrive i fee reali di Binance anziché quelli simulati.

### 4. Errori: log + alert + skip

Se Binance rifiuta un ordine (insufficient balance, min notional, prezzo fuori range):
- Log l'errore in `bot_events_log` con event_type `ORDER_REJECTED`
- Alert Telegram (canale privato)
- Skip questa iterazione, riprova al prossimo ciclo
- **MAI** retry automatico aggressivo (rischio di loop infinito su ordini rifiutati)

### 5. Riconciliazione: fill Binance vs DB interno

Dopo ogni ordine eseguito, il bot:
1. Invia ordine a Binance → riceve fill con prezzo/qty/fee reali
2. Usa il **prezzo e la qty del fill** (non quelli calcolati) per scrivere in DB
3. Log il `orderId` Binance in `trades` (colonna nuova `exchange_order_id`)

Questo garantisce che il DB rifletta esattamente quello che Binance ha eseguito.

---

## Architettura del codice

### File da modificare

**`bot/exchange.py`** — refactoring principale:
- Rimuovere il bypass legacy (righe 8-11, commento "We don't use Binance testnet")
- Aggiungere init del client `python-binance` con `testnet=True`
- Nuovi metodi: `place_market_buy()`, `place_market_sell()`, `get_account_balance()`, `get_symbol_info()`
- Il metodo `get_price()` esistente resta (legge prezzi, già funziona)

**`bot/strategies/buy_pipeline.py`** — nella funzione di buy:
- Dove oggi scrive "ho comprato X a prezzo Y" nel DB...
- ...sostituire con: chiama `exchange.place_market_buy()` → leggi fill → scrivi in DB con prezzo/qty/fee reali

**`bot/strategies/sell_pipeline.py`** — nella funzione di sell:
- Stessa logica: chiama `exchange.place_market_sell()` → leggi fill → scrivi in DB

**`bot/grid_runner.py`** — rimuovere il blocco `if mode == "live": exit()`

**`.env`** — aggiungere le credenziali testnet

### File da NON modificare

- `bot/strategies/grid_bot.py` — logica decisionale (Strategy A, greed-decay, stop-loss). Invariata.
- `bot/sentinel/` — invariato
- `bot/sherpa/` — invariato
- `bot/strategies/state_manager.py` — invariato (il replay dal DB funziona come prima)

### Migration Supabase

Nuove colonne in `trades`:
```sql
ALTER TABLE trades ADD COLUMN IF NOT EXISTS exchange_order_id TEXT;
ALTER TABLE trades ADD COLUMN IF NOT EXISTS fee NUMERIC DEFAULT 0;
ALTER TABLE trades ADD COLUMN IF NOT EXISTS fee_asset TEXT DEFAULT 'USDT';
```

---

## Decisioni delegate a CC

- Struttura interna di `exchange.py` (classi, metodi helper) — a discrezione di CC purché l'interfaccia pubblica sia chiara
- Gestione dei fill parziali (market orders su testnet possono avere fill multipli — aggregarli in un unico trade DB o splittarli?)
- Arrotondamento qty/price ai filtri Binance: `python-binance` ha helper per leggere i `LOT_SIZE` e `PRICE_FILTER` da `exchangeInfo` — usarli

## Decisioni che CC DEVE chiedere

- Se scopre che il testnet ha behavior diverso dal previsto (es. fill parziali frequenti, rate limit diversi)
- Se la struttura di `buy_pipeline.py` o `sell_pipeline.py` richiede cambi non triviali (>20 righe) alla logica decisionale
- Se il TF (`trend_follower/`) ha un path di esecuzione ordini separato che non passa per `buy_pipeline`/`sell_pipeline`

---

## Output atteso

A fine implementazione:
1. `pip install python-binance` nel venv del Mac Mini
2. `.env` aggiornato con chiavi testnet
3. `exchange.py` refactored con client `python-binance` + metodi buy/sell
4. `buy_pipeline.py` e `sell_pipeline.py` che inviano ordini reali a testnet
5. Migration Supabase per colonne `exchange_order_id`, `fee`, `fee_asset`
6. Blocco `if mode == "live": exit()` rimosso da `grid_runner.py`
7. **Test manuale**: un buy + un sell su BTCUSDT testnet, verificando che il fill Binance corrisponda a quanto scritto in DB

---

## Vincoli

- **NON cambiare la logica decisionale** (quando comprare, quando vendere, quanto). Solo il "come" dell'esecuzione.
- **NON toccare Sentinel/Sherpa**.
- **NON implementare limit orders**. Solo market per ora.
- **NON implementare WebSocket** per i fill. Usa il response sincrono del market order.
- Il testnet ha prezzi scollegati dal mercato reale e order book caotici (altri utenti ci testano). I prezzi "assurdi" sono normali — non è un bug.
- `/sapi` endpoints NON disponibili su testnet → il dust converter automatico (`/sapi/v1/asset/dust`) non funziona. Non è un problema: Step 2 previene la dust alla fonte.
- Il testnet viene resettato circa 1x/mese (ordini e bilanci azzerati, API key sopravvivono). Se capita durante i test, non è un bug — ricominciare.

---

## Sequenza

Questo brief è il **prerequisito** per:
- **Step 4** (Brief 66a): reset DB + restart orchestrator su testnet con $100 fresh
- **Step 5** (Brief 66a): reconciliation gate nightly

NON partire con Step 4 finché Step 3 non ha il test manuale buy+sell verde.
