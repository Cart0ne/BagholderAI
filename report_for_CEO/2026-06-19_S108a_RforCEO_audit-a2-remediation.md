# Report per CEO — S108a — audit-a2-remediation — 2026-06-19

**Da:** CC (Claude Code) · **A:** CEO
**Brief sorgente:** `briefresolved.md/2026-06-19_S108a_brief_audit-a2-remediation.md`
**Audit di riferimento:** A2 del 2026-06-19, CON RISERVE (post-review CEO: 1 HIGH, 3 MED, 6 LOW) — `audits/reports/20260619_audit[A2].md` (gitignored/locale)
**Commit:** `0fb4d82` (P1/P2/P3), `9b41548` + `478b1ad` (bonus shadow-only + cleanup), `44d2510` (M2 mixer, fixato pre-brief)
**Esito:** SHIPPED (web-only, nessun bot / nessun restart)

---

## 1. Remediation per finding A2

| Finding | Sev | Azione | Stato |
|---|---|---|---|
| **H1** roadmap pubblica stale (recidiva) | HIGH | `roadmap.ts` → version **1.49** + lastUpdated 2026-06-19; NewsKeeper Sprint 2 (Haiku) planned→done (S94a) + nuovo task **barometro v2** (S100); **ETH** 4° coin (first TF→grid handoff). Sentinel/Sherpa LIVE erano già nel contenuto — solo l'etichetta versione era ferma. | ✅ `0fb4d82` |
| **H2** errata Vol1 "we never used the testnet" | HIGH→ | Nessuna azione CC: volumi = artefatti storici immutabili (decisione editoriale CEO, confermata da Max). Eventuale forward-note in un volume futuro è territorio CEO/diary. | ✅ risolto (editoriale) |
| **M1** BUSINESS_STATE descrive nav "News" + `/news` (404) | MED | Territorio BUSINESS_STATE/CEO. | ✅ risolto (Max) |
| **M2** card GRID home mostra coin sbagliati (BTC·ETH·SOL) | MED | Mixer reso **data-driven**: default BTC/SOL/BONK + refresh live da `bot_config` (managed_by='grid'). ETH resta sul lato TF. | ✅ `44d2510` |
| **M3** diary WIP indietro + mirror audit-source non sync | MED | Process/CEO (diary), no CC. | — (CEO) |
| **L1** date fresh-start incoerenti (Jun 4 vs Jun 5) | LOW | Allineato a **Jun 5** (Day 1 / primo trade) su sticker + dashboard. | ✅ `0fb4d82` |
| **L2** snapshot "$0.00" | LOW | **No-op**: è il fallback del contatore animato (`data-count="0"`) prima del JS, non un valore cablato. Per brief: accettabile. | ✅ verificato |
| **L3** howwework "Nine canonical sections" | LOW | → "Ten" (PROJECT_STATE ha 10 sezioni). | ✅ `0fb4d82` |
| **L4** howwework restart orchestrator | LOW | Wording → "pushes to git autonomously, restarts only when Max asks" (CLAUDE.md §5 S105b). | ✅ `0fb4d82` |
| **L6** label TEST vs LIVE home/dashboard | LOW | **Parcheggiato**: difendibile (testnet-environment vs running-state); allineare o commentare in un futuro tocco web. | ⏸ parked |

**Bonus (non in audit, trovato durante L6):** dashboard intro diceva "Two live, two shadowed / (Sentinel/Sherpa shadow-only)" — stale (Sherpa LIVE da S102b). Riformulato "Two trade, two advise / (Sentinel/Sherpa advise live, no capital of their own)" (`9b41548`). Rimosse anche 2 entry **vestigiali** in `index.astro` botData (sentinel/sherpa, "observing in DRY_RUN") — non renderizzate, `maxStat` invariato; homepage HTML ora 0 "DRY_RUN" (`478b1ad`).

## 2. Anti-recidiva (P2)

Aggiunto **ROADMAP CHECK** in `CLAUDE.md [1]`: a fine sessione, prima di committare PROJECT_STATE, CC verifica se lo shipped tocca una Phase della roadmap e in tal caso bumpa `roadmap.ts`. Safety net indipendente dalla sezione "Roadmap impact" dei brief (che dipende dal CEO che si ricordi di scriverla). Motivo: H1 era una **recidiva** dell'audit 27/05.

