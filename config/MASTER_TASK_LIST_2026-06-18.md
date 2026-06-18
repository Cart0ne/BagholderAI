# BagHolderAI — Master Task List

**Data:** 18 giugno 2026
**Regola:** da oggi niente nuovi task. Solo bug fix. Si finisce quello che c'è.

---

## FASE 0 — IN OSSERVAZIONE (nessuna azione, solo aspettare)

Queste cose girano da sole. Non toccare, non aggiungere scope.

| # | Cosa | Scadenza / trigger | Chi |
|---|---|---|---|
| 0.1 | Barometro v2 shadow validation | Verdetto ~23 giugno | Automatico |
| 0.2 | Sherpa 7-day observation (tutti i 7 parametri + debounce) | 7gg da S102b (11 giugno) → già maturi | Automatico |

**Nota:** Sherpa ha già superato i 7 giorni (live dal 11 giugno). Se non
l'abbiamo ancora guardato, è il PRIMO task attivo da fare.

---

## FASE 1 — PRE-MAINNET OBBLIGATORI (in ordine di esecuzione)

Senza questi non si va live. Sequenza logica, non parallelo.

| # | Cosa | Dipende da | Chi | Stima |
|---|---|---|---|---|
| 1.1 | **Verdetto barometro** — analizzare dati shadow, decidere se cablare Sentinel | 0.1 (dati ~23 giugno) | CEO + Max | 1 sessione |
| 1.2 | **Verdetto Sherpa** — analisi 7gg parametri, decidere se il flicker serve fix (A/B/C) | 0.2 | CEO + Max | parte della stessa sessione |
| 1.2b | **Verifica breadth tier → Sentinel** — i bullish (tier 1/2/3) che partono *prima* che Sentinel cambi regime: anticipano il cambio di stato? Read-only, brief `config/2026-06-18_brief_tier-breadth-regime-signal.md` | dati ~23 giu (stessa sessione 1.1/1.2) | CEO + Max | parte della sessione |
| 1.3 | **Sessione go-live experiment** — formalizzare rampa/rabbocco/verdetto/Victory Lap | 1.1 + 1.2 | CEO + Max | 1 sessione dedicata (da PARKED_golive_experiment_design.md) |
| 1.4 | **DUST write-off** — convert-to-BNB + reconciliation wallet↔DB | Pre-mainnet | CC (brief esistente in parked) | ~2h CC |
| 1.5 | **sell_pct + slippage_buffer parametrico per coin** | Pre-mainnet | CC (estensione brief 70a) | ~2-3h CC |
| 1.6 | **Integration test config reader chain** | Pre-mainnet (gap da S76) | CC | ~30-60min CC |
| 1.7 | **Mobile smoke test** | 1.4-1.6 completati | Max (telefono) | 30min |
| 1.8 | **Board approval call** | Tutto sopra OK | Max | 15min |

---

## FASE 2 — BLOG PIPELINE (parallela a Fase 1, non bloccante)

Questi possono avanzare tra una sessione tecnica e l'altra.

| # | Cosa | Stato | Chi | Note |
|---|---|---|---|---|
| 2.1 | **Cross-post "non-coder-5-brains" → Substack** | Pronto, solo da fare | Max | 15min, copia+adatta |
| 2.2 | **Pubblicare "vibe-coding-a-real-business.md"** | Draft, serve intro umana + light ritocco SEO (cluster S107 non-coder) | Max scrive intro → CEO traduce → CC pubblica | Applicare standard two-voice |
| 2.3 | **Pubblicare "why-most-ai-trading-bots-fail.md"** ⭐ **priorità** | SEO già forte (head keyword "ai trading bot" + FAQ + intro GEO); serve SOLO intro umana | CEO rivede → Max intro → CC pubblica | Applicare standard two-voice |
| 2.4 | **"ai-crypto-trading-bot-real-testnet-results.md"** | PARKED — placeholder data | Nessuno finché non ci sono dati reali | Sblocca dopo go-live |
| 2.5 | **"Thirty-Two Hours" Dev.to cross-post** | Draft su Dev.to, primo del nuovo standard | Max intro + lezione tecnica in cima | Da PARKED_blog_voice_strategy |

**Ordine consigliato:** 2.1 (5min) → **2.3** (più pronto: SEO già fatto, serve solo la tua intro) → 2.2 → 2.5 (2.4 aspetta dati).

---

## FASE 3 — SUBITO DOPO GO-LIVE (le prime settimane live)

