"""
tests/test_insights.py — Comprehensive tests for Phase 3 Insights:
- (1) Timezone fix (IST / APP_TIMEZONE, 00:00 - 05:30 window)
- (2) "What if I had saved it" Simulator
- (3) Month-End Balance Prediction
- (4) Smart Insights Summary
- (5) Weekly Report
"""

import os
import unittest
from datetime import datetime, timezone, timedelta, date
from pathlib import Path
from unittest.mock import patch

from config import Config
from database.db import init_db
from app import create_app


def _make_test_db(path: str):
    Config.DATABASE_PATH = path
    if os.path.exists(path):
        os.remove(path)
    init_db()


class TestTimezoneFix(unittest.TestCase):
    """
    Tests proving timezone fix:
    Simulated time: 2026-10-05 20:00 UTC == 2026-10-06 01:30 IST.
    - Preset use creates an expense dated 2026-10-06.
    - An udhar due 2026-10-05 is overdue.
    """

    def setUp(self):
        self.test_db = str(Path(__file__).resolve().parent / "test_tz.db")
        _make_test_db(self.test_db)

        from flask import Flask
        from database.db import init_app, get_db
        self.app = Flask(__name__)
        init_app(self.app)
        self.ctx = self.app.app_context()
        self.ctx.push()

        # Simulated UTC time: 2026-10-05 20:00:00 UTC (01:30 AM IST on Oct 6)
        self.simulated_utc = datetime(2026, 10, 5, 20, 0, 0, tzinfo=timezone.utc)

    def tearDown(self):
        self.ctx.pop()
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_clock_today_local_is_next_day_in_ist(self):
        from utils.clock import today_local
        with patch("utils.clock.now_utc", return_value=self.simulated_utc):
            loc_date = today_local()
        self.assertEqual(loc_date, date(2026, 10, 6))

    def test_preset_creates_expense_in_ist_date(self):
        from services.preset_service import create_preset, use_preset
        preset = create_preset(1, "Chai", 20.0, "faltu", "Snacks")

        with patch("utils.clock.now_utc", return_value=self.simulated_utc):
            expense = use_preset(1, preset["id"])

        self.assertEqual(expense["date"], "2026-10-06")

    def test_udhar_due_yesterday_is_overdue_in_ist(self):
        from services.udhar_service import create_udhar, get_udhar_list

        with patch("utils.clock.now_utc", return_value=self.simulated_utc):
            create_udhar(1, "Amit", 500.0, "lent", due_date="2026-10-05")
            records = get_udhar_list(1, status="pending")

        self.assertEqual(len(records), 1)
        # In IST it is 2026-10-06, so due_date 2026-10-05 must be overdue!
        self.assertTrue(records[0]["is_overdue"])


