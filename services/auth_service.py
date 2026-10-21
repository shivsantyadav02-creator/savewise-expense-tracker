"""
services/auth_service.py — Authentication business logic.

Design decisions:
- Passwords hashed with werkzeug.security. Never stored or logged as plain text.
- Brute-force protection: 5 failures per email within 15 minutes → 429 for 15 min.
  Counter is in-memory (process-local). Limitation: resets on restart; not shared
  across multiple worker processes. A Redis/DB-backed counter is the production fix.
- First registration adopts user row id=1 (the seed default_user whose password_hash
  is NULL) inside a single transaction, so all existing Phase 1/2 data stays linked.
  Every subsequent registration inserts a new user row.
- session.clear() is called before setting a new session (prevents session fixation).
- utils.clock.now_utc() is used for all time reads so tests can control time.
"""
import re
from datetime import timedelta
from collections import defaultdict

from werkzeug.security import generate_password_hash, check_password_hash

from database.db import get_db
from utils.clock import now_utc

# ── constants ──────────────────────────────────────────────────────────────────
_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,30}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PASSWORD_MIN_LEN = 8

# ── in-memory brute-force tracker ─────────────────────────────────────────────
# NOTE: This is process-local and resets on restart. For production with multiple
# workers, replace with a Redis/database-backed counter.
_login_failures: dict[str, list] = defaultdict(list)  # email → [timestamp, ...]
_LOCKOUT_WINDOW_SECONDS = 900   # 15 minutes
_LOCKOUT_MAX_ATTEMPTS = 5


def _is_locked_out(email: str) -> bool:
    """Returns True if this email is currently locked out (brute-force guard)."""
    cutoff = now_utc() - timedelta(seconds=_LOCKOUT_WINDOW_SECONDS)
    # Prune old failures outside the window
    _login_failures[email] = [
        t for t in _login_failures[email] if t > cutoff
    ]
    return len(_login_failures[email]) >= _LOCKOUT_MAX_ATTEMPTS


def _record_failure(email: str) -> None:
    """Records a failed login attempt for brute-force counting."""
    _login_failures[email].append(now_utc())


def _clear_failures(email: str) -> None:
    """Clears failure history on successful login."""
    _login_failures.pop(email, None)


# ── validation helpers ─────────────────────────────────────────────────────────

def _validate_registration(username: str, email: str, password: str) -> None:
    """
    Raises ValueError with a user-facing message if any field fails validation.
    """
    # Username: 3-30 chars, letters/digits/underscore only
    if not username or not _USERNAME_RE.match(username):
        raise ValueError(
            "Username must be 3–30 characters and contain only letters, digits, or underscores."
        )

    # Email: basic format, stored lowercase
    if not email or not _EMAIL_RE.match(email.strip()):
        raise ValueError("A valid email address is required.")

    # Password: minimum length
    if not password or len(password) < _PASSWORD_MIN_LEN:
        raise ValueError(f"Password must be at least {_PASSWORD_MIN_LEN} characters long.")

    # Password must not equal username or email
    if password.lower() == username.lower():
        raise ValueError("Password must not be the same as your username.")
    if password.lower() == email.strip().lower():
        raise ValueError("Password must not be the same as your email address.")


# ── public service functions ───────────────────────────────────────────────────

def register_user(username: str, email: str, password: str) -> dict:
    """
    Registers a new user.

    Special case — first registration adopts the default seed user (id=1, password_hash=NULL):
    Instead of inserting a new row, we UPDATE row id=1. This preserves all existing Phase 1/2
    data (incomes, expenses, etc.) that was created under user_id=1.

    Every subsequent registration inserts a new user row.

    Returns a dict with id, username, email.
    Raises ValueError on validation failure or uniqueness conflict.
    """
    username = username.strip() if username else ""
    email = email.strip().lower() if email else ""
    password = password or ""

    _validate_registration(username, email, password)

    pw_hash = generate_password_hash(password)
    db = get_db()

    # Check for duplicate username (case-insensitive)
    existing_uname = db.execute(
        "SELECT id FROM users WHERE LOWER(username) = LOWER(?)", (username,)
    ).fetchone()
    if existing_uname:
        raise ValueError("That username is already taken.")

    # Check for duplicate email
    existing_email = db.execute(
        "SELECT id FROM users WHERE email = ?", (email,)
    ).fetchone()
    if existing_email:
        raise ValueError("An account with that email already exists.")

    # Is there an unclaimed default user (id=1, password_hash IS NULL)?
    default_user = db.execute(
        "SELECT id FROM users WHERE id = 1 AND password_hash IS NULL"
    ).fetchone()

    if default_user:
        # Adopt user row id=1 — all existing data keeps its user_id=1 link
        db.execute(
            "UPDATE users SET username = ?, email = ?, password_hash = ? WHERE id = 1",
            (username, email, pw_hash),
        )
        db.commit()
        user_id = 1
    else:
        # New user → insert fresh row
        cursor = db.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username, email, pw_hash),
        )
        db.commit()
        user_id = cursor.lastrowid

    return {"id": user_id, "username": username, "email": email}


def login_user(email: str, password: str) -> dict:
    """
    Authenticates a user by email + password.

    Returns user dict {id, username, email} on success.
    Raises ValueError("locked") if locked out.
    Raises ValueError("invalid") on bad credentials (generic — never reveals
    whether the email exists to prevent user enumeration).
    """
    email_clean = (email or "").strip().lower()

    if _is_locked_out(email_clean):
        raise ValueError("locked")

    db = get_db()
    row = db.execute(
        "SELECT id, username, email, password_hash FROM users WHERE email = ?",
        (email_clean,),
    ).fetchone()

    # Constant-time-ish: always call check_password_hash even when row is None
    # to avoid timing-based user enumeration.
    dummy_hash = "pbkdf2:sha256:dummy"
    stored_hash = row["password_hash"] if (row and row["password_hash"]) else dummy_hash
    password_ok = check_password_hash(stored_hash, password or "")

    if not row or not password_ok:
        _record_failure(email_clean)
        raise ValueError("invalid")

    _clear_failures(email_clean)
    return {"id": row["id"], "username": row["username"], "email": row["email"]}


def get_user_by_id(user_id: int) -> dict | None:
    """
    Returns {id, username, email} for the given user_id, or None if not found.
    Never returns the password_hash.
    """
    db = get_db()
    row = db.execute(
        "SELECT id, username, email FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    if not row:
        return None
    return {"id": row["id"], "username": row["username"], "email": row["email"]}
