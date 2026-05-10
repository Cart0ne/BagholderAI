# Brief 70c — Riapertura sito + aggiornamenti dashboard pubblica

**Data:** 2026-05-10  
**Basato su:** PROJECT_STATE.md aggiornato 2026-05-09 (S69 chiusura, commit cb21179)  
**Autore:** CEO  
**Priorità:** alta — il sito è in maintenance da S65 (5 giorni), i numeri ora sono verificati  
**Stima:** ~3-4h (modifiche distribuite su più file Astro + dashboard)

---

## Contesto

Il sito è in maintenance dal S65 (8 maggio) perché i numeri P&L erano falsati dal bias FIFO (+28%). Da allora:
- Avg-cost trading puro deployato e verificato (S69)
- Reconciliation Binance completata: BTC 9/9, SOL 5/5, BONK 12/12, zero drift (S70)
- Bot Grid stabile su testnet da 36+ ore
- I numeri sono ora certificabili

È il momento di riaprire la vetrina.

---

## Cosa implementare

### 1. Rimuovere maintenance mode

Disabilitare il meccanismo di maintenance (redirect, middleware, o pagina statica — CC sa come è implementato). Il sito deve tornare navigabile normalmente.

### 2. Disclaimer banner — homepage

Banner visibile in homepage, posizionato sotto l'header e sopra il contenuto principale. Stile: announcement bar, sfondo leggero, non aggressivo ma impossibile da ignorare.

**Testo:**

```
🟢 LIVE on Binance Testnet — Real orders, simulated money. 
Every trade you see is executed on Binance's test exchange. 
The logic is real, the dollars aren't. Yet.
```

Design: coerente con lo styleguide Astro. Colore di sfondo suggerito: surface con bordo verde tenue (--green desaturato). NON usare AnnouncementBar.astro se il componente è progettato per altro — creare un componente dedicato `TestnetBanner.astro` o equivalente.

### 3. Replace "paper" → "Binance Testnet"

Cercare in tutto il sito (pagine Astro, componenti, testi statici) ogni riferimento a "paper trading", "paper", "simulated" e sostituire con "Binance Testnet" o "testnet" dove appropriato.

File probabilmente impattati: homepage, dashboard, /blueprint, /howwework, eventuali testi in componenti condivisi.

**NON toccare:** diary entries in Supabase (quelle sono storiche), file .docx, post X archiviati.

### 4. Metrica pubblica principale — Net Realized Profit

Nella homepage e/o dashboard pubblica, sostituire il "Total P&L" come metrica hero con **"Net Realized Profit"**.

**Definizione:**

```sql
SELECT 
  SUM(CASE WHEN side = 'sell' THEN realized_pnl ELSE 0 END) - SUM(fee) 
  AS net_realized_profit
FROM trades 
WHERE config_version = 'v3';
```

È la somma dei guadagni da vendite completate, meno TUTTE le fee (buy + sell). Rappresenta il profitto certo, già incassato, non soggetto a oscillazioni di mercato.

**Label pubblica:** "Net Realized Profit" (o "Verified Profit" — Board deciderà la label finale, per ora usare "Net Realized Profit").

**Nota importante:** il Total P&L (Stato attuale - Budget) può restare visibile come metrica secondaria o nella dashboard dettagliata, ma NON deve essere la metrica hero pubblica.

### 5. Reconciliation table — dashboard pubblica

Aggiungere una sezione nella dashboard pubblica che mostra i risultati della reconciliation Binance. Versione semplificata rispetto a grid.html.

**Layout:** tabella con 3 righe (BTC, SOL, BONK), colonne essenziali:

| Bot | Status | Trades Verified | Drift |
|-----|--------|-----------------|-------|
| BTC | ✓ OK   | 9 / 9           | 0     |
| SOL | ✓ OK   | 5 / 5           | 0     |
| BONK| ✓ OK   | 12 / 12         | 0     |

**Sotto la tabella**, una riga di testo:

```
Every trade on this dashboard is reconciled against Binance. Zero discrepancies.
```

**Fonte dati:** tabella `reconciliation_runs` (creata nello Step A di oggi). Query: ultimo run per symbol, mostrare status + binance_count + db_count + drift_count.

**Aggiornamento:** la tabella si aggiorna automaticamente quando lo script di reconciliation viene rieseguito (per ora manuale, futuro cron).

### 6. Capital at Risk — breakdown

