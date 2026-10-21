import os
import unittest
from datetime import datetime
from pathlib import Path

from config import Config
from database.db import init_db
from app import create_app

class TestPresetService(unittest.TestCase):
    """Unit tests for services/preset_service.py."""

    def setUp(self):
        self.test_db_path = str(Path(__file__).resolve().parent / "test_presets_services.db")
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

    def test_create_and_get_presets(self):
        from services.preset_service import create_preset, get_presets, get_preset_by_id
        # Initially empty
        self.assertEqual(get_presets(1), [])

        preset = create_preset(1, "Chai", 15.0, "faltu", "Snacks", "☕")
        self.assertEqual(preset["title"], "Chai")
        self.assertEqual(preset["amount_paise"], 1500)
        self.assertEqual(preset["amount_inr"], 15.0)
        self.assertEqual(preset["type"], "faltu")
        self.assertEqual(preset["sub_category"], "Snacks")
        self.assertEqual(preset["icon"], "☕")

        all_presets = get_presets(1)
        self.assertEqual(len(all_presets), 1)
        self.assertEqual(all_presets[0]["title"], "Chai")

        single = get_preset_by_id(1, preset["id"])
        self.assertIsNotNone(single)
        self.assertEqual(single["amount_inr"], 15.0)

    def test_create_preset_validations(self):
        from services.preset_service import create_preset
        # Empty title
        with self.assertRaises(ValueError):
            create_preset(1, "", 10.0, "daily")
        with self.assertRaises(ValueError):
            create_preset(1, "   ", 10.0, "daily")

        # Title > 30 chars
        with self.assertRaises(ValueError):
            create_preset(1, "A" * 31, 10.0, "daily")

        # Amount <= 0
        with self.assertRaises(ValueError):
            create_preset(1, "Valid Title", 0, "daily")
        with self.assertRaises(ValueError):
            create_preset(1, "Valid Title", -5, "daily")

        # Invalid type
        with self.assertRaises(ValueError):
            create_preset(1, "Valid Title", 10.0, "invalid_type")

        # Icon > 4 characters
        with self.assertRaises(ValueError):
            create_preset(1, "Valid Title", 10.0, "daily", icon="Toolong")

    def test_max_12_presets_limit(self):
        from services.preset_service import create_preset
        for i in range(1, 13):
            create_preset(1, f"Preset {i}", 10.0 * i, "daily")

        # 13th preset must raise ValueError
        with self.assertRaises(ValueError) as ctx:
            create_preset(1, "Preset 13", 100.0, "daily")
        self.assertIn("12", str(ctx.exception))

    def test_preset_user_isolation(self):
        from services.preset_service import create_preset, get_presets, get_preset_by_id, update_preset, delete_preset
        p1 = create_preset(1, "User1 Item", 50.0, "daily")

        # User 2 cannot see it
        self.assertEqual(get_presets(2), [])
        self.assertIsNone(get_preset_by_id(2, p1["id"]))

        # User 2 cannot update or delete it
        with self.assertRaises(ValueError):
            update_preset(2, p1["id"], title="Hacked")
        with self.assertRaises(ValueError):
            delete_preset(2, p1["id"])

    def test_update_preset(self):
        from services.preset_service import create_preset, update_preset
        p = create_preset(1, "Original", 20.0, "faltu", "Cafe", "⚡")
        updated = update_preset(1, p["id"], title="Updated", amount_inr=25.0, preset_type="daily", icon="🍔")
        self.assertEqual(updated["title"], "Updated")
        self.assertEqual(updated["amount_inr"], 25.0)
        self.assertEqual(updated["type"], "daily")
        self.assertEqual(updated["icon"], "🍔")

    def test_delete_preset(self):
        from services.preset_service import create_preset, get_presets, delete_preset
        p = create_preset(1, "To Delete", 10.0, "daily")
        self.assertEqual(len(get_presets(1)), 1)
        res = delete_preset(1, p["id"])
        self.assertTrue(res)
        self.assertEqual(len(get_presets(1)), 0)

    def test_use_preset_creates_expense(self):
        from services.preset_service import create_preset, use_preset
        from services.expense_service import get_expenses
        p = create_preset(1, "Metro Card", 100.0, "daily", sub_category="Travel", icon="🛺")
        expense = use_preset(1, p["id"])

        today = datetime.now().strftime("%Y-%m-%d")
        current_month = datetime.now().strftime("%Y-%m")

        self.assertEqual(expense["amount_inr"], 100.0)
        self.assertEqual(expense["type"], "daily")
        self.assertEqual(expense["sub_category"], "Travel")
        self.assertEqual(expense["date"], today)
        self.assertEqual(expense["month"], current_month)

        # Check expense is logged in expenses table
        all_exp = get_expenses(1, month=current_month)
        self.assertEqual(len(all_exp), 1)
        self.assertEqual(all_exp[0]["id"], expense["id"])


