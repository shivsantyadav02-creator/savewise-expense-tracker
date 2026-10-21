from datetime import datetime, timedelta
from database.db import get_db
from utils.clock import now_utc, to_iso_utc, parse_iso_utc
from utils.helpers import inr_to_paise, paise_to_inr, derive_month_from_date
from services.expense_service import get_expense_by_id

VALID_WISHLIST_STATUSES = {"waiting", "bought", "dropped", "all"}

def format_wait_duration(seconds: int) -> str:
    """
    Formats remaining seconds into a human-friendly string (e.g. '5h 20m', '45m', '30s').
    """
    if seconds <= 0:
        return "0s"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m"
    else:
        return f"{secs}s"

def _format_wishlist_row(row, now=None) -> dict:
    if row is None:
        return None
    data = dict(row)
    data["estimated_amount_inr"] = paise_to_inr(data["estimated_amount_paise"])

    current_time = now if now is not None else now_utc()
    unlock_dt = parse_iso_utc(data["unlock_at"])

    if current_time >= unlock_dt:
        data["is_unlocked"] = True
        data["seconds_remaining"] = 0
    else:
        data["is_unlocked"] = False
        data["seconds_remaining"] = int((unlock_dt - current_time).total_seconds())

    return data

def get_wishlist_items(user_id: int, status: str = "waiting") -> list:
    """
    Retrieves wishlist items for a user, filtered by status ('waiting', 'bought', 'dropped', or 'all').
    Each item includes is_unlocked and seconds_remaining.
    """
    if not user_id or not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user_id is required.")

    clean_status = status.strip().lower() if status else "waiting"
    if clean_status not in VALID_WISHLIST_STATUSES:
        raise ValueError("Invalid status filter. Must be 'waiting', 'bought', 'dropped', or 'all'.")

    db = get_db()
    if clean_status == "all":
        rows = db.execute(
            """
            SELECT * FROM wishlist_items
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            """,
            (user_id,)
        ).fetchall()
    else:
        rows = db.execute(
            """
            SELECT * FROM wishlist_items
            WHERE user_id = ? AND status = ?
            ORDER BY created_at DESC, id DESC
            """,
            (user_id, clean_status)
        ).fetchall()

    now = now_utc()
    return [_format_wishlist_row(r, now) for r in rows]

def get_wishlist_item_by_id(user_id: int, item_id: int) -> dict:
    """
    Retrieves a single wishlist item by ID for the given user.
    """
    if not user_id or not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user_id is required.")
    if not item_id or not isinstance(item_id, int) or item_id <= 0:
        raise ValueError("A valid item_id is required.")

    db = get_db()
    row = db.execute(
        """
        SELECT * FROM wishlist_items
        WHERE id = ? AND user_id = ?
        """,
        (item_id, user_id)
    ).fetchone()
    return _format_wishlist_row(row)

def create_wishlist_item(user_id: int, item_name: str, estimated_amount_inr, sub_category: str = "Shopping") -> dict:
    """
    Creates a new wishlist item.
    Enforces 24-hour wait rule: unlock_at = created_at + 24 hours (server-computed).
    Client-sent unlock_at is never accepted.
    """
    if not user_id or not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user_id is required.")

    if not item_name or not isinstance(item_name, str) or not item_name.strip():
        raise ValueError("Item name is required and cannot be empty.")
    clean_name = item_name.strip()
    if len(clean_name) > 60:
        raise ValueError("Item name cannot exceed 60 characters.")

    amount_paise = inr_to_paise(estimated_amount_inr)

    clean_category = sub_category.strip() if sub_category and isinstance(sub_category, str) else "Shopping"
    if len(clean_category) > 50:
        clean_category = clean_category[:50]

    # Server generates UTC timestamps
    now = now_utc()
    created_at_iso = to_iso_utc(now)
    unlock_at_iso = to_iso_utc(now + timedelta(hours=24))

    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        """
        INSERT INTO wishlist_items (user_id, item_name, estimated_amount_paise, sub_category, status, unlock_at, created_at)
        VALUES (?, ?, ?, ?, 'waiting', ?, ?)
        """,
        (user_id, clean_name, amount_paise, clean_category, unlock_at_iso, created_at_iso)
    )
    db.commit()
    new_id = cursor.lastrowid
    return get_wishlist_item_by_id(user_id, new_id)

