import os
import json
import unittest
from pathlib import Path

from config import Config
from database.db import init_db
from app import create_app

class TestPhase2Services(unittest.TestCase):
    """Unit tests for budget_service, goal_service, history, and month validation."""

    def setUp(self):
        self.test_db_path = str(Path(__file__).resolve().parent / "test_phase2_services.db")
        Config.DATABASE_PATH = self.test_db_path
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        init_db()

        from flask import Flask
        from database.db import init_app, get_db
        self.app = Flask(__name__)
        init_app(self.app)
        self.ctx = self.app.app_context()
        self.ctx.push()

        db = get_db()
        db.execute("INSERT INTO users (id, username, email) VALUES (2, 'user2', 'u2@test.local')")
        db.commit()

    def tearDown(self):
        self.ctx.pop()
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    # ----------------------------------------------------------
    # Strict Month Validation Tests
    # ----------------------------------------------------------
    def test_validate_month_strict_regex(self):
        from utils.helpers import validate_month
        # Valid cases
        self.assertEqual(validate_month("2026-01"), "2026-01")
        self.assertEqual(validate_month("2026-12"), "2026-12")

        # Invalid cases specified by user requirement
        invalid_cases = ["2026-1", "2026-13", "2026-00", "26-01", "2026-01-05", "", None, "not-a-month"]
        for case in invalid_cases:
            with self.subTest(case=case):
                with self.assertRaises(ValueError):
                    validate_month(case)

    # ----------------------------------------------------------
    # Budget (Faltu Limit) Service Tests
    # ----------------------------------------------------------
    def test_set_and_get_faltu_limit(self):
        from services.budget_service import set_faltu_limit, get_faltu_limit
        result = set_faltu_limit(1, "2026-10", 1500.0)
        self.assertEqual(result["faltu_limit_paise"], 150000)
        self.assertEqual(result["faltu_limit_inr"], 1500.0)
        self.assertEqual(result["month"], "2026-10")

        fetched = get_faltu_limit(1, "2026-10")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["faltu_limit_inr"], 1500.0)

    def test_update_faltu_limit_upserts(self):
        from services.budget_service import set_faltu_limit
        set_faltu_limit(1, "2026-10", 1000.0)
        updated = set_faltu_limit(1, "2026-10", 2000.0)
        self.assertEqual(updated["faltu_limit_inr"], 2000.0)

    def test_zero_faltu_limit_allowed(self):
        from services.budget_service import set_faltu_limit
        result = set_faltu_limit(1, "2026-10", 0)
        self.assertEqual(result["faltu_limit_paise"], 0)
        self.assertEqual(result["faltu_limit_inr"], 0.0)

    def test_negative_limit_rejected(self):
        from services.budget_service import set_faltu_limit
        with self.assertRaises(ValueError):
            set_faltu_limit(1, "2026-10", -100)

    def test_invalid_month_format_rejected_for_limit(self):
        from services.budget_service import set_faltu_limit
        for bad_month in ["2026-1", "2026/10", "2026-10-01", "2026-13", "26-01"]:
            with self.subTest(month=bad_month):
                with self.assertRaises(ValueError):
                    set_faltu_limit(1, bad_month, 1000)

    def test_get_limit_returns_none_when_unset(self):
        from services.budget_service import get_faltu_limit
        self.assertIsNone(get_faltu_limit(1, "2099-01"))

    def test_limit_user_isolation(self):
        from services.budget_service import set_faltu_limit, get_faltu_limit
        set_faltu_limit(1, "2026-10", 1000.0)
        self.assertIsNone(get_faltu_limit(2, "2026-10"))

    # ----------------------------------------------------------
    # Goal Service Tests
    # ----------------------------------------------------------
    def test_set_and_get_savings_goal(self):
        from services.goal_service import set_savings_goal, get_savings_goal
        result = set_savings_goal(1, "2026-10", 5000.0, "Laptop Fund")
        self.assertEqual(result["target_amount_paise"], 500000)
        self.assertEqual(result["target_inr"], 5000.0)
        self.assertEqual(result["title"], "Laptop Fund")

        fetched = get_savings_goal(1, "2026-10")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["target_inr"], 5000.0)

    def test_update_savings_goal_upserts(self):
        from services.goal_service import set_savings_goal
        set_savings_goal(1, "2026-10", 3000.0)
        updated = set_savings_goal(1, "2026-10", 6000.0, "New Goal")
        self.assertEqual(updated["target_inr"], 6000.0)
        self.assertEqual(updated["title"], "New Goal")

    def test_zero_goal_rejected(self):
        from services.goal_service import set_savings_goal
        with self.assertRaises(ValueError):
            set_savings_goal(1, "2026-10", 0)

    def test_negative_goal_rejected(self):
        from services.goal_service import set_savings_goal
        with self.assertRaises(ValueError):
            set_savings_goal(1, "2026-10", -500)

    def test_invalid_month_format_rejected_for_goal(self):
        from services.goal_service import set_savings_goal
        for bad_month in ["2026-1", "Oct-2026", "2026-00", "2026-01-05"]:
            with self.subTest(month=bad_month):
                with self.assertRaises(ValueError):
                    set_savings_goal(1, bad_month, 1000)

    def test_get_goal_returns_none_when_unset(self):
        from services.goal_service import get_savings_goal
        self.assertIsNone(get_savings_goal(1, "2099-01"))

    def test_goal_user_isolation(self):
        from services.goal_service import set_savings_goal, get_savings_goal
        set_savings_goal(1, "2026-10", 5000.0)
        self.assertIsNone(get_savings_goal(2, "2026-10"))

    def test_default_goal_title_when_not_provided(self):
        from services.goal_service import set_savings_goal
        result = set_savings_goal(1, "2026-10", 1000.0)
        self.assertEqual(result["title"], "Monthly Savings Target")

    # ----------------------------------------------------------
    # Dashboard Summary Phase 2 Fields
    # ----------------------------------------------------------
    def _setup_data(self, income=10000.0, daily=3000.0, faltu=1000.0, month="2026-10"):
        from services.income_service import create_income
        from services.expense_service import create_expense
        create_income(1, income, "Salary", f"{month}-01")
        create_expense(1, daily, "daily", "Groceries", f"{month}-02")
        create_expense(1, faltu, "faltu", "Snacks", f"{month}-03")

    def test_dashboard_no_limit_no_goal(self):
        from services.dashboard_service import get_monthly_summary
        self._setup_data()
        s = get_monthly_summary(1, "2026-10")
        self.assertEqual(s["faltu_status"], "none")
        self.assertIsNone(s["faltu_limit_inr"])
        self.assertEqual(s["savings_status"], "none")
        self.assertIsNone(s["savings_goal_inr"])

    def test_faltu_status_normal_below_80(self):
        from services.budget_service import set_faltu_limit
        from services.dashboard_service import get_monthly_summary
        from services.expense_service import create_expense
        set_faltu_limit(1, "2026-10", 1000.0)
        create_expense(1, 790.0, "faltu", "Shopping", "2026-10-04")
        s = get_monthly_summary(1, "2026-10")
        self.assertEqual(s["faltu_status"], "normal")
        self.assertAlmostEqual(s["faltu_used_percent_of_limit"], 79.0, places=1)

    def test_faltu_status_warning_at_80(self):
        from services.budget_service import set_faltu_limit
        from services.dashboard_service import get_monthly_summary
        from services.expense_service import create_expense
        set_faltu_limit(1, "2026-10", 1000.0)
        create_expense(1, 800.0, "faltu", "Shopping", "2026-10-04")
        s = get_monthly_summary(1, "2026-10")
        self.assertEqual(s["faltu_status"], "warning")
        self.assertAlmostEqual(s["faltu_used_percent_of_limit"], 80.0, places=1)

    def test_faltu_status_critical_at_100(self):
        from services.budget_service import set_faltu_limit
        from services.dashboard_service import get_monthly_summary
        from services.expense_service import create_expense
        set_faltu_limit(1, "2026-10", 1000.0)
        create_expense(1, 1000.0, "faltu", "Shopping", "2026-10-04")
        s = get_monthly_summary(1, "2026-10")
        self.assertEqual(s["faltu_status"], "critical")
        self.assertAlmostEqual(s["faltu_used_percent_of_limit"], 100.0, places=1)

    def test_savings_goal_in_progress(self):
        from services.goal_service import set_savings_goal
        from services.dashboard_service import get_monthly_summary
        self._setup_data()
        set_savings_goal(1, "2026-10", 10000.0)
        s = get_monthly_summary(1, "2026-10")
        self.assertEqual(s["savings_status"], "in_progress")
        self.assertAlmostEqual(s["savings_progress_percent"], 60.0, places=1)
        self.assertAlmostEqual(s["savings_raw_progress_percent"], 60.0, places=1)

    def test_savings_goal_achieved(self):
        from services.goal_service import set_savings_goal
        from services.dashboard_service import get_monthly_summary
        self._setup_data()
        set_savings_goal(1, "2026-10", 5000.0)
        s = get_monthly_summary(1, "2026-10")
        self.assertEqual(s["savings_status"], "achieved")
        self.assertEqual(s["savings_progress_percent"], 100.0)
        self.assertGreater(s["savings_raw_progress_percent"], 100.0)

    def test_savings_goal_deficit_negative_balance(self):
        from services.goal_service import set_savings_goal
        from services.expense_service import create_expense
        from services.dashboard_service import get_monthly_summary
        create_expense(1, 500.0, "faltu", "Treat", "2026-10-01")
        set_savings_goal(1, "2026-10", 2000.0)
        s = get_monthly_summary(1, "2026-10")
        self.assertEqual(s["savings_status"], "deficit")
        self.assertLess(s["balance_inr"], 0)
        self.assertEqual(s["savings_progress_percent"], 0.0)

    # ----------------------------------------------------------
    # History Service Tests
    # ----------------------------------------------------------
    def test_history_service_empty(self):
        from services.dashboard_service import get_monthly_history
        hist = get_monthly_history(1, months=6, end_month="2026-10")
        self.assertEqual(len(hist), 6)
        self.assertEqual(hist[0]["month"], "2026-05")
        self.assertEqual(hist[-1]["month"], "2026-10")
        for entry in hist:
            self.assertEqual(entry["income_inr"], 0.0)
            self.assertEqual(entry["daily_inr"], 0.0)
            self.assertEqual(entry["faltu_inr"], 0.0)
            self.assertEqual(entry["balance_inr"], 0.0)

    def test_history_service_one_month(self):
        from services.dashboard_service import get_monthly_history
        from services.income_service import create_income
        create_income(1, 4000.0, "Gift", "2026-10-05")
        hist = get_monthly_history(1, months=1, end_month="2026-10")
        self.assertEqual(len(hist), 1)
        self.assertEqual(hist[0]["month"], "2026-10")
        self.assertEqual(hist[0]["income_inr"], 4000.0)
        self.assertEqual(hist[0]["balance_inr"], 4000.0)

    def test_history_service_several_months(self):
        from services.dashboard_service import get_monthly_history
        from services.income_service import create_income
        from services.expense_service import create_expense
        # Month 1 (2026-08): Income 5000, daily 1000
        create_income(1, 5000.0, "Freelance", "2026-08-01")
        create_expense(1, 1000.0, "daily", "Food", "2026-08-02")
        # Month 2 (2026-10): Faltu 500
        create_expense(1, 500.0, "faltu", "Cafe", "2026-10-03")

        hist = get_monthly_history(1, months=4, end_month="2026-10")
        self.assertEqual(len(hist), 4)
        # Oldest to newest: 2026-07, 2026-08, 2026-09, 2026-10
        self.assertEqual([h["month"] for h in hist], ["2026-07", "2026-08", "2026-09", "2026-10"])

        aug = hist[1]
        self.assertEqual(aug["income_inr"], 5000.0)
        self.assertEqual(aug["daily_inr"], 1000.0)
        self.assertEqual(aug["balance_inr"], 4000.0)

        oct_item = hist[3]
        self.assertEqual(oct_item["faltu_inr"], 500.0)
        self.assertEqual(oct_item["balance_inr"], -500.0)

    def test_history_service_invalid_months_parameter(self):
        from services.dashboard_service import get_monthly_history
        for invalid_m in [0, -1, 25, 100]:
            with self.subTest(months=invalid_m):
                with self.assertRaises(ValueError):
                    get_monthly_history(1, months=invalid_m, end_month="2026-10")

    def test_history_service_user_isolation(self):
        from services.dashboard_service import get_monthly_history
        from services.income_service import create_income
        create_income(1, 10000.0, "Salary", "2026-10-01")
        # User 2 calls history
        hist2 = get_monthly_history(2, months=3, end_month="2026-10")
        for entry in hist2:
            self.assertEqual(entry["income_inr"], 0.0)


