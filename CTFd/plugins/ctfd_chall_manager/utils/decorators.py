"""
This module defines decorators used by API endpoints.
"""

import functools

from CTFd.models import Challenges, Solves
from CTFd.utils.config import is_teams_mode
from CTFd.utils.dates import ctftime, ctf_paused
from CTFd.utils.decorators import require_verified_emails
from CTFd.utils.decorators.visibility import check_challenge_visibility
from CTFd.utils.modules import can_access_challenge
from CTFd.utils.user import get_current_user, is_admin
from flask import request
from flask_restx import abort


def challenge_visible(func):
    """
    This decorator abort the request if the challenge is not visible.
    The request is NOT abort if the user is admin.
    """

    @functools.wraps(func)
    @check_challenge_visibility
    @require_verified_emails
    def _challenge_visible(*args, **kwargs):
        # Parse once, then pass the authorized ID to the operation. Mutations
        # require JSON; a query parameter must never authorize another body ID.
        query_ids = request.args.getlist("challengeId")
        if len(query_ids) > 1:
            abort(400, "duplicate challengeId", success=False)
        read_request = request.method in ("GET", "HEAD")
        data = None if read_request else request.get_json(silent=True)
        if not read_request and not isinstance(data, dict):
            abort(400, "expected a JSON object", success=False)
        value = query_ids[0] if read_request and query_ids else (data or {}).get("challengeId")

        def parse_id(value):
            if isinstance(value, bool) or not isinstance(value, (str, int)):
                abort(400, "invalid challengeId", success=False)
            try:
                result = int(value)
            except (TypeError, ValueError, OverflowError):
                abort(400, "invalid challengeId", success=False)
            if result <= 0:
                abort(400, "invalid challengeId", success=False)
            return result

        challenge_id = parse_id(value)
        if query_ids and parse_id(query_ids[0]) != challenge_id:
            abort(400, "conflicting challengeId", success=False)
        challenge = Challenges.query.get(challenge_id)
        if challenge is None or challenge.type != "dynamic_iac":
            abort(404, "no instance challenge", success=False)

        if not is_admin():
            user = get_current_user()
            if is_teams_mode() and not user.team_id:
                abort(403, "join a team first", success=False)
            # Owners may clean up after an event; other actions follow CTFd access.
            if request.method != "DELETE":
                if not ctftime() or ctf_paused():
                    abort(403, "challenge access is closed or paused", success=False)
                if challenge.state in ("hidden", "locked") or not can_access_challenge(challenge, user):
                    abort(403, "challenge not visible", success=False)
                requirements = (challenge.requirements or {}).get("prerequisites", [])
                existing = {c.id for c in Challenges.query.with_entities(Challenges.id).all()}
                solved = {s.challenge_id for s in Solves.query.filter_by(account_id=user.account_id).all()}
                if not set(requirements).intersection(existing).issubset(solved):
                    abort(403, "challenge prerequisites not solved", success=False)
        return func(*args, {"challengeId": challenge_id}, **kwargs)

    return _challenge_visible
