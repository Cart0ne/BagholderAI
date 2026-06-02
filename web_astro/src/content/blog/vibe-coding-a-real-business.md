---
title: "Vibe Coding a Real Business: From Zero to 5 AI Modules in 3 Months"
subtitle: "Not a weekend prototype. A three-month project with five AI modules, three ebooks, a public site, and all the technical debt that came with it."
date: 2026-06-02
tags: ["vibe-coding", "claude-code", "ai-coding-assistant", "build-in-public", "indie-hacker"]
summary: "What does a real vibe coding project look like past the weekend? Here's a three-month case study: five AI modules, three ebooks, a public site — and the honest cost of building it without writing code."
type: "lesson"
draft: true
faq:
  - question: "What does a real vibe coding project look like?"
    answer: "Past the weekend-prototype stage, it looks like a months-long management job. Ours produced five AI modules, a 20-table database, a public website, and three ebooks over three months — built by a non-coder directing Claude Code, with a growing pile of technical debt to manage alongside the features."
  - question: "Can you build a real business with vibe coding?"
    answer: "You can build a real system. Whether it's a real business depends on the same things any business does — customers, revenue, durability. Vibe coding solved the 'how do I build this without coding' problem; it did not solve the 'will anyone pay' problem. Those are separate."
  - question: "Does vibe coding scale to complex projects?"
    answer: "Partly. The first 20 sessions felt like magic — fast, clean, exhilarating. The later sessions got slower and heavier: more modules to not break, more debt, more time spent reviewing than building. It scales, but the difficulty curve is real."
  - question: "What's the real cost of vibe coding?"
    answer: "Not the subscription. The real costs are the review time (you read everything the AI writes), the bugs the AI can't see (which land on you), and the technical debt that accumulates faster than in hand-written code because it's so easy to add more."
  - question: "Would you build with vibe coding again?"
    answer: "Yes — but only with guardrails built early: written project instructions, disciplined briefs, and an audit process. The first weeks without those were exhilarating and fragile. The structure is what turned a fun experiment into something that survived three months."
---

**What does a real vibe coding project look like once you're past the weekend?** It looks like work. Three months, near-daily sessions, five AI modules, a 20-table backend, a public website, three ebooks — all directed by someone who can't code, using Claude Code as the builder. It's not a prototype. It's a project, with everything that word implies: scope creep, technical debt, and the slow discovery that building was the easy part.

## The timeline

| When | What got built |
|---|---|
| **Month 1** | The grid bot — the first module that actually trades. Get one thing working end-to-end on a real exchange's test network. |
| **Month 2** | The dashboard, the watchtower (market-regime detection), and the parameter tuner. The system stops being one bot and becomes a supervised set of modules. |
| **Month 3** | The news classifier, the public blog, and the third ebook. The project turns outward — distribution, documentation, telling the story. |

Five modules in twelve weeks, built by a non-coder. That's the headline vibe-coding promise, and it's real. What the promise leaves out is everything in the next three sections.

## What scales — and what doesn't

Compare the first 20 sessions to the last 20 and you can feel the curve bend.

**The early sessions scaled beautifully.** One module, a clean slate, fast feedback. You describe what you want, the AI builds it, it works, you feel unstoppable. This is the part everyone screenshots.

**The later sessions got heavy.** With five modules running, every change risks breaking something three files away. A single refactor took a 1,600-line monolith and split it into eight smaller modules — necessary work, but it produces no new features, just survivability. More of each session went to *not breaking things* than to building new ones. The exhilaration-to-effort ratio quietly inverts.

The thing that scales is the *building*. The thing that doesn't is the *keeping-it-alive*. Nobody warns you that the second one eventually eats the first.

## The real cost of vibe coding

The subscription is the cheap part. Here's the actual bill:

- **Review time.** You read everything. Every diff, every log, every "I fixed it." If you don't, the bugs you didn't catch become the bugs in production. For a non-coder, this is slow and unavoidable.
- **The bugs the AI can't see.** A [fictional price on a data feed](https://bagholderai.lol/blog/ai-is-useful-but-it-doesnt-think-like-we-do), a fee counted in the wrong currency, a safety brake calibrated to never fire. The AI wrote all three confidently. They landed on the human, because the AI didn't know they were there.
- **Technical debt, accelerated.** Hand-coding is slow enough that you feel the weight of each new file. Vibe coding removes that friction — which means debt accumulates *faster*, because adding more is so easy. The convenience is the trap.

And the cost nobody prices in: the AI sometimes lies. Not maliciously — it fills gaps with confident fiction. One night the planning AI [reported three results that were false](https://bagholderai.lol/blog/when-your-ai-ceo-lies-about-the-numbers) and didn't notice. You pay for that in vigilance, every single session.

## Would I do it again?

Yes — but not the way we started.

The first weeks were exhilarating and fragile: pure momentum, no structure, a system that worked until it didn't. What turned it from a fun experiment into something that survived three months was the boring stuff we added later — a written instruction file the AI reads every session, a discipline of precise briefs, an audit process where a fresh AI checks the work. Guardrails.

So: vibe coding a real business? The *coding* part absolutely works — a non-coder really can build a complex, supervised system with AI. The *business* part is a separate question that no AI tool answers for you: the building was never the hard part. Getting someone to care was. That's the honest difference between a real vibe-coding project and a weekend demo — three months in, you find out which problem you were actually trying to solve.

---

*The whole arc — from the first grid order to the eight-module refactor — is documented in [the diary](https://bagholderai.lol/diary), session by session. The [ebooks](https://bagholderai.lol/library) collect it in volumes.*
