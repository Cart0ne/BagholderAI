# Report sessione 83 — NewsKeeper Brain #5 scaffold Session 1

**Data:** 2026-05-24
**Brief:** NewsKeeper Architecture (Board-approved 2026-05-23, 4 sessioni)
**Scope sessione:** Session 1 — DB + bot package + Modulo 1 (CryptoPanic, poi pivotato a RSS feeds) + test standalone, NO orchestrator integration, NO modulo ETF flows, NO modulo macro_calendar, NO Strategist+Haiku.
**Esito:** SHIPPED. Commit `49473a9` pushato su origin/main. NewsKeeper LIVE come processo standalone sul Mac Mini (PID 78098).

---

## TL;DR — cosa è successo

1. **Migration Supabase** `newskeeper_signals` applicata: tabella + RLS + 2 policy + CHECK constraints + 3 indici. RLS-from-day-1 per nuova regola formalizzata (Max: "ce lo siamo dimenticati in passato e poi rincorriamo").

2. **Scaffold `bot/newskeeper/`** (5 file, 429 righe): `main.py` (loop 15min + SIGINT/SIGTERM), `signal_writer.py` (write-on-change + heartbeat 30min, S79c pattern), `readers/rss_feeds.py` (3 RSS + classifier). Pattern modulare clone di `bot/sentinel/inputs/`.

