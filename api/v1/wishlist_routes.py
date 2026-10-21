from flask import Blueprint, request

from utils.auth import get_current_user_id, login_required
from utils.responses import success_response, error_response
from services.wishlist_service import (
    create_wishlist_item,
    get_wishlist_items,
    get_wishlist_item_by_id,
    update_wishlist_item,
    buy_wishlist_item,
    drop_wishlist_item,
    get_wishlist_summary
)

wishlist_bp = Blueprint("wishlist", __name__, url_prefix="/wishlist")

@wishlist_bp.route("", methods=["GET"], strict_slashes=False)
@login_required
def list_wishlist():
    """
    Retrieves wishlist items for the current user.
    Optional query parameter: ?status=waiting|bought|dropped|all (default: 'waiting').
    """
    try:
        user_id = get_current_user_id()
        status = request.args.get("status", "waiting").strip()
        items = get_wishlist_items(user_id=user_id, status=status)
        return success_response(data=items, message="Wishlist items retrieved successfully", status_code=200)
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception:
        return error_response("An unexpected server error occurred.", 500)

@wishlist_bp.route("/summary", methods=["GET"], strict_slashes=False)
@login_required
def wishlist_summary():
    """
    Retrieves statistics: items_dropped, amount_saved_inr, items_waiting.
    """
    try:
        user_id = get_current_user_id()
        summary = get_wishlist_summary(user_id=user_id)
        return success_response(data=summary, message="Wishlist summary retrieved successfully", status_code=200)
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception:
        return error_response("An unexpected server error occurred.", 500)

@wishlist_bp.route("", methods=["POST"], strict_slashes=False)
@login_required
def add_wishlist_item():
    """
    Creates a new wishlist item.
    Expected JSON: { item_name, estimated_amount_inr, sub_category? }
    """
    if not request.is_json:
        return error_response("Request body must be valid JSON.", 400)

    data = request.get_json(silent=True)
    if data is None:
        return error_response("Request body cannot be empty or invalid JSON.", 400)

    try:
        user_id = get_current_user_id()
        item_name = data.get("item_name")
        estimated_amount_inr = data.get("estimated_amount_inr")
        sub_category = data.get("sub_category", "Shopping")

        if item_name is None or not str(item_name).strip():
            return error_response("Field 'item_name' is required.", 400)
        if estimated_amount_inr is None:
            return error_response("Field 'estimated_amount_inr' is required.", 400)

        new_item = create_wishlist_item(
            user_id=user_id,
            item_name=item_name,
            estimated_amount_inr=estimated_amount_inr,
            sub_category=sub_category
        )
        return success_response(
            data=new_item,
            message=f"Added '{new_item['item_name']}' to 24-hour wait wishlist",
            status_code=201
        )
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception:
        return error_response("An unexpected server error occurred.", 500)

@wishlist_bp.route("/<int:item_id>", methods=["GET"], strict_slashes=False)
@login_required
def get_single_wishlist_item(item_id: int):
    """
    Retrieves a single wishlist item by ID.
    """
    try:
        user_id = get_current_user_id()
        item = get_wishlist_item_by_id(user_id=user_id, item_id=item_id)
        if not item:
            return error_response("Wishlist item not found.", 404)
        return success_response(data=item, message="Wishlist item retrieved successfully", status_code=200)
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception:
        return error_response("An unexpected server error occurred.", 500)

@wishlist_bp.route("/<int:item_id>", methods=["PUT"], strict_slashes=False)
@login_required
def edit_wishlist_item(item_id: int):
    """
    Edits an item's name or amount while in 'waiting' status.
    Client-sent unlock_at is ignored and cannot reset unlock_at.
    """
    if not request.is_json:
        return error_response("Request body must be valid JSON.", 400)

    data = request.get_json(silent=True)
    if data is None:
        return error_response("Request body cannot be empty or invalid JSON.", 400)

    try:
        user_id = get_current_user_id()
        item_name = data.get("item_name")
        estimated_amount_inr = data.get("estimated_amount_inr")
        sub_category = data.get("sub_category")

        updated = update_wishlist_item(
            user_id=user_id,
            item_id=item_id,
            item_name=item_name,
            estimated_amount_inr=estimated_amount_inr,
            sub_category=sub_category
        )
        return success_response(data=updated, message="Wishlist item updated successfully", status_code=200)
    except ValueError as e:
        msg = str(e)
        code = 404 if "not found" in msg.lower() else 400
        return error_response(msg, code)
    except Exception:
        return error_response("An unexpected server error occurred.", 500)

@wishlist_bp.route("/<int:item_id>/buy", methods=["POST"], strict_slashes=False)
@login_required
def buy_item(item_id: int):
    """
    Converts a waiting, unlocked wishlist item into a 'faltu' expense.
    """
    try:
        user_id = get_current_user_id()
        result = buy_wishlist_item(user_id=user_id, item_id=item_id)
        return success_response(
            data=result,
            message=f"Wishlist item bought and logged as expense (₹{result['amount_inr']:.2f})",
            status_code=200
        )
    except ValueError as e:
        msg = str(e)
        code = 404 if "not found" in msg.lower() else 400
        return error_response(msg, code)
    except Exception:
        return error_response("An unexpected server error occurred.", 500)

@wishlist_bp.route("/<int:item_id>/drop", methods=["POST"], strict_slashes=False)
@login_required
def drop_item(item_id: int):
    """
    Drops a waiting wishlist item.
    """
    try:
        user_id = get_current_user_id()
        result = drop_wishlist_item(user_id=user_id, item_id=item_id)
        return success_response(
            data=result,
            message=f"Dropped '{result['item_name']}'. Money saved!",
            status_code=200
        )
    except ValueError as e:
        msg = str(e)
        code = 404 if "not found" in msg.lower() else 400
        return error_response(msg, code)
    except Exception:
        return error_response("An unexpected server error occurred.", 500)
