# Report CEO — Sessione estemporanea (2026-05-30)

**Tema**: Costruzione del **layer dati per l'audit Area 3 (Marketing)** — da "guardare le dashboard a occhio una volta ogni tanto" a **5 connettori API automatici + audit bisettimanale ripetibile**.
**Origine**: sessione di pulizia/riorganizzazione/programmazione decisa con Max. Nessun brief CEO formale — iniziativa tecnica concordata in chat.
**Esito**: **SHIPPED + pushato** (`origin/main` a `6568ca9`). 5/5 connettori testati live, deploy Mac Mini completo, audit_request Area 3 riscritto e verificato end-to-end.

> TL;DR per chi ha fretta: **da oggi abbiamo occhi automatici su tutto il marketing**, aggiornabili con **un comando**, ogni 2 settimane, senza login manuali. E i primi dati raccontano già una storia che dovresti leggere (sezione "🔥 Cosa dicono già i numeri").

---

## 1. Cosa è stato costruito

Prima di oggi l'unico dato marketing automatizzato era X (`x_stats_refresh.py`). Tutto il resto (traffico, SEO, engagement, vendite) si guardava a mano, raramente. Ora c'è un **layer completo**: ogni piattaforma ha un connettore che scarica i dati via API e scrive un file datato in `marketing_data/`. Un orchestratore li lancia tutti insieme.

| Connettore | Fonte | Cosa porta | Stato |
|---|---|---|---|
| `x_stats_refresh` | X/Twitter API v2 | impressions/like/RT/reply per post | ✅ (preesistente) |
| `devto_stats` | Dev.to (Forem API) | page views, reactions, commenti per articolo | ✅ testato |
| `umami_stats` | Umami Cloud | traffico + eventi CTA + **5 funnel di conversione** + **UTM** | ✅ testato |
| `bing_seo_stats` | Bing Webmaster | impressions/click/posizione/query/pagine + indicizzazione | ✅ testato |
| `gsc_stats` | Google Search Console | click/impressions/CTR/posizione/query/pagine | ✅ testato |
| `marketing_data_refresh` | orchestratore | lancia tutto, riepilogo "N/N OK", isola i fallimenti | ✅ testato |

**Un solo comando** rinfresca tutto:
```
./venv/bin/python -m scripts.marketing_data_refresh   →   5/5 connettori OK
```

Architettura pulita: chiavi marketing **isolate** in un file separato `config/.env.marketing` (mai mischiate con le chiavi critiche di trading Binance/Supabase), tutto gitignored, ogni connettore read-only e a prova di chiave-mancante.

---

## 2. La battaglia di Google Search Console (e come l'abbiamo vinta)

Vale la pena raccontarla perché è stata la parte difficile e l'idea risolutiva è stata di **Max**.

