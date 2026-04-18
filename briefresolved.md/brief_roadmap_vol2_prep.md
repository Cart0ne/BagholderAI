# INTERN BRIEF — Roadmap Update: Volume 2 prep task

**Scope:** Add a single future task to Phase 4 of the public roadmap, to remind us to batch-convert Volume 2 diaries from `.docx` to `.md` when publication is scheduled.

---

## File: `web/roadmap.html`

### Change 1 — Update `last_updated` date

Find the `last_updated` field inside the `ROADMAP` const.

Replace the current value with:

```
"2026-04-18"
```

### Change 2 — Add new task to Phase 4

Locate the phase object with `id: 4` (title `"Dashboard + Monetization"`).

At the **end of its `tasks` array** (right before the closing `]` of that phase's tasks, after the task `"Publish Volume 1"`), add this new entry:

```javascript
{ text: "Volume 2 prep: batch convert diaries S24→last + preface + interlude (S34) from .docx to .md", status: "todo", who: "AI", comment: "Trigger when Volume 2 publication is scheduled. One-shot script using mammoth (Python), output to diary/md/." },
```

Make sure the trailing comma is correct — add a comma after the previous task's closing `}` if the current last task doesn't already have one.

### Change 3 — Validate JS

After editing, run:

```bash
node -e "$(cat web/roadmap.html | sed -n '/const ROADMAP/,/};/p')"
```

Must exit cleanly with no parse errors.

---

## Commit message

```
docs: roadmap — Volume 2 prep task (docx→md conversion)
```

---

## Rules

- No external connections. No launching the bot.
- Push directly to `main`, no PR.
- Stop when done.
