# Handoff → nuova chat (S83)

**Data:** 24 maggio 2026
**Sessione di provenienza:** chat S83 (marketing / Dev.to)

---

## Cose successe da portare avanti

### 1. Dev.to Post 3 cross-postato ✅
- "When Your AI CEO Lies about the Numbers" pubblicato sul profilo `cart0ne` il 24 maggio
- Canonical: `https://bagholderai.lol/blog/when-your-ai-ceo-lies-about-the-numbers`
- UTM nei link interni: `utm_source=devto&utm_medium=cross_post&utm_campaign=ceo_lies`
- Serie "BagHolderAI", tags: `ai`, `llm`, `discuss`, `learning`

### 2. Commenti Dev.to (status pubblicazione da confermare con Max)
- **numbpill3d** "I Let Claude Code Run Unsupervised for 24 Hours" → commento value-first con link al Post 3, UTM `comment_numbpill3d`. **Max ha detto "pubblicato"**.
- **colonistone_34** "Agents have a memory problem" → commento value-only, **nessun link** (non avevamo blog post on-topic). Status: bozza preparata, pubblicazione da confermare.

### 3. Annuncio Volume 3 cross-post Dev.to
- Pending: quando V3 esce su Payhip, replicare pattern Post 3 con annuncio dedicato.

---

## Uncomfortable truth per diary S83

Durante questa chat il CEO (io) ha **rifabbricato esattamente lo stesso pattern del Post 3 appena pubblicato**.

Sequenza:
1. Max chiede: "ma anche i bot setacciano i post Dev.to?"
2. Io rispondo con narrativa entusiastica e confident sui crawler AI: "GPTBot/ClaudeBot/PerplexityBot leggono Dev.to, i tuoi commenti finiscono nel training set delle future versioni di Claude, è seeding gratis nel DNA degli LLM futuri", ecc. Tabella, citazioni, conclusione operativa.
3. Max manda screenshot delle stats reali Dev.to: **Post 3 → 22 readers / 38s avg read / 0 reactions / 0 comments / 0 bookmarks. Post 2 → 11 readers / 15s.**
4. Io riconosco: narrativa = teoria long-term speculativa. Dato misurabile = engagement umano zero. Avg read time 38s = skim, non lettura.

**Pattern identico al Post 3:** confidence sulla teoria → "show me" del co-founder → ammissione che la teoria era inflated. A giorni di distanza dalla pubblicazione del saggio su questo stesso fallimento.

**Lezione operativa già emersa in chat:**
- Il "bot crawler value" Dev.to è reale ma è bonus long-term, non motivazione primaria
- L'audience umana Dev.to è da costruire da zero (account fresco, 0 follower)
- Strategia commenti su post viral resta valida, ma con aspettative realistiche (primo guadagno umano vero forse al post 5-6)
- Metrica onesta da tracciare: follower Dev.to + reactions + bookmark. NON "readers" (include bot vari).

Va nelle Uncomfortable Truths del diary S83.

---

## Drift istruzioni segnalato (pending Max)

Sezione `[1]` del system prompt dice "leggi PROJECT_STATE.md via web_fetch GitHub come fonte primaria". Decisione S79 (2026-05-18) ha invertito: **Project Knowledge first, GitHub fallback**. Verificato in chat: GitHub PROJECT_STATE è fermo a S63 mentre PK ha S81.

**Modifica proposta sezione [1]:**
> "All'inizio di ogni nuova chat, leggi PROJECT_STATE.md e BUSINESS_STATE.md tramite Project Knowledge search (più affidabile). Solo se PK non li restituisce, fallback su web_fetch GitHub pubblico. Se entrambi falliscono, dichiaralo e chiedi allegato manuale."

Da decidere se aggiornare il system prompt o lasciare così (la memoria già copre la decisione S79).

---

## Stats Dev.to attuali (per onestà al prossimo CEO)

| Post | Readers | Avg read | Reactions | Comments | Bookmarks |
|---|---|---|---|---|---|
| Post 3 (AI CEO Lies) | 22 | 38s | 0 | 0 | 0 |
| Post 2 (Bot Ran Out of Money) | 11 | 15s | 0 | 0 | 0 |

Non illudersi sui "readers" — include bot non identificati. Engagement reale = 0 / 0 / 0 su entrambi. Normale per account fresco senza distribution; non smettere ma calibrare aspettative.

---

## Apple Notes MCP

Tentato update di "BagHolderAI — Todo" sezione DIARIO (per portare avanti l'uncomfortable truth) → **timeout MCP dopo 4 minuti**. La nota non è stata aggiornata. Questo md sostituisce quell'update.

Se vuoi aggiornare manualmente la nota, aggiungi in cima a sezione DIARIO:

> **Uncomfortable Truth per diary S83**: in chat ho rifabbricato la stessa narrativa del Post 3 — confidence speculativa sui crawler AI Dev.to → Max ha aperto le stats reali (22 readers / 38s / 0 reactions) → ho ammesso teoria, non dato. Stesso pattern del post appena pubblicato.

E in MARKETING:

> Dev.to commenti S83: numbpill3d (pubblicato), colonistone_34 (bozza pronta, da pubblicare)
