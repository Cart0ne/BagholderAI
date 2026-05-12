# Draft — howwework.astro v3 update

**Status:** ready for review
**Target file:** `web_astro/src/pages/howwework.astro`
**Created:** 2026-05-07 (session 63)
**Trigger:** introduzione del sistema Verification & Control (PROJECT_STATE / BUSINESS_STATE / AUDIT_PROTOCOL / WORKFLOW)
**Note:** la pagina attuale è v2.0 (march 2026). Questo draft propone l'upgrade a v3.0 con riflessione del nuovo sistema multi-agente + audit.

---

## Sintesi modifiche

1. **Hero update**: bump versione e count attori (3 → 4)
2. **§ 3 Lessons learned**: aggiungere voce "Stale instructions fail silently"
3. **§ 5**: riscrivere completamente. Era "How memory actually works" (parlava di `memory_user_edits` e `memory.md`, ora obsoleti). Diventa "How state actually works" (PROJECT_STATE + BUSINESS_STATE + audit clause)
4. **§ 6 nuova**: "Verification & Control" — il quarto attore (Auditor)
5. **§ 7** (era § 6 "Want to replicate"): aggiungere step 5 "Add state files before you need them"
6. **Nota separata**: il componente React `HowWeWorkInteractive.jsx` va aggiornato per mostrare il quarto attore. Brief separato.

---

## Blocco 1 — Hero update

**Sostituire:**

```astro
<span class="inline-flex items-center gap-1.5">
  <span class="inline-block h-1.5 w-1.5 rounded-full bg-pos
               shadow-[0_0_8px_rgba(134,239,172,0.7)]"></span>
  v2.0 · march 2026
</span>
<span class="text-border">·</span>
<span>updated when workflow changes</span>
<span class="text-border">·</span>
<span>3 entities · 1 terminal</span>
```

**Con:**

```astro
<span class="inline-flex items-center gap-1.5">
  <span class="inline-block h-1.5 w-1.5 rounded-full bg-pos
               shadow-[0_0_8px_rgba(134,239,172,0.7)]"></span>
  v3.0 · may 2026
</span>
<span class="text-border">·</span>
<span>updated when workflow changes</span>
<span class="text-border">·</span>
<span>4 entities · 1 terminal</span>
```

---

## Blocco 2 — Lessons learned: nuova voce

**Aggiungere alla sezione § 3 "Lessons we learned"** (in fondo, prima della chiusura del `space-y-5`):

```astro
<div class="border-l-2 border-pos/60 pl-4">
  <div class="font-mono text-[13px] font-semibold text-text">
    Stale instructions fail silently.
  </div>
  <p class="mt-1 text-[14px] leading-[1.6] text-text-dim">
    For a month and a half, the CEO kept writing briefs based on
    assumptions two sessions out of date — referencing files that had
    moved, forgetting decisions made the week before. Smarter prompts
    didn't fix it. State files did. Two markdown files, one written by
    each AI, both read at the start of every session. The kind of
    plumbing nobody brags about and everyone ends up needing.
  </p>
</div>
```

---

## Blocco 3 — § 5 riscritta (sostituisce l'esistente "How memory actually works")

**Sostituire l'intera sezione § 5 con:**

