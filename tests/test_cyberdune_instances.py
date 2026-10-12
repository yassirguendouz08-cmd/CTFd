"""CTFd integration tests with a fake instance service; never starts containers."""
import json
import time
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import requests

from CTFd.cache import cache, clear_challenges
from CTFd.config import TestingConfig
from CTFd.models import Challenges, Users, db
from CTFd.utils import set_config
from tests.helpers import create_ctfd, gen_challenge, gen_flag, gen_team, gen_user, login_as_user


class InstanceTestConfig(TestingConfig):
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SAFE_MODE = False
    SERVER_NAME = None


class FakeManager:
    def __init__(self):
        self.instances = {}
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        parsed = urlparse(url)
        path = parsed.path.split("/")
        payload = json.loads(kwargs.get("data") or "{}")
        response = requests.Response()
        response._content_consumed = True
        response.status_code = 200
        data = {}
        if "instance" in path:
            if len(path) == 4 and method == "GET":
                source = parse_qs(parsed.query)["sourceId"][0]
                response._content = b"\n".join(json.dumps({"result": v}).encode() for k, v in self.instances.items() if k[1] == source)
                return response
            if method == "POST":
                key = (payload["challengeId"], payload["sourceId"])
                now = datetime.utcnow()
                data = {"challengeId": key[0], "sourceId": key[1], "since": now.isoformat() + "Z", "until": (now + timedelta(minutes=10)).isoformat() + "Z", "connectionInfo": "http://target.example.test:32001", "flags": ["CYBERDUNE{" + key[0] + "_" + key[1] + "}"]}
                self.instances[key] = data
            else:
                key = (path[-2], path[-1])
                if key not in self.instances:
                    response.status_code = 404
                    data = {"code": 5, "message": "instance not found", "details": []}
                elif method == "DELETE":
                    self.instances.pop(key)
                else:
                    data = self.instances[key]
        response._content = json.dumps(data).encode()
        return response


