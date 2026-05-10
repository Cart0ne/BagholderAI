# Dashboard `/admin` Sentinel + Sherpa — Design Report

**Da:** Intern (Claude Code) → CEO
**Data:** 2026-05-07
**Sessione:** ~63 (continuazione 62)
**Stato:** 📐 Design finalizzato, **non ancora implementato**. Spec pronta per quando il Board darà il via.

---

## TL;DR

Discussione di ~1h con il Board per definire una dashboard interna `/admin` di osservabilità di Sentinel + Sherpa. Il design è passato per **3 iterazioni**, ognuna ha rimosso una cosa inutile o aggiunto una più potente. Risultato finale: 4 sezioni, ~9h di lavoro frontend, una sessione e mezza.

Punti chiave emersi:

1. **Read-only ora**, modifiche parametri restano via codice fino a Sprint 2 (coerente col DRY_RUN: cambiare costanti a metà raccolta dati invaliderebbe il counterfactual)
2. Una sezione che pareva utile ("Proposals count per bot") è stata **eliminata** dal Board: informazione non azionabile, ridondante con altre viste
3. Aggiunta dal Board la richiesta più interessante: un grafico **incrocio Sentinel → Sherpa**, che diventa la storia visiva del sistema. È anche il candidato perfetto per una futura pagina pubblica `/sentinel`

---

## 1. Il bisogno del Board

Max ha posto la domanda: *"Posso vedere da qualche parte i dati che usa Sentinel? Anche solo un esempio?"*

Risposta tecnica: i dati ci sono in `sentinel_scores` e `sherpa_proposals`, ma per leggerli servono query SQL su Supabase. Non c'è modo "umano" di guardare il sistema. Per un Board-member non programmatore questo è un blocco serio: le decisioni sul go-live richiedono di **fidarsi che il sistema funzioni**, e fidarsi senza poterlo guardare è un atto di fede.

Da qui la richiesta: dashboard interna con **3 obiettivi**:
- Vedere stato attuale di Sentinel (cosa raccoglie, cosa sta calcolando ora)
- Vedere stato attuale di Sherpa (cosa propone, perché)
- Vedere il "peso" del sistema su Supabase (size tabelle, rate di scrittura, retention)

Tutto privato, dietro basic auth. Pubblico verrà semmai dopo.

---

## 2. La prima proposta CC — e cosa non andava

### Mockup v1 (mio errore, corretto subito dal Board)

Avevo proposto inizialmente una sezione "**Proposals count 24h per bot**":

```
BTC   ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ 720 (di cui 12 changed)
SOL   ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ 720 (di cui  3 changed, 717 cooldown)
BONK  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ 720 (di cui  8 changed)
```

L'avevo messa per dare un senso di "quanto Sherpa ha lavorato".

**Critica del Board (Max):** *"Non so se serve."*

Aveva ragione su tre fronti:

1. **Non genera azione.** Cosa fai vedendo "BTC 720/12 changed"? Niente. Non è una metrica decisionale, è una statistica di processo.
2. **È ridondante.** "Sherpa è vivo" lo vedi dal timestamp dell'ultima proposta. "Sherpa ha cambiato idea X volte" lo capisci dal grafico storico dei parametri. Il numero in sé è derivato.
3. **La barra è quasi sempre piena.** 720/giorno × bot è il regime stabile, raramente vedrai numeri molto diversi. Visualizzazione che non discrimina.

**Lezione:** una sezione che genera un numero che non guida una decisione è solo **rumore che occupa spazio**. Eliminata.

### Mockup v2 (mia proposta corretta)

Sostituita la sezione tolta con un **grafico storico dei parametri proposti** (linea `proposed_buy_pct` per ogni bot, 24h). Più utile: vedi a colpo d'occhio quando Sherpa è uscito dal regime "neutral" e di quanto.

---

## 3. La controproposta del Board (la cosa potente)

Sul mockup v2, Max ha aggiunto: *"Sarebbe interessante un grafico che incrocia i dati di Sentinel con le reazioni di Sherpa... uno di quei grafici che poi possono tornare utili in una pagina pubblica."*

Questa intuizione cambia il taglio della dashboard.

