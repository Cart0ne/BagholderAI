# Report per CEO — S93b — tbot-competitive-analysis

- **Brief sorgente**: `config/2026-06-01_S93b_brief_tbot-competitive-analysis.md`
- **Data analisi**: 2026-06-06 (dati tbot verificati live in questa data)
- **Tipo**: intelligence di prodotto (read-only, nessuna modifica al sito, nessun contatto esterno)
- **Inquadramento (direttiva Max)**: **né guerra né alleanza**. L'estetica è già smarcata (redesign Pastel Sticker v2 LIVE). Il brief è stato ri-focalizzato da "positioning" a **3 domande di prodotto**.

---

## Executive summary

tbot.augustwheel.com è vivo, su **capitale reale** su Kraken, e mostra numeri **palesemente rotti** (+34.208% di return con P&L realizzato −$11.361). L'analisi delle 5 pagine porta a un verdetto netto e in parte sorprendente:

> **Su due delle tre dimensioni che ci interessavano, siamo già avanti noi.** La sua architettura è più stretta della nostra e si sta auto-distruggendo sui microcap; i suoi numeri rotti sono *il nostro vecchio bug* (S96b) che abbiamo già curato; la sua sezione news — che sembra il suo punto forte — sotto il cofano sono gli **stessi 3 feed RSS gratuiti** che NewsKeeper già ingerisce, **senza** la classificazione AI che noi abbiamo.

Il valore della sessione non è competitivo (non è un avversario serio) ma **strategico**: conferma il nostro moat reale (contabilità onesta + brain multipli + news classificata) e suggerisce 2-3 mosse di esposizione a basso costo.

---

## Domanda 1 — Le sue logiche di trading (meglio o peggio delle nostre?)

**Cos'è (inferito dal pubblico):** un puro **breakout/momentum hunter**. Scansiona 1.500+ coppie/ora cercando spike di volume; 3 tier per market cap (Tier 1 top-10, Tier 2 rank 11-30, Tier 3 "unicorn hunter" sui microcap); stop/target per tier (es. Tier 1 stop 4%/target 8%, Tier 2 stop 6%/target 12%); regime detection **price-based** (BTC/ETH a 7gg → BULL/BEAR/RANGING/DIVERGING) che blocca i BUY in BEAR (eccetto Tier 3). Solo long, exit via "Signal" (Claude) o "Stop Loss".

**Confronto con noi:** la sua architettura ≈ il nostro **TF (Trend Follower) coi tier**, ma è SOLO quello. Noi abbiamo **Grid (mean-reversion/DCA) + TF + Sentinel + Sherpa**: spettro più ampio. Il suo regime è più semplice (solo prezzo); il nostro usa anche Fear&Greed + CoinMarketCap.

**Verdetto (sul DISEGNO — sui risultati è impossibile, i suoi numeri sono spazzatura):**
- 🔴 **Si auto-distrugge**: tutti i 43 trade vengono dal Tier 3 (microcap speculativi); i tier "stabili" non hanno mai tradato. Win rate 26%, **worst trade −52% (−$7.868)**, asset FOREST −$9.167.
- 🔴 Quel −52% è **la stessa malattia che abbiamo curato oggi su BONK** (S98a): stop-loss che "salta" perché il book del microcap è vuoto → fill molto sotto. Lui ce l'ha 100× peggio (microcap illiquidi). **Validazione esterna del lavoro S98a.**
- ⚠️ Incongruenza sospetta sul sizing: /about dice Tier 3 = **25%** di posizione, la home dice **2,5%**. Se è davvero 25% su un microcap illiquido, un −52% = −13% di portafoglio in un colpo → spiega il blow-up. Sizing aggressivo sulla parte più rischiosa.

**Conclusione: architettura più stretta della nostra e attualmente in fiamme. Non è meglio.**

---

## Domanda 2 — Dati che espone e noi no (idee da rubare lato presentazione)

Catalogo di ciò che mostra e che varrebbe la pena esporre anche noi:

| Cosa | Lui | Noi oggi | Vale per noi? |
|------|-----|----------|---------------|
| **Tabella Performance per regime** (trade/win/P&L per BULL/BEAR/RANGING/DIVERGING) | ✅ | ❌ (rileviamo il regime con Sentinel ma non lo colleghiamo agli esiti) | 🟢 **Sì, forte** |
| Tabella per-tier / per-brain (trade/win/P&L) | ✅ | parziale | 🟢 Sì (Grid vs TF) |
| P&L by Asset (per-coin: trade/wins/losses/win-rate/totale/media) | ✅ (77 asset) | parziale | 🟡 Sì ma sparsa (3 coin) |
| Curva P&L cumulata (combinata + per-tier) | ✅ | parziale (§3) | 🟡 |
| Discovery/Signal log pubblico ("cosa sta watching lo scanner") | ✅ | ❌ | 🟢 analogo: esporre segnali NewsKeeper o proposte Sherpa |
| Indicatore freshness ("aggiornato N min fa") | ✅ | ❌ | 🟢 quick win |

