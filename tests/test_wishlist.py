import os
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

from config import Config
from database.db import init_db
from app import create_app
from utils.clock import to_iso_utc

class TestWishlistService(unittest.TestCase):
    """Unit tests for services/wishlist_service.py with time simulation."""

    def setUp(self):
        self.test_db_path = str(Path(__file__).resolve().parent / "test_wishlist_services.db")
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

        # Fixed reference start time
        self.start_time = datetime(2026, 10, 6, 12, 0, 0, tzinfo=timezone.utc)

    def tearDown(self):
        self.ctx.pop()
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    def test_create_wishlist_item_and_timestamps(self):
        from services.wishlist_service import create_wishlist_item

        with patch("services.wishlist_service.now_utc", return_value=self.start_time):
            item = create_wishlist_item(1, "Headphones", 3500.0, "Electronics")

        self.assertEqual(item["item_name"], "Headphones")
        self.assertEqual(item["estimated_amount_paise"], 350000)
        self.assertEqual(item["estimated_amount_inr"], 3500.0)
        self.assertEqual(item["sub_category"], "Electronics")
        self.assertEqual(item["status"], "waiting")
        self.assertEqual(item["created_at"], to_iso_utc(self.start_time))
        self.assertEqual(item["unlock_at"], to_iso_utc(self.start_time + timedelta(hours=24)))
        self.assertFalse(item["is_unlocked"])
        self.assertEqual(item["seconds_remaining"], 86400)

    def test_create_wishlist_validations(self):
        from services.wishlist_service import create_wishlist_item

        # Empty name
        with self.assertRaises(ValueError):
            create_wishlist_item(1, "", 500.0)
        with self.assertRaises(ValueError):
            create_wishlist_item(1, "   ", 500.0)

        # Name > 60 chars
        with self.assertRaises(ValueError):
            create_wishlist_item(1, "X" * 61, 500.0)

        # Amount <= 0
        with self.assertRaises(ValueError):
            create_wishlist_item(1, "Sneakers", 0)
        with self.assertRaises(ValueError):
            create_wishlist_item(1, "Sneakers", -100)

    def test_buy_before_24h_fails(self):
        from services.wishlist_service import create_wishlist_item, buy_wishlist_item

        with patch("services.wishlist_service.now_utc", return_value=self.start_time):
            item = create_wishlist_item(1, "Watch", 2000.0)

        # Attempt to buy after only 5 hours
        five_hours_later = self.start_time + timedelta(hours=5)
        with patch("services.wishlist_service.now_utc", return_value=five_hours_later):
            with self.assertRaises(ValueError) as ctx:
                buy_wishlist_item(1, item["id"])
            self.assertIn("Please wait", str(ctx.exception))
            self.assertIn("19h", str(ctx.exception))

    def test_buy_at_exactly_24h_works(self):
        from services.wishlist_service import create_wishlist_item, buy_wishlist_item

        with patch("services.wishlist_service.now_utc", return_value=self.start_time):
            item = create_wishlist_item(1, "Coffee Maker", 4500.0, "Kitchen")

        # Simulate exactly 24 hours later
        exact_24h = self.start_time + timedelta(hours=24)
        with patch("services.wishlist_service.now_utc", return_value=exact_24h):
            result = buy_wishlist_item(1, item["id"])

        self.assertEqual(result["item"]["status"], "bought")
        self.assertEqual(result["type"], "faltu")
        self.assertEqual(result["amount_inr"], 4500.0)
        self.assertEqual(result["wishlist_item_id"], item["id"])
        self.assertEqual(result["note"], "Coffee Maker")
        self.assertEqual(result["date"], "2026-10-07")

    def test_buy_after_24h_works(self):
        from services.wishlist_service import create_wishlist_item, buy_wishlist_item

        with patch("services.wishlist_service.now_utc", return_value=self.start_time):
            item = create_wishlist_item(1, "Shoes", 3000.0)

        # Simulate 30 hours later
        thirty_hours_later = self.start_time + timedelta(hours=30)
        with patch("services.wishlist_service.now_utc", return_value=thirty_hours_later):
            result = buy_wishlist_item(1, item["id"])

        self.assertEqual(result["item"]["status"], "bought")
        self.assertEqual(result["type"], "faltu")
        self.assertEqual(result["amount_inr"], 3000.0)

    def test_double_buy_fails_exactly_one_expense(self):
        from services.wishlist_service import create_wishlist_item, buy_wishlist_item
        from database.db import get_db

        with patch("services.wishlist_service.now_utc", return_value=self.start_time):
            item = create_wishlist_item(1, "Speaker", 2500.0)

        exact_24h = self.start_time + timedelta(hours=24)
        with patch("services.wishlist_service.now_utc", return_value=exact_24h):
            # First buy succeeds
            buy_wishlist_item(1, item["id"])

            # Second buy must fail
            with self.assertRaises(ValueError):
                buy_wishlist_item(1, item["id"])

        # Verify exactly one expense exists in the database
        db = get_db()
        count = db.execute("SELECT COUNT(*) AS total FROM expenses WHERE wishlist_item_id = ?", (item["id"],)).fetchone()["total"]
        self.assertEqual(count, 1)

    def test_drop_early_works(self):
        from services.wishlist_service import create_wishlist_item, drop_wishlist_item

        with patch("services.wishlist_service.now_utc", return_value=self.start_time):
            item = create_wishlist_item(1, "Jacket", 5000.0)

        # Drop 10 minutes later (early drop)
        ten_mins_later = self.start_time + timedelta(minutes=10)
        with patch("services.wishlist_service.now_utc", return_value=ten_mins_later):
            dropped = drop_wishlist_item(1, item["id"])

        self.assertEqual(dropped["status"], "dropped")

    def test_cannot_buy_dropped_item(self):
        from services.wishlist_service import create_wishlist_item, drop_wishlist_item, buy_wishlist_item

        with patch("services.wishlist_service.now_utc", return_value=self.start_time):
            item = create_wishlist_item(1, "Drone", 15000.0)
            drop_wishlist_item(1, item["id"])

        two_days_later = self.start_time + timedelta(days=2)
        with patch("services.wishlist_service.now_utc", return_value=two_days_later):
            with self.assertRaises(ValueError):
                buy_wishlist_item(1, item["id"])

    def test_cannot_drop_bought_item(self):
        from services.wishlist_service import create_wishlist_item, buy_wishlist_item, drop_wishlist_item

        with patch("services.wishlist_service.now_utc", return_value=self.start_time):
            item = create_wishlist_item(1, "Keyboard", 1200.0)

        exact_24h = self.start_time + timedelta(hours=24)
        with patch("services.wishlist_service.now_utc", return_value=exact_24h):
            buy_wishlist_item(1, item["id"])

            with self.assertRaises(ValueError):
                drop_wishlist_item(1, item["id"])

    def test_editing_does_not_change_unlock_at(self):
        from services.wishlist_service import create_wishlist_item, update_wishlist_item

        with patch("services.wishlist_service.now_utc", return_value=self.start_time):
            item = create_wishlist_item(1, "Old Name", 1000.0)
            original_unlock_at = item["unlock_at"]

            # Edit name and amount
            updated = update_wishlist_item(1, item["id"], item_name="New Name", estimated_amount_inr=1500.0)

        self.assertEqual(updated["item_name"], "New Name")
        self.assertEqual(updated["estimated_amount_inr"], 1500.0)
        self.assertEqual(updated["unlock_at"], original_unlock_at)

    def test_summary_totals(self):
        from services.wishlist_service import create_wishlist_item, drop_wishlist_item, buy_wishlist_item, get_wishlist_summary

        with patch("services.wishlist_service.now_utc", return_value=self.start_time):
            # 1 waiting: 1000 INR
            create_wishlist_item(1, "Item Waiting", 1000.0)

            # 2 dropped: 500 + 300 = 800 INR
            d1 = create_wishlist_item(1, "Dropped 1", 500.0)
            d2 = create_wishlist_item(1, "Dropped 2", 300.0)
            drop_wishlist_item(1, d1["id"])
            drop_wishlist_item(1, d2["id"])

            # 1 bought: 200 INR (after 24h)
            b1 = create_wishlist_item(1, "Bought 1", 200.0)

        later = self.start_time + timedelta(hours=25)
        with patch("services.wishlist_service.now_utc", return_value=later):
            buy_wishlist_item(1, b1["id"])
            summary = get_wishlist_summary(1)

        self.assertEqual(summary["items_waiting"], 1)
        self.assertEqual(summary["items_dropped"], 2)
        self.assertEqual(summary["amount_saved_inr"], 800.0)

    def test_user_isolation(self):
        from services.wishlist_service import create_wishlist_item, get_wishlist_items, get_wishlist_item_by_id, update_wishlist_item, drop_wishlist_item

        with patch("services.wishlist_service.now_utc", return_value=self.start_time):
            u1_item = create_wishlist_item(1, "Private Item", 5000.0)

        # User 2 cannot see it
        self.assertEqual(get_wishlist_items(2), [])
        self.assertIsNone(get_wishlist_item_by_id(2, u1_item["id"]))

        # User 2 cannot edit or drop it
        with self.assertRaises(ValueError):
            update_wishlist_item(2, u1_item["id"], item_name="Hacked")
        with self.assertRaises(ValueError):
            drop_wishlist_item(2, u1_item["id"])

    def test_buy_item_expense_date_uses_today_local(self):
        """
        At simulated time 2026-10-05 20:00 UTC (which is 2026-10-06 01:30 AM IST),
        buying an unlocked item creates an expense dated 2026-10-06.
        """
        from services.wishlist_service import create_wishlist_item, buy_wishlist_item

        # Create item at 2026-10-04 12:00 UTC (unlocks at 2026-10-05 12:00 UTC)
        created_time = datetime(2026, 10, 4, 12, 0, 0, tzinfo=timezone.utc)
        with patch("services.wishlist_service.now_utc", return_value=created_time):
            item = create_wishlist_item(1, "Noise Cancelling Headphones", 4500.0, "Electronics")

        # Buy at simulated time: 2026-10-05 20:00:00 UTC (01:30 AM IST on Oct 6)
        simulated_time = datetime(2026, 10, 5, 20, 0, 0, tzinfo=timezone.utc)
        with patch("services.wishlist_service.now_utc", return_value=simulated_time), \
             patch("utils.clock.now_utc", return_value=simulated_time):
            res = buy_wishlist_item(1, item["id"])

        self.assertEqual(res["item"]["status"], "bought")
        self.assertEqual(res["expense"]["date"], "2026-10-06")
        self.assertEqual(res["date"], "2026-10-06")
        self.assertEqual(res["month"], "2026-10")


