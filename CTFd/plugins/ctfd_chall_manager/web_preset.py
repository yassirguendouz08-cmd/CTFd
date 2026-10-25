"""Admin-only shortcuts for the reusable CyberDune web scenario."""
import re
import secrets
import os

from flask import redirect, render_template, request

from CTFd.cache import clear_challenges
from CTFd.exceptions.challenges import ChallengeCreateException
from CTFd.plugins.ctfd_chall_manager.models import DynamicIaCValueChallenge
from CTFd.utils import get_config
from CTFd.utils.decorators import admins_only

DEFAULT_WEB_SCENARIO = "scenario-registry:5000/scenarios/web-container:v4-amd64"


def web_payload(values):
    name = values.get("name", "").strip()
    image = values.get("image", "").strip()
    if not name or len(name) > 128:
        raise ValueError("Enter a challenge name (up to 128 characters).")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/@-]{0,254}", image):
        raise ValueError("Enter a valid Docker image reference without spaces.")
    try:
        points = int(values.get("points", "100"))
        port = int(values.get("port", "8080"))
    except (ValueError, TypeError) as exc:
        raise ValueError("Points and port must be whole numbers.") from exc
    if not 1 <= points <= 1000000 or not 1 <= port <= 65535:
        raise ValueError("Use positive points and an internal port between 1 and 65535.")
    scenario = get_config("chall-manager:web_scenario") or DEFAULT_WEB_SCENARIO
    payload = {
        "type": "dynamic_iac", "name": name, "category": "Web",
        "description": values.get("description", "").strip() or "Find the flag in your private web instance.",
        "initial": points, "minimum": points, "decay": 10, "function": "linear",
        "state": "hidden", "shared": False, "destroy_on_flag": False,
        "mana_cost": 1, "timeout": 600, "until": None, "min": 0, "max": 0,
        "scenario": scenario,
        "additional": {"image": image, "port": str(port), "flag_seed": secrets.token_hex(32)},
    }
    public_host = os.getenv("INSTANCE_PUBLIC_HOST", "").strip()
    if public_host:
        payload["additional"]["public_host"] = public_host
    return payload


def register_web_preset(blueprint):
    @blueprint.route("/admin/web/new", methods=["GET", "POST"])
    @admins_only
    def new_web_challenge():
        values = {"name": "", "image": "cyberdune/cookie-mirage:v1",
                  "description": "", "points": "100", "port": "8080"}
        error = None
        status = 200
        if request.method == "POST":
            values.update({key: request.form.get(key, default) for key, default in values.items()})
            try:
                payload = web_payload(values)
                challenge = DynamicIaCValueChallenge.create_from_data(payload)
                clear_challenges()
                return redirect(f"{request.script_root}/admin/challenges/{challenge.id}")
            except ValueError as exc:
                error, status = str(exc), 400
            except ChallengeCreateException:
                error = "The backend could not register this challenge. Check the saved web scenario and backend logs."
                status = 502
        return render_template("chall_manager_new_web.html", values=values, error=error), status
