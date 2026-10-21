"""
tests/test_pwa.py — Comprehensive test suite for Progressive Web App (PWA) support.

Validates:
1. static/manifest.json is valid JSON, contains all required PWA fields, and all icon files exist.
2. /service-worker.js route returns JavaScript with Service-Worker-Allowed: / and Cache-Control: no-cache.
3. /offline.html is served successfully with HTTP 200.
4. static/service-worker.js contains rules strictly excluding /api/ from caching.
5. HTML templates (base.html, login.html) include manifest, theme-color, and apple-touch-icon.
6. Pinned Chart.js vendor asset exists and is served.
"""
import json
import os
import unittest
from pathlib import Path

from config import Config
from app import create_app


class TestPWASupport(unittest.TestCase):
    """Test suite for Savewise PWA assets, routes, and caching rules."""

    def setUp(self):
        self.workspace_dir = Path(__file__).resolve().parent.parent
        self.static_dir = self.workspace_dir / "static"

        class TestConfig(Config):
            TESTING = True
            SECRET_KEY = "test-pwa-secret-key"

        self.app = create_app(TestConfig)
        self.client = self.app.test_client()

    def test_manifest_valid_json_and_required_fields(self):
        """manifest.json must be valid JSON with required fields and valid icon files."""
        manifest_path = self.static_dir / "manifest.json"
        self.assertTrue(manifest_path.exists(), "manifest.json must exist in static/")

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        self.assertEqual(manifest.get("name"), "Savewise")
        self.assertEqual(manifest.get("short_name"), "Savewise")
        self.assertEqual(manifest.get("start_url"), "/")
        self.assertEqual(manifest.get("display"), "standalone")
        self.assertTrue(manifest.get("theme_color"), "theme_color must be set")
        self.assertTrue(manifest.get("background_color"), "background_color must be set")

        icons = manifest.get("icons", [])
        self.assertGreaterEqual(len(icons), 2, "Manifest must declare icons (192, 512, maskable)")

        sizes_found = set()
        has_maskable = False

        for icon in icons:
            src = icon.get("src", "")
            sizes = icon.get("sizes", "")
            purpose = icon.get("purpose", "any")

            sizes_found.add(sizes)
            if "maskable" in purpose:
                has_maskable = True

            # Convert /static/... path to local filesystem path
            clean_path = src.lstrip("/")
            if clean_path.startswith("static/"):
                clean_path = clean_path[len("static/"):]
            icon_file = self.static_dir / clean_path
            self.assertTrue(icon_file.exists(), f"Icon file must exist on disk: {icon_file}")
            self.assertGreater(os.path.getsize(icon_file), 0, f"Icon file must not be empty: {icon_file}")

        self.assertIn("192x192", sizes_found, "Must include 192x192 icon")
        self.assertIn("512x512", sizes_found, "Must include 512x512 icon")
        self.assertTrue(has_maskable, "Must include a maskable icon")

    def test_service_worker_served_with_correct_headers(self):
        """GET /service-worker.js returns JavaScript with root scope and no-cache headers."""
        res = self.client.get("/service-worker.js")
        self.assertEqual(res.status_code, 200)
        self.assertIn("javascript", res.content_type.lower())
        self.assertEqual(res.headers.get("Service-Worker-Allowed"), "/")
        self.assertIn("no-cache", res.headers.get("Cache-Control", "").lower())
        res.close()

    def test_offline_html_served(self):
        """GET /offline.html returns 200 and renders the offline fallback template."""
        res = self.client.get("/offline.html")
        self.assertEqual(res.status_code, 200)
        text = res.get_data(as_text=True)
        self.assertIn("offline", text.lower())
        self.assertIn("Savewise", text)
        res.close()

    def test_service_worker_excludes_api_from_caching(self):
        """static/service-worker.js must explicitly contain a rule excluding /api/ from caching."""
        sw_path = self.static_dir / "service-worker.js"
        self.assertTrue(sw_path.exists(), "static/service-worker.js must exist")

        with open(sw_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check for /api/ bypass
        self.assertIn("/api/", content, "Service worker must mention /api/")
        self.assertTrue(
            "url.pathname.startsWith(\"/api/\")" in content or "startsWith('/api/')" in content,
            "Service worker must contain a rule excluding /api/ routes from caching"
        )

        # Check for versioned cache name and offline fallback
        self.assertIn("CACHE_VERSION", content)
        self.assertIn("/offline.html", content)

    def test_html_pages_link_manifest_and_meta_tags(self):
        """Login page and base template must link manifest.json, theme-color, and apple-touch-icon."""
        res = self.client.get("/login")
        self.assertEqual(res.status_code, 200)
        login_html = res.get_data(as_text=True)

        self.assertIn('rel="manifest"', login_html)
        self.assertIn('name="theme-color"', login_html)
        self.assertIn('rel="apple-touch-icon"', login_html)
        self.assertIn("pwa.js", login_html)
        res.close()

    def test_chartjs_vendor_asset_exists_and_served(self):
        """Vendored Chart.js must exist in static/vendor/ and be served via static endpoint."""
        vendor_file = self.static_dir / "vendor" / "chart.umd.min.js"
        self.assertTrue(vendor_file.exists(), "Vendored Chart.js must exist in static/vendor/")
        self.assertGreater(os.path.getsize(vendor_file), 100000, "Vendored Chart.js must be a complete bundle")

        res = self.client.get("/static/vendor/chart.umd.min.js")
        self.assertEqual(res.status_code, 200)
        res.close()


if __name__ == "__main__":
    unittest.main()
