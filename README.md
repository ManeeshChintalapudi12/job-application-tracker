# Job Application Tracker

A small full-stack app to track job applications — **one application per company, latest application wins.** I built it because I was applying to a lot of roles by email and job boards and losing track of who I had applied to, for what role, and what happened next. This replaces the spreadsheet.

![Status](https://img.shields.io/badge/status-working%20MVP-green) ![Stack](https://img.shields.io/badge/stack-FastAPI%20%2B%20vanilla%20JS-blue)

## What it does

- Add an application: company, role, date applied, status, notes
- List all applications, newest first, with a status filter
- Update an application as it moves: `Applied → Screening → Interview → Offer / Rejected / Withdrawn`
- Delete an application (e.g. a duplicate — the exact problem this project was built to prevent)
- See counts by status at `/stats` (total applications, how many are in interview, etc.)
- Interactive API docs automatically at `/docs` (Swagger UI, built into FastAPI)

## Tech stack

| Layer    | Choice                              | Why |
|----------|-------------------------------------|-----|
| Backend  | Python + FastAPI                    | Fast to build, automatic validation and API docs |
| Storage  | SQLite (Python standard library)    | Zero setup, real SQL, one file |
| Frontend | Single HTML page + vanilla JavaScript (`fetch`) | No build step — open it and it talks to the API |
| Tests    | pytest + FastAPI TestClient         | Real HTTP-level tests against a throwaway DB |

## Project structure

```
job-application-tracker/
├── backend/
│   ├── main.py            # FastAPI app: CRUD + /stats, SQLite storage
│   └── requirements.txt
├── frontend/
│   └── index.html         # List / add / delete UI, calls the API
├── tests/
│   └── test_api.py        # 4 tests: create/list, update/delete, validation, stats
└── README.md
```

## Setup & run

```bash
# 1. Backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8000
# API: http://localhost:8000   Docs: http://localhost:8000/docs

# 2. Frontend (in a second terminal)
python3 -m http.server 5500 --directory frontend
# Open http://localhost:5500
```

## API at a glance

| Method | Endpoint              | Description |
|--------|-----------------------|-------------|
| GET    | `/health`             | Health check |
| GET    | `/applications`       | List (optional `?status=` filter, `?q=` search) |
| POST   | `/applications`       | Create (201) |
| GET    | `/applications/{id}`  | Get one |
| PUT    | `/applications/{id}`  | Update any field |
| DELETE | `/applications/{id}`  | Delete (204) |
| GET    | `/stats`              | Total + counts by status |

Example:

```bash
curl -X POST http://localhost:8000/applications \
  -H "Content-Type: application/json" \
  -d '{"company":"Paystand","role":"Junior Fullstack Engineer","date_applied":"2026-11-19","status":"Applied"}'
```

## Tests

```bash
pytest -q
# 4 passed — create/list, update→delete flow, validation/404s, stats
```

## Screenshots

> _Placeholder — add after first run:_
> - [ ] Frontend list view with 5+ sample applications
> - [ ] Swagger docs page at `/docs`
> - [ ] `/stats` response showing counts by status

## What actually runs (honest status)

- ✅ Backend: fully working CRUD + stats, SQLite persistence, tested
- ✅ Frontend: working single-page UI — lists, adds, deletes, filters by status by calling the live API
- ❌ No login/auth, no deployment yet, no edit-in-place in the UI (status updates are via API/`/docs` for now)

## Roadmap

- [ ] Edit status directly from the frontend table
- [ ] Duplicate warning: flag when a company already has an active application
- [ ] Follow-up reminders (applied 7–10 days ago, no response)
- [ ] Import applications from a CSV
- [ ] Deploy (Render/Fly.io backend + static frontend) and add the live link here

## Author

Maneesh Chintalapudi — entry-level software / full-stack developer.
Built as a portfolio project during my job search — the tracker now tracks its own job search.