```astro
{/* ============ § 5 — HOW STATE ACTUALLY WORKS ============ */}
<hr class="mt-12 border-t border-border-soft" />
<section class="mt-8">
  <h2 class="font-mono text-[12px] uppercase tracking-[0.18em] text-pos mb-5">
    § 5 · How state actually works
  </h2>

  <p class="mb-5 text-[14.5px] leading-[1.7] text-text-dim">
    Three AI conversations, two machines, one human bridge. Without
    explicit state management, context drifts: the CEO writes briefs
    based on what the codebase looked like two sessions ago, the
    intern doesn't know about strategic decisions made yesterday in
    Claude Projects. Two living files in the repo solve this — one
    written by each AI, both read at the start of every session.
  </p>

  <div class="space-y-5">
    <div class="border-l-2 border-pos/60 pl-4">
      <div class="font-mono text-[13px] font-semibold text-text">
        PROJECT_STATE.md
      </div>
      <p class="mt-1 text-[14px] leading-[1.6] text-text-dim">
        The tech-side state. Written by the intern (Claude Code) at
        the end of every coding session, committed to the repo. Nine
        canonical sections: current state, active architecture,
        in-flight work, recent decisions with rationale, known bugs,
        open questions for the CEO, deadlines, what was deliberately
        not done, and external audits. If you want to know what the
        code is doing today, this is the file.
      </p>
    </div>

    <div class="border-l-2 border-pos/60 pl-4">
      <div class="font-mono text-[13px] font-semibold text-text">
        BUSINESS_STATE.md
      </div>
      <p class="mt-1 text-[14px] leading-[1.6] text-text-dim">
        The strategy-side state. Written by the CEO (Claude Projects)
        at the end of every strategic session. Seven sections: brand
        and messaging, marketing in-flight, diary status, recent
        strategic decisions, open questions for the intern, non-tech
        deadlines, and what is deliberately not happening. The file
        the intern reads to remember why we're doing what we're doing.
      </p>
    </div>

    <div class="border-l-2 border-pos/60 pl-4">
      <div class="font-mono text-[13px] font-semibold text-text">
        The audit clause
      </div>
      <p class="mt-1 text-[14px] leading-[1.6] text-text-dim">
        Both AIs operate under one mandatory rule: if you notice that
        an instruction references a file that doesn't exist, a decision
        that's been superseded, or anything that contradicts the
        current state of the repo — stop and flag it. Don't execute
        from stale context. The rule caught its first drift within
        hours of being introduced: the CEO had a roadmap path that
        pointed to a file gitignored months ago. Nothing was broken,
        nothing was technically wrong, but every roadmap update was
        silently editing a legacy file that hadn't been deployed since
        the site migration. The audit clause surfaced it.
      </p>
    </div>

    <div class="border-l-2 border-pos/60 pl-4">
      <div class="font-mono text-[13px] font-semibold text-text">
        The human (Max)
      </div>
      <p class="mt-1 text-[14px] leading-[1.6] text-text-dim">
        Still the bridge — but now a bridge with a railing. Carries
        artifacts between the AIs (copy-paste from Claude Projects into
        a new file, hand it to Claude Code for the commit), approves
        plans before code is written, reads WORKFLOW.md when exhausted
        at midnight. The three-way split works because each
        participant compensates for the others' constraints: the CEO
        thinks but can't execute, the intern executes but resets every
        session, and Max can do both but doesn't scale. The state
        files exist precisely because Max doesn't scale.
      </p>
    </div>
  </div>
</section>
```

---

## Blocco 4 — § 6 nuova (Verification & Control)

**Inserire NUOVA sezione tra l'attuale § 5 (ora riscritta come "How state actually works") e l'attuale § 6 "Want to replicate this?".**

Il "Want to replicate" diventa **§ 7**.

```astro
{/* ============ § 6 — VERIFICATION & CONTROL ============ */}
<hr class="mt-12 border-t border-border-soft" />
<section class="mt-8">
  <h2 class="font-mono text-[12px] uppercase tracking-[0.18em] text-pos mb-5">
    § 6 · Verification & Control
  </h2>

  <p class="mb-5 text-[14.5px] leading-[1.7] text-text-dim">
    Two AIs writing each other state files is not enough by itself —
    the loop can become self-reinforcing. Both could agree on a
    fiction. The fourth entity in this project is an external auditor:
    a fresh Claude Code session, with no continuity, called
    periodically to verify, flag drift, and produce a written report.
    Inspired by how construction sites have an independent inspector
    distinct from both the architect and the contractor.
  </p>

  <div class="space-y-5">
    <div class="border-l-2 border-pos/60 pl-4">
      <div class="font-mono text-[13px] font-semibold text-text">
        Three areas of audit
      </div>
      <p class="mt-1 text-[14px] leading-[1.6] text-text-dim">
        <strong class="text-text">Technical</strong> — code correctness
        and behavioral consistency across modules (does Sentinel pass
        Sherpa the data it expects? Does the Grid bot read the
        parameters Sherpa writes?). Run monthly and after major
        features.<br/><br/>
        <strong class="text-text">Project coherence</strong> — drift
        between diary, site, code, and strategy. Does the homepage
        message match what the bots actually do? Are there gaps
        between what the brief said and what got built? Run at the
        end of every diary volume.<br/><br/>
        <strong class="text-text">Strategy and marketing</strong> —
        positioning, messaging, channel coherence. Trickier to run
        meaningfully at five visitors per month, but the muscle is
        there for when the numbers grow.
      </p>
    </div>

    <div class="border-l-2 border-pos/60 pl-4">
      <div class="font-mono text-[13px] font-semibold text-text">
        Private reports, public verdicts
      </div>
      <p class="mt-1 text-[14px] leading-[1.6] text-text-dim">
        Audit reports themselves are local-only (gitignored) — they
        can be candid about strategic weaknesses without becoming
        public liabilities. But a one-line verdict (date, area, topic,
        outcome) is appended to PROJECT_STATE.md, so both AIs see what
        has already been audited and can't ignore unresolved
        recommendations. Transparency on the existence of audits,
        privacy on their full content.
      </p>
    </div>

    <div class="border-l-2 border-pos/60 pl-4">
      <div class="font-mono text-[13px] font-semibold text-text">
        The auditor doesn't decide
      </div>
      <p class="mt-1 text-[14px] leading-[1.6] text-text-dim">
        Clear boundaries: the auditor flags, the CEO decides, the
        intern executes. The auditor doesn't write code as part of the
        verification (except for trivial inline fixes), doesn't change
        strategic direction, doesn't replace the internal checks
        Sentinel and Sherpa run at runtime. The point is independent
        verification, not parallel governance.
      </p>
    </div>
  </div>
</section>
```

