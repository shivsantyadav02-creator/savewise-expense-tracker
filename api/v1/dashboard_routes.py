from datetime import datetime
from flask import Blueprint, request

from utils.auth import get_current_user_id, login_required
from utils.responses import success_response, error_response
from utils.helpers import validate_month
from utils.clock import today_local
from services.dashboard_service import get_monthly_summary, get_monthly_history

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")

@dashboard_bp.route("/summary", methods=["GET"], strict_slashes=False)
@login_required
def dashboard_summary():
    """
    Retrieves the monthly financial summary for the current user.
    Supports ?month=YYYY-MM query parameter (defaults to current month if omitted).
    Returns total income, daily expenses, faltu expenses, balance, and faltu percentages.
    """
    try:
        user_id = get_current_user_id()
        raw_month = request.args.get("month", "").strip()
        month = validate_month(raw_month) if raw_month else today_local().strftime("%Y-%m")
        summary = get_monthly_summary(user_id=user_id, month=month)
        return success_response(
            data=summary,
            message=f"Dashboard summary retrieved successfully for {month}",
            status_code=200
        )
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception:
        return error_response("An unexpected server error occurred.", 500)

@dashboard_bp.route("/history", methods=["GET"], strict_slashes=False)
@login_required
def dashboard_history():
    """
    Retrieves the month-wise financial history for the last N months (default 6, max 24).
    Supports query parameters:
      - ?months=N (1 <= N <= 24, default 6)
      - ?month=YYYY-MM (optional reference/end month, defaults to current month)
    """
    try:
        user_id = get_current_user_id()

        # Parse and strictly validate 'months'
        raw_months = request.args.get("months")
        if raw_months is None or raw_months.strip() == "":
            months = 6
        else:
            cleaned = raw_months.strip()
            # Reject floats like "6.5" or negative formatted numbers with decimals
            if "." in cleaned:
                return error_response("Parameter 'months' must be an integer between 1 and 24.", 400)
            try:
                months = int(cleaned)
            except ValueError:
                return error_response("Parameter 'months' must be an integer between 1 and 24.", 400)

        # Optional end month
        raw_month = request.args.get("month", "").strip()
        end_month = validate_month(raw_month) if raw_month else None

        history = get_monthly_history(user_id=user_id, months=months, end_month=end_month)
        return success_response(
            data=history,
            message=f"Monthly history retrieved successfully for the last {months} months",
            status_code=200
        )
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception:
        return error_response("An unexpected server error occurred.", 500)
