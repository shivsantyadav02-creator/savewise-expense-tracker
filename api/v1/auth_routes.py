"""
api/v1/auth_routes.py — Authentication API endpoints.

Routes:
  POST /api/v1/auth/register  — create account (or adopt default user id=1)
  POST /api/v1/auth/login     — authenticate, set session cookie
  POST /api/v1/auth/logout    — clear session
  GET  /api/v1/auth/me        — return current user info (username + email only)
"""
from flask import Blueprint, request, session

from utils.responses import success_response, error_response
from services.auth_service import register_user, login_user, get_user_by_id
from utils.auth import get_current_user_id, login_required

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/register", methods=["POST"], strict_slashes=False)
def register():
    """
    POST /api/v1/auth/register
    Body: { username, email, password }
    Returns 201 and logs the user in on success.
    """
    if not request.is_json:
        return error_response("Request body must be valid JSON.", 400)

    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    try:
        user = register_user(username, email, password)
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception:
        return error_response("An unexpected server error occurred.", 500)

    # Log the new user in immediately
    session.clear()
    session["user_id"] = user["id"]
    session.permanent = False

    return success_response(
        data={"id": user["id"], "username": user["username"], "email": user["email"]},
        message="Account created successfully.",
        status_code=201,
    )


@auth_bp.route("/login", methods=["POST"], strict_slashes=False)
def login():
    """
    POST /api/v1/auth/login
    Body: { email, password }
    On any failure returns generic 401 (never reveals whether the email exists).
    session.clear() is called before setting new session to prevent session fixation.
    """
    if not request.is_json:
        return error_response("Request body must be valid JSON.", 400)

    data = request.get_json(silent=True) or {}
    email = data.get("email") or ""
    password = data.get("password") or ""

    try:
        user = login_user(email, password)
    except ValueError as e:
        if str(e) == "locked":
            return error_response(
                "Too many failed attempts. Please try again in 15 minutes.", 429
            )
        # Generic 401 — never reveal whether the email exists
        return error_response("Invalid email or password.", 401)
    except Exception:
        return error_response("An unexpected server error occurred.", 500)

    # Prevent session fixation: clear any existing session before setting new one
    session.clear()
    session["user_id"] = user["id"]
    session.permanent = False

    return success_response(
        data={"id": user["id"], "username": user["username"], "email": user["email"]},
        message="Logged in successfully.",
        status_code=200,
    )


@auth_bp.route("/logout", methods=["POST"], strict_slashes=False)
def logout():
    """
    POST /api/v1/auth/logout
    Clears the session. Safe to call even when not logged in.
    """
    session.clear()
    return success_response(data=None, message="Logged out successfully.", status_code=200)


@auth_bp.route("/me", methods=["GET"], strict_slashes=False)
@login_required
def me():
    """
    GET /api/v1/auth/me
    Returns the authenticated user's username and email. Never returns the password hash.
    """
    user_id = get_current_user_id()
    try:
        user = get_user_by_id(user_id)
    except Exception:
        return error_response("An unexpected server error occurred.", 500)

    if not user:
        # Session references a user that no longer exists
        session.clear()
        return error_response("Login required", 401)

    return success_response(
        data={"id": user["id"], "username": user["username"], "email": user["email"]},
        message="Current user retrieved successfully.",
        status_code=200,
    )
