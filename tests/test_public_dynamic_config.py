"""Local-only coverage for HTTPS sessions and public challenge presets."""
import os
import unittest
from unittest.mock import patch

from CTFd.config import TestingConfig
from CTFd.models import db
from tests.helpers import create_ctfd, gen_user


class HttpsCookieTests(unittest.TestCase):
    def setUp(self):
        class HttpsConfig(TestingConfig):
            SQLALCHEMY_DATABASE_URI = "sqlite://"
            SERVER_NAME = None
            PUBLIC_ORIGIN = "https://ctfd.example.test"
            SESSION_COOKIE_SECURE = True

        self.app = create_ctfd(config=HttpsConfig, enable_plugins=False)
        with self.app.app_context():
            gen_user(db, name="cookie-test", email="cookie@example.test")
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()

    def test_secure_cookie_follows_the_public_origin(self):
        from CTFd.config import secure_session_cookies

        self.assertTrue(secure_session_cookies("https://ctfd.example.test", False))
        self.assertTrue(secure_session_cookies("HTTPS://ctfd.example.test", False))
        self.assertTrue(secure_session_cookies("http://ctfd.example.test", True))
        self.assertFalse(secure_session_cookies("http://ctfd.example.test", False))
        self.assertFalse(secure_session_cookies("", False))

    def test_https_login_sets_secure_host_only_lax_session_cookie(self):
        request_args = {"base_url": "https://ctfd.example.test"}
        self.client.get("/login", **request_args)
        with self.client.session_transaction(**request_args) as session:
            nonce = session["nonce"]
        response = self.client.post(
            "/login",
            data={"name": "cookie-test", "password": "password", "nonce": nonce},
            **request_args,
        )

        cookie = next(value for key, value in response.headers if key.lower() == "set-cookie")
        attributes = {part.strip().lower() for part in cookie.split(";")[1:]}
        self.assertIn("secure", attributes)
        self.assertIn("httponly", attributes)
        self.assertIn("samesite=lax", attributes)
        self.assertFalse(any(attribute.startswith("domain=") for attribute in attributes))
        with self.client.session_transaction(**request_args) as session:
            self.assertTrue(session.get("id"), "HTTPS login should keep an authenticated session")


class PublicChallengePresetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Importing the plugin touches current_app while registering URL rules.
        cls.app = create_ctfd(config=TestingConfig, enable_plugins=False)
        cls.context = cls.app.app_context()
        cls.context.push()

    @classmethod
    def tearDownClass(cls):
        cls.context.pop()
        with cls.app.app_context():
            db.session.remove()
            db.engine.dispose()

    def setUp(self):
        from CTFd.plugins.ctfd_chall_manager.web_preset import web_payload

        self.web_payload = web_payload

    def test_configured_public_host_is_attached_to_new_preset_only(self):
        values = {"name": "test", "image": "example/test:v1", "port": "8080"}
        with patch.dict(os.environ, {
            "INSTANCE_PUBLIC_HOST": "targets.cyberdune.online",
            "INSTANCE_PORT_MIN": "20000",
            "INSTANCE_PORT_MAX": "20127",
            "INSTANCE_PORT_STATE_FILE": "/var/lib/chall-manager/ports.json",
        }), patch(
            "CTFd.plugins.ctfd_chall_manager.web_preset.get_config", return_value=None
        ):
            payload = self.web_payload(values)
        self.assertEqual(payload["additional"]["public_host"], "targets.cyberdune.online")
        self.assertEqual(payload["additional"]["port_min"], "20000")
        self.assertEqual(payload["additional"]["port_max"], "20127")
        self.assertEqual(payload["additional"]["port_state_file"], "/var/lib/chall-manager/ports.json")

    def test_unconfigured_host_preserves_private_default(self):
        values = {"name": "test", "image": "example/test:v1", "port": "8080"}
        with patch.dict(os.environ, {}, clear=True), patch(
            "CTFd.plugins.ctfd_chall_manager.web_preset.get_config", return_value=None
        ):
            payload = self.web_payload(values)
        self.assertNotIn("public_host", payload["additional"])

    def test_public_host_rejects_scheme_port_path_and_local_host(self):
        values = {"name": "test", "image": "example/test:v1", "port": "8080"}
        for invalid in (
            "https://targets.cyberdune.online",
            "targets.cyberdune.online:443",
            "targets.cyberdune.online/path",
            "localhost",
            "127.0.0.1",
        ):
            with self.subTest(host=invalid), patch.dict(
                os.environ, {"INSTANCE_PUBLIC_HOST": invalid}
            ), patch("CTFd.plugins.ctfd_chall_manager.web_preset.get_config", return_value=None):
                with self.assertRaisesRegex(ValueError, "INSTANCE_PUBLIC_HOST"):
                    self.web_payload(values)

    def test_public_preset_rejects_invalid_range_and_nonpersistent_state_path(self):
        values = {"name": "test", "image": "example/test:v1", "port": "8080"}
        for environment, message in (
            ({"INSTANCE_PUBLIC_HOST": "targets.cyberdune.online", "INSTANCE_PORT_MIN": "30000", "INSTANCE_PORT_MAX": "29999"}, "port range"),
            ({"INSTANCE_PUBLIC_HOST": "targets.cyberdune.online", "INSTANCE_PORT_MIN": "30000", "INSTANCE_PORT_MAX": "30001", "INSTANCE_PORT_STATE_FILE": "relative/ports.json"}, "STATE_FILE"),
            ({"INSTANCE_PUBLIC_HOST": "targets.cyberdune.online", "INSTANCE_PORT_MIN": "30000", "INSTANCE_PORT_MAX": "30001", "INSTANCE_PORT_STATE_FILE": "/var/lib/chall-manager/../outside.json"}, "STATE_FILE"),
        ):
            with self.subTest(environment=environment), patch.dict(os.environ, environment, clear=True), patch(
                "CTFd.plugins.ctfd_chall_manager.web_preset.get_config", return_value=None
            ):
                with self.assertRaisesRegex(ValueError, message):
                    self.web_payload(values)


if __name__ == "__main__":
    unittest.main()
