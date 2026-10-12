"""
This module describes the UserInstance API endpoint of the plugin:
Route: /api/v1/plugins/ctfd-chall-manager/instance.
"""

from CTFd.api.v1.helpers.request import validate_args
from CTFd.plugins.ctfd_chall_manager.models import DynamicIaCChallenge
from CTFd.plugins.ctfd_chall_manager.utils.chall_manager_error import (
    ChallManagerException,
)
from CTFd.plugins.ctfd_chall_manager.utils.decorators import challenge_visible
from CTFd.plugins.ctfd_chall_manager.utils.helpers import (
    check_source_can_create_instance,
    check_source_can_edit_instance,
    check_source_can_patch_instance,
)
from CTFd.plugins.ctfd_chall_manager.utils.instance_manager import (
    create_instance,
    delete_instance,
    get_instance,
    update_instance,
)
from CTFd.plugins.ctfd_chall_manager.utils.lock import load_or_store
from CTFd.plugins.ctfd_chall_manager.utils.logger import configure_logger
from CTFd.utils import user as current_user
from CTFd.utils.config import is_teams_mode
from CTFd.utils.decorators import authed_only
from flask_restx import Resource, abort

# Configure logger for this module
logger = configure_logger(__name__)


# region UserInstance
# Resource to permit user to manage their instance
class UserInstance(Resource):
    """
    UserInstance class handle CRUD operation for /instance API endpoint.
    To use methods, you need to be authenticated with user capable permission on CTFd.
    The sourceId cannot be defined as long as the current will be retrieve from flask session.
    If CTFd is configured as Team mode, the sourceId will be replaced by
    the team_id of the current user.
    """

    @staticmethod
    @authed_only
    @challenge_visible
    @validate_args({"challengeId": (int, None)}, location="query")
    def get(query_args):
        """
        Retrieve instance informations of challengeId provided on Chall-Manager.
        """
        # mandatory
        challenge_id = query_args.pop("challengeId", None)

        # check userMode of CTFd
        user = current_user.get_current_user()
        user_id = user.id
        source_id = user_id
        logger.info("user %s request GET on challenge %s", source_id, challenge_id)

        if is_teams_mode():
            source_id = user.team_id
            # If user has no team
            if not source_id:
                logger.info("user %s has no team, abort", user_id)
                abort(403, "unauthorized", success=False)

        if not challenge_id or not source_id:
            logger.warning("Missing argument: challenge_id or source_id")
            abort(400, "missing argument challenge_id of source_id", success=False)

        # if challenge is shared
        challenge = DynamicIaCChallenge.query.filter_by(id=challenge_id).first()
        if challenge.shared:
            source_id = 0

        try:
            logger.debug(
                "getting instance for challenge_id: %s, source_id: %s",
                challenge_id,
                source_id,
            )
            result = get_instance(challenge_id, source_id)
            logger.info("instance retrieved for challenge %s source %s", challenge_id, source_id)
        except ChallManagerException as e:
            if e.http_code == 404:
                return {"success": True, "data": None}, 200
            logger.error("error while getting instance: %s", e)
            return {
                "success": False,
                "message": "error while getting instance info, contact admins",
            }, e.http_code

        # return only necessary values
        data = {}
        for k in ["connectionInfo", "until", "since"]:
            if k in result.keys():
                data[k] = result[k]

        return {"success": True, "data": data}, 200

    @staticmethod
    @authed_only
    @challenge_visible
    @validate_args({"challengeId": (int, None)}, location="json")
    def post(json_args):  # pylint: disable=too-many-return-statements,too-many-branches
        """
        Create an instance of challengeId provided on Chall-Manager.
        This method requires user to be authenticated and has suffisant mana to perform creation.
        """
        challenge_id = json_args.pop("challengeId", None)
        if challenge_id is None:
            abort(400, "missing challenge_id")

        user = current_user.get_current_user()
        user_id = int(user.id)
        source_id = user_id
        logger.info(
            "user %s request instance creation of challenge %s", source_id, challenge_id
        )
        # check userMode of CTFd
        if is_teams_mode():
            source_id = user.team_id
            # If user has no team
            if not source_id:
                logger.info("user %s has no team, abort", user_id)
                abort(403, "unauthorized", success=False)

        lock = load_or_store(str(source_id))
        if not lock.lock(blocking=False):
            logger.debug("instance creation already in progress, abort")
            abort(429, "instance creation already in progress", success=False)

        try:
            logger.debug("post /instance acquire the player lock for %s", source_id)
            # Return the current instance for retries instead of issuing another create.
            try:
                existing = get_instance(challenge_id, source_id, fresh=True)
            except ChallManagerException as error:
                if error.http_code != 404:
                    raise
            else:
                return {"success": True, "data": {k: existing[k] for k in ["connectionInfo", "until", "since"] if k in existing}}, 200

            if not check_source_can_create_instance(challenge_id, source_id):
                abort(403, "You or your team used up all your mana.", success=False)

            logger.debug(
                "creating instance for challenge_id: %s, source_id: %s",
                challenge_id,
                source_id,
            )
            result = create_instance(challenge_id, source_id)
            logger.info(
                "instance for challenge_id: %s, source_id: %s created successfully",
                challenge_id,
                source_id,
            )

        except ChallManagerException as e:
            if "already exist" in e.message:
                return {
                    "success": False,
                    "message": "instance already exists",
                }, 200
            return {
                "success": False,
                "message": "error while creating instance, contact admins",
            }, e.http_code

        finally:
            logger.debug("post /instance release the player lock for %s", source_id)
            lock.unlock()

        # return only necessary values
        data = {}
        for k in ["connectionInfo", "until", "since"]:
            if k in result.keys():
                data[k] = result[k]

        return {"success": True, "data": data}, 200

    @staticmethod
    @authed_only
    @challenge_visible
    @validate_args({"challengeId": (int, None)}, location="json")
    def patch(json_args):  # pylint: disable=too-many-return-statements
        """
        Renew instance on Chall-Manager.
        If the challengeId provided
        """
        challenge_id = json_args.pop("challengeId", None)
        if challenge_id is None:
            abort(400, "missing challenge_id")

        user = current_user.get_current_user()
        user_id = int(user.id)
        source_id = user_id
        logger.info(
            "user %s request instance renew of challenge %s", source_id, challenge_id
        )
        # check userMode of CTFd
        if is_teams_mode():
            source_id = user.team_id
            # If user has no team
            if not source_id:
                logger.info("user %s has no team, abort", user_id)
                abort(403, "unauthorized", success=False)

        if not check_source_can_patch_instance(challenge_id, source_id):
            abort(403, "unauthorized", success=False)

        try:
            logger.debug(
                "updating instance for challenge_id: %s, source_id: %s",
                challenge_id,
                source_id,
            )
            update_instance(challenge_id, source_id)
            logger.info(
                "instance for challenge_id: %s, source_id: %s updated successfully",
                challenge_id,
                source_id,
            )
        except ChallManagerException as e:
            logger.error("error while patching instance : %s", e)
            return {
                "success": False,
                "message": "error while patching instance, contact admins",
            }, e.http_code

        return {
            "success": True,
            "data": {"message": "Your instance has been renewed !"},
        }, 200

    @staticmethod
    @authed_only
    @challenge_visible
    @validate_args({"challengeId": (int, None)}, location="json")
    def delete(json_args):
        """
        Delete instance of the challengeId provided
        """
        challenge_id = json_args.pop("challengeId", None)
        if challenge_id is None:
            abort(400, "missing challenge_id")

        user = current_user.get_current_user()
        user_id = int(user.id)
        source_id = user_id
        logger.info(
            "user %s request instance delete of challenge %s", user_id, challenge_id
        )
        # check userMode of CTFd
        if is_teams_mode():
            source_id = user.team_id
            # If user has no team
            if not source_id:
                logger.info("user %s has no team, abort", user_id)
                abort(403, "unauthorized", success=False)

        lock = load_or_store(str(source_id))
        if not lock.lock(blocking=False):
            logger.debug("instance deletion already in progress, abort")
            abort(429, "instance deletion already in progress", success=False)

        try:
            # lock = load_or_store(f"{source_id}")
            logger.debug("delete /instance acquire the player lock for %s", source_id)
            if not check_source_can_edit_instance(challenge_id, source_id):
                abort(403, "unauthorized", success=False)

            logger.debug(
                "deleting instance for challenge_id: %s, source_id: %s",
                challenge_id,
                source_id,
            )
            delete_instance(challenge_id, source_id)
            logger.info(
                "instance for challenge_id: %s, source_id: %s deleted successfully",
                challenge_id,
                source_id,
            )

        except ChallManagerException as e:
            logger.error("error while deleting instance: %s", e)
            return {
                "success": False,
                "message": "error while deleting instance, contact admins",
            }, e.http_code

        finally:
            logger.debug("delete /instance release the player lock for %s", source_id)
            lock.unlock()

        return {"success": True, "data": {}}, 200
