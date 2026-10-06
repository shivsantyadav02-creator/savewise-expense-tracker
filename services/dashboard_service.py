from datetime import datetime
from database.db import get_db
from utils.helpers import paise_to_inr

def get_monthly_summary(user_id: int, month: str = None) -> dict:
    """
    Computes financial totals and key ratios for a given user and month.
    
    Returns:
    - total_income_paise & total_income_inr
    - total_daily_paise & total_daily_inr
    - total_faltu_paise & total_faltu_inr
    - total_expenses_paise & total_expenses_inr
    - balance_paise & balance_inr
    - faltu_percentage: % of total expenses that is faltu
    - faltu_percent_of_income: % of total income spent on faltu
    
    Safely handles division by zero when income or expenses are 0.
    """
    if not user_id or not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user_id is required.")

    # Default to current month if not specified
    target_month = month.strip() if month else datetime.now().strftime("%Y-%m")

    db = get_db()

    # 1. Total Income aggregation
    income_row = db.execute(
        """
        SELECT COALESCE(SUM(amount_paise), 0) AS total_income, COUNT(id) AS income_count
        FROM incomes
        WHERE user_id = ? AND month = ?
        """,
        (user_id, target_month)
    ).fetchone()
    total_income_paise = int(income_row["total_income"])
    income_count = int(income_row["income_count"])

    # 2. Daily vs Faltu Expenses aggregation in a single query
    expense_row = db.execute(
        """
        SELECT 
            COALESCE(SUM(CASE WHEN type = 'daily' THEN amount_paise ELSE 0 END), 0) AS total_daily,
            COALESCE(SUM(CASE WHEN type = 'faltu' THEN amount_paise ELSE 0 END), 0) AS total_faltu,
            COALESCE(SUM(amount_paise), 0) AS total_expenses,
            COUNT(id) AS expense_count
        FROM expenses
        WHERE user_id = ? AND month = ?
        """,
        (user_id, target_month)
    ).fetchone()
    total_daily_paise = int(expense_row["total_daily"])
    total_faltu_paise = int(expense_row["total_faltu"])
    total_expenses_paise = int(expense_row["total_expenses"])
    expense_count = int(expense_row["expense_count"])

    # 3. Balance calculation
    balance_paise = total_income_paise - total_expenses_paise

    # 4. Ratio calculations with zero-division safety
    if total_expenses_paise > 0:
        faltu_percentage = round((total_faltu_paise / total_expenses_paise) * 100.0, 2)
    else:
        faltu_percentage = 0.0

    if total_income_paise > 0:
        faltu_percent_of_income = round((total_faltu_paise / total_income_paise) * 100.0, 2)
    else:
        faltu_percent_of_income = 0.0

    return {
        "user_id": user_id,
        "month": target_month,
        "total_income_paise": total_income_paise,
        "total_income_inr": paise_to_inr(total_income_paise),
        "total_daily_paise": total_daily_paise,
        "total_daily_inr": paise_to_inr(total_daily_paise),
        "total_faltu_paise": total_faltu_paise,
        "total_faltu_inr": paise_to_inr(total_faltu_paise),
        "total_expenses_paise": total_expenses_paise,
        "total_expenses_inr": paise_to_inr(total_expenses_paise),
        "balance_paise": balance_paise,
        "balance_inr": paise_to_inr(balance_paise),
        "faltu_percentage": faltu_percentage,
        "faltu_percent_of_income": faltu_percent_of_income,
        "income_count": income_count,
        "expense_count": expense_count
    }
