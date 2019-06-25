import asyncio
import enum
import logging
import os
from random import uniform

import zigpy.types as t
import zigpy.zdo.types as zdo_t
from zigpy.exceptions import DeliveryError
from zigpy.util import retryable

from homeassistant.util.json import save_json

LOGGER = logging.getLogger(__name__)


@retryable((DeliveryError, asyncio.TimeoutError), tries=5)
def wrapper(cmd, *args, **kwargs):
    return cmd(*args, **kwargs)


async def routes_and_neighbours(app, listener, ieee, cmd, data, service):
    if ieee is None:
        LOGGER.error("missing ieee")
        return

    LOGGER.debug("Getting routes and neighbours: %s", service)
    device = app.get_device(ieee=ieee)
    await _routes_and_neighbours(device, listener)


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

    ieee_tail = ''.join(['%02x' % (o, ) for o in device.ieee])
    file_suffix = '_{}.txt'.format(ieee_tail)

    routes_name = os.path.join(
        listener._hass.config.config_dir, 'scans', 'routes'+file_suffix)
    save_json(routes_name, routes)

    neighbours_name = os.path.join(
        listener._hass.config.config_dir, 'scans', 'neighbours'+file_suffix)
    save_json(neighbours_name, nbns)

    LOGGER.debug("Wrote scan results to '%s' and '%s'",
                 routes_name,
                 neighbours_name)


async def all_routes_and_neighbours(app, listener, ieee, cmd, data, service):
    LOGGER.debug("Getting routes and neighbours for all devices: %s", service)

    counter = 1
    devs = [d for d in app.devices.values() if not d.node_desc.is_end_device]
    for device in devs:
        LOGGER.debug("%s: Quering routes and neighbours: %s out of %s",
                     device.ieee, counter, len(devs))
        await _routes_and_neighbours(device, listener)
        LOGGER.debug("%s: Got %s out of %s", device.ieee, counter, len(devs))
        counter += 1


async def async_get_neighbours(device):
    """Pull neighbor table from a device."""

    def _process_neighbor(nbg):
        """Return dict of a neighbor entry."""
        class NeighbourType(enum.IntEnum):
            Coordinator = 0x0
            Router = 0x1
            End_Device = 0x2
            Unknown = 0x3

        class RxOnIdle(enum.IntEnum):
            Off = 0x0
            On = 0x1
            Unknown = 0x2

        class Relation(enum.IntEnum):
            Parent = 0x0
            Child = 0x1
            Sibling = 0x2
            None_of_the_above = 0x3
            Previous_Child = 0x4

        class PermitJoins(enum.IntEnum):
            Not_Accepting = 0x0
            Accepting = 0x1
            Unknown = 0x2

        res = {}

        res['pan_id'] = str(nbg.PanId)
        res['ieee'] = str(nbg.IEEEAddr)

        raw = nbg.NeighborType & 0x03
        try:
            nei_type = NeighbourType(raw).name
        except ValueError:
            nei_type = 'undefined_0x{:02x}'.format(raw)
        res['device_type'] = nei_type

        raw = (nbg.NeighborType >> 2) & 0x03
        try:
            rx_on = RxOnIdle(raw).name
        except ValueError:
            rx_on = 'undefined_0x{:02x}'.format(raw)
        res['rx_on_when_idle'] = rx_on

        raw = (nbg.NeighborType >> 4) & 0x07
        try:
            relation = Relation(raw).name
        except ValueError:
            relation = 'undefined_0x{:02x}'.format(raw)
        res['relationship'] = relation

        raw = nbg.PermitJoining & 0x02
        try:
            joins = PermitJoins(raw).name
        except ValueError:
            joins = 'undefined_0x{:02x}'.format(raw)
        res['new_joins_accepted'] = joins

        res['depth'] = nbg.Depth
        res['lqi'] = nbg.LQI

        return res

    result = []
    idx = 0
    while True:
        status, val = await device.zdo.request(zdo_t.ZDOCmd.Mgmt_Lqi_req, idx)
        LOGGER.debug("%s: neighbor request Status: %s. Response: %r",
                     device.ieee, status, val)
        if zdo_t.Status.SUCCESS != status:
            LOGGER.debug("%s: device oes not support 'Mgmt_Lqi_req'",
                         device.ieee)
            break

        neighbors = val.NeighborTableList
        for neighbor in neighbors:
            result.append(_process_neighbor(neighbor))
            idx += 1
        if idx >= val.Entries:
            break
        await asyncio.sleep(uniform(1.0, 1.5))

    return sorted(result, key=lambda x: x['ieee'])


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

        res = {}
        res['destination'] = '0x{:04x}'.format(route.DstNWK)
        res['next_hop'] = '0x{:04x}'.format(route.NextHop)
        raw = route.RouteStatus & 0x07
        try:
            cooked = RouteStatus(raw).name
        except ValueError:
            cooked = 'reserved_{:02x}'.format(raw)
        res['status'] = cooked
        res['memory_constrained'] = bool((route.RouteStatus >> 3) & 0x01)
        res['many_to_one'] = bool((route.RouteStatus >> 4) & 0x01)
        res['route_record_required'] = bool((route.RouteStatus >> 5) & 0x01)
        return res

    routes = []
    idx = 0
    while True:
        status, val = await device.zdo.request(zdo_t.ZDOCmd.Mgmt_Rtg_req, idx)
        LOGGER.debug("%s: route request Status:%s. Routes: %r",
                     device.ieee, status, val)
        if zdo_t.Status.SUCCESS != status:
            LOGGER.debug("%s: Does not support 'Mgmt_rtg_req': %s",
                         device.ieee, status)
            break

        for route in val.RoutingTableList:
            routes.append(_process_route(route))
            idx += 1
        if idx >= val.Entries:
            break
        await asyncio.sleep(uniform(1.0, 1.5))

    return routes
