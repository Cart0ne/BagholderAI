Brief S108b — tf-recap-architecture — 2026-06-20

Basato su: PROJECT_STATE.md consultato via PK search 2026-06-20.
Sessione: S108 (mini sessione mobile + follow-up al PC).

---

## Contesto

Il Trend Follower (TF) è inattivo da settimane (focus su Sherpa/
NewsKeeper/barometro). Max ha bisogno di un recap aggiornato su come
funziona il sistema TF prima di riprendere il lavoro su di esso.

Separatamente, la decisione strategica del Board (S108) è di andare
live su mainnet SOLO con i grid bot (collegati a NewsKeeper, Sentinel,
Sherpa) mentre il TF resta in testnet. Serve verifica tecnica che
l'architettura supporti questa separazione senza contaminazione dati.

Stima: task di ricerca/documentazione, < 1h. CC può procedere
direttamente senza piano preliminare.

---

## Task 1 — TF recap per Max (documento .md)

Produrre un documento `docs/tf_recap_S108.md` (o simile) che risponda
a queste domande in italiano, linguaggio accessibile:

### 1.1 Come funziona il TF oggi

- Quali monete scansiona? Quante? Con che frequenza?
- Come decide se un segnale è BULLISH / BEARISH / SIDEWAYS / NO_SIGNAL?
- Quali indicatori usa (EMA, RSI, ATR, volume)?
- Quando scatta un ALLOCATE vs HOLD?

### 1.2 Parametri sulla dashboard (screenshot di Max: admin config)

Spiegare ogni parametro visibile nella config TF:
- **BUY %**: cos'è, come viene calcolato (ATR-adaptive), chi lo scrive
- **SELL %**: cos'è, come funziona il greed decay, formula
  `MAX(LAST_TIER - 0.5, 0.3)`, perché le edit manuali vengono
  sovrascritte alla prossima allocazione
- **MIN PROFIT %**: perché è sempre 0 sui TF bot, ruolo del greed
  decay + stop loss come floor alternativo
- **IDLE RE-ENTRY**: cosa controlla, valore attuale
- **Fixed Grid** (vuoto): perché TF non usa la griglia tradizionale

### 1.3 Meta-parametri vs output

Distinguere chiaramente:
- **Output** (calcolati dal TF, sovrascritti a ogni allocazione):
  buy_pct, sell_pct — Sherpa NON può gestirli senza conflitto
- **Meta-parametri** (configurabili, governano come il TF calcola):
  moltiplicatore ATR, velocità greed decay, stop_loss_pct, tiers del
  greed decay, idle_reentry_hours — potenzialmente gestibili da Sherpa
- Per ogni meta-parametro: dove vive nel codice/config, range sensato,
  cosa succede se lo cambi

### 1.4 Stop loss e greed decay

- Come funziona il TF stop loss? Fisso o dinamico?
- Come funziona il greed decay tier by tier?
- Schema attuale delle tier: quante, soglie, effetto su sell_pct

---

## Task 2 — Verifica architettura grid mainnet + TF testnet

Verificare che il sistema possa supportare:
- Grid bot (BTC, SOL, BONK) su mainnet
- TF bot su testnet
- Contemporaneamente, sulla stessa macchina (Mac Mini)

### Checklist da verificare

1. **API keys**: grid usa le key mainnet, TF usa le key testnet.
   Sono separabili via env var o config? O condividono la stessa
   istanza exchange?

2. **Supabase**: le tabelle usano `cycle` e `config_version` per
   separare i dati. Grid mainnet e TF testnet scriverebbero sulle
   stesse tabelle? Serve un campo aggiuntivo per distinguerli?

3. **bot_config**: grid e TF leggono dalla stessa tabella. I record
   sono separati per symbol? O serve una colonna `environment`?

4. **Processi**: grid e TF girano come processi separati
   (orchestrator)? Possono avere env var diverse?

5. **Sentinel/Sherpa/NewsKeeper**: servono grid E TF, o solo grid
   su mainnet? Se servono entrambi, leggono/scrivono sugli stessi
   record?

6. **daily_report / daily_pnl**: il report combina Grid + TF in un
   unico portfolio. Su mainnet grid + testnet TF, i numeri verrebbero
   mischiati. Serve separazione?

### Output atteso

Un paragrafo per ogni punto della checklist:
- **OK** se già supportato, con spiegazione
- **RICHIEDE MODIFICA** se serve lavoro, con stima scope
- **BLOCCA GO-LIVE** se è un prerequisito non aggirabile

---

## Decisioni delegate a CC

- Struttura e formato del documento recap (Task 1)
- Livello di dettaglio tecnico (adattare al fatto che Max non ha
  background tecnico — linguaggio accessibile, esempi concreti)

## Decisioni che CC DEVE chiedere a Max

- Nessuna per questo brief — è tutto lettura/documentazione

## Output atteso

1. `docs/tf_recap_S108.md` — recap TF in italiano per Max
2. Sezione architettura dentro lo stesso file o file separato
   (`docs/grid_mainnet_tf_testnet_assessment.md`)
3. Se emergono blocchi go-live, segnalarli immediatamente a Max
   (non aspettare fine sessione)

## Vincoli

- NON restartare il bot
- NON modificare codice — questo è un task di documentazione/analisi
- NON toccare la config TF (nessun parametro)
- Se durante l'analisi CC trova bug o inconsistenze, documentarli
  nel report ma NON fixarli (scope separato)

## Auto-obiezione

Il Task 2 potrebbe scoprire che la separazione grid mainnet / TF
testnet richiede modifiche non banali (es. separazione env var per
processo, campo environment in bot_config). Se così, il go-live
grid-only non è bloccato — si può semplicemente spegnere il TF durante
il periodo mainnet e riaccenderlo dopo. Ma è una soluzione bruta, non
elegante. Meglio saperlo prima.
