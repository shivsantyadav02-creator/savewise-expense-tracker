"""
utils/auth.py — Authentication utilities.

SINGLE SOURCE OF TRUTH: get_current_user_id() is the ONE place that decides
the current user. All other code reads from here.
"""
from functools import wraps
from flask import session, jsonify


def get_current_user_id() -> int | None:
    """
    Returns the user_id of the currently authenticated user from the session,
    or None if not logged in.

    This is the ONE authoritative place that reads authentication state.
    Phase 3: reads session["user_id"] set by POST /api/v1/auth/login.
    """
    return session.get("user_id")


def login_required(f):
    """
    Decorator that protects an API route from unauthenticated access.
    On failure returns JSON 401 {"success": false, "error": "Login required"}.
    Must be applied AFTER @blueprint.route().
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if get_current_user_id() is None:
            return jsonify({"success": False, "error": "Login required"}), 401
        return f(*args, **kwargs)
    return decorated
