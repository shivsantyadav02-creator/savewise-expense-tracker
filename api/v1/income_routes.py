from datetime import datetime
from flask import Blueprint, request

from utils.auth import get_current_user_id
from utils.responses import success_response, error_response
from services.income_service import (
    create_income,
    get_incomes,
    get_income_by_id,
    update_income,
    delete_income
)

income_bp = Blueprint("incomes", __name__, url_prefix="/incomes")

@income_bp.route("", methods=["GET"], strict_slashes=False)
def list_incomes():
    """
    List all incomes for the current user.
    Supports ?month=YYYY-MM query parameter (defaults to current month if omitted).
    """
    try:
        user_id = get_current_user_id()
        month = request.args.get("month", "").strip() or datetime.now().strftime("%Y-%m")
        incomes = get_incomes(user_id=user_id, month=month)
        return success_response(
            data=incomes,
            message=f"Incomes retrieved successfully for month {month}",
            status_code=200
        )
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception:
        return error_response("An unexpected server error occurred.", 500)

@income_bp.route("", methods=["POST"], strict_slashes=False)
def add_income():
    """
    Creates a new income record.
    Expected JSON body: { amount_inr, source, date, note? }
    """
    if not request.is_json:
        return error_response("Request body must be valid JSON.", 400)

    data = request.get_json(silent=True)
    if data is None:
        return error_response("Request body cannot be empty or invalid JSON.", 400)

    try:
        user_id = get_current_user_id()
        amount_inr = data.get("amount_inr")
        source = data.get("source")
        date = data.get("date")
        note = data.get("note", "")

        new_income = create_income(
            user_id=user_id,
            amount_inr=amount_inr,
            source=source,
            date=date,
            note=note
        )
        return success_response(
            data=new_income,
            message="Income record created successfully.",
            status_code=201
        )
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception:
        return error_response("An unexpected server error occurred.", 500)

@income_bp.route("/<int:income_id>", methods=["GET"], strict_slashes=False)
def get_income(income_id: int):
    """
    Fetches a single income record by its ID.
    Returns 404 if not found or unauthorized.
    """
    try:
        user_id = get_current_user_id()
        income = get_income_by_id(user_id=user_id, income_id=income_id)
        if not income:
            return error_response(f"Income with ID {income_id} not found.", 404)
        return success_response(
            data=income,
            message="Income record retrieved successfully.",
            status_code=200
        )
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception:
        return error_response("An unexpected server error occurred.", 500)

@income_bp.route("/<int:income_id>", methods=["PUT"], strict_slashes=False)
def modify_income(income_id: int):
    """
    Updates an existing income record.
    Expected JSON body with optional fields: { amount_inr?, source?, date?, note? }
    """
    user_id = get_current_user_id()
    existing = get_income_by_id(user_id=user_id, income_id=income_id)
    if not existing:
        return error_response(f"Income with ID {income_id} not found.", 404)

    if not request.is_json:
        return error_response("Request body must be valid JSON.", 400)

    data = request.get_json(silent=True)
    if data is None:
        return error_response("Request body cannot be empty or invalid JSON.", 400)

    try:
        updated = update_income(
            user_id=user_id,
            income_id=income_id,
            amount_inr=data.get("amount_inr"),
            source=data.get("source"),
            date=data.get("date"),
            note=data.get("note")
        )
        return success_response(
            data=updated,
            message="Income record updated successfully.",
            status_code=200
        )
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception:
        return error_response("An unexpected server error occurred.", 500)

@income_bp.route("/<int:income_id>", methods=["DELETE"], strict_slashes=False)
def remove_income(income_id: int):
    """
    Deletes an income record owned by current user.
    Returns 404 if not found.
    """
    try:
        user_id = get_current_user_id()
        existing = get_income_by_id(user_id=user_id, income_id=income_id)
        if not existing:
            return error_response(f"Income with ID {income_id} not found.", 404)

        delete_income(user_id=user_id, income_id=income_id)
        return success_response(
            data=None,
            message="Income record deleted successfully.",
            status_code=200
        )
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception:
        return error_response("An unexpected server error occurred.", 500)
