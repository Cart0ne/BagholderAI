# QUICKSTART — BagHolderAI

Libretto di istruzioni rapido. Copia-incolla e vai.

## Avviare il bot

```bash
# 1. Vai nella cartella del progetto
cd ~/Desktop/BagHolderAI/Repository/bagholder

# 2. Attiva il virtual environment
source venv/bin/activate

# 3. Lancia il bot (paper trading)
python3 -m bot.grid_runner
```

Il bot gira in loop, controlla il prezzo ogni 30 secondi. Premi `Ctrl+C` per fermarlo.

## Modalità di lancio

```bash
# Normale — gira in loop, logga su Supabase
python3 -m bot.grid_runner

# Un solo ciclo — controlla una volta e esce
python3 -m bot.grid_runner --once

# Dry run — non scrive su database
python3 -m bot.grid_runner --dry-run

# Test connessione Binance
python3 main.py --test

# Stato configurazione
python3 main.py --status
```

## Fermare il bot

Premi `Ctrl+C` nel terminale. Il bot si ferma in modo pulito e mostra lo stato finale.

## Uscire dal virtual environment

```bash
deactivate
```

## Se il venv è rotto

Ricrea da zero:

```bash
deactivate
rm -rf venv
python3.13 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
```

**IMPORTANTE:** Usa `python3.13`, NON `python3` (che potrebbe puntare a 3.14, troppo nuovo).

## Test rapidi

```bash
# Test grid bot (niente rete, pura logica)
python3 tests/test_grid_bot.py

# Test scrittura su Supabase
python3 -c "
from db.client import TradeLogger
tl = TradeLogger()
result = tl.log_trade(
    symbol='BTC/USDT', side='buy', amount=0.0001, price=70000.0,
    fee=0.005, strategy='A', brain='grid',
    reason='TEST — delete this row', mode='paper'
)
print('SUCCESS:', result)
"

# Test Telegram
python3 -c "
from utils.telegram_notifier import SyncTelegramNotifier
n = SyncTelegramNotifier()
n.send_message('🎒 Test: BagHolderAI is alive!')
"
```

## Dove guardare i dati

- **Terminale:** log in tempo reale (trades, errori, status ogni 5 min)
- **Supabase:** Table Editor → tabella `trades` (tutti i trade loggati)
- **Telegram:** notifiche sul telefono (trade alerts + report giornaliero)

## File importanti

```
config/.env          → API keys (MAI pushare su GitHub)
config/settings.py   → Regole hardcoded e configurazione
bot/grid_runner.py   → Il loop principale del bot
bot/strategies/       → Logica del grid bot
db/client.py         → Scrittura su Supabase
utils/telegram_notifier.py → Notifiche Telegram
```
