"""
tests/test_udhar.py — Comprehensive tests for the Udhar tracker.

Coverage:
- Input validation (name, amount, type, date formats including 2026-02-30)
- Overdue logic: due_date < today → overdue, due_date == today → NOT overdue, settled → never overdue
- Settle / reopen idempotency rules
- Summary totals (to_receive, to_pay, overdue_count, per-person net)
- User isolation (user2 cannot see or modify user1's records)
- Creating udhar does NOT change the dashboard summary
- DELETE endpoint
- API route tests (status codes, response envelopes)
"""

import os
import json
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

from config import Config
from database.db import init_db
from app import create_app


# ─── Test DB helpers ────────────────────────────────────────────────────────

def _make_test_db(path: str):
    Config.DATABASE_PATH = path
    if os.path.exists(path):
        os.remove(path)
    init_db()


# ─── Service-level tests ────────────────────────────────────────────────────

class TestUdharService(unittest.TestCase):
    """Tests for services/udhar_service.py"""

    def setUp(self):
        self.test_db = str(Path(__file__).resolve().parent / "test_udhar_service.db")
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

        # Fixed reference UTC "today"
        self.today = datetime(2026, 10, 6, 0, 0, 0, tzinfo=timezone.utc)

    def tearDown(self):
        self.ctx.pop()
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def _patch_today(self, dt=None):
        """Returns a context-manager patch for clock.now_utc."""
        target_time = dt if dt is not None else self.today
        return patch("services.udhar_service.now_utc", return_value=target_time)

    # ── Validation tests ──────────────────────────────────────────────────

    def test_empty_name_rejected(self):
        from services.udhar_service import create_udhar
        with self._patch_today():
            with self.assertRaises(ValueError, msg="Empty name must be rejected"):
                create_udhar(1, "", 100.0, "lent")
            with self.assertRaises(ValueError):
                create_udhar(1, "   ", 100.0, "lent")

    def test_name_too_long_rejected(self):
        from services.udhar_service import create_udhar
        with self._patch_today():
            with self.assertRaises(ValueError):
                create_udhar(1, "A" * 41, 100.0, "lent")

    def test_zero_amount_rejected(self):
        from services.udhar_service import create_udhar
        with self._patch_today():
            with self.assertRaises(ValueError):
                create_udhar(1, "Rahul", 0, "lent")

    def test_negative_amount_rejected(self):
        from services.udhar_service import create_udhar
        with self._patch_today():
            with self.assertRaises(ValueError):
                create_udhar(1, "Rahul", -50.0, "lent")

    def test_invalid_type_rejected(self):
        from services.udhar_service import create_udhar
        with self._patch_today():
            for bad_type in ("give", "take", "", None, 123):
                with self.assertRaises(ValueError, msg=f"Type '{bad_type}' should be rejected"):
                    create_udhar(1, "Raj", 100.0, bad_type)

    def test_bad_date_format_rejected(self):
        from services.udhar_service import create_udhar
        bad_dates = [
            "2026-1-5",     # missing zero-padding
            "06-10-2026",   # DD-MM-YYYY
            "2026/10/06",   # wrong separator
            "26-10-2026",   # 2-digit year
            "2026-13-01",   # month 13
            "2026-00-10",   # month 00
        ]
        with self._patch_today():
            for bad_date in bad_dates:
                with self.assertRaises(ValueError, msg=f"Date '{bad_date}' should be rejected"):
                    create_udhar(1, "Raj", 100.0, "lent", due_date=bad_date)

    def test_nonexistent_calendar_date_rejected(self):
        """2026-02-30 matches the regex but fails the calendar check."""
        from services.udhar_service import create_udhar
        with self._patch_today():
            with self.assertRaises(ValueError, msg="2026-02-30 is not a real date"):
                create_udhar(1, "Raj", 100.0, "lent", due_date="2026-02-30")

    def test_valid_date_accepted(self):
        from services.udhar_service import create_udhar
        with self._patch_today():
            rec = create_udhar(1, "Raj", 200.0, "lent", due_date="2026-12-31")
        self.assertEqual(rec["due_date"], "2026-12-31")

    # ── Create / basic get ────────────────────────────────────────────────

    def test_create_and_read_lent(self):
        from services.udhar_service import create_udhar, get_udhar_by_id
        with self._patch_today():
            rec = create_udhar(1, "Priya", 500.0, "lent", due_date="2026-11-01", note="Lunch")
        self.assertEqual(rec["person_name"], "Priya")
        self.assertEqual(rec["amount_inr"], 500.0)
        self.assertEqual(rec["type"], "lent")
        self.assertEqual(rec["is_settled"], 0)
        self.assertEqual(rec["due_date"], "2026-11-01")
        self.assertEqual(rec["note"], "Lunch")
        self.assertFalse(rec["is_overdue"])  # due_date is in the future

    def test_create_borrowed(self):
        from services.udhar_service import create_udhar
        with self._patch_today():
            rec = create_udhar(1, "Suresh", 750.0, "borrowed")
        self.assertEqual(rec["type"], "borrowed")
        self.assertIsNone(rec["due_date"])

    # ── Overdue logic ─────────────────────────────────────────────────────

    def test_due_yesterday_is_overdue(self):
        from services.udhar_service import create_udhar, get_udhar_list
        yesterday = (self.today - timedelta(days=1)).strftime("%Y-%m-%d")
        with self._patch_today():
            create_udhar(1, "Amit", 300.0, "lent", due_date=yesterday)
        # re-fetch with clock at "today"
        with self._patch_today():
            items = get_udhar_list(1, status="pending")
        self.assertEqual(len(items), 1)
        self.assertTrue(items[0]["is_overdue"])

    def test_due_today_is_not_overdue(self):
        from services.udhar_service import create_udhar, get_udhar_list
        today_str = self.today.strftime("%Y-%m-%d")
        with self._patch_today():
            create_udhar(1, "Pankaj", 400.0, "lent", due_date=today_str)
        with self._patch_today():
            items = get_udhar_list(1, status="pending")
        self.assertFalse(items[0]["is_overdue"])

    def test_due_tomorrow_is_not_overdue(self):
        from services.udhar_service import create_udhar, get_udhar_list
        tomorrow = (self.today + timedelta(days=1)).strftime("%Y-%m-%d")
        with self._patch_today():
            create_udhar(1, "Kavya", 200.0, "lent", due_date=tomorrow)
        with self._patch_today():
            items = get_udhar_list(1, status="pending")
        self.assertFalse(items[0]["is_overdue"])

    def test_settled_record_never_overdue(self):
        from services.udhar_service import create_udhar, settle_udhar, get_udhar_list
        yesterday = (self.today - timedelta(days=1)).strftime("%Y-%m-%d")
        with self._patch_today():
            rec = create_udhar(1, "Dev", 150.0, "lent", due_date=yesterday)
            settle_udhar(1, rec["id"])
        with self._patch_today():
            settled = get_udhar_list(1, status="settled")
        self.assertEqual(len(settled), 1)
        self.assertFalse(settled[0]["is_overdue"])  # settled → never overdue

    def test_no_due_date_never_overdue(self):
        from services.udhar_service import create_udhar, get_udhar_list
        with self._patch_today():
            create_udhar(1, "Suman", 100.0, "lent")  # no due_date
        with self._patch_today():
            items = get_udhar_list(1)
        self.assertFalse(items[0]["is_overdue"])

    # ── Settle / Reopen ───────────────────────────────────────────────────

    def test_settle_marks_record(self):
        from services.udhar_service import create_udhar, settle_udhar, get_udhar_by_id
        with self._patch_today():
            rec = create_udhar(1, "Neha", 200.0, "lent")
            settled = settle_udhar(1, rec["id"])
        self.assertEqual(settled["is_settled"], 1)

    def test_settle_already_settled_raises(self):
        from services.udhar_service import create_udhar, settle_udhar
        with self._patch_today():
            rec = create_udhar(1, "Neha", 200.0, "lent")
            settle_udhar(1, rec["id"])
            with self.assertRaises(ValueError, msg="Double settle must fail"):
                settle_udhar(1, rec["id"])

    def test_reopen_settled_record(self):
        from services.udhar_service import create_udhar, settle_udhar, reopen_udhar
        with self._patch_today():
            rec = create_udhar(1, "Tom", 100.0, "borrowed")
            settle_udhar(1, rec["id"])
            reopened = reopen_udhar(1, rec["id"])
        self.assertEqual(reopened["is_settled"], 0)

    def test_reopen_pending_raises(self):
        from services.udhar_service import create_udhar, reopen_udhar
        with self._patch_today():
            rec = create_udhar(1, "Sara", 300.0, "borrowed")
            with self.assertRaises(ValueError, msg="Reopening a pending record must fail"):
                reopen_udhar(1, rec["id"])

    def test_delete_record(self):
        from services.udhar_service import create_udhar, delete_udhar, get_udhar_by_id
        with self._patch_today():
            rec = create_udhar(1, "Mike", 100.0, "lent")
            result = delete_udhar(1, rec["id"])
        self.assertTrue(result)
        with self._patch_today():
            self.assertIsNone(get_udhar_by_id(1, rec["id"]))

    def test_delete_nonexistent_returns_false(self):
        from services.udhar_service import delete_udhar
        self.assertFalse(delete_udhar(1, 99999))

    # ── Update ────────────────────────────────────────────────────────────

    def test_update_fields(self):
        from services.udhar_service import create_udhar, update_udhar
        with self._patch_today():
            rec = create_udhar(1, "Old Name", 100.0, "lent")
            updated = update_udhar(1, rec["id"], person_name="New Name", amount_inr=250.0, note="Changed")
        self.assertEqual(updated["person_name"], "New Name")
        self.assertEqual(updated["amount_inr"], 250.0)
        self.assertEqual(updated["note"], "Changed")

    def test_update_clears_due_date_on_empty_string(self):
        from services.udhar_service import create_udhar, update_udhar
        with self._patch_today():
            rec = create_udhar(1, "Raj", 100.0, "lent", due_date="2026-12-01")
            updated = update_udhar(1, rec["id"], due_date="")  # clear it
        self.assertIsNone(updated["due_date"])

    def test_update_nonexistent_returns_none(self):
        from services.udhar_service import update_udhar
        result = update_udhar(1, 99999, person_name="Ghost")
        self.assertIsNone(result)

    # ── Summary ───────────────────────────────────────────────────────────

    def test_summary_totals(self):
        from services.udhar_service import create_udhar, get_udhar_summary
        with self._patch_today():
            create_udhar(1, "A", 1000.0, "lent")
            create_udhar(1, "A", 500.0, "lent")
            create_udhar(1, "B", 300.0, "borrowed")
            summary = get_udhar_summary(1)
        self.assertAlmostEqual(summary["total_to_receive_inr"], 1500.0)
        self.assertAlmostEqual(summary["total_to_pay_inr"], 300.0)
        self.assertEqual(summary["pending_count"], 3)

    def test_summary_overdue_count(self):
        from services.udhar_service import create_udhar, get_udhar_summary
        yesterday = (self.today - timedelta(days=1)).strftime("%Y-%m-%d")
        today_str = self.today.strftime("%Y-%m-%d")
        with self._patch_today():
            create_udhar(1, "X", 100.0, "lent", due_date=yesterday)  # overdue
            create_udhar(1, "Y", 100.0, "lent", due_date=today_str)  # NOT overdue
            create_udhar(1, "Z", 100.0, "lent")                       # no due date → NOT overdue
            summary = get_udhar_summary(1)
        self.assertEqual(summary["overdue_count"], 1)

    def test_per_person_net_breakdown(self):
        """
        Lent 1000 to Raj and borrowed 400 from Raj → net = +600 (Raj owes me).
        Borrowed 200 from Priya → net = -200 (I owe Priya).
        """
        from services.udhar_service import create_udhar, get_udhar_summary
        with self._patch_today():
            create_udhar(1, "Raj", 1000.0, "lent")
            create_udhar(1, "Raj", 400.0, "borrowed")
            create_udhar(1, "Priya", 200.0, "borrowed")
            summary = get_udhar_summary(1)

        per_person = {p["person_name"]: p["net_inr"] for p in summary["per_person"]}
        self.assertAlmostEqual(per_person["Raj"], 600.0)
        self.assertAlmostEqual(per_person["Priya"], -200.0)

    def test_settled_records_excluded_from_summary(self):
        from services.udhar_service import create_udhar, settle_udhar, get_udhar_summary
        with self._patch_today():
            rec = create_udhar(1, "Ghost", 9999.0, "lent")
            settle_udhar(1, rec["id"])
            summary = get_udhar_summary(1)
        self.assertEqual(summary["total_to_receive_inr"], 0.0)
        self.assertEqual(summary["pending_count"], 0)

    # ── User isolation ────────────────────────────────────────────────────

    def test_user2_cannot_see_user1_records(self):
        from services.udhar_service import create_udhar, get_udhar_list, get_udhar_by_id
        with self._patch_today():
            rec = create_udhar(1, "Secret", 100.0, "lent")
            items_u2 = get_udhar_list(2, status="all")
        self.assertEqual(len(items_u2), 0)
        self.assertIsNone(get_udhar_by_id(2, rec["id"]))

    def test_user2_cannot_settle_user1_record(self):
        from services.udhar_service import create_udhar, settle_udhar
        with self._patch_today():
            rec = create_udhar(1, "Raj", 200.0, "lent")
            result = settle_udhar(2, rec["id"])  # wrong user → returns None
        self.assertIsNone(result)

    def test_user2_cannot_delete_user1_record(self):
        from services.udhar_service import create_udhar, delete_udhar
        with self._patch_today():
            rec = create_udhar(1, "Raj", 200.0, "lent")
            result = delete_udhar(2, rec["id"])
        self.assertFalse(result)

    # ── Dashboard isolation ────────────────────────────────────────────────

    def test_creating_udhar_does_not_affect_dashboard(self):
        """Udhar records must NOT appear in income, expenses, or balance."""
        from services.udhar_service import create_udhar
        from services.dashboard_service import get_monthly_summary
        month = "2026-10"
        with self._patch_today():
            before = get_monthly_summary(1, month)
            create_udhar(1, "Ravi", 5000.0, "lent")
            create_udhar(1, "Sita", 2000.0, "borrowed")
            after = get_monthly_summary(1, month)
        self.assertEqual(before["total_income_inr"], after["total_income_inr"])
        self.assertEqual(before["total_daily_inr"], after["total_daily_inr"])
        self.assertEqual(before["total_faltu_inr"], after["total_faltu_inr"])
        self.assertEqual(before["balance_inr"], after["balance_inr"])

    # ── List filters ──────────────────────────────────────────────────────

    def test_status_filter_settled(self):
        from services.udhar_service import create_udhar, settle_udhar, get_udhar_list
        with self._patch_today():
            rec = create_udhar(1, "A", 100.0, "lent")
            create_udhar(1, "B", 200.0, "lent")
            settle_udhar(1, rec["id"])
            pending = get_udhar_list(1, "pending")
            settled = get_udhar_list(1, "settled")
            all_rec = get_udhar_list(1, "all")
        self.assertEqual(len(pending), 1)
        self.assertEqual(len(settled), 1)
        self.assertEqual(len(all_rec), 2)

    def test_type_filter(self):
        from services.udhar_service import create_udhar, get_udhar_list
        with self._patch_today():
            create_udhar(1, "A", 100.0, "lent")
            create_udhar(1, "B", 200.0, "borrowed")
            lent_only = get_udhar_list(1, "all", udhar_type="lent")
            borrowed_only = get_udhar_list(1, "all", udhar_type="borrowed")
        self.assertEqual(len(lent_only), 1)
        self.assertEqual(lent_only[0]["type"], "lent")
        self.assertEqual(len(borrowed_only), 1)
        self.assertEqual(borrowed_only[0]["type"], "borrowed")

    def test_invalid_status_raises(self):
        from services.udhar_service import get_udhar_list
        with self.assertRaises(ValueError):
            get_udhar_list(1, status="unknown")

    def test_invalid_type_filter_raises(self):
        from services.udhar_service import get_udhar_list
        with self.assertRaises(ValueError):
            get_udhar_list(1, udhar_type="give")

    def test_note_truncated_to_200(self):
        from services.udhar_service import create_udhar
        long_note = "X" * 300
        with self._patch_today():
            rec = create_udhar(1, "Raj", 100.0, "lent", note=long_note)
        self.assertEqual(len(rec["note"]), 200)


