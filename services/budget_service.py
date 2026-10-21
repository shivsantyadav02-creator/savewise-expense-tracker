from database.db import get_db
from utils.helpers import inr_to_paise, paise_to_inr, validate_month

def _format_budget_row(row) -> dict:
    """Formats an SQLite row from monthly_budgets into a dictionary with amount in INR."""
    if row is None:
        return None
    data = dict(row)
    data["faltu_limit_inr"] = paise_to_inr(data["faltu_limit_paise"])
    return data

def get_faltu_limit(user_id: int, month: str) -> dict:
    """
    Retrieves the monthly faltu limit budget for a user and month ('YYYY-MM').
    Returns None if no limit has been configured.
    """
    if not user_id or not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user_id is required.")
    
    clean_month = validate_month(month)
    db = get_db()
    row = db.execute(
        "SELECT * FROM monthly_budgets WHERE user_id = ? AND month = ?",
        (user_id, clean_month)
    ).fetchone()
    return _format_budget_row(row)

def set_faltu_limit(user_id: int, month: str, amount_inr) -> dict:
    """
    Creates or updates the monthly faltu spending limit for a user and month.
    Enforces amount_inr >= 0 (supports zero limit budgets).
    """
    if not user_id or not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user_id is required.")
    
    clean_month = validate_month(month)
    limit_paise = inr_to_paise(amount_inr, allow_zero=True)

    db = get_db()
    db.execute(
        """
        INSERT INTO monthly_budgets (user_id, month, faltu_limit_paise)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id, month) DO UPDATE SET faltu_limit_paise = excluded.faltu_limit_paise
        """,
        (user_id, clean_month, limit_paise)
    )
    db.commit()
    return get_faltu_limit(user_id, clean_month)
