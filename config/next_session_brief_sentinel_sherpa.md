# NEXT SESSION BRIEF — Sentinel + Sherpa Brainstorming

**Preparato:** Session ~60 (May 6, 2026)
**Tipo:** Brainstorming puro. Zero codice.
**Obiettivo:** Uscire dalla sessione con un diagramma di flusso chiaro e condiviso prima di scrivere qualsiasi brief per CC.

---

## Contesto strategico (decisione del Board)

**L'idea di Max:** Sentinel non nasce per proteggere TF (come nella sentinel_gate_spec_v1), ma per **tunare i parametri di Grid** — il motore che funziona (179W / 0L). Grid ha solo 4 manopole. Se Sentinel sbaglia, i danni sono minimi.

Se Sentinel funziona su Grid → lo estendiamo a TF e/o Shitcoin Scanner.
Se non funziona → Grid continua a lavorare come prima, nessun danno.

**TF non è morto.** Analisi dati ~12 maggio deciderà il suo futuro. Sentinel su Grid è un test a basso rischio, non una sostituzione.

---

## La gerarchia aggiornata

```
MAX (Board)
  │  veto · override manuale · go/no-go
  ▼
SHERPA (Regista)
  │  decide il ritmo del sistema
  │  "Sentinel, scansiona ogni 30min" / "ogni 4h"
  │  "Grid, allarga buy_pct" / "stringi idle_reentry"
  ▼
SENTINEL (Occhi)                    SUPABASE (Memoria)
  │  guarda fuori: news,              │  bot_config
  │  sentiment, macro                 │  trend_config
  │  produce risk/opportunity score   │  config_changes_log
  │  riporta a Sherpa                 │  audit trail
  ▼                                   ▼
ORCHESTRATOR (Logistica)
  │  lancia · monitora · riavvia
  ▼
GRID BOTS (Mani)          TF (Mani, budget ridotto)
  BTC · SOL · BONK          Rotation altcoin
  4 parametri                ~20 parametri
```

**Differenza chiave vs VISION v2:** Sherpa è il regista (non esisteva come entità separata nella VISION). Sentinel è gli occhi, non il decisore finale. Sherpa coordina sia Sentinel (frequenza scan) sia i bot (parametri).

---

## Blocco 1 — Mappa parametri Grid (target Sentinel/Sherpa)

I 4 bottoni che Sherpa può girare su Grid:

| Parametro | Cosa fa | Valore attuale | Range proposto | Esempio bullish | Esempio bearish |
|-----------|---------|----------------|----------------|-----------------|-----------------|
| `buy_pct` | % di calo per triggerare un buy | 0.5-1.8% | 0.3% — 3.0% | Abbassa (compra più spesso) | Alza (compra solo su dip profondi) |
| `sell_pct` | % di salita per triggerare una sell | 1.0-1.5% | 0.8% — 4.0% | Alza (lascia correre i profit) | Abbassa (vendi prima che scenda) |
| `idle_reentry_hours` | Ore di attesa tra un buy e l'altro | 1h | 0.5h — 6h | Riduci (più aggressivo) | Alza (più cauto) |
| `capital_per_trade` | $ per singolo trade | varia | da discutere | Alza? (più skin in the game) | Riduci? (meno esposizione) |

**Da discutere:**
- I range min/max sono giusti? Troppo stretti? Troppo larghi?
- `capital_per_trade` è rischioso da toccare automaticamente — lo includiamo o lo teniamo solo manuale?
- Ci sono altri parametri Grid che ci sfuggono?

---

## Blocco 2 — Input di Sentinel (proposta CEO)

Sentinel guarda il mondo esterno — roba che Grid NON vede oggi. Se usasse solo indicatori tecnici (EMA, RSI) sarebbe TF con un nome diverso.

