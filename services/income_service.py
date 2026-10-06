from database.db import get_db
from utils.helpers import inr_to_paise, paise_to_inr, derive_month_from_date

def _format_income_row(row) -> dict:
    """Helper to convert an SQLite Row into a user-friendly dictionary with amount_inr."""
    if row is None:
        return None
    data = dict(row)
    data["amount_inr"] = paise_to_inr(data["amount_paise"])
    return data

def create_income(user_id: int, amount_inr, source: str, date: str, note: str = "") -> dict:
    """
    Creates a new income entry for a user.
    - user_id: ID of the user.
    - amount_inr: Monetary amount in rupees (> 0).
    - source: Income source (e.g. 'Pocket Money', 'Salary').
    - date: Transaction date formatted as 'YYYY-MM-DD'.
    - note: Optional description.
    """
    if not user_id or not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user_id is required.")
    
    if not source or not str(source).strip():
        raise ValueError("Income source is required and cannot be empty.")
    
    amount_paise = inr_to_paise(amount_inr)
    month = derive_month_from_date(date)
    clean_source = str(source).strip()
    clean_note = str(note).strip() if note else ""

    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        """
        INSERT INTO incomes (user_id, amount_paise, source, date, month, note)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (user_id, amount_paise, clean_source, date.strip(), month, clean_note)
    )
    db.commit()
    new_id = cursor.lastrowid
    return get_income_by_id(user_id, new_id)

def get_incomes(user_id: int, month: str = None) -> list:
    """
    Retrieves all income records for a given user, optionally filtered by month ('YYYY-MM').
    Records are sorted with most recent transactions first.
    """
    if not user_id or not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user_id is required.")
    
    db = get_db()
    if month:
        cursor = db.execute(
            """
            SELECT * FROM incomes
            WHERE user_id = ? AND month = ?
            ORDER BY date DESC, id DESC
            """,
            (user_id, month.strip())
        )
    else:
        cursor = db.execute(
            """
            SELECT * FROM incomes
            WHERE user_id = ?
            ORDER BY date DESC, id DESC
            """,
            (user_id,)
        )
    return [_format_income_row(r) for r in cursor.fetchall()]

def get_income_by_id(user_id: int, income_id: int) -> dict:
    """
    Retrieves a single income entry by its primary key id.
    Strictly filters by user_id to prevent unauthorized access across users.
    """
    if not user_id or not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user_id is required.")
    if not income_id or not isinstance(income_id, int) or income_id <= 0:
        raise ValueError("A valid income_id is required.")
        
    db = get_db()
    row = db.execute(
        "SELECT * FROM incomes WHERE id = ? AND user_id = ?",
        (income_id, user_id)
    ).fetchone()
    return _format_income_row(row)

def update_income(user_id: int, income_id: int, amount_inr=None, source: str = None, date: str = None, note: str = None) -> dict:
    """
    Updates an existing income entry.
    Only provided fields are updated; unspecified fields remain unchanged.
    """
    existing = get_income_by_id(user_id, income_id)
    if not existing:
        raise ValueError(f"Income with id {income_id} not found for this user.")

    # Validate updates if provided
    new_amount_paise = inr_to_paise(amount_inr) if amount_inr is not None else existing["amount_paise"]
    
    if source is not None:
        clean_source = str(source).strip()
        if not clean_source:
            raise ValueError("Income source cannot be empty.")
    else:
        clean_source = existing["source"]

    if date is not None:
        clean_date = date.strip()
        new_month = derive_month_from_date(clean_date)
    else:
        clean_date = existing["date"]
        new_month = existing["month"]

    clean_note = str(note).strip() if note is not None else existing["note"]

    db = get_db()
    db.execute(
        """
        UPDATE incomes
        SET amount_paise = ?, source = ?, date = ?, month = ?, note = ?
        WHERE id = ? AND user_id = ?
        """,
        (new_amount_paise, clean_source, clean_date, new_month, clean_note, income_id, user_id)
    )
    db.commit()
    return get_income_by_id(user_id, income_id)

def delete_income(user_id: int, income_id: int) -> bool:
    """
    Deletes an income entry owned by user_id.
    Returns True on success, or raises ValueError if not found.
    """
    if not user_id or not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user_id is required.")
    if not income_id or not isinstance(income_id, int) or income_id <= 0:
        raise ValueError("A valid income_id is required.")

    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "DELETE FROM incomes WHERE id = ? AND user_id = ?",
        (income_id, user_id)
    )
    db.commit()
    if cursor.rowcount == 0:
        raise ValueError(f"Income with id {income_id} not found for this user.")
    return True
