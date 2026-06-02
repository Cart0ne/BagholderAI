# Report per CEO — S94a — newskeeper-haiku-classifier — 2026-06-01

**Brief sorgente:** `config/2026-06-01_S94a_brief_newskeeper-haiku-classifier.md`
(archiviato in `briefresolved.md/`)
**Commit:** `651bd45` (codice+test) — su `origin/main` e Mac Mini
**Esito:** ✅ SHIPPED + restart Mac Mini + verifica T+1 superata

---

## 1. In una riga

Il classifier regex di NewsKeeper (~65% falsi positivi) è stato sostituito da
**Haiku + pre-processing Python**, con feed macro aggiunti. È LIVE sul Mac Mini
e la prima finestra di segnali è **100% Haiku** (0 fallback).

## 2. Cosa è cambiato

- **Pre-processing Python** (`preprocessor.py`): per ogni titolo calcola in
  Python la `direction` (su/giù/flat/misto) — **autoritativa**. Lezione Brief
  81b: Python fa i conti, l'LLM legge. Haiku non fa mai matematica.
- **Haiku classifier** (`haiku_classifier.py`): `claude-haiku-4-5`, stessa
  chiave del commentary. Restituisce `theme / market_impact / severity /
  confidence`. **Guardrail Python post-call**: se Haiku contraddice la
  direzione nota la corregge; video/recap/confidence<0.3 declassano la
  severity; se Haiku non risponde → fallback regex **rumoroso** (evento
  `NEWSKEEPER_HAIKU_FALLBACK` + tag `classifier_version`).
- **Feed macro**: i candidati del brief (Reuters, AP) erano **morti**
  (HTTP 000/403). Prima cablati BBC Business + MarketWatch, poi **BBC swappato
  per CNBC Economy** su tua correzione (commit `8515378`): CNBC targetizza molto
  meglio il macro — 22/30 item passano il gate vs il rumore business generico
  di BBC. MarketWatch resta, rivalutato a T+7. Gate `_MACRO_KEYWORDS`
  (Fed/rates/inflazione/tariffe/…).
- **Pulizia**: scartati i video Decrypt a monte; cap 25 candidati/tick con
  **round-robin** tra i feed (così CoinDesk in giornata di news non affama i
  macro).

## 3. Verifica T+1 (meccanica)

- Startup log: `S2 — Haiku classifier … haiku=ready`.
- Primo tick: `25 candidate(s) -> 19 signal(s) written`, vocabolario nuovo
  (`market_crash/adoption/exploit/macro`).
- **DB**: tutte le 19 righe `classifier_version="haiku_s2"` → **0 fallback**.
  Guardrail attivo: ogni riga `direction=down` ha `impact=negative`.
- Nessun crash, processo vivo.

## 4. Problemi incontrati (e risolti)

1. **CHECK constraint** su `newskeeper_signals`: la colonna `source` accetta
   solo `{cryptopanic, rss_feeds, etf_flows, macro_calendar}`. → i feed macro
   scrivono `source="rss_feeds"`, l'identità (bbc/marketwatch) sta in
   `raw_data.feed_source`. `signal_type` è libero → **niente migration**.
2. **Cap che affamava i macro** (scoperto nello smoke test): risolto con
   round-robin.
3. **"breaks/tops" → falso `up`** ("Saylor breaks silence"): rimossi dal
   lessico (bias verso `mixed`, più sicuro perché la direction governa il
   guardrail).
4. **Chiave Haiku nell'ambiente standalone** (il rischio più serio): NewsKeeper
   gira **fuori dall'orchestrator**; se la chiave non ci fosse, in produzione
   girerebbe a regex in silenzio. Verificato sul Mac Mini che `config.settings`
   la carica all'import via `load_dotenv` → presente. Confermato a runtime
   (`haiku=ready` + 0 fallback).

## 5. Istruzioni di restart (per replicare)

Processo standalone, **non** orchestrator-managed. Sul Mac Mini:
```
cd /Volumes/Archivio/bagholderai
git pull --ff-only origin main
# stop:
kill -TERM <pid_python_newskeeper>   # SIGTERM = shutdown pulito (logga NEWSKEEPER_STOP)
# start (SEMPRE venv/bin/python3.13):
nohup caffeinate -i -s -- venv/bin/python3.13 -m bot.newskeeper.main >> logs/newskeeper.log 2>&1 < /dev/null & disown
```
PID attuali: python `27626`, caffeinate `27628` (ultimo restart 2026-06-01 22:04 CET, post-swap CNBC).

## 6. Prossimo (T+7, ~8 giugno)

Verifica qualità: tasso FP reale, direzioni corrette, **confronto lead/lag vs
Sentinel**, costo Haiku effettivo. È il dato che sblocca la decisione
*timing Sentinel: Phase B vs accelerare NewsKeeper S3-S4*.

## 7. Anti-assenso (protocollo §[7])

3 obiezioni reali sollevate **prima** di codare (CHECK constraint, cold-start
burst, chiave standalone) — tutte e 3 chiuse. La 4ª (direction primitivo su
titoli ambigui) è l'obiezione del CEO nel brief: mitigata da `confidence` +
bias a `mixed`; la valutiamo a T+7.