class TestPresetAPI(unittest.TestCase):
    """Integration tests for /api/v1/presets endpoints."""

    def setUp(self):
        self.test_db_path = str(Path(__file__).resolve().parent / "test_presets_api.db")
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

        # Log in as user 1
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1

    def tearDown(self):
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    def test_get_presets_empty_for_new_user(self):
        res = self.client.get("/api/v1/presets")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"], [])

    def test_post_preset_success(self):
        payload = {
            "title": "Chai",
            "amount_inr": 15.0,
            "type": "faltu",
            "sub_category": "Snacks",
            "icon": "☕"
        }
        res = self.client.post("/api/v1/presets", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["title"], "Chai")
        self.assertEqual(data["data"]["amount_inr"], 15.0)
        self.assertEqual(data["data"]["type"], "faltu")

    def test_post_preset_invalid_body(self):
        # Missing title
        res = self.client.post("/api/v1/presets", json={"amount_inr": 10, "type": "daily"})
        self.assertEqual(res.status_code, 400)

        # Missing amount
        res = self.client.post("/api/v1/presets", json={"title": "Tea", "type": "daily"})
        self.assertEqual(res.status_code, 400)

        # Negative amount
        res = self.client.post("/api/v1/presets", json={"title": "Tea", "amount_inr": -5, "type": "daily"})
        self.assertEqual(res.status_code, 400)

        # Invalid type
        res = self.client.post("/api/v1/presets", json={"title": "Tea", "amount_inr": 10, "type": "other"})
        self.assertEqual(res.status_code, 400)

    def test_put_preset(self):
        create_res = self.client.post("/api/v1/presets", json={"title": "Auto", "amount_inr": 30, "type": "daily"})
        preset_id = create_res.get_json()["data"]["id"]

        update_res = self.client.put(f"/api/v1/presets/{preset_id}", json={"amount_inr": 40, "title": "Auto Rickshaw"})
        self.assertEqual(update_res.status_code, 200)
        updated = update_res.get_json()["data"]
        self.assertEqual(updated["amount_inr"], 40.0)
        self.assertEqual(updated["title"], "Auto Rickshaw")

    def test_delete_preset(self):
        create_res = self.client.post("/api/v1/presets", json={"title": "Snacks", "amount_inr": 20, "type": "faltu"})
        preset_id = create_res.get_json()["data"]["id"]

        del_res = self.client.delete(f"/api/v1/presets/{preset_id}")
        self.assertEqual(del_res.status_code, 200)

        get_res = self.client.get("/api/v1/presets")
        self.assertEqual(get_res.get_json()["data"], [])

    def test_use_preset_endpoint(self):
        create_res = self.client.post("/api/v1/presets", json={
            "title": "Chai",
            "amount_inr": 15,
            "type": "faltu",
            "sub_category": "Tea"
        })
        preset_id = create_res.get_json()["data"]["id"]

        use_res = self.client.post(f"/api/v1/presets/{preset_id}/use")
        self.assertEqual(use_res.status_code, 201)
        expense = use_res.get_json()["data"]
        today = datetime.now().strftime("%Y-%m-%d")

        self.assertEqual(expense["amount_inr"], 15.0)
        self.assertEqual(expense["type"], "faltu")
        self.assertEqual(expense["sub_category"], "Tea")
        self.assertEqual(expense["date"], today)

    def test_12_presets_limit_via_api(self):
        for i in range(1, 13):
            r = self.client.post("/api/v1/presets", json={"title": f"P{i}", "amount_inr": 10, "type": "daily"})
            self.assertEqual(r.status_code, 201)

        # 13th fails with 400
        r13 = self.client.post("/api/v1/presets", json={"title": "P13", "amount_inr": 10, "type": "daily"})
        self.assertEqual(r13.status_code, 400)

    def test_user_isolation_via_api(self):
        create_res = self.client.post("/api/v1/presets", json={"title": "Private Item", "amount_inr": 50, "type": "daily"})
        preset_id = create_res.get_json()["data"]["id"]

        from unittest.mock import patch
        # User 2 tries to use or delete User 1's preset
        with patch("api.v1.preset_routes.get_current_user_id", return_value=2):
            del_res = self.client.delete(f"/api/v1/presets/{preset_id}")
            self.assertEqual(del_res.status_code, 404)

            use_res = self.client.post(f"/api/v1/presets/{preset_id}/use")
            self.assertEqual(use_res.status_code, 404)


if __name__ == "__main__":
    unittest.main()