| # | Cosa | Note |
|---|---|---|
| 3.1 | **Monitor "griglia silenziosa"** — alert quando una griglia non trada da X ore | Brief da scrivere. Nasce da buco S105. Dettaglio critico: soglia X |
| 3.2 | **Verifica commenti Haiku** | Da todo Board |
| 3.3 | **Verifica acquisto Ethereum + dashboard** | ✅ 18-giu: restart Mac Mini → ETH su `testnet_2` (tf_grid), causa-radice (cycle stale) risolta. Resta conferma visiva dashboard pubblica |
| 3.4 | **Fix copy /library** — frase "Read Volume II if you only care about the brain" datata | ✅ RISOLTO 18-giu (commit `1e22c87`), copy future-proof, in deploy |
| 3.5 | **BNB-discount fee future-proof** — colonna fee_native_amount | Pre scale-up |

---

## FASE 4 — POST GO-LIVE / QUANDO SERVE (backlog ordinato)

Non toccare fino a che Fase 1-3 non sono chiuse.

| # | Cosa | Trigger |
|---|---|---|
| 4.1 | Sentinel: espandere oltre F&G Index (Phase B) | Dopo stabilità mainnet |
| 4.2 | TF distance filter + regime-awareness (12% fisso paralizza TF) | Post Brain Analysis |
| 4.3 | Calibrare BASE_TABLE Sherpa se troppo distante | Post-analysis |
| 4.4 | Pagina /news pubblica con label AI (NewsKeeper maturo) | Post verdetto barometro |
| 4.5 | Tabella "Performance per regime" in dashboard | Serve profondità dati mainnet |
| 4.6 | History paper mode sito/blog | Quando ha senso |
| 4.7 | Guida all'uso | Quando ha senso |
| 4.8 | Patience timer per sell ladder | Serve dati reali testnet cycle 2 |
| 4.9 | Script replay counterfactual Sherpa | Da brief 80a |
| 4.10 | Decidere TRUNCATE tabelle Sentinel/Sherpa/TF paper-era | Quando si ricollega brain |
| 4.11 | Investigare recalibrate-on-restart (buy_pct cambia al boot) | CEO |

---

## CONGELATO (non toccare, non pianificare)

Roba che esiste ma NON entra in pipeline fino a nuova decisione Board.

| Cosa | Perché congelato |
|---|---|
| X automated Haiku posts | Paused, riprendere in sessione dedicata (X_STRATEGY_REVISION.md) |
| X Scanner automazione weekly cron | Manuale on-demand per ora |
| IG/Canva | Post risultati cambio tono Haiku X (2-3 sett) |
| Anthropic Admin API (costi Haiku) | Parked |
| Security audit (headers, CSP, RLS) | Parked |
| Sentinel market breadth da TF scanner | Phase B/C |
| Newsletter/mailing list blog | Post-lancio V3, valutare |
| Reddit r/ClaudeAI post | Serve 50 karma, Max karma building |
| HN | Account shadowbannato, serve nuovo account |
| Canale pubblico Telegram espansione | Da decidere |
| Post Show HN / X su Sentinel+Sherpa | Post go-live |
| NewsKeeper modulo 2 Grok/X scanner | Post-mainnet, API X premium |
| Anthropic Financial Services Agents repo | Reference, non task |
| ImMike kill-switch pattern | Reference per Sentinel mainnet |
| Brain Analysis round 2 | Serve NewsKeeper maturo |

---

## BUG APERTI (questi entrano sempre, unica eccezione alla regola)

| Bug | Priorità | Chi |
|---|---|---|
| Fix exchange_order_id null su sell OP/USDT | Cosmetico | CC |
| DeprecationWarning datetime.utcnow() | Low | CC |
| PortfolioManager istanziato ma mai usato | Low | CC |
| Aggiornare validation_and_control_system.md §2 | Low | CC |

---

## DIARIO

- Volume 4 "From Eyes to Live" (S83+): in corso, arco narrativo
  NewsKeeper → go-live → primi risultati. Nessun task — si scrive
  sessione per sessione.
- S106 risulta BUILDING in Supabase. S107 menzionata in memoria
  ma non presente in DB — da verificare con Max.

---

*Compilata: CEO, 18 giugno 2026. Fonti: Apple Notes todo, PARKED briefs
(PK), BUSINESS_STATE, memoria CEO. Regola: zero nuovi task, solo bug fix,
fino a chiusura Fase 1.*

*Aggiornato: CC, 18 giugno 2026 — 3.3 (restart Mac Mini → ETH su `testnet_2`)
e 3.4 (/library) risolti; aggiunto 1.2b (verifica breadth tier → Sentinel,
read-only, sessione del ~23). 1.2b è misura/analisi per decidere, non nuovo
scope di build — coerente con la regola "solo bug fix".*
