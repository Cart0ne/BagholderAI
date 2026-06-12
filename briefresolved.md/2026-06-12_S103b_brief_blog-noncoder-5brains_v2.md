# Brief S103b — blog-noncoder-5brains — 2026-06-12

**Da:** CEO (Claude)
**Per:** CC
**Sessione:** S103 (estemporanea marketing)
**Scope:** aggiornamento post blog `non-coder-manages-5-ai-brains-claude-code.md` + pubblicazione

---

## Obiettivo

Aggiornare il post SEO-GEO draft con il formato two-voice (intro Max + voce CEO) e pubblicarlo (`draft: false`).

## File da modificare

`web_astro/src/content/blog/non-coder-manages-5-ai-brains-claude-code.md`

## Modifiche richieste (3 punti, tutti nel file sopra)

### 1. Aggiungere sezioni two-voice IN CIMA al body

Subito dopo il frontmatter `---`, PRIMA del paragrafo "**Can a non-coder use Claude Code...**", inserire il blocco two-voice con header H3 (NON H2 — gli H2 restano riservati alle sezioni keyword-driven per SEO):

```markdown
### The Human Side

*When I started this project, back at the first brainstorm, I thought I'd build a "game" for myself, something quick to test that would let me learn a bit about AI and the crypto world, partly as a hobby partly out of curiosity; generating passive income was never a certainty. I'd say the little game got a bit out of hand, and now I find myself with a website, a blog, 3 volumes of a diary, a marketing plan, and 5 bots that should be trading on my behalf.*

*How did I get to 5 bots, knowing nothing about coding? Here's what the CEO thinks — the real mastermind behind all of this.*

### The Machine Side
```

Separare con una riga vuota dall'inizio del corpo CEO ("**Can a non-coder...**").

**REGOLA GENERALE (da ora in poi):** `### The Human Side` / `### The Machine Side` (H3) su TUTTI i post two-voice — narrativi e SEO. Gli H2 restano per le sezioni di contenuto.

### 2. Tabella "five brains" — riga Tuner

Nella tabella dei 5 brain, riga **Tuner**, la cella di sinistra dice:

> Proposes per-asset parameter settings (still in dry-run)

Rimuovere "(still in dry-run)". Risultato:

> Proposes per-asset parameter settings based on market regime and volatility

(Motivo: Sherpa è passato LIVE testnet in S102 e i parametri Board sono ora dinamici da S103.)

### 3. Firma finale

Sostituire:

```
**— Claude, CEO of BagHolderAI**
```

Con:

```
**— Max & Claude**
```

(Standard two-voice, come `thirty-two-hours`.)

### 4. Pubblicare

Cambiare nel frontmatter:

```yaml
draft: false
```

### 5. Aggiornare la data

Cambiare nel frontmatter:

```yaml
date: 2026-06-12
```

(La data originale era 2026-06-02, data di creazione del draft. La data di pubblicazione è oggi.)

---

## OFF-LIMITS

- NON toccare nessun altro file del progetto
- NON toccare le FAQ nel frontmatter
- NON toccare i cross-link interni (sono corretti)
- NON riscrivere il corpo del post
- NON modificare tags, summary, title, subtitle
- NON restartare il bot

## Verifica post-modifica

1. `npm run build` — deve essere verde, il post deve comparire nella lista blog, nella home (sezione blog recenti) e nell'RSS
2. Verificare che il post renderizzi correttamente su `localhost` (intro in italico, tabella, firma)
3. Push diretto su main (come sempre, NO PR)

## Roadmap impact

Nessuno. È un post di marketing, non tocca backend/bot/trading.

## Anti-assenso

1. La data nel frontmatter: pubblicare con `date: 2026-06-12` (oggi) è corretto perché è la data di pubblicazione effettiva. La data draft originale (06-02) non ha significato per il lettore. Se CC ha obiezioni sulla data (es. impatto su ordinamento blog), le sollevi prima di pushare.

2. Thirty-Two Hours (caso-zero, già live) usa `## The Human Side / ## The Machine Side` (H2). Questo post usa H3. La discrepanza è intenzionale: da ora in poi lo standard è H3, ma Thirty-Two Hours non è retrofit (regola: post live non si toccano). Se CC ritiene che vada allineato dato che è ancora draft su Dev.to, lo segnali — ma il canonical su BHAI resta com'è.

---

## Cross-posting (azione Max, NON CC)

Dopo il push, Max fa cross-post manuale su:
- **Dev.to** — canonical URL: `https://bagholderai.lol/blog/non-coder-manages-5-ai-brains-claude-code`, serie "BagHolderAI", UTM footer: `?utm_source=devto&utm_medium=referral&utm_campaign=crosspost_non-coder-manages-5-ai-brains-claude-code`
- **Medium** — canonical URL stessa
- **Substack** — test puntuale (canale tagliato 08/06, riapertura sperimentale per misurare delta views)
