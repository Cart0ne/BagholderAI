# Audit Request — Area 3 (Strategia & Marketing) — TEMPLATE EVERGREEN

> Questo è il **template fisso** dell'audit Area 3, valido sempre. L'Auditor lo
> riceve come brief. Cadenza: **mensile (~30 giorni)**, backstop 30gg. Per un audit specifico, Max
> può duplicarlo in `audits/requests/YYYYMMDD_audit[A3].md` e aggiungere note;
> altrimenti questo file è sufficiente così com'è.
>
> **Owner del processo:** Max. **Esecutore:** una sessione CC FRESH (vedi
> `AUDIT_PROTOCOL.md §3`: nessuno sviluppo prima nella stessa chat; l'Auditor
> non shippa codice, solo diagnostica e raccomanda).

---

## 0. Cosa fa questo audit

Fotografa lo stato del marketing (tutti i canali), individua trend di
crescita/decrescita, e produce **diagnosi + strategia** (target e interventi a
breve/medio/lungo periodo). Non è solo una fotografia: deve proporre la rotta.

Il formato è a **2 strati** (vedi §4) per restare sostenibile a cadenza
mensile: un *cruscotto* diagnostico ripetibile + una *strategia* che si
aggiorna invece di riscriversi da zero.

---

## 1. Raccolta dati (FAI QUESTO PRIMA DI ANALIZZARE)

I dati NON si guardano a mano dalle dashboard: si scaricano via API. Dal root
del repo, usando il **Python del venv** (sul Mac Mini `python3.13` di sistema
NON esiste, le dipendenze stanno solo nel venv — verificato 2026-05-30):

```
cd /Volumes/Archivio/bagholderai          # repo sul Mac Mini (Cowork scheduled)
./venv/bin/python -m scripts.marketing_data_refresh
```

> Su una macchina dove `python3.13` ha le dipendenze installate a sistema (es.
> il MacBook in dev) equivale a `python3.13 -m scripts.marketing_data_refresh`.
> Ma per lo **scheduled su Mac Mini usa SEMPRE `./venv/bin/python`**.

Prerequisiti sul Mac Mini (già predisposti 2026-05-30):
- volume `/Volumes/Archivio` montato;
- `config/.env.marketing` presente (chiavi marketing);
- `marketing_data/gsc_token.json` + il `client_secret_*.json` presenti → GSC gira
  **headless** senza aprire il browser. Se il token manca/scade, rigeneralo da
  una macchina con browser (`./venv/bin/python -m scripts.gsc_stats`) e ricopialo.

Questo popola `marketing_data/` con un file datato per piattaforma:

| File | Fonte | Contenuto |
|---|---|---|
| `post_x/x_scan_*.md` | X/Twitter (API v2) | impressions, like, RT, reply per post |
| `marketing_data/devto_*.md` | Dev.to (Forem API) | page views, reactions, commenti per articolo |
| `marketing_data/umami_*.md` | Umami | traffico sito + eventi custom (CTA) + **5 funnel di conversione** |
| `marketing_data/seo_bing_*.md` | Bing Webmaster | impressions/click/posizione + query + pagine |
| `marketing_data/seo_gsc_*.md` | Google Search Console | impressions/click/CTR/posizione + query + pagine |

**Fonti che NON hanno connettore automatico** — recuperale così:
- **Reddit (u/Cart0neM)**: osservazione **manuale**. Reddit ha **chiuso l'accesso API self-service** (verificato 2026-05-30: app self-service terminata; JSON pubblico → 403; Devvit = solo app on-platform; resta solo il contratto commerciale, N/A per noi). Quindi l'Auditor apre il profilo nel browser e annota a mano karma + andamento ultimi post/commenti. Il connettore `scripts/reddit_stats.py` resta **dormiente ma pronto** (ibrido praw + JSON) se un domani Reddit riapre. È un *finding strutturale*, non un dato mancante per pigrizia.
- **Payhip (vendite libri)**: Max esporta il CSV vendite → `marketing_data/payhip_YYYY-MM-DD.csv`. Se assente, segnalalo e marca le vendite "non verificate".
- **Blog (contenuti)**: leggi `web_astro/src/content/blog/*.md` (frontmatter: date, volume, type, tags) per inventario e cadenza di pubblicazione.
- **Vercel Web Analytics**: opzionale via MCP Vercel (traffico totale, utile per stimare il blocco-adblocker di Umami). Se non accessibile, nota il limite.

