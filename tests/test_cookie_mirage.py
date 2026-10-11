"""Exercise the intended exploit and instance flag isolation without a web server."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "cookie_mirage", Path(__file__).resolve().parents[1] / "challenges/cookie-mirage/app.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def request(app, path="/", cookie=""):
    result = {}
    def start_response(status, headers):
        result.update(status=status, headers=dict(headers))
    result["body"] = b"".join(app({"PATH_INFO": path, "HTTP_COOKIE": cookie}, start_response)).decode()
    return result


class CookieMirageTests(unittest.TestCase):
    def test_guest_cannot_see_flag(self):
        app = module.create_app("CYBERDUNE{private-one}")
        for path in ("/", "/admin", "/robots.txt", "/missing"):
            self.assertNotIn("private-one", request(app, path)["body"])
        self.assertEqual(request(app, "/admin")["status"], "403 Forbidden")
        self.assertIn("role=guest", request(app)["headers"]["Set-Cookie"])

    def test_cookie_exploit_and_isolation(self):
        first = module.create_app("CYBERDUNE{private-one}")
        second = module.create_app("CYBERDUNE{private-two}")
        own = request(first, "/admin", "role=admin")
        other = request(second, "/admin", "role=admin")
        self.assertEqual(own["status"], "200 OK")
        self.assertIn("private-one", own["body"])
        self.assertNotIn("private-two", own["body"])
        self.assertIn("private-two", other["body"])
        self.assertNotIn("private-one", other["body"])

    def test_escape_and_require_flag(self):
        with self.assertRaises(ValueError):
            module.create_app("")
        app = module.create_app("<test>")
        self.assertIn("&lt;test&gt;", request(app, "/admin", "role=admin")["body"])
        self.assertEqual(request(app, "/admin", "role=guest")["status"], "403 Forbidden")


if __name__ == "__main__":
    unittest.main()
