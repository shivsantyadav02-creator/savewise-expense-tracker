"""
api/v1/insights_routes.py — Phase 3 REST routes for Insights
- (A) GET /api/v1/insights/simulator
- (B) GET /api/v1/insights/prediction
- (C) GET /api/v1/insights/summary
- (D) GET /api/v1/insights/weekly

Routes only: parse request -> call service -> return response.
No business logic, no SQL here.
"""

from flask import Blueprint, request

from utils.auth import get_current_user_id, login_required
from utils.clock import today_local
from utils.responses import success_response, error_response
from services.insights_service import (
    get_savings_simulator,
    get_month_prediction,
    get_smart_insights,
    get_weekly_report,
)

insights_bp = Blueprint("insights", __name__, url_prefix="/insights")


@insights_bp.route("/simulator", methods=["GET"])
@login_required
def simulator():
    user_id = get_current_user_id()
    month = request.args.get("month")
    if not month:
        return error_response("The 'month' parameter is required (format YYYY-MM).", 400)

    annual_return_param = request.args.get("annual_return", "12")
    try:
        annual_return = float(annual_return_param)
    except (ValueError, TypeError):
        return error_response("Annual return must be a valid number.", 400)

    try:
        data = get_savings_simulator(user_id, month=month, annual_return=annual_return)
    except ValueError as e:
        return error_response(str(e), 400)

    return success_response(data)


@insights_bp.route("/prediction", methods=["GET"])
@login_required
def prediction():
    user_id = get_current_user_id()
    raw_month = request.args.get("month")
    month = raw_month.strip() if raw_month else today_local().strftime("%Y-%m")

    try:
        data = get_month_prediction(user_id, month=month)
    except ValueError as e:
        return error_response(str(e), 400)

    return success_response(data)


@insights_bp.route("/summary", methods=["GET"])
@login_required
def insights_summary():
    """
    Returns smart actionable insights for the given month.
    Defaults to current month if omitted.
    """
    user_id = get_current_user_id()
    raw_month = request.args.get("month")
    month = raw_month.strip() if raw_month else today_local().strftime("%Y-%m")

    try:
        data = get_smart_insights(user_id, month=month)
    except ValueError as e:
        return error_response(str(e), 400)

    return success_response(data)


@insights_bp.route("/weekly", methods=["GET"])
@login_required
def weekly_report():
    """
    Returns 7-day spending report.
    Optional ?week_start=YYYY-MM-DD. Defaults to last 7 days ending today_local().
    """
    user_id = get_current_user_id()
    week_start = request.args.get("week_start")

    try:
        data = get_weekly_report(user_id, week_start=week_start)
    except ValueError as e:
        return error_response(str(e), 400)

    return success_response(data)
