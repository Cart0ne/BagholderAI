# Pastel Sticker v2 — pattern AS-BUILT (regole per finire il sito)

**Creato:** 2026-06-02 (S95b) · **Stato:** homepage COMPLETA (commit `c681427`), resto del sito DA FARE.
**Scopo del redesign (stella polare):** rendere il sito **giocoso e simpatico**, lontano dallo
stile austero di una dashboard finanziaria. È un `.lol`, non un `.com`. Sticker, pastello,
arrotondato, mascotte. Quando un'idea sembra "seria/tecnica", è probabilmente sbagliata.

> Questo doc descrive ciò che è GIÀ stato costruito sulla home, da **replicare** sulle altre
> pagine. L'handoff originale del designer è `REFACTOR_GUIDE_FOR_CC.md` + `theme.css` +
> `bot-cards.css` + i mockup HTML. Qui ci sono le decisioni concrete prese con Max in sessione.

---

## 0. Stato git (NON perdere)
- Branch di lavoro: **`redesign/pastel-sticker-v2`** (tutto il redesign vive qui).
- Checkpoint home: commit **`c681427`**.
- Tag rollback (sito vecchio dark): **`pre-redesign-pastel-v2`**.
- **`main` è intoccato** = la produzione mostra ancora il sito dark finché non si fa merge.
- Anteprima: `cd web_astro && npm run build && npm run preview` → http://localhost:4321/
- Workflow review (regola Max): **prima mostra dal vivo sul preview, NON screenshot**; Max
  controlla nel browser. Si procede **sezione per sezione**, build dopo ogni modifica.
- Archivio "prima/dopo": `dev-screenshots/redesign-pastel-v2/` (before/ = dark baseline,
  `shoot.mjs` = script CDP full-page 1440px ×2 con force-reveal, riusare per l'after).

## 1. Token (già in `web_astro/src/styles/global.css` @theme)
Light pastello. Nomi invariati rispetto al dark (le utility Tailwind si aggiornano da sole).
- Superfici: `bg` #D7E0CA (sage pagina), `surface` #FFFFFF (bianco = dato), `panel` #E9EEDF
  (pale-sage = lettura), `surface-hover` #F4F7EE (salvia chiarissimo, hover), `border` #D2DCC4.
- Testo: `text` #283026 ink, `text-dim` #455041, `text-muted` #59634F (tutti AA).
- Accenti: `primary` #3F7589 (powder), `pos` #4E8A57 (salvia), `neg` #BC4032 (rosso leggibile),
  `neu` #2F7E91, `warn` #B79029, `tf` #B5862E (burro), `cc` #6E68B0 (lilla).
- **`sand` #9A7C3C / `sand-soft` #F4ECD3** — accento sabbia caldo (scelta Max, lo usa volentieri).
- Bot (pastello, override regola §5 STYLEGUIDE): `bot-grid` #5E8A54, `bot-tf` #B5862E,
  `bot-sentinel` #4E8198, `bot-sherpa` #BC4032 + i rispettivi `-soft`.
- Ombre: `shadow-sticker`, `shadow-sticker-sm`. Font display: `font-display` = Bricolage Grotesque.
- ⚠ **Niente hex letterali nel markup**: solo token. Se serve un colore che non c'è → chiedi a Max.

## 2. Tipografia
- **Bricolage (`font-display`, extrabold)** = SOLO titoli grandi: h1 hero, h2 di sezione,
  nomi (bot/team/book), numeroni.
- **`font-sans` (Inter)** = narrazione: sottotitoli, descrizioni, body.
- **`font-mono` (JetBrains)** = dati/label/numeri/meta. (mono=dato, sans=racconto, display=titolo.)

## 3. Pattern delle card (il cuore)
- **Sticker card**: `rounded-2xl border border-border bg-surface shadow-sticker-sm`.
- **Hover (uniforme, NON inverte i colori)**: `transition hover:-translate-y-0.5 hover:shadow-sticker`
  + per le card bianche cliccabili `hover:bg-surface-hover` (lift + salvia chiarissimo). Mai
  invertire bianco↔sage all'hover (Max l'ha bocciato).