class TestPhase2API(unittest.TestCase):
    """Integration tests for budget, goal, history API, and strict month validation."""

    def setUp(self):
        self.test_db_path = str(Path(__file__).resolve().parent / "test_phase2_api.db")
        Config.DATABASE_PATH = self.test_db_path
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        init_db()

        class TestConfig(Config):
            TESTING = True
            DATABASE_PATH = self.test_db_path
            SECRET_KEY = "test-secret-key"

        self.app = create_app(TestConfig)
        self.client = self.app.test_client()

        # Log in as the seeded default user (id=1) via session_transaction()
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1

    def tearDown(self):
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    # ----------------------------------------------------------
    # Strict Month Validation Across All Endpoints
    # ----------------------------------------------------------
    def test_strict_month_validation_across_all_endpoints(self):
        invalid_months = ["2026-1", "2026-13", "2026-00", "26-01", "2026-01-05"]
        for bad_m in invalid_months:
            with self.subTest(month=bad_m):
                # 1. Budget endpoint
                res1 = self.client.put(f"/api/v1/budgets/{bad_m}", json={"faltu_limit_inr": 100})
                self.assertEqual(res1.status_code, 400)
                # 2. Goal endpoint
                res2 = self.client.put(f"/api/v1/goals/{bad_m}", json={"target_inr": 500})
                self.assertEqual(res2.status_code, 400)
                # 3. Dashboard summary
                res3 = self.client.get(f"/api/v1/dashboard/summary?month={bad_m}")
                self.assertEqual(res3.status_code, 400)
                # 4. Incomes list
                res4 = self.client.get(f"/api/v1/incomes?month={bad_m}")
                self.assertEqual(res4.status_code, 400)
                # 5. Expenses list
                res5 = self.client.get(f"/api/v1/expenses?month={bad_m}")
                self.assertEqual(res5.status_code, 400)

    # ----------------------------------------------------------
    # Budget API
    # ----------------------------------------------------------
    def test_put_budget_creates_limit(self):
        res = self.client.put("/api/v1/budgets/2026-10", json={"faltu_limit_inr": 1500})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["faltu_limit_inr"], 1500.0)
        self.assertEqual(data["data"]["faltu_limit_paise"], 150000)

    def test_put_budget_zero_limit_allowed(self):
        res = self.client.put("/api/v1/budgets/2026-10", json={"faltu_limit_inr": 0})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["data"]["faltu_limit_paise"], 0)

    def test_put_budget_negative_rejected(self):
        res = self.client.put("/api/v1/budgets/2026-10", json={"faltu_limit_inr": -100})
        self.assertEqual(res.status_code, 400)
        self.assertFalse(res.get_json()["success"])

    def test_put_budget_missing_field_rejected(self):
        res = self.client.put("/api/v1/budgets/2026-10", json={"something_else": 500})
        self.assertEqual(res.status_code, 400)

    def test_put_budget_invalid_month_rejected(self):
        res = self.client.put("/api/v1/budgets/2026-1", json={"faltu_limit_inr": 1000})
        self.assertEqual(res.status_code, 400)

    def test_get_budget_returns_none_when_unset(self):
        res = self.client.get("/api/v1/budgets/2099-01")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["success"])
        self.assertIsNone(res.get_json()["data"])

    def test_get_budget_after_set(self):
        self.client.put("/api/v1/budgets/2026-10", json={"faltu_limit_inr": 2000})
        res = self.client.get("/api/v1/budgets/2026-10")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["data"]["faltu_limit_inr"], 2000.0)

    def test_put_budget_upsert(self):
        self.client.put("/api/v1/budgets/2026-10", json={"faltu_limit_inr": 1000})
        res = self.client.put("/api/v1/budgets/2026-10", json={"faltu_limit_inr": 3000})
        self.assertEqual(res.get_json()["data"]["faltu_limit_inr"], 3000.0)

    def test_budget_not_json_rejected(self):
        res = self.client.put("/api/v1/budgets/2026-10", data="not json")
        self.assertEqual(res.status_code, 400)

    # ----------------------------------------------------------
    # Goal API
    # ----------------------------------------------------------
    def test_put_goal_creates_goal(self):
        res = self.client.put("/api/v1/goals/2026-10", json={"target_inr": 5000, "title": "Laptop"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["target_inr"], 5000.0)
        self.assertEqual(data["data"]["target_amount_paise"], 500000)
        self.assertEqual(data["data"]["title"], "Laptop")

    def test_put_goal_zero_rejected(self):
        res = self.client.put("/api/v1/goals/2026-10", json={"target_inr": 0})
        self.assertEqual(res.status_code, 400)

    def test_put_goal_negative_rejected(self):
        res = self.client.put("/api/v1/goals/2026-10", json={"target_inr": -500})
        self.assertEqual(res.status_code, 400)

    def test_put_goal_missing_field_rejected(self):
        res = self.client.put("/api/v1/goals/2026-10", json={"something": 500})
        self.assertEqual(res.status_code, 400)

    def test_put_goal_invalid_month_rejected(self):
        res = self.client.put("/api/v1/goals/2026-1", json={"target_inr": 1000})
        self.assertEqual(res.status_code, 400)
        res2 = self.client.put("/api/v1/goals/2026-13", json={"target_inr": 1000})
        self.assertEqual(res2.status_code, 400)

    def test_get_goal_returns_none_when_unset(self):
        res = self.client.get("/api/v1/goals/2099-01")
        self.assertEqual(res.status_code, 200)
        self.assertIsNone(res.get_json()["data"])

    def test_get_goal_after_set(self):
        self.client.put("/api/v1/goals/2026-10", json={"target_inr": 8000, "title": "Phone"})
        res = self.client.get("/api/v1/goals/2026-10")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["data"]["target_inr"], 8000.0)
        self.assertEqual(res.get_json()["data"]["title"], "Phone")

    def test_put_goal_upsert(self):
        self.client.put("/api/v1/goals/2026-10", json={"target_inr": 3000})
        res = self.client.put("/api/v1/goals/2026-10", json={"target_inr": 7000, "title": "Holiday"})
        self.assertEqual(res.get_json()["data"]["target_inr"], 7000.0)
        self.assertEqual(res.get_json()["data"]["title"], "Holiday")

    def test_goal_not_json_rejected(self):
        res = self.client.put("/api/v1/goals/2026-10", data="not json")
        self.assertEqual(res.status_code, 400)

    # ----------------------------------------------------------
    # Dashboard History API Tests
    # ----------------------------------------------------------
    def test_api_history_empty(self):
        res = self.client.get("/api/v1/dashboard/history?months=6&month=2026-10")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(len(data["data"]), 6)
        for row in data["data"]:
            self.assertEqual(row["income_inr"], 0.0)
            self.assertEqual(row["daily_inr"], 0.0)
            self.assertEqual(row["faltu_inr"], 0.0)
            self.assertEqual(row["balance_inr"], 0.0)

    def test_api_history_one_month(self):
        res = self.client.get("/api/v1/dashboard/history?months=1&month=2026-10")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()["data"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["month"], "2026-10")

    def test_api_history_several_months_with_data(self):
        # Create an income and an expense via API
        self.client.post("/api/v1/incomes", json={"amount_inr": 12000, "source": "Job", "date": "2026-09-15"})
        self.client.post("/api/v1/expenses", json={"amount_inr": 2500, "type": "daily", "sub_category": "Rent", "date": "2026-09-16"})
        self.client.post("/api/v1/expenses", json={"amount_inr": 1000, "type": "faltu", "sub_category": "Games", "date": "2026-10-01"})

        res = self.client.get("/api/v1/dashboard/history?months=3&month=2026-10")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()["data"]
        self.assertEqual(len(data), 3)
        self.assertEqual([d["month"] for d in data], ["2026-08", "2026-09", "2026-10"])

        sep = data[1]
        self.assertEqual(sep["income_inr"], 12000.0)
        self.assertEqual(sep["daily_inr"], 2500.0)
        self.assertEqual(sep["faltu_inr"], 0.0)
        self.assertEqual(sep["balance_inr"], 9500.0)

        oct_data = data[2]
        self.assertEqual(oct_data["faltu_inr"], 1000.0)
        self.assertEqual(oct_data["balance_inr"], -1000.0)

    def test_api_history_invalid_months_parameter(self):
        invalid_queries = [
            "/api/v1/dashboard/history?months=0",
            "/api/v1/dashboard/history?months=-5",
            "/api/v1/dashboard/history?months=25",
            "/api/v1/dashboard/history?months=abc",
            "/api/v1/dashboard/history?months=6.5"
        ]
        for url in invalid_queries:
            with self.subTest(url=url):
                res = self.client.get(url)
                self.assertEqual(res.status_code, 400)
                self.assertFalse(res.get_json()["success"])

    def test_api_history_user_isolation(self):
        # Insert income as user 1
        self.client.post("/api/v1/incomes", json={"amount_inr": 5000, "source": "Bonus", "date": "2026-10-01"})
        # Temporarily mock get_current_user_id to return 2
        from unittest.mock import patch
        with patch("api.v1.dashboard_routes.get_current_user_id", return_value=2):
            res = self.client.get("/api/v1/dashboard/history?months=2&month=2026-10")
            self.assertEqual(res.status_code, 200)
            data = res.get_json()["data"]
            for row in data:
                self.assertEqual(row["income_inr"], 0.0)

    # ----------------------------------------------------------
    # Dashboard summary fields
    # ----------------------------------------------------------
    def test_dashboard_summary_contains_phase2_fields(self):
        res = self.client.get("/api/v1/dashboard/summary?month=2099-01")
        self.assertEqual(res.status_code, 200)
        s = res.get_json()["data"]
        self.assertIn("faltu_status", s)
        self.assertIn("faltu_limit_inr", s)
        self.assertIn("faltu_used_percent_of_limit", s)
        self.assertIn("savings_status", s)
        self.assertIn("savings_goal_inr", s)
        self.assertIn("savings_progress_percent", s)
        self.assertEqual(s["faltu_status"], "none")
        self.assertEqual(s["savings_status"], "none")


if __name__ == "__main__":
    unittest.main()
