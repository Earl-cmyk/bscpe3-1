# Deadline Tracker

A responsive Flask + SQLite deadline planner with a bento-style calendar workspace, task search, local attachments, and a natural-language planner chat.

## Run on Windows

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

Open `http://127.0.0.1:5000`.

## Pages and announcements

- `/` is the dark dashboard with recent announcements, current class-fund balance, and the next three deadlines.
- `/tasks` is the dedicated task calendar.
- `/budget` is the dedicated class-fund ledger.
- `/announcements` is the announcement history and poll results page.

Announcements require the configured PIN. Posts can include a title, message,
HTTP(S) link, attachment, and optional poll options. Voting requires a School
ID listed on its own line in `valid_school_ids.txt`; the database prevents the
same School ID from voting twice on one poll.

The app currently uses SQLite and local uploads. This is suitable for local
hosting, but Vercel serverless storage is not durable across instances or
deployments. Use hosted database and object storage services for production
persistence on Vercel.

The calendar and class fund workspaces are full-width panels that stay centered
within the page shell. Frontend code is in `app/templates/index.html`,
`app/static/css/style.css`, and `app/static/js/main.js`.

## Features

- Month, week, and day calendar views with UTC deadline times.
- PIN-protected task creation. The current PIN is `313131`.
- Courses: HDL, LCD, DDC, CEDD, FOSS, TRW, Elec, and Engr Econ.
- Task detail, edit, completion, and deletion controls.
- Search across title, description, and course.
- Image previews and local document downloads from `app/static/uploads`.
- Planner queries: `deadlines today`, `deadlines this week`, `deadlines this month`, `to do for HDL today`, `to do for FOSS on 2026-09-15`, and date ranges.

## Data and API

SQLite is stored at `instance/deadlines.db`. On startup, existing rows from the original `deadlines` table are copied into the new `tasks` table once. Existing titles, notes, due dates, and completion state are preserved.

The JSON API includes:

- `GET /api/tasks?search=term`
- `POST /api/tasks` with multipart form data and `pin`
- `GET /api/tasks/<id>`
- `PATCH /api/tasks/<id>`
- `DELETE /api/tasks/<id>`
- `GET /api/query?q=deadlines%20this%20week`
- `GET /uploads/<stored-filename>`

Uploaded files are assigned generated storage names and are limited to 16 MB. The upload directory is local to this application and should be protected appropriately in production.