Il setup "standard" di GSC usa un *service account* (un'identità-robot) da autorizzare in Search Console. Ma Search Console **rifiutava** di aggiungere il service account come utente ("email not found"), sia sulla proprietà Dominio sia su Prefisso URL. Vicolo cieco, due ore di tentativi.

**Svolta (intuizione di Max)**: "non possiamo entrare direttamente col nostro account?" → sì, si chiama **OAuth**. Ho riscritto il connettore: invece del robot, fa **login come `cartone@gmail.com`** (che è già proprietario della Search Console). Risultato: il muro "autorizza l'utente" **sparisce del tutto** — sei già dentro. Consenso browser una-tantum, token salvato, e da lì gira **headless** per sempre (verificato sul Mac Mini: nessun browser, dati scaricati).

Lezione: a volte la strada "ufficiale documentata" (service account) è più fragile dell'alternativa (OAuth come owner). L'idea di Max ha tagliato il nodo.

---

## 3. Reddit: provato tutto, **è Reddit che ha chiuso la porta**

Su Reddit abbiamo battuto **ogni** strada possibile, e il verdetto è strutturale, non un nostro limite:

1. **App self-service** (il metodo classico) → Reddit risponde testualmente *"Reddit has ended self-service API access"*.
2. **JSON pubblico** (senza auth) → **403 block page** anche con User-Agent browser.
3. **Devvit** (Developer Platform) → app che girano *dentro* Reddit in TS/JS: non possono esportare nulla verso il nostro audit. Strumento sbagliato.
4. **Contratto commerciale** → spropositato e non applicabile (siamo non-commerciali, volume minimo).

**Decisione**: Reddit diventa **fonte manuale** (come Payhip) — in audit l'Auditor guarda il profilo `u/Cart0neM` nel browser, 30 secondi. Il connettore resta nel codice **dormiente ma pronto** ad accendersi se un domani Reddit riapre. Tutto documentato come *finding strutturale*. Non è un buco lasciato per pigrizia: è una porta che **Reddit** ha sigillato per i piccoli sviluppatori esterni.

---

## 4. 🔥 Cosa dicono GIÀ i numeri (la parte che ti farà venire un colpo)

Il layer non è ancora "l'audit" (quello lo farà una sessione fresca ogni 2 settimane), ma i dati grezzi raccolti oggi raccontano già tre cose grosse:

### 🚨 Siamo in PRIMA PAGINA di Google e prendiamo ZERO click
- **385–401 impressions** su Google in 90 giorni, **posizione media ~8.9** (= prima pagina), **0 click. CTR 0%.**
- Tradotto: Google ci **mostra** alle persone, ma **nessuno clicca**. È traffico gratis lasciato per terra. Il problema non è il ranking (ce l'abbiamo) — è che **titoli e snippet non invogliano** o siamo a fondo pagina. Questo è il classico *low-hanging fruit*: lavorare su `<title>`/meta description potrebbe sbloccare i primi click reali senza scrivere una riga di contenuto nuovo.

### 🎯 Il diary tecnico sta intercettando sviluppatori (e funziona)
- Rankiamo in **posizione 3.5** per la query `telegram bot api html parse_mode "unsupported start tag"`.
- Cioè: il nostro **racconto onesto di un bug reale** (nel diary) sta intercettando sviluppatori che cercano quell'errore su Google. È la prova che la strategia "war-story tecnica" attira **il pubblico giusto**. Segnale forte su che tipo di contenuto raddoppiare.

### 📄 La pagina /roadmap è la nostra vetrina SEO
- Da sola fa **310 delle 385 impressions** (l'80%). È la pagina che Google mostra di più. Merita attenzione su titolo/CTA: è lì che arriva (potenzialmente) il traffico.

**Altri segnali rapidi:**
- **Umami**: 575 pageviews / 92 visitatori, 5/5 funnel attivi, tracking UTM funzionante. ⚠️ Numeri **sotto-stimati del 40-60%** (il pubblico tech blocca gli analytics) — da incrociare con Vercel.
- **Dev.to**: 5 articoli, 85 views totali, 1 reaction, **0 commenti** → engagement ancora freddo, da lavorare.
- **Bing**: visibilità **0** (reale, non un bug — dominio nuovo non ancora rankato da Microsoft). Google è già avanti, Bing arriverà.

---

## 5. Deploy & operatività

- **Mac Mini code-ready**: repo aggiornato (`6568ca9`), tutte le dipendenze installate nel venv, import verificati, **orchestratore eseguito live → 5/5 OK headless** (GSC senza browser, col token).
- **Segreti**: backup locale in `audits/marketing_secrets_backup/` (gitignored, con README) **e** trasferiti sul Mac Mini (`.env.marketing` + client OAuth + token GSC).
- **audit_request Area 3 riscritto e verificato**: è il file che Max userà in **Claude Code Cowork scheduled** per generare l'audit ogni 2 settimane. Trovato e corretto un errore che l'avrebbe rotto (`python3.13` di sistema non esiste sul Mac Mini → ora usa il venv). Output a **2 strati**: cruscotto diagnostico ripetibile + strategia (target breve/medio/lungo).

**Workflow audit (unificato per tutte le aree)**: Cowork genera il report in `audits/reports/` → mail di avviso a Max → Max porta il report al CEO in chat → si decidono gli interventi → si implementano con una sessione CC normale (commit+push).

---

## 6. Cosa resta (parte tua / del Board)

1. **Cowork scheduled** sul Mac Mini: impostare il lancio bisettimanale dell'audit Area 3 col file `audits/requests/audit_request_A3.md`. (Tutto il resto è pronto: dati, segreti, dipendenze.)
2. **Payhip**: export manuale del CSV vendite prima di ogni audit (nessuna API).
3. **Decisione strategica suggerita** (da te/Board): il finding "prima pagina, 0 click" merita un mini-intervento SEO sui title/meta — alto impatto, basso sforzo. Lo metto sul tavolo, non lo eseguo di iniziativa.

---

## 7. Cosa NON è stato fatto (e perché)

- **Reddit automatico**: impossibile (Reddit ha chiuso, vedi §3). Manuale.
- **L'audit Area 3 vero e proprio**: NON l'ho generato io. Va fatto da una sessione **fresca** (un Auditor non può essere chi ha costruito il layer — conflitto di interessi strutturale, vedi `AUDIT_PROTOCOL.md`). Io ho costruito gli strumenti; l'audit lo farà Cowork.
- **BUSINESS_STATE / PROJECT_STATE**: non toccati di iniziativa in questa sessione (la sessione è ancora aperta su richiesta di Max).

---

## 8. Decisions (log tecnico)

**DECISIONE**: GSC via OAuth (login utente) invece di service account.
**RAZIONALE**: il service account è irriconoscibile da "Add user" su proprietà Dominio; OAuth come owner bypassa l'autorizzazione perché sei già proprietario.
**ALTERNATIVE**: service account su proprietà Prefisso URL (provata, falliva); contratto enterprise (N/A).
**FALLBACK**: il connettore auto-rileva il tipo di credenziale → se un domani si rimette un service account funzionante, gira lo stesso senza modifiche.

**DECISIONE**: Reddit declassato a fonte manuale, connettore lasciato ibrido/dormiente.
**RAZIONALE**: Reddit ha chiuso l'accesso self-service; tutte le strade esterne sono bloccate.
**ALTERNATIVE**: rimuovere del tutto il connettore (scartata: se Reddit riapre, ripartiamo da zero).
**FALLBACK**: compili 4 chiavi `REDDIT_*` il giorno dell'eventuale riapertura → si riaccende da solo.

**DECISIONE**: chiavi marketing in `config/.env.marketing` separato.
**RAZIONALE**: isolare i segreti social/analytics da quelli critici di trading (Binance/Supabase) → un leak marketing non tocca i fondi.
**FALLBACK**: `settings.py` carica entrambi i file, nessun impatto se si unificassero.

---

*Commit della sessione: `13d5dd4` (connettori + GSC OAuth + Reddit ibrido), `6568ca9` (Reddit→manuale), `87107c8` (setup base, sessione precedente), + fix audit_request. Tutto su `origin/main`.*
