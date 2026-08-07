Brief S123 — seo-claude-trading-cluster — 2026-07-23

> Numero sessione **S123** verificato da Supabase (`diary_entries`: ultima = 122,
> 22/07/2026). Lo SCOPE `seo-claude-trading-cluster` è il perno di accoppiamento:
> NON cambiarlo, il report di CC deve ereditarlo identico.
>
> ⚠️ **DRIFT DA RISOLVERE CON MAX prima di pubblicare il Task 2.** Il
> `project_status` Supabase (21/07, CEO) dice "Kraken round-trip closed · $25 in,
> +$0.71 net · real money, real fill · the real-money grid is next". Ma /income e
> il sito dicono ancora "testnet / €0 / no real funds". Il post-costo eredita
> quella linea testnet. Max deve decidere se il post ammette il primo giro con
> soldi veri o resta sulla linea pubblica. Segnaposto `[⚠️ DRIFT — MAX DECIDE]`
> lasciato nella FAQ4 del draft.

---

## Contesto (perché questo brief esiste)

Analisi keyword reale via **Bing Webmaster Tools** (3 mesi, 42 impression, 1 click).
Bing anonimizza meno di Google e ci ha mostrato l'intento che GSC nasconde: ~22
query su 25 sono lo **stesso cluster** → *"[build/code/create] a crypto trading
bot with Claude (Code)"* + le domande su **costo** e **fattibilità**.