class TestInsightsService(unittest.TestCase):
    """Unit tests for services/insights_service.py"""

    def setUp(self):
        self.test_db = str(Path(__file__).resolve().parent / "test_insights_service.db")
        _make_test_db(self.test_db)

        from flask import Flask
        from database.db import init_app, get_db
        self.app = Flask(__name__)
        init_app(self.app)
        self.ctx = self.app.app_context()
        self.ctx.push()

        db = get_db()
        db.execute("INSERT INTO users (id, username, email) VALUES (2, 'user2', 'u2@test.local')")
        db.commit()

        # Fixed reference date: 2026-10-10 (Day 10 of a 31-day month)
        self.ref_now = datetime(2026, 10, 10, 12, 0, 0, tzinfo=timezone.utc)

    def tearDown(self):
        self.ctx.pop()
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def _patch_now(self, dt=None):
        target = dt if dt is not None else self.ref_now
        return patch("utils.clock.now_utc", return_value=target)

    # ── Simulator Tests ─────────────────────────────────────────────────────

    def test_simulator_math_known_values(self):
        from services.insights_service import get_savings_simulator
        from services.expense_service import create_expense

        create_expense(1, 1000.0, "faltu", "Shopping", "2026-10-02")

        res = get_savings_simulator(1, "2026-10", annual_return=12.0)
        self.assertTrue(res["has_faltu"])
        self.assertAlmostEqual(res["monthly_investment_inr"], 1000.0)
        self.assertEqual(len(res["projections"]), 3)

        # 1 Year (12 months): FV = 12,809.33, Invested = 12,000.00, Gain = 809.33
        p1 = res["projections"][0]
        self.assertEqual(p1["years"], 1)
        self.assertEqual(p1["months"], 12)
        self.assertAlmostEqual(p1["total_invested_inr"], 12000.0, places=2)
        self.assertAlmostEqual(p1["future_value_inr"], 12809.33, places=2)
        self.assertAlmostEqual(p1["gain_inr"], 809.33, places=2)

    def test_simulator_zero_return(self):
        from services.insights_service import get_savings_simulator
        from services.expense_service import create_expense

        create_expense(1, 500.0, "faltu", "Impulse", "2026-10-05")

        res = get_savings_simulator(1, "2026-10", annual_return=0.0)
        p1 = res["projections"][0]
        self.assertAlmostEqual(p1["total_invested_inr"], 6000.0)
        self.assertAlmostEqual(p1["future_value_inr"], 6000.0)
        self.assertAlmostEqual(p1["gain_inr"], 0.0)

    def test_simulator_zero_faltu_friendly_response(self):
        from services.insights_service import get_savings_simulator

        res = get_savings_simulator(1, "2026-10", annual_return=12.0)
        self.assertFalse(res["has_faltu"])
        self.assertAlmostEqual(res["monthly_investment_inr"], 0.0)
        self.assertIn("No faltu spending", res["message"])

    def test_simulator_invalid_annual_return(self):
        from services.insights_service import get_savings_simulator

        with self.assertRaises(ValueError):
            get_savings_simulator(1, "2026-10", annual_return=-1.0)
        with self.assertRaises(ValueError):
            get_savings_simulator(1, "2026-10", annual_return=35.0)

    # ── Prediction Tests ────────────────────────────────────────────────────

    def test_prediction_day_1_low_confidence(self):
        from services.insights_service import get_month_prediction
        from services.income_service import create_income
        from services.expense_service import create_expense

        create_income(1, 31000.0, "Salary", "2026-10-01")
        create_expense(1, 500.0, "daily", "Food", "2026-10-01")

        day_1_dt = datetime(2026, 10, 1, 9, 0, 0, tzinfo=timezone.utc)
        with self._patch_now(day_1_dt):
            res = get_month_prediction(1, "2026-10")

        self.assertEqual(res["status"], "current")
        self.assertEqual(res["days_elapsed"], 1)
        self.assertEqual(res["days_remaining"], 30)
        self.assertEqual(res["confidence"], "low")
        self.assertAlmostEqual(res["average_daily_spend_inr"], 500.0)
        self.assertAlmostEqual(res["projected_expense_inr"], 15500.0)

    def test_prediction_day_10_medium_confidence(self):
        from services.insights_service import get_month_prediction
        from services.income_service import create_income
        from services.expense_service import create_expense

        create_income(1, 40000.0, "Salary", "2026-10-01")
        create_expense(1, 10000.0, "daily", "Rent", "2026-10-05")

        day_10_dt = datetime(2026, 10, 10, 10, 0, 0, tzinfo=timezone.utc)
        with self._patch_now(day_10_dt):
            res = get_month_prediction(1, "2026-10")

        self.assertEqual(res["status"], "current")
        self.assertEqual(res["confidence"], "medium")
        self.assertAlmostEqual(res["average_daily_spend_inr"], 1000.0)

    def test_prediction_last_day_high_confidence(self):
        from services.insights_service import get_month_prediction
        from services.income_service import create_income
        from services.expense_service import create_expense

        create_income(1, 20000.0, "Salary", "2026-10-01")
        create_expense(1, 15500.0, "daily", "Bills", "2026-10-25")

        day_31_dt = datetime(2026, 10, 31, 23, 59, 0, tzinfo=timezone.utc)
        with self._patch_now(day_31_dt):
            res = get_month_prediction(1, "2026-10")

        self.assertEqual(res["confidence"], "high")
        self.assertEqual(res["days_remaining"], 0)
        self.assertAlmostEqual(res["safe_daily_budget_inr"], 0.0)

    def test_prediction_past_month(self):
        from services.insights_service import get_month_prediction
        with self._patch_now(self.ref_now):
            res = get_month_prediction(1, "2026-09")
        self.assertEqual(res["status"], "completed")

    def test_prediction_future_month(self):
        from services.insights_service import get_month_prediction
        with self._patch_now(self.ref_now):
            res = get_month_prediction(1, "2026-11")
        self.assertEqual(res["status"], "future")
        self.assertIsNone(res["projected_expense_inr"])

    def test_prediction_no_data_safe(self):
        from services.insights_service import get_month_prediction
        with self._patch_now(self.ref_now):
            res = get_month_prediction(1, "2026-10")
        self.assertEqual(res["status"], "current")
        self.assertAlmostEqual(res["average_daily_spend_inr"], 0.0)

    # ── Smart Insights Tests ────────────────────────────────────────────────

    def test_smart_insights_empty_month_no_crash(self):
        from services.insights_service import get_smart_insights
        with self._patch_now(self.ref_now):
            insights = get_smart_insights(1, "2026-10")
        self.assertIsInstance(insights, list)

    def test_smart_insights_faltu_income_ratio(self):
        from services.insights_service import get_smart_insights
        from services.income_service import create_income
        from services.expense_service import create_expense

        create_income(1, 10000.0, "Salary", "2026-10-01")
        create_expense(1, 4000.0, "faltu", "Shopping", "2026-10-02")

        with self._patch_now(self.ref_now):
            insights = get_smart_insights(1, "2026-10")

        codes = [i["code"] for i in insights]
        self.assertIn("FALTU_INCOME_HIGH", codes)
        ratio_insight = next(i for i in insights if i["code"] == "FALTU_INCOME_HIGH")
        self.assertEqual(ratio_insight["severity"], "warning")
        self.assertIn("40.0%", ratio_insight["message"])

    def test_smart_insights_zero_income_does_not_crash(self):
        from services.insights_service import get_smart_insights
        from services.expense_service import create_expense

        create_expense(1, 1000.0, "faltu", "Cafe", "2026-10-02")
        with self._patch_now(self.ref_now):
            insights = get_smart_insights(1, "2026-10")

        # Ratio insight is skipped when income is 0
        codes = [i["code"] for i in insights]
        self.assertNotIn("FALTU_INCOME_HIGH", codes)
        self.assertNotIn("FALTU_INCOME_LOW", codes)

    def test_smart_insights_month_change_increased(self):
        from services.insights_service import get_smart_insights
        from services.expense_service import create_expense

        create_expense(1, 1000.0, "faltu", "Snacks", "2026-09-10")
        create_expense(1, 1500.0, "faltu", "Snacks", "2026-10-05")

        with self._patch_now(self.ref_now):
            insights = get_smart_insights(1, "2026-10")

        codes = [i["code"] for i in insights]
        self.assertIn("FALTU_INCREASED", codes)
        item = next(i for i in insights if i["code"] == "FALTU_INCREASED")
        self.assertEqual(item["severity"], "warning")
        self.assertIn("50.0%", item["message"])

    def test_smart_insights_month_change_skipped_if_no_prev_data(self):
        from services.insights_service import get_smart_insights
        from services.expense_service import create_expense

        # Only current month has faltu
        create_expense(1, 1500.0, "faltu", "Snacks", "2026-10-05")

        with self._patch_now(self.ref_now):
            insights = get_smart_insights(1, "2026-10")

        codes = [i["code"] for i in insights]
        self.assertNotIn("FALTU_INCREASED", codes)
        self.assertNotIn("FALTU_DECREASED", codes)

    def test_smart_insights_top_category(self):
        from services.insights_service import get_smart_insights
        from services.expense_service import create_expense

        create_expense(1, 3000.0, "faltu", "Shopping", "2026-10-02")
        create_expense(1, 1000.0, "faltu", "Gaming", "2026-10-03")

        with self._patch_now(self.ref_now):
            insights = get_smart_insights(1, "2026-10")

        item = next((i for i in insights if i["code"] == "TOP_FALTU_CATEGORY"), None)
        self.assertIsNotNone(item)
        self.assertIn("Shopping", item["message"])
        self.assertIn("75.0%", item["message"])

    def test_smart_insights_savings_goal_and_limit_and_wishlist(self):
        from services.insights_service import get_smart_insights
        from services.goal_service import set_savings_goal
        from services.budget_service import set_faltu_limit
        from services.wishlist_service import create_wishlist_item, drop_wishlist_item
        from services.income_service import create_income

        create_income(1, 10000.0, "Salary", "2026-10-01")
        set_savings_goal(1, "2026-10", 5000.0, "Target")
        set_faltu_limit(1, "2026-10", 2000.0)

        # Wishlist drop
        item = create_wishlist_item(1, "Headphones", 3000.0, "Electronics")
        drop_wishlist_item(1, item["id"])

        with self._patch_now(self.ref_now):
            insights = get_smart_insights(1, "2026-10")

        codes = [i["code"] for i in insights]
        self.assertIn("SAVINGS_GOAL_ACHIEVED", codes)
        self.assertIn("FALTU_LIMIT_SAFE", codes)
        self.assertIn("WISHLIST_DROPPED_SAVINGS", codes)

    def test_smart_insights_limit_of_6_and_sorting(self):
        """Never more than 6 insights, warning severity comes first."""
        from services.insights_service import get_smart_insights
        from services.goal_service import set_savings_goal
        from services.budget_service import set_faltu_limit
        from services.wishlist_service import create_wishlist_item, drop_wishlist_item
        from services.income_service import create_income
        from services.expense_service import create_expense

        create_income(1, 10000.0, "Salary", "2026-10-01")
        create_expense(1, 500.0, "faltu", "LastM", "2026-09-10")
        create_expense(1, 4000.0, "faltu", "Shopping", "2026-10-02")
        set_savings_goal(1, "2026-10", 20000.0, "Goal")  # behind
        set_faltu_limit(1, "2026-10", 1000.0)            # exceeded
        it = create_wishlist_item(1, "Bag", 1000.0, "Fashion")
        drop_wishlist_item(1, it["id"])

        with self._patch_now(self.ref_now):
            insights = get_smart_insights(1, "2026-10")

        self.assertLessEqual(len(insights), 6)
        # Warning items must come before non-warning items
        severities = [i["severity"] for i in insights]
        if "warning" in severities:
            self.assertEqual(severities[0], "warning")

    # ── Weekly Report Tests ─────────────────────────────────────────────────

    def test_weekly_report_defaults_to_last_7_days(self):
        from services.insights_service import get_weekly_report
        with self._patch_now(self.ref_now):  # 2026-10-10
            report = get_weekly_report(1)

        self.assertEqual(report["end_date"], "2026-10-10")
        self.assertEqual(report["start_date"], "2026-10-04")
        self.assertEqual(report["total_spent_inr"], 0.0)

    def test_weekly_report_known_data(self):
        from services.insights_service import get_weekly_report
        from services.expense_service import create_expense
        from services.income_service import create_income

        # Current 7 days: 2026-10-01 to 2026-10-07
        create_income(1, 10000.0, "Salary", "2026-10-01")
        create_expense(1, 500.0, "daily", "Food", "2026-10-01")
        create_expense(1, 1500.0, "faltu", "Shopping", "2026-10-02")
        create_expense(1, 200.0, "daily", "Metro", "2026-10-03")
        create_expense(1, 300.0, "daily", "Food", "2026-10-04")
        # 2026-10-05, 06, 07 have 0 expenses (no-spend days = 3)

        # Previous 7 days: 2026-09-24 to 2026-09-30 (spent 2000)
        create_expense(1, 2000.0, "daily", "Groceries", "2026-09-25")

        report = get_weekly_report(1, week_start="2026-10-01")

        self.assertEqual(report["start_date"], "2026-10-01")
        self.assertEqual(report["end_date"], "2026-10-07")
        self.assertAlmostEqual(report["total_spent_inr"], 2500.0)
        self.assertAlmostEqual(report["daily_inr"], 1000.0)
        self.assertAlmostEqual(report["faltu_inr"], 1500.0)
        self.assertAlmostEqual(report["income_received_inr"], 10000.0)

        # Top categories
        self.assertEqual(len(report["top_3_sub_categories"]), 3)
        self.assertEqual(report["top_3_sub_categories"][0]["sub_category"], "Shopping")
        self.assertAlmostEqual(report["top_3_sub_categories"][0]["amount_inr"], 1500.0)

        # Highest spending day
        self.assertEqual(report["highest_spending_day"]["date"], "2026-10-02")
        self.assertAlmostEqual(report["highest_spending_day"]["amount_inr"], 1500.0)

        # No spend days (4 active days: 01, 02, 03, 04 -> 7 - 4 = 3 no-spend days)
        self.assertEqual(report["no_spend_days"], 3)

        # Previous week comparison: ((2500 - 2000) / 2000) * 100 = +25.0%
        self.assertAlmostEqual(report["change_versus_previous_week_percent"], 25.0)

    def test_weekly_report_invalid_week_start_rejected(self):
        from services.insights_service import get_weekly_report
        with self.assertRaises(ValueError):
            get_weekly_report(1, week_start="2026-02-30")
        with self.assertRaises(ValueError):
            get_weekly_report(1, week_start="garbage")

    def test_weekly_report_user_isolation(self):
        from services.insights_service import get_weekly_report
        from services.expense_service import create_expense

        create_expense(2, 9999.0, "daily", "Secret", "2026-10-05")

        with self._patch_now(self.ref_now):
            rep1 = get_weekly_report(1, week_start="2026-10-04")

        self.assertAlmostEqual(rep1["total_spent_inr"], 0.0)


