# PROPOSTA (CC → CEO/Board, da validare) — Sentinel regime: fallback tecnico anti-singola-fonte

**Data:** 2026-06-14
**Autore:** CC (intern) — nata da una conversazione Max↔CEO (idea del CEO)
**Stato:** DRAFT / da approvare dal CEO+Board prima di qualsiasi codice
**Scope (stringa per il report futuro):** `sentinel-regime-technical-fallback`

---

## 0. Cosa NON è questo brief (confini netti)

L'idea madre del CEO — "aggiungere RSI/ADX/volatilità per un regime più robusto, F&G come uno dei segnali invece dell'unico" — contiene **due cose diverse** con rischio e tempi opposti. Questo brief copre **solo la prima**:

- ✅ **(A) Robustezza di disponibilità** — togliere la dipendenza da un'unica fonte esterna (F&G). ← QUESTO BRIEF.
- ❌ **(B) Regime "migliore" fondendo i segnali** (F&G co-equale ai tecnici) — è ricerca, non ingegneria. Richiede una **teoria di combinazione + una metrica di validazione** che oggi non abbiamo, e una **decisione architetturale del CEO** ("qual è l'asse del regime?", vedi §6). Resta brief separato = **Phase B**, da fare dopo il verdetto barometro (~23 giu) e con più varietà di regimi di quella vista finora.

## 1. Il problema (reale, oggi)

Il regime Sentinel è deciso **solo** dal Fear & Greed Index (`bot/sentinel/regime_analyzer.py`). Se alternative.me è giù, malformato, o il dato è **vecchio > 36h**, il regime crolla a `neutral` (fallback attuale). È un **single point of failure** esterno: una fonte di terze parti decide la postura di tutti e 3 i grid bot. `neutral` non è "neutro innocuo" — disarma il freno stop-buy (armato solo su `extreme_fear`) proprio quando una API morta potrebbe coincidere con turbolenza di mercato.

## 2. Proposta (A): un regime tecnico calcolato da noi, come rete di sicurezza

Calcoliamo indicatori tecnici **dalle candele Binance** (klines — già abbiamo l'accesso ccxt/public API, zero nuove dipendenze esterne) e li usiamo **quando F&G non c'è**, invece di cadere su `neutral`.

Indicatori candidati (da decidere in §5): **RSI** (momentum/iper-comprato-venduto), **volatilità realizzata** (magnitudine del rischio). **ADX** lo lascio opzionale e con cautela: misura la *forza* del trend, **non la direzione** — da solo non dice bull/bear, va combinato con un segno.

**Comportamento:**
- F&G valido → **nulla cambia** (regime da F&G, come oggi). Zero regressione.
- F&G assente/stale → regime dal **blocco tecnico** invece di `neutral`. `decision_log.regime_source = "technical_fallback"` + `fallback_reason` conservati per audit.

## 3. Disciplina anti-assenso: shadow PRIMA, falsificabile

Stessa identica disciplina del barometro NewsKeeper (gate falsificabile). **NON** cabliamo il fallback al primo colpo:

- **Fase 1 — SHADOW (no behavior change):** calcoliamo SEMPRE il regime tecnico e lo **scriviamo accanto** a quello F&G in `sentinel_scores.raw_signals` (es. `regime_technical`), senza che tocchi le decisioni. Per N giorni confrontiamo: quanto spesso tecnico e F&G concordano? Quando divergono, chi aveva ragione vs il prezzo BTC a +24h? (⚠ attenzione circolarità — vedi §4.)
- **Fase 2 — WIRE come fallback:** solo se la Fase 1 mostra che il regime tecnico è sano, lo lasciamo subentrare quando F&G manca. Reversibile (flag env, come `SHERPA_MODE`).

## 4. Anti-assenso / rischi (li smonto io)

1. **Circolarità nella validazione.** RSI/ADX/vol derivano dal prezzo: validare "regime migliore" contro il ritorno del prezzo è viziato (correlati per costruzione). Per questo (A) si limita all'obiettivo **testabile**: "non cadere su neutral quando l'API è morta", non "regime più giusto" (quello è (B)).
2. **Indicatori in ritardo.** Un regime che flippa perché RSI buca 30 reagisce a un movimento già avvenuto. Accettabile per un *fallback di emergenza*; non lo sarebbe come segnale primario.
3. **Per-coin vs globale.** F&G è un numero globale; RSI/ADX/vol sono per-asset. Per il fallback globale propongo di calcolarli su **BTC** come proxy del regime macro (il grid è dominato dalla correlazione a BTC). Un regime per-coin è Phase B, non qui.
4. **Soglie arbitrarie.** Senza dati storici, le bande RSI→regime sono tirate a indovinare → motivo in più per la Fase 1 shadow prima di fidarsene.

## 5. Domande aperte da chiudere col CEO/Board prima del codice

1. Quali indicatori nel blocco tecnico minimo? (proposta CC: **RSI + volatilità realizzata su BTC**; ADX opzionale).
2. Mapping indicatori → 5 bucket: a soglie, oppure riuso del **modello a voti+astensione** già collaudato nel barometro NewsKeeper?
3. Durata della Fase 1 shadow prima di considerare il wire (proposta: ~2 settimane, come il barometro).
4. Confini: il fallback rimpiazza solo il caso `neutral`-da-mancanza-F&G, o anche lo smussa quando F&G è valido ma "sospetto"? (CC: solo il primo — non toccare il caso F&G-valido = (B)).

## 6. La decisione che NON spetta a CC (la flaggo al CEO)

Se un giorno andiamo su **(B)**, la domanda madre è: **qual è l'asse del regime?** Resta sentiment puro (fear↔greed) coi tecnici a conferma/override, o diventa multidimensionale (sentiment + forza-trend + tier-volatilità)? Cambia anche Sherpa. Territorio architetturale del CEO — qui solo segnalato.

## 7. Confini di scope (cosa NON si tocca)

- Niente modifica al comportamento quando F&G è valido (= (B), fuori scope).
- Niente regime per-coin (= Phase B).
- Niente nuove dipendenze esterne (solo klines Binance già in uso).
- Nessun restart finché non si arriva alla Fase 2.

## Roadmap impact

(A) è un **hardening** di Sentinel slow loop, additivo e reversibile, complementare alla Phase B (che resta la sede di (B)). Toglie una dipendenza esterna single-point-of-failure. Gated dietro: approvazione CEO/Board su §5 + Fase 1 shadow falsificabile.
