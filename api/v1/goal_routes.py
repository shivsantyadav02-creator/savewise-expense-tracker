from flask import Blueprint, request

from utils.auth import get_current_user_id, login_required
from utils.responses import success_response, error_response
from utils.helpers import validate_month
from services.goal_service import get_savings_goal, set_savings_goal

goal_bp = Blueprint("goals", __name__, url_prefix="/goals")

@goal_bp.route("/<string:month>", methods=["GET"], strict_slashes=False)
@login_required
def get_monthly_goal(month: str):
    """
    Retrieves the savings goal for the specified month ('YYYY-MM').
    Returns 200 with data=None if no goal is configured.
    """
    try:
        user_id = get_current_user_id()
        clean_month = validate_month(month)
        goal = get_savings_goal(user_id=user_id, month=clean_month)
        msg = f"Savings goal retrieved for {clean_month}" if goal else f"No goal configured for {clean_month}"
        return success_response(data=goal, message=msg, status_code=200)
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception:
        return error_response("An unexpected server error occurred.", 500)

@goal_bp.route("/<string:month>", methods=["PUT"], strict_slashes=False)
@login_required
def update_monthly_goal(month: str):
    """
    Sets or updates the monthly savings goal.
    Expected JSON body: { "target_inr": <number > 0>, "title"?: "<string>" }
    """
    if not request.is_json:
        return error_response("Request body must be valid JSON.", 400)

    data = request.get_json(silent=True)
    if data is None:
        return error_response("Request body cannot be empty or invalid JSON.", 400)

    try:
        user_id = get_current_user_id()
        clean_month = validate_month(month)

        if "target_inr" not in data or data["target_inr"] is None:
            return error_response("Field 'target_inr' is required.", 400)

        target_inr = data["target_inr"]
        title = data.get("title", "")

        updated = set_savings_goal(
            user_id=user_id,
            month=clean_month,
            target_inr=target_inr,
            title=title
        )
        return success_response(
            data=updated,
            message=f"Savings goal for {clean_month} set to ₹{updated['target_inr']:.2f}",
            status_code=200
        )
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception:
        return error_response("An unexpected server error occurred.", 500)
