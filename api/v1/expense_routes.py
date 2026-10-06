from datetime import datetime
from flask import Blueprint, request

from utils.auth import get_current_user_id
from utils.responses import success_response, error_response
from services.expense_service import (
    create_expense,
    get_expenses,
    get_expense_by_id,
    update_expense,
    delete_expense
)

expense_bp = Blueprint("expenses", __name__, url_prefix="/expenses")

@expense_bp.route("", methods=["GET"], strict_slashes=False)
def list_expenses():
    """
    List all expenses for the current user.
    Supports query parameters:
      - ?month=YYYY-MM (defaults to current month if omitted)
      - ?type=daily|faltu|all (optional filter)
    """
    try:
        user_id = get_current_user_id()
        month = request.args.get("month", "").strip() or datetime.now().strftime("%Y-%m")
        expense_type = request.args.get("type", "").strip() or None

        expenses = get_expenses(user_id=user_id, month=month, expense_type=expense_type)
        return success_response(
            data=expenses,
            message=f"Expenses retrieved successfully for month {month}",
            status_code=200
        )
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception:
        return error_response("An unexpected server error occurred.", 500)

@expense_bp.route("", methods=["POST"], strict_slashes=False)
def add_expense():
    """
    Creates a new expense record (daily or faltu).
    Expected JSON body: { amount_inr, type (or expense_type), sub_category, date, note?, wishlist_item_id? }
    """
    if not request.is_json:
        return error_response("Request body must be valid JSON.", 400)

    data = request.get_json(silent=True)
    if data is None:
        return error_response("Request body cannot be empty or invalid JSON.", 400)

    try:
        user_id = get_current_user_id()
        amount_inr = data.get("amount_inr")
        expense_type = data.get("type") or data.get("expense_type")
        sub_category = data.get("sub_category")
        date = data.get("date")
        note = data.get("note", "")
        wishlist_item_id = data.get("wishlist_item_id")

        new_expense = create_expense(
            user_id=user_id,
            amount_inr=amount_inr,
            expense_type=expense_type,
            sub_category=sub_category,
            date=date,
            note=note,
            wishlist_item_id=wishlist_item_id
        )
        return success_response(
            data=new_expense,
            message="Expense record created successfully.",
            status_code=201
        )
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception:
        return error_response("An unexpected server error occurred.", 500)

@expense_bp.route("/<int:expense_id>", methods=["GET"], strict_slashes=False)
def get_expense(expense_id: int):
    """
    Fetches a single expense record by its ID.
    Returns 404 if not found or unauthorized.
    """
    try:
        user_id = get_current_user_id()
        expense = get_expense_by_id(user_id=user_id, expense_id=expense_id)
        if not expense:
            return error_response(f"Expense with ID {expense_id} not found.", 404)
        return success_response(
            data=expense,
            message="Expense record retrieved successfully.",
            status_code=200
        )
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception:
        return error_response("An unexpected server error occurred.", 500)

@expense_bp.route("/<int:expense_id>", methods=["PUT"], strict_slashes=False)
def modify_expense(expense_id: int):
    """
    Updates an existing expense record.
    Expected JSON body: { amount_inr?, type?, sub_category?, date?, note? }
    """
    user_id = get_current_user_id()
    existing = get_expense_by_id(user_id=user_id, expense_id=expense_id)
    if not existing:
        return error_response(f"Expense with ID {expense_id} not found.", 404)

    if not request.is_json:
        return error_response("Request body must be valid JSON.", 400)

    data = request.get_json(silent=True)
    if data is None:
        return error_response("Request body cannot be empty or invalid JSON.", 400)

    try:
        expense_type = data.get("type") or data.get("expense_type")
        updated = update_expense(
            user_id=user_id,
            expense_id=expense_id,
            amount_inr=data.get("amount_inr"),
            expense_type=expense_type,
            sub_category=data.get("sub_category"),
            date=data.get("date"),
            note=data.get("note")
        )
        return success_response(
            data=updated,
            message="Expense record updated successfully.",
            status_code=200
        )
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception:
        return error_response("An unexpected server error occurred.", 500)

@expense_bp.route("/<int:expense_id>", methods=["DELETE"], strict_slashes=False)
def remove_expense(expense_id: int):
    """
    Deletes an expense record owned by current user.
    Returns 404 if not found.
    """
    try:
        user_id = get_current_user_id()
        existing = get_expense_by_id(user_id=user_id, expense_id=expense_id)
        if not existing:
            return error_response(f"Expense with ID {expense_id} not found.", 404)

        delete_expense(user_id=user_id, expense_id=expense_id)
        return success_response(
            data=None,
            message="Expense record deleted successfully.",
            status_code=200
        )
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception:
        return error_response("An unexpected server error occurred.", 500)