3. **Pivot CryptoPanic → RSS feeds.** Il brief assumeva CryptoPanic free Developer API, ma quella tier è **discontinued dal 1 aprile 2026** (verificato live: l'endpoint citato dal brief restituisce HTTP 404). Recon su 4 fonti alternative con prezzi → Board ha scelto RSS feeds (zero auth, zero paywall risk, zero costi).

4. **Test live MBP** (con `.env` Mac Mini scopiato per test, gitignored): 28 INSERT in 1 tick, shutdown SIGTERM clean. TRUNCATE righe test prima del deploy.

5. **Deploy standalone Mac Mini** (NON via orchestrator — S2): PID 78098 + caffeinate parent 78100, launch alle 10:56 CET. Primo tick LIVE: **13 signal inseriti** (2 critical, 8 bearish, 5 bullish).

6. **Classifier rumoroso noto.** Keyword regex context-blind ha ~60% falsi positivi visibili a campione. Decisione Max (ship as-is per osservazione 7gg) coerente con principio data-first. Calibration o anticipo Haiku-classify in S2.

7. **Push S82** (homepage WatchtowerCard + SherpaLockedCard) sbloccato in chiusura. Il sito ora rivela pubblicamente NewsKeeper come "duo Sentinel+NewsKeeper" nella card Watchtower.

---

## 1. Sources delle news — i 3 RSS feed scelti

Tutti verificati live oggi (2026-05-24), HTTP 200, schema RSS 2.0 standard.

| Feed | URL | Items per tick | Note |
|------|-----|----------------|------|
| **CoinDesk** | `https://www.coindesk.com/arc/outboundfeeds/rss` | ~25 | URL canonico segue redirect 308 (rimuovere trailing `/`). News editoriali mainstream. |
| **CoinTelegraph** | `https://cointelegraph.com/rss` | ~30 | Schema con namespace `media:` + `dc:`. News + analisi. |
| **Decrypt** | `https://decrypt.co/feed` | ~39-59 | Mix crypto + general-tech (Decrypt copre anche AI/Web3 in senso lato). Filtro `_CRYPTO_KEYWORDS` taglia gli articoli non-crypto a monte. |

**Totale aggregato per tick:** ~94-114 items. Costo: €0/mese. Auth: nessuna.

**Perché questi 3 e non altri:**
- CryptoPanic (brief originale): free dead da 1 aprile 2026, paid ~$30/mese (sfora budget brief < €1/mese)
- CoinGecko `/news`: PRO subscribers only (verificato HTTP 401)
- CoinMarketCap `/content/latest`: probabile paid tier (CMC docs)
- CryptoCompare `/news/v2`: free tier 100k call/mese ma richiede sign-up + API key
- NewsAPI.org: 100 req/giorno free (loop 15min sfora soglia), generalista non-crypto

**Vantaggio collaterale:** l'architettura modulare `readers/` permette di aggiungere una fonte = 1 file nuovo + 1 riga di import in `main.py`. Se in futuro vogliamo riaggiungere CryptoPanic paid o aggiungere RSS aggiuntivi (The Block, Bitcoin Magazine, ecc.), zero refactor.

---

## 2. Schema della tabella `newskeeper_signals`

```sql
CREATE TABLE public.newskeeper_signals (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source TEXT NOT NULL CHECK (source IN ('cryptopanic', 'rss_feeds', 'etf_flows', 'macro_calendar')),
    signal_type TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    summary TEXT NOT NULL,
    raw_data JSONB,
    expires_at TIMESTAMPTZ
);
-- + 3 indici: (source, signal_type, created_at DESC), (severity, expires_at), (created_at DESC)
-- + RLS enabled + 2 policy anon INSERT/SELECT (modellate su sentinel_scores)
```

**Note operative:**
- `source = 'cryptopanic'` mantenuto nel CHECK constraint per future paid-tier re-add senza migration
- `expires_at = NULL` significa "nessuna scadenza"; per RSS oggi è `now + 24h` (brief)
- TTL differenziato per source (ETF +daily-close, macro +event-window) è parcheggiato per S2 come da nota Max

---

## 3. Classifier — come funziona oggi e perché è rumoroso

**Pipeline:** per ogni articolo dei 3 feed:
1. Filtro `_CRYPTO_KEYWORDS` (regex bitcoin|btc|ethereum|sol|crypto|...) — skip se non matcha
2. Filtro `_CRITICAL_BEARISH` (crash|plunge|exploit|hack|...) → severity critical
3. Filtro `_HIGH_BEARISH` (sec|fomc|cpi|tariff|warning|...) → severity high
4. Filtro `_HIGH_BULLISH` (rally|surge|ATH|inflow|approval|...) → severity high
5. Se niente matcha, skip

**Falsi positivi visibili nel sample test (28 INSERT MBP):**

| Title (truncato) | Classificato | Realtà | Motivo errore |
|------------------|--------------|--------|---------------|
| "The White Whale up 10x in a week! Saylor buys $109M BTC!" | bearish critical | bullish | Match keyword critical in sommario |
| "Crypto is Green! Up 6-9%! Memes outperform!" | bearish high | bullish | Match qualche bear keyword in sommario |
| "Saylor buys $109M BTC!" | bearish critical | bullish | Idem |
| "A16z raise $15B! Jerome Powell vs Trump!" | bearish high | mixed | Match "Powell" / "Fed" via regex |
| "Crypto rebounds after Trump TACO'd on Tariffs!" | bearish high | bullish | Match "tariff" → bearish, ma contesto è "rebounds" |
| "SEC approves Nasdaq to list Bitcoin index options" | bearish high | bullish | Match "SEC" → bearish, ma "approves" è bullish |

**Root cause:** regex non capisce contesto. "Bitcoin rebounds despite Fed hawkish" matcha "hawkish" → bearish anche se il punto è "rebounds".

**Mitigation a regime:**
- Volume previsto con heartbeat 30min: ~192 row/giorno (4 combinazioni signal_type×severity × 48 cicli)
- Dedupe per `guid` con TTL 24h evita reinserimento dello stesso articolo
- Storage Supabase free tier copre comodamente

**Tre vie per S2 (decisione Board nelle prossime settimane):**

| Opzione | Effort | Risultato atteso | Costo |
|---------|--------|------------------|-------|
| Calibrare regex (word-boundary su acronimi, rimuovere "warning"/"risk-off" troppo generici, BOTH-bearish-AND-bullish → skip) | 30-60 min | rumore 60% → 20-25% | €0 |
| Anticipare Haiku-classify (era S3-4) | 1.5-2h | rumore < 10%, context-aware | ~€0.50/mese |
| Lasciar così e leggere il dataset reale per capire pattern di falsi positivi sistematici | 0 effort, 7gg attesa | dati per decidere meglio | €0 |

**Mia raccomandazione:** lasciar correre 7gg, raccogliere ~1.3k righe reali, poi decidere su pattern visti. Coerente con `feedback_data_first_then_review`.

---

## 4. Stato live attuale

**Processi sul Mac Mini (2026-05-24 11:00 CET):**
- Orchestrator `28217` + caffeinate `28219` + 5 figli managed (3 Grid + TF + Sentinel + Sherpa) — invariato da S81 restart
- **NEW** NewsKeeper standalone `78098` + caffeinate parent `78100` — standalone (NON orchestrator-managed)

**Totale processi:** 7 orchestrator-managed + 2 NewsKeeper standalone = 9.

**Limitation S1 nota:** se Mac Mini riavvia, NewsKeeper non si rialza (l'orchestrator non lo conosce). Mitigation S2 = aggiungere `ENABLE_NEWSKEEPER` env + `_spawn_newskeeper()` in `bot/orchestrator.py`, stesso pattern Sentinel/Sherpa.

**Telegram:** silenziato di default (env `NEWSKEEPER_TELEGRAM_ENABLED=false`), coerente con memoria CC "no Telegram alerts da brain non-Grid".

---

## 5. Cosa NON è stato fatto e perché

- **Modulo 2 ETF flows** + **Modulo 3 macro_calendar**: scope Sessione 2 brief. Non fatti per non sforare il piano concordato.
- **Orchestrator wiring**: brief diceva esplicitamente "for S1 the process is launched manually for stand-alone tests, no orchestrator wiring yet".
- **Strategist + Haiku-classify**: scope Sessione 3-4 brief.
- **Dashboard widget `/admin`**: brief separato dopo core working.
- **Test unit**: scope S2 quando il pattern reader sarà rodato (rischio testare codice che cambierà in S2 con Haiku).
- **TTL differenziato per source**: parcheggiato in S2 come da nota Max ("ETF = daily close, macro = event-based").
- **Calibration classifier**: parcheggiato in S2 per data-first.

---

## 6. Audit cadenze (check obbligatorio fine sessione)

Conteggio sui FILE `audits/audit_report_*.md`, non sulle righe §9 (regola formalizzata 2026-05-15, vedi `CLAUDE.md §1`):

- **Area 1 (tecnica, cadenza 30gg):** ultimo audit 2026-05-07 (17gg fa) — dentro soglia ✅ (scade 2026-06-06)
- **Area 2 (coerenza progetto, cadenza 90gg / fine-volume):** **mai eseguito** — ⚠️ **DOVUTO** (proposta CC già in §6 da S78, eseguibile durante 7-10gg osservazione Sherpa Sprint 2 / NewsKeeper). Aggiunta urgenza S83: NewsKeeper è il 5° brain, ha senso un audit Area 2 prima di S2 che aggiunge i moduli ETF + macro + integrazione orchestrator + Strategist.
- **Area 3 (strategy & marketing, cadenza 90gg):** ultimo audit 2026-05-15 (9gg fa) — dentro soglia ✅

⚠️ **Audit Area 2 dovuto: mai eseguito. Proponi a Max di pianificarlo prima dell'apertura di S2.**

---

## 7. Decisioni per il CEO

1. **Approvi Sessione 2 brief NewsKeeper** (Modulo 2 ETF flows + Modulo 3 macro_calendar + integrazione orchestrator)? Quando? Possibile timeline: dopo che osserviamo NewsKeeper standalone 7gg + risolto l'audit Area 2.

2. **Sul classifier**: preferenze tra le 3 vie sopra (calibrare regex / anticipare Haiku / lasciar correre 7gg)? La mia raccomandazione è lasciar correre, ma se vuoi accelerare possiamo calibrare in 30-60 min in S83b.

3. **Sull'audit Area 2**: ti propongo CC fresh con `audit_request_20260527_area2_coherence.md` lunedì 27 (3gg di gap per lasciare NewsKeeper raccogliere dati che l'audit potrà valutare). Approvi?

---

## 8. Commit + push effettuati

- `cdb5ff8` (S82, già su origin pre-sessione) — docs BUSINESS_STATE S82 closure
- `85b2751` (S82, già su origin pre-sessione) — homepage WatchtowerCard + Blog section
- `49473a9` (S83, push effettuato in chiusura sessione) — bot: NewsKeeper Brain 5 scaffold

**Files modificati S83:**
- Aggiunti: `bot/newskeeper/__init__.py`, `bot/newskeeper/main.py`, `bot/newskeeper/signal_writer.py`, `bot/newskeeper/readers/__init__.py`, `bot/newskeeper/readers/rss_feeds.py`, `briefresolved.md/brief_s83_newskeeper_architecture.md`
- Rimosso: `config/brief_newskeeper_architecture.md` (moved to briefresolved.md/)
- Supabase: 2 migration applicate via MCP (CREATE TABLE + ALTER source CHECK), non in repo

---

*Report generato da Claude Code (Intern). Allegati al PROJECT_STATE.md aggiornato S83.*
