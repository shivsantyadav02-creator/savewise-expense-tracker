from flask import Flask, jsonify, request, render_template
from flask_cors import CORS

from config import Config
from database.db import init_app
from api.v1 import api_v1_bp

def create_app(config_class=Config):
    """
    Application Factory for Savewise.
    - Configures Flask application from Config class.
    - Sets up SQLite per-request teardown hooks.
    - Configures CORS for all /api/* routes.
    - Registers API v1 routes under /api/v1.
    - Serves responsive frontend shell at /.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Register database teardown lifecycle
    init_app(app)

    # Enable CORS for API routes
    # NOTE: Origins are wildcarded ('*') for local development. Restrict origins to specific trusted domains before production deployment.
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Register API v1 endpoints
    app.register_blueprint(api_v1_bp)

    # Web UI Dashboard route
    @app.route("/")
    def index():
        return render_template("index.html")

    # Global JSON error handlers for API paths
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
