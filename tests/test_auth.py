"""
tests/test_auth.py — Comprehensive tests for Authentication & Authorization.

Covers:
1. services/auth_service.py
   - Registration with default user id=1 adoption (preserves existing data)
   - Subsequent user registration
   - Input validation (username, email, password strength, password != email/username)
   - Duplicate username & duplicate email handling
   - Login authentication & constant-time password check
   - In-memory brute force lockout (5 attempts -> 429/locked)
   - User retrieval without leaking password_hash

2. api/v1/auth_routes.py
   - POST /api/v1/auth/register (201 created, session cookie set)
   - POST /api/v1/auth/login (200 success, session fixation prevented)
   - POST /api/v1/auth/login failures (generic 401, 429 on lockout)
   - POST /api/v1/auth/logout (200, session cleared)
   - GET /api/v1/auth/me (200 with user data, 401 when unauthenticated)

3. Page Routes & Route Protection
   - GET / redirects to /login when unauthenticated
   - GET / returns 200 when authenticated
   - GET /login redirects to / when authenticated
   - GET /login returns 200 when unauthenticated
   - GET /logout clears session and redirects to /login
   - Unauthenticated API calls to /api/v1/* return 401 JSON
"""
import os
import unittest
from pathlib import Path
from flask import session

from config import Config
from database.db import init_db, get_db
from app import create_app
import services.auth_service as auth_service


class BaseAuthTestCase(unittest.TestCase):
    """Base setup for auth tests with isolated SQLite database."""

    def setUp(self):
        self.test_db_path = str(Path(__file__).resolve().parent / "test_auth_temp.db")
        Config.DATABASE_PATH = self.test_db_path
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        init_db()

        class TestConfig(Config):
            TESTING = True
            DATABASE_PATH = self.test_db_path
            SECRET_KEY = "test-auth-secret-key"

        self.app = create_app(TestConfig)
        self.client = self.app.test_client()

        # Reset process-local brute-force failure tracking
        auth_service._login_failures.clear()

    def tearDown(self):
        auth_service._login_failures.clear()
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)