- **Card "numerone"** (blog, diary, e il log della dashboard): griglia `[auto_1fr]`, a sinistra
  blocco `[label mono micro / NUMERO Bricolage grande nel colore-sezione / sub mono micro]`,
  a destra il contenuto. **Bordo sinistro colorato** `border-l-4 border-l-<accento>` (come la
  logcard del mockup dashboard).
  - blog: numero = giorno del mese, accento **sand**.
  - diary: numero = sessione, accento **pos (salvia)**.
  - log (dashboard, da fare): numero = "Day N", accento pos; a destra **citazione** corsiva
    (non titolo). L'ultima entry può essere "featured" (più grande, vedi mockup `.logcard.featured`).

## 4. Logica "colore = identità di sezione"
Ogni sezione-lista ha UN accento, usato sia per il **numerone** sia per la **parola-accento
nel titolo** (Bricolage). Es: titolo "Latest **posts**" con "posts" sand + numeri blog sand;
"Development **diary**" con "diary" salvia + numeri sessione salvia. (Diary e blog hanno **stesso
layout**, si differenziano per accento; entrambi su **bianco**.)

## 5. Header di sezione
Bricolage `font-display text-[22px] font-extrabold tracking-[-0.01em] text-text`, con parola
accento nel colore-sezione. NON più il vecchio `§ · Titolo` mono.

## 6. Navbar (fatto)
Pill nav: link = testo `text-text-dim`; **hover = pill bianca piatta** (`hover:bg-surface`);
**attiva = pill bianca rialzata** (`bg-surface shadow-sticker-sm font-semibold`). NIENTE azzurro/
colore sull'attiva (Max l'ha bocciato — bianco è più coerente). Wordmark "BagHolder·AI" grande in
Bricolage. Striscia "live" = chip bianco sticker con dot salvia (niente glow neon).

## 7. Bottoni
Pill `rounded-full`: primario `bg-primary text-primary-ink shadow-sticker-sm`, secondario
`bg-surface text-text`. Hover `-translate-y-0.5`. Display font sui bottoni grandi.

## 8. Bot card (fatto — minimale, NON il rewrite completo del mockup)
Le 4 card home usano il blocco legacy `.bot-card` in global.css, ora ricolorato light:
card bianca, **cornice mascotte = soft per-bot** (`bot-*-soft`, altezza frame **172px** per non
tagliare il radar TF), colori bot **pastello** (token, non più #22c55e/#f59e0b/…), **pill LIVE =
pieno pastello + testo bianco**, **TEST = outline soft**. Mascotte SVG invariate (si leggono sul soft).

## 9. Hero (fatto)
Card bianca "snapshot" con **4 tile colorate 2×2** (Orders powder / P&L salvia / Days **sand** /
Budget powder) + 2 foot-tile su `bg`, **mascot-badge** emoji ruotato. A sinistra: eyebrow =
**pill sabbia inclinata**, h1 Bricolage con "operation." evidenziato in pill powder, CTA a pill.

## 10. Footer (fatto)
Social = **hover pill bianca**; Terms/Privacy/Refund = **solo cambio colore** (muted→ink);
banner a-ads ritematizzato al sage (`background_color=D7E0CA&title_color=3F7589`).

## 11. Spazi
Sezioni di contenuto: `py-4 sm:py-5` uniforme (ritmo costante, compatto).

## 12. Dati live — NON rompere
Cambiare solo la **presentazione**, mai la logica. Preservare gli ID/attributi letti dagli
script: `stat-trades/pnl/days/today-pnl/today-trades/session`, `project-status-box/emoji/text/meta`,
`home-diary-list` + `data-slot`/`data-field`, watchtower/sherpa. (In S95b live-stats è stato
toccato SOLO per presentazione: numero sessione da solo + data "Jun 1".)

## 13. CLS / performance
Elementi rivelati in ritardo da JS (es. badge stato `hidden`→visibile) **riservano lo spazio**
(`min-h-[...]` sul contenitore) per non far scattare la pagina. Pattern già applicato al badge stato.

## 14. Da fare a fine redesign (Fase 4)
- Aggiornare `web_astro/STYLEGUIDE.md` §5 alla palette pastello + nota override bot.
- Catturare gli screenshot **after/** (stesso metodo di before/) per l'archivio + diario.
- Push del branch (anteprima Vercel) → review Max → **merge in main** = go-live.
