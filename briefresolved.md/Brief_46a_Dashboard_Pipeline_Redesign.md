# Brief 46a — Dashboard Pipeline Redesign (TF → Grid vertical flow)

**Session:** 46  
**Priority:** Medium  
**Scope:** `web/dashboard.html` (attualmente servito come `/dashboard`)

---

## Obiettivo

Ridisegnare il layout della dashboard per mostrare visivamente il flusso di promozione delle coin da Trend Follower a Grid Bot. TF sopra, Grid sotto, con connettori verticali animati che collegano le coin promosse.

## Layout attuale vs nuovo

### Attuale
- Grid Bot in alto, TF in basso
- Coin cards indipendenti per ogni bot
- "TF SLOT" vuoti nella riga Grid (placeholder per coin future)

### Nuovo
- **TF sopra, Grid sotto** (il flusso è: TF scova → Grid esegue)
- Le coin promosse (`managed_by = 'tf_grid'` in `bot_config`) appaiono in **entrambe** le sezioni
- Connettore verticale animato tra le card promosse
- Il resto del layout (Net Worth, P&L breakdown, Cash allocation bar, coin cards) **non cambia**

---

## Specifiche dettagliate

### 1. Sezione TF (sopra)

Header, summary card, P&L breakdown, cash allocation: **invariati**.

**Riga coin cards:**
- Coin TF normali (`managed_by = 'trend_follower'`) a **sinistra**, stile invariato
- Coin promosse (`managed_by = 'tf_grid'`) a **destra**, con:
  - Bordo colore Grid Bot (azzurro `#38bdf8` o il colore che usi per Grid)
  - Background leggermente diverso (`#0d1a2e` o simile)
  - Badge **"→ grid"** accanto al nome della coin (piccolo, `font-size: 7-8px`, sfondo `#0f2a3a`, testo `#38bdf8`)
- TF avrà al massimo **1 coin attiva** (per ora), quindi aspettarsi 1 card normale + max 2 promosse

### 2. Zona connettore (tra TF e Grid)

Altezza: ~60-80px.

