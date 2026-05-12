# Brief 65b — Integrazione mascotte Sentinel & Sherpa SVG

**Da:** CEO (Claude)  
**Per:** CC (Claude Code)  
**Basato su:** PROJECT_STATE.md aggiornato 2026-05-07 (S63 chiusura)  
**Sessione:** 65  
**Stima totale:** ~1.5–2h  
**Priorità:** Media (estetica/coerenza, non gating)

---

## Contesto

Claude Design ha prodotto 2 SVG mascotte (Sentinel blu, Sherpa rosso) che 
seguono lo stile visivo dei mascot Grid (verde) e TF (giallo/ambra) già 
presenti nella homepage. I file SVG sono allegati al brief:
- `sentinel.svg` — zaino blu, occhio scanner centrale, antenna ciano
- `sherpa.svg` — zaino rosso, due occhi, bandierina gialla, mappa aperta

Obiettivo: integrare le mascotte in tutto il sito dove servono, sostituendo 
emoji placeholder.

---

## Task 1 — Homepage: aggiornare card Sentinel e Sherpa (~30 min)

Le card "SENTINEL" e "SHERPA" nella sezione "THE AI BOTS · AT WORK" in 
`index.astro` usano attualmente SVG grayed-out/silhouette con label "LOCKED" 
e badge "SOON".

**Cosa fare:**
1. Sostituire le silhouette Sentinel e Sherpa con i nuovi SVG a colori
2. Mantenere label "LOCKED" e badge "SOON" — i bot NON sono ancora live 
   (SHERPA_MODE = dry_run, Sentinel è in raccolta dati)
3. I nuovi SVG mostrano il personaggio a colori ma "spento" — applicare 
   lo stesso effetto dimming/desaturazione usato attualmente per comunicare 
   "not yet active" (es. opacity ridotta, filter grayscale parziale, 
   o overlay scuro — scegliere il metodo più coerente con Grid/TF)

**Vincolo gradient IDs:** i 4 SVG mascotte coesistono nella stessa pagina. 
Rinominare TUTTI i gradient ID per evitare conflitti:
- Grid: `body-grid`, `flap-grid`, `pock-grid`
- TF: `body-tf`, `flap-tf`, `pock-tf`
- Sentinel: `body-sentinel`, `flap-sentinel`, `pock-sentinel`
- Sherpa: `body-sherpa`, `flap-sherpa`, `pock-sherpa`

Verificare anche i gradient ID dei mascot Grid/TF esistenti (generati da 
`BotMascot.astro` o da `mascotSVG()`) — se usano ID generici come `body-r0`, 
rinominarli.

---

## Task 2 — Dashboard private /grid /tf /admin: aggiungere mascotte (~1h)

Le 3 dashboard private in `web_astro/public/` usano emoji (📡, 🎒, ecc.) 
come icone bot. Sostituire con i mascot SVG inline.

**Cosa fare per ciascuna pagina:**

### /grid (`grid.html`)
- Aggiungere mascot Grid (verde) come icona nel header/titolo della pagina
- Dimensione piccola (~40-60px altezza), posizionata accanto al titolo 
  "Grid Control" o equivalente

### /tf (`tf.html`)
- Aggiungere mascot TF (ambra/giallo) come icona nel header/titolo
- Stessa dimensione e posizionamento di /grid

### /admin (`admin.html`)
- Nella sezione Sentinel: aggiungere mascot Sentinel (blu) accanto al 
  titolo sezione
- Nella sezione Sherpa: aggiungere mascot Sherpa (rosso) accanto al 
  titolo sezione
- Nella sezione DB Monitor: nessun mascot (non è un bot)

**Approccio tecnico:** per le pagine `public/*.html` (non Astro), inlinare 
gli SVG direttamente nell'HTML. NON è necessario convertire a .astro per 
questo task — quello è un refactoring futuro separato.

**Vincolo gradient IDs:** anche qui, rinominare gli ID gradient per evitare 
conflitti se più mascot appaiono nella stessa pagina (es. admin.html ha sia 
Sentinel che Sherpa).

---

## File allegati

- `sentinel.svg` — da Max/Claude Design (S65)
- `sherpa.svg` — da Max/Claude Design (S65)
- Grid e TF SVG: estrarre dal componente `BotMascot.astro` o dal DOM della 
  homepage live

---

## Decisioni delegate a CC

- Dimensione esatta dei mascot nelle dashboard private (40-60px range, 
  scegliere ciò che sta meglio)
- Metodo di dimming per card LOCKED in homepage (opacity vs grayscale vs 
  overlay — deve essere coerente col design esistente)
- Se inlinare tutto o usare un `<symbol>` + `<use>` per evitare duplicazione 
  SVG — a discrezione CC

## Decisioni che CC DEVE chiedere

- Se i gradient ID dei mascot Grid/TF esistenti NON possono essere rinominati 
  senza rompere qualcosa → segnalare prima di procedere
- Se il cambio mascotte in homepage richiede modifiche a `BotMascot.astro` 
  che impattano altri usi del componente → segnalare

## Roadmap impact

Nessuno. Task cosmetico/brand, non impatta Phase 9 V&C o go-live.

## Git

Push diretto su main. Commit: `S65: add Sentinel & Sherpa mascots to site`.
