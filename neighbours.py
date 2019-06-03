import asyncio
import enum
import logging
import os
from collections import OrderedDict
from random import uniform

import zigpy.zdo.types as zdo_t
from zigpy.exceptions import DeliveryError
from zigpy.util import retryable

from homeassistant.util.json import save_json

LOGGER = logging.getLogger(__name__)


@retryable((DeliveryError, asyncio.TimeoutError), tries=5)
def wrapper(cmd, *args, **kwargs):
    return cmd(*args, **kwargs)


async def get_routes(dev):
    return []


async def routes_and_neighbours(app, listener, ieee, cmd, data, service):
    if ieee is None:
        LOGGER.error("missing ieee")
        return

    LOGGER.debug("Getting routes and neighbours: %s", service)
    device = app.get_device(ieee=ieee)
    routes = await get_routes(device)
    nbns = await async_get_neighbours(device)

    ieee_tail = ''.join(['%02x' % (o, ) for o in ieee])
    file_suffix = '_{}.txt'.format(ieee_tail)

    routes_name = os.path.join(
        listener._hass.config.config_dir, 'scans', 'routes'+file_suffix)
    save_json(routes_name, routes)

    neighbours_name = os.path.join(
        listener._hass.config.config_dir, 'scans', 'neighbours'+file_suffix)
    save_json(neighbours_name, nbns)

    LOGGER.debug("Wrote scan results to '%s' and '%s'", routes_name, neighbours_name)


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
        await asyncio.sleep(uniform(0.1, 1.0))

    return sorted(result, key=lambda x: x['ieee'])
