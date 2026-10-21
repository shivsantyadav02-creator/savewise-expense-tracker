"""
services/udhar_service.py — Udhar (Money Lent / Borrowed) Tracker

Design rules:
- Udhar records are completely isolated from incomes, expenses, balance, and charts.
- All money stored in paise using existing helpers.
- Dates validated as YYYY-MM-DD with calendar-strict parsing.
- utils/clock.py used for "today" so tests can control the date without sleeping.
- Every function takes user_id first.
- Parameterized SQL only; no string interpolation.
"""

import re
from datetime import datetime
from database.db import get_db
from utils.clock import now_utc, to_local_date, today_local
from utils.helpers import inr_to_paise, paise_to_inr

VALID_STATUSES = {"pending", "settled", "all"}
VALID_TYPES = {"lent", "borrowed"}
DATE_REGEX = re.compile(r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$")


def _validate_date(date_str: str) -> str:
    """
    Validates and returns a strict YYYY-MM-DD date string.
    Rejects non-existent dates (e.g. 2026-02-30) by actually parsing with datetime.
    Raises ValueError on any invalid input.
    """
    if not date_str or not isinstance(date_str, str):
        raise ValueError("Date must be a string in 'YYYY-MM-DD' format.")
    clean = date_str.strip()
    if not DATE_REGEX.match(clean):
        raise ValueError(f"Invalid date '{date_str}'. Expected format is 'YYYY-MM-DD'.")
    # Strict calendar check: rejects e.g. 2026-02-30
    try:
        datetime.strptime(clean, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"Invalid calendar date '{date_str}' (e.g. day out of range for month).")
    return clean


def _today_date() -> str:
    """Returns today's local date as YYYY-MM-DD in APP_TIMEZONE, using clock helper."""
    return to_local_date(now_utc()).isoformat()


def _format_udhar_row(row, today: str = None) -> dict:
    """Converts a sqlite3.Row to a dict with computed is_overdue."""
    if row is None:
        return None
    data = dict(row)
    data["amount_inr"] = paise_to_inr(data["amount_paise"])

    today_str = today if today is not None else _today_date()
    due = data.get("due_date")
    is_pending = (data["is_settled"] == 0)

    # Overdue: only pending items where due_date exists and is strictly BEFORE today
    if is_pending and due and due < today_str:
        data["is_overdue"] = True
    else:
        data["is_overdue"] = False

    return data


def create_udhar(
    user_id: int,
    person_name: str,
    amount_inr,
    udhar_type: str,
    due_date: str = None,
    note: str = None
) -> dict:
    """
    Creates a new udhar record.

    Validations:
    - user_id must be a positive integer
    - person_name: required, max 40 chars
    - amount_inr: > 0
    - udhar_type: 'lent' | 'borrowed'
    - due_date: optional YYYY-MM-DD, calendar-strict
    - note: optional, max 200 chars
    """
    if not user_id or not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user_id is required.")

    if not person_name or not isinstance(person_name, str) or not person_name.strip():
        raise ValueError("Person name is required and cannot be empty.")
    clean_name = person_name.strip()
    if len(clean_name) > 40:
        raise ValueError("Person name cannot exceed 40 characters.")

    amount_paise = inr_to_paise(amount_inr)

    if not udhar_type or not isinstance(udhar_type, str) or udhar_type.strip().lower() not in VALID_TYPES:
        raise ValueError("Type must be 'lent' or 'borrowed'.")
    clean_type = udhar_type.strip().lower()

    clean_due = None
    if due_date is not None and str(due_date).strip():
        clean_due = _validate_date(str(due_date))

    clean_note = None
    if note is not None and isinstance(note, str) and note.strip():
        clean_note = note.strip()[:200]

    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        """
        INSERT INTO udhar_records (user_id, person_name, amount_paise, type, due_date, note, is_settled)
        VALUES (?, ?, ?, ?, ?, ?, 0)
        """,
        (user_id, clean_name, amount_paise, clean_type, clean_due, clean_note)
    )
    db.commit()
    new_id = cursor.lastrowid
    return get_udhar_by_id(user_id, new_id)


