# Brief 77c — Admin /admin: 2 widget per visualizzare Sentinel slow loop

**Da:** Claude Code (Intern) — proposta al Board
**Per:** CEO (Claude, claude.ai) — approvazione richiesta
**Data:** 2026-05-14 sera
**Basato su:** Sprint 2 LIVE su Mac Mini dalle 21:46:23 CET (commit `a62e5d5`)
**Stima:** **45-60 minuti** (15 min widget A + 30 min widget B + 10 min QA)
**Priorità:** MEDIA — non blocca la sequenza Sentinel-first ma rende osservabile la fase 3 (osservazione 5-7 giorni)

---

## Contesto

Brief 77b shipped + restart Mac Mini fatto in chiusura S77. Sprint 2 è LIVE: Sentinel scrive `sentinel_scores` con `score_type='slow'` ogni 4h, Sherpa legge il regime dinamicamente. Verifica empirica end-to-end (DB query 21:46:23 UTC):

- Prima riga slow inserita 2s dopo restart: `regime=fear`, `risk=30`, `opp=65`, `fng=34`, `btc_dom=60.24%`, `cmc_seen=true`
- Sherpa ciclo successivo (19:48:23 UTC): `proposed_regime=fear` con BTC buy 1.0→1.8, sell 1.5→1.2, idle 1.0→2.0 (diverso da neutral del ciclo precedente)

**Problema**: tutto questo è visibile **solo via SQL query** sui dati DB. Per la **fase 3 della roadmap Sentinel-first (osservazione 5-7 giorni)** serve un canale visivo che Max (e potenzialmente in futuro lettori del sito) possano consultare senza aprire pgAdmin/Supabase Studio.

**Richiesta esplicita Board (Max, 2026-05-14 sera)**: aggiungere a `/admin` 1 o più grafici che mostrino cosa fa Sentinel slow.

---

## Scope (2 widget, ordine di priorità)

### Widget A — Regime banner (priorità alta, ~15 min)

**Cosa**: una riga in cima alla sezione Sentinel di `/admin` che mostra **stato istantaneo**:

```
┌─────────────────────────────────────────────────────────────────────┐
│ SENTINEL SLOW · regime: 🟡 FEAR · F&G: 34 (Fear)                    │
│ BTC dominance: 60.24% · last update: 6 min ago · next tick: 3h 54m  │
└─────────────────────────────────────────────────────────────────────┘
```

**Fonte dati**: 1 query a `sentinel_scores WHERE score_type='slow' ORDER BY created_at DESC LIMIT 1`. Estrae `raw_signals->>'regime'`, `fng_value`, `fng_label`, `btc_dominance`, calcola age e ETA next tick (created_at + 4h).

**Aggiornamento**: polling REST Supabase ogni 30s (pattern già usato in altre sezioni `/admin`).

**Layout**: 1 riga, ~700px wide, dentro l'esistente sezione "Sentinel + Sherpa" o sopra di essa.

**Edge cases**:
- Nessuna riga slow ancora (caso boot/fresh deploy): mostra `regime: — (boot)` + suggerimento "Sentinel just started, first slow tick within 1 minute"
- F&G stale fallback: mostra `regime: 🟢 NEUTRAL (fallback)` con tooltip "F&G data is stale (>36h), regime defaulted to neutral"
- CMC assente: mostra `BTC dominance: —` (non rompere il banner)

### Widget B — Regime timeline 7 giorni (priorità media, ~30 min)

**Cosa**: band chart degli ultimi 7 giorni dei regimi macro. Asse X tempo, asse Y "categorical" (5 buckets, dal panic al greed).

**Layout proposto**:

```
        21:46    01:46    05:46    09:46    13:46    17:46    21:46    ...
        ─────────────────────────────────────────────────────────────────
ext.G   │
greed   │
neutral │       ░░░░░░
fear    │░░░░░░░       ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
ext.F   │
        ─────────────────────────────────────────────────────────────────
```

**Versione alternativa** (più moderna, da preferire se possibile): band chart con riempimento colorato (5 colori, uno per regime). Stratificato come una "fascia regime" che cambia altezza nel tempo.

**Fonte dati**: query `sentinel_scores WHERE score_type='slow' AND created_at > now() - interval '7 days' ORDER BY created_at`. Tipicamente 42 record (24h/4h * 7gg).

**Sovrapposizione opzionale (decisione CEO)**: linea continua F&G value (0-100) sovrapposta al band chart. Mostra la fonte del regime senza dover guardare ogni record. **Default proposto**: SÌ, sottile, semi-trasparente.

**Tooltip on hover**: data/ora, regime, F&G value, BTC dominance, eventuali fallback reason.

**Edge cases**:
- Meno di 7 giorni di dati (es. primo restart): mostra "Showing X hours since first slow tick" e adatta asse X
- Buchi nei dati (es. orchestrator crashato per N ore): linea spezzata, no interpolazione

---

## Decisioni delegate al CEO

### 1. Colori dei 5 regimi

**Proposta CC (palette standard "sentiment heatmap")**:
- `extreme_fear` → **#1e3a8a** (deep blue) — "deep panic"
- `fear` → **#3b82f6** (blue) — "cautious"
- `neutral` → **#9ca3af** (grey) — "indifferent"
- `greed` → **#f59e0b** (amber) — "warming"
- `extreme_greed` → **#dc2626** (red) — "danger zone, top"

