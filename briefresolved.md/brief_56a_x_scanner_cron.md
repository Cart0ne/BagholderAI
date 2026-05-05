# BRIEF 56a — X Scanner Weekly Cron

**From:** CEO (Claude, Projects)  
**To:** CC (Claude Code, Intern)  
**Session:** 56 — May 4, 2026  
**Priority:** MEDIUM — no trading impact, marketing infrastructure

---

## Objective

Transform the existing X scanner script (manual, on-demand) into a **weekly cron job** on Mac Mini. The scanner already works — this brief only automates the scheduling and adds a Telegram notification.

---

## What Exists Today

- A Python script that:
  - Authenticates via OAuth 2.0 Bearer Token (app-only, read access)
  - Downloads posts from @BagHolderAI timeline
  - Only fetches **new posts** since last run (incremental)
  - Generates a `.md` report with impressions, engagement, clicks
  - Costs ~$0.04 per scan (X API pay-per-use)
- The script lives in the repo and runs manually when Max remembers to launch it

**CC:** Find the existing scanner script in the repo. If you're unsure which file it is, check `memory.md` or search for files referencing `Bearer` token + X/Twitter API + user timeline.

---

## What To Build

### 1. Shell wrapper script

Create `scripts/x_scanner_cron.sh` in the repo:

```bash
#!/bin/bash
# X Scanner Weekly Cron — BagHolderAI
# Runs every Monday at 08:00 CET

cd /Volumes/Archivio/bagholderai
source venv/bin/activate

# Run the scanner (adjust path/command to match existing script)
python3.13 <path_to_scanner_script> 2>&1 | tee -a logs/x_scanner_cron.log

# Log timestamp
echo "--- Scan completed at $(date) ---" >> logs/x_scanner_cron.log
```

- Create `logs/` directory if it doesn't exist
- Make the script executable: `chmod +x scripts/x_scanner_cron.sh`

### 2. Cron entry on Mac Mini

Add to Max's crontab (`crontab -e`):

```
0 8 * * 1 /Volumes/Archivio/bagholderai/scripts/x_scanner_cron.sh
```

This runs every Monday at 08:00. Mac Mini timezone should be CET (verify with `date`).

**Edge case:** if Mac Mini is asleep/off at 08:00, the cron won't fire. This is acceptable — the scan runs the next Monday. No retry logic needed.

### 3. Telegram notification (optional but recommended)

After the scan completes, send a summary to the **private** Telegram bot (Max's bot, NOT the public channel). The Telegram send function already exists in the codebase (used by Haiku daily commentary).

Message format:
```
📊 X Scanner Weekly Report
Posts scanned: [N new]
Top post: [title/excerpt] — [impressions] impressions
Report saved: x_scan_[date].md
```

Keep it short — Max just needs to know it ran and what the highlight was.

### 4. Git ignore for logs

Add to `.gitignore` if not already present:
```
logs/
```

---

## What NOT To Do

- **Do NOT modify the scanner logic** — it works, don't touch it
- **Do NOT change the authentication method** — OAuth 2.0 Bearer stays
- **Do NOT set up retries or complex error handling** — if it fails, it logs and we check next week
- **Do NOT scan anything other than our own posts** — sentiment scanning for coins is a future task (Sentinel Layer 2), not this brief

---

## Test Checklist

1. [ ] Run `scripts/x_scanner_cron.sh` manually on Mac Mini — does it produce a report?
2. [ ] Check `logs/x_scanner_cron.log` — is there a timestamp entry?
3. [ ] Check Telegram — did the summary arrive on Max's private bot?
4. [ ] Verify cron is installed: `crontab -l` shows the Monday 08:00 entry
5. [ ] Verify the `.md` report only has NEW posts (not re-downloading old ones)

---

## Execution

1. `git pull` on Mac Mini
2. Find existing scanner script, note exact path
3. Create wrapper shell script
4. Test wrapper manually
5. Add Telegram notification
6. Test again
7. Install cron entry
8. `git add . && git commit -m "feat: x scanner weekly cron (brief 56a)" && git push`
