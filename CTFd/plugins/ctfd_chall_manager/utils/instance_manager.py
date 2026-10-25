"""
This module contains all functions to use Chall-Manager InstanceManager group.
"""

import json
import time

import requests
from CTFd.cache import cache
from CTFd.plugins.ctfd_chall_manager.utils.chall_manager_error import (
    ChallManagerException,
    chall_manager_exception_builder,
)
from CTFd.plugins.ctfd_chall_manager.utils.logger import configure_logger
from CTFd.utils import get_config

logger = configure_logger(__name__)
def api_timeout():
    # Resolve after plugin setup and honour later admin updates.
    try:
        value = int(get_config("chall-manager:chall-manager_api_timeout") or 60)
    except (TypeError, ValueError):
        value = 60
    return max(1, value)

# pylint: disable=duplicate-code
# pylint detect duplicate-code between challenge_store and intance_manager
# This is false positive


def create_instance(challenge_id: int, source_id: int) -> dict | ChallManagerException:
    """
    Spins up a challenge instance, iif the challenge is registered and no instance is yet running.

    :param challenge_id: id of challenge for the instance
    :param source_id: id of source for the instance
    :return dict: JSON response of chall-manager API
    :raise ChallManagerException:
    """

    cm_api_url = get_config("chall-manager:chall-manager_api_url")
    url = f"{cm_api_url}/api/v1/instance"
    cache_key = f"instance:{challenge_id}:{source_id}"

    payload = {"challengeId": str(challenge_id), "sourceId": str(source_id)}

    headers = {"Content-Type": "application/json"}

    logger.debug(
        "creating instance for challenge_id=%s, source_id=%s", challenge_id, source_id
    )

    started = time.monotonic()
    try:
        r = requests.post(
            url, data=json.dumps(payload), headers=headers, timeout=api_timeout()
        )
        logger.debug("manager response status: %s", r.status_code)
        r.raise_for_status()
    except requests.HTTPError as e:
        custom_exception = chall_manager_exception_builder(r)
        raise custom_exception from e
    except requests.RequestException as e:
        raise ChallManagerException() from e

    logger.info("instance create completed challenge=%s source=%s elapsed=%.3fs", challenge_id, source_id, time.monotonic() - started)
    # store the informations on cache
    result = r.json()
    cache.set(cache_key, result, timeout=60)

    return result


def delete_instance(challenge_id: int, source_id: int) -> dict | ChallManagerException:
    """
    After completion, the challenge instance is no longer required.
    This spins down the instance and removes if from filesystem.

    :param challenge_id: id of challenge for the instance
    :param source_id: id of source for the instance
    :return dict: JSON response of chall-manager API
    :raise ChallManagerException:
    """

    cm_api_url = get_config("chall-manager:chall-manager_api_url")
    url = f"{cm_api_url}/api/v1/instance/{challenge_id}/{source_id}"
    cache_key = f"instance:{challenge_id}:{source_id}"

    logger.debug(
        "deleting instance for challenge_id=%s, source_id=%s", challenge_id, source_id
    )

    try:
        r = requests.delete(url, timeout=api_timeout())
        logger.debug("manager response status: %s", r.status_code)
        r.raise_for_status()
    except requests.HTTPError as e:
        custom_exception = chall_manager_exception_builder(r)
        raise custom_exception from e
    except requests.RequestException as e:
        raise ChallManagerException() from e

    # delete cache to prevent connectionInfo in front
    cached = cache.get(cache_key)
    if cached:
        logger.debug("delete cache informations for %s", cache_key)
        cache.delete(cache_key)

    return r.json()


def get_instance(challenge_id: int, source_id: int, fresh=False) -> dict | ChallManagerException:
    """
    Once created, you can retrieve the instance information.
    If it has not been created yet, returns an error.

    :param challenge_id: id of challenge for the instance
    :param source_id: id of source for the instance
    :return dict: JSON response of chall-manager API
    :raise ChallManagerException:
    """

    cm_api_url = get_config("chall-manager:chall-manager_api_url")
    url = f"{cm_api_url}/api/v1/instance/{challenge_id}/{source_id}"
    cache_key = f"instance:{challenge_id}:{source_id}"

    cached = cache.get(cache_key)
    if cached and not fresh:
        logger.debug("use cache informations for %s", cache_key)
        return cached

    logger.debug(
        "getting instance information for challenge_id=%s, source_id=%s",
        challenge_id,
        source_id,
    )

    try:
        r = requests.get(url, timeout=api_timeout())
        logger.debug("manager response status: %s", r.status_code)
        r.raise_for_status()
    except requests.HTTPError as e:
        custom_exception = chall_manager_exception_builder(r)
        raise custom_exception from e
    except requests.RequestException as e:
        raise ChallManagerException() from e

    result = r.json()
    if "since" in result.keys() and result["since"] is not None:
        # store in cache only if the instance exists
        logger.debug("store result in cache for better performances")
        cache.set(cache_key, result, timeout=60)

    return result


def update_instance(challenge_id: int, source_id: int) -> dict | ChallManagerException:
    """
    This will set the until date to the request time more the challenge timeout.

    :param challenge_id: id of challenge for the instance
    :param source_id: id of source for the instance
    :return dict: JSON response of chall-manager API
    :raise ChallManagerException:
    """

    cm_api_url = get_config("chall-manager:chall-manager_api_url")
    url = f"{cm_api_url}/api/v1/instance/{challenge_id}/{source_id}"
    cache_key = f"instance:{challenge_id}:{source_id}"

    payload = {}

    headers = {"Content-Type": "application/json"}

    logger.debug(
        "updating instance for challenge_id=%s, source_id=%s", challenge_id, source_id
    )

    try:
        r = requests.patch(
            url, data=json.dumps(payload), headers=headers, timeout=api_timeout()
        )
        logger.debug("manager response status: %s", r.status_code)
        r.raise_for_status()
    except requests.HTTPError as e:
        custom_exception = chall_manager_exception_builder(r)
        raise custom_exception from e
    except requests.RequestException as e:
        raise ChallManagerException() from e

    # update informations for the next GET request
    result = r.json()
    if "since" in result.keys() and result["since"] is not None:
        logger.debug("store result in cache for better performances")
        cache.set(cache_key, result, timeout=60)

    return result


def query_instance(source_id: int) -> list | ChallManagerException:
    """
    This will return a list with all instances that exists on chall-manager for the source_id given.

    :param source_id: id of source for the instance
    :return list: all instances for the source_id (e.g [{source_id:x, challenge_id, y},..])
    """

    cm_api_url = get_config("chall-manager:chall-manager_api_url")
    url = f"{cm_api_url}/api/v1/instance?sourceId={source_id}"
    s = requests.Session()

    result = []

    logger.debug("querying instances for sourceId=%s", source_id)

    try:
        with s.get(url, headers=None, stream=True, timeout=api_timeout()) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if line:
                    res = line.decode("utf-8")
                    res = json.loads(res)
                    if not isinstance(res, dict) or "error" in res or not isinstance(res.get("result"), dict):
                        raise ValueError("Invalid instance listing response")
                    instance = res["result"]
                    if "challengeId" not in instance or "sourceId" not in instance or str(instance["sourceId"]) != str(source_id):
                        raise ValueError("Invalid instance listing ownership")
                    result.append(instance)
        logger.debug("queried %s instances", len(result))
    except Exception as e:
        logger.error("connection error: %s", e)
        raise ChallManagerException(message="connection error") from e

    return result
