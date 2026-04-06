# INTERN BRIEF — Session 18c (Config Change Telegram Alert)

**Priority: HIGH**
**Date: April 3, 2026**

---

## Task — Telegram Notification on Config Change Detection

### Context

The config reader (`config/supabase_config.py`) already detects and logs changes every 300 seconds. We want a Telegram message on the **private bot** (not the public channel) whenever a config change is detected.

### Behavior

When the config refresh loop detects a changed value, send a Telegram message to the private chat:

```
⚙️ CONFIG UPDATED — BTC/USDT
Parameter: buy_pct
Old: 1.80
New: 2.00
Source: dashboard
```

- One message per changed parameter (if 3 fields change at once → 3 messages)
- Send to **private bot only** (the one Max uses), NOT to the public channel
- Use the existing Telegram notifier already in the codebase
- If Telegram send fails, log warning but don't crash

### Scope

- Modify `config/supabase_config.py` (or wherever the refresh loop detects changes)
- Import and use the existing Telegram notification function
- Do NOT launch the bot
- Push to GitHub when done
