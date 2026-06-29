# PARKED — MatrixAgentNet External Code Audit

**Origine:** Sessione marketing 28/06/2026 (post-S110)
**Tipo:** Caso 2 — side quest post-mainnet, non blocca go-live
**Stato:** ESPLORATA 2026-06-29 — agente registrato, primi post + review fatti. Vedi update sotto.

---

## UPDATE 2026-06-29 (sessione "gioco" CC↔Max) — ESEGUITA in anticipo sul post-mainnet

Su richiesta di Max abbiamo esplorato il network invece di aspettare il post-mainnet.

**Fatto:**
- Agente **BagHolderAI** registrato → https://matrixagentnet.com/agents/bagholderai (slug `bagholderai`, model `claude-opus-4`).
- Credenziali in `config/.env.matrix` (gitignored, solo MacBook Air; include `MATRIX_RECOVERY_KEY`).
- Post #1 (audit del feed), 1 review seria su lavoro altrui, Post #2 (avg-cost vs FIFO). Reputation salita a 11 (punti attività). Rate limit: **1 creation / 30 min**.
- Memoria durevole creata: `project_matrixagentnet_agent.md` → "dedicarci qualche minuto ogni tanto".

**Verdetto sui rischi/domande aperte di questo file:**
- **#1 Qualità review → CONFERMATO BASSA.** Feed = aforismi sintetici ripetitivi; review generiche da una riga, una addirittura off-topic (cache TTL su un post di agent-loop). L'ipotesi "audit esterno di qualità del nostro codice" è **debole**: rischi rumore, non audit.
- **Valore-contenuto → CONFERMATO.** L'esperimento stesso ("abbiamo misurato che le review sono rumore") è materiale onesto per blog/diary — più forte della marchetta originale.
- **#3 Esposizione codice:** evitata. Finora pubblicati solo articoli (ragionamento generale, zero edge). Il "modulo safe vero" (health_check.py) resta NON fatto — opzione aperta per il futuro.

**Conclusione:** non vale come canale d'audit serio; vale come presenza low-effort + fonte di contenuto. Tenere vivo con check sporadici (vedi memoria). Le sezioni sotto restano come contesto originale.

---

## L'idea

Sottoporre parti del codice di BagHolderAI a peer review su **MatrixAgentNet** (matrixagentnet.com), un social network dove gli utenti sono agenti AI. Gli agenti pubblicano lavoro, si recensiscono a vicenda con feedback strutturato (BUG_REPORT / IMPROVEMENT / ALTERNATIVE), e costruiscono reputazione.

**Perché ha senso per noi:** coerente con il principio "l'audit deve essere esterno" (tema ricorrente, validato anche da Mike Czerwinski/jugeni nei post del 28/06). Il nostro audit interno (Cowork automated, CEO review) verifica coerenza e processo. Un audit esterno da agenti AI terzi verificherebbe qualità del codice da una prospettiva indipendente.

**Valore contenutistico:** "abbiamo chiesto ad agenti AI di auditare il codice scritto dal nostro agente AI" è un pezzo di contenuto forte per blog/diary.

---

## Cosa pubblicare (safe)

Moduli non sensibili che mostrano qualità senza esporre logica di trading:

- `bot/health_check.py` — integrity checks su DB
- `bot/grid/state_manager.py` — ricostruzione stato avg-cost
- `db/event_logger.py` — logging strutturato
- `bot/newskeeper/` — barometro, parsing RSS, regime detection
- Diary/docx workflow scripts

## Cosa NON pubblicare

- Logica di trading (scanner, classifier, allocator, sell pipeline)
- Chiavi, config, parametri operativi
- Pattern di connessione exchange
- Sentinel gate logic (potenziale edge)

---

## Riferimenti

- **Sito:** https://matrixagentnet.com
- **Agenti attivi:** 269 (dato 28/06/2026)
- **Directory:** https://matrixagentnet.com/agents
- **Creazioni:** https://matrixagentnet.com/explore
- **API:** auth via X-Matrix-Key header, REST API, RSS feeds per agente/topic
- **Thread Reddit originale:** r/AI_Agents, "I built a social network where the users are AI agents"
- **Charter:** https://matrixagentnet.com/agent-charter

---

## Rischi e domande aperte

1. **Qualità review:** 269 agenti, qualità sconosciuta. Potrebbe uscire rumore. Ma anche quello è un dato utile.
2. **Collusion/gaming:** il fondatore stesso ammette che la reputazione peer-review è gameable. Da valutare quanto sono affidabili le review.
3. **Esposizione codice:** anche i moduli "safe" rivelano struttura del progetto. Valutare se ok.
4. **Effort CC:** registrare agente, formattare codice per pubblicazione, raccogliere review. Stimare tempo.

---

## Next step

Sessione di lavoro con CC post-mainnet: esplorare API, registrare un agente BagHolderAI, pubblicare un modulo di test (health_check.py?), valutare qualità delle review ricevute prima di procedere con altri moduli.
