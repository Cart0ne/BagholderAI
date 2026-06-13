# Report S105a — RforCEO — newskeeper-homepage-dedup — 2026-06-13

**Brief sorgente:** `config/2026-06-13_S105a_brief_newskeeper-homepage-dedup.md`
**Commit:** `0c4d810` (web-only, 1 file, +4 −1)
**Esito:** SHIPPED (build verde). **Deploy:** in attesa di OK Max (commit locale, non pushato).
**Scope:** solo frontend Astro. Zero codice bot, zero restart, zero DB change. v1 NON spenta.

---

## ⚠️ Drift istruzioni (segnalato a Max, confermato da lui)

Il brief (Task 1) indicava la card NewsKeeper *"in homepage (`/`), sezione 2.2 The Brains"*. Nel repo reale la card live con headline + barometro **è su `/dashboard` §2.2**, non in homepage:

- **Homepage (`/`)** monta solo `WatchtowerCard.astro` — teaser *locked/dimmed* (Sentinel × NewsKeeper). Non mostra headline e non interroga `newskeeper_signals` (il suo unico fetch, `watchtower-live.ts`, legge solo `sentinel_scores` per la pip del regime). Nessun duplicato lì.
- **`/dashboard` §2.2** (`dashboard.astro:373-392`, dati da `dashboard-live.ts:1605-1631`) è la card con le headline e il barometro 24H. La "sezione 2.2" citata dal brief è proprio la numerazione di `/dashboard` (introdotta in S104).

Quindi **Task 1 e Task 3 erano lo stesso posto** (`/dashboard`). Max ha confermato: l'errore di pagina era suo, non del CEO. Fix applicato a `/dashboard`.

---

## 1. File modificati e diff

**`web_astro/src/scripts/dashboard-live.ts`** (funzione `renderBrains`, query headline NewsKeeper):

```diff
+    /* polarity=not.is.null → keep only NewsKeeper v2 rows (barometro Haiku);
+       v1 shadow rows have polarity NULL and would double every headline
+       during the shadow-comparison window (S105a). */
     const heads = await sbGet<{ summary: string; polarity: number | null }>(
-      "newskeeper_signals", `select=summary,polarity&order=created_at.desc&limit=4`);
+      "newskeeper_signals", `select=summary,polarity&polarity=not.is.null&order=created_at.desc&limit=4`);
```

Nota tecnica: questo codice usa query-string PostgREST raw via `sbGet`, **non** il client JS Supabase — quindi il filtro è `&polarity=not.is.null`, non `.not('polarity','is',null)` come ipotizzato nel brief. Stesso effetto: esclude le righe v1 senza toccare i dati.

**Verifica a DB (sola lettura) — bug confermato e risolto:**

Query attuale (no filtro), `limit=4` → solo **2 titoli unici, ciascuno doppiato** (v1 polarity NULL + v2 polarity set):

| Titolo | polarity | origine |
|---|---|---|
| UK economy shrank 0.1%… | `null` | v1 |
| SpaceX rallies nearly 20%… | `null` | v1 |
| UK economy shrank 0.1%… | `-1` | v2 |
| SpaceX rallies nearly 20%… | `1` | v2 |

Con `polarity IS NOT NULL` → 4 titoli **tutti diversi** (UK -1, SpaceX +1, SpaceX IPO 0, Cryptographers 0). I bullet di severità riflettono la classificazione v2. Volumi 24h: 102 righe v1 + 104 v2 (coerente col brief).

## 2. Barometro v2: filtrava già correttamente? → **SÌ, by-design. Non era un bug.**

Il barometro **non aggrega** `newskeeper_signals` lato client. Legge **una singola riga** da una tabella separata, `newskeeper_regime` (`dashboard-live.ts:1617-1618`, `select=state&order=created_at.desc&limit=1` → `bearish`). Quella tabella è scritta **solo da NewsKeeper v2** (il calcolo polarità→regime avviene nel processo Python v2, non nel frontend; v1 vecchio schema non ha il concetto di regime). Quindi **nessun doppio conteggio**: il barometro era già corretto. Nessuna modifica applicata.

La premessa del Task 2 ("il barometro doppia-conta ogni articolo") assumeva un'aggregazione client-side delle righe signals che non esiste.

## 3. Stato `/dashboard`

`/dashboard` **è** la pagina con le headline NewsKeeper (Task 1 e Task 3 coincidono). Fixata con l'unica modifica sopra. La homepage non ha headline NewsKeeper (solo Watchtower locked), quindi nulla da fare lì.

---

## Decisions

DECISIONE: filtro `&polarity=not.is.null` sulla sola query headline di `/dashboard`; barometro lasciato invariato.
RAZIONALE: esclude le righe v1 dal display senza toccare dati/tabella/bot; il barometro legge già una tabella v2-only, intervenire sarebbe stato un no-op rischioso.
ALTERNATIVE CONSIDERATE: (A) filtrare anche la query barometro — scartata, target sbagliato (`newskeeper_regime`, non `signals`); (B) fix lato homepage come da brief — scartata, lì non c'è card live (drift confermato con Max).
FALLBACK SE SBAGLIATA: revert commit `0c4d810` (singola riga). Quando v1 verrà spenta (post-verdetto barometro ~23 giu), il filtro resta innocuo (tutte le righe avranno polarity).

## Cosa NON è stato fatto
- Nessun deploy Vercel finché Max non dà l'OK al push (commit locale).
- Nessun tocco a v1/v2 Python, tabelle, processi Mac Mini (OFF-LIMITS rispettati).