## 3. Decisions (DECISION LOG)

**DECISIONE:** L1 — riformulato "Clean slate since Jun 4" → "Fresh start · Jun 5".
**RAZIONALE:** il brief chiede UNA data (primo trade). Jun 5 = Day 1 = primo trade testnet_2; coerente con "DAYS RUNNING 15" (Jun 5→Jun 19 inclusivo). "Clean slate since Jun 5" sarebbe contraddittorio (il *reset* fu Jun 4).
**ALTERNATIVE:** tenere "Jun 4" (data del reset) e cambiare le altre superfici.
**FALLBACK:** se il CEO vuole marcare il *reset* (Jun 4), 2 edit per tornare indietro (sticker + dashboard).

**DECISIONE:** M2 — mixer GRID reso data-driven (live da `bot_config`) invece di rietichetta statica.
**RAZIONALE:** scelta di Max — non torna mai più in drift. Coerente col pattern live già usato (`live-stats.ts`, fallback server-rendered).
**ALTERNATIVE:** rietichetta statica BTC/SOL/BONK (più semplice, ma ri-driftabile).
**FALLBACK:** il default SSG è già BTC/SOL/BONK corretto, quindi anche senza il fetch live la card è giusta.

## 4. Anti-assenso (al brief)

3 obiezioni reali sollevate prima di codare: (1) **L2 non è un bug** → non l'ho "fixato", verificato come fallback di caricamento; (2) **H2** confermato declassato (volumi immutabili), nessuna azione CC; (3) **roadmap timebox** — marcato "done" solo il verificabile a codice/commit (no archeologia cieca).

## 5. Altri lavori della sessione S108 (fuori da questo brief)

- **og-image** cache-bust → `og-image-v2.jpg` (X cacheizza per URL; filename versionato forza il refresh). `096525c`.
- **Workflow audit sincronizzato e pulito**: 3 report Archivio→repo (A1 06-01 + A2 06-19), cadenza A3 allineata a **mensile** (era stale "bisettimanale" nei doc; il task Cowork era già mensile), §9/§7 aggiornati, Mac Mini sincronizzato. Creato template mancante `audit_request_A2.md`. **Fix C** (skip-guard robusto + chiusura git senza no-op): documento consegnato, **Max l'ha applicato nei 3 task Cowork**, backup allineati. `5ef7f82`, `a94abec`.
- **Live snapshot homepage**: il Total P&L escludeva la posizione TF→grid (ETH) → mostrava un finto +$0.76 invece dell'onesto ~−$1.69 del board. Reso fund-aware come il board (one source of truth). `b146543`.

## 6. Cosa NON è stato fatto / parcheggiato

- **L6** label TEST/LIVE (difendibile, futuro tocco web).
- `BotCardOriginal` mantiene il supporto variant sentinel/sherpa/testmode **dormiente** (componente riusabile; la stringa "DRY_RUN · v3" è ora irraggiungibile — rimuoverla è un refactor del componente, fuori scope).
- OFF-LIMITS rispettati: nessun `bot/`, nessun BUSINESS_STATE, nessun volume, §9/§7 aggiornati solo a fine sessione come da procedura.

## 7. Roadmap impact

`roadmap.ts` version **1.48 → 1.49 (Giugno 2026)**, lastUpdated 2026-06-19. Task done aggiunti: ETH first TF→grid handoff, NewsKeeper Sprint 2 (Haiku), + nuovo task barometro v2 (active, verdetto T+14 ~23 giu).

## 8. Next (chiusura S108, in attesa CEO)

- **In attesa del BUSINESS_STATE update dal CEO** → poi CC aggiorna PROJECT_STATE (§9 con riga A2 06-19 + §10 sessioni shipped + header) **insieme** a BUSINESS_STATE e chiude la sessione.
- Verdetto barometro NewsKeeper v2 **T+14 dovuto ~23 giugno** (validare flip vs prezzo BTC 24h, non F&G).
