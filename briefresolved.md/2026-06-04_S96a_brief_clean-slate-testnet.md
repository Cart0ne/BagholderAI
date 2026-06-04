# Brief S96a — clean-slate-testnet — 2026-06-04

**Da:** CEO (Claude, Projects)
**A:** CC (Claude Code, Intern)
**Sessione:** S96
**Pre-condizione:** il nuovo sito deve essere deployato prima di eseguire la parte 2 (disclaimer). Le parti 1 e 3 sono indipendenti dal deploy.

---

## Contesto

La testnet Binance ha eseguito il suo reset mensile durante un riavvio del Mac Mini. I wallet sono tornati ai saldi baseline (10.000 USDT, 1 BTC, 6 SOL, 18.446 BONK). Il DB crede ancora di avere 21,6M BONK, 1,59 SOL, 0,0025 BTC — numeri che non esistono più sull'exchange.

La guardia 72a ha bloccato correttamente BONK (deficit −99,91%). SOL e BTC sono partiti con surplus phantom (il wallet ha più di quanto il DB creda).

**Decisione Board+CEO:** Opzione C — clean slate uniforme per tutti e 3 i grid bot. I vecchi trade restano nel DB taggati come ciclo archiviato. I bot ripartono da zero.

Il TF (Trend Follower) **non è coinvolto** — ha budget e gestione separati, e non è stato impattato dal reset.

Riferimento: `2026-06-04_s96_bonk-testnet-reset-decision_report_for_ceo.md` (report CC).
Precedente storico: `brief_66a_operation_clean_slate.md`.

---

## Parte 1 — Clean Slate Grid Bot (DB + bot state)

### Obiettivo

Archiviare lo storico trade dei 3 grid bot (BTC/USDT, SOL/USDT, BONK/USDT) e farli ripartire da zero con i saldi testnet correnti, senza cancellare dati.

### Implementazione

**Step 1 — Snapshot pre-reset.** Prima di qualsiasi modifica, logga un evento `TESTNET_RESET_CLEAN_SLATE` in `bot_events_log` per ciascun symbol (BTC, SOL, BONK) con dettagli:
- holdings attuali nel DB
- avg_buy_price
- realized_pnl totale
- numero di trade nel ciclo
- cash disponibile

Questo è la "foto ricordo" consultabile in futuro.

**Step 2 — Tagga i trade.** Aggiungi una colonna `cycle` (integer, default 1) alla tabella `trades` via migration. Tutti i trade esistenti ricevono `cycle = 1`. I nuovi trade partiranno con `cycle = 2`.

Alternativa (se CC valuta più semplice): invece di una nuova colonna, aggiungi un campo `reset_at` (timestamp) su `bot_config` per ciascun symbol grid. Le query di replay e dashboard filtrano `created_at > reset_at`. Valuta quale approccio è più pulito — l'importante è che:
- I vecchi trade restino nel DB, consultabili
- Il replay di stato al boot non li consideri
- Il dashboard mostri solo i dati del ciclo corrente

**Step 3 — Aggiorna le query.** Punti da toccare (lista indicativa, CC verifica):
- `bot/grid/state_manager.py` → `init_avg_cost_state_from_db` (replay trade al boot)
- `web_astro/public/admin.html` → query dashboard (P&L, orders, holdings, grafici)
- `web_astro/public/grid.html` → query griglia dettagliata
- Homepage live snapshot → se legge da Supabase direttamente
- `scripts/reconcile_binance.py` → se filtra per config_version

**Step 4 — Reset contatori dashboard.**
- `DAYS RUNNING` → deve ripartire dalla data del clean slate, non dalla data di primo trade assoluto
- `ORDERS` → conta solo trade del ciclo corrente
- `TOTAL P&L` → solo ciclo corrente

**Step 5 — Riavvia i bot.** Dopo la migration + deploy:
1. Ferma orchestrator
2. Riavvia → i 3 grid bot bootano, il replay non trova trade nel ciclo corrente → stato pulito
3. BONK riparte (la guardia 72a passa: DB crede holdings=0, wallet ha 18.446 → surplus, ok)
4. Verifica: tutti e 3 attivi, 0 P&L, cash al 100%

### Test checklist

- [ ] I vecchi trade sono ancora nel DB e consultabili con query diretta
- [ ] Il dashboard mostra 0 orders, $0.00 P&L, 0 days running (o 1)
- [ ] Grid bot cards (BTC/SOL/BONK) non appaiono finché non ci sono holdings
- [ ] BONK si avvia senza blocco della guardia 72a
- [ ] Nessun messaggio Telegram di errore al boot
- [ ] `reconcile_binance.py` gira senza drift

### Auto-obiezione

