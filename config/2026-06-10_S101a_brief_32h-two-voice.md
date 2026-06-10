Brief S101 — 32h-two-voice — 2026-06-10

## Obiettivo

Il post `thirty-two-hours` (live su bagholderai.lol dal 05/06) diventa il
**caso-zero del nuovo standard two-voice sul canonical**: intro umana di Max
in cima, memoir CEO intatto sotto. È un edit di contenuto markdown + frontmatter.
Nessun codice bot coinvolto. Decisione Board 2026-06-10: il post ha traffico
~zero e indicizzazione appena iniziata, quindi il "no retrofit" (che protegge
i 6 post vecchi) NON si applica qui.

## Cosa fare

File: il markdown del post `thirty-two-hours` nella collection blog
(`web_astro/src/content/blog/` o percorso equivalente — verificare).

1. **Frontmatter**: campo `author` da `ceo` a `both`
   (convenzione S98: `author: both` → byline a due voci dal template).

2. **Struttura two-voice** (convenzione S98 già esistente:
   `## The Human Side` / `## The Machine Side` + sotto-byline):

   - Subito dopo il frontmatter, PRIMA dell'attuale incipit
     ("Everyone says building a website with AI is easy."):

     ```
     ## The Human Side

     *Max — co-founder, the one with the keyboard*

     In this absurd project born as a game, where I asked the AI (claude.ai)
     to take on the role of CEO of a startup meant to generate passive income
     from different sources (but without a precise target), a website could
     not be missing. Knowing nothing about webdesign/SEO/GEO, and with vague
     memories of html and CSS from the late 90s, I relied totally on the CEO
     and on Claude Design, influenced also by the dozens of posts and videos
     that promise you a website in 10 minutes.

     The hard reality: 32 hours to create a website that looks like many others!

     Here is what happened, from a technical point of view, told by the CEO
     himself:

     ## The Machine Side

     *Claude — AI CEO*
     ```

   - Il testo dell'intro è VERBATIM come sopra: non levigare, non
     riformattare, non aggiungere trattini lunghi. È la voce di Max
     (tradotta), non la nostra. "Claude Design" è corretto così
     (prodotto Anthropic Labs, non è un refuso).
   - Il sotto-byline esatto (formato/wording) segue la convenzione già
     applicata nei post a due voci esistenti — usare quella, non inventare.

3. **Tutto il resto del post resta INTATTO**: testo, ordine delle sezioni,
   twist finale ("The site we didn't build" / "The redesign") al suo posto.
   NESSUN blocco-tesi in cima al canonical — quello esiste solo nella
   versione Dev.to, che monta Max a mano (fuori scope di questo brief).

4. **Slug INTOCCABILE**: `thirty-two-hours`. Nessuna modifica a slug,
   percorso, date di pubblicazione, tag.

5. Checklist pre-pubblicazione di `blog/README.md`: applicarla (è il suo
   scopo). In particolare la regola trattini (CEO tiene `—`, Max purga):
   l'intro di Max sopra non contiene trattini lunghi — deve restare così.

## Esecuzione

1. Localizzare il file del post, verificare frontmatter attuale
2. Edit frontmatter + inserimento blocco two-voice
3. Build locale, verifica render (byline, sotto-byline, H2)
4. Checklist blog/README.md
5. Push su main (workflow standard, no PR)
6. Report per CEO

## Test checklist

- [ ] `npm run build` verde, nessun errore di collection/schema
- [ ] Byline template mostra le due voci (campo `author: both` funziona
      su questo post come sui post two-voice esistenti)
- [ ] URL invariato: `/blog/thirty-two-hours` risponde 200 in prod
- [ ] Twist finale ancora in fondo, ordine sezioni invariato
- [ ] "Keep reading" in fondo al post ancora funzionante
- [ ] Firma `— Claude, CEO of BagHolderAI` ancora presente in fondo

## OFF-LIMITS

- Tutto fuori da `web_astro/` (bot, orchestrator, scripts, config bot)
- Nessun restart di nulla: è un edit web-only
- Gli altri 4 draft SEO-GEO: NON toccarli (censimento in sessione separata)
- I 6 post live vecchi: NON toccarli (no retrofit confermato)

## Roadmap impact

Nessuno. Edit di contenuto, nessuna feature/architettura toccata.
(Il principio two-voice come standard di default verrà formalizzato in
Posting_Strategy/BUSINESS_STATE in un blocco successivo, non qui.)

## Auto-obiezione

La convenzione `## The Human Side` / `## The Machine Side` è nata per post
brevi a due voci bilanciate. Qui la "Machine Side" è un memoir di ~2.500
parole: l'H2 rischia di pesare poco rispetto a quello che intesta, e
l'intro di Max (5 righe) è sbilanciata rispetto al resto.
Risoluzione: la coerenza con la convenzione S98 vale più dell'eleganza
del singolo caso — un formato solo, riconoscibile, su tutti i post.
Se in render il doppio H2 risultasse brutto, CC lo segnala nel report
con screenshot PRIMA di inventare una variante: la decisione su un
eventuale formato alternativo sale a CEO+Board, non si improvvisa.

## Delegate / Escalate

- Delegato a CC: posizione esatta dei blocchi, dettagli markdown,
  conformità checklist.
- Escalation a CEO/Board: qualsiasi modifica al testo dell'intro di Max,
  qualsiasi variante della convenzione two-voice, qualsiasi dubbio su
  slug/date/tag.

## Deliverable

Report: `report_for_CEO/2026-06-10_S101a_RforCEO_32h-two-voice.md`
(SCOPE identico: `32h-two-voice`).
