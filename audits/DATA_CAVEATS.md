# DATA_CAVEATS — stranezze note dei dati marketing/analytics

> **Leggi questo file PRIMA di toccare qualsiasi numero marketing/analytics.**
> Vale per: Auditor Cowork (Area 3), CEO, CC, o qualunque umano che legga i
> dati. Ogni voce è una trappola già pagata: se la ignori, rifai un errore che
> qualcuno ha già commesso e corretto.

**Perché esiste**: la verifica dell'audit A3 del 2026-07-02 ha confermato i
numeri grezzi ma **ribaltato le conclusioni** — il traffico Umami era inquinato
da bot (DE+FI) e self-traffic (IT). Traffico esterno reale al sito a giugno
2026: **~3 visitatori**. Nessun analista futuro deve ripartire dai numeri lordi.

**La verità di fondo (tienila a mente sempre)**: il collo di bottiglia NON è la
SEO on-page né il CTR — è la **distribuzione**. Con ~3 visitatori esterni/mese,
ottimizzare title/meta è igiene, non una leva. Le leve vere stanno altrove
(canali, contenuti, backlink), non nello snippet.

---

## Umami (traffico sito + funnel)

1. **Bot ricorrenti — Germania + Finlandia.** DE+FI sono bot noti da mesi
   (~420 visite/mese totali, bounce 99–100%, durata 0s, nessun referrer).
   **Azione: FILTRARE SEMPRE** DE+FI prima di ogni analisi. Non sono utenti.

2. **Self-traffic — Italia.** Le visite IT sono ~in gran parte **Max**
   (controllo/sviluppo del sito). Il **traffico esterno reale** è il residuo
   *dopo* aver escluso **DE + FI + IT**. Riferimento: giugno 2026 → **~3
   visitatori** esterni.

3. **API declassata a fonte MANUALE.** Da ~giugno 2026 le API key di Umami
   Cloud sono riservate ai piani a pagamento → il connettore automatico
   (`scripts/umami_stats.py`) riceve **401**. Per gli audit A3 Umami si legge
   **a mano** dalla dashboard (screenshot + filtri paese applicati come sopra).
   **Non tentare di rigenerare/toccare la chiave** (fuori scope, non risolve).

---

## Bing Webmaster (`scripts/bing_seo_stats.py`)

4. **Varianti URL nella "Top pagine".** `GetPageStats` di Bing può restituire
   la **stessa pagina su più righe** (varianti di URL: trailing slash / query
   string / scheme). Il connettore **ora normalizza + aggrega** per URL prima
   di ordinare (fix S115a, 2026-07-02) → attesa **una riga per pagina**. Se
   rivedi righe doppie della stessa pagina, il normalizzatore ha mancato una
   variante nuova: **segnalalo**, non sommare a mano in silenzio.

5. **Impressioni bassissime = rumore.** A questa scala (decine di impressioni/
   mese) il ranking Bing è un dato di *igiene*, non di traffico. Un ottimo CTR
   su 18 impressioni = 1–2 click. Non trattare i movimenti Bing come segnale
   di crescita.

6. **"4xx" = conteggio cumulato, NON URL rotte live.** Il numero di 4xx negli
   audit viene da `GetCrawlStats`, che **somma** le risposte di crawl 4xx sulla
   finestra (~65 giorni) → un "25" può essere solo bot che colpiscono URL
   inesistenti nel tempo, **non 25 pagine rotte adesso**. Le URL problematiche
   *live* stanno in `GetCrawlIssues` (sezione dedicata del report connettore,
   aggiunta S115a). Verificato 2026-07-02: **25 cumulati ma 0 issue live** →
   nessun redirect da fare. Non inseguire i 4xx cumulati come pagine rotte.

---

## Google Search Console (GSC)

7. **Posizione media NON comparabile mese-su-mese.** È **pesata sulle
   impressions**: basta un cambio di *mix* di query/pagine e si sposta senza
   che sia cambiato **nessun ranking reale**. Confronta solo **per-pagina** e
   **per-query**, mai l'aggregato mese-su-mese.

8. **Query anonimizzate.** Le query di `/roadmap` sono ~100% anonimizzate da
   Google (long-tail rara) → **non ottimizzabili** via title/meta (lavoreresti
   al buio). NON riscrivere title/meta di pagine con query prevalentemente
   anonime.

---

## Payhip (vendite)

9. **Views di natura non verificabile.** La dashboard non distingue umano da
   bot sulle *views* dei prodotti. Trattale come **ordine di grandezza**, non
   come conteggio di persone reali. Le **vendite** (ordini) sono invece reali.

---

## Cross-strumento

10. **Vercel Analytics ≠ Umami.** Contano in modo diverso (Vercel non è bloccato
   dagli adblocker, Umami sì; definizioni di "visita"/"pageview" diverse). Sono
   validi solo i **delta DENTRO lo stesso strumento**; **mai** confrontare il
   numero assoluto di uno con quello dell'altro.

---

_Creato: 2026-07-02 (S115a, brief `config/2026-07-02_S115a_brief_seo-hygiene-fixes.md`) dalla verifica dell'audit A3 2026-07-02. Aggiornare quando emerge una nuova stranezza dei dati o quando una qui elencata viene risolta (annotare, non cancellare)._
