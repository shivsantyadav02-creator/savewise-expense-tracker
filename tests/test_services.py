import os
import unittest
from pathlib import Path
from flask import Flask

from config import Config
from database.db import get_db, init_app, init_db
from services.income_service import (
    create_income, get_incomes, get_income_by_id, update_income, delete_income
)
from services.expense_service import (
    create_expense, get_expenses, get_expense_by_id, update_expense, delete_expense
)
from services.dashboard_service import get_monthly_summary

class TestSavewiseServices(unittest.TestCase):
    def setUp(self):
        """Set up an isolated test database before each test run."""
        self.test_db_path = str(Path(__file__).resolve().parent / "test_savewise.db")
        Config.DATABASE_PATH = self.test_db_path
        
        # Remove old test DB if present
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

        # Initialize schema and seed user id=1
        init_db()

        # Seed a second user for testing multi-user isolation
        conn = get_db() if False else None
        # We need an app context
        self.app = Flask(__name__)
        init_app(self.app)
        self.app_context = self.app.app_context()
        self.app_context.push()

        # Create user 2
        db = get_db()
        db.execute(
            "INSERT INTO users (id, username, email) VALUES (2, 'second_user', 'second@savewise.local')"
        )
        db.commit()

    def tearDown(self):
        """Clean up app context and delete test database file."""
        self.app_context.pop()
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    # ==========================================================
    # 1. INCOME SERVICE TESTS
    # ==========================================================
    def test_create_income_success(self):
        income = create_income(
            user_id=1,
            amount_inr=5000.50,
            source="Pocket Money",
            date="2026-10-01",
            note="Monthly allowance"
        )
        self.assertEqual(income["amount_paise"], 500050)
        self.assertEqual(income["amount_inr"], 5000.50)
        self.assertEqual(income["source"], "Pocket Money")
        self.assertEqual(income["month"], "2026-10")
        self.assertEqual(income["user_id"], 1)

    def test_create_income_invalid_inputs(self):
        # Negative / Zero amount
        with self.assertRaises(ValueError):
            create_income(1, 0, "Pocket Money", "2026-10-01")
        with self.assertRaises(ValueError):
            create_income(1, -500, "Pocket Money", "2026-10-01")

        # Empty source
        with self.assertRaises(ValueError):
            create_income(1, 1000, "", "2026-10-01")

        # Invalid date
        with self.assertRaises(ValueError):
            create_income(1, 1000, "Pocket Money", "not-a-date")

        # Invalid user_id
        with self.assertRaises(ValueError):
            create_income(0, 1000, "Pocket Money", "2026-10-01")

    def test_income_isolation_and_crud(self):
        # User 1 creates income
        inc1 = create_income(1, 2000, "Freelance", "2026-10-02")
        # User 2 creates income
        inc2 = create_income(2, 3000, "Salary", "2026-10-03")

        # User 1 cannot see User 2's income
        self.assertIsNone(get_income_by_id(user_id=1, income_id=inc2["id"]))
        user1_incomes = get_incomes(user_id=1)
        self.assertEqual(len(user1_incomes), 1)
        self.assertEqual(user1_incomes[0]["id"], inc1["id"])

        # User 1 updates their own income
        updated = update_income(user_id=1, income_id=inc1["id"], amount_inr=2500, source="Freelance Web")
        self.assertEqual(updated["amount_inr"], 2500.0)
        self.assertEqual(updated["source"], "Freelance Web")

        # User 1 deletes their income
        self.assertTrue(delete_income(user_id=1, income_id=inc1["id"]))
        self.assertIsNone(get_income_by_id(user_id=1, income_id=inc1["id"]))

    # ==========================================================
    # 2. EXPENSE SERVICE TESTS
    # ==========================================================
    def test_create_expense_daily_and_faltu(self):
        # Daily expense
        daily = create_expense(
            user_id=1,
            amount_inr=50.00,
            expense_type="daily",
            sub_category="Metro Fare",
            date="2026-10-05"
        )
        self.assertEqual(daily["type"], "daily")
        self.assertEqual(daily["amount_paise"], 5000)
        self.assertEqual(daily["amount_inr"], 50.00)
        self.assertEqual(daily["month"], "2026-10")

        # Faltu expense
        faltu = create_expense(
            user_id=1,
            amount_inr=150.00,
            expense_type="faltu",
            sub_category="Cafe Brownie",
            date="2026-10-05"
        )
        self.assertEqual(faltu["type"], "faltu")
        self.assertEqual(faltu["amount_paise"], 15000)
        self.assertEqual(faltu["amount_inr"], 150.00)

    def test_create_expense_validation(self):
        # Invalid expense type
        with self.assertRaises(ValueError):
            create_expense(1, 100, "luxury", "Watch", "2026-10-05")

        # Empty sub-category
        with self.assertRaises(ValueError):
            create_expense(1, 100, "daily", "   ", "2026-10-05")

        # Non-positive amount
        with self.assertRaises(ValueError):
            create_expense(1, 0, "daily", "Food", "2026-10-05")

    def test_expense_isolation_and_filters(self):
        # User 1 creates daily and faltu in Oct and Nov
        create_expense(1, 100, "daily", "Lunch", "2026-10-01")
        create_expense(1, 50, "faltu", "Soda", "2026-10-02")
        create_expense(1, 200, "daily", "Groceries", "2026-11-01")

        # Filter by month '2026-10'
        oct_expenses = get_expenses(user_id=1, month="2026-10")
        self.assertEqual(len(oct_expenses), 2)

        # Filter by type 'faltu' in '2026-10'
        oct_faltu = get_expenses(user_id=1, month="2026-10", expense_type="faltu")
        self.assertEqual(len(oct_faltu), 1)
        self.assertEqual(oct_faltu[0]["sub_category"], "Soda")

        # User 2 cannot delete User 1's expense
        with self.assertRaises(ValueError):
            delete_expense(user_id=2, expense_id=oct_expenses[0]["id"])

    # ==========================================================
    # 3. DASHBOARD SERVICE TESTS (Financial Math & Division by Zero)
    # ==========================================================
    def test_dashboard_summary_normal_case(self):
        user_id = 1
        month = "2026-10"

        # Income: 10,000 INR
        create_income(user_id, 10000.0, "Salary", "2026-10-01")

        # Expenses: Daily = 3000 INR, Faltu = 1000 INR -> Total = 4000 INR
        create_expense(user_id, 3000.0, "daily", "Rent & Groceries", "2026-10-02")
        create_expense(user_id, 1000.0, "faltu", "Shopping", "2026-10-03")

        summary = get_monthly_summary(user_id, month=month)

        self.assertEqual(summary["total_income_inr"], 10000.0)
        self.assertEqual(summary["total_daily_inr"], 3000.0)
        self.assertEqual(summary["total_faltu_inr"], 1000.0)
        self.assertEqual(summary["total_expenses_inr"], 4000.0)
        self.assertEqual(summary["balance_inr"], 6000.0)

        # faltu_percentage = (1000 / 4000) * 100 = 25.0%
        self.assertEqual(summary["faltu_percentage"], 25.0)

        # faltu_percent_of_income = (1000 / 10000) * 100 = 10.0%
        self.assertEqual(summary["faltu_percent_of_income"], 10.0)

    def test_dashboard_zero_income_case(self):
        """Tests that 0 income does not trigger ZeroDivisionError and tracks negative balance."""
        user_id = 1
        month = "2026-10"

        # No income added
        create_expense(user_id, 500.0, "faltu", "Online Game", "2026-10-04")

        summary = get_monthly_summary(user_id, month=month)

        self.assertEqual(summary["total_income_inr"], 0.0)
        self.assertEqual(summary["total_faltu_inr"], 500.0)
        self.assertEqual(summary["balance_inr"], -500.0)

        # Faltu is 100% of expenses
        self.assertEqual(summary["faltu_percentage"], 100.0)

        # Handled division by zero for income -> must be 0.0
        self.assertEqual(summary["faltu_percent_of_income"], 0.0)

    def test_dashboard_zero_expense_case(self):
        """Tests that 0 expenses does not trigger ZeroDivisionError."""
        user_id = 1
        month = "2026-10"

        create_income(user_id, 5000.0, "Scholarship", "2026-10-01")

        summary = get_monthly_summary(user_id, month=month)

        self.assertEqual(summary["total_income_inr"], 5000.0)
        self.assertEqual(summary["total_expenses_inr"], 0.0)
        self.assertEqual(summary["balance_inr"], 5000.0)

        # Division by zero handled safely
        self.assertEqual(summary["faltu_percentage"], 0.0)
        self.assertEqual(summary["faltu_percent_of_income"], 0.0)

    def test_dashboard_empty_month_case(self):
        """Tests a brand new month with zero activity."""
        summary = get_monthly_summary(user_id=1, month="2027-01")
        self.assertEqual(summary["total_income_inr"], 0.0)
        self.assertEqual(summary["total_expenses_inr"], 0.0)
        self.assertEqual(summary["balance_inr"], 0.0)
        self.assertEqual(summary["faltu_percentage"], 0.0)
        self.assertEqual(summary["faltu_percent_of_income"], 0.0)

if __name__ == "__main__":
    unittest.main()
