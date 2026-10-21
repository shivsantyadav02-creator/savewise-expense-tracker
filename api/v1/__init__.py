from flask import Blueprint

from api.v1.auth_routes import auth_bp
from api.v1.income_routes import income_bp
from api.v1.expense_routes import expense_bp
from api.v1.dashboard_routes import dashboard_bp
from api.v1.budget_routes import budget_bp
from api.v1.goal_routes import goal_bp
from api.v1.preset_routes import preset_bp
from api.v1.wishlist_routes import wishlist_bp
from api.v1.udhar_routes import udhar_bp
from api.v1.insights_routes import insights_bp

# Master API v1 Blueprint
api_v1_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")

# Register child blueprints
api_v1_bp.register_blueprint(auth_bp)
api_v1_bp.register_blueprint(income_bp)
api_v1_bp.register_blueprint(expense_bp)
api_v1_bp.register_blueprint(dashboard_bp)
api_v1_bp.register_blueprint(budget_bp)
api_v1_bp.register_blueprint(goal_bp)
api_v1_bp.register_blueprint(preset_bp)
api_v1_bp.register_blueprint(wishlist_bp)
api_v1_bp.register_blueprint(udhar_bp)
api_v1_bp.register_blueprint(insights_bp)
