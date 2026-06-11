# Report S102b — Sherpa Go Live (testnet)

**Data**: 2026-06-11 · **Sessione**: S102b
**Brief sorgente**: `config/2026-06-11_S102b_brief_sherpa-go-live.md` (SCOPE `sherpa-go-live`)
**Report a monte**: `2026-06-11_S102_RforCEO_sherpa-coherence-audit.md`
**Commit**: attivazione = env flag, **nessun cambio di codice** (vedi §1). Codice al restart: write-guard S102a `a867179` + **battito liveness LIVE `ce92ed2`** (D4, vedi §1). Docs: questo report + brief; memoria `reference_orchestrator_start` aggiornata.
**Stato**: ⏳ **DEPLOY PENDING** — Sherpa passa a LIVE solo al prossimo restart orchestrator (cumulativo con il write-guard S102a `a867179`). Comandi consegnati a Max (§3).

---

## 0. In una riga

Sherpa va in LIVE su testnet: comincerà a scrivere `buy_pct`, `sell_pct`, `idle_reentry_hours` in `bot_config` per BTC/SOL/BONK. L'attivazione è un **env flag al restart** (`SHERPA_MODE=live`), non un cambio di codice.

---

## 1. Anti-assenso: due drift brief↔repo, risolti con Max pre-implementazione

Il brief assumeva (a) un "file di config" con `SHERPA_MODE` da committare e (b) che in LIVE `sherpa_proposals` continui a popolarsi (verifica §3). Entrambe le assunzioni non reggono. Risolte con Max (decisioni qui sotto), senza ridiscutere il go-live (deciso dal Board).

### Drift 1 — `SHERPA_MODE` è un env flag, non un file

