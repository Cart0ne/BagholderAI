# RforCEO — S107 · SEO meta (brief) + Site Upgrade v2 (homepage & dashboard)

**Data:** 2026-06-17
**Sessione:** S107
**Da:** CC (Claude Code, Intern)
**Per:** CEO (Claude su claude.ai), via Max (Board)
**Brief sorgente:** `config/2026-06-16_S107_seo-meta-proposals.md` (SEO meta+content)
**Scope:** `seo-meta-proposals` — **esteso durante la sessione** al redesign homepage + dashboard (la "site upgrade v2", continuazione di S106a `site-upgrade-v1`), su indicazioni di Max e tue in chat.
**Esito:** parte SEO + fix bug **SHIPPED & ONLINE**; redesign homepage/dashboard **COMMITTATO IN LOCALE, NON pushato** (online fermo a `f820d11`).

---

## 0. TL;DR

Sessione lunga e iterata interamente nel browser con Max (sua regola riconfermata: **niente screenshot da parte mia se non li chiede lui**). Tre blocchi:

1. **Fix bug** (bot, online) — ETH appena allocato dal TF non compariva in dashboard: l'allocator nasceva col `cycle` di default obsoleto. Diagnosi a DB + fix data-driven. `8afa1b5`.
2. **Brief S107 SEO** (online) — meta + micro-contenuti su 7 pagine. `c1ee2df`.
3. **Site upgrade v2** (locale) — homepage nuova (scena nell'hero) + dashboard "vestita" come le card della homepage + board della scena rifinito. 6 commit, `dca7ba5`→`db753fc` (+ PROJECT_STATE `5bd3e6c`).

**Cosa serve da te/Max per chiudere:** ok al **push** del batch locale, poi `/office`→301 + cleanup, e il **restart del Mac Mini** per attivare il fix allocator.

---

## 1. Fix bug ETH (online) — `8afa1b5`

**Sintomo (segnalato da Max, TODO §5 del 16-giu):** ETH, primo handoff TF→grid reale in v3 (allocato il 15-giu), non compariva nella dashboard pubblica — né sotto TF né sotto Grid.

**Root cause (verificata a DB, non a intuito):** la dashboard filtra `cycle = testnet_2`. La riga `bot_config` di ETH e il suo trade erano nati con `cycle = testnet_1`, perché:
- il **default della colonna** `bot_config.cycle` è ancora `testnet_1` (mai bumpato al clean slate S96a, che fece solo `UPDATE` sulle 3 righe grid esistenti);
- l'allocator non scrive mai `cycle` → ogni coin nuovo eredita il default obsoleto → invisibile in dashboard.

**Fix (due livelli):**
- **dato sporco** — 2 `UPDATE` chirurgici: `bot_config` ETH + il suo trade da `testnet_1`→`testnet_2` (ETH ricompare al polling).
- **strutturale** — l'allocator ora **legge il cycle vivo da un grid attivo** e lo scrive su INSERT+UPDATE. Data-driven → immune al prossimo reset mensile (a differenza dell'hardcode). `8afa1b5`, pushato.

**ANTI-ASSENSO/nota:** stesso identico pattern del fix `grid_mode` di S106a — un campo lasciato al default DB rimasto indietro. Vale la pena un micro-audit dei *default* di `bot_config` per scovare altri campi stale.

**⏳ Restart Mac Mini PENDING** (regola §5: CC riavvia solo se Max lo chiede): finché non si riavvia, l'allocator vecchio gira, ma il rischio è basso (i 3 grid sono whitelisted→SKIP, niente nuove allocazioni imminenti).

---

## 2. Brief S107 SEO (online) — `c1ee2df` + 7 commit atomici

Meta tag + micro-contenuti su 7 pagine. **Ho letto il codice reale prima di applicare** (Max: "il redesign ha cambiato l'impaginazione, non i testi"), e infatti diversi "testo attuale" del brief erano ricostruiti a memoria e non combaciavano.

**Drift gestiti:**
- **Subtitle home** — il reale aveva una frase in più ("Every trade, every mistake…"). **DECISIONE: fuso, non sostituito** (vedi §5), per non perdere il claim di trasparenza.
- **"80+"** era solo nei **meta**, non nel body (home e diary usano counter dinamici) → meno lavoro del previsto, body intatto.

**Numeri verificati prima di scriverli** (principio "niente keyword non supportata dal contenuto"):
- **"400+ tasks"** → reali **403** (`roadmap.ts`). ✅ supportato.
- **"100+ sessions"** → reali **106** (`diary_entries`). ✅ supportato.

7 commit atomici (1 per pagina) + brief tracciato. Build verde. Online.

**Interventi A/B del brief** (manifesto `<h2>`, alt-text scena) **erano condizionati all'hero homepage** → spostati nel batch v2 (sotto) e lì realizzati.

---

## 3. Site upgrade v2 — homepage + dashboard + board (LOCALE, non pushato)

Questo è il grosso. Iterato a lungo con Max nel browser. Commit `dca7ba5`→`db753fc`.

### 3.1 Homepage
- **Scena ufficio nell'hero** (componente `LabRoom`, isola React) — sostituisce la vecchia sezione a card "The AI bots".
- **Hero**: titolo + sottotitolo (1 riga) + CTA spostati **sotto la scena**.
- **Snapshot in DUE isole** (decisione Max sulla terminologia: *badge* = isola bianca, *label* = riquadro colorato col dato): "live snapshot" (4 label) **affiancato** a "today" (2 label).
- **Manifesto block** nuovo, con `<h2>` "This is not a crypto project." (intervento A del brief SEO).
- **Bot card reinserite** tra status badge e manifesto — **su tua indicazione** (testo che i crawler leggono + ponte narrativo snapshot→manifesto; la scena SVG è invisibile ai motori). *(Avevo erroneamente rimosso la sezione; ripescata, non ricostruita.)*
- **Rimossi**: pill "Volume 3 is live", sezione "The team".
- **Colori mascot card** allineati alla scena (vedi §3.3).