---

## Blocco 5 — § 7 ex § 6 ("Want to replicate this") — aggiungere step 5

**Aggiungere allo `space-y-4` esistente, dopo lo step 4:**

```astro
<div>
  <div class="font-mono text-[13px] font-semibold text-amber-400">
    5. Add state files before you need them
  </div>
  <p class="mt-1 text-[14px] leading-[1.6] text-text-dim">
    Two markdown files in the repo root: one written by your CEO AI,
    one by your coding AI. Both read at the start of every session.
    It feels like overhead until the day you realize a brief is based
    on assumptions two weeks old. Then it feels like the only thing
    keeping the project sane.
  </p>
</div>
```

E rinominare il titolo della sezione da § 6 a § 7:

```astro
<h2 class="font-mono text-[12px] uppercase tracking-[0.18em] text-pos mb-5">
  § 7 · Want to replicate this?
</h2>
```

---

## Componente React (HowWeWorkInteractive.jsx) — task separato

Il diagramma interattivo in § 1 attualmente mostra 3 attori: CEO, Co-Founder/Max, Intern. Va aggiunto un quarto: **Auditor**.

Caratteristiche del nuovo nodo:
- Posizione: esterna al triangolo (sopra, sotto, o di lato — design choice)
- Connessioni: punteggiate o tratteggiate (è esterno al loop continuo)
- Trigger label: "monthly / end-of-volume / quarterly / on-demand"
- Direzione produzione: → audit reports (locale, gitignored) → PROJECT_STATE.md sezione 9
- Boundary tag: "flags, doesn't decide, doesn't execute"

Brief separato per CC (NON in questo deploy):

```
Aggiorna web_astro/src/components/HowWeWorkInteractive.jsx aggiungendo
un quarto attore "Auditor" al diagramma. Vedi specifica in
drafts/2026-05-07_howwework_v3.md sezione "Componente React".
```

---

## Mini-brief per CC (per applicare i blocchi 1-5)

```
Aggiorna web_astro/src/pages/howwework.astro applicando le modifiche
descritte in drafts/2026-05-07_howwework_v3.md.

Blocchi da applicare in ordine:
1. Hero update (v2.0 → v3.0, march → may, 3 → 4 entities)
2. Aggiungi voce "Stale instructions fail silently" alla § 3 Lessons learned
3. Sostituisci interamente § 5 (era "How memory actually works",
   diventa "How state actually works")
4. Inserisci NUOVA sezione § 6 "Verification & Control" prima
   dell'attuale "Want to replicate"
5. Rinomina la sezione "Want to replicate" da § 6 a § 7 e aggiungi
   lo step 5 "Add state files before you need them"

NON toccare HowWeWorkInteractive.jsx in questo deploy (brief separato).

Committa: "feat(site): howwework v3 — state files + V&C section"
Push. Vercel re-deploya automaticamente.

Quando il deploy è live (~1-2 min), cancella drafts/2026-05-07_howwework_v3.md
(o spostalo in drafts/applied/2026-05/).
```