# ─── API-level tests ─────────────────────────────────────────────────────────

class TestUdharAPI(unittest.TestCase):
    """HTTP-level tests for /api/v1/udhar routes."""

    def setUp(self):
        self.test_db = str(Path(__file__).resolve().parent / "test_udhar_api.db")
        _make_test_db(self.test_db)

        class TestConfig(Config):
            TESTING = True
            DATABASE_PATH = self.test_db
            SECRET_KEY = "test-secret-key"

        app = create_app(TestConfig)
        self.client = app.test_client()
        self.app = app

        with app.app_context():
            from database.db import get_db
            db = get_db()
            db.execute("INSERT INTO users (id, username, email) VALUES (2, 'user2', 'u2@test.local')")
            db.commit()

        # Log in as user 1
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1

        self.today = datetime(2026, 10, 6, 0, 0, 0, tzinfo=timezone.utc)

    def tearDown(self):
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def _post(self, data):
        return self.client.post("/api/v1/udhar", json=data)

    # ── POST validation ───────────────────────────────────────────────────

    def test_post_missing_name_returns_400(self):
        res = self._post({"amount_inr": 100, "type": "lent"})
        self.assertEqual(res.status_code, 400)

    def test_post_bad_amount_returns_400(self):
        res = self._post({"person_name": "Raj", "amount_inr": 0, "type": "lent"})
        self.assertEqual(res.status_code, 400)

    def test_post_bad_type_returns_400(self):
        res = self._post({"person_name": "Raj", "amount_inr": 100, "type": "give"})
        self.assertEqual(res.status_code, 400)

    def test_post_bad_date_returns_400(self):
        res = self._post({"person_name": "Raj", "amount_inr": 100, "type": "lent", "due_date": "2026-2-30"})
        self.assertEqual(res.status_code, 400)

    def test_post_nonexistent_date_returns_400(self):
        res = self._post({"person_name": "Raj", "amount_inr": 100, "type": "lent", "due_date": "2026-02-30"})
        self.assertEqual(res.status_code, 400)

    def test_post_success_returns_201(self):
        res = self._post({"person_name": "Priya", "amount_inr": 500, "type": "lent"})
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["person_name"], "Priya")
        self.assertEqual(data["data"]["amount_inr"], 500.0)

    # ── GET list ──────────────────────────────────────────────────────────

    def test_get_pending_default(self):
        self._post({"person_name": "A", "amount_inr": 100, "type": "lent"})
        res = self.client.get("/api/v1/udhar")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.get_json()["data"]), 1)

    def test_get_invalid_status_returns_400(self):
        res = self.client.get("/api/v1/udhar?status=garbage")
        self.assertEqual(res.status_code, 400)

    # ── GET summary ───────────────────────────────────────────────────────

    def test_get_summary_endpoint(self):
        self._post({"person_name": "Raj", "amount_inr": 1000, "type": "lent"})
        self._post({"person_name": "Raj", "amount_inr": 200, "type": "borrowed"})
        res = self.client.get("/api/v1/udhar/summary")
        self.assertEqual(res.status_code, 200)
        d = res.get_json()["data"]
        self.assertAlmostEqual(d["total_to_receive_inr"], 1000.0)
        self.assertAlmostEqual(d["total_to_pay_inr"], 200.0)
        self.assertIn("per_person", d)

    # ── PUT ───────────────────────────────────────────────────────────────

    def test_put_updates_record(self):
        r = self._post({"person_name": "Old", "amount_inr": 100, "type": "lent"})
        rid = r.get_json()["data"]["id"]
        res = self.client.put(f"/api/v1/udhar/{rid}", json={"person_name": "New", "amount_inr": 250})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["data"]["person_name"], "New")

    def test_put_nonexistent_returns_404(self):
        res = self.client.put("/api/v1/udhar/99999", json={"person_name": "Ghost", "amount_inr": 100})
        self.assertEqual(res.status_code, 404)

    # ── Settle / Reopen ───────────────────────────────────────────────────

    def test_settle_endpoint(self):
        r = self._post({"person_name": "X", "amount_inr": 100, "type": "lent"})
        rid = r.get_json()["data"]["id"]
        res = self.client.post(f"/api/v1/udhar/{rid}/settle")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["data"]["is_settled"], 1)

    def test_settle_twice_returns_400(self):
        r = self._post({"person_name": "Y", "amount_inr": 100, "type": "lent"})
        rid = r.get_json()["data"]["id"]
        self.client.post(f"/api/v1/udhar/{rid}/settle")
        res = self.client.post(f"/api/v1/udhar/{rid}/settle")
        self.assertEqual(res.status_code, 400)

    def test_reopen_pending_returns_400(self):
        r = self._post({"person_name": "Z", "amount_inr": 100, "type": "lent"})
        rid = r.get_json()["data"]["id"]
        res = self.client.post(f"/api/v1/udhar/{rid}/reopen")
        self.assertEqual(res.status_code, 400)

    def test_reopen_settled_returns_200(self):
        r = self._post({"person_name": "W", "amount_inr": 100, "type": "lent"})
        rid = r.get_json()["data"]["id"]
        self.client.post(f"/api/v1/udhar/{rid}/settle")
        res = self.client.post(f"/api/v1/udhar/{rid}/reopen")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["data"]["is_settled"], 0)

    def test_settle_nonexistent_returns_404(self):
        res = self.client.post("/api/v1/udhar/99999/settle")
        self.assertEqual(res.status_code, 404)

    # ── DELETE ────────────────────────────────────────────────────────────

    def test_delete_endpoint(self):
        r = self._post({"person_name": "Del", "amount_inr": 100, "type": "lent"})
        rid = r.get_json()["data"]["id"]
        res = self.client.delete(f"/api/v1/udhar/{rid}")
        self.assertEqual(res.status_code, 200)
        # Confirm gone
        get_res = self.client.get("/api/v1/udhar?status=all")
        self.assertEqual(len(get_res.get_json()["data"]), 0)

    def test_delete_nonexistent_returns_404(self):
        res = self.client.delete("/api/v1/udhar/99999")
        self.assertEqual(res.status_code, 404)

    # ── Overdue flag in API response ──────────────────────────────────────

    def test_overdue_flag_in_api_response(self):
        """Records due yesterday must have is_overdue=True in the API response."""
        yesterday = (self.today - timedelta(days=1)).strftime("%Y-%m-%d")
        with patch("services.udhar_service.now_utc", return_value=self.today):
            self._post({"person_name": "Late", "amount_inr": 100, "type": "lent", "due_date": yesterday})
            res = self.client.get("/api/v1/udhar?status=pending")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()["data"]
        self.assertEqual(len(data), 1)
        self.assertTrue(data[0]["is_overdue"])

    def test_due_today_not_overdue_in_api(self):
        today_str = self.today.strftime("%Y-%m-%d")
        with patch("services.udhar_service.now_utc", return_value=self.today):
            self._post({"person_name": "On time", "amount_inr": 100, "type": "lent", "due_date": today_str})
            res = self.client.get("/api/v1/udhar?status=pending")
        self.assertFalse(res.get_json()["data"][0]["is_overdue"])

    # ── Dashboard isolation via API ────────────────────────────────────────

    def test_udhar_does_not_change_dashboard_api(self):
        month = "2026-10"
        before = self.client.get(f"/api/v1/dashboard/summary?month={month}").get_json()["data"]
        self._post({"person_name": "Ghost", "amount_inr": 9999, "type": "lent"})
        self._post({"person_name": "Ghost", "amount_inr": 5555, "type": "borrowed"})
        after = self.client.get(f"/api/v1/dashboard/summary?month={month}").get_json()["data"]
        self.assertEqual(before["total_income_inr"], after["total_income_inr"])
        self.assertEqual(before["total_faltu_inr"], after["total_faltu_inr"])
        self.assertEqual(before["balance_inr"], after["balance_inr"])


if __name__ == "__main__":
    unittest.main()