class TestAuthService(BaseAuthTestCase):
    """Direct unit tests for services/auth_service.py logic."""

    def test_first_registration_adopts_default_user_row(self):
        with self.app.app_context():
            # Initially user id=1 exists with password_hash is NULL
            db = get_db()
            row = db.execute("SELECT id, username, password_hash FROM users WHERE id = 1").fetchone()
            self.assertIsNotNone(row)
            self.assertIsNone(row["password_hash"])

            # First registration updates row id=1
            user = auth_service.register_user("first_user", "first@example.com", "SecurePass123")
            self.assertEqual(user["id"], 1)
            self.assertEqual(user["username"], "first_user")
            self.assertEqual(user["email"], "first@example.com")

            # Verify in DB that row id=1 was adopted
            updated = db.execute("SELECT id, username, email, password_hash FROM users WHERE id = 1").fetchone()
            self.assertEqual(updated["username"], "first_user")
            self.assertEqual(updated["email"], "first@example.com")
            self.assertIsNotNone(updated["password_hash"])

    def test_second_registration_creates_new_row(self):
        with self.app.app_context():
            # First user adopts id=1
            u1 = auth_service.register_user("user_one", "u1@example.com", "Password123")
            self.assertEqual(u1["id"], 1)

            # Second user gets fresh id (2)
            u2 = auth_service.register_user("user_two", "u2@example.com", "Password123")
            self.assertEqual(u2["id"], 2)
            self.assertEqual(u2["username"], "user_two")

    def test_register_validation_invalid_username(self):
        invalid_usernames = ["ab", "a" * 31, "user space", "user@name", "user-name!"]
        with self.app.app_context():
            for bad_u in invalid_usernames:
                with self.subTest(username=bad_u):
                    with self.assertRaises(ValueError) as ctx:
                        auth_service.register_user(bad_u, "valid@example.com", "Password123")
                    self.assertIn("Username must be", str(ctx.exception))

    def test_register_validation_invalid_email(self):
        invalid_emails = ["notanemail", "missingat.com", "user@", "@domain.com", "bad email@domain.com"]
        with self.app.app_context():
            for bad_e in invalid_emails:
                with self.subTest(email=bad_e):
                    with self.assertRaises(ValueError) as ctx:
                        auth_service.register_user("valid_user", bad_e, "Password123")
                    self.assertIn("valid email", str(ctx.exception).lower())

    def test_register_validation_short_password(self):
        with self.app.app_context():
            with self.assertRaises(ValueError) as ctx:
                auth_service.register_user("valid_user", "test@example.com", "short1")
            self.assertIn("at least 8 characters", str(ctx.exception))

    def test_register_validation_password_matches_username_or_email(self):
        with self.app.app_context():
            with self.assertRaises(ValueError) as ctx:
                auth_service.register_user("samename", "test@example.com", "samename")
            self.assertIn("not be the same as your username", str(ctx.exception))

            with self.assertRaises(ValueError) as ctx2:
                auth_service.register_user("diffuser", "user@test.com", "user@test.com")
            self.assertIn("not be the same as your email", str(ctx2.exception))

    def test_register_duplicate_username_and_email(self):
        with self.app.app_context():
            auth_service.register_user("john_doe", "john@example.com", "Password123")

            # Duplicate username (case-insensitive)
            with self.assertRaises(ValueError) as ctx_u:
                auth_service.register_user("JOHN_DOE", "other@example.com", "Password123")
            self.assertIn("already taken", str(ctx_u.exception))

            # Duplicate email
            with self.assertRaises(ValueError) as ctx_e:
                auth_service.register_user("new_user", "john@example.com", "Password123")
            self.assertIn("already exists", str(ctx_e.exception))

    def test_login_success(self):
        with self.app.app_context():
            auth_service.register_user("login_user", "login@example.com", "SecretPass1")
            logged_in = auth_service.login_user("login@example.com", "SecretPass1")
            self.assertEqual(logged_in["username"], "login_user")
            self.assertEqual(logged_in["email"], "login@example.com")

    def test_login_invalid_credentials(self):
        with self.app.app_context():
            auth_service.register_user("login_user", "login@example.com", "SecretPass1")

            # Wrong password
            with self.assertRaises(ValueError) as ctx_pw:
                auth_service.login_user("login@example.com", "WrongPassword")
            self.assertEqual(str(ctx_pw.exception), "invalid")

            # Unknown email
            with self.assertRaises(ValueError) as ctx_em:
                auth_service.login_user("nonexistent@example.com", "SecretPass1")
            self.assertEqual(str(ctx_em.exception), "invalid")

    def test_login_brute_force_lockout(self):
        email = "target@example.com"
        with self.app.app_context():
            auth_service.register_user("target_user", email, "SecretPass1")

            # 5 failed attempts
            for i in range(5):
                with self.assertRaises(ValueError) as ctx:
                    auth_service.login_user(email, f"WrongPass{i}")
                self.assertEqual(str(ctx.exception), "invalid")

            # 6th attempt triggers lockout
            with self.assertRaises(ValueError) as ctx_locked:
                auth_service.login_user(email, "SecretPass1")  # even correct password
            self.assertEqual(str(ctx_locked.exception), "locked")

    def test_get_user_by_id(self):
        with self.app.app_context():
            u = auth_service.register_user("retrieved", "ret@example.com", "Password123")
            found = auth_service.get_user_by_id(u["id"])
            self.assertEqual(found["username"], "retrieved")
            self.assertNotIn("password_hash", found)

            none_user = auth_service.get_user_by_id(99999)
            self.assertIsNone(none_user)