Se un connettore fallisce (chiave mancante/errore), **non bloccarti**: lavora con
ciò che hai e marca quella piattaforma "dati non disponibili" nel report.

---

## 2. Domande guida

1. **Trend per canale**: ogni piattaforma cresce o cala? Rispetto all'audit
   precedente (delta) e nel trend interno alla finestra.
2. **Cosa funziona / cosa floppa**: quali contenuti/post performano e quali no.
   Pattern ricorrenti (formato, tema, voce, orario).
3. **Funnel & conversioni**: i 5 funnel Umami convertono? Dove si perde traffico?
   Gli eventi CTA (buy-click, cta-*) scattano? Le vendite Payhip seguono il traffico?
4. **Coerenza cross-piattaforma**: i post tra X / Dev.to / Reddit / blog sono
   coerenti per messaggio, voce, CTA? C'è cannibalizzazione o gap?
5. **SEO**: Bing e Google indicizzano? Quali query portano traffico? CTR sano?
6. **Allineamento con BUSINESS_STATE §1-2**: lo stato reale conferma o smentisce
   il positioning/target dichiarato?

---

## 3. Confronto con l'audit precedente

Leggi l'ultimo `audits/reports/*audit[A3]*.md` e calcola i **delta** sulle
metriche chiave (traffico, follower/engagement per canale, SEO, vendite). Il
valore dell'audit mensile è nel **movimento**, non nel valore assoluto.

---

## 4. Struttura del report (output atteso)

File: `audits/reports/YYYYMMDD_audit[A3].md`. Due strati:

### Strato 1 — Cruscotto diagnostico (ripetibile)
- **Tabella metriche per canale** con: valore attuale · delta vs audit precedente · trend nella finestra.
- **Findings** con severity `CRITICAL > HIGH > MED > LOW` (es. "X: reach −40% in 3 settimane", "funnel Library: 0 conversioni").
- Sezione **Cosa funziona** / **Cosa floppa** con esempi concreti (post/articoli specifici).

### Strato 2 — Strategia (si aggiorna, non si riscrive)
- **Target** a breve (2-4 settimane) / medio (3 mesi) / lungo (6-12 mesi), ancorati ai numeri di BUSINESS_STATE §"Target traffico".
- **Interventi proposti**, prioritizzati per `priorità × sforzo` (alto impatto/basso sforzo prima).
- Cosa **ritirare** (canali/tattiche che non rendono) e cosa **raddoppiare**.
- Nota chiara su cosa è **decisione del Board/CEO** vs cosa può eseguire CC.

### Chiusura
- **Verdetto**: `APPROVED` / `CON RISERVE` / `REJECTED`.
- **Riga di sintesi per PROJECT_STATE §9** (1 paragrafo con metriche grezze + next action).
- **Out of scope**: lista esplicita di cosa non hai potuto verificare (es. connettore fallito, Payhip CSV assente, Vercel non accessibile).

---

## 5. Regole

- **Niente login manuale alle dashboard per le fonti automatiche**: per X, Dev.to,
  Umami, Bing, GSC usa SOLO i file in `marketing_data/`/`post_x/`. Se uno di quei
  dati manca, è out-of-scope, non un buco da riempire loggandoti a mano. Fanno
  eccezione le **fonti dichiarate manuali in §1** (Reddit nel browser, Payhip CSV,
  blog nel repo, Vercel via MCP): quelle si raccolgono come scritto lì.
- **Adblocker su Umami**: i numeri Umami sono sotto-stimati (~40-60% del pubblico
  tech blocca). Dichiaralo; incrocia con Vercel se disponibile.
- **L'Auditor non shippa**: i fix/le campagne li flagga, non li esegue (li farà una
  sessione CC normale con brief dedicato, o il CEO).
- Verdetto e riga §9 vanno scritti solo da questa sessione-Auditor (vedi `AUDIT_PROTOCOL.md §5`).