Il pezzo migliore è la **Performance per regime**: è esattamente il tipo di "processo trasparente" che è il nostro brand, e abbiamo già i dati (Sentinel) per costruirla.

---

## Domanda 3 — La sezione news (sfruttabile per NewsKeeper?)

**Il colpo di scena:** la sua news sembra "ben fatta e aggiornatissima", ma sotto il cofano è **identica a quello che NewsKeeper già mangia**: 30 item da **CoinDesk + CoinTelegraph + Decrypt** (10 ciascuno), link agli originali, "Refreshed every 5 minutes". **Stessi 3 feed RSS gratuiti** che usiamo dal lancio di NewsKeeper (S83). Nessuna API a pagamento, nessuna magia.

E soprattutto: **lui NON ha classificazione AI** — solo titolo + estratto + ora. **Noi sì** (Haiku: sentiment/severità, `haiku_s2`).

**Risposta:** non c'è nulla da rubargli sul backend — **siamo già avanti**. Ciò che a noi manca è solo l'**esposizione pubblica**: una pagina news pulita e auto-refresh. E possiamo batterlo facilmente perché abbiamo già i dati classificati: una pagina che mostra **sentiment/severità AI per ogni titolo** — cosa che lui non ha — ci farebbe sembrare visibilmente più intelligenti.

---

## Implicazioni strategiche

1. **Il nostro moat reale è confermato** e non è l'estetica: (a) **contabilità onesta** (lui mostra numeri impossibili = il nostro bug S96b, che abbiamo diagnosticato e risolto), (b) **architettura multi-brain** (lui ha solo un trend-follower), (c) **news classificata con AI** (lui ha feed grezzo).
2. **Non è un avversario da temere**: capitale reale ma in blow-up su microcap, accounting rotto. La "differenziazione tecnica quasi zero" temuta nel brief **non regge**: il moat esiste, è solo poco raccontato/esposto.
3. **Validazione esterna di S98a**: il suo −52% per stop-loss-su-book-vuoto è la nostra malattia BONK al quadrato. Conferma che il lavoro di oggi (Adaptive Sell Penalty) attacca un problema reale e diffuso.

## Mosse concrete proposte (decisione CEO)

1. **🟢 Pagina /news pubblica** che espone NewsKeeper **con le label AI** (sentiment/severità per titolo) — il suo punto debole, il nostro punto forte. Quick win, dati già esistenti.
2. **🟢 Tabella "Performance per regime"** in dashboard (collega Sentinel agli esiti). Lui ce l'ha, noi no, ed è puro "processo trasparente" = nostro brand.
3. **🟡 Materiale diary/blog**: la trappola contabile comune ("+34.000% con P&L negativo") raccontata **su di noi** (come l'abbiamo presa e risolta in S96b), **senza nominarlo né additarlo**. Rafforza il brand onestà. Contenuto, non codice.

Ognuna è un brief separato se il Board la approva. La 1 e la 2 sono lato sito (frontend, dati già in Supabase); la 3 è editoriale.

## Decisioni del brief — chiuse da Max

- **Contattare augustwheel?** ❌ No (direttiva Max: né alleanza né guerra).
- **Cross-promozione?** ❌ No.
- **Ubersuggest/Ahrefs €29?** ⏸️ Non serve per questa analisi; eventuale solo se si volesse una battaglia SEO/keyword (altra sessione, altra decisione).

## Cosa NON è stato fatto (per scelta)

- Nessun callout pubblico dei suoi numeri rotti (rischio boomerang + glass house: anche i nostri numeri erano sbagliati — è il tema del nostro post sul CEO).
- Nessun contatto esterno, nessuna modifica al sito. Solo ricognizione read-only.

## Caveat metodologico

Da un sito pubblico si vedono gli **esiti**, non il codice: le logiche sono **inferite**, non confermate. Il confronto "meglio/peggio" è qualitativo sul disegno, non un verdetto di performance (i suoi numeri sono inutilizzabili). Tutti i dati tbot citati sono verificati al 2026-06-06.

## Roadmap impact

Potenziale impatto frontend (pagina /news pubblica + tabella regime) se il Board approva le mosse 1-2. Nessun impatto backend (i dati esistono già). Positioning: confermata la rotta "onestà + prodotto editoriale + multi-brain", l'estetica già differenziata col pastel.
