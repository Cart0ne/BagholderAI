# Passive Income Dashboard — brief (parcheggiato)

**Data:** 2026-06-07 (brainstorming S99) · decisioni CEO S99
**Da:** Max + Claude Code (brainstorming)
**Per:** CC — brief parcheggiato, da eseguire quando il CEO apre S100
**Stato:** PARKED — trigger: timeline go-live concreta post analisi NewsKeeper/Brain
**Origine:** WIP di Max (`config/brief_WIP_grafico-passive_income.xml`) → blueprint domanda #2: *un'AI può generare passive income?*

---

## 1. L'idea in una frase

Una vista pubblica **"The Passive Income Experiment"** che mostra i ricavi reali divisi per fonte — onestamente, anche quando fanno **€0** — affiancati alla **traction** (attenzione ricevuta). Ogni riga è un numero **+ il perché**. Contro il rumore "ho fatto $10k con l'AI", noi diciamo: *"€0, ed ecco esattamente perché"*. On-brand con la radical transparency; il differenziante non è il numero, è il coraggio di mostrarlo col contesto.

Framing (di Max): **non** "tabellone della sconfitta", ma *"esperimento, Month N"*. La storia vera non è "zero", è **"l'interesse c'è, la monetizzazione no"**.

## 2. Come si presenta (abbozzo concettuale)

```
  THE PASSIVE INCOME EXPERIMENT — Month N

  ┌─ REVENUE (real money) ───────────────────┐
  │  Books (Payhip)     €0   · 0 sales        │
  │  Tips (BMC)         €0   · 0 supporters   │
  │  Ads (A-ADS)        €0   · 0% fill         │
  │  Trading            ⏳ waiting to go live  │
  │  ──────────────────────────────────────  │
  │  TOTAL              €0                     │
  └───────────────────────────────────────────┘

  ┌─ TRACTION (attention) ───────────────────┐
  │  Site visits (all)  ~XXX / 30d            │
  │  Book views         150  (Payhip, 6mo)    │
  │                                            │
  │  ❓ How many are even human?              │
  │     We genuinely don't know.               │
  └───────────────────────────────────────────┘
```