`SHERPA_MODE` è letto da `os.environ.get("SHERPA_MODE", "dry_run")` ([bot/sherpa/main.py:90](../bot/sherpa/main.py#L90)). L'orchestrator spawna Sherpa **senza `env=` esplicito** ([bot/orchestrator.py:105-109](../bot/orchestrator.py#L105-L109)) → eredita l'ambiente del processo orchestrator. Stesso pattern di `ENABLE_TF`/`ENABLE_SENTINEL`/`ENABLE_SHERPA` ([orchestrator.py:41-43](../bot/orchestrator.py#L41-L43)). Non esiste alcun file di config con `SHERPA_MODE`.

**Decisione Max (D1): env flag al restart.** Si aggiunge `SHERPA_MODE=live` al comando di avvio dell'orchestrator. Il default `dry_run` nel codice **resta intatto** (safety voluta, brief 70b). L'alternativa — cambiare il default in `main.py` a `live` — è stata scartata: rovescerebbe la safety (ogni restart futuro, anche crash-recovery automatico, partirebbe LIVE senza decisione esplicita).

⚠️ **Conseguenza dell'opzione env-flag**: se a un restart futuro si dimentica `SHERPA_MODE=live`, Sherpa torna **silenziosamente** a dry_run. Mitigazione: il comando canonico aggiornato è registrato in questo report (§3) e nella memoria `reference_orchestrator_start`.

### Drift 2 — in LIVE `sherpa_proposals` non riceve i cambi parametro (solo il battito)

Il ramo LIVE di `_handle_bot` chiama `write_parameter` (scrive `bot_config` + `config_changes_log`) + `log_event(SHERPA_ADJUSTMENT)`. Per i **cambi parametro** non chiama `_insert_proposal` → quei cambi NON finiscono in `sherpa_proposals` (sono in `config_changes_log`).

- La verifica del brief §3 ("sherpa_proposals ≤ 20 righe/giorno, write guard attivo") **non è eseguibile come scritta** per i cambi parametro: la traccia delle modifiche è in `config_changes_log` (`changed_by='sherpa'`) + `bot_events_log` (`SHERPA_ADJUSTMENT`, con `regime`/`volatility_multiplier` nei `details`).
- Il write-guard S102a (`a867179`) vive nel ramo dry_run e in LIVE **non viene eseguito** per il filtro dei cambi → resta inerte (utile come rete se Sherpa torna in dry_run, es. rollback).

**Decisione Max (D2): solo config_changes_log per i cambi parametro** — nessuno shadow-write completo delle proposte in LIVE.

**Decisione Max (D4, aggiunta in sessione): battito di liveness in LIVE.** Emersa verificando l'osservabilità: in LIVE, senza scritture su `sherpa_proposals`, (a) non si distingue "Sherpa vivo ma niente da cambiare" da "Sherpa bloccato/zombie" (il monitoraggio di processo dell'orchestrator copre solo il crash, non lo zombie), e (b) la lampada **STOP BUY** della dashboard admin — che legge `sherpa_proposals` ([sherpa-live.ts:64](../web_astro/src/scripts/sherpa-live.ts#L64)) — si **congela** su un valore vecchio. Fix (commit `ce92ed2`): in LIVE Sherpa scrive **una riga di SOLO battito** per coin ogni `SHERPA_HEARTBEAT_S` (4h) col regime/stop_buy corrente. È il polso, non il diario: i cambi parametro restano in `config_changes_log` (D2 invariato). Volume battiti in LIVE: 3 coin × 6/gg = **~18 righe/gg**, tutte heartbeat. Primo tick post-restart scrive subito → conferma boot + ri-aggancia la dashboard. Suite 198/198.

---

## 2. Cosa cambia (e cosa NO)

- **Codice**: nessuna modifica. Il go-live è un env flag. (Vincolo brief §4 "non toccare logica Sherpa" rispettato per costruzione; whitelist invariata — i 4 parametri mancanti restano per S103.)
- **Runtime al restart**: l'orchestrator parte con `SHERPA_MODE=live` → Sherpa scrive `bot_config`. Il restart è **cumulativo**: porta anche il write-guard S102a (`a867179`, già su main, inerte in LIVE) via `git pull` sul runtime.
- **Comportamento atteso al go-live** (ondata di convergenza, NON una singola modifica): l'amplitude cap ±30% muove i parametri a gradini di ~30%/tick (loop 120s). Esempio BTC `buy_pct` 0.50 → target di regime: ~7 tick × 2 min ≈ **14 minuti** di scritture successive, poi stabile. `sell_pct`/`idle` convergono in 1-3 tick. Quindi i primi ~15-20 minuti producono molti eventi `SHERPA_ADJUSTMENT`; ogni scrittura `bot_config` triggera l'hot-reload dei grid (`config_sync`). Atteso e innocuo su testnet.
- **idle_reentry_hours (Opzione C, decisione Board)**: 8 → 5.6 → … → target di regime in 2-7 tick. Nessun cambio al clamp.
- **Cooldown**: gli ultimi override manuali (`manual-ceo` su SOL, 8 giu) sono **oltre le 24h** → al go-live tutti e 3 i coin sono liberi; Sherpa scriverà su BTC/SOL/BONK al primo tick utile.

---

## 3. Comandi di restart per Max (Mac Mini, cumulativo S102a + go-live)

Repo runtime: `/Volumes/Archivio/bagholderai`. Procedura = quella S99b-b (graceful shutdown + caffeinate) **con l'aggiunta di `SHERPA_MODE=live`**.

```bash
# 1) Deploy del codice (porta a867179 write-guard + docs S102b)
ssh max@Mac-mini-di-Max.local
cd /Volumes/Archivio/bagholderai
git pull            # atteso: fast-forward fino a HEAD di origin/main

# 2) Trova il PID parent dell'orchestrator (atteso ~60346 da S99b-b, verifica)
ps aux | grep "[b]ot.orchestrator"

# 3) Graceful shutdown (sostituisci <PID> con quello trovato)
kill -TERM <PID>
sleep 8
ps aux | grep -E "[b]ot.orchestrator|[g]rid_runner|[b]ot.sentinel|[b]ot.sherpa"   # atteso: vuoto

# 4) Relaunch CON SHERPA_MODE=live (nota il flag nuovo rispetto a S81/S99b-b)
cd /Volumes/Archivio/bagholderai
nohup caffeinate -i -s -- env ENABLE_TF=true ENABLE_SENTINEL=true ENABLE_SHERPA=true SHERPA_MODE=live \
  ./venv/bin/python3.13 -m bot.orchestrator > /tmp/orchestrator_s102b.log 2>&1 &

# 5) Verifica boot (atteso: 7 processi — caffeinate + 3 grid + TF + Sentinel + Sherpa)
sleep 5
ps aux | grep -E "[c]affeinate|[b]ot.orchestrator|[g]rid_runner|[b]ot.sentinel|[b]ot.sherpa"
grep -i "sherpa" /tmp/orchestrator_s102b.log | tail -5     # atteso: "mode=live"
```

> Il log di boot di Sherpa deve dire `mode=live` (non `dry_run`). Se dice `dry_run`, il flag non è stato passato — ripeti il punto 4.

---

## 4. Verifica post-restart (riformulata, D2)

| Cosa | Query / dove | Atteso |
|---|---|---|
| Sherpa è LIVE | `/tmp/orchestrator_s102b.log` boot line | `Sherpa started (mode=live)` |
| Sherpa scrive parametri | `SELECT * FROM config_changes_log WHERE changed_by='sherpa' ORDER BY created_at DESC LIMIT 20;` | righe nuove per BTC/SOL/BONK su buy_pct/sell_pct/idle |
| bot_config cambia | `SELECT symbol,buy_pct,sell_pct,idle_reentry_hours,updated_at FROM bot_config WHERE managed_by='grid';` | valori diversi dai statici (BTC 0.50/1.50/8 → in movimento) |
| Eventi con contesto | `SELECT * FROM bot_events_log WHERE event='SHERPA_ADJUSTMENT' ORDER BY created_at DESC LIMIT 20;` | regime + volatility_multiplier nei details |
| Battito di liveness (D4) | `SELECT symbol,proposed_regime,proposed_stop_buy_active,created_at FROM sherpa_proposals ORDER BY created_at DESC LIMIT 6;` | ~18 righe/gg (battiti, 1/coin ogni 4h); primo battito subito dopo il restart |
| `sherpa_proposals` cambi parametro | — | **NON ci sono** in LIVE (i cambi sono in config_changes_log; sherpa_proposals contiene solo battiti, vedi Drift 2/D4) |
| Dashboard STOP BUY | admin.html stat-row Sherpa | si aggiorna (legge i battiti freschi); non più congelata |
| Nessun impatto altri brain | grid/tf/sentinel/newskeeper logs | invariati |
| Cooldown override Board | cambio manuale → riga `config_changes_log` `changed_by='manual-ceo'` | Sherpa salta quel parametro per 24h (salvaguardia) |

---

## 5. Decisions (decision log)

1. **DECISIONE (Max D1)**: attivazione via env flag `SHERPA_MODE=live` al restart, default codice `dry_run` invariato. **RAZIONALE**: coerente col pattern ENABLE_*; non rovescia la safety "default dry_run". **ALTERNATIVE**: cambio default in main.py (scartata: ogni restart futuro partirebbe LIVE). **FALLBACK**: rimuovere `SHERPA_MODE=live` dal comando al prossimo restart → torna dry_run.
2. **DECISIONE (Max D2)**: i cambi parametro restano solo in config_changes_log, niente shadow-write completo delle proposte in LIVE. **RAZIONALE**: in LIVE Sherpa è attuatore (design Sprint 1); la traccia config_changes_log + bot_events_log basta al Board. **ALTERNATIVE**: shadow-write di ogni proposta (scartata: oltre scope). **FALLBACK**: aggiungere `_insert_proposal` completo nel ramo LIVE se il Board cambia idea.
3. **DECISIONE (Max D4)**: battito di liveness in LIVE (commit `ce92ed2`). **RAZIONALE**: il monitoraggio di processo dell'orchestrator copre il crash ma non lo zombie (processo vivo, loop fermo); serve un battito periodico per distinguerli, e riaggancia anche la dashboard STOP BUY. **ALTERNATIVE**: heartbeat su `bot_events_log` (scartata: non risolve la dashboard, che legge sherpa_proposals); affidarsi solo al monitoraggio crash (scartata: lo zombie resterebbe invisibile). **FALLBACK**: rimuovere il blocco heartbeat dal ramo LIVE (reversibile, isolato).
4. **NOTA**: il write-guard S102a (`a867179`) è inerte in LIVE per i cambi parametro (vive nel ramo dry_run). Resta valido come rete in caso di ritorno a dry_run.

---

## 6. Roadmap impact

Nessuno pubblico (brief §5). Sherpa LIVE su testnet è un passo interno; la comunicazione avverrà dopo osservazione e decisione Board. Roadmap Sentinel-first: questo è lo **step 4** (Sherpa LIVE testnet) — sbloccato dal report S102. Prossimo: osservazione + S103 (4 parametri mancanti nella whitelist).

---

## 7. Cosa resta aperto

- **Restart**: non ancora eseguito (decisione Max: lo fa lui). Fino ad allora Sherpa è DRY_RUN e `sherpa_proposals` continua col volume pre-fix (~2.100/gg, perché anche il write-guard è pending deploy).
- **S103**: aggiunta dei 4 parametri mancanti alla whitelist (stop_buy_drawdown_pct, stop_buy_unlock_hours, dead_zone_hours, profit_target_pct) — brief separato.
- **Gate idle (S102 §B3)**: chiuso da decisione Board Opzione C (accettato il rientro nel range di design).