class TestCyberduneInstances(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_ctfd(enable_plugins=True, config=InstanceTestConfig)
        cls.manager = FakeManager()
        cls.patches = [patch("requests." + method, side_effect=lambda url, _method=method.upper(), **kw: cls.manager.request(_method, url, **kw)) for method in ["get", "post", "patch", "delete"]]
        cls.patches.append(patch("requests.Session.get", side_effect=lambda url, **kw: cls.manager.request("GET", url, **kw)))
        for p in cls.patches:
            p.start()
        with cls.app.app_context():
            set_config("ctf_theme", "cyberdune")
            set_config("chall-manager:chall-manager_api_url", "http://fake-manager")
            set_config("chall-manager:chall-manager_api_timeout", 17)
            set_config("chall-manager:chall-manager_mana_total", 3)
            set_config("challenge_visibility", "public")
            set_config("start", None)
            set_config("end", None)
            cls.first_id = gen_user(db, name="instance-one", email="one@example.test").id
            cls.second_id = gen_user(db, name="instance-two", email="two@example.test").id
            cls.normal_id = gen_challenge(db, name="ordinary", value=100).id
            gen_flag(db, cls.normal_id, content="ordinary-flag")
        cls.admin = login_as_user(cls.app, name="admin", password="password")
        cls.first = login_as_user(cls.app, name="instance-one", password="password")
        cls.second = login_as_user(cls.app, name="instance-two", password="password")

    @classmethod
    def tearDownClass(cls):
        for p in reversed(cls.patches):
            p.stop()

    def setUp(self):
        self.manager.instances.clear()
        self.manager.calls.clear()
        with self.app.app_context():
            cache.clear()
            set_config("user_mode", "users")
            set_config("paused", False)
            set_config("start", None)
            set_config("end", None)
            set_config("challenge_visibility", "public")
            for uid in [self.first_id, self.second_id]:
                Users.query.get(uid).team_id = None
            db.session.commit()
        self.admin = login_as_user(self.app, name="admin", password="password")
        self.first = login_as_user(self.app, name="instance-one", password="password")
        self.second = login_as_user(self.app, name="instance-two", password="password")
        created = self.admin.post("/api/v1/challenges", json={"name": "Instance fixture", "category": "Web", "description": "Isolated integration fixture", "type": "dynamic_iac", "initial": 500, "minimum": 100, "decay": 10, "function": "logarithmic", "state": "visible", "scenario": "registry.example.test/scenario:v1", "timeout": 600, "mana_cost": 1, "shared": False, "additional": {"image": "private-image"}})
        self.assertEqual(created.status_code, 200, created.get_json())
        self.id = created.get_json()["data"]["id"]
        self.url = "/api/v1/plugins/ctfd-chall-manager/instance"

    def test_type_admin_and_normal_challenge(self):
        types = self.admin.get("/api/v1/challenges/types").get_json()["data"]
        self.assertIn("dynamic_iac", types)
        self.assertEqual(self.admin.get("/plugins/ctfd-chall-manager/admin/settings").status_code, 200)
        self.assertIn(b"Launch instance", self.first.get(f"/api/v1/challenges/{self.id}").data)
        self.assertEqual(self.first.post(self.url, json={"challengeId": self.normal_id}).status_code, 404)
        with patch("requests.get", side_effect=requests.ConnectionError()):
            self.assertEqual(self.first.post("/api/v1/challenges/attempt", json={"challenge_id": self.normal_id, "submission": "ordinary-flag"}).get_json()["data"]["status"], "correct")

    def test_owner_isolation_flag_validation_and_lifecycle(self):
        for client in [self.first, self.second]:
            result = client.post(self.url, json={"challengeId": self.id, "sourceId": 999})
            self.assertEqual(result.status_code, 200, result.get_json())
            self.assertNotIn("flags", result.get_json()["data"])
        other_flag = self.manager.instances[(str(self.id), str(self.second_id))]["flags"][0]
        own_flag = self.manager.instances[(str(self.id), str(self.first_id))]["flags"][0]
        self.assertEqual(self.first.post("/api/v1/challenges/attempt", json={"challenge_id": self.id, "submission": other_flag}).get_json()["data"]["status"], "incorrect")
        self.assertEqual(self.first.post("/api/v1/challenges/attempt", json={"challenge_id": self.id, "submission": own_flag}).get_json()["data"]["status"], "correct")
        self.assertEqual(self.first.patch(self.url, json={"challengeId": self.id}).status_code, 200)
        self.assertEqual(self.first.delete(self.url, json={"challengeId": self.id}).status_code, 200)
        self.assertIn((str(self.id), str(self.second_id)), self.manager.instances)
        self.assertNotIn((str(self.id), str(self.first_id)), self.manager.instances)

    def test_duplicate_launch_returns_existing_and_busy_lock_rejects_mutation(self):
        from CTFd.plugins.ctfd_chall_manager.utils.lock import load_or_store
        empty = self.first.get(self.url + f"?challengeId={self.id}")
        self.assertEqual(empty.status_code, 200)
        self.assertIsNone(empty.get_json()["data"])
        first = self.first.post(self.url, json={"challengeId": self.id})
        second = self.first.post(self.url, json={"challengeId": self.id})
        self.assertEqual(first.get_json(), second.get_json())
        creates = [call for call in self.manager.calls if call[0] == "POST" and call[1].endswith('/instance')]
        self.assertEqual(len(creates), 1)
        lock = load_or_store(str(self.first_id))
        self.assertTrue(lock.lock(blocking=False))
        try:
            self.assertEqual(self.first.post(self.url, json={"challengeId": self.id}).status_code, 429)
            self.assertEqual(self.first.delete(self.url, json={"challengeId": self.id}).status_code, 429)
        finally:
            lock.unlock()
        self.assertEqual(self.first.delete(self.url, json={"challengeId": self.id}).status_code, 200)

    def test_access_rules_and_current_backend_state(self):
        self.assertIn(self.app.test_client().post(self.url, json={"challengeId": self.id}).status_code, [302, 403])
        with self.app.app_context():
            set_config("paused", True)
        self.assertEqual(self.first.post(self.url, json={"challengeId": self.id}).status_code, 403)
        with self.app.app_context():
            set_config("paused", False)
            c = Challenges.query.get(self.id)
            c.requirements = {"prerequisites": [self.normal_id]}
            db.session.commit()
        self.assertEqual(self.first.post(self.url, json={"challengeId": self.id}).status_code, 403)
        with self.app.app_context():
            c = Challenges.query.get(self.id)
            c.requirements = None
            c.scheduled_at = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()
        self.assertEqual(self.first.post(self.url, json={"challengeId": self.id}).status_code, 403)
        with self.app.app_context():
            c = Challenges.query.get(self.id)
            c.scheduled_at = None
            db.session.commit()
        self.assertEqual(self.first.post(self.url, json={"challengeId": self.id}).status_code, 200)
        key = (str(self.id), str(self.first_id))
        flag = self.manager.instances.pop(key)["flags"][0]
        # Cache still contains the instance; submissions must consult authoritative state.
        result = self.first.post("/api/v1/challenges/attempt", json={"challenge_id": self.id, "submission": flag}).get_json()
        self.assertEqual(result["data"]["status"], "incorrect")
        self.assertIn("Expired", result["data"]["message"])
        self.assertTrue(all(call[2].get("timeout") == 17 for call in self.manager.calls if call[1].startswith("http://fake-manager")))

    def test_team_ownership(self):
        with self.app.app_context():
            team = gen_team(db, name="instance-team")
            team_id = team.id
            for uid in [self.first_id, self.second_id]:
                Users.query.get(uid).team_id = team_id
            db.session.commit()
            set_config("user_mode", "teams")
        self.assertEqual(self.first.post(self.url, json={"challengeId": self.id}).status_code, 200)
        self.assertEqual(self.second.get(self.url + f"?challengeId={self.id}").status_code, 200)
        self.assertEqual(list(self.manager.instances), [(str(self.id), str(team_id))])

    def test_mana_limit_and_backend_failure(self):
        with self.app.app_context():
            set_config("chall-manager:chall-manager_mana_total", 1)
        self.assertEqual(self.first.post(self.url, json={"challengeId": self.id}).status_code, 200)
        created = self.admin.post("/api/v1/challenges", json={"name": "Second resource", "type": "dynamic_iac", "initial": 100, "minimum": 100, "decay": 10, "function": "linear", "state": "visible", "scenario": "registry.example.test/scenario:v1", "mana_cost": 1})
        other_id = created.get_json()["data"]["id"]
        self.assertEqual(self.first.post(self.url, json={"challengeId": other_id}).status_code, 403)
        self.assertEqual(self.first.delete(self.url, json={"challengeId": self.id}).status_code, 200)
        with patch("requests.post", side_effect=requests.ConnectionError()):
            response = self.first.post(self.url, json={"challengeId": other_id})
        self.assertEqual(response.status_code, 500)
        self.assertFalse(response.get_json()["success"])
        with self.app.app_context():
            set_config("chall-manager:chall-manager_mana_total", 3)

    def test_future_timing_and_cleanup_after_event(self):
        self.assertEqual(self.first.post(self.url, json={"challengeId": self.id}).status_code, 200)
        with self.app.app_context():
            set_config("start", int(time.time()) + 3600)
        self.assertEqual(self.first.patch(self.url, json={"challengeId": self.id}).status_code, 403)
        self.assertEqual(self.first.get(self.url + f"?challengeId={self.id}").status_code, 403)
        self.assertEqual(self.first.delete(self.url, json={"challengeId": self.id}).status_code, 200)

    def test_expiry_deadline_before_janitor(self):
        self.assertEqual(self.first.post(self.url, json={"challengeId": self.id}).status_code, 200)
        data = self.manager.instances[(str(self.id), str(self.first_id))]
        data["until"] = (datetime.utcnow() - timedelta(seconds=1)).isoformat() + "Z"
        result = self.first.post("/api/v1/challenges/attempt", json={"challenge_id": self.id, "submission": data["flags"][0]}).get_json()
        self.assertEqual(result["data"]["status"], "incorrect")
        self.assertIn("Expired", result["data"]["message"])
