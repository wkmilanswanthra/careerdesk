# CareerDesk

A standalone, offline Windows application for managing your job search.

## Run

This repository contains source code only. Follow the build instructions below to generate **CareerDesk.exe**, then double-click the executable to run it. The built application requires no Python installation, account, or internet connection. Windows may show a SmartScreen prompt because locally built executables are unsigned.

## What you can do

- Track jobs from Saved through Applied, Screening, Interview, Offer, Accepted, Rejected, or Withdrawn.
- Store company, job title, location, work arrangement, salary/currency, job link, contact, dates, and multiline notes.
- Review pipeline counts, due follow-ups, interviews, and applications arranged by company.
- Search all application fields, filter by stage, and sort by clicking a column heading.
- Log calls, emails, and other updates in each application's activity history. Creation and status changes are recorded automatically.
- Export/import CSV files, create complete database backups, and restore backups with an automatic safety copy of your previous data.

Dates use `YYYY-MM-DD`. Interview times, time zones, meeting links, and preparation details belong in notes. Amber rows indicate follow-ups due today or overdue. Follow-ups are visible in the app; there are no background notifications when it is closed. Clear or reschedule the follow-up date after completing it.

Double-click a row to edit it. **Ctrl+N** creates a new application, **Ctrl+F** focuses search, and **Ctrl+S** saves an open application form. Unsaved form changes trigger a confirmation before closing.

## Your data

The database is stored in `%LOCALAPPDATA%\CareerDesk\careers.db`, separately from the executable. Use **Data & backups → Open data folder** to locate it. Updates to the executable preserve your records. Back up regularly to a separate drive or your preferred backup folder.

CSV exports include application fields but not activity history. Complete `.db` backups include both. CSV imports add records and do not deduplicate. A malformed CSV is rejected before any rows are added. Exported values that could be interpreted as spreadsheet formulas are escaped; CareerDesk removes this escape on import.

No records are preloaded. No analytics, telemetry, cloud storage, or subscription is used. The app opens your default browser only when you click a job link. The local database is not encrypted; your Windows account and device security protect it.

## Build from source

Requires Python 3.12+ with Tk support on Windows:

```powershell
python -m pip install -r requirements-build.txt
python -m unittest discover -s tests -p "test_*.py"
python tests/smoke_ui.py
python -m PyInstaller --noconfirm --clean --onefile --windowed --name CareerDesk --icon assets/careerdesk.ico src/app.py
```

The standalone executable is generated at `dist/CareerDesk.exe`.
