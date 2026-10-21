"""
services/insights_service.py — Phase 3 Pure Calculation Services
- (A) "What if I had saved it" Simulator (SIP-style compound interest projection)
- (B) Month-End Balance Prediction
- (C) Smart Insights Summary (Rule-based actionable feedback)
- (D) Weekly Financial Report

Rules:
- Parameterized SQL only.
- user_id first in every function.
- utils/clock.py (today_local / now_utc) for current time and timezone handling.
- Decimal / integer paise for all financial math.
- Zero changes to tables or schema.
- Safe against division by zero and empty dataset crashes.
"""

import calendar
import re
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from datetime import datetime, date, timedelta, timezone

from database.db import get_db
from utils.clock import now_utc, today_local, to_local_date
from utils.helpers import paise_to_inr, inr_to_paise, validate_month

DATE_REGEX = re.compile(r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$")


def _validate_date_str(date_str: str) -> str:
    """Validates calendar-strict YYYY-MM-DD format."""
    if not date_str or not isinstance(date_str, str):
        raise ValueError("A valid date string in 'YYYY-MM-DD' format is required.")
    clean = date_str.strip()
    if not DATE_REGEX.match(clean):
        raise ValueError(f"Invalid date '{date_str}'. Expected format is 'YYYY-MM-DD'.")
    try:
        datetime.strptime(clean, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"Invalid calendar date '{date_str}'.")
    return clean


def calculate_sip_future_value(monthly_investment: Decimal, annual_return_percent: Decimal, months: int) -> Decimal:
    """
    SIP compound interest formula:
    FV = P * (((1 + r)^n - 1) / r) * (1 + r)
    where:
      P = monthly investment
      r = annual_return_percent / 12 / 100
      n = months

    If r == 0: FV = P * n
    """
    if months <= 0 or monthly_investment <= 0:
        return Decimal("0.00")

    if annual_return_percent == Decimal("0"):
        return (monthly_investment * Decimal(months)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    r = annual_return_percent / Decimal("1200")
    one_plus_r = Decimal("1") + r
    fv = monthly_investment * (((one_plus_r ** months) - Decimal("1")) / r) * one_plus_r
    return fv.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def get_savings_simulator(user_id: int, month: str, annual_return: float = 12.0) -> dict:
    """
    (A) "What if I had saved it" simulator:
    Takes the faltu total of the selected month as the monthly saving amount.
    Returns 1, 3, and 5 year projections.

    Validations:
    - user_id must be a positive integer
    - month must be YYYY-MM
    - annual_return must be between 0 and 30 (percent)
    """
    if not user_id or not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user_id is required.")

    clean_month = validate_month(month)

    try:
        dec_return = Decimal(str(annual_return))
        if dec_return < Decimal("0") or dec_return > Decimal("30"):
            raise ValueError()
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("Annual return must be a number between 0 and 30 percent.")

    db = get_db()
    row = db.execute(
        """
        SELECT COALESCE(SUM(amount_paise), 0) AS faltu_paise
        FROM expenses
        WHERE user_id = ? AND month = ? AND type = 'faltu'
        """,
        (user_id, clean_month)
    ).fetchone()

    faltu_paise = int(row["faltu_paise"]) if row else 0
    monthly_investment_inr = paise_to_inr(faltu_paise)
    p_dec = Decimal(str(monthly_investment_inr))

    periods = [
        {"years": 1, "months": 12},
        {"years": 3, "months": 36},
        {"years": 5, "months": 60},
    ]

    projections = []
    has_faltu = (faltu_paise > 0)

    for p in periods:
        n = p["months"]
        invested_dec = (p_dec * Decimal(n)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        fv_dec = calculate_sip_future_value(p_dec, dec_return, n)
        gain_dec = (fv_dec - invested_dec).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        projections.append({
            "years": p["years"],
            "months": n,
            "total_invested_inr": float(invested_dec),
            "future_value_inr": float(fv_dec),
            "gain_inr": float(gain_dec),
        })

    return {
        "month": clean_month,
        "monthly_investment_inr": monthly_investment_inr,
        "annual_return_percent": float(dec_return),
        "has_faltu": has_faltu,
        "message": (
            "Projections calculated successfully."
            if has_faltu
            else "No faltu spending recorded for this month to simulate."
        ),
        "projections": projections,
        "disclaimer": "This is an illustration with an assumed return, not a guarantee and not financial advice."
    }


def get_month_prediction(user_id: int, month: str = None) -> dict:
    """
    (B) Month-End Balance Prediction:
    - Current month: calculates daily spend average so far, projects month-end expenses and balance.
    - Past month: returns final numbers with status 'completed'.
    - Future month: returns status 'future' with no prediction.

    Validations:
    - user_id must be a positive integer
    - month must be YYYY-MM (or None for current month)
    """
    if not user_id or not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user_id is required.")

    # Timezone-aware today via today_local()
    current_date = today_local()
    current_month_str = current_date.strftime("%Y-%m")
    target_month = validate_month(month) if month else current_month_str

    try:
        parts = target_month.split("-")
        target_year = int(parts[0])
        target_month_num = int(parts[1])
        _, days_in_month = calendar.monthrange(target_year, target_month_num)
    except Exception:
        raise ValueError("Invalid month format.")

    db = get_db()

    # Query total income and expenses for user and month
    income_row = db.execute(
        """
        SELECT COALESCE(SUM(amount_paise), 0) AS total_income
        FROM incomes
        WHERE user_id = ? AND month = ?
        """,
        (user_id, target_month)
    ).fetchone()
    total_income_paise = int(income_row["total_income"]) if income_row else 0
    total_income_inr = paise_to_inr(total_income_paise)

    expense_row = db.execute(
        """
        SELECT COALESCE(SUM(amount_paise), 0) AS total_expenses
        FROM expenses
        WHERE user_id = ? AND month = ?
        """,
        (user_id, target_month)
    ).fetchone()
    total_expenses_paise = int(expense_row["total_expenses"]) if expense_row else 0
    total_expenses_inr = paise_to_inr(total_expenses_paise)

    # 1. Past Month
    if target_month < current_month_str:
        actual_balance = round(total_income_inr - total_expenses_inr, 2)
        avg_spend = round(total_expenses_inr / days_in_month, 2) if days_in_month > 0 else 0.0
        return {
            "status": "completed",
            "month": target_month,
            "days_in_month": days_in_month,
            "days_elapsed": days_in_month,
            "days_remaining": 0,
            "confidence": "high",
            "total_income_inr": total_income_inr,
            "total_expense_inr": total_expenses_inr,
            "average_daily_spend_inr": avg_spend,
            "projected_expense_inr": total_expenses_inr,
            "projected_balance_inr": actual_balance,
            "safe_daily_budget_inr": 0.0,
            "will_overspend": (actual_balance < 0),
            "message": "This month has already ended."
        }

    # 2. Future Month
    if target_month > current_month_str:
        return {
            "status": "future",
            "month": target_month,
            "days_in_month": days_in_month,
            "days_elapsed": 0,
            "days_remaining": days_in_month,
            "confidence": None,
            "total_income_inr": total_income_inr,
            "total_expense_inr": total_expenses_inr,
            "average_daily_spend_inr": 0.0,
            "projected_expense_inr": None,
            "projected_balance_inr": None,
            "safe_daily_budget_inr": 0.0,
            "will_overspend": False,
            "message": "Future month. Prediction will be available when the month begins."
        }

    # 3. Current Month
    today_day = max(1, min(current_date.day, days_in_month))
    days_elapsed = today_day
    days_remaining = max(0, days_in_month - days_elapsed)

    # Confidence based on days elapsed
    if days_elapsed < 7:
        confidence = "low"
    elif days_elapsed <= 15:
        confidence = "medium"
    else:
        confidence = "high"

    # Daily spend average so far using Decimal
    exp_dec = Decimal(str(total_expenses_inr))
    inc_dec = Decimal(str(total_income_inr))
    days_elapsed_dec = Decimal(days_elapsed)
    days_in_month_dec = Decimal(days_in_month)

    avg_spend_dec = (exp_dec / days_elapsed_dec) if days_elapsed > 0 else Decimal("0.00")
    projected_expense_dec = (avg_spend_dec * days_in_month_dec).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    projected_balance_dec = (inc_dec - projected_expense_dec).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # Safe daily budget: (remaining balance / days_remaining, never negative)
    remaining_balance_dec = inc_dec - exp_dec
    if days_remaining > 0 and remaining_balance_dec > Decimal("0"):
        safe_daily_budget_dec = (remaining_balance_dec / Decimal(days_remaining)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    else:
        safe_daily_budget_dec = Decimal("0.00")

    will_overspend = bool(projected_balance_dec < Decimal("0"))

    return {
        "status": "current",
        "month": target_month,
        "days_in_month": days_in_month,
        "days_elapsed": days_elapsed,
        "days_remaining": days_remaining,
        "confidence": confidence,
        "total_income_inr": total_income_inr,
        "total_expense_inr": total_expenses_inr,
        "average_daily_spend_inr": float(avg_spend_dec.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        "projected_expense_inr": float(projected_expense_dec),
        "projected_balance_inr": float(projected_balance_dec),
        "safe_daily_budget_inr": float(safe_daily_budget_dec),
        "will_overspend": will_overspend,
        "message": (
            "Warning: projected to overspend by month end."
            if will_overspend
            else "Spending is within current projected balance."
        )
    }


def get_smart_insights(user_id: int, month: str = None) -> list:
    """
    (C) Smart Insights:
    Returns a list of up to 6 insight objects:
      { "code": str, "severity": "warning" | "good" | "info", "message": str }
    Sorted by severity (warning first).

    Rules:
    1. Faltu as percent of income (if income > 0 and faltu > 0)
    2. Faltu change compared with previous month (if prev month has faltu)
    3. Top faltu sub-category of the month with its share
    4. Faltu-free days count in the month
    5. Savings goal status (if goal exists)
    6. Faltu limit status (if limit exists)
    7. Money saved by dropped wishlist items (if any)
    """
    if not user_id or not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user_id is required.")

    current_date = today_local()
    current_month_str = current_date.strftime("%Y-%m")
    target_month = validate_month(month) if month else current_month_str

    try:
        parts = target_month.split("-")
        target_year = int(parts[0])
        target_month_num = int(parts[1])
        _, days_in_month = calendar.monthrange(target_year, target_month_num)
    except Exception:
        raise ValueError("Invalid month format.")

    db = get_db()
    insights = []

    # 1. Total income
    inc_row = db.execute(
        "SELECT COALESCE(SUM(amount_paise), 0) AS total_inc FROM incomes WHERE user_id = ? AND month = ?",
        (user_id, target_month)
    ).fetchone()
    total_inc_paise = int(inc_row["total_inc"]) if inc_row else 0

    # 2. Total expenses & faltu expenses
    exp_row = db.execute(
        """
        SELECT 
            COALESCE(SUM(amount_paise), 0) AS total_exp,
            COALESCE(SUM(CASE WHEN type = 'faltu' THEN amount_paise ELSE 0 END), 0) AS total_faltu
        FROM expenses
        WHERE user_id = ? AND month = ?
        """,
        (user_id, target_month)
    ).fetchone()
    total_exp_paise = int(exp_row["total_exp"]) if exp_row else 0
    total_faltu_paise = int(exp_row["total_faltu"]) if exp_row else 0

    # Rule 1: Faltu as % of income
    if total_inc_paise > 0 and total_faltu_paise > 0:
        pct = round((total_faltu_paise / total_inc_paise) * 100, 1)
        if pct >= 30.0:
            insights.append({
                "code": "FALTU_INCOME_HIGH",
                "severity": "warning",
                "message": f"Faltu spending consumed {pct}% of your income this month."
            })
        elif pct <= 10.0:
            insights.append({
                "code": "FALTU_INCOME_LOW",
                "severity": "good",
                "message": f"Only {pct}% of your income went to faltu spending this month."
            })
        else:
            insights.append({
                "code": "FALTU_INCOME_MODERATE",
                "severity": "info",
                "message": f"Faltu spending accounted for {pct}% of your income this month."
            })

    # Rule 2: Faltu change compared with previous month
    prev_year = target_year if target_month_num > 1 else target_year - 1
    prev_m_num = target_month_num - 1 if target_month_num > 1 else 12
    prev_month_str = f"{prev_year:04d}-{prev_m_num:02d}"

    prev_row = db.execute(
        """
        SELECT COALESCE(SUM(amount_paise), 0) AS prev_faltu
        FROM expenses
        WHERE user_id = ? AND month = ? AND type = 'faltu'
        """,
        (user_id, prev_month_str)
    ).fetchone()
    prev_faltu_paise = int(prev_row["prev_faltu"]) if prev_row else 0

    if prev_faltu_paise > 0:
        diff_paise = total_faltu_paise - prev_faltu_paise
        diff_inr = paise_to_inr(abs(diff_paise))
        pct_change = round(((total_faltu_paise - prev_faltu_paise) / prev_faltu_paise) * 100, 1)

        if diff_paise > 0:
            insights.append({
                "code": "FALTU_INCREASED",
                "severity": "warning",
                "message": f"Faltu spending increased by {pct_change}% (₹{diff_inr:,.2f}) compared with last month."
            })
        elif diff_paise < 0:
            insights.append({
                "code": "FALTU_DECREASED",
                "severity": "good",
                "message": f"Faltu spending decreased by {abs(pct_change)}% (₹{diff_inr:,.2f}) compared with last month."
            })
        else:
            insights.append({
                "code": "FALTU_UNCHANGED",
                "severity": "info",
                "message": "Faltu spending was unchanged compared with last month."
            })

    # Rule 3: Top faltu sub-category of the month with its share
    if total_faltu_paise > 0:
        top_cat_row = db.execute(
            """
            SELECT sub_category, SUM(amount_paise) AS sub_paise
            FROM expenses
            WHERE user_id = ? AND month = ? AND type = 'faltu'
            GROUP BY sub_category
            ORDER BY sub_paise DESC
            LIMIT 1
            """,
            (user_id, target_month)
        ).fetchone()

        if top_cat_row:
            top_paise = int(top_cat_row["sub_paise"])
            top_name = top_cat_row["sub_category"]
            share_pct = round((top_paise / total_faltu_paise) * 100, 1)
            top_inr = paise_to_inr(top_paise)
            insights.append({
                "code": "TOP_FALTU_CATEGORY",
                "severity": "warning" if share_pct >= 50.0 else "info",
                "message": f"{top_name} was your biggest faltu spend at ₹{top_inr:,.2f} ({share_pct}% of all faltu spending)."
            })

    # Rule 4: Faltu-free days count in the month
    if target_month == current_month_str:
        days_considered = max(1, min(current_date.day, days_in_month))
    elif target_month < current_month_str:
        days_considered = days_in_month
    else:
        days_considered = 0

    if days_considered > 0:
        days_with_faltu_row = db.execute(
            """
            SELECT COUNT(DISTINCT date) AS faltu_days
            FROM expenses
            WHERE user_id = ? AND month = ? AND type = 'faltu'
            """,
            (user_id, target_month)
        ).fetchone()
        faltu_days_count = int(days_with_faltu_row["faltu_days"]) if days_with_faltu_row else 0
        free_days = max(0, days_considered - faltu_days_count)

        insights.append({
            "code": "FALTU_FREE_DAYS",
            "severity": "good" if free_days >= (days_considered // 2) else "info",
            "message": f"You had {free_days} faltu-free day{'s' if free_days != 1 else ''} this month."
        })

    # Rule 5: Savings goal on track or behind (if a goal exists)
    goal_row = db.execute(
        "SELECT target_amount_paise, title FROM savings_goals WHERE user_id = ? AND month = ?",
        (user_id, target_month)
    ).fetchone()

    if goal_row:
        target_paise = int(goal_row["target_amount_paise"])
        target_inr = paise_to_inr(target_paise)
        balance_paise = total_inc_paise - total_exp_paise
        balance_inr = paise_to_inr(balance_paise)

        if balance_paise >= target_paise:
            insights.append({
                "code": "SAVINGS_GOAL_ACHIEVED",
                "severity": "good",
                "message": f"Savings goal of ₹{target_inr:,.2f} achieved! Current balance is ₹{balance_inr:,.2f}."
            })
        elif balance_paise > 0:
            pct_achieved = round((balance_paise / target_paise) * 100, 1)
            insights.append({
                "code": "SAVINGS_GOAL_PROGRESS",
                "severity": "warning" if pct_achieved < 50.0 else "info",
                "message": f"Savings goal is at {pct_achieved}% (₹{balance_inr:,.2f} of ₹{target_inr:,.2f})."
            })
        else:
            insights.append({
                "code": "SAVINGS_GOAL_DEFICIT",
                "severity": "warning",
                "message": f"Savings goal of ₹{target_inr:,.2f} is behind due to negative monthly balance."
            })

    # Rule 6: Faltu limit status (if a limit exists)
    budget_row = db.execute(
        "SELECT faltu_limit_paise FROM monthly_budgets WHERE user_id = ? AND month = ?",
        (user_id, target_month)
    ).fetchone()

    if budget_row:
        limit_paise = int(budget_row["faltu_limit_paise"])
        limit_inr = paise_to_inr(limit_paise)
        faltu_inr = paise_to_inr(total_faltu_paise)

        if total_faltu_paise > limit_paise:
            over_inr = paise_to_inr(total_faltu_paise - limit_paise)
            insights.append({
                "code": "FALTU_LIMIT_EXCEEDED",
                "severity": "warning",
                "message": f"You exceeded your faltu limit of ₹{limit_inr:,.2f} by ₹{over_inr:,.2f}."
            })
        elif limit_paise > 0 and total_faltu_paise >= int(limit_paise * 0.8):
            pct_used = round((total_faltu_paise / limit_paise) * 100, 1)
            insights.append({
                "code": "FALTU_LIMIT_NEAR",
                "severity": "warning",
                "message": f"You have used {pct_used}% of your faltu limit (₹{faltu_inr:,.2f} of ₹{limit_inr:,.2f})."
            })
        else:
            insights.append({
                "code": "FALTU_LIMIT_SAFE",
                "severity": "good",
                "message": f"You are within your faltu limit (₹{faltu_inr:,.2f} of ₹{limit_inr:,.2f})."
            })

    # Rule 7: Money saved by dropped wishlist items
    dropped_row = db.execute(
        """
        SELECT COALESCE(SUM(estimated_amount_paise), 0) AS dropped_paise, COUNT(id) AS dropped_count
        FROM wishlist_items
        WHERE user_id = ? AND status = 'dropped' AND strftime('%Y-%m', created_at) = ?
        """,
        (user_id, target_month)
    ).fetchone()

    if dropped_row and int(dropped_row["dropped_paise"]) > 0:
        dropped_paise = int(dropped_row["dropped_paise"])
        dropped_count = int(dropped_row["dropped_count"])
        saved_inr = paise_to_inr(dropped_paise)
        insights.append({
            "code": "WISHLIST_DROPPED_SAVINGS",
            "severity": "good",
            "message": f"You saved ₹{saved_inr:,.2f} by dropping {dropped_count} impulse item{'s' if dropped_count != 1 else ''} from your wishlist."
        })

    # Sort by severity (warning first, then good, then info)
    severity_order = {"warning": 0, "good": 1, "info": 2}
    insights.sort(key=lambda item: severity_order.get(item["severity"], 3))

    # Never produce more than 6 insights
    return insights[:6]


def get_weekly_report(user_id: int, week_start: str = None) -> dict:
    """
    (D) Weekly Report:
    Calculates a 7-day spending overview.
    Default is the last 7 days ending today_local().

    Validations:
    - user_id must be a positive integer
    - week_start if provided must be YYYY-MM-DD (calendar strict)
    """
    if not user_id or not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user_id is required.")

    if week_start is not None and str(week_start).strip():
        clean_start = _validate_date_str(str(week_start))
        start_dt = datetime.strptime(clean_start, "%Y-%m-%d").date()
        end_dt = start_dt + timedelta(days=6)
    else:
        end_dt = today_local()
        start_dt = end_dt - timedelta(days=6)

    start_date_str = start_dt.isoformat()
    end_date_str = end_dt.isoformat()

    db = get_db()

    # 1. Period spending totals
    spend_row = db.execute(
        """
        SELECT
            COALESCE(SUM(amount_paise), 0) AS total_paise,
            COALESCE(SUM(CASE WHEN type = 'daily' THEN amount_paise ELSE 0 END), 0) AS daily_paise,
            COALESCE(SUM(CASE WHEN type = 'faltu' THEN amount_paise ELSE 0 END), 0) AS faltu_paise
        FROM expenses
        WHERE user_id = ? AND date >= ? AND date <= ?
        """,
        (user_id, start_date_str, end_date_str)
    ).fetchone()

    total_spent_paise = int(spend_row["total_paise"]) if spend_row else 0
    daily_paise = int(spend_row["daily_paise"]) if spend_row else 0
    faltu_paise = int(spend_row["faltu_paise"]) if spend_row else 0

    # 2. Top 3 sub-categories
    cat_rows = db.execute(
        """
        SELECT sub_category, SUM(amount_paise) AS cat_paise
        FROM expenses
        WHERE user_id = ? AND date >= ? AND date <= ?
        GROUP BY sub_category
        ORDER BY cat_paise DESC
        LIMIT 3
        """,
        (user_id, start_date_str, end_date_str)
    ).fetchall()

    top_3_sub_categories = [
        {
            "sub_category": r["sub_category"],
            "amount_inr": paise_to_inr(int(r["cat_paise"]))
        }
        for r in cat_rows
    ]

    # 3. Highest spending day
    highest_day_row = db.execute(
        """
        SELECT date, SUM(amount_paise) AS day_paise
        FROM expenses
        WHERE user_id = ? AND date >= ? AND date <= ?
        GROUP BY date
        ORDER BY day_paise DESC, date ASC
        LIMIT 1
        """,
        (user_id, start_date_str, end_date_str)
    ).fetchone()

    if highest_day_row and int(highest_day_row["day_paise"]) > 0:
        highest_spending_day = {
            "date": highest_day_row["date"],
            "amount_inr": paise_to_inr(int(highest_day_row["day_paise"]))
        }
    else:
        highest_spending_day = None

    # 4. No-spend days count (in this 7-day period)
    active_days_row = db.execute(
        """
        SELECT COUNT(DISTINCT date) AS active_days
        FROM expenses
        WHERE user_id = ? AND date >= ? AND date <= ?
        """,
        (user_id, start_date_str, end_date_str)
    ).fetchone()
    active_days = int(active_days_row["active_days"]) if active_days_row else 0
    no_spend_days = max(0, 7 - active_days)

    # 5. Previous 7 days comparison
    prev_start_dt = start_dt - timedelta(days=7)
    prev_end_dt = start_dt - timedelta(days=1)
    prev_start_str = prev_start_dt.isoformat()
    prev_end_str = prev_end_dt.isoformat()

    prev_spend_row = db.execute(
        """
        SELECT COALESCE(SUM(amount_paise), 0) AS prev_total_paise
        FROM expenses
        WHERE user_id = ? AND date >= ? AND date <= ?
        """,
        (user_id, prev_start_str, prev_end_str)
    ).fetchone()
    prev_total_paise = int(prev_spend_row["prev_total_paise"]) if prev_spend_row else 0

    if prev_total_paise > 0:
        change_versus_previous_week_percent = round(
            ((total_spent_paise - prev_total_paise) / prev_total_paise) * 100, 1
        )
    else:
        change_versus_previous_week_percent = None

    # 6. Income received in period
    inc_row = db.execute(
        """
        SELECT COALESCE(SUM(amount_paise), 0) AS income_paise
        FROM incomes
        WHERE user_id = ? AND date >= ? AND date <= ?
        """,
        (user_id, start_date_str, end_date_str)
    ).fetchone()
    income_received_paise = int(inc_row["income_paise"]) if inc_row else 0

    return {
        "start_date": start_date_str,
        "end_date": end_date_str,
        "total_spent_inr": paise_to_inr(total_spent_paise),
        "daily_inr": paise_to_inr(daily_paise),
        "faltu_inr": paise_to_inr(faltu_paise),
        "top_3_sub_categories": top_3_sub_categories,
        "highest_spending_day": highest_spending_day,
        "no_spend_days": no_spend_days,
        "change_versus_previous_week_percent": change_versus_previous_week_percent,
        "income_received_inr": paise_to_inr(income_received_paise)
    }