class TestWishlistAPI(unittest.TestCase):
    """Integration tests for /api/v1/wishlist endpoints."""

    def setUp(self):
        self.test_db_path = str(Path(__file__).resolve().parent / "test_wishlist_api.db")
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
        self.start_time = datetime(2026, 10, 6, 10, 0, 0, tzinfo=timezone.utc)

        # Log in as user 1
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1

    def tearDown(self):
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    def test_post_wishlist_item(self):
        with patch("services.wishlist_service.now_utc", return_value=self.start_time):
            res = self.client.post("/api/v1/wishlist", json={
                "item_name": "Smart Watch",
                "estimated_amount_inr": 2999.0,
                "sub_category": "Gadgets",
                "unlock_at": "client_hack_attempt"
            })
        self.assertEqual(res.status_code, 201)
        data = res.get_json()["data"]
        self.assertEqual(data["item_name"], "Smart Watch")
        self.assertEqual(data["estimated_amount_inr"], 2999.0)
        self.assertEqual(data["status"], "waiting")
        # Client-sent unlock_at is ignored
        self.assertNotEqual(data["unlock_at"], "client_hack_attempt")
        self.assertEqual(data["unlock_at"], to_iso_utc(self.start_time + timedelta(hours=24)))

    def test_get_wishlist_items_with_seconds_remaining(self):
        with patch("services.wishlist_service.now_utc", return_value=self.start_time):
            self.client.post("/api/v1/wishlist", json={"item_name": "Book", "estimated_amount_inr": 499.0})

        # 4 hours later
        later = self.start_time + timedelta(hours=4)
        with patch("services.wishlist_service.now_utc", return_value=later):
            res = self.client.get("/api/v1/wishlist?status=waiting")

        self.assertEqual(res.status_code, 200)
        items = res.get_json()["data"]
        self.assertEqual(len(items), 1)
        self.assertFalse(items[0]["is_unlocked"])
        self.assertEqual(items[0]["seconds_remaining"], 20 * 3600)

    def test_api_buy_before_24h_returns_400(self):
        with patch("services.wishlist_service.now_utc", return_value=self.start_time):
            create_res = self.client.post("/api/v1/wishlist", json={"item_name": "Tent", "estimated_amount_inr": 3500.0})
            item_id = create_res.get_json()["data"]["id"]

        with patch("services.wishlist_service.now_utc", return_value=self.start_time + timedelta(hours=23)):
            buy_res = self.client.post(f"/api/v1/wishlist/{item_id}/buy")
            self.assertEqual(buy_res.status_code, 400)
            self.assertIn("Please wait", buy_res.get_json()["error"])

    def test_api_buy_after_24h_returns_200_and_creates_expense(self):
        with patch("services.wishlist_service.now_utc", return_value=self.start_time):
            create_res = self.client.post("/api/v1/wishlist", json={"item_name": "Tent", "estimated_amount_inr": 3500.0})
            item_id = create_res.get_json()["data"]["id"]

        with patch("services.wishlist_service.now_utc", return_value=self.start_time + timedelta(hours=25)):
            buy_res = self.client.post(f"/api/v1/wishlist/{item_id}/buy")
            self.assertEqual(buy_res.status_code, 200)
            data = buy_res.get_json()["data"]
            self.assertEqual(data["amount_inr"], 3500.0)
            self.assertEqual(data["type"], "faltu")
            self.assertEqual(data["wishlist_item_id"], item_id)

    def test_api_double_buy_returns_400(self):
        with patch("services.wishlist_service.now_utc", return_value=self.start_time):
            create_res = self.client.post("/api/v1/wishlist", json={"item_name": "Tripod", "estimated_amount_inr": 800.0})
            item_id = create_res.get_json()["data"]["id"]

        with patch("services.wishlist_service.now_utc", return_value=self.start_time + timedelta(hours=24, seconds=1)):
            buy1 = self.client.post(f"/api/v1/wishlist/{item_id}/buy")
            self.assertEqual(buy1.status_code, 200)
            buy2 = self.client.post(f"/api/v1/wishlist/{item_id}/buy")
            self.assertEqual(buy2.status_code, 400)

    def test_api_drop_endpoint(self):
        with patch("services.wishlist_service.now_utc", return_value=self.start_time):
            create_res = self.client.post("/api/v1/wishlist", json={"item_name": "Hat", "estimated_amount_inr": 400.0})
            item_id = create_res.get_json()["data"]["id"]
            drop_res = self.client.post(f"/api/v1/wishlist/{item_id}/drop")

        self.assertEqual(drop_res.status_code, 200)
        self.assertEqual(drop_res.get_json()["data"]["status"], "dropped")

    def test_api_summary_endpoint(self):
        with patch("services.wishlist_service.now_utc", return_value=self.start_time):
            # Create and drop item of Rs 1500
            c = self.client.post("/api/v1/wishlist", json={"item_name": "Sunglasses", "estimated_amount_inr": 1500.0})
            self.client.post(f"/api/v1/wishlist/{c.get_json()['data']['id']}/drop")
            # Create waiting item of Rs 800
            self.client.post("/api/v1/wishlist", json={"item_name": "Belt", "estimated_amount_inr": 800.0})

            res = self.client.get("/api/v1/wishlist/summary")

        self.assertEqual(res.status_code, 200)
        summary = res.get_json()["data"]
        self.assertEqual(summary["items_dropped"], 1)
        self.assertEqual(summary["amount_saved_inr"], 1500.0)
        self.assertEqual(summary["items_waiting"], 1)

    def test_api_user_isolation(self):
        with patch("services.wishlist_service.now_utc", return_value=self.start_time):
            c = self.client.post("/api/v1/wishlist", json={"item_name": "User 1 Item", "estimated_amount_inr": 2000.0})
            item_id = c.get_json()["data"]["id"]

        with patch("api.v1.wishlist_routes.get_current_user_id", return_value=2):
            res_get = self.client.get(f"/api/v1/wishlist/{item_id}")
            self.assertEqual(res_get.status_code, 404)
            res_drop = self.client.post(f"/api/v1/wishlist/{item_id}/drop")
            self.assertEqual(res_drop.status_code, 404)

    def test_api_ignores_client_sent_unlock_at_in_past(self):
        """
        Sending an unlock_at in the past in POST and PUT /api/v1/wishlist is ignored by the server.
        """
        past_unlock = "2020-01-01T00:00:00Z"

        with patch("services.wishlist_service.now_utc", return_value=self.start_time):
            # 1. POST /api/v1/wishlist with unlock_at in the past
            post_res = self.client.post("/api/v1/wishlist", json={
                "item_name": "Smart Watch",
                "estimated_amount_inr": 2999.0,
                "unlock_at": past_unlock
            })
            self.assertEqual(post_res.status_code, 201)
            item = post_res.get_json()["data"]
            expected_unlock = to_iso_utc(self.start_time + timedelta(hours=24))
            self.assertEqual(item["unlock_at"], expected_unlock)
            self.assertFalse(item["is_unlocked"])

            # 2. PUT /api/v1/wishlist/<id> with unlock_at in the past
            put_res = self.client.put(f"/api/v1/wishlist/{item['id']}", json={
                "item_name": "Smart Watch Pro",
                "unlock_at": past_unlock
            })
            self.assertEqual(put_res.status_code, 200)
            updated_item = put_res.get_json()["data"]
            self.assertEqual(updated_item["item_name"], "Smart Watch Pro")
            self.assertEqual(updated_item["unlock_at"], expected_unlock)
            self.assertFalse(updated_item["is_unlocked"])


if __name__ == "__main__":
    unittest.main()
