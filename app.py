import os
from flask import Flask, jsonify, request, render_template, redirect, url_for, session, send_from_directory
from flask_cors import CORS

from config import Config
from database.db import init_app
from api.v1 import api_v1_bp
from utils.auth import get_current_user_id


def create_app(config_class=Config):
    """
    Application Factory for Savewise.
    - Configures Flask application from Config class.
    - Sets up SQLite per-request teardown hooks.
    - Configures CORS for /api/* routes (same-origin by default; read CORS_ORIGINS from .env).
    - Registers API v1 routes under /api/v1.
    - Serves responsive frontend at / (redirects to /login when not authenticated).
    - Serves login/register UI at /login (redirects to / when already authenticated).
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Register database teardown lifecycle
    init_app(app)

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Because we use session cookies (credentials), we CANNOT combine origins="*"
    # with supports_credentials=True.
    # Default: same-origin only (no CORS header sent, browsers treat it as same-origin).
    # To allow specific trusted front-end origins set CORS_ORIGINS in .env as a
    # comma-separated list, e.g. CORS_ORIGINS=https://app.example.com,https://dev.example.com
    raw_origins = os.environ.get("CORS_ORIGINS", "").strip()
    allowed_origins = [o.strip() for o in raw_origins.split(",") if o.strip()] if raw_origins else []

    if allowed_origins:
        CORS(
            app,
            resources={r"/api/*": {"origins": allowed_origins}},
            supports_credentials=True,
        )
    # If no explicit CORS origins configured, no CORS headers are added (same-origin only).

    # Register API v1 endpoints
    app.register_blueprint(api_v1_bp)

    # ── Page Routes ───────────────────────────────────────────────────────────

    @app.route("/")
    def index():
        """Dashboard — redirects to /login when not authenticated."""
        if get_current_user_id() is None:
            return redirect(url_for("login_page"))
        return render_template("index.html")

    @app.route("/login")
    def login_page():
        """Login / Register page — redirects to / when already authenticated."""
        if get_current_user_id() is not None:
            return redirect(url_for("index"))
        return render_template("login.html")

    @app.route("/logout")
    def logout_page():
        """Logout page — clears session and redirects to /login."""
        session.clear()
        return redirect(url_for("login_page"))

    @app.route("/service-worker.js")
    def service_worker():
        """Serves the root-scoped PWA service worker with appropriate headers."""
        response = send_from_directory(app.static_folder, "service-worker.js", mimetype="application/javascript")
        response.headers["Service-Worker-Allowed"] = "/"
        response.headers["Cache-Control"] = "no-cache"
        return response

    @app.route("/offline.html")
    def offline_page():
        """Serves the offline fallback page."""
        return render_template("offline.html")

    # ── Global JSON error handlers for API paths ──────────────────────────────

    @app.errorhandler(404)
    def handle_not_found(e):
        if request.path.startswith("/api/"):
            return jsonify({
                "success": False,
                "error": "The requested API endpoint was not found."
            }), 404
        return "Not Found", 404

    @app.errorhandler(405)
    def handle_method_not_allowed(e):
        if request.path.startswith("/api/"):
            return jsonify({
                "success": False,
                "error": f"Method {request.method} not allowed for this endpoint."
            }), 405
        return "Method Not Allowed", 405

    @app.errorhandler(500)
    def handle_internal_error(e):
        if request.path.startswith("/api/"):
            return jsonify({
                "success": False,
                "error": "An internal server error occurred."
            }), 500
        return "Internal Server Error", 500

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=5000, debug=Config.DEBUG)