def update_wishlist_item(user_id: int, item_id: int, item_name: str = None, estimated_amount_inr = None, sub_category: str = None) -> dict:
    """
    Updates an item while in 'waiting' status.
    Must NOT reset unlock_at.
    """
    existing = get_wishlist_item_by_id(user_id, item_id)
    if not existing:
        raise ValueError("Wishlist item not found.")

    if existing["status"] != "waiting":
        raise ValueError(f"Cannot edit item with status '{existing['status']}'.")

    clean_name = existing["item_name"]
    if item_name is not None:
        if not isinstance(item_name, str) or not item_name.strip():
            raise ValueError("Item name cannot be empty.")
        clean_name = item_name.strip()
        if len(clean_name) > 60:
            raise ValueError("Item name cannot exceed 60 characters.")

    amount_paise = existing["estimated_amount_paise"]
    if estimated_amount_inr is not None:
        amount_paise = inr_to_paise(estimated_amount_inr)

    clean_category = existing["sub_category"]
    if sub_category is not None:
        clean_category = sub_category.strip() if isinstance(sub_category, str) and sub_category.strip() else "Shopping"
        if len(clean_category) > 50:
            clean_category = clean_category[:50]

    db = get_db()
    db.execute(
        """
        UPDATE wishlist_items
        SET item_name = ?, estimated_amount_paise = ?, sub_category = ?
        WHERE id = ? AND user_id = ? AND status = 'waiting'
        """,
        (clean_name, amount_paise, clean_category, item_id, user_id)
    )
    db.commit()
    return get_wishlist_item_by_id(user_id, item_id)

def buy_wishlist_item(user_id: int, item_id: int) -> dict:
    """
    Executes buy for a wishlist item.
    Allowed ONLY if:
      1. status is 'waiting'
      2. now_utc() >= unlock_at
    In ONE database transaction:
      - updates status to 'bought'
      - creates a 'faltu' expense with wishlist_item_id = item_id
    Double-buy is strictly impossible.
    """
    existing = get_wishlist_item_by_id(user_id, item_id)
    if not existing:
        raise ValueError("Wishlist item not found.")

    if existing["status"] != "waiting":
        raise ValueError(f"Cannot buy item with status '{existing['status']}'.")

    now = now_utc()
    unlock_dt = parse_iso_utc(existing["unlock_at"])
    if now < unlock_dt:
        seconds_left = int((unlock_dt - now).total_seconds())
        wait_str = format_wait_duration(seconds_left)
        raise ValueError(f"Please wait {wait_str} more before buying.")

    today_date = now.strftime("%Y-%m-%d")
    month = derive_month_from_date(today_date)

    db = get_db()
    cursor = db.cursor()

    # Atomic update - ensures only one thread/request can succeed
    cursor.execute(
        """
        UPDATE wishlist_items
        SET status = 'bought'
        WHERE id = ? AND user_id = ? AND status = 'waiting'
        """,
        (item_id, user_id)
    )
    if cursor.rowcount == 0:
        raise ValueError("Item cannot be bought (already bought or dropped).")

    # Insert expense linked to the wishlist item in the same transaction
    cursor.execute(
        """
        INSERT INTO expenses (user_id, amount_paise, type, sub_category, date, month, note, wishlist_item_id)
        VALUES (?, ?, 'faltu', ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            existing["estimated_amount_paise"],
            existing["sub_category"],
            today_date,
            month,
            existing["item_name"],
            item_id
        )
    )
    new_expense_id = cursor.lastrowid
    db.commit()

    created_expense = get_expense_by_id(user_id, new_expense_id)
    updated_item = get_wishlist_item_by_id(user_id, item_id)

    # Return structure with both item and expense
    return {
        **created_expense,
        "item": updated_item,
        "expense": created_expense
    }

def drop_wishlist_item(user_id: int, item_id: int) -> dict:
    """
    Drops a wishlist item while in 'waiting' status.
    Early drop is allowed anytime before or after 24h as long as status is 'waiting'.
    """
    existing = get_wishlist_item_by_id(user_id, item_id)
    if not existing:
        raise ValueError("Wishlist item not found.")

    if existing["status"] != "waiting":
        raise ValueError(f"Cannot drop item with status '{existing['status']}'.")

    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        """
        UPDATE wishlist_items
        SET status = 'dropped'
        WHERE id = ? AND user_id = ? AND status = 'waiting'
        """,
        (item_id, user_id)
    )
    if cursor.rowcount == 0:
        raise ValueError("Item cannot be dropped (already processed).")
    db.commit()

    return get_wishlist_item_by_id(user_id, item_id)

def get_wishlist_summary(user_id: int) -> dict:
    """
    Returns summary of wishlist items for user:
    - items_dropped
    - amount_saved_inr (sum of dropped items)
    - items_waiting
    """
    if not user_id or not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user_id is required.")

    db = get_db()
    row = db.execute(
        """
        SELECT 
            COALESCE(SUM(CASE WHEN status = 'dropped' THEN 1 ELSE 0 END), 0) AS items_dropped,
            COALESCE(SUM(CASE WHEN status = 'dropped' THEN estimated_amount_paise ELSE 0 END), 0) AS amount_saved_paise,
            COALESCE(SUM(CASE WHEN status = 'waiting' THEN 1 ELSE 0 END), 0) AS items_waiting
        FROM wishlist_items
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchone()

    return {
        "items_dropped": int(row["items_dropped"]),
        "amount_saved_inr": paise_to_inr(int(row["amount_saved_paise"])),
        "items_waiting": int(row["items_waiting"])
    }