### Da "monitor di sistema" a "racconto del sistema"

Una dashboard di sola osservazione è utile per il debugging interno. Ma se mostra la **catena causale** (stimolo → risposta), diventa una narrazione: *"guarda l'AI Sentinel che vede il mercato, guarda l'AI Sherpa che reagisce."*

Mockup del grafico **Sentinel → Sherpa Reaction**:

```
Risk     ╲                              ╱╲
Score    ─╲────────╱╲──────────────────╱──╲────────
          ╲      ╱  ╲                ╱      ╲
           ╲___╱    ╲______________╱        ╲___
      20 ───────────────────────────────────────  base

Sherpa
buy_pct  ─────────────────────────────╱──╲──────  (BTC)
 (BTC)  1.0% ──╲╱──────────────────────────────
                                     ↑
                                risk crossed 50

       00:00    06:00    12:00    18:00    now
```

Tre livelli di lettura:

| Livello | Info |
|---|---|
| **Sopra:** risk_score 24h | Cosa Sentinel ha pensato |
| **Sotto:** proposed_buy_pct per bot (3 linee) | Cosa Sherpa avrebbe fatto |
| **Annotazioni:** linee verticali sulle soglie chiave (50, 70, 90) | Quando il regime è cambiato |

### Tre scenari, tre storie

1. **Mercato calmo (oggi):** risk piatto a 20, buy_pct piatto a 1.0%. → "non è successo niente, e Sherpa è rimasto fermo." Coerente.
2. **Crash BTC:** risk schizza a 80, buy_pct sale a 2.5% sui 3 bot in pochi minuti. → "Sentinel ha visto il crollo, Sherpa ha alzato la difesa." Reazione visibile e raccontabile.
3. **Falso positivo:** risk schizza ma BTC non crolla. Sherpa reagisce comunque. → "Sherpa ha sprecato un'opportunità." Diventa input per il counterfactual a 7gg.

