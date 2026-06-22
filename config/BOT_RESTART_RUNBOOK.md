# Runbook — Riavvio bot sul Mac Mini

**Creato:** 2026-06-22, con la procedura collaudata durante il restart post-blackout del 22-giu (boot 18:07, restart bot 18:20).
**Scopo:** trasformare il riavvio dei bot da "ricostruzione a memoria dei comandi" a checklist copia-incollabile. Serve in due casi: **(A) cold start** dopo blackout/reboot del Mac Mini (tutto giù), **(B) restart graceful** per ricaricare codice nuovo (bot ancora vivi).

> Regola di governance (CLAUDE.md §5, S105b): **CC riavvia i bot SOLO se Max lo chiede esplicitamente.** Pull e push restano autonomi di CC; il restart no. Questo runbook documenta *come* farlo quando Max lo chiede, non autorizza CC a farlo di iniziativa.

---

## 0. Mappa di cosa gira (10 processi python + 3 wrapper caffeinate)

| Gruppo | Processo | Lancio | Note |
|---|---|---|---|
| **Managed** (1 padre + 7 figli) | orchestrator | `-m bot.orchestrator` | supervisor: spawna i 7 figli sotto |
| | grid BTC/SOL/BONK/ETH | `-m bot.grid_runner --symbol X/USDT` | 4 processi, spawnati dall'orchestrator |
| | Trend Follower | `-m bot.trend_follower.trend_follower` | Tier 1-2 LIVE |
| | Sentinel | `-m bot.sentinel.main` | slow loop LIVE |
| | Sherpa | `-m bot.sherpa.main` | `SHERPA_MODE=live` |
| **Standalone** (NON managed dall'orchestrator) | NewsKeeper v1 | `-m bot.newskeeper.main` | scrive `news_signals`; logger `bagholderai.newskeeper` |
| | NewsKeeper v2 barometro | `-m bot.newskeeper_v2` | shadow, stato persistito; logger `bagholderai.newskeeper_v2` |

I 7 figli dell'orchestrator NON vanno lanciati a mano: li spawna l'orchestrator. **Tu lanci 3 processi**: orchestrator, NewsKeeper v1, NewsKeeper v2.

**Cose che NON sono bot e NON si toccano qui:** `x_poster`, cron `reconcile_binance` (03:00 Europe/Rome), cron `db_maintenance` (06:00).

---

## 1. Note critiche (leggere PRIMA di lanciare)

- **Python:** sempre `venv/bin/python3.13` (mai `python3` — rischio phantom 3.14). Il venv è su `/Volumes/Archivio/bagholderai/venv`.
- **API key Haiku:** `ANTHROPIC_API_KEY` **NON** è nell'ambiente shell né nel `.env` di root. Vive in **`config/.env`**, caricata da `load_dotenv` in [config/settings.py:14](settings.py#L14). I NewsKeeper la prendono importando `config.settings` → all'avvio devono loggare `haiku=ready`. Se loggano `haiku=...` falso, degradano LOUDLY al fallback regex: vuol dire che `config/.env` manca o è incompleto.
- **Volume montato:** il repo runtime è su `/Volumes/Archivio/bagholderai`. Se `/Volumes/Archivio` non è montato, niente parte. Verifica: `ls /Volumes/Archivio/bagholderai` deve elencare il repo.
- **caffeinate:** ogni processo si lancia sotto `caffeinate -i` (impedisce l'idle sleep del Mac di ucciderlo). `nohup … &` lo stacca dalla sessione SSH.
- **Flag env orchestrator** (catturati dal restart S106a/S108, verificati 22-giu): `ENABLE_TF=true ENABLE_SENTINEL=true ENABLE_SHERPA=true SHERPA_MODE=live SHERPA_TELEGRAM_ENABLED=true`. ⚠️ `SHERPA_TELEGRAM_ENABLED=true` è ancora attivo ma **da togliere a un restart futuro** (PROJECT_STATE §1): se Max conferma, ometterlo.
- **NewsKeeper entrypoint asimmetrico:** v1 = `-m bot.newskeeper.main` (il package `bot/newskeeper/` NON ha `__main__.py`). v2 = `-m bot.newskeeper_v2` (questo SÌ ha `__main__.py`). Non confonderli.

---

## 2. Pre-check (1 min, read-only)

```bash
# Raggiungibilità + da quanto è su (conferma reboot post-blackout)
ssh max@Mac-mini-di-Max.local "uptime"

# Volume montato + allineamento git (serve pull?)
ssh max@Mac-mini-di-Max.local 'cd /Volumes/Archivio/bagholderai && \
  git fetch origin -q && git status -s && \
  echo "ahead/behind vs origin/main:" && git rev-list --left-right --count HEAD...origin/main'

# Cosa è già vivo? (cold boot = vuoto; graceful = 10 processi)
ssh max@Mac-mini-di-Max.local "ps aux | grep -E '[-]m bot\.' | grep -v grep"
```

- `git rev-list … 0 0` = allineato, **nessun pull**. Se "behind" > 0: `git pull` PRIMA di lanciare (così riparte col codice nuovo). Promemoria: il Mac Mini **non pusha** via SSH (osxkeychain) — se serve pushare, si pusha dalla MacBook Air e si fa `git pull` sul Mini.

---

## 3. Scenario A — COLD START (dopo blackout / reboot, tutto giù)

Il pre-check §2 mostra 0 processi. Non c'è nulla da fermare: si lancia e basta.

```bash
ssh max@Mac-mini-di-Max.local 'cd /Volumes/Archivio/bagholderai
TS=$(date +%Y%m%d_%H%M%S)
# 1) Orchestrator (spawna i 7 figli)
ENABLE_TF=true ENABLE_SENTINEL=true ENABLE_SHERPA=true SHERPA_MODE=live SHERPA_TELEGRAM_ENABLED=true \
  nohup caffeinate -i venv/bin/python3.13 -m bot.orchestrator > logs/orchestrator_restart_$TS.log 2>&1 &
echo "orchestrator wrapper pid=$!"
sleep 1
# 2) NewsKeeper v1
nohup caffeinate -i venv/bin/python3.13 -m bot.newskeeper.main >> logs/newskeeper.out 2>&1 &
echo "newskeeper_v1 wrapper pid=$!"
sleep 1
# 3) NewsKeeper v2 barometro
nohup caffeinate -i venv/bin/python3.13 -m bot.newskeeper_v2 >> logs/newskeeper_v2.out 2>&1 &
echo "newskeeper_v2 wrapper pid=$!"
sleep 4
tail -14 logs/orchestrator_restart_$TS.log'
```

Atteso nel log orchestrator: `Brain flags: TF=True SENTINEL=True SHERPA=True`, 4 `Grid bot spawned`, `Trend Follower spawned`, `Sentinel spawned`, `Sherpa spawned`, 2 `Telegram message sent`.

---

## 4. Scenario B — RESTART GRACEFUL (bot vivi, ricarico codice)

Qui i NewsKeeper standalone **NON si toccano** (non c'entrano col codice dei brain). Si riavvia solo l'orchestrator.

```bash
# 1) CATTURA gli env flag esatti dal processo LIVE. ⚠️ `ps -o command=` NON li mostra:
#    gli ENABLE_*/SHERPA_* stanno nell'AMBIENTE, non in argv → serve `ps eww`.
#    (Verificato 22-giu: ps eww funziona sul Mac Mini per il pid python orchestrator.)
ssh max@Mac-mini-di-Max.local "ps eww -p \$(pgrep -f '[-]m bot.orchestrator') | tr ' ' '\n' | grep -E 'ENABLE_|SHERPA_|BINANCE_TESTNET'"

# 2) Shutdown graceful: SIGTERM all'orchestrator → propaga ai 7 figli
ssh max@Mac-mini-di-Max.local "pkill -TERM -f '[-]m bot.orchestrator'"
# attendi qualche secondo, poi verifica che i figli siano spariti
ssh max@Mac-mini-di-Max.local "ps aux | grep -E '[-]m bot\.(grid_runner|trend_follower|sentinel|sherpa|orchestrator)' | grep -v grep"

# 3) Rilancia SOLO l'orchestrator (step 1 dello Scenario A), con i flag catturati al punto 1
```

⚠️ Non uccidere i NewsKeeper in questo scenario. Se per sbaglio cadono, rilanciali con gli step 2-3 dello Scenario A.

---

## 5. Verifica post-restart (obbligatoria — §5 governance: "processi su + effetto a DB")

```bash
ssh max@Mac-mini-di-Max.local 'cd /Volumes/Archivio/bagholderai
echo "=== 8 managed + 2 standalone ==="
ps aux | grep -E "[-]m bot\." | grep -v grep | grep -v caffeinate | sed -E "s|.*Python(.app.*MacOS/Python\|/bin/python3.13) ||"
echo "=== NewsKeeper haiku=ready? ==="
tail -3 logs/newskeeper.out; tail -3 logs/newskeeper_v2.out
echo "=== effetto a DB: un grid sta loggando il ciclo? ==="
tail -3 logs/grid_ETH_USDT.log'
```

Checklist verde:
- [ ] **8 processi managed**: 1 orchestrator + 4 grid (BTC/SOL/BONK/ETH) + TF + Sentinel + Sherpa. (Nota: i figli girano col binario `…/Python.app/…/Python`, non con la stringa `venv/bin/python3.13` — è lo stesso venv via symlink. Per contarli usa i PID dal log orchestrator: `ps -p <pid1>,<pid2>,…`.)
- [ ] **2 NewsKeeper standalone** vivi, entrambi `haiku=ready`, v1 scrive `insert source=rss_feeds`, v2 logga `v2 tick … state=…`.
- [ ] **Telegram di avvio** ricevuto (2 messaggi dall'orchestrator).
- [ ] **Effetto a DB**: un grid logga `IDLE RECALIBRATE CHECK` / cicli con timestamp aggiornato.

---

## 6. Trappole note

- **ETH grid in "capital-exhausted" ($0 cash, holda ~0.027 ETH):** è lo stato pre-esistente dell'handoff TF→grid (S108), **non** un bug del restart. Il grid bootta "capital-exhausted state restored silently" e holda: corretto.
- **`grep python3.13 -m bot` conta solo 3:** matcha solo i wrapper `caffeinate`, non i 7 figli (binario `Python.app`). Non è un'anomalia — vedi nota in §5.
- **`config/.env` mancante o senza key:** NewsKeeper degradano al regex fallback (haiku NON ready). Sintomo nei `.out`. Non è fatale per il trading (i brain non dipendono da Haiku) ma la classificazione news peggiora.
- **NewsKeeper v1 e v2 sono ENTRAMBI da rilanciare in cold start.** Sono standalone: il blackout li uccide come tutto il resto. In un restart graceful invece restano su e non si toccano.

---

## 7. Riferimenti

- Governance restart: `CLAUDE.md §5` (regola S105b).
- Flag orchestrator verificati: memoria `reference_orchestrator_start.md` (S106a) + `PROJECT_STATE.md §1`.
- Push workaround Mac Mini: memoria `reference_macmini_push_workaround.md`.
- Reset testnet (procedura DATI, diversa da questa): `config/TESTNET_RESET_RUNBOOK.md`.
