"""Small SQLite persistence layer for users and scan reports."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import os

from app.config import settings


def _connection() -> sqlite3.Connection:
    path: Path = settings.database_path
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    with _connection() as connection:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS scans (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                submitted_url TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                result_json TEXT,
                error TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS screenshot_assets (
                asset_id TEXT PRIMARY KEY,
                request_id TEXT,
                object_ref TEXT NOT NULL,
                hash TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                dimensions TEXT NOT NULL,
                ocr_confidence INTEGER,
                retention_expiry TEXT NOT NULL
            );
        """)
    purge_expired_screenshot_assets()


def create_screenshot_asset(
    asset_id: str,
    request_id: str | None,
    object_ref: str,
    sha256: str,
    file_size: int,
    dimensions: str,
    ocr_confidence: int | None,
    retention_expiry: str,
) -> None:
    with _connection() as connection:
        connection.execute(
            """INSERT INTO screenshot_assets
            (asset_id, request_id, object_ref, hash, file_size, dimensions, ocr_confidence, retention_expiry)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (asset_id, request_id, object_ref, sha256, file_size, dimensions, ocr_confidence, retention_expiry),
        )


def purge_expired_screenshot_assets() -> None:
    """Delete expired re-encoded screenshot files and their database records."""
    now = datetime.now(timezone.utc).isoformat()
    with _connection() as connection:
        rows = connection.execute(
            "SELECT asset_id, object_ref FROM screenshot_assets WHERE retention_expiry <= ?", (now,)
        ).fetchall()
        for row in rows:
            # object_ref is generated internally as a relative path only.
            path = Path(row["object_ref"])
            if path.is_file():
                try:
                    os.remove(path)
                except OSError:
                    pass
        connection.execute("DELETE FROM screenshot_assets WHERE retention_expiry <= ?", (now,))


def create_user(user_id: str, email: str, password_hash: str) -> dict[str, Any]:
    created_at = datetime.now(timezone.utc).isoformat()
    with _connection() as connection:
        connection.execute(
            "INSERT INTO users (id, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (user_id, email.lower(), password_hash, created_at),
        )
    return {"id": user_id, "email": email.lower(), "created_at": created_at}


def find_user_by_email(email: str) -> dict[str, Any] | None:
    with _connection() as connection:
        row = connection.execute("SELECT * FROM users WHERE email = ?", (email.lower(),)).fetchone()
    return dict(row) if row else None


def create_scan(scan_id: str, submitted_url: str, user_id: str | None) -> dict[str, Any]:
    created_at = datetime.now(timezone.utc).isoformat()
    with _connection() as connection:
        connection.execute(
            "INSERT INTO scans (id, user_id, submitted_url, status, created_at) VALUES (?, ?, ?, 'queued', ?)",
            (scan_id, user_id, submitted_url, created_at),
        )
    return get_scan(scan_id) or {}


def complete_scan(scan_id: str, result: dict[str, Any]) -> None:
    with _connection() as connection:
        connection.execute(
            "UPDATE scans SET status = 'completed', completed_at = ?, result_json = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), json.dumps(result), scan_id),
        )


def fail_scan(scan_id: str, error: str) -> None:
    with _connection() as connection:
        connection.execute(
            "UPDATE scans SET status = 'failed', completed_at = ?, error = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), error, scan_id),
        )


def get_scan(scan_id: str) -> dict[str, Any] | None:
    with _connection() as connection:
        row = connection.execute("SELECT * FROM scans WHERE id = ?", (scan_id,)).fetchone()
    if not row:
        return None
    scan = dict(row)
    scan["result"] = json.loads(scan.pop("result_json")) if scan.get("result_json") else None
    return scan


def list_scans(user_id: str | None, limit: int = 20) -> list[dict[str, Any]]:
    with _connection() as connection:
        if user_id:
            rows = connection.execute(
                "SELECT * FROM scans WHERE user_id = ? ORDER BY created_at DESC LIMIT ?", (user_id, limit)
            ).fetchall()
        else:
            rows = connection.execute("SELECT * FROM scans ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return [
        {**dict(row), "result": json.loads(row["result_json"]) if row["result_json"] else None, "result_json": None}
        for row in rows
    ]