| Input | Fonte | Costo | Frequenza | Cosa aggiunge |
|-------|-------|-------|-----------|---------------|
| **Fear & Greed Index** | alternative.me API | Gratis | 1x/giorno | Proxy di sentiment globale crypto |
| **BTC come proxy macro** | Binance API (già disponibile) | Gratis | Ogni scan | Se BTC crolla, le alt seguono. Segnale più semplice e affidabile |
| **X Sentiment** | Grok/xAI scanner (già funzionante) | ~$0.04/scan | On-demand | Sentiment social pre-evento |
| **CryptoPanic News** | API REST | Gratis (free tier) | Ogni scan | News filtrate per rilevanza crypto |
| **Funding Rates** | Binance API | Gratis | Ogni scan | Indicatore di leva eccessiva nel mercato |
| **On-chain (whale alerts)** | API da valutare | Da verificare | Periodico | Movimenti grossi pre-dump |

**Da discutere:**
- Quali includiamo nel Livello A (MVP)?
- Quali sono "nice to have" per dopo?
- Quanto budget API mensile è accettabile? (collegato al business model che dobbiamo fare)

---

## Blocco 3 — Sherpa: il meccanismo

**Cosa fa Sherpa concretamente:**
1. Riceve il risk/opportunity score da Sentinel
2. Valuta il "regime" di mercato (bullish / bearish / lateral)
3. Decide la frequenza di scansione di Sentinel
4. Traduce il regime in modifiche parametri Grid
5. Scrive le modifiche in `bot_config` via Supabase
6. Logga tutto in `config_changes_log` (fonte: `sherpa`)

**Domande aperte:**
- Sherpa è un processo Python separato? Una funzione dentro Sentinel? Parte dell'Orchestrator?
- Quanto spesso Sherpa rivaluta il regime? Ogni scan di Sentinel? Ogni N ore? Ogni giorno?
- Il cooldown umano (da S18): quando Max tocca un parametro, Sherpa lo rispetta per Xh. Quanto è X?

---

## Blocco 4 — Refactoring Grid (prerequisito tecnico)

grid_bot.py è a 2000+ righe. Prima che Sherpa scriva parametri e Sentinel influenzi il comportamento, il file deve essere più modulare.

Piano dalla S50:
- **Fase 1:** Estrarre filtri (stop_loss, take_profit, profit_lock, gain_saturation) in moduli separati. ~800-1000 righe fuori.
- **Fase 2:** Estrarre liquidation pipeline, trade execution, state management. grid_bot.py → ~300-500 righe orchestratore puro.
- **Prerequisito:** Unit test pre-refactoring.

**Da discutere:**
- Lo facciamo prima di Sentinel (più sicuro) o in parallelo (più veloce)?
- Il refactoring è bloccante per Sentinel? (Probabilmente no per il Layer A puro, che è un processo esterno.)

---

## Blocco 5 — Cosa esiste già (documenti di riferimento)

| Documento | Dove | Cosa contiene |
|-----------|------|---------------|
| VISION_brains_architecture_v2.md | Project knowledge | Architettura 4 cervelli, domande aperte, ordine implementazione |
| sentinel_gate_spec_v1.md | Project knowledge | Spec dettagliata del Gate per TF (Layer 0-1-2, tabella sentinel_decisions, percorso evolutivo) |
| bagholderai_architecture.html | Generato oggi | Diagramma visivo completo dell'ufficio |
| Conversazioni S18, S50, S53-54 | Chat history | Cooldown override, refactoring plan, nome Sherpa |

---

## Deliverable atteso dalla prossima sessione

1. **Diagramma di flusso definitivo:** Input → Sentinel → Sherpa → Parametri Grid → Effetto
2. **Scelta input Sentinel Livello A** (MVP, costi chiari)
3. **Range parametri Grid** validati dal Board
4. **Decisione Sherpa:** processo separato o integrato?
5. **Sequenza:** cosa si fa prima, cosa dopo, cosa in parallelo

Tutto in schemi. Zero codice. Il primo brief per CC nasce DOPO che il Board ha approvato il design.