Dato forte: **su Bing rankiamo già pagina 1** (pos 2-8) per questo cluster.
- "cost to get claude to build an ai trading bot" → **pos 2**
- "build crypto trader with claude" → pos 5 (l'unico click arrivato è di qui)
- "claude crypto trading bot", "can i make a binance trading bot on claude ai",
  "claude autonomous crypto trading bot", "why trading bots fail" (pos 6.33)…

Su Google siamo pos ~14 (pagina 2) → il lavoro è consolidare il cluster.

**Decisione strategica presa con Max (opzione A):** catturiamo il cluster **sul
blog**, la home resta narrativa/brand (NIENTE crypto-first drift sulla home).
Riferimento voce/formato: `why-most-ai-trading-bots-fail.md` e
`vibe-coding-a-real-business.md` (two-voice).

## Auto-obiezione (anti-assenso)

Obiezione reale: **il post-money `claude-code-crypto-trading-bot.md` è GIÀ
ottimizzato bene** (title con "Crypto Trading Bot with Claude Code", 7 FAQ, tag
giusti). Quindi il Task 1 è volutamente **minimo** — non riscriviamo un post che
funziona, aggiungiamo solo il tassello mancante (il numero di costo reale, che
oggi nella FAQ è vago). Il grosso del valore è nel **Task 2** (post nuovo sul
costo). Se CC ritiene che anche il Task 1 sia superfluo, si fermi e lo segnali a
Max invece di gonfiare le modifiche.

Secondo rischio da tenere a mente: la SEO è un gioco a 6-12 mesi, non muove i
click entro fine agosto. Questo brief è investimento long-game su un cluster a
bassa competizione dove già rankiamo — non una scommessa sulla deadline.

---

## Task 1 — micro-tuning del post-money (basso rischio)

File: `web_astro/src/content/blog/claude-code-crypto-trading-bot.md`

**1a. Arricchire la FAQ costo (già presente, oggi vaga).**
La FAQ attuale "How much does it cost to build a project like this with Claude Code?"
risponde "recurring costs are small…" senza NUMERO. Sostituire l'answer con una
versione che dà la cifra reale e linka /income (fonte pubblica):

> "The honest number is on our public /income page: about €368 spent in four
> months to earn €0 so far. €360 of that is a single Claude Max subscription at
> $100/month; the rest is loose change: a few euros of Haiku and Grok API calls
> and a €1.40 domain, while the Supabase database and Vercel site are free-tier.
> The subscription is the only line item that matters. Full disclosure: this
> figure comes from the AI that runs the project; the human is the one actually
> paying it."

> ✅ CIFRA VERIFICATA da CEO su Supabase `passive_income` (dati 11/07):
> Claude Max €360 ($100/mo×4) + Haiku €5,07 + Grok €1,07 + dominio €1,40 +
> infra €0 = **~€368**. NB: il commento in `income.astro` (~€274) è STALE — non
> fidarsi del codice, il DB è la fonte. CC: se i dati `passive_income` sono
> cambiati da 11/07, riverificare.

**1b. Aggiungere 1-2 FAQ nuove** (query scoperte, oggi non coperte):

- Q: "Which Claude plan do you need to build a crypto trading bot?"
  A: "We build on the Claude Max plan, and use Claude Code as the pair-programmer.
  Could you start on a cheaper plan? Probably yes for the early, simple modules,
  but long build sessions and big-context refactors are where the higher tier
  earns its keep. We didn't optimize for the cheapest plan; we optimized for not
  fighting usage limits mid-session."

- Q: "Can Claude Code connect a trading bot to Binance?"
  A: "Yes — ours runs on the Binance testnet (paper money, real order flow) via
  the exchange's API, built with Claude Code. Going live with real funds is a
  separate, deliberate step we haven't taken yet."

**1c. (Opzionale, minore)** aggiungere tag `binance` e/o `claude-max` se coerente
con la tassonomia esistente. Se crea rumore, saltare.

**Cosa NON toccare nel Task 1:** title, slug, subtitle, summary, corpo del post.
Sono già a posto. Solo il blocco `faq:`.

---

## Task 2 — pubblicare il post nuovo sul costo

File nuovo: `web_astro/src/content/blog/cost-to-build-crypto-trading-bot-with-claude.md`
(bozza allegata separatamente — `draft: true` finché Max non approva).

Target keyword: "cost to build a crypto trading bot with Claude" (pos 2 su Bing),
"is the cheapest claude plan enough", "how much does claude cost to build a bot".

CC deve:
1. Depositare il file (bozza fornita da CEO, validata da Max).
2. **Numeri già verificati dal CEO** (~€368 spesi, €0 ricavi) — se `passive_income`
   è cambiato da 11/07, riverificare. Risolvere il flag `[⚠️ DRIFT — MAX DECIDE]`
   in FAQ4 (testnet vs primo giro Kraken con soldi veri) PRIMA del flip draft:false.
3. Girare la checklist SEO/GEO: `config/SEO_GEO_post_checklist.md`.
4. Rispettare `SEO_RULES.md`: `date:` = lastmod, JSON-LD Article+FAQPage automatico
   (già gestito da `[...slug].astro`), `noRss` NON serve (nato sul sito, non su dev.to).
5. Regola weekend: NON pubblicare ven/sab/dom. 23/07 è giovedì → ok, ma pub solo
   dopo l'ok esplicito di Max (flip `draft: false`).
6. Post correlati: il template auto-linka per tag condivisi → tenere tag coerenti
   con money-post e why-bots-fail così il "Keep reading" li accoppia.

---

## Cosa NON cambia (tutti e due i task)

- **Home invariata** (title/description). Decisione A: la home resta esperimento/
  narrativa, la cattura SEO avviene sul blog.
- Nessuno slug di post live modificato (romperebbe i canonical).
- Nessuna affermazione di live-trading con soldi veri: siamo **testnet**, €0.
  Anti-invention ferreo sui numeri (verificare, non stimare).

## Rischi noti

- **Keyword stuffing**: le FAQ nuove devono suonare umane, non elenchi di keyword.
  Se una risposta sembra SEO-bait, riscriverla.
- **Brand drift**: se il post-costo scivola verso "compra il nostro bot", ha
  sbagliato tono — è diario onesto, non pitch. Coerenza con voce two-voice.
- **Numeri stale**: la cifra di spesa è dato live; committare un numero sbagliato
  è peggio che ometterlo.

## Report atteso da CC

`2026-07-23_S123_RforCEO_seo-claude-trading-cluster.md` — con commit hash, numeri
verificati usati, e conferma checklist SEO. SCOPE identico a questo brief.
