from flask import Blueprint, request

from utils.auth import get_current_user_id, login_required
from utils.responses import success_response, error_response
from services.preset_service import (
    create_preset,
    get_presets,
    get_preset_by_id,
    update_preset,
    delete_preset,
    use_preset
)

preset_bp = Blueprint("presets", __name__, url_prefix="/presets")

@preset_bp.route("", methods=["GET"], strict_slashes=False)
@login_required
def list_presets():
    """
    List all quick presets for the current user.
    """
    try:
        user_id = get_current_user_id()
        presets = get_presets(user_id=user_id)
        return success_response(
            data=presets,
            message="Presets retrieved successfully",
            status_code=200
        )
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception:
        return error_response("An unexpected server error occurred.", 500)

@preset_bp.route("", methods=["POST"], strict_slashes=False)
@login_required
def add_preset():
    """
    Creates a new quick preset.
    Expected JSON: { title, amount_inr, type (or preset_type), sub_category?, icon? }
    """
    if not request.is_json:
        return error_response("Request body must be valid JSON.", 400)

    data = request.get_json(silent=True)
    if data is None:
        return error_response("Request body cannot be empty or invalid JSON.", 400)

    try:
        user_id = get_current_user_id()
        title = data.get("title")
        amount_inr = data.get("amount_inr")
        preset_type = data.get("type") or data.get("preset_type")
        sub_category = data.get("sub_category", "")
        icon = data.get("icon", "⚡")

        if title is None or not str(title).strip():
            return error_response("Field 'title' is required.", 400)
        if amount_inr is None:
            return error_response("Field 'amount_inr' is required.", 400)
        if preset_type is None:
            return error_response("Field 'type' is required ('daily' or 'faltu').", 400)

        new_preset = create_preset(
            user_id=user_id,
            title=title,
            amount_inr=amount_inr,
            preset_type=preset_type,
            sub_category=sub_category,
            icon=icon
        )
        return success_response(
            data=new_preset,
            message=f"Preset '{new_preset['title']}' created successfully",
            status_code=201
        )
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception:
        return error_response("An unexpected server error occurred.", 500)

@preset_bp.route("/<int:preset_id>", methods=["GET"], strict_slashes=False)
@login_required
def get_single_preset(preset_id: int):
    """
    Retrieves a single preset by ID.
    """
    try:
        user_id = get_current_user_id()
        preset = get_preset_by_id(user_id=user_id, preset_id=preset_id)
        if not preset:
            return error_response("Preset not found.", 404)
        return success_response(data=preset, message="Preset retrieved successfully", status_code=200)
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception:
        return error_response("An unexpected server error occurred.", 500)

@preset_bp.route("/<int:preset_id>", methods=["PUT"], strict_slashes=False)
@login_required
def edit_preset(preset_id: int):
    """
    Updates an existing preset.
    """
    if not request.is_json:
        return error_response("Request body must be valid JSON.", 400)

    data = request.get_json(silent=True)
    if data is None:
        return error_response("Request body cannot be empty or invalid JSON.", 400)

    try:
        user_id = get_current_user_id()
        title = data.get("title")
        amount_inr = data.get("amount_inr")
        preset_type = data.get("type") or data.get("preset_type")
        sub_category = data.get("sub_category")
        icon = data.get("icon")

        updated = update_preset(
            user_id=user_id,
            preset_id=preset_id,
            title=title,
            amount_inr=amount_inr,
            preset_type=preset_type,
            sub_category=sub_category,
            icon=icon
        )
        return success_response(data=updated, message="Preset updated successfully", status_code=200)
    except ValueError as e:
        msg = str(e)
        code = 404 if "not found" in msg.lower() else 400
        return error_response(msg, code)
    except Exception:
        return error_response("An unexpected server error occurred.", 500)

@preset_bp.route("/<int:preset_id>", methods=["DELETE"], strict_slashes=False)
@login_required
def remove_preset(preset_id: int):
    """
    Deletes a preset by ID.
    """
    try:
        user_id = get_current_user_id()
        delete_preset(user_id=user_id, preset_id=preset_id)
        return success_response(data=None, message="Preset deleted successfully", status_code=200)
    except ValueError as e:
        msg = str(e)
        code = 404 if "not found" in msg.lower() else 400
        return error_response(msg, code)
    except Exception:
        return error_response("An unexpected server error occurred.", 500)

@preset_bp.route("/<int:preset_id>/use", methods=["POST"], strict_slashes=False)
@login_required
def use_single_preset(preset_id: int):
    """
    Quick-adds an expense from the preset using today's server date.
    Returns 201 with the created expense.
    """
    try:
        user_id = get_current_user_id()
        expense = use_preset(user_id=user_id, preset_id=preset_id)
        return success_response(
            data=expense,
            message=f"Added {expense['type'].title()} expense of ₹{expense['amount_inr']:.2f}",
            status_code=201
        )
    except ValueError as e:
        msg = str(e)
        code = 404 if "not found" in msg.lower() else 400
        return error_response(msg, code)
    except Exception:
        return error_response("An unexpected server error occurred.", 500)
