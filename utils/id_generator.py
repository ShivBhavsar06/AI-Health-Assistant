"""Reusable VARCHAR(20) primary key generator. No AUTO_INCREMENT."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone

from sqlalchemy import select

from extensions import db

PREFIXES = {
    "user": "USR",
    "admin": "ADM",
    "medicine": "MED",
    "reminder": "REM",
    "appointment": "APP",
    "health_record": "HRC",
    "medical_report": "REP",
    "feedback": "FDB",
}

MAX_LENGTH = 20


def generate_id(prefix: str, model, pk_field: str) -> str:
    if len(prefix) > 5:
        prefix = prefix[:5]
    year = datetime.now(timezone.utc).strftime("%Y")
    stem = f"{prefix}{year}"
    column = getattr(model, pk_field)

    last = db.session.execute(
        select(model).where(column.like(f"{stem}%")).order_by(column.desc()).limit(1)
    ).scalar_one_or_none()

    next_number = 1
    if last:
        raw = getattr(last, pk_field)[len(stem) :]
        if raw.isdigit():
            next_number = int(raw) + 1
    candidate = f"{stem}{next_number:05d}"
    if len(candidate) > MAX_LENGTH:
        candidate = candidate[:MAX_LENGTH]
    if not db.session.get(model, candidate):
        return candidate

    for _ in range(30):
        suffix = secrets.randbelow(10**6)
        candidate = f"{stem}{suffix:06d}"[:MAX_LENGTH]
        if not db.session.get(model, candidate):
            return candidate

    return f"{prefix}{secrets.token_hex(6).upper()}"[:MAX_LENGTH]


def assign_new_id(instance, prefix: str, pk_field: str) -> str:
    current = getattr(instance, pk_field, None)
    if current:
        return current
    value = generate_id(prefix, instance.__class__, pk_field)
    setattr(instance, pk_field, value)
    return value
