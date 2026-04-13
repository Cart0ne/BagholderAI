# INTERN BRIEF — Session 18b (Admin Dashboard Update)

**Priority: MEDIUM (do after Session 18 main brief is complete)**
**Date: April 3, 2026**

---

## Context

The admin dashboard (`admin.html`) already reads and writes to `bot_config` in Supabase. Three new columns were added today: `buy_pct`, `sell_pct`, and `grid_mode`. The dashboard needs to display and allow editing of these new fields.

---

## Task — Add New Fields to Admin Dashboard

### What to add per coin card:

1. **Grid Mode** — display current value (`fixed` or `percentage`). Editable as a dropdown/toggle.
2. **Buy %** (`buy_pct`) — display current value. Editable input field, same style as existing parameter inputs.
3. **Sell %** (`sell_pct`) — display current value. Editable input field, same style as existing parameter inputs.

### Where to place them

In each coin's parameter section, **above** the old grid parameters (grid_lower, grid_upper, grid_levels). Visually group them together, maybe with a subtle label like "Percentage Grid" to distinguish from the legacy fixed grid fields.

### Behavior

- Read from `bot_config` table (same as other fields)
- Write to `bot_config` table on edit (same as other fields)
- Log changes to `config_changes_log` table (same as other fields — use `changed_by: 'manual-ceo'`)
- When `grid_mode = 'percentage'`, visually de-emphasize the old fixed grid fields (lower opacity or grey out) to signal they're not active. Don't hide them — Max still wants to see them.

### Style

Same dark aesthetic, same mobile-first layout, same input style. Nothing new to invent — just extend what's already there.

---

## Scope Rules

- No external connections
- Do NOT launch the bot
- Push to GitHub when done
- Stop when complete

## Files involved

- `web/admin.html` — the only file to modify