È **esattamente il grafico che racconta se Sherpa funziona davvero**, e il valore aumenterà ogni giorno: oggi è una linea piatta (mercato calmo da quando l'abbiamo acceso), tra una settimana sarà una storia.

### Dual-use: privato ora, pubblico dopo

Questo grafico è la **killer feature** sia della dashboard `/admin` (per il Board) sia di una futura pagina `/sentinel` pubblica. Su `/admin` lo vedi grezzo per giudicare. Su una pagina pubblica lo affianchi a un titolo tipo *"Watch the AI watch the market"* — diventa contenuto Twitter/HN.

Non costruiremo `/sentinel` pubblico ora (Max: *"per me è prematuro, può aspettare"* — corretto, vogliamo vedere i dati in privato prima di esporli). Ma la stessa componente grafica sarà riutilizzabile.

---

## 4. Una decisione di principio — read-only ora, non interattivo

Domanda implicita di Max: *"Quindi è una legenda di parametri, senza possibilità di intervenire? Anche perché i parametri di setup non sono su Supabase, ma direttamente nel codice?"*

Risposta: corretto. E spiego il **perché** è la decisione giusta per Sprint 1.

### I parametri Sentinel/Sherpa sono costanti Python

| Cosa | Dove | Esempio |
|---|---|---|
| Soglie scoring Sentinel | `bot/sentinel/score_engine.py` | `if change_1h <= -10: risk += 80` |
| BASE_TABLE regimi Sherpa | `bot/sherpa/parameter_rules.py` | `"neutral": {"buy_pct": 1.0, ...}` |
| DROP_LADDER fast | `bot/sherpa/parameter_rules.py` | `(-10, "btc_drop_10pct_1h", 1.5, -0.7, 3.0)` |
| RANGES clamp | `bot/sherpa/parameter_rules.py` | `"buy_pct": (0.3, 3.0)` |

Per modificarle: edit file → commit → ssh Mac Mini → pull → restart orchestrator. Cinque minuti di lavoro.

### Tre opzioni considerate, una scelta

**A. Dashboard read-only (raccomandato e accettato)** — modifiche solo via codice.
**B. Read-only ora, interattiva in Sprint 2** — doppio lavoro frontend.
**C. Interattiva subito** — nuova migration `sentinel_config` + `sherpa_config`, lettura DB con cache, UI con form e log dei cambiamenti. ~12-15h.

Ho consigliato **A** per tre motivi:

1. **Il bisogno reale del Board è "voglio capire cosa fa il sistema"**, non "voglio modificarlo continuamente". Le costanti vanno cambiate poche volte, e quando le cambi vuoi farlo con intenzione, non per impulso UI.
2. **Sprint 1 è DRY_RUN per raccogliere dati counterfactual.** Se variamo le soglie a metà run, i dati raccolti diventano fuffa: stiamo confrontando "cosa avrebbe fatto Sherpa" con un Sherpa che cambia identità ogni 3 giorni. **L'osservazione richiede stabilità.**
3. **Sprint 2 può aggiungere modifiche da UI** dopo che avremo i dati per dire "ok, le costanti sono ragionevoli, ora le finalizziamo in DB con possibilità di tweak controllato + audit log."

In altre parole: **prima leggi, poi scrivi.** Se Max in Sprint 2 vorrà modificarli da UI, costruiamo allora le tabelle `sentinel_config` / `sherpa_config` (~10h aggiuntive, lavoro pulito non duplicato grazie al decoupling read/write).

### Una via di mezzo offerta

Per attenuare l'attrito, ho proposto un'opzione "**A + bottone Edit on GitHub**": dalla dashboard, accanto alla tabella delle regole, un link diretto al file su GitHub con la sezione delle costanti evidenziata. Cambi col tuo workflow git normale invece che ssh+vim+restart.

Max non si è ancora pronunciato su questo bottone, ma è un add-on minore (~30 min di lavoro). Lo includerò di default a meno di indicazione contraria.

---

## 5. Mockup finale concordato

```
╔══════════ SENTINEL ══════════════════════════════════════╗

  📡 LAST SCAN                          07:42:31 UTC (1m ago)
   BTC price        $81,333.49         Funding   -0.006%
   BTC 1h           +0.34%             Speed     stable ●
   BTC 24h          -0.16%             Samples   698

   ╭──────────────╮  ╭────────────────╮
   │  Risk: 20    │  │ Opportunity:20 │
   │  ▓▓░░░░░░░░  │  │ ▓▓░░░░░░░░░░░  │
   ╰──────────────╯  ╰────────────────╯

  📈 24h TREND  (risk + opp lines, multi-window selector)

  📋 SCORING RULES (statiche, parsed at build time)
   [tabella 10 regole con i loro pesi: BTC drop ladders + funding + speed]

╚══════════════════════════════════════════════════════════╝

╔══════════ SHERPA ════════════════════════════════════════╗

  🏔️ LAST PROPOSALS                     07:42:48 UTC (1m ago)
   ┌──────────┬────────────────┬────────────────┬────────┐
   │ Bot      │ Tu (current)   │ Sherpa (prop.) │ Status │
   │ BTC/USDT │ 0.50/1.50/4h   │ 1.00/1.50/1h   │ ⚠ diff │
   │ SOL/USDT │ 0.50/2.00/4h   │ 1.00/1.50/1h   │ 🔒 cool│
   │ BONK/USDT│ 1.50/2.00/4h   │ 1.00/1.50/1h   │ ⚠ diff │
   └──────────┴────────────────┴────────────────┴────────┘

  📊 SENTINEL → SHERPA REACTION (24h)        ⭐ killer feature
   [grafico combinato: risk_score sopra, buy_pct sotto per 3 bot,
    annotation lines sui crossing dei threshold]

  📈 PROPOSED PARAMETERS HISTORY (24h)
   [3 grafici impilati: buy_pct, sell_pct, idle_reentry,
    1 linea per bot ciascuno]

  📋 PARAMETER RULES (statiche, parsed at build time)
   [BASE_TABLE 5 regimi (regime attivo evidenziato) +
    DROP/PUMP/FUNDING ladder + RANGES clamp]

╚══════════════════════════════════════════════════════════╝

╔══════════ DB MONITOR ════════════════════════════════════╗

   Used:        16 MB / 500 MB free tier (3.2%)
   Top table:   trend_scans (8.1 MB, 30k rows) ⚠️ TEMP
   Sentinel:    863 rows (0.5 MB) — last scan 2m ago ✓
   Sherpa:      1,284 rows (0.5 MB) — last proposal 4m ago ✓
   Retention:   30d sentinel · 60d sherpa · 14d events · 7d snapshots
   Last cleanup: 04:00 UTC, 2,341 rows purged

╚══════════════════════════════════════════════════════════╝
```

---

## 6. Effort breakdown

| Componente | Effort |
|---|---|
| Layout `/admin` con basic auth | 1h |
| Sentinel: state card + 24h chart + multi-window selector | 2h |
| Sentinel: scoring rules table (statica) | 30min |
| Sherpa: Last Proposals table | 1h |
| **Sherpa: Reaction chart Sentinel→Sherpa** | **2h** ⭐ |
| Sherpa: Parameters history (3 stacked charts) | 1h |
| Sherpa: parameter rules tables (statica) | 30min |
| DB monitor (size + retention) | 1h |
| **Totale** | **~9h, 1.5 sessioni** |

Distribuibile in due tranche da ~5h e ~4h.

---

## 7. Decisioni residue (per il CEO)

Tre cose ancora da chiudere prima di iniziare:

1. **Fonti dati delle "Rules tables"**: statiche (parsate a build time dal codice Python) o live (script che le legge a runtime). **Mio consiglio: statiche** — Sprint 2 le sposterà in DB e allora diventeranno live. Risparmiamo lavoro adesso.

2. **Auth method**: basic auth, IP-restrict (Mac Mini + iPhone Tailscale), Vercel Password Protection? Tre livelli di rigore crescente. **Mio consiglio: Vercel Password Protection** — gratuito, nativo, nessun codice extra.

3. **`speed_of_fall_accelerating` come si visualizza?** Boolean che non si mette nei grafici classici. **Mio consiglio: pallino acceso/spento accanto a `Risk: N` + counter giornaliero** ("scattato 3 volte oggi"). Discreto ma visibile.

Nessuna di queste decisioni è bloccante: posso partire con i miei consigli e correggere se il CEO non concorda.

---

## 8. Quando iniziare

Non è prioritario tra le voci della Apple Note. Sequenza che mi sembra ragionevole:

| Priorità | Lavoro | Effort |
|---|---|---|
| 1 | Allineare `grid.html` / `tf.html` ai calcoli FIFO canonici | TBD |
| 2 | **Dashboard `/admin`** read-only | ~9h |
| 3 | Refactoring Grid bot (2000+ righe) | TBD |
| 4 | Replay counterfactual script (richiede 7gg di dati) | ~3h |

Il `/admin` ha il vantaggio di essere **utile da subito** (lo guardi mentre i dati si accumulano per il counterfactual) e di **richiedere zero modifiche al codice di Sentinel/Sherpa**, quindi a rischio nullo per il sistema in produzione.

---

## 9. Cosa è andato bene in questa discussione

Nello spirito di tracciare il processo decisionale (non solo l'outcome):

- **Iterazione veloce.** Ho proposto v1, Max ha tagliato la sezione inutile, ho proposto v2, Max ha aggiunto la sezione potente. ~3 round, ~30 minuti, design pulito.
- **Critica costruttiva del Board.** "Non so se serve" è il feedback più prezioso che si possa ricevere su una proposta. Ha eliminato un quarto di mockup di rumore.
- **Nessun lavoro sprecato.** La conversazione è avvenuta su mockup ASCII, prima di toccare codice. Una volta partito, parto sapendo esattamente cosa costruire.

---

## 10. Roadmap impact

Nessuno. La dashboard è strumentazione interna, non shippa al pubblico, non modifica Sentinel/Sherpa. Quando partirà, sarà un commit con `Roadmap impact: none`.

Se invece a un certo punto convertissimo la sezione "Reaction chart" in pagina pubblica `/sentinel`, allora andrà in roadmap come milestone narrativa — ma è una decisione separata da prendere con almeno 2-4 settimane di dati raccolti.

---

**Commit di riferimento:** nessuno per ora, design-only. Quando partirà l'implementazione, riferimenti aggiornati nel report di chiusura.
