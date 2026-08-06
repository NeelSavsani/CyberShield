"""Authenticated scan queue, history, and account endpoints."""

from __future__ import annotations

import asyncio
import sqlite3
import sys
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.orchestrator import analyze_url
from app.services.auth import create_access_token, hash_password, optional_user_id, verify_password
from app.services.database import complete_scan, create_scan, create_user, fail_scan, find_user_by_email, get_scan, list_scans
from app.services.rate_limit import enforce_rate_limit


router = APIRouter(prefix="/api", tags=["Platform"])


class Credentials(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=12, max_length=128)


class ScanRequest(BaseModel):
    url: str = Field(min_length=4, max_length=2048)


def _run_scan_sync(scan_id: str, url: str) -> None:
    """Run browser-capable analysis on a Proactor loop on Windows.

    Uvicorn's reload mode uses a Selector loop on Windows, which cannot launch
    Playwright subprocesses. A dedicated worker thread avoids that limitation
    while keeping the API responsive.
    """
    loop = None
    try:
        if sys.platform == "win32":
            from asyncio.windows_events import ProactorEventLoop
            loop = ProactorEventLoop()
        else:
            loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(analyze_url(url))
        complete_scan(scan_id, result.model_dump(mode="json"))
    except Exception as error:
        fail_scan(scan_id, str(error))
    finally:
        if loop:
            loop.close()


async def _run_scan(scan_id: str, url: str) -> None:
    await asyncio.to_thread(_run_scan_sync, scan_id, url)


@router.post("/auth/register", status_code=201)
async def register(credentials: Credentials):
    user_id = str(uuid4())
    try:
        user = create_user(user_id, credentials.email, hash_password(credentials.password))
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    return {"user": user, "access_token": create_access_token(user_id, user["email"]), "token_type": "bearer"}


@router.post("/auth/login")
async def login(credentials: Credentials):
    user = find_user_by_email(credentials.email)
    if not user or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    return {"user": {"id": user["id"], "email": user["email"], "created_at": user["created_at"]}, "access_token": create_access_token(user["id"], user["email"]), "token_type": "bearer"}


@router.post("/scans", status_code=202)
async def submit_scan(request: Request, scan_request: ScanRequest):
    enforce_rate_limit(request.client.host if request.client else "unknown")
    user_id = optional_user_id(request)
    scan_id = str(uuid4())
    scan = create_scan(scan_id, scan_request.url, user_id)
    asyncio.create_task(_run_scan(scan_id, scan_request.url))
    return {"scan": scan, "poll_url": f"/api/scans/{scan_id}"}


@router.get("/scans")
async def scan_history(request: Request):
    return {"scans": list_scans(optional_user_id(request))}


@router.get("/scans/{scan_id}")
async def scan_status(scan_id: str, request: Request):
    scan = get_scan(scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found.")
    user_id = optional_user_id(request)
    if scan["user_id"] and scan["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="You do not have access to this scan.")
    return {"scan": scan}
