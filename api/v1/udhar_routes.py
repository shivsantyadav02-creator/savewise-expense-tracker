"""
api/v1/udhar_routes.py — REST routes for the Udhar tracker.

Routes only: parse request → call service → return response.
No business logic, no SQL here.
"""

from flask import Blueprint, request

from utils.auth import get_current_user_id, login_required
from utils.responses import success_response, error_response
from services.udhar_service import (
    create_udhar,
    get_udhar_list,
    get_udhar_by_id,
    update_udhar,
    settle_udhar,
    reopen_udhar,
    delete_udhar,
    get_udhar_summary,
)

udhar_bp = Blueprint("udhar", __name__, url_prefix="/udhar")


# ── GET /api/v1/udhar?status=pending|settled|all&type=lent|borrowed ──────────
@udhar_bp.route("", methods=["GET"])
@login_required
def list_udhar():
    user_id = get_current_user_id()
    status = request.args.get("status", "pending")
    udhar_type = request.args.get("type", None)

    try:
        items = get_udhar_list(user_id, status=status, udhar_type=udhar_type)
    except ValueError as e:
        return error_response(str(e), 400)

    return success_response(items)


# ── POST /api/v1/udhar ───────────────────────────────────────────────────────
@udhar_bp.route("", methods=["POST"])
@login_required
def add_udhar():
    user_id = get_current_user_id()
    body = request.get_json(silent=True) or {}

    person_name = body.get("person_name")
    amount_inr = body.get("amount_inr")
    udhar_type = body.get("type")
    due_date = body.get("due_date")   # optional
    note = body.get("note")           # optional

    try:
        record = create_udhar(
            user_id,
            person_name=person_name,
            amount_inr=amount_inr,
            udhar_type=udhar_type,
            due_date=due_date,
            note=note
        )
    except ValueError as e:
        return error_response(str(e), 400)

    return success_response(record, "Udhar record created.", 201)


# ── GET /api/v1/udhar/summary ────────────────────────────────────────────────
# NOTE: this route MUST be registered before /<int:record_id> so Flask picks it first.
@udhar_bp.route("/summary", methods=["GET"])
@login_required
def udhar_summary():
    user_id = get_current_user_id()
    try:
        summary = get_udhar_summary(user_id)
    except ValueError as e:
        return error_response(str(e), 400)

    return success_response(summary)


# ── PUT /api/v1/udhar/<id> ───────────────────────────────────────────────────
@udhar_bp.route("/<int:record_id>", methods=["PUT"])
@login_required
def edit_udhar(record_id):
    user_id = get_current_user_id()
    body = request.get_json(silent=True) or {}

    try:
        updated = update_udhar(
            user_id,
            record_id,
            person_name=body.get("person_name"),
            amount_inr=body.get("amount_inr"),
            due_date=body.get("due_date"),
            note=body.get("note")
        )
    except ValueError as e:
        return error_response(str(e), 400)

    if updated is None:
        return error_response("Udhar record not found.", 404)

    return success_response(updated, "Udhar record updated.")


# ── POST /api/v1/udhar/<id>/settle ──────────────────────────────────────────
@udhar_bp.route("/<int:record_id>/settle", methods=["POST"])
@login_required
def settle_record(record_id):
    user_id = get_current_user_id()
    try:
        result = settle_udhar(user_id, record_id)
    except ValueError as e:
        return error_response(str(e), 400)

    if result is None:
        return error_response("Udhar record not found.", 404)

    return success_response(result, "Record marked as settled.")


# ── POST /api/v1/udhar/<id>/reopen ──────────────────────────────────────────
@udhar_bp.route("/<int:record_id>/reopen", methods=["POST"])
@login_required
def reopen_record(record_id):
    user_id = get_current_user_id()
    try:
        result = reopen_udhar(user_id, record_id)
    except ValueError as e:
        return error_response(str(e), 400)

    if result is None:
        return error_response("Udhar record not found.", 404)

    return success_response(result, "Record reopened.")


# ── DELETE /api/v1/udhar/<id> ────────────────────────────────────────────────
@udhar_bp.route("/<int:record_id>", methods=["DELETE"])
@login_required
def remove_udhar(record_id):
    user_id = get_current_user_id()
    try:
        deleted = delete_udhar(user_id, record_id)
    except ValueError as e:
        return error_response(str(e), 400)

    if not deleted:
        return error_response("Udhar record not found.", 404)

    return success_response(None, "Udhar record deleted.")