Razionale: gradiente blu (cool, panic) → grey (neutral) → caldo (greed) → rosso (sell zone). Coerente con la convenzione finanziaria "rosso = pericolo top di mercato" che è opposta alla convenzione semaforica "rosso = stop" — è una scelta importante e voglio chiarirla con te.

**Alternativa 1**: gradiente semaforico — fear=verde (buying opportunity), greed=rosso (danger). Coerente con il mapping risk/opp interno: fear ha opp alta = verde "go".

**Alternativa 2**: monocromo con saturazione — extreme_fear darkest blue, neutral grey, extreme_greed darkest blue (saturazione=intensità del sentiment, no judgment).

Il CEO decide. Default CC: palette standard.

### 2. Sovrapposizione F&G line sul band chart

- **Default proposto**: SÌ
- Razionale: senza F&G non si capisce *perché* il regime è quello. Con F&G visibile, Max può vedere "regime fear al value 34, regime neutral al value 55" → contesto immediato

### 3. Aggiornamento polling rate

- **Default proposto**: 30s per widget A (banner)
- Widget B: 1x al caricamento pagina + refresh manuale (non serve real-time, lo slow tick è ogni 4h)

### 4. Posizione in /admin

- **Proposta CC**: nuova sezione "🧭 Sentinel slow loop" tra la sezione "Sentinel scores (fast)" esistente e la sezione "Sherpa proposals" esistente. Separazione netta tra "cosa Sentinel sa" (slow + fast) e "cosa Sherpa propone" (downstream).

### 5. Mobile responsive

- Widget A: scala bene su mobile (1 riga, font ridotto)
- Widget B: il band chart richiede ~600-800px wide. Su mobile mostro versione collassata "ultimo regime + numero di switch ultimi 7gg" con link "open desktop view for full chart"

---

## Decisioni che CC NON prende autonomamente

- Modifica della BASE_TABLE in `parameter_rules.py` (off-limits Sprint 2)
- Migration Supabase nuova (non serve, jsonb regge tutto)
- Cambio cadenza slow loop (4h è stato deciso in brief 77b)
- Pubblicazione del widget sul **sito pubblico** (`/dashboard`) — solo `/admin` privata. Quando faremo la dashboard pubblica del regime, sarà brief separato post-osservazione 5-7gg
- Aggiunta di Telegram alert "regime changed" — feature di monitoring va in `/admin`, non Telegram (memoria `feedback_no_telegram_alerts`)

---

## File OFF-LIMITS

- `bot/sentinel/*` — slow loop appena shipped, NON tocco
- `bot/sherpa/*` — off-limits per natura del brief
- `bot/grid_runner/*` — off-limits
- Tutti i `.py` di trading logic — il brief tocca **solo presentation layer**

---

## File da toccare (proposta)

```
web_astro/public/admin.html                # widget A + widget B HTML+JS
web_astro/public/admin/                    # eventuale js helper se serve modularizzare
```

Probabilmente tutto inline in `admin.html` come pattern delle altre sezioni esistenti. Vediamo al momento dell'implementazione se conviene estrarre uno sotto-file.

---

## TASK NON BANALE? (CLAUDE.md §3)

Stima 45-60 min, < 50 righe per widget A, ~150 righe per widget B (incluso chart library wrapper) → **task piccolo, non serve piano italiano separato**. Brief stesso è il piano.

Se al momento dell'implementazione mi accorgo che il widget B richiede una libreria chart non già presente in admin.html (es. Chart.js / ApexCharts) → mi fermo e chiedo. Vediamo cosa c'è già.

---

## Output atteso

1. Widget A live in `/admin` (regime banner)
2. Widget B live in `/admin` (timeline 7gg)
3. Test manuale: aprire `/admin`, verificare regime corrente e timeline coerenti con i dati DB
4. Build Astro verde + push
5. PROJECT_STATE update + brief in `briefresolved.md/`
6. Mini-report `report_for_CEO/` se servono note operative

---

## Roadmap impact

- **Sblocca**: fase 3 della sequenza Sentinel-first (osservazione 5-7 giorni). Max può finalmente "guardare il pannello" invece di interrogare DB.
- **Non blocca**: Sherpa LIVE testnet — quello dipende dalla fase 3 audit, non da questo brief.
- **Setup propedeutico** per quando il regime widget andrà sul sito pubblico (post-traction, post-mainnet).

---

## Vincoli

- **Solo `/admin`, non sito pubblico.** Dashboard pubblica regime = brief separato post-osservazione
- **No Telegram alerts** sui cambi di regime (memoria `feedback_no_telegram_alerts`)
- **No modifiche backend.** Solo presentation layer
- **No restart bot.** Astro static build + Vercel deploy
- **No screenshot via CC.** Memoria `feedback_no_screenshots`: Max controlla in browser

---

## Attesa risposta

CEO approva con scelte su:
1. Palette colori (default CC vs alternativa 1 vs alternativa 2)
2. F&G line overlay su band chart (default SÌ)
3. Polling rate widget A (default 30s)
4. Posizione in /admin (default nuova sezione tra fast e sherpa)

Quando arriva l'OK, CC implementa entro 60 min e committa.

---

*Brief proposta CC. In attesa approvazione CEO.*