class TestInsightsAPI(unittest.TestCase):
    """HTTP-level tests for /api/v1/insights routes."""

    def setUp(self):
        self.test_db = str(Path(__file__).resolve().parent / "test_insights_api.db")
        _make_test_db(self.test_db)

        app = create_app()
        app.config["TESTING"] = True
        self.client = app.test_client()
        self.app = app

        # Log in as the seeded default user (id=1) via session_transaction()
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1

        self.ref_now = datetime(2026, 10, 10, 12, 0, 0, tzinfo=timezone.utc)

    def tearDown(self):
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_api_summary_route(self):
        with patch("utils.clock.now_utc", return_value=self.ref_now):
            res = self.client.get("/api/v1/insights/summary?month=2026-10")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["success"])
        self.assertIsInstance(res.get_json()["data"], list)

    def test_api_weekly_route(self):
        with patch("utils.clock.now_utc", return_value=self.ref_now):
            res = self.client.get("/api/v1/insights/weekly?week_start=2026-10-01")
        self.assertEqual(res.status_code, 200)
        d = res.get_json()["data"]
        self.assertEqual(d["start_date"], "2026-10-01")
        self.assertEqual(d["end_date"], "2026-10-07")

    def test_api_weekly_invalid_date_returns_400(self):
        res = self.client.get("/api/v1/insights/weekly?week_start=2026-02-30")
        self.assertEqual(res.status_code, 400)


if __name__ == "__main__":
    unittest.main()
