# INTERN BRIEF — Session 29: Roadmap Update

## File: `web/roadmap.html`

### Change 1: Update last_updated date
Find the `last_updated` field in the ROADMAP const.
Replace the current date with: `"2026-04-10"`

### Change 2: Add Session 29 tasks to Phase 4

In the Phase 4 tasks array, add these new entries at the end (before the closing `]`):

```javascript
{ text: "Memory audit: purged 15 duplicate memory edits, established correction-only policy", status: "done", who: "AI", comment: "Session 29." },
{ text: "Discovered Anthropic docx→text conversion in project files, new diary workflow (template via chat)", status: "done", who: "BOTH", comment: "Session 29." },
{ text: "Roadmap workflow: HTML-only, killed routine docx generation", status: "done", who: "BOTH", comment: "Session 29." },
{ text: "Project instructions backup (BagHolderAI_Instructions_Backup.md)", status: "done", who: "AI", comment: "Session 29." },
```

### Change 3: Validate JS

After editing, validate:
```bash
node -e "$(cat web/roadmap.html | sed -n '/const ROADMAP/,/};/p')"
```

## Commit message

```
docs: S29 roadmap — memory audit, diary/roadmap workflow fixes
```

## Rules

No external connections. No launching the bot. Stop when done.
