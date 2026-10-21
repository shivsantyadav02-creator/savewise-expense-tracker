from datetime import datetime
from database.db import get_db
from utils.helpers import paise_to_inr, validate_month
from utils.clock import today_local
from services.budget_service import get_faltu_limit
from services.goal_service import get_savings_goal

def get_monthly_summary(user_id: int, month: str = None) -> dict:
    """
    Computes financial totals, ratios, budget limit status, and savings goal progress
    for a given user and month ('YYYY-MM').
    
    Safe against division by zero in all cases.
    """
    if not user_id or not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user_id is required.")

    # Validate or default to current month
    target_month = validate_month(month) if month else today_local().strftime("%Y-%m")

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

    # 5. Faltu Limit & Budget Metrics (Phase 2)
    budget = get_faltu_limit(user_id, target_month)
    if budget is None:
        faltu_limit_inr = None
        faltu_limit_paise = None
        faltu_used_percent_of_limit = 0.0
        faltu_status = "none"
    else:
        faltu_limit_paise = budget["faltu_limit_paise"]
        faltu_limit_inr = budget["faltu_limit_inr"]
        if faltu_limit_paise == 0:
            if total_faltu_paise == 0:
                faltu_used_percent_of_limit = 0.0
                faltu_status = "normal"
            else:
                faltu_used_percent_of_limit = 100.0
                faltu_status = "critical"
        else:
            raw_used_pct = round((total_faltu_paise / faltu_limit_paise) * 100.0, 2)
            faltu_used_percent_of_limit = raw_used_pct
            if raw_used_pct >= 100.0:
                faltu_status = "critical"
            elif raw_used_pct >= 80.0:
                faltu_status = "warning"
            else:
                faltu_status = "normal"

    # 6. Savings Goal & Progress Metrics (Phase 2)
    goal = get_savings_goal(user_id, target_month)
    if goal is None:
        savings_goal_inr = None
        savings_goal_paise = None
        savings_goal_title = None
        savings_progress_percent = 0.0
        savings_raw_progress_percent = 0.0
        savings_status = "none"
    else:
        savings_goal_paise = goal["target_amount_paise"]
        savings_goal_inr = goal["target_inr"]
        savings_goal_title = goal["title"]

        raw_savings_pct = round((balance_paise / savings_goal_paise) * 100.0, 2)
        savings_raw_progress_percent = raw_savings_pct
        savings_progress_percent = max(0.0, min(100.0, raw_savings_pct))

        if balance_paise < 0:
            savings_status = "deficit"
        elif balance_paise == 0:
            savings_status = "not_started"
        elif raw_savings_pct >= 100.0:
            savings_status = "achieved"
        else:
            savings_status = "in_progress"

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
        "expense_count": expense_count,
        # Phase 2 metrics
        "faltu_limit_paise": faltu_limit_paise,
        "faltu_limit_inr": faltu_limit_inr,
        "faltu_used_percent_of_limit": faltu_used_percent_of_limit,
        "faltu_status": faltu_status,
        "savings_goal_paise": savings_goal_paise,
        "savings_goal_inr": savings_goal_inr,
        "savings_goal_title": savings_goal_title,
        "savings_progress_percent": savings_progress_percent,
        "savings_raw_progress_percent": savings_raw_progress_percent,
        "savings_status": savings_status
    }

def get_monthly_history(user_id: int, months: int = 6, end_month: str = None) -> list:
    """
    Retrieves month-wise financial history for the last N months ending at `end_month`.
    - user_id: ID of the user (> 0).
    - months: Number of months to retrieve (1 <= months <= 24, default 6).
    - end_month: 'YYYY-MM' ending month (defaults to current month).
    
    Returns list of dicts in oldest-to-newest order:
    [
        {
            "month": "YYYY-MM",
            "income_inr": 0.0,
            "daily_inr": 0.0,
            "faltu_inr": 0.0,
            "total_expense_inr": 0.0,
            "balance_inr": 0.0
        },
        ...
    ]
    Includes months with zero data. Parameterized SQL only, filtered by user_id.
    """
    if not user_id or not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user_id is required.")

    if not isinstance(months, int) or months < 1 or months > 24:
        raise ValueError("Parameter 'months' must be an integer between 1 and 24.")

    target_end_month = validate_month(end_month) if end_month else today_local().strftime("%Y-%m")

    # Generate N month strings in oldest-to-newest order
    year, m_num = map(int, target_end_month.split("-"))
    month_list = []
    for i in range(months - 1, -1, -1):
        total_m = year * 12 + (m_num - 1) - i
        y = total_m // 12
        m = (total_m % 12) + 1
        month_list.append(f"{y:04d}-{m:02d}")

    db = get_db()
    placeholders = ",".join(["?"] * len(month_list))

    # 1. Total income aggregated per month
    income_rows = db.execute(
        f"""
        SELECT month, COALESCE(SUM(amount_paise), 0) AS total_income
        FROM incomes
        WHERE user_id = ? AND month IN ({placeholders})
        GROUP BY month
        """,
        [user_id, *month_list]
    ).fetchall()
    income_map = {row["month"]: int(row["total_income"]) for row in income_rows}

    # 2. Daily, Faltu, and Total expenses aggregated per month
    expense_rows = db.execute(
        f"""
        SELECT 
            month,
            COALESCE(SUM(CASE WHEN type = 'daily' THEN amount_paise ELSE 0 END), 0) AS total_daily,
            COALESCE(SUM(CASE WHEN type = 'faltu' THEN amount_paise ELSE 0 END), 0) AS total_faltu,
            COALESCE(SUM(amount_paise), 0) AS total_expenses
        FROM expenses
        WHERE user_id = ? AND month IN ({placeholders})
        GROUP BY month
        """,
        [user_id, *month_list]
    ).fetchall()
    expense_map = {
        row["month"]: {
            "daily": int(row["total_daily"]),
            "faltu": int(row["total_faltu"]),
            "total": int(row["total_expenses"])
        }
        for row in expense_rows
    }

    # 3. Assemble chronological history (oldest to newest)
    history = []
    for m in month_list:
        inc_paise = income_map.get(m, 0)
        exp_data = expense_map.get(m, {"daily": 0, "faltu": 0, "total": 0})
        daily_paise = exp_data["daily"]
        faltu_paise = exp_data["faltu"]
        total_exp_paise = exp_data["total"]
        balance_paise = inc_paise - total_exp_paise

        history.append({
            "month": m,
            "income_inr": paise_to_inr(inc_paise),
            "daily_inr": paise_to_inr(daily_paise),
            "faltu_inr": paise_to_inr(faltu_paise),
            "total_expense_inr": paise_to_inr(total_exp_paise),
            "balance_inr": paise_to_inr(balance_paise)
        })

    return history

