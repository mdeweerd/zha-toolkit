from __future__ import annotations

import logging
from typing import Any

from . import utils as u
from .params import INTERNAL_PARAMS as p

LOGGER = logging.getLogger(__name__)


async def get_groups(
    app, listener, ieee, cmd, data, service, params, event_data
):
    if ieee is None:
        LOGGER.error("missing ieee")
        return

    src_dev = await u.get_device(app, listener, ieee)

    groups: dict[int, dict[str, Any]] = {}
    endpoint_id = params[p.EP_ID]

    event_data["result"] = []
    for ep_id, ep in src_dev.endpoints.items():
        if ep_id == 0 or (endpoint_id is not None and ep_id != endpoint_id):
            continue
        try:
            ep_info: dict[str, Any] = {}
            res = await u.retry_wrapper(
                ep.groups.read_attributes,
                ["name_support"],
                tries=params[p.TRIES],
            )
            event_data["result"].append(res)

            name_support = res[0]["name_support"]
            ep_info["name_support"] = int(name_support)
            LOGGER.debug(
                "Group on 0x%04X EP %u name support: %s",
                src_dev.nwk,
                ep_id,
                name_support,
            )

            all_groups = await u.retry_wrapper(
                ep.groups.get_membership, [], tries=params[p.TRIES]
            )
            LOGGER.debug(
                "Groups on 0x%04X EP %u : %s", src_dev.nwk, ep_id, all_groups
            )
            ep_info["groups"] = all_groups[1]
            groups[ep_id] = ep_info
        except AttributeError:
            LOGGER.debug(
                "0x%04X/EP %u: no group cluster found", src_dev.nwk, ep_id
            )

    event_data["groups"] = groups


async def add_group(
    app, listener, ieee, cmd, data, service, params, event_data
):
    if ieee is None or not data:
        raise ValueError("ieee and command_data required")

    src_dev = await u.get_device(app, listener, ieee)

    group_id = u.str2int(data)
    endpoint_id = params[p.EP_ID]

    result = []
    for ep_id, ep in src_dev.endpoints.items():
        if ep_id == 0 or (endpoint_id is not None and ep_id != endpoint_id):
            # Skip ZDO or endpoints that are not selected
            continue
        try:
            res = await u.retry_wrapper(
                ep.groups.add,
                group_id,
                f"group {group_id}",
                tries=params[p.TRIES],
            )
            result.append(res)
            LOGGER.debug(
                "0x%04x EP %u: Setting group 0x%04x: %s",
                src_dev.nwk,
                ep_id,
                group_id,
                res,
            )
        except AttributeError:
            LOGGER.debug(
                "0x%04x EP %u : no group cluster found", src_dev.nwk, ep_id
            )

    event_data["result"] = result


async def remove_group(
    app, listener, ieee, cmd, data, service, params, event_data
):
    if ieee is None or not data:
        raise ValueError("ieee and command_data required")

    src_dev = await u.get_device(app, listener, ieee)

    group_id = u.str2int(data)
    endpoint_id = params[p.EP_ID]

    result = []
    for ep_id, ep in src_dev.endpoints.items():
        if ep_id == 0 or (endpoint_id is not None and ep_id != endpoint_id):
            # Skip ZDO or endpoints that are not selected
            continue
        try:
            res = await ep.groups.remove(group_id)
            result.append(res)
            LOGGER.debug(
                "0x%04x EP %u: Removing group 0x%04x: %s",
                src_dev.nwk,
                ep_id,
                group_id,
                res,
            )
        except AttributeError:
            LOGGER.debug(
                "0x%04x EP %u: no group cluster found", src_dev.nwk, ep_id
            )

    event_data["result"] = result


async def remove_all_groups(
    app, listener, ieee, cmd, data, service, params, event_data
):
    LOGGER.debug("running 'remove all group' command: %s", service)
    if ieee is None:
        return

    src_dev = await u.get_device(app, listener, ieee)
    endpoint_id = params[p.EP_ID]
    result = []

    for ep_id, ep in src_dev.endpoints.items():
        if ep_id == 0 or (endpoint_id is not None and ep_id != endpoint_id):
            continue
        try:
            res = await ep.groups.remove_all()
            result.append(res)
            LOGGER.debug("0x%04x: Removing all groups: %s", src_dev.nwk, res)
        except AttributeError:
            LOGGER.debug(
                "0x%04x: no group cluster on endpoint #%d", src_dev.nwk, ep_id
            )

    event_data["result"] = result


async def add_to_group(
    app, listener, ieee, cmd, data, service, params, event_data
):
    if data is None or ieee is None:
        LOGGER.error("invalid arguments for subscribe_group()")
        return

    dev = await u.get_device(app, listener, ieee)

    grp_id = u.str2int(data)
    endpoint_id = params[p.EP_ID]

    result = []
    for ep_id, ep in dev.endpoints.items():
        if ep_id == 0 or (endpoint_id is not None and ep_id != endpoint_id):
            continue
        LOGGER.debug("Subscribing %s EP %u to group: %s", ieee, ep_id, grp_id)
        res = await ep.add_to_group(grp_id, f"Group {data}")
        result.append(res)
        LOGGER.info(
            "Subscribed %s EP %u to group: %s Result: %r",
            ieee,
            ep_id,
            grp_id,
            res,
        )

    event_data["result"] = result


async def remove_from_group(
    app, listener, ieee, cmd, data, service, params, event_data
):
    if data is None or ieee is None:
        raise ValueError("ieee and command_data required")

    dev = await u.get_device(app, listener, ieee)

    grp_id = u.str2int(data)
    endpoint_id = params[p.EP_ID]

    result = []
    for ep_id, ep in dev.endpoints.items():
        if ep_id == 0 or (endpoint_id is not None and ep_id != endpoint_id):
            continue
        LOGGER.debug(
            "Unsubscribing %s EP %u from group: %s", ieee, ep_id, grp_id
        )
        res = await ep.remove_from_group(grp_id)
        result.append(res)
        LOGGER.info(
            "Unsubscribed %s EP %u from group: %s Result: %r",
            ieee,
            ep_id,
            grp_id,
            res,
        )

    event_data["result"] = result


async def get_zll_groups(
    app, listener, ieee, cmd, data, service, params, event_data
):
    from zigpy.zcl.clusters.lightlink import LightLink

    if ieee is None:
        LOGGER.error("missing ieee")
        return

    dev = await u.get_device(app, listener, ieee)

    clusters = [
        ep.in_clusters[LightLink.cluster_id]
        for epid, ep in dev.endpoints.items()
        if epid and LightLink.cluster_id in ep.in_clusters
    ]
    zll_cluster = None
    try:
        zll_cluster = next(iter(clusters))
    except Exception:
        LOGGER.warning("No cluster in clusters")

    if not zll_cluster:
        msg = f"Couldn't find ZLL Commissioning cluster on {dev.ieee}"
        event_data["warning"] = msg
        LOGGER.warning(msg)
        return

    res = await zll_cluster.get_group_identifiers(0)
    groups = [g.group_id for g in res[2]]
    LOGGER.debug("Get group identifiers response: %s", groups)

    event_data["groups"] = groups