def get_udhar_by_id(user_id: int, record_id: int) -> dict:
    """Returns a single udhar record belonging to user, or None if not found."""
    if not user_id or not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user_id is required.")
    if not record_id or not isinstance(record_id, int) or record_id <= 0:
        raise ValueError("A valid record_id is required.")

    db = get_db()
    row = db.execute(
        """
        SELECT * FROM udhar_records
        WHERE id = ? AND user_id = ?
        """,
        (record_id, user_id)
    ).fetchone()
    if row is None:
        return None
    return _format_udhar_row(row)


def get_udhar_list(
    user_id: int,
    status: str = "pending",
    udhar_type: str = None
) -> list:
    """
    Returns udhar records for a user.

    status: 'pending' | 'settled' | 'all' (default 'pending')
    udhar_type: optional filter 'lent' | 'borrowed'
    Each record includes is_overdue.
    """
    if not user_id or not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user_id is required.")

    clean_status = status.strip().lower() if status else "pending"
    if clean_status not in VALID_STATUSES:
        raise ValueError("Invalid status filter. Must be 'pending', 'settled', or 'all'.")

    clean_type = None
    if udhar_type is not None and str(udhar_type).strip():
        t = str(udhar_type).strip().lower()
        if t not in VALID_TYPES:
            raise ValueError("Invalid type filter. Must be 'lent' or 'borrowed'.")
        clean_type = t

    db = get_db()
    params = [user_id]

    where_clauses = ["user_id = ?"]
    if clean_status == "pending":
        where_clauses.append("is_settled = 0")
    elif clean_status == "settled":
        where_clauses.append("is_settled = 1")

    if clean_type:
        where_clauses.append("type = ?")
        params.append(clean_type)

    where_sql = " AND ".join(where_clauses)
    rows = db.execute(
        f"SELECT * FROM udhar_records WHERE {where_sql} ORDER BY created_at DESC, id DESC",
        params
    ).fetchall()

    today = _today_date()
    return [_format_udhar_row(r, today) for r in rows]


def update_udhar(
    user_id: int,
    record_id: int,
    person_name: str = None,
    amount_inr=None,
    due_date: str = None,
    note: str = None
) -> dict:
    """
    Updates editable fields of an udhar record.
    Type cannot be changed.
    Can edit both pending and settled records (allows correcting data).
    Returns 404-style None if record not found.
    """
    existing = get_udhar_by_id(user_id, record_id)
    if existing is None:
        return None

    clean_name = existing["person_name"]
    if person_name is not None:
        if not isinstance(person_name, str) or not person_name.strip():
            raise ValueError("Person name cannot be empty.")
        clean_name = person_name.strip()
        if len(clean_name) > 40:
            raise ValueError("Person name cannot exceed 40 characters.")

    amount_paise = existing["amount_paise"]
    if amount_inr is not None:
        amount_paise = inr_to_paise(amount_inr)

    # due_date: None means "keep as is", empty string means "clear it"
    clean_due = existing["due_date"]
    if due_date is not None:
        if str(due_date).strip() == "":
            clean_due = None
        else:
            clean_due = _validate_date(str(due_date))

    clean_note = existing["note"]
    if note is not None:
        clean_note = note.strip()[:200] if isinstance(note, str) and note.strip() else None

    db = get_db()
    db.execute(
        """
        UPDATE udhar_records
        SET person_name = ?, amount_paise = ?, due_date = ?, note = ?
        WHERE id = ? AND user_id = ?
        """,
        (clean_name, amount_paise, clean_due, clean_note, record_id, user_id)
    )
    db.commit()
    return get_udhar_by_id(user_id, record_id)


