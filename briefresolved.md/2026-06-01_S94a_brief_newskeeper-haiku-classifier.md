# Brief S94a — newskeeper-haiku-classifier — 2026-06-01

**Basato su:** PROJECT_STATE.md aggiornato 2026-06-01 (S93a)
**Contesto:** NewsKeeper Brain #5 Session 2. Analisi 8 giorni (24 maggio–1 giugno)
ha confermato che il classifier regex è inutilizzabile: ~65% falsi positivi,
direzioni invertite, severity inflazionata, spam video Decrypt.
Questo brief sostituisce il regex classifier con Haiku LLM + Python
pre-processing, e aggiunge feed RSS macro.

**Roadmap impact:** Sblocca l'osservazione pulita di 7 giorni necessaria per
decidere Sentinel Phase B vs accelerare NewsKeeper S3-S4. Prerequisito per
il go-live mainnet (sequenza: NewsKeeper funzionante → Sherpa testnet →
dry_run → Board approval).

---

## Timeline di validazione

- **T+1 giorno:** verifica meccanica — Haiku risponde? I segnali arrivano
  in `newskeeper_signals`? Nessun crash? Feed macro produce risultati?
- **T+7 giorni:** verifica qualità — tasso FP, direzioni corrette,
  confronto lead/lag vs Sentinel, costo Haiku effettivo.

---

## Cosa cambia

### 1. Python pre-processing (NUOVO modulo)

Nuovo file: `bot/newskeeper/preprocessor.py`

Riceve titolo + description da RSS. Restituisce una busta strutturata
(dict Python) con questi campi:

```python
{
    "title": str,              # titolo originale
    "description": str,        # description originale (può essere None)
    "numbers": [               # lista di numeri estratti
        {"value": 528, "unit": "M", "currency": "USD", "context": "outflow"},
        {"value": -15, "unit": "%", "context": "price change"},
    ],
    "direction": str,          # "up" | "down" | "flat" | "mixed"
    "content_type": str,       # "article" | "video" | "recap" | "opinion"
    "entities": [str],         # ["BTC", "ETF", "SEC", "Aave", ...]
    "feed_source": str,        # "coindesk" | "cointelegraph" | "decrypt" | "reuters" | ...
}
```

**Regole critiche per `direction`:**
- "losses fall 90%" → `direction: "up"` (calano le perdite = positivo)
- "outflows of $1.67B" → `direction: "down"` (deflussi = negativo)
- "Bitcoin slides under $73K" → `direction: "down"`
- "BTC surges past $80K" → `direction: "up"`
- Nessun numero chiaro nel titolo → `direction: "mixed"`

Questa è la lezione del Brief 81b (commentary): **Python calcola la
direzione, l'LLM la legge**. Haiku NON deve fare math.

**Regole per `content_type`:**
- Se `link` contiene `/videos/` → `"video"`
- Se il titolo contiene "here's what happened" o pattern recap → `"recap"`
- Default → `"article"`

### 2. Haiku classifier (sostituisce regex severity/direction)

Nuovo file: `bot/newskeeper/haiku_classifier.py`

Riceve la busta strutturata dal preprocessor.
Chiama Haiku (claude-haiku-4-5-20251001) con un prompt stretto.

**Output Haiku (JSON):**

```json
{
    "theme": "market_crash | regulatory | adoption | exploit | macro | irrelevant",
    "market_impact": "positive | negative | neutral",
    "severity": "critical | high | medium | low",
    "confidence": 0.0-1.0,
    "reasoning": "1 frase max"
}
```

**Regole nel prompt Haiku (MANDATORIE):**

```
You classify crypto/macro news for a trading system.
You receive pre-processed structured data. NEVER do math.
The `direction` field is pre-computed by Python and is AUTHORITATIVE.

Rules:
1. If direction="down", market_impact CANNOT be "positive"
2. If direction="up", market_impact CANNOT be "negative"
3. If content_type="video", severity is at most "low"
4. If content_type="recap", severity is at most "low"
5. theme="irrelevant" for news that don't affect crypto markets
6. Respond ONLY with JSON, no other text
```