Aggiungere una colonna `cycle` o un filtro `reset_at` tocca il hot path del bot (replay al boot) e il dashboard. Se il filtro è sbagliato (es. off-by-one sul timestamp), il bot potrebbe bootare con stato parziale. **Mitigazione:** test del replay in dry-run prima del riavvio reale. Inoltre, al prossimo reset testnet (~30gg) servirà incrementare il ciclo di nuovo — verificare che l'operazione sia semplice (un UPDATE o una riga di config).

---

## Parte 2 — Disclaimer Testnet sul sito (post-deploy nuovo sito)

### Obiettivo

Rendere esplicito a qualsiasi visitatore che i dati mostrati sono testnet, non soldi reali, e che i saldi possono essere resettati senza preavviso.

### Implementazione

**A — Dashboard (`/dashboard` o admin.html)**

Aggiungi un banner persistente (non dismissibile) in cima alla sezione dati, prima di qualsiasi numero. Testo:

> ⚠️ TESTNET DATA — These numbers run on Binance Testnet. Balances are reset periodically by Binance without notice. Prices are synthetic and do not reflect real market conditions. No real money is at risk.

Styling: coerente col design del sito. Il banner "FEAR" di Sentinel è un buon riferimento per il pattern visivo (banner fisso in cima, monospace, colore di attenzione).

**B — Homepage (Live Snapshot card)**

Il badge "BINANCE TESTNET · LIVE DATA" c'è già. Aggiungi sotto il badge una riga di testo piccolo:

> Testnet balances reset periodically. Not real money.

**C — Grid page (grid.html)**

Stesso banner della dashboard, adattato al contesto.

### Test checklist

- [ ] Banner visibile su dashboard, homepage snapshot, grid page
- [ ] Banner non dismissibile (no X di chiusura)
- [ ] Testo leggibile su mobile
- [ ] Il banner non copre dati importanti

### Auto-obiezione

Nessuna obiezione reale — è un fix di trasparenza, non c'è downside. L'unica nota: quando andremo su mainnet, il banner dovrà essere rimosso o sostituito con "MAINNET · LIVE". Conviene renderlo configurabile (flag in config o env var) piuttosto che hardcodato.

---

## Parte 3 — Documentazione immagini blog (STYLEGUIDE.md)

### Obiettivo

Aggiornare `web_astro/STYLEGUIDE.md` sezione §22 (Blog) per documentare come aggiungere immagini ai post del blog.

### Implementazione

Aggiungi una sottosezione "Immagini nei post" dopo "Markdown supportato" nella sezione §22. Contenuto:

```markdown
### Immagini nei post

Le immagini si aggiungono con markdown standard nel corpo del post:

```md
![Descrizione accessibile dell'immagine](/images/blog/nome-file.png)
```

**Dove mettere i file:**
- Cartella: `web_astro/public/images/blog/`
- Creare la cartella se non esiste
- Formati accettati: `.png`, `.jpg`, `.webp`
- Naming: kebab-case, descrittivo (es. `old-site-homepage.png`, `dashboard-v1.png`)

**Sizing:**
- Larghezza massima consigliata: 800px (il CSS `.prose-blog img` gestisce il responsive)
- Comprimere le immagini prima del commit (strumenti: `pngquant`, `jpegoptim`, o qualsiasi compressore online)

**Accessibilità:**
- Il testo alt (`![QUESTO TESTO QUI]()`) è obbligatorio — descrive l'immagine per screen reader e per quando l'immagine non carica

**Nota:** il blog NON ha un campo `cover` o `image` nel frontmatter. Le immagini vivono solo nel corpo markdown del post.
```

Inoltre, verifica che il CSS in `[...slug].astro` sotto `.prose-blog` gestisca correttamente le immagini (max-width: 100%, border-radius opzionale, margine verticale). Se non c'è una regola per `img`, aggiungila:

```css
.prose-blog img {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  margin: 1.5rem 0;
}
```

### Test checklist

- [ ] Cartella `web_astro/public/images/blog/` esiste
- [ ] Un'immagine di test nel post è visibile in `npm run dev`
- [ ] L'immagine è responsive su mobile
- [ ] STYLEGUIDE.md aggiornato con la nuova sottosezione

### Auto-obiezione

Nessuna — è documentazione. L'unico rischio è committare immagini pesanti nel repo (git non è pensato per file binari grandi). La nota sulla compressione mitiga.

---

## Roadmap impact

- Dashboard/homepage: aggiunta disclaimer testnet (visuale, non funzionale)
- Blog: nessun impatto roadmap — è documentazione interna
- Grid bot: nessuna feature nuova, è manutenzione stato

---

## Ordine di esecuzione

1. **Parte 3** (STYLEGUIDE) — indipendente, può andare subito
2. **Parte 1** (clean slate) — appena Max conferma che il nuovo sito è online
3. **Parte 2** (disclaimer) — dopo il deploy del nuovo sito, stesso commit della Parte 1 se possibile

Commit message suggerito: `fix: testnet clean slate cycle 2 + disclaimer + blog image docs (S96a)`
Oppure split in commit separati se CC preferisce (uno per parte).
