from database.db import get_db
from utils.helpers import inr_to_paise, paise_to_inr, derive_month_from_date, validate_month

VALID_EXPENSE_TYPES = {"daily", "faltu"}

def _format_expense_row(row) -> dict:
    """Helper to convert an SQLite Row into a user-friendly dictionary with amount_inr."""
    if row is None:
        return None
    data = dict(row)
    data["amount_inr"] = paise_to_inr(data["amount_paise"])
    return data

def create_expense(user_id: int, amount_inr, expense_type: str, sub_category: str, date: str, note: str = "", wishlist_item_id: int = None) -> dict:
    """
    Creates a new expense entry for a user.
    - user_id: ID of the user.
    - amount_inr: Amount in rupees (> 0).
    - expense_type: Must be 'daily' (necessary) or 'faltu' (wasteful/impulse).
    - sub_category: Category description (e.g. 'Food', 'Travel', 'Chai').
    - date: Transaction date in 'YYYY-MM-DD'.
    - note: Optional description.
    - wishlist_item_id: Optional ID of the originating wishlist item (Phase 2).
    """
    if not user_id or not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user_id is required.")

    if not expense_type or str(expense_type).strip().lower() not in VALID_EXPENSE_TYPES:
        raise ValueError("Expense type must be either 'daily' or 'faltu'.")
    clean_type = str(expense_type).strip().lower()

    if not sub_category or not str(sub_category).strip():
        raise ValueError("Sub-category is required and cannot be empty.")
    clean_sub_category = str(sub_category).strip()

    amount_paise = inr_to_paise(amount_inr)
    month = derive_month_from_date(date)
    clean_note = str(note).strip() if note else ""

    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        """
        INSERT INTO expenses (user_id, amount_paise, type, sub_category, date, month, note, wishlist_item_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, amount_paise, clean_type, clean_sub_category, date.strip(), month, clean_note, wishlist_item_id)
    )
    db.commit()
    new_id = cursor.lastrowid
    return get_expense_by_id(user_id, new_id)

def get_expenses(user_id: int, month: str = None, expense_type: str = None) -> list:
    """
    Retrieves expenses for a user.
    Optional filters:
    - month: 'YYYY-MM'
    - expense_type: 'daily', 'faltu', or None/'all'
    """
    if not user_id or not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user_id is required.")

    query = "SELECT * FROM expenses WHERE user_id = ?"
    params = [user_id]

    if month:
        clean_month = validate_month(month)
        query += " AND month = ?"
        params.append(clean_month)

    if expense_type and expense_type.lower() in VALID_EXPENSE_TYPES:
        query += " AND type = ?"
        params.append(expense_type.strip().lower())

    query += " ORDER BY date DESC, id DESC"

    db = get_db()
    cursor = db.execute(query, tuple(params))
    return [_format_expense_row(r) for r in cursor.fetchall()]

def get_expense_by_id(user_id: int, expense_id: int) -> dict:
    """
    Fetches a single expense entry by ID, strictly scoped to user_id.
    """
    if not user_id or not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user_id is required.")
    if not expense_id or not isinstance(expense_id, int) or expense_id <= 0:
        raise ValueError("A valid expense_id is required.")

    db = get_db()
    row = db.execute(
        "SELECT * FROM expenses WHERE id = ? AND user_id = ?",
        (expense_id, user_id)
    ).fetchone()
    return _format_expense_row(row)

def update_expense(user_id: int, expense_id: int, amount_inr=None, expense_type: str = None, sub_category: str = None, date: str = None, note: str = None) -> dict:
    """
    Updates an existing expense entry owned by user_id.
    """
    existing = get_expense_by_id(user_id, expense_id)
    if not existing:
        raise ValueError(f"Expense with id {expense_id} not found for this user.")

    new_amount_paise = inr_to_paise(amount_inr) if amount_inr is not None else existing["amount_paise"]

    if expense_type is not None:
        clean_type = str(expense_type).strip().lower()
        if clean_type not in VALID_EXPENSE_TYPES:
            raise ValueError("Expense type must be either 'daily' or 'faltu'.")
    else:
        clean_type = existing["type"]

    if sub_category is not None:
        clean_sub_cat = str(sub_category).strip()
        if not clean_sub_cat:
            raise ValueError("Sub-category cannot be empty.")
    else:
        clean_sub_cat = existing["sub_category"]

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
        UPDATE expenses
        SET amount_paise = ?, type = ?, sub_category = ?, date = ?, month = ?, note = ?
        WHERE id = ? AND user_id = ?
        """,
        (new_amount_paise, clean_type, clean_sub_cat, clean_date, new_month, clean_note, expense_id, user_id)
    )
    db.commit()
    return get_expense_by_id(user_id, expense_id)

def delete_expense(user_id: int, expense_id: int) -> bool:
    """
    Deletes an expense entry owned by user_id.
    """
    if not user_id or not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user_id is required.")
    if not expense_id or not isinstance(expense_id, int) or expense_id <= 0:
        raise ValueError("A valid expense_id is required.")

    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "DELETE FROM expenses WHERE id = ? AND user_id = ?",
        (expense_id, user_id)
    )
    db.commit()
    if cursor.rowcount == 0:
        raise ValueError(f"Expense with id {expense_id} not found for this user.")
    return True