**Guardrail post-call (Python, in haiku_classifier.py):**
Dopo aver ricevuto la risposta Haiku, Python verifica:
- Se `direction == "down"` e Haiku dice `market_impact == "positive"` →
  override a `"negative"`, log warning
- Se `direction == "up"` e Haiku dice `market_impact == "negative"` →
  override a `"positive"`, log warning
- Se `confidence < 0.3` → declassa severity a `"low"`
- Se Haiku non risponde o errore → **fallback al regex attuale**
  (meglio un segnale rumoroso che nessun segnale)

**Costi:** ~0.001-0.002€ per call. Con ~15-20 segnali/giorno (incluso
macro), stimiamo ~€0.60-1.00/mese. Budget accettabile pre-mainnet.

**API key:** usa la stessa chiave Anthropic che il sistema già usa per
il commentary Haiku (`daily_commentary.py`). Verifica come è configurata
(env var `ANTHROPIC_API_KEY` o simile) e riusa lo stesso pattern.

### 3. Feed RSS macro (NUOVI feed)

File modificato: `bot/newskeeper/readers/rss_feeds.py`

Aggiungere feed macro a `_FEEDS`:

```python
_FEEDS = [
    # Crypto (esistenti)
    ("coindesk", "https://www.coindesk.com/arc/outboundfeeds/rss"),
    ("cointelegraph", "https://cointelegraph.com/rss"),
    ("decrypt", "https://decrypt.co/feed"),
    # Macro (NUOVI)
    ("reuters_business", "<URL da verificare>"),
    ("ap_business", "<URL da verificare>"),
]
```

**CC: verifica le URL dei feed macro prima di implementare.**
Candidati: Reuters Business RSS, AP News Business, BBC Business.
Serve che il feed sia: (a) gratuito, (b) RSS 2.0 standard, (c) attivo
(HTTP 200 + contenuto valido). Testa con `curl` prima di cablare.

**Filtro keyword per feed macro:** il gate `_CRYPTO_KEYWORDS` attuale
rimane per i feed crypto. Aggiungere `_MACRO_KEYWORDS`:

```python
_MACRO_KEYWORDS = re.compile(
    r"\b(fed|fomc|rate hike|rate cut|interest rate|tariff|"
    r"gdp|inflation|recession|employment|unemployment|"
    r"sanctions|treasury|geopolitical|war|trade war|"
    r"oil price|commodities|dollar|dxy|bond yield)\b",
    re.IGNORECASE,
)
```

**Routing:** ogni item RSS passa per il filtro corrispondente al tipo
di feed. Un item dal feed Reuters passa `_MACRO_KEYWORDS`, non
`_CRYPTO_KEYWORDS`. Un item CoinDesk passa `_CRYPTO_KEYWORDS` come oggi.

Implementazione suggerita: aggiungere un terzo campo alla tupla feed:

```python
_FEEDS = [
    ("coindesk", "https://...", "crypto"),
    ("reuters_business", "https://...", "macro"),
]
```

E nel loop di fetch:

```python
keyword_filter = _CRYPTO_KEYWORDS if feed_type == "crypto" else _MACRO_KEYWORDS
if not keyword_filter.search(text):
    continue
```

### 4. Fix dedup Decrypt video

File modificato: `bot/newskeeper/readers/rss_feeds.py`

I video Decrypt restano nel feed RSS per settimane e vengono
re-inseriti ogni volta che il TTL 24h in memoria scade.

**Fix:** nel loop di processing degli item, prima del keyword filter:

```python
link = item.get("link", "")
if "/videos/" in link:
    continue  # skip video content entirely
```

Motivazione: i video sono titoli clickbait YouTube con topic multipli
("Saylor buys BTC! Claude Meme! TGE reactions!"). Non sono notizie
classificabili. Scartarli a monte è più pulito che declassarli.

### 5. Aggiornamento signal_writer

File modificato: `bot/newskeeper/signal_writer.py`

Il campo `signal_type` oggi contiene `bearish_news` o `bullish_news`
(output del regex). Con Haiku, i campi in `newskeeper_signals` diventano:

- `signal_type`: valore di `theme` da Haiku (market_crash, regulatory,
  adoption, exploit, macro, irrelevant)
- `severity`: valore di `severity` da Haiku (critical, high, medium, low)
- `summary`: titolo originale (come oggi)
- `raw_data`: aggiungere al JSONB esistente i campi Haiku:
  `market_impact`, `confidence`, `reasoning`, `direction` (pre-computed),
  `classifier_version: "haiku_s2"`

**NOTA:** il cambio di valori in `signal_type` rompe la retrocompatibilità
con i 258 segnali esistenti. Questo è accettabile — i dati regex sono
noise e non hanno valore analitico. Nessuna migrazione necessaria.

### 6. Integrazione nel loop principale

File modificato: `bot/newskeeper/main.py`

Il loop attuale:
1. `rss_feeds.fetch_signals()` → lista di candidati classificati via regex
2. `signal_writer.write_if_changed()` per ciascuno

Il loop S2:
1. `rss_feeds.fetch_candidates()` → lista di item RSS filtrati (crypto
   keyword o macro keyword), NON classificati
2. `preprocessor.preprocess(item)` → busta strutturata
3. `haiku_classifier.classify(envelope)` → classificazione + guardrail
4. `signal_writer.write_if_changed()` con i nuovi campi

**Rename suggerito:** `fetch_signals()` → `fetch_candidates()` per
chiarire che il feed non classifica più.

---

## Decisioni delegate a CC

- Scelta URL feed macro (verifica con curl, pick i 2 migliori)
- Struttura interna di `preprocessor.py` (regex per numeri, heuristic
  per direction — CC è libero sulla implementazione)
- Pattern di chiamata Haiku (sync vs async, retry policy, timeout)
- Logging level e formato dei warning del guardrail

## Decisioni che CC DEVE chiedere

- Qualsiasi modifica a tabelle Supabase (schema `newskeeper_signals`)
- Qualsiasi modifica al loop interval (oggi 15 min)
- Qualsiasi nuovo env var richiesto oltre a `ANTHROPIC_API_KEY`
- Se un feed macro candidato non è disponibile/affidabile, chiedere
  prima di scegliere un'alternativa

---

## Vincoli — cosa NON cambiare

- `_CRYPTO_KEYWORDS` regex: resta come gate per feed crypto
- Il pattern write-on-change + heartbeat 30 min
- Il fatto che NewsKeeper è standalone (NON orchestrator-managed)
- La tabella `newskeeper_signals` e le sue colonne esistenti
  (aggiungere dati dentro `raw_data` JSONB è OK)
- Nessun import da altri brain (Sentinel, Sherpa) — comunicazione
  solo via Supabase
- Telegram resta off (env var `NEWSKEEPER_TELEGRAM_ENABLED=false`)

---

## Output atteso a fine sessione CC

1. `bot/newskeeper/preprocessor.py` — nuovo, testato
2. `bot/newskeeper/haiku_classifier.py` — nuovo, testato
3. `bot/newskeeper/readers/rss_feeds.py` — modificato (macro feeds +
   video filter + rename fetch_signals → fetch_candidates)
4. `bot/newskeeper/signal_writer.py` — modificato (nuovi campi)
5. `bot/newskeeper/main.py` — modificato (nuovo loop)
6. Test unitari per preprocessor (direction logic) e guardrail
7. Commit pushato a main, pronto per restart su Mac Mini
8. Report per CEO con: feed macro scelti, eventuali problemi,
   istruzioni di restart

---

## Obiezione CEO (mandatoria per protocollo S92)

Il rischio principale è che il preprocessor `direction` calculator sia
troppo primitivo per i titoli ambigui. "Bitcoin analysis eyes sharp
rebound after BTC collapses below M2 supply" — collapse (down) e
rebound (up) nello stesso titolo. Il campo `direction` sarà "mixed",
e Haiku dovrà decidere da solo. Questo è il caso residuo dove Haiku
può ancora sbagliare. Mitigazione: il campo `confidence` permette di
declassare i segnali dove Haiku non è sicuro. A 7 giorni valuteremo
se basta.