def settle_udhar(user_id: int, record_id: int) -> dict:
    """
    Marks an udhar record as settled.
    Returns ValueError if already settled or not found.
    """
    existing = get_udhar_by_id(user_id, record_id)
    if existing is None:
        return None

    if existing["is_settled"] == 1:
        raise ValueError("This record is already settled.")

    db = get_db()
    db.execute(
        """
        UPDATE udhar_records
        SET is_settled = 1
        WHERE id = ? AND user_id = ? AND is_settled = 0
        """,
        (record_id, user_id)
    )
    db.commit()
    return get_udhar_by_id(user_id, record_id)


def reopen_udhar(user_id: int, record_id: int) -> dict:
    """
    Reopens a settled udhar record (sets is_settled = 0).
    Returns ValueError if already pending or not found.
    """
    existing = get_udhar_by_id(user_id, record_id)
    if existing is None:
        return None

    if existing["is_settled"] == 0:
        raise ValueError("This record is already open (not settled).")

    db = get_db()
    db.execute(
        """
        UPDATE udhar_records
        SET is_settled = 0
        WHERE id = ? AND user_id = ? AND is_settled = 1
        """,
        (record_id, user_id)
    )
    db.commit()
    return get_udhar_by_id(user_id, record_id)


def delete_udhar(user_id: int, record_id: int) -> bool:
    """
    Permanently deletes an udhar record.
    Returns True if deleted, False if not found.
    """
    existing = get_udhar_by_id(user_id, record_id)
    if existing is None:
        return False

    db = get_db()
    db.execute(
        "DELETE FROM udhar_records WHERE id = ? AND user_id = ?",
        (record_id, user_id)
    )
    db.commit()
    return True


def get_udhar_summary(user_id: int) -> dict:
    """
    Returns summary of pending udhar records:
    - total_to_receive_inr: sum of pending 'lent' amounts
    - total_to_pay_inr: sum of pending 'borrowed' amounts
    - overdue_count: count of pending records where due_date < today
    - pending_count: total pending records
    - per_person: list of {person_name, net_inr, record_count}
      where net_inr > 0 means they owe me (net lent), < 0 means I owe them (net borrowed)
    """
    if not user_id or not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user_id is required.")

    today = _today_date()
    db = get_db()

    agg = db.execute(
        """
        SELECT
            COALESCE(SUM(CASE WHEN type = 'lent'     THEN amount_paise ELSE 0 END), 0) AS to_receive_paise,
            COALESCE(SUM(CASE WHEN type = 'borrowed' THEN amount_paise ELSE 0 END), 0) AS to_pay_paise,
            COALESCE(SUM(CASE WHEN due_date IS NOT NULL AND due_date < ? THEN 1 ELSE 0 END), 0) AS overdue_count,
            COUNT(*) AS pending_count
        FROM udhar_records
        WHERE user_id = ? AND is_settled = 0
        """,
        (today, user_id)
    ).fetchone()

    # Per-person net breakdown (pending only)
    person_rows = db.execute(
        """
        SELECT
            person_name,
            SUM(CASE WHEN type = 'lent'     THEN  amount_paise
                     WHEN type = 'borrowed' THEN -amount_paise
                     ELSE 0 END) AS net_paise,
            COUNT(*) AS record_count
        FROM udhar_records
        WHERE user_id = ? AND is_settled = 0
        GROUP BY person_name
        ORDER BY person_name COLLATE NOCASE ASC
        """,
        (user_id,)
    ).fetchall()

    per_person = [
        {
            "person_name": r["person_name"],
            "net_inr": paise_to_inr(abs(int(r["net_paise"]))) * (1 if int(r["net_paise"]) >= 0 else -1),
            "record_count": int(r["record_count"])
        }
        for r in person_rows
    ]

    return {
        "total_to_receive_inr": paise_to_inr(int(agg["to_receive_paise"])),
        "total_to_pay_inr":     paise_to_inr(int(agg["to_pay_paise"])),
        "overdue_count":        int(agg["overdue_count"]),
        "pending_count":        int(agg["pending_count"]),
        "per_person":           per_person
    }
