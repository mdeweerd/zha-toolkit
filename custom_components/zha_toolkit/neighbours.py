from __future__ import annotations

import asyncio
import enum
import logging
import os
from random import uniform

import zigpy.zdo.types as zdo_t
from zigpy.exceptions import DeliveryError

from . import utils as u

LOGGER = logging.getLogger(__name__)


async def get_routes_and_neighbours(
    app, listener, ieee, cmd, data, service, params, event_data
):
    if ieee is None:
        LOGGER.error("missing ieee")
        return

    LOGGER.debug("Getting routes and neighbours: %s", service)
    device = await u.get_device(app, listener, ieee)
    event_data["result"] = await _routes_and_neighbours(device, listener)

    ieee_tail = "".join([f"{o:02X}" for o in device.ieee])

    fname = os.path.join(
        u.get_hass(listener).config.config_dir,
        "scans",
        f"routes_and_neighbours_{ieee_tail}.json",
    )
    u.helper_save_json(fname, event_data["result"])

    LOGGER.debug("Wrote scan results to '%s'", fname)


async def _routes_and_neighbours(device, listener):
    try:
        routes = await asyncio.wait_for(async_get_routes(device), 180)
    except asyncio.TimeoutError:
        routes = []
    await asyncio.sleep(uniform(1.0, 1.5))
    try:
        nbns = await asyncio.wait_for(async_get_neighbours(device), 180)
    except asyncio.TimeoutError:
        nbns = []

    return {"routes": routes, "neighbours": nbns}


async def all_routes_and_neighbours(
    app, listener, ieee, cmd, data, service, params, event_data
):
    LOGGER.debug("Getting routes and neighbours for all devices: %s", service)

    counter = 1
    devs = [d for d in app.devices.values() if not d.node_desc.is_end_device]
    all_routes = {}
    for device in devs:
        LOGGER.debug(
            "%s: Querying routes and neighbours: %s out of %s",
            device.ieee,
            counter,
            len(devs),
        )
        all_routes[str(device.ieee)] = await _routes_and_neighbours(
            device, listener
        )
        LOGGER.debug("%s: Got %s out of %s", device.ieee, counter, len(devs))
        counter += 1

    event_data["result"] = all_routes

    all_routes_name = os.path.join(
        u.get_hass(listener).config.config_dir,
        "scans",
        "all_routes_and_neighbours.json",
    )
    u.helper_save_json(all_routes_name, all_routes)


async def async_get_neighbours(device):
    """Pull neighbour table from a device."""

    def _process_neighbour(nbg):
        """Return dict of a neighbour entry."""

        # LOGGER.debug(f"NEIGHBOR: {nbg!r}")
        res = {}
        res["pan_id"] = str(nbg.extended_pan_id)
        res["ieee"] = str(nbg.ieee)
        res["nwk"] = str(nbg.nwk)
        res["device_type"] = nbg.device_type.name
        res["rx_on_when_idle"] = nbg.rx_on_when_idle.name
        res["relationship"] = nbg.relationship.name
        res["permit_joining"] = nbg.permit_joining.name
        res["depth"] = nbg.depth
        res["lqi"] = nbg.lqi
        return res

    result = []
    idx = 0
    while True:
        try:
            status, val = await device.zdo.request(
                zdo_t.ZDOCmd.Mgmt_Lqi_req, idx
            )
            LOGGER.debug(
                "%s: neighbour request Status: %s. Response: %r",
                device.ieee,
                status,
                val,
            )
            if zdo_t.Status.SUCCESS != status:
                LOGGER.debug(
                    "%s: device does not support 'Mgmt_Lqi_req'", device.ieee
                )
                break
        except DeliveryError:
            LOGGER.debug("%s: Could not deliver 'Mgmt_Lqi_req'", device.ieee)
            break

        LOGGER.debug(f"NEIGHBORS: {val!r}")

        if hasattr(val, "neighbor_table_list"):
            neighbours = val.neighbor_table_list
            entries = val.entries
        else:
            neighbours = val.NeighborTableList
            entries = val.Entries

        for neighbour in neighbours:
            result.append(_process_neighbour(neighbour))
            idx += 1

        if idx >= entries:
            break

        await asyncio.sleep(uniform(1.0, 1.5))

    return sorted(result, key=lambda x: x["ieee"])


async def async_get_routes(device):
    """Pull routing table from a device."""

    def _process_route(route):
        """Return a dict representing routing entry."""

        class RouteStatus(enum.IntEnum):
            Active = 0x0
            Discovery_Underway = 0x1
            Discovery_Failed = 0x2
            Inactive = 0x3
            Validation_Underway = 0x4

        res: dict[str, str | bool | None | int] = {}
        res["destination"] = f"0x{route.DstNWK:04x}"
        res["next_hop"] = f"0x{route.NextHop:04x}"
        raw = route.RouteStatus & 0x07
        try:
            cooked = RouteStatus(raw).name
        except ValueError:
            cooked = f"reserved_{raw:02x}"
        res["status"] = cooked
        res["memory_constrained"] = bool((route.RouteStatus >> 3) & 0x01)
        res["many_to_one"] = bool((route.RouteStatus >> 4) & 0x01)
        res["route_record_required"] = bool((route.RouteStatus >> 5) & 0x01)
        return res

    routes = []
    idx = 0
    while True:
        try:
            status, val = await device.zdo.request(
                zdo_t.ZDOCmd.Mgmt_Rtg_req, idx
            )
            LOGGER.debug(
                "%s: route request Status:%s. Routes: %r",
                device.ieee,
                status,
                val,
            )
            if zdo_t.Status.SUCCESS != status:
                LOGGER.debug(
                    "%s: Does not support 'Mgmt_rtg_req': %s",
                    device.ieee,
                    status,
                )
                break
        except DeliveryError:
            LOGGER.debug("%s: Could not deliver 'Mgmt_rtg_req'", device.ieee)
            break

        LOGGER.debug(f"Mgmt_Rtg_rsp: {val!r}")
        for route in val.RoutingTableList:
            routes.append(_process_route(route))
            idx += 1
        if idx >= val.Entries:
            break
        await asyncio.sleep(uniform(1.0, 1.5))

    return routes
