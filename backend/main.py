"""Job Application Tracker — minimal FastAPI backend.

CRUD for job applications, stored in SQLite (standard library only
for storage; FastAPI + Pydantic for the HTTP layer).

Run:
    uvicorn backend.main:app --reload --port 8000
Docs: http://localhost:8000/docs
"""
from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from datetime import date
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

Status = Literal[
    "Applied", "Screening", "Interview", "Offer", "Rejected", "Withdrawn"
]

DEFAULT_DB = Path(__file__).with_name("applications.db")


def _valid_iso_date(value: str) -> str:
    """Reject malformed dates (e.g. 'tomorrow', '2026-13-40') at the API edge."""
    try:
        date.fromisoformat(value)
    except ValueError:
        raise ValueError("date_applied must be a valid ISO date, e.g. 2026-11-19")
    return value


# ---------- Schemas ----------
class ApplicationCreate(BaseModel):
    company: str = Field(..., min_length=1, max_length=120)
    role: str = Field(..., min_length=1, max_length=120)
    date_applied: str = Field(..., description="ISO date, e.g. 2026-11-19")
    status: Status = "Applied"
    notes: Optional[str] = Field(default="", max_length=1000)

    @field_validator("date_applied")
    @classmethod
    def check_date(cls, value: str) -> str:
        return _valid_iso_date(value)


class ApplicationUpdate(BaseModel):
    company: Optional[str] = Field(default=None, min_length=1, max_length=120)
    role: Optional[str] = Field(default=None, min_length=1, max_length=120)
    date_applied: Optional[str] = None
    status: Optional[Status] = None
    notes: Optional[str] = Field(default=None, max_length=1000)

    @field_validator("date_applied")
    @classmethod
    def check_date(cls, value: Optional[str]) -> Optional[str]:
        return None if value is None else _valid_iso_date(value)


class ApplicationOut(ApplicationCreate):
    id: int


# ---------- Storage ----------
def init_db(db_path: Path) -> None:
    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL,
                role TEXT NOT NULL,
                date_applied TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Applied',
                notes TEXT DEFAULT ''
            )
            """
        )
        conn.commit()


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "company": row["company"],
        "role": row["role"],
        "date_applied": row["date_applied"],
        "status": row["status"],
        "notes": row["notes"] or "",
    }


# ---------- App factory (so tests can use a temp DB) ----------
def create_app(db_path: Path | str | None = None) -> FastAPI:
    path = Path(db_path) if db_path else Path(os.getenv("JOB_TRACKER_DB", DEFAULT_DB))
    init_db(path)

    app = FastAPI(title="Job Application Tracker", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # local development only
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def connect() -> sqlite3.Connection:
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return conn

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/applications", response_model=list[ApplicationOut])
    def list_applications(
        status: Optional[Status] = None,
        q: Optional[str] = Query(default=None, description="Search company/role"),
    ) -> list[dict]:
        sql = "SELECT * FROM applications WHERE 1=1"
        params: list = []
        if status:
            sql += " AND status = ?"
            params.append(status)
        if q:
            sql += " AND (company LIKE ? OR role LIKE ?)"
            params += [f"%{q}%", f"%{q}%"]
        sql += " ORDER BY date_applied DESC, id DESC"
        with closing(connect()) as conn:
            return [_row_to_dict(r) for r in conn.execute(sql, params)]

    @app.post("/applications", response_model=ApplicationOut, status_code=201)
    def create_application(payload: ApplicationCreate) -> dict:
        with closing(connect()) as conn:
            cur = conn.execute(
                "INSERT INTO applications (company, role, date_applied, status, notes)"
                " VALUES (?, ?, ?, ?, ?)",
                (payload.company, payload.role, payload.date_applied,
                 payload.status, payload.notes or ""),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM applications WHERE id = ?", (cur.lastrowid,)
            ).fetchone()
        return _row_to_dict(row)

    @app.get("/applications/{app_id}", response_model=ApplicationOut)
    def get_application(app_id: int) -> dict:
        with closing(connect()) as conn:
            row = conn.execute(
                "SELECT * FROM applications WHERE id = ?", (app_id,)
            ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Application not found")
        return _row_to_dict(row)

    @app.put("/applications/{app_id}", response_model=ApplicationOut)
    def update_application(app_id: int, payload: ApplicationUpdate) -> dict:
        updates = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not updates:
            return get_application(app_id)
        set_sql = ", ".join(f"{k} = ?" for k in updates)
        with closing(connect()) as conn:
            cur = conn.execute(
                f"UPDATE applications SET {set_sql} WHERE id = ?",
                (*updates.values(), app_id),
            )
            conn.commit()
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Application not found")
            row = conn.execute(
                "SELECT * FROM applications WHERE id = ?", (app_id,)
            ).fetchone()
        return _row_to_dict(row)

    @app.delete("/applications/{app_id}", status_code=204)
    def delete_application(app_id: int) -> None:
        with closing(connect()) as conn:
            cur = conn.execute("DELETE FROM applications WHERE id = ?", (app_id,))
            conn.commit()
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Application not found")
        return None

    @app.get("/stats")
    def stats() -> dict:
        with closing(connect()) as conn:
            rows = conn.execute(
                "SELECT status, COUNT(*) AS n FROM applications GROUP BY status"
            ).fetchall()
            total = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
        return {"total": total, "by_status": {r["status"]: r["n"] for r in rows}}

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
