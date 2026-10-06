import os
import json
import unittest
from pathlib import Path

from config import Config
from database.db import init_db
from app import create_app

class TestSavewiseAPI(unittest.TestCase):
    def setUp(self):
        """Set up an isolated test database and Flask test client before each test."""
        self.test_db_path = str(Path(__file__).resolve().parent / "test_api_savewise.db")
        Config.DATABASE_PATH = self.test_db_path

        # Clean up any leftover database file
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

        # Initialize test schema & seed default user
        init_db()

        class TestConfig(Config):
            TESTING = True
            DATABASE_PATH = self.test_db_path

        self.app = create_app(TestConfig)
        self.client = self.app.test_client()

    def tearDown(self):
        """Remove temporary database file after test completion."""
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    # ==========================================================
    # 1. INCOME API ENDPOINT TESTS
    # ==========================================================
    def test_post_income_success(self):
        res = self.client.post(
            "/api/v1/incomes",
            data=json.dumps({
                "amount_inr": 7500.50,
                "source": "Scholarship",
                "date": "2026-10-01",
                "note": "Merit award"
            }),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["amount_inr"], 7500.50)
        self.assertEqual(data["data"]["amount_paise"], 750050)
        self.assertEqual(data["data"]["source"], "Scholarship")
        self.assertEqual(data["data"]["month"], "2026-10")

    def test_post_income_invalid_body_or_type(self):
        # Missing Content-Type application/json
        res = self.client.post("/api/v1/incomes", data="not json")
        self.assertEqual(res.status_code, 400)
        self.assertFalse(res.get_json()["success"])

        # Non-positive amount
        res = self.client.post(
            "/api/v1/incomes",
            json={"amount_inr": -100, "source": "Freelance", "date": "2026-10-01"}
        )
        self.assertEqual(res.status_code, 400)
        self.assertFalse(res.get_json()["success"])

        # Blank source
        res = self.client.post(
            "/api/v1/incomes",
            json={"amount_inr": 500, "source": "   ", "date": "2026-10-01"}
        )
        self.assertEqual(res.status_code, 400)
        self.assertFalse(res.get_json()["success"])

        # Invalid date
        res = self.client.post(
            "/api/v1/incomes",
            json={"amount_inr": 500, "source": "Salary", "date": "2026/10/01"}
        )
        self.assertEqual(res.status_code, 400)
        self.assertFalse(res.get_json()["success"])

    def test_get_incomes_list_and_filter(self):
        # Add income in October and November
        self.client.post("/api/v1/incomes", json={"amount_inr": 2000, "source": "A", "date": "2026-10-05"})
        self.client.post("/api/v1/incomes", json={"amount_inr": 3000, "source": "B", "date": "2026-11-05"})

        # Filter by October
        res = self.client.get("/api/v1/incomes?month=2026-10")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(len(data["data"]), 1)
        self.assertEqual(data["data"][0]["source"], "A")

        # Missing month query parameter defaults to current month
        res_default = self.client.get("/api/v1/incomes")
        self.assertEqual(res_default.status_code, 200)
        self.assertTrue(res_default.get_json()["success"])

    def test_income_by_id_and_404(self):
        create_res = self.client.post(
            "/api/v1/incomes",
            json={"amount_inr": 1500, "source": "Gift", "date": "2026-10-10"}
        )
        income_id = create_res.get_json()["data"]["id"]

        # GET existing
        get_res = self.client.get(f"/api/v1/incomes/{income_id}")
        self.assertEqual(get_res.status_code, 200)
        self.assertEqual(get_res.get_json()["data"]["source"], "Gift")

        # GET non-existent
        res_404 = self.client.get("/api/v1/incomes/99999")
        self.assertEqual(res_404.status_code, 404)
        self.assertFalse(res_404.get_json()["success"])

    def test_update_and_delete_income(self):
        create_res = self.client.post(
            "/api/v1/incomes",
            json={"amount_inr": 1000, "source": "Freelance", "date": "2026-10-10"}
        )
        income_id = create_res.get_json()["data"]["id"]

        # PUT update
        update_res = self.client.put(
            f"/api/v1/incomes/{income_id}",
            json={"amount_inr": 1200, "source": "Freelance Bonus"}
        )
        self.assertEqual(update_res.status_code, 200)
        self.assertEqual(update_res.get_json()["data"]["amount_inr"], 1200.0)
        self.assertEqual(update_res.get_json()["data"]["source"], "Freelance Bonus")

        # PUT 404
        bad_put = self.client.put("/api/v1/incomes/99999", json={"amount_inr": 500})
        self.assertEqual(bad_put.status_code, 404)

        # DELETE existing
        del_res = self.client.delete(f"/api/v1/incomes/{income_id}")
        self.assertEqual(del_res.status_code, 200)
        self.assertTrue(del_res.get_json()["success"])

        # DELETE again -> 404
        del_404 = self.client.delete(f"/api/v1/incomes/{income_id}")
        self.assertEqual(del_404.status_code, 404)

    # ==========================================================
    # 2. EXPENSE API ENDPOINT TESTS
    # ==========================================================
    def test_post_expense_daily_and_faltu(self):
        # Create daily
        res1 = self.client.post(
            "/api/v1/expenses",
            json={
                "amount_inr": 60.00,
                "type": "daily",
                "sub_category": "Bus Pass",
                "date": "2026-10-02"
            }
        )
        self.assertEqual(res1.status_code, 201)
        data1 = res1.get_json()
        self.assertTrue(data1["success"])
        self.assertEqual(data1["data"]["type"], "daily")
        self.assertEqual(data1["data"]["amount_paise"], 6000)

        # Create faltu (also testing 'expense_type' alias)
        res2 = self.client.post(
            "/api/v1/expenses",
            json={
                "amount_inr": 250.00,
                "expense_type": "faltu",
                "sub_category": "Snacks",
                "date": "2026-10-02"
            }
        )
        self.assertEqual(res2.status_code, 201)
        data2 = res2.get_json()
        self.assertEqual(data2["data"]["type"], "faltu")
        self.assertEqual(data2["data"]["amount_paise"], 25000)

    def test_post_expense_validation(self):
        # Invalid type
        res = self.client.post(
            "/api/v1/expenses",
            json={"amount_inr": 50, "type": "luxury", "sub_category": "Watch", "date": "2026-10-02"}
        )
        self.assertEqual(res.status_code, 400)
        self.assertFalse(res.get_json()["success"])

        # Non-positive amount
        res = self.client.post(
            "/api/v1/expenses",
            json={"amount_inr": 0, "type": "daily", "sub_category": "Lunch", "date": "2026-10-02"}
        )
        self.assertEqual(res.status_code, 400)

        # Empty body
        res = self.client.post("/api/v1/expenses", data="", content_type="application/json")
        self.assertEqual(res.status_code, 400)

    def test_get_expenses_list_and_filters(self):
        self.client.post("/api/v1/expenses", json={"amount_inr": 50, "type": "daily", "sub_category": "Tea", "date": "2026-10-01"})
        self.client.post("/api/v1/expenses", json={"amount_inr": 150, "type": "faltu", "sub_category": "Ice cream", "date": "2026-10-02"})

        # Filter by type=faltu
        res = self.client.get("/api/v1/expenses?month=2026-10&type=faltu")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(len(data["data"]), 1)
        self.assertEqual(data["data"][0]["sub_category"], "Ice cream")

    def test_expense_crud_and_404(self):
        create_res = self.client.post(
            "/api/v1/expenses",
            json={"amount_inr": 80, "type": "daily", "sub_category": "Lunch", "date": "2026-10-03"}
        )
        exp_id = create_res.get_json()["data"]["id"]

        # GET existing
        get_res = self.client.get(f"/api/v1/expenses/{exp_id}")
        self.assertEqual(get_res.status_code, 200)

        # GET non-existent
        res_404 = self.client.get("/api/v1/expenses/99999")
        self.assertEqual(res_404.status_code, 404)

        # PUT update
        update_res = self.client.put(f"/api/v1/expenses/{exp_id}", json={"amount_inr": 95})
        self.assertEqual(update_res.status_code, 200)
        self.assertEqual(update_res.get_json()["data"]["amount_inr"], 95.0)

        # DELETE
        del_res = self.client.delete(f"/api/v1/expenses/{exp_id}")
        self.assertEqual(del_res.status_code, 200)

        # DELETE 404
        del_404 = self.client.delete(f"/api/v1/expenses/{exp_id}")
        self.assertEqual(del_404.status_code, 404)

    # ==========================================================
    # 3. DASHBOARD SUMMARY ENDPOINT TESTS
    # ==========================================================
    def test_dashboard_summary_calculation(self):
        # 10,000 Income
        self.client.post("/api/v1/incomes", json={"amount_inr": 10000, "source": "Allowance", "date": "2026-10-01"})
        # 3,000 Daily
        self.client.post("/api/v1/expenses", json={"amount_inr": 3000, "type": "daily", "sub_category": "Rent", "date": "2026-10-02"})
        # 1,000 Faltu
        self.client.post("/api/v1/expenses", json={"amount_inr": 1000, "type": "faltu", "sub_category": "Gaming", "date": "2026-10-03"})

        res = self.client.get("/api/v1/dashboard/summary?month=2026-10")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        summary = data["data"]

        self.assertEqual(summary["total_income_inr"], 10000.0)
        self.assertEqual(summary["total_daily_inr"], 3000.0)
        self.assertEqual(summary["total_faltu_inr"], 1000.0)
        self.assertEqual(summary["total_expenses_inr"], 4000.0)
        self.assertEqual(summary["balance_inr"], 6000.0)
        self.assertEqual(summary["faltu_percentage"], 25.0)
        self.assertEqual(summary["faltu_percent_of_income"], 10.0)

    def test_dashboard_summary_zero_cases_and_empty_month(self):
        # Zero income, zero expense month
        res = self.client.get("/api/v1/dashboard/summary?month=2027-05")
        self.assertEqual(res.status_code, 200)
        summary = res.get_json()["data"]
        self.assertEqual(summary["total_income_inr"], 0.0)
        self.assertEqual(summary["total_expenses_inr"], 0.0)
        self.assertEqual(summary["balance_inr"], 0.0)
        self.assertEqual(summary["faltu_percentage"], 0.0)
        self.assertEqual(summary["faltu_percent_of_income"], 0.0)

        # Only faltu expense, 0 income
        self.client.post("/api/v1/expenses", json={"amount_inr": 400, "type": "faltu", "sub_category": "Treat", "date": "2027-05-02"})
        res2 = self.client.get("/api/v1/dashboard/summary?month=2027-05")
        self.assertEqual(res2.status_code, 200)
        summary2 = res2.get_json()["data"]
        self.assertEqual(summary2["balance_inr"], -400.0)
        self.assertEqual(summary2["faltu_percentage"], 100.0)
        self.assertEqual(summary2["faltu_percent_of_income"], 0.0)

    # ==========================================================
    # 4. CORS AND GLOBAL 404 HANDLER TESTS
    # ==========================================================
    def test_cors_headers_present(self):
        res = self.client.get("/api/v1/dashboard/summary")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Access-Control-Allow-Origin", res.headers)
        self.assertEqual(res.headers["Access-Control-Allow-Origin"], "*")

    def test_non_existent_api_route_returns_404_json(self):
        res = self.client.get("/api/v1/non_existent_endpoint")
        self.assertEqual(res.status_code, 404)
        data = res.get_json()
        self.assertFalse(data["success"])
        self.assertIn("not found", data["error"].lower())

if __name__ == "__main__":
    unittest.main()
