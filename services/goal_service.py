from database.db import get_db
from utils.helpers import inr_to_paise, paise_to_inr, validate_month

DEFAULT_GOAL_TITLE = "Monthly Savings Target"

def _format_goal_row(row) -> dict:
    """Formats an SQLite row from savings_goals into a dictionary with amount in INR."""
    if row is None:
        return None
    data = dict(row)
    data["target_inr"] = paise_to_inr(data["target_amount_paise"])
    return data

def get_savings_goal(user_id: int, month: str) -> dict:
    """
    Retrieves the savings goal for a user and month ('YYYY-MM').
    Returns None if no goal has been configured.
    """
    if not user_id or not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user_id is required.")
    
    clean_month = validate_month(month)
    db = get_db()
    row = db.execute(
        "SELECT * FROM savings_goals WHERE user_id = ? AND month = ?",
        (user_id, clean_month)
    ).fetchone()
    return _format_goal_row(row)

def set_savings_goal(user_id: int, month: str, target_inr, title: str = None) -> dict:
    """
    Creates or updates the monthly savings goal for a user and month.
    Enforces target_inr > 0.
    """
    if not user_id or not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user_id is required.")
    
    clean_month = validate_month(month)
    target_paise = inr_to_paise(target_inr, allow_zero=False)
    
    clean_title = str(title).strip() if (title and str(title).strip()) else DEFAULT_GOAL_TITLE

    db = get_db()
    db.execute(
        """
        INSERT INTO savings_goals (user_id, month, target_amount_paise, title)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, month) DO UPDATE SET target_amount_paise = excluded.target_amount_paise, title = excluded.title
        """,
        (user_id, clean_month, target_paise, clean_title)
    )
    db.commit()
    return get_savings_goal(user_id, clean_month)