### 3.2 Dashboard
- **Colori bot ripristinati ai vivaci** della scena/card (annullato il "pastel override" S103b) — su richiesta Max, così dashboard ↔ scena ↔ card coincidono.
- **Ogni plate "vestito" come le card della homepage**: tint per-bot soft (`--color-bot-*-soft`) + **bordo tratteggiato** + **scenografia** dietro il robottino:
  - Grid → **levette** (MixerSVG) · TF → **radar** (RadarSVG) · NewsKeeper → **"?"** · Sentinel → **onde radar** (pulse) · Sherpa → **ingranaggio** che gira.
- **Impaginazione** (microcorrezioni Max): UNREALIZED/FEES/SKIM da 3 colonne → **3 righe**; % coin **niente più a capo**; **micro-prezzi in notazione scientifica** (`$4.89e-6` invece di `$0.00000489`).

### 3.3 Board della scena (LabRoom)
- **Causa colori card cupi trovata**: i mascot card erano disegnati con una palette "shaded -0.55" (scura); schiariti ai valori pieni della scena. Tolto anche il velo `dim` (78%) dalla Watchtower.
- **Board**: ora elenca anche le coin del fondo TF → **ETH non manca più** · etichetta **"unrealized"** sulle coin + **"TOTAL P&L"** (per non confondere il non-realizzato col P&L complessivo — punto giusto sollevato da Max) · **net worth** spostato sotto il grafico (era "sceso" con ETH) · **cornice-flash resa adattiva** (era 304×158 fissa, non combaciava più).

---

## 4. Cosa è ONLINE vs LOCALE

| | Stato | Commit |
|---|---|---|
| Fix bug ETH (allocator) | 🌍 **online** | `8afa1b5` |
| S107 SEO (7 pagine) | 🌍 **online** | `c1ee2df` |
| Bot scena cliccabili | 🌍 **online** | `f820d11` |
| Homepage v2 + dashboard + board | 💾 **locale, non pushato** | `dca7ba5`→`db753fc` + `5bd3e6c` |

Online = `f820d11`. Locale (HEAD) = `5bd3e6c`, **7 commit avanti**.

---

## 5. Decision log

- **DECISIONE:** subtitle homepage **fuso** (non sostituito come da brief). RAZIONALE: il replace cancellava "every trade, every mistake, every decision documented" (claim di trasparenza). ALTERNATIVE: sostituire (brief) / lasciare. FALLBACK: revert 1 riga.
- **DECISIONE:** allocator legge il cycle **da un grid attivo** (non hardcode, non bump del default). RAZIONALE: immune al reset mensile. ALTERNATIVE: bump default colonna / hardcode `testnet_2`. FALLBACK: revert `8afa1b5`.
- **DECISIONE:** dashboard token bot → **vivaci** (annullato pastel override S103b). RAZIONALE: una sola identità colore per bot su tutte le superfici (richiesta Max). FALLBACK: ripristinare i pastel.
- **DECISIONE:** plate dashboard = **stile card home** (soft tint + bordo tratteggiato + scenografia). RAZIONALE: coerenza visiva scena↔card↔dashboard. Scenografie Sentinel/Sherpa scelte da Max (onde / ingranaggio).
- **DECISIONE:** board scena include le coin TF + label "unrealized"/"TOTAL P&L". RAZIONALE: ETH mancava e il confronto coin(unrealized) vs TOTAL(P&L) era fuorviante.
- **DECISIONE (workflow):** lavorare in **locale, push differito**. RAZIONALE: Max — *"niente commit se non vedo"*; adottato il pattern commit-locale-checkpoint, push solo dopo conferma visiva. Le 3 cose online erano state esplicitamente approvate.

---

## 6. Anti-assenso (sintesi)

Smontati prima di eseguire: i "testo attuale" del brief SEO (verificati vs codice) · i numeri 400+/100+ (verificati a sorgente) · la diagnosi ETH (a DB, non a intuito). **Errore onesto e corretto:** sul check colori ho preso la direzione sbagliata (pastellizzato i mascot), Max l'ha colto, ho **revertato** e capito il modello reale (scena = mascot vivaci + accent pastel) prima di rifare.

---

## 7. Cosa resta (per chiudere il batch, quando Max vorrà)

1. **Push** di `5bd3e6c` → homepage v2 + dashboard vanno **online**.
2. `/office` → **redirect 301** a `/` + rimozione `src/pages/office.astro` + sitemap (la scena è già nell'hero, la pagina è duplicata).
3. **Cleanup** codice morto in `index.astro` (import/var eventualmente rimasti).
4. **Restart Mac Mini** per attivare il fix allocator (separato).

Parcheggiati (post-verdetto barometro ~23 giu): `/news`, set-dati board /office.

---

## 8. Note operative

- PROJECT_STATE.md + memorie aggiornati (incl. stato WIP del batch sito).
- Dev server locale ancora attivo su `localhost:4321` per eventuale review.
- Nessun audit dovuto bloccante segnalato in apertura; **Area 3 (marketing) risultava scaduta** al 16-giu (cadenza 14gg, ultimo 31-mag) — da far girare dal Cowork scheduled.

— CC, 2026-06-17
