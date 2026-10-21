from datetime import datetime
from database.db import get_db
from utils.helpers import inr_to_paise, paise_to_inr
from services.expense_service import create_expense

VALID_PRESET_TYPES = {"daily", "faltu"}
MAX_PRESETS_PER_USER = 12

def _format_preset_row(row) -> dict:
    if row is None:
        return None
    data = dict(row)
    data["amount_inr"] = paise_to_inr(data["amount_paise"])
    return data

def get_presets(user_id: int) -> list:
    """
    Retrieves all quick presets for a user, ordered by ID.
    Returns empty list if user has no presets.
    """
    if not user_id or not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user_id is required.")

    db = get_db()
    rows = db.execute(
        """
        SELECT * FROM quick_presets
        WHERE user_id = ?
        ORDER BY id ASC
        """,
        (user_id,)
    ).fetchall()
    return [_format_preset_row(row) for row in rows]

def get_preset_by_id(user_id: int, preset_id: int) -> dict:
    """
    Retrieves a single preset by ID for the specified user.
    """
    if not user_id or not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user_id is required.")
    if not preset_id or not isinstance(preset_id, int) or preset_id <= 0:
        raise ValueError("A valid preset_id is required.")

    db = get_db()
    row = db.execute(
        """
        SELECT * FROM quick_presets
        WHERE id = ? AND user_id = ?
        """,
        (preset_id, user_id)
    ).fetchone()
    return _format_preset_row(row)

def create_preset(user_id: int, title: str, amount_inr, preset_type: str, sub_category: str = "", icon: str = "⚡") -> dict:
    """
    Creates a new quick preset.
    Validations:
      - title: non-empty, max 30 chars
      - amount_inr: > 0
      - preset_type: 'daily' | 'faltu'
      - icon: max 4 characters
      - max 12 presets per user
    """
    if not user_id or not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user_id is required.")

    if not title or not isinstance(title, str) or not title.strip():
        raise ValueError("Title is required and cannot be empty.")
    clean_title = title.strip()
    if len(clean_title) > 30:
        raise ValueError("Title cannot exceed 30 characters.")

    amount_paise = inr_to_paise(amount_inr)

    if not preset_type or not isinstance(preset_type, str):
        raise ValueError("Preset type is required ('daily' or 'faltu').")
    clean_type = preset_type.strip().lower()
    if clean_type not in VALID_PRESET_TYPES:
        raise ValueError("Preset type must be either 'daily' or 'faltu'.")

    clean_sub_category = sub_category.strip() if sub_category and isinstance(sub_category, str) else clean_title

    clean_icon = icon.strip() if icon and isinstance(icon, str) else "⚡"
    if len(clean_icon) > 4:
        raise ValueError("Icon cannot exceed 4 characters.")

    db = get_db()
    # Check 12 presets limit per user
    count_row = db.execute(
        "SELECT COUNT(*) AS total FROM quick_presets WHERE user_id = ?",
        (user_id,)
    ).fetchone()
    if count_row["total"] >= MAX_PRESETS_PER_USER:
        raise ValueError(f"Maximum {MAX_PRESETS_PER_USER} presets allowed per user.")

    cursor = db.cursor()
    cursor.execute(
        """
        INSERT INTO quick_presets (user_id, title, amount_paise, type, sub_category, icon)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (user_id, clean_title, amount_paise, clean_type, clean_sub_category, clean_icon)
    )
    db.commit()
    new_id = cursor.lastrowid
    return get_preset_by_id(user_id, new_id)

def update_preset(user_id: int, preset_id: int, title: str = None, amount_inr = None, preset_type: str = None, sub_category: str = None, icon: str = None) -> dict:
    """
    Updates an existing preset owned by user_id.
    """
    existing = get_preset_by_id(user_id, preset_id)
    if not existing:
        raise ValueError("Preset not found.")

    clean_title = existing["title"]
    if title is not None:
        if not isinstance(title, str) or not title.strip():
            raise ValueError("Title cannot be empty.")
        clean_title = title.strip()
        if len(clean_title) > 30:
            raise ValueError("Title cannot exceed 30 characters.")

    amount_paise = existing["amount_paise"]
    if amount_inr is not None:
        amount_paise = inr_to_paise(amount_inr)

    clean_type = existing["type"]
    if preset_type is not None:
        if not isinstance(preset_type, str) or preset_type.strip().lower() not in VALID_PRESET_TYPES:
            raise ValueError("Preset type must be either 'daily' or 'faltu'.")
        clean_type = preset_type.strip().lower()

    clean_sub_category = existing["sub_category"]
    if sub_category is not None:
        clean_sub_category = sub_category.strip() if sub_category and isinstance(sub_category, str) else clean_title

    clean_icon = existing["icon"]
    if icon is not None:
        clean_icon = icon.strip() if icon and isinstance(icon, str) else "⚡"
        if len(clean_icon) > 4:
            raise ValueError("Icon cannot exceed 4 characters.")

    db = get_db()
    db.execute(
        """
        UPDATE quick_presets
        SET title = ?, amount_paise = ?, type = ?, sub_category = ?, icon = ?
        WHERE id = ? AND user_id = ?
        """,
        (clean_title, amount_paise, clean_type, clean_sub_category, clean_icon, preset_id, user_id)
    )
    db.commit()
    return get_preset_by_id(user_id, preset_id)

def delete_preset(user_id: int, preset_id: int) -> bool:
    """
    Deletes a preset owned by user_id.
    """
    existing = get_preset_by_id(user_id, preset_id)
    if not existing:
        raise ValueError("Preset not found.")

    db = get_db()
    db.execute(
        "DELETE FROM quick_presets WHERE id = ? AND user_id = ?",
        (preset_id, user_id)
    )
    db.commit()
    return True

def use_preset(user_id: int, preset_id: int) -> dict:
    """
    Creates an expense from the preset using today's local date in APP_TIMEZONE via create_expense.
    """
    from utils.clock import today_local

    preset = get_preset_by_id(user_id, preset_id)
    if not preset:
        raise ValueError("Preset not found.")

    today_date = today_local().isoformat()
    expense = create_expense(
        user_id=user_id,
        amount_inr=preset["amount_inr"],
        expense_type=preset["type"],
        sub_category=preset["sub_category"],
        date=today_date,
        note=f"{preset['title']}"
    )
    return expense
