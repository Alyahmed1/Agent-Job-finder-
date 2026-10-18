# Willy's Job Finder

A free, local job-finding agent. Every morning it collects jobs, ranks them against your profile, and shows the best ones in a small dashboard.

- **Free.** No paid APIs. Scoring is rule-based; the optional cover-note writer uses a local [Ollama](https://ollama.com) model.
- **LinkedIn-safe.** It never logs in to or scrapes LinkedIn. It reads the job-alert emails LinkedIn sends you, through read-only Gmail access.
- **Remote jobs** come from free public feeds: Remotive, Remote OK, We Work Remotely, Jobicy, Himalayas, Working Nomads. Every card links back to the site it came from.
- **You stay in control.** Apply opens the job page. Nothing is ever sent for you.

## What you get

| Tab | Jobs |
|---|---|
| Egypt | On-site and hybrid jobs in Egypt, ranked first |
| Remote | Remote jobs you can do from anywhere |
| Relocation | Jobs abroad (Canada, UAE, Saudi Arabia, Europe) |
| Saved / Applied / Not interested | Your own lists, with Restore and Undo |

Each job shows a score and why (for example `Tier 1: AI / ML / GenAI +70`, `Egypt +10`, `senior role -10`). The agent also learns from what you hide, save and apply to, and can draft a short cover note (only when you press the button, and only kept if you press Save note).

## Setup (Windows)

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
copy profile.example.yaml profile.yaml     # then put your name and gmail in profile.yaml (it stays private)
```

1. **LinkedIn alerts.** Create daily job alerts on LinkedIn for your roles and places, sent to your Gmail.
2. **Gmail access (read-only).** In Google Cloud: create a project, enable the Gmail API, create an OAuth *Desktop app* client, and save it as `credentials.json` in this folder. Add your Gmail as a test user.
3. **First login.** Run `login_gmail.bat` once and allow read-only access. (While the Google app is in "Testing" the login expires about weekly; run it again when the dashboard says so.)
4. **Run it.**
   ```powershell
   .venv\Scripts\python run_daily.py        # collect + score
   open_dashboard.bat                       # open the dashboard
   ```
5. **Automatic daily run (optional).** `install_windows_task.ps1` creates a 7:00 AM task and a Desktop shortcut. The dashboard also refreshes itself on open if its list is older than `auto_refresh_hours`.

`credentials.json`, `token.json`, `jobs.db`, `profile.yaml`, `settings.json`, `samples/` and `logs/` are git-ignored on purpose. Never commit them.

## Tests

```powershell
.venv\Scripts\python -m pytest -q
```

## Layout

| File | Job |
|---|---|
| `collect/` | Gmail reader, LinkedIn email parser, remote-job feeds |
| `pipeline.py` | One refresh: LinkedIn + feeds, scored and saved once |
| `score.py`, `learn.py`, `classify.py` | Ranking rules, learning from clicks, Egypt/Remote/Relocation tabs |
| `cover.py` | Optional cover-note draft with a local model |
| `app.py`, `ui.py`, `stats.py` | The Streamlit dashboard, its themes and numbers |
| `db.py`, `settings.py` | SQLite store and small settings |
| `scheduled_run.py`, `install_windows_task.ps1` | The daily 7:00 AM run |

## Notes

- Tab detection uses an Egypt city list in `classify.py`; edit it for another home country.
- Remote feed terms: each source asks to be credited with a link back, which the cards do. Remotive asks for at most about 4 requests a day; cooldowns are in `profile.yaml`.