Nella dashboard pubblica, dove appare "Capital at Risk: $600", modificare in:

```
Capital at Risk: $600
  Grid (BTC · SOL · BONK): $500
  Trend Follower: $100 (paused)
```

Il breakdown rende chiaro che il budget è allocato e che TF ha una quota riservata anche se temporaneamente spento.

### 7. Sentinel + Sherpa cards — "TEST MODE"

Le card Sentinel e Sherpa in homepage (quelle con il mascot e lo stato) devono mostrare una label "TEST MODE" visibile.

**Implementazione suggerita:** badge/tag nell'angolo della card, stile coerente con il "LOCKED" già esistente ma con testo diverso. Colore: blu (--color-sentinel #3b82f6) per Sentinel, rosso (--color-sherpa #ef4444) per Sherpa, oppure un colore neutro comune tipo ambra per "test mode".

**Il badge deve dire:** "TEST MODE" o "DRY RUN" — preferenza Board per "TEST MODE" (più comprensibile al pubblico).

Le card NON devono più apparire come "LOCKED" o "OFF" — i cervelli sono riaccesi, solo in modalità osservazione.

### 8. Sezione TF → placeholder "dal dottore"

La sezione della dashboard pubblica che prima mostrava i dati TF (il riquadro grande con le statistiche del Trend Follower) deve essere sostituita con un **placeholder umoristico**.

**Contenuto:** un SVG del mascot TF (ambra) in una scena "dal dottore" — il Board sta commissionando il visual a Claude Design separatamente. Per ora:

1. **Placeholder immediato** (per andare online stasera): card con il mascot TF esistente + testo tipo "Trend Follower is undergoing maintenance. Will return smarter." con un'icona 🩺 o 🔧. Stile coerente con le card Sentinel/Sherpa locked.

2. **Sostituzione futura:** quando il Board fornisce l'SVG "TF dal dottore", CC lo inserisce al posto del placeholder.

**NON rimuovere** la sezione TF — sostituire il contenuto. Lo spazio deve restare occupato per comunicare che TF esiste ed è parte del progetto.

---

## Decisioni delegate a CC

- Meccanismo tecnico di rimozione maintenance (CC sa come è implementato)
- Scelta del componente per il disclaimer banner (nuovo componente vs riuso esistente)
- Layout esatto della reconciliation table nella dashboard pubblica
- Stile del badge "TEST MODE" sulle card Sentinel/Sherpa (coerente con design system)
- Design del placeholder TF temporaneo

## Decisioni che CC DEVE chiedere

- Se la rimozione del maintenance richiede un redeploy Vercel manuale (Max deve farlo dal dashboard Vercel)
- Se qualche pagina referenzia dati TF live che andrebbero a errore con TF spento → segnalare prima di pushare
- Se il cambio della metrica hero (Total P&L → Net Realized Profit) richiede modifiche al componente homepage che impattano anche la dashboard privata grid.html → NON toccare grid.html, la modifica è solo per le pagine pubbliche

## Output atteso

1. Sito online e navigabile su bagholderai.lol
2. Banner testnet visibile in homepage
3. Zero riferimenti a "paper trading" nelle pagine pubbliche
4. Net Realized Profit come metrica hero
5. Reconciliation table nella dashboard pubblica
6. Capital breakdown $500 + $100
7. Sentinel/Sherpa con badge "TEST MODE"
8. Sezione TF con placeholder (SVG definitivo sarà fornito dopo)
9. Nessuna regressione sulle pagine private (grid.html, tf.html, admin.html)

## Vincoli

- **NON toccare** grid.html, tf.html, admin.html (dashboard private)
- **NON toccare** diary entries in Supabase
- **NON modificare** la query/logica della dashboard privata grid.html
- **Mantenere** tutti gli stili custom esistenti (STYLEGUIDE §5 colori bot, design tokens)
- **Mantenere** A-Ads nel footer (SiteFooter.astro — non rimuovere, non spostare)
- **Mantenere** analytics (Umami + Vercel) — non toccare i guard script
- **Task > 1h → piano in italiano** leggibile da Max prima di scrivere codice

## Roadmap impact

Chiude il gate "Sito online con numeri certificati" (pre-live gate da S65). La reconciliation pubblica aggiunge un livello di trasparenza unico nel settore.

## Git

Push diretto su main. Vercel re-deploya automaticamente. Se serve redeploy manuale, chiedere a Max.

---

*CEO, 2026-05-10*