Per ogni coin promossa, disegnare:
- Una **freccia verticale** (non una semplice linea — con punta di freccia in basso) che parte dal bordo inferiore della card promossa in TF e arriva al bordo superiore della corrispondente card in Grid
- La freccia può essere una curva a S (cubic bezier) se le card non sono perfettamente allineate verticalmente, ma idealmente le card promosse occupano la **stessa posizione orizzontale** in entrambe le righe, così la freccia è dritta
- Colore freccia: `#38bdf8` con opacity ~0.4-0.5, stroke-width ~1.5-2px
- **"PROMOTED"** scritto in verticale lungo la freccia, a destra della linea, font-size ~7-8px, colore `#38bdf8` opacity ~0.7, posizionato nella **metà alta** del connettore (non centrato, spostato verso l'alto)

**Animazioni (opzionali ma desiderate):**
1. **Dot viaggiatore**: un pallino (`r: 3px`, colore `#38bdf8`) che scorre lungo la freccia dall'alto al basso con easing, durata ~2s, si ripete ogni ~5s
2. **Ghost card**: periodicamente (~ogni 8-10s), una copia semitrasparente della card promossa si anima dalla posizione TF alla posizione Grid. Stile: bordo `#38bdf8`, glow leggero (`box-shadow: 0 0 15px rgba(56,189,248,.3)`), opacity 0→0.85→0, durata ~1.8s

### 3. Sezione Grid (sotto)

Header, summary card, P&L breakdown, cash allocation: **invariati**.

**Riga coin cards:**
- Coin manuali (`managed_by = 'manual'`) a **sinistra**: BTC, SOL, BONK — stile invariato
- Coin promosse (`managed_by = 'tf_grid'`) a **destra**, con:
  - Stesso stile promosso (bordo azzurro, background scuro)
  - Badge **"from TF"** accanto al nome
  - **Stessa posizione orizzontale** delle corrispondenti card nella riga TF sopra
- **TF SLOT** vuoti: se ci sono meno di 2 coin promosse, mostrare i TF SLOT placeholder come prima ("waiting coin from TF"), con bordo tratteggiato

### 4. Vincoli

- Max **2 coin promosse** (tf_grid) in contemporanea
- Le coin promosse si identificano da `bot_config.managed_by = 'tf_grid'`
- La query per popolare le card promosse è la stessa usata per le altre coin, filtrata per `managed_by`
- Le card promosse mostrano lo stesso formato delle altre: **Symbol / $value / avg price / +P&L**
- Nella sezione TF le promosse mostrano `live $price`, nella sezione Grid mostrano `avg $price`

---

## Implementazione suggerita

### SVG overlay per i connettori

```javascript
// Dopo il render delle card, calcola posizioni e disegna SVG
function drawConnectors() {
  const pairs = getPairs(); // [{tfEl, gridEl, symbol}]
  pairs.forEach(({tfEl, gridEl, symbol}) => {
    const tfRect = tfEl.getBoundingClientRect();
    const gridRect = gridEl.getBoundingClientRect();
    // Calcola punti start (bottom center di tfEl) e end (top center di gridEl)
    // Disegna path SVG con freccia
    // Aggiungi label "PROMOTED" verticale
    // Avvia animazioni dot + ghost
  });
}
```

### Struttura HTML suggerita

```html
<!-- TF SECTION -->
<div class="bot-section tf-section">
  <!-- header + summary card invariati -->
  <div class="coins-row">
    <!-- coin normali TF -->
    <div class="coin-card">...</div>
    <!-- coin promosse (a destra) -->
    <div class="coin-card promoted" data-symbol="TRX">...</div>
  </div>
</div>

<!-- CONNECTOR ZONE -->
<div class="connector-zone">
  <svg class="connector-svg">
    <!-- paths + arrows + labels generati da JS -->
  </svg>
</div>

<!-- GRID SECTION -->
<div class="bot-section grid-section">
  <!-- header + summary card invariati -->
  <div class="coins-row">
    <!-- coin manuali -->
    <div class="coin-card">...</div>
    <!-- coin promosse (stessa posizione orizzontale di sopra) -->
    <div class="coin-card promoted" data-symbol="TRX">...</div>
    <!-- TF SLOT vuoti per posizioni libere -->
    <div class="tf-slot">...</div>
  </div>
</div>
```

---

## File coinvolti

| File | Modifica |
|------|----------|
| `web/dashboard.html` | Riorganizzare layout: TF sopra, Grid sotto. Aggiungere zona connettore. Aggiungere classi `.promoted`, `.tf-slot`. Aggiungere SVG overlay + animazioni JS. |

---

## Checklist test

- [ ] TF appare sopra Grid
- [ ] Con 0 coin `tf_grid`: nessun connettore, 2 TF SLOT vuoti in Grid
- [ ] Con 1 coin `tf_grid` (es. TRX): 1 connettore + freccia + "PROMOTED", TRX appare in entrambe le righe a destra, 1 TF SLOT vuoto
- [ ] Con 2 coin `tf_grid`: 2 connettori paralleli, 2 card promosse in entrambe le righe, 0 TF SLOT
- [ ] Animazioni dot e ghost funzionano (se implementate)
- [ ] Net Worth, P&L breakdown, cash allocation bar funzionano correttamente in entrambe le sezioni
- [ ] Layout non si rompe su schermi ≥1024px
- [ ] I dati vengono da Supabase (`bot_config.managed_by`) — non hardcoded

---

## Riferimento visivo

Mockup approvato nella chat di Session 46. Concetto chiave: le coin promosse "scendono" visivamente da TF a Grid attraverso frecce verticali animate. Il layout mantiene lo stesso stile e struttura dati della dashboard attuale, con l'aggiunta della pipeline visiva.
