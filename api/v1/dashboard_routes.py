from datetime import datetime
from flask import Blueprint, request

from utils.auth import get_current_user_id
from utils.responses import success_response, error_response
from services.dashboard_service import get_monthly_summary

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")

@dashboard_bp.route("/summary", methods=["GET"], strict_slashes=False)
def dashboard_summary():
    """
    Retrieves the monthly financial summary for the current user.
    Supports ?month=YYYY-MM query parameter (defaults to current month if omitted).
    Returns total income, daily expenses, faltu expenses, balance, and faltu percentages.
    """
    try:
        user_id = get_current_user_id()
        month = request.args.get("month", "").strip() or datetime.now().strftime("%Y-%m")
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