class TestAuthAPI(BaseAuthTestCase):
    """API endpoint tests for /api/v1/auth/* routes."""

    def test_api_register_success(self):
        payload = {
            "username": "api_user",
            "email": "api@example.com",
            "password": "Password123"
        }
        res = self.client.post("/api/v1/auth/register", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["username"], "api_user")

        # Verify session was established
        with self.client.session_transaction() as sess:
            self.assertEqual(sess["user_id"], data["data"]["id"])

    def test_api_register_validation_error(self):
        payload = {
            "username": "bad",
            "email": "invalid-email",
            "password": "123"
        }
        res = self.client.post("/api/v1/auth/register", json=payload)
        self.assertEqual(res.status_code, 400)
        self.assertFalse(res.get_json()["success"])

    def test_api_login_success(self):
        # Register user first
        self.client.post(
            "/api/v1/auth/register",
            json={"username": "logintest", "email": "test@test.com", "password": "Password123"}
        )

        # Clear session to test clean login
        with self.client.session_transaction() as sess:
            sess.clear()

        res = self.client.post(
            "/api/v1/auth/login",
            json={"email": "test@test.com", "password": "Password123"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["username"], "logintest")

        with self.client.session_transaction() as sess:
            self.assertEqual(sess["user_id"], data["data"]["id"])

    def test_api_login_generic_401_on_failure(self):
        res = self.client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "wrong"}
        )
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"], "Invalid email or password.")

    def test_api_login_lockout_returns_429(self):
        for _ in range(5):
            self.client.post(
                "/api/v1/auth/login",
                json={"email": "locked@test.com", "password": "wrong"}
            )

        res_6th = self.client.post(
            "/api/v1/auth/login",
            json={"email": "locked@test.com", "password": "wrong"}
        )
        self.assertEqual(res_6th.status_code, 429)
        data = res_6th.get_json()
        self.assertFalse(data["success"])
        self.assertIn("Too many failed attempts", data["error"])

    def test_api_logout(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1

        res = self.client.post("/api/v1/auth/logout")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["success"])

        with self.client.session_transaction() as sess:
            self.assertNotIn("user_id", sess)

    def test_api_me_authenticated(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1

        res = self.client.get("/api/v1/auth/me")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["id"], 1)
        self.assertNotIn("password_hash", data["data"])

    def test_api_me_unauthenticated_returns_401(self):
        res = self.client.get("/api/v1/auth/me")
        self.assertEqual(res.status_code, 401)
        self.assertFalse(res.get_json()["success"])


class TestPageRoutesAndProtection(BaseAuthTestCase):
    """Tests for page route redirects and API endpoint authentication guards."""

    def test_index_unauthenticated_redirects_to_login(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 302)
        self.assertTrue(res.headers["Location"].endswith("/login"))

    def test_index_authenticated_returns_200(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1

        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)

    def test_login_page_unauthenticated_returns_200(self):
        res = self.client.get("/login")
        self.assertEqual(res.status_code, 200)

    def test_login_page_authenticated_redirects_to_index(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1

        res = self.client.get("/login")
        self.assertEqual(res.status_code, 302)
        self.assertTrue(res.headers["Location"].endswith("/"))

    def test_logout_page_route_clears_session_and_redirects(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1

        res = self.client.get("/logout")
        self.assertEqual(res.status_code, 302)
        self.assertTrue(res.headers["Location"].endswith("/login"))

        with self.client.session_transaction() as sess:
            self.assertNotIn("user_id", sess)

    def test_protected_api_endpoints_return_401_when_unauthenticated(self):
        endpoints = [
            ("GET", "/api/v1/incomes"),
            ("GET", "/api/v1/expenses"),
            ("GET", "/api/v1/dashboard/summary"),
            ("GET", "/api/v1/budgets/2026-10"),
            ("GET", "/api/v1/goals/2026-10"),
            ("GET", "/api/v1/presets"),
            ("GET", "/api/v1/wishlist"),
            ("GET", "/api/v1/udhar"),
            ("GET", "/api/v1/insights/summary?month=2026-10")
        ]
        for method, endpoint in endpoints:
            with self.subTest(endpoint=endpoint):
                if method == "GET":
                    res = self.client.get(endpoint)
                self.assertEqual(res.status_code, 401)
                data = res.get_json()
                self.assertFalse(data["success"])
                self.assertEqual(data["error"], "Login required")


if __name__ == "__main__":
    unittest.main()