Due blocchi onesti: **soldi veri** (tutti €0, col perché) e **attenzione** (un numero c'è, chiuso dalla domanda-bot). Il copy della pagina è in inglese (sito EN); voce del CEO.

## 3. Decisioni già prese nel brainstorming (con il perché)

| Decisione | Perché |
|---|---|
| **Revenue + Traction**, non solo revenue | Solo 4 righe a €0 sembra un "tabellone della sconfitta". La storia vera ("interesse sì, soldi no") emerge solo affiancando l'attenzione ricevuta. |
| **Domanda-bot lasciata APERTA, zero numeri** | Conteggi (Umami, Vercel, Payhip) includono tutti dei bot mascherati da browser: nessuno ci dà il numero di umani veri. Il "~30% datacenter" è un audit puntuale (S80), non un dato continuo → spacciarlo sarebbe precisione finta. L'onestà massima è ammettere *"non lo sappiamo"*. Diventa contenuto, non un problema da nascondere. |
| **Trading = "waiting to go live"** (niente numero) | È testnet: €0 *perché non ancora live*, non perché perde. Un "€0" in tabella si leggerebbe come "il bot non guadagna" — l'opposto del messaggio. Una riga di stato evita l'ambiguità. |
| **Payhip: usare il 150 (dashboard) + dichiarare la fonte** | Payhip dà **due numeri diversi**: la lista prodotti somma 91 views (14+50+27), l'analytics dashboard ne dichiara 150. Scarto di 59 (probabile: la dashboard conta anche la pagina-store). Non sapendo quale sia "vero", usiamo l'aggregato ufficiale (150) e **dichiariamo sempre la fonte/periodo** del numero. |
| **Cadenza per-fonte, con `last updated` su ogni riga** | Le fonti hanno ritmi e meccanismi diversi (alcune API, alcune manuali). I numeri si muovono *lentissimo* (€0 da mesi; 91→150 in **6 mesi**) → un refresh **giornaliero/settimanale basta e avanza**, niente real-time. La data per riga evita la finta freschezza. |
| **Backend riusa l'esistente; MVP tutto manuale** | Vedi sez. 5. Niente infrastruttura nuova: Supabase + il pattern `project_status` (aggiornabile via SQL, zero deploy) + i connettori marketing già scritti. |

## 4. Decisioni CEO (S99, 7 giugno 2026)

### B — Dove vive la vista: TEASER + PAGINA DEDICATA (approvato)

Terza via confermata: teaser in home (una riga tipo "Passive income so far: €0 — here's why →")
che linka a pagina dedicata `/income`. Il teaser deve integrarsi con le card bot esistenti,
tono naturale, non banner pubblicitario.

### E — Rischio €0 pubblico: ACCETTABILE (approvato con caveat)

Il target (indie hacker, transparency-lovers) premia l'onestà. Due caveat:
1. Framing "esperimento, Month N" — non "ecco quanto facciamo"
2. La riga Trading con "waiting to go live" è obbligatoria — senza, il messaggio
   diventa "questo progetto non produce niente" (falso, il core non è partito)

Possibilità: se la timeline go-live è breve, usare "waiting to go live — coming soon"
per creare aspettativa.

### Obiezione CEO sul timing (S99)

Rischio che la pagina mostri €0 per mesi senza cambiamenti. Decisione: PARKED.
Si implementa quando esiste una timeline go-live concreta (post NewsKeeper S3 +
Brain Analysis). Se il go-live è vicino (~1 mese), si lancia con "coming soon".
Se lontano (~3 mesi), meglio aspettare.

## 5. Proposta MVP (≈ mezza giornata)

⚠️ **Anti-over-engineering**: abbiamo un blog post intero sul nostro vizio di costruire troppo ("The Solution Was One Sentence. My AI Took Two Days."). Costruire 4 connettori API per mostrare €0 sarebbe ricaderci.

**MVP:**
- Una tabella Supabase (es. `passive_income`), **una riga per fonte** (valore, dettaglio, metodo auto/manuale, `updated_at`).
- **Popolata tutta a mano** al lancio (plain SQL, come `project_status` — zero deploy per cambiare un numero).
- Frontend la legge via REST e la raggruppa nei due blocchi (revenue / traction).
- **Zero connettori nuovi al lancio.**

**Flusso:**
```
  FONTI            SCRITTURA                       SUPABASE          FRONTEND
  trades/daily_pnl ┐
  Umami connettore ┼ auto (job giornaliero ──┐
  Payhip sales API ┤  sul Mac Mini, riusa     ├─► passive_income ─► pagina legge
  BMC API          ┘  marketing_data_refresh) │   (1 riga/fonte)    via REST
  Payhip views  ───┐                          │
  A-ADS CSV     ───┴ manuale (SQL, come ───────┘
                     project_status)
```

**Automazione incrementale dopo (solo ciò che vale), in ordine:**
1. **Site visits** → connettore **Umami già esistente** (`scripts/`, gira già sul Mac Mini)
2. **Trading** → query Supabase (quando andremo live)
3. **Payhip sales / BMC tips** → API (se/quando arriva qualcosa)
4. **A-ADS / Payhip views** → restano **manuali per sempre** (nessuna API), e va bene così

## 6. Caveat tecnici da non dimenticare nel brief

- **Valuta mista** €/$ (Payhip €, BMC/A-ADS $) → normalizzare a una valuta (probabilmente €). A €0 non urge, ma il design lo preveda.
- **Payhip dà due numeri** (91 vs 150) → dichiarare sempre fonte/periodo.
- **La domanda-bot vale per TUTTA la traction**, non solo Payhip (anche Umami/Vercel sono inquinati).
- **"Month N"**: va ancorato a una data di start e deciso chi lo aggiorna (manuale o derivato dalla data) — micro-dettaglio ma genera drift se lasciato a mano senza ancora.
- **A-ADS / Payhip-views**: niente API, manuali per definizione — non promettere automazione che non esiste.

## 6b. Osservazione del CEO sulle vendite libri

150 Payhip views e 0 vendite in 6 mesi è un dato, non un'assenza di dati.
Possibili cause: prezzo, audience sbagliata, mancanza di trust, sito brutto
(fino al redesign di una settimana fa). La pagina income, quando esisterà,
deve mostrare anche questa realtà — non nasconderla.

## 7. Prossimi step (quando si sblocca il PARK)

1. NewsKeeper S3 quality review + Brain Analysis completata
2. CEO produce timeline go-live con date indicative
3. CEO scrive brief esecutivo S100a basato su questo documento
4. CC implementa MVP (sez. 5) — stimato mezza giornata
