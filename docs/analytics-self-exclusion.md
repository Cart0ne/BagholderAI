# Analytics — Owner Self-Exclusion

Escludere il tuo browser dal conteggio statistiche del sito (Umami + Vercel
Web Analytics), così le visite che fai per controllare che il sito funzioni
non sporcano i numeri reali.

## Cosa fa

Entrambi gli analytics sul sito leggono un flag `localStorage` all'avvio.
Se il flag è presente, il tag di tracking **non viene iniettato** nella
pagina e nessuna richiesta parte verso i server di analytics.

| Tool                | Flag `localStorage`  | Come funziona                              |
|---------------------|----------------------|--------------------------------------------|
| Umami               | `umami.disabled=1`   | Feature ufficiale di Umami                 |
| Vercel Web Analytics| `va.disabled=1`      | Wrapper custom nelle 10 pagine pubbliche   |

Il flag vale **solo per il browser in cui lo imposti**. Safari Mac, Safari
iPhone, Chrome, Brave, ecc. sono browser distinti → devi ripetere la
procedura su ciascuno che usi per navigare il sito live.

## Setup (Safari macOS) — una volta per browser

### Step 1 — Abilita il menu Develop (solo la prima volta)

Safari per default nasconde gli strumenti da sviluppatore.

- Menu **Safari** (in alto a sinistra) → **Settings**
- Tab **Advanced** (ultima a destra)
- Spunta **Show Develop menu in menu bar**

Ora hai un menu **Develop** nella barra dei menu.

### Step 2 — Apri il sito e la Console

- Apri https://bagholderai.lol (qualunque pagina, landing va bene)
- Menu **Develop** → **Show JavaScript Console**
- Shortcut equivalente: **Option + ⌘ + C**

### Step 3 — Lancia i due comandi

In Console (in basso c'è il prompt `>`), scrivi uno alla volta, Invio dopo ciascuno:

```javascript
localStorage.setItem('va.disabled', '1')
```

```javascript
localStorage.setItem('umami.disabled', '1')
```

Safari risponde `"1"` a ciascuno — quello è il valore appena salvato, è il
segnale che ha funzionato.

### Step 4 — Ricarica la pagina

**⌘+R** (o Cmd+Shift+R per bypass cache).

### Step 5 — Verifica che sei escluso

- Menu **Develop** → **Show Web Inspector**
- Tab **Network**
- Campo filtro in alto a destra: scrivi `umami`
- Naviga tra le pagine del sito (/, /dashboard, /diary, ...)
- Non deve comparire nessuna riga `script.js` verso `cloud.umami.is`

Ripeti il filtro con `insights` (o `vercel`):
- Non deve comparire nessuna riga verso `/_vercel/insights/script.js`

Se entrambe le richieste non partono, **sei escluso** da entrambi i tool.

## Setup (altri browser)

Procedura identica, cambia solo come aprire la Console:

| Browser   | Apri Console                           |
|-----------|----------------------------------------|
| Chrome    | View → Developer → JavaScript Console (⌥⌘J) |
| Firefox   | Tools → Browser Tools → Web Console (⌥⌘K) |
| Brave     | come Chrome                            |
| Edge      | come Chrome                            |

Poi lancia gli stessi due `localStorage.setItem(...)`.

## Setup (Safari iOS / iPadOS)

Più macchinoso, richiede il Mac collegato via cavo:

1. Sul **iPhone**: Impostazioni → Safari → Avanzate → abilita **Web Inspector**
2. Collega iPhone al Mac via USB
3. Apri `bagholderai.lol` nel Safari dell'iPhone
4. Sul **Mac**: Safari → menu Develop → scegli il tuo iPhone → scegli la pagina aperta
5. Si apre Web Inspector che controlla la pagina mobile → tab Console
6. Lancia i due `localStorage.setItem(...)`

Alternative più semplici se non vuoi fare il setup iOS:

- **Non guardare mai il sito pubblico dall'iPhone** — usa solo bagholderai.lol/admin
  o /tf da mobile, che non hanno analytics
- **Accetta di essere un visitatore in più da mobile** — se il traffico reale cresce,
  il tuo singolo browser non falsa molto

## Annullare l'esclusione (se serve testare)

```javascript
localStorage.removeItem('va.disabled')
localStorage.removeItem('umami.disabled')
```

Dopo un refresh, ritorni a essere un visitatore tracciato normalmente.

## Cosa NON esclude il flag

- **Pagine private admin/tf/buy**: non tracciano nessuno, flag o no.
- **Log server-side Vercel** (dashboard → Logs): sempre presenti, zero
  opt-out. Ma non si usano per statistiche aggregate.
- **Log di rete del provider**: esclusi dal nostro stack analytics ma
  non dalle metriche di Vercel internals.

Per uso pratico di "non conto le mie visite nelle statistiche pubbliche"
il flag è sufficiente.

## Dove è implementato (riferimento codice)

- Umami guard (nelle 10 pagine pubbliche):
  blocco `<script>` che legge `localStorage.getItem('umami.disabled')` prima
  di iniettare `cloud.umami.is/script.js`. Già presente da sessione 34.

- Vercel Analytics guard (nelle 10 pagine pubbliche):
  blocco `<script>` che legge `localStorage.getItem('va.disabled')` prima
  di iniettare `/_vercel/insights/script.js`. Aggiunto in sessione 45 —
  commit `e23f3d5`.

Se servono modifiche (es. nuova pagina pubblica), replicare lo stesso
pattern in testa al `<head>`.
