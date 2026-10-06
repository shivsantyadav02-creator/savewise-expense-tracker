from flask import Blueprint

from api.v1.income_routes import income_bp
from api.v1.expense_routes import expense_bp
from api.v1.dashboard_routes import dashboard_bp

# Master API v1 Blueprint
api_v1_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")

# Register child blueprints
api_v1_bp.register_blueprint(income_bp)
api_v1_bp.register_blueprint(expense_bp)
api_v1_bp.register_blueprint(dashboard_bp)
