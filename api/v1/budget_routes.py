from flask import Blueprint, request

from utils.auth import get_current_user_id, login_required
from utils.responses import success_response, error_response
from utils.helpers import validate_month
from services.budget_service import get_faltu_limit, set_faltu_limit

budget_bp = Blueprint("budgets", __name__, url_prefix="/budgets")

@budget_bp.route("/<string:month>", methods=["GET"], strict_slashes=False)
@login_required
def get_monthly_budget(month: str):
    """
    Retrieves the configured faltu limit budget for the specified month ('YYYY-MM').
    Returns 200 with data=None if no limit is configured.
    """
    try:
        user_id = get_current_user_id()
        clean_month = validate_month(month)
        budget = get_faltu_limit(user_id=user_id, month=clean_month)
        msg = f"Budget limit retrieved for {clean_month}" if budget else f"No limit configured for {clean_month}"
        return success_response(data=budget, message=msg, status_code=200)
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception:
        return error_response("An unexpected server error occurred.", 500)

@budget_bp.route("/<string:month>", methods=["PUT"], strict_slashes=False)
@login_required
def update_monthly_budget(month: str):
    """
    Sets or updates the monthly faltu limit budget.
    Expected JSON body: { "faltu_limit_inr": <number >= 0> }
    """
    if not request.is_json:
        return error_response("Request body must be valid JSON.", 400)

    data = request.get_json(silent=True)
    if data is None:
        return error_response("Request body cannot be empty or invalid JSON.", 400)

    try:
        user_id = get_current_user_id()
        clean_month = validate_month(month)
        
        if "faltu_limit_inr" not in data or data["faltu_limit_inr"] is None:
            return error_response("Field 'faltu_limit_inr' is required.", 400)

        faltu_limit_inr = data["faltu_limit_inr"]
        updated = set_faltu_limit(user_id=user_id, month=clean_month, amount_inr=faltu_limit_inr)
        return success_response(
            data=updated,
            message=f"Faltu spending limit for {clean_month} set to ₹{updated['faltu_limit_inr']:.2f}",
            status_code=200
        )
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception:
        return error_response("An unexpected server error occurred.", 500)
