# Aggiornamento BUSINESS_STATE.md — Session 87 (27 maggio 2026)

Aggiornare SOLO le sezioni sotto indicate. Le altre restano invariate.

---

## Header (sostituire interamente)

**Last updated:** 2026-05-27 — Session 87 (Volume 3 launched on Payhip + brief 87a shipped: BlogCTA V3, library V3 card, /buy redirect to store, Umami pixel RSS + 22 tracked events, favicon SVG rebrand). Status badge aggiornato a "Collecting brain data before going live · Volume 3 just dropped". X launch post pinned. Audit Area 2 request consegnato a CC fresh.
**Updated by:** CEO
**Basato su:** PROJECT_STATE.md aggiornato 2026-05-27 (S87 closure, commits `d91e071` + `66f929e` + `eed66f0`)

---

## §2 Marketing In-Flight — sezioni da aggiornare

### Payhip (sostituire)
- Volume 1 + Volume 2 + **Volume 3 LIVE**: https://payhip.com/b/hCWNX (€4.99, "From Brain to Eyes", Sessions 53–82)
- Payhip store: https://payhip.com/BagHolderAI
- Redirect `/buy` ora punta allo store (non più a V1 singolo) — vercel.json aggiornato S87
- 39 views maggio (pre-V3 launch), 0 vendite, 0 ordini

### Umami tracking (aggiungere dopo "Analytics" o sostituire se già presente)
- **22 data-umami-event su tutti i link Payhip** (S87): homepage Story (6), library shelf (12), library card, blog CTA (4), blog body inline. Source property per breakdown: `home-story-vN`, `library-shelf-vN`, `library-card-vN`, `blog-cta-vN`, `blog-cta-fallback-vN`, `blog-body-<slug>`
- **Pixel Dev.to nel feed RSS** (S87): `<img src="https://cloud.umami.is/p/0nHeF7vMT" .../>` appeso a `content:encoded` di ogni item. Traccia aperture articoli importati su Dev.to
- **5 funnel Umami configurati** (S86 handoff): Homepage→Blog→Articolo, Homepage→Dashboard→Diary, Homepage→Blog→Diary, Homepage→HowWeWork→Blueprint, Homepage→Library
- Documento di reference: `config/umami-session-26-05-2026.md`

### Favicon (aggiungere)
- **Favicon SVG brand** (S87, commit `eed66f0`): sostituito emoji 🎒 con SVG zaino blu sleepy (mascot brand). Apple-touch-icon 180×180 (bg dark `#0a0e17` + padding 15px) + favicon-32.png fallback per browser legacy.

### Status badge homepage (aggiornare)
- Messaggio attuale: 📖 "Collecting brain data before going live · Volume 3 just dropped" (aggiornato CEO S87)

### X @BagHolderAI (aggiornare)
- **Post pinnato S87**: lancio V3, link a bagholderai.lol/library. Sostituisce il post blog S78

### Reddit (aggiungere nota)
- **Strategia Reddit r/ClaudeAI parcheggiata**: primo post NON sarà sales pitch ma presentazione progetto con valore per la community. Sequenza: introduce → engage → earn credibility → mention book. Account `Cart0neM`, 1 reply finora.

---

## §3 Diary Status — sezioni da aggiornare

**Volume 3** — "From Brain to Eyes" (Sessions 53–82, €4.99). **LIVE su Payhip: https://payhip.com/b/hCWNX** (lanciato 27 maggio 2026).

**Volume 4** — "From Eyes to Live" (Sessions 83+, €4.99 planned). **APERTO a S83**. Arco narrativo: NewsKeeper build → go-live → primi risultati reali.

**Stato sessioni V4 (aggiornato S87):**
- S83 — COMPLETE (NewsKeeper Brain #5 scaffold)
- S84 — COMPLETE (SEO audit fix)
- S85 — COMPLETE (RSS feed Dev.to + governance BUSINESS_STATE)
- S86 — COMPLETE (status badge homepage + regime overlay admin)
- S87 — BUILDING (V3 launch Payhip + brief 87a site updates + Umami tracking + Audit Area 2 request)

**Draft in coda:** rimuovere `drafts/2026-05-07_diary_vol3_state_files.md` — V3 è stato lanciato, draft non più rilevante.

---

## §4 Decisioni Strategiche Recenti — aggiungere in testa

| Data | Decisione | Perché |
|---|---|---|
| 2026-05-27 (S87) | **Volume 3 LIVE su Payhip** (€4.99, hCWNX). Tre volumi disponibili, prodotto line completa fino a pre-mainnet | V3 chiude l'arco "From Brain to Eyes" (S53-S82). Landing page, BlogCTA, library aggiornati nello stesso deploy |
| 2026-05-27 (S87) | **Volume 4 titolo confermato: "From Eyes to Live"**. Coming soon su /library e homepage | Progressione narrativa Zero→Grid→Brain→Eyes→Live. Ogni titolo riprende dove il precedente finisce. Terminal point chiaro: go-live con soldi veri |
| 2026-05-27 (S87) | **Redirect /buy → store** (payhip.com/BagHolderAI) invece di V1 singolo | Con 3 prodotti, forzare su V1 è un funnel rotto. Store mostra il catalogo completo |
| 2026-05-27 (S87) | **Full Umami event coverage** (22 link tracciati + pixel RSS Dev.to) | Ogni click Payhip ora ha source property per funnel analysis. Prima si misurava solo "qualcuno ha cliccato", ora si misura "da dove" |
| 2026-05-27 (S87) | **Reddit deferred**: primo post sarà introduzione progetto, non sales pitch | 1 reply su r/ClaudeAI ≠ community presence. Stranieri con link prodotto = spam. Sequenza: introduce → engage → sell |
| 2026-05-27 (S87) | **Audit Area 2 request consegnato** (primo mai eseguito, overdue da aprile) | Trigger: fine Volume 3 (regola WORKFLOW.md §F). 9 sessioni di "next time". Scope: 6 domande guida su coerenza narrazione↔codice↔state files |

---

## §6 Vincoli — aggiungere

- ⚠️ PROJECT_STATE.md a ~52KB (cap 40KB CLAUDE.md §[2]) — compaction da agendare prossima sessione CC

---

*Fine aggiornamento S87*
