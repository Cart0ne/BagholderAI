# Brief 80b — Homepage Funnel Fix + TF Status Update + UTM Links

**Basato su:** PROJECT_STATE.md aggiornato 2026-05-18 (S79 chiusura)  
**Scritto da:** CEO, 20 maggio 2026  
**Priorità:** alta — dati Umami mostrano 90% traffico si ferma sulla home senza scoprire il blog  
**Stima:** 1–2 ore totali

---

## Contesto

Analisi traffico 19-20 maggio: 34 visitatori (di cui ~25 umani, il resto bot datacenter). Entry page e exit page = sempre `/`. Il blog ha ricevuto 4 visitatori su 34 (12%). I 3 blog post esistenti hanno un engagement alto (chi arriva legge 2-9 minuti), ma quasi nessuno li scopre dalla home. Il blog appare SOLO nella navbar — zero sezioni, zero CTA nel corpo della pagina.

Payhip ha 39 views totali a maggio, 0 vendite. Il funnel home → blog → Payhip è rotto al primo step.

---

## Blocco 1 — Aggiunta CTA "Read the blog" nell'hero

**File:** `web_astro/src/pages/index.astro`

**Cosa fare:** Aggiungere un terzo pulsante CTA nella hero section, accanto a "Read the diary" e "Live numbers →".

Layout attuale:
```
[Read the diary]  [Live numbers →]
```

Layout target:
```
[Read the blog]  [Read the diary]  [Live numbers →]
```

- "Read the blog" = **pulsante primario** (stile pieno/filled, come "Read the diary" attuale), link a `/blog`
- "Read the diary" = **pulsante secondario** (stile outline), link a `/diary`  
- "Live numbers →" = **pulsante secondario** (stile outline), link a `/dashboard`

Il blog è la porta d'ingresso per i nuovi visitatori. Il diary è per chi è già agganciato.

**Decisioni delegate a CC:** styling esatto dei 3 pulsanti (se 3 pulsanti non stanno bene su mobile, CC può impilare o fare 2+1). Seguire lo STYLEGUIDE.md per colori/spacing.

**Decisioni che CC DEVE chiedere:** nessuna, è un cambio puntuale.

---

## Blocco 2 — Fix TF "ON HOLD" → LIVE

**File:** `web_astro/src/pages/index.astro` (sezione bot cards)

**Cosa fare:** La card Trend Follower mostra:
- Badge: "ON HOLD"
- Subtitle: "PAUSED · v3"
- Corpo: emoji 🩺 + "Trend Follower is undergoing maintenance. Will return smarter."
- Link: "→ see the doctor"

TF è LIVE da S79 (2026-05-18 21:14 CET) su Tier 1-2 only, Tier 3 weight=0.

Aggiornare a:
- Badge: **"LIVE"** (verde, stessa classe del Grid Bot)
- Subtitle: **"ACTIVE · v3"**
- Corpo: mostrare le stesse stats del Grid Bot (Patience, Speed, Capital, Wins, Losses) lette da Supabase. Se i dati TF non sono ancora disponibili nella stessa query della home, mostrare testo statico: **"Scanning Tier 1-2 assets. Shitcoins excluded."**
- Rimuovere emoji 🩺 e link "see the doctor"

**Decisioni delegate a CC:** scelta dell'illustrazione/visual per la card TF live (può riusare lo stile del Grid Bot). Se i dati TF da Supabase richiedono una query separata, CC decide se fare query aggiuntiva o testo statico.

**Decisioni che CC DEVE chiedere:** nessuna.

---

## Blocco 2b — Fix TF sulla dashboard pubblica

**File:** `web_astro/src/pages/dashboard.astro` (o il file che contiene la sezione TF recovery / "dal dottore")

**Cosa fare:** La dashboard pubblica ha una sezione TF con stato "paused" / "dal dottore" / recovery. Deve essere aggiornata per riflettere che TF è LIVE su Tier 1-2.

- Rimuovere la sezione "TF recovery" / "dal dottore" con l'SVG
- Mostrare i dati TF live (stessa logica delle pagine admin se possibile, oppure testo statico: "Trend Follower is live on Tier 1-2. Shitcoins excluded.")
- Se la sezione TF aveva un anchor `#tf-recovery`, rimuoverlo o rinominarlo a `#tf`

**Decisioni delegate a CC:** come presentare i dati TF nella dashboard pubblica (card minimale vs sezione dettagliata). Il modello è la sezione Grid già esistente nella stessa pagina.

**Decisioni che CC DEVE chiedere:** nessuna.

---

## Blocco 3 — UTM nei link automatici

### 3a — Haiku (X auto-poster)

**File:** il file che genera/template il tweet Haiku (probabile `x_poster.py` o `x_poster_approve.py` o simile)

**Cosa fare:** ogni link a `bagholderai.lol` nei tweet generati da Haiku deve avere `?utm_source=x&utm_medium=social&utm_campaign=haiku_daily` appeso.

Se il link è a una pagina specifica (es. `/blog/slug`), aggiungere gli stessi UTM.

### 3b — Report Telegram

**File:** il file che genera il report giornaliero Telegram (probabile `commentary.py` o `daily_report.py`)

**Cosa fare:** ogni link a `bagholderai.lol` nel report Telegram deve avere `?utm_source=telegram&utm_medium=social&utm_campaign=daily_report`.

### 3c — Verifica

Dopo il deploy, verificare che:
1. Un tweet Haiku di test contiene l'UTM nel link
2. Il report Telegram serale contiene l'UTM nel link
3. Su Umami → UTM → Source mostra "x" e "telegram" come fonti separate

**Decisioni delegate a CC:** individuare i file corretti e la logica di template dei link.

**Decisioni che CC DEVE chiedere:** nessuna.

---

## Output atteso

A fine sessione devono esistere:
1. Homepage con 3 CTA nell'hero (blog primario)
2. Card TF aggiornata a LIVE su homepage
3. Sezione TF aggiornata a LIVE su dashboard pubblica
4. UTM nei link Haiku + Telegram
5. Deploy Vercel completato

## Vincoli

- **NON** aggiungere una sezione "From the blog" sulla home (decisione Board: prima misuriamo l'effetto del solo CTA swap, poi valutiamo se serve)
- **NON** spostare la sezione diary o le card bot (il layout attuale above-the-fold funziona)
- **NON** toccare le sezioni live snapshot, bot Grid/Sentinel/Sherpa
- **NON** cambiare la navbar (il link Blog c'è già)
- **NON** toccare il codice dei bot o la logica di trading
- Seguire STYLEGUIDE.md per qualsiasi scelta di design

## Roadmap impact

Nessun impatto su roadmap tecnica. È un fix di conversione/funnel, non una feature.
