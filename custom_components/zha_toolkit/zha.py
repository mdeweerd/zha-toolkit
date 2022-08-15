from __future__ import annotations

import logging

from . import utils as u
from .params import INTERNAL_PARAMS as p

LOGGER = logging.getLogger(__name__)


async def zha_devices(
    app, listener, ieee, cmd, data, service, params, event_data
):

    devices = [device.zha_device_info for device in listener.devices.values()]
    event_data["devices"] = devices

    if params[p.CSV_LABEL] is not None and isinstance(
        params[p.CSV_LABEL], str
    ):
        try:
            # Lambda function gets column and returns false if None
            # This make compares possible for ints)
            devices = sorted(
                devices,
                key=lambda item: (  # pylint: disable=C3002
                    lambda a: (a is None, a)
                )(item[params[p.CSV_LABEL]]),
            )
        except Exception:  # nosec
            pass

    if params[p.CSV_FILE] is not None:
        if data is not None and isinstance(data, list):
            columns = data
        else:
            columns = [
                "ieee",
                "nwk",
                "manufacturer",
                "model",
                "name",
                "quirk_applied",
                "quirk_class",
                "manufacturer_code",
                "power_source",
                "lqi",
                "rssi",
                "last_seen",
                "available",
                "device_type",
                "user_given_name",
                "device_reg_id",
                "area_id",
            ]
            # TODO: Skipped in columns, needs special handling
            #  'signature'
            #  'endpoints'

        u.append_to_csvfile(
            columns,
            "csv",
            params[p.CSV_FILE],
            "device_dump['HEADER']",
            listener=listener,
            overwrite=True,
        )

        for d in devices:
            fields: list[int | str | None] = []
            for c in columns:
                if c not in d.keys():
                    fields.append(None)
                else:
                    val = d[c]
                    if c in ["manufacturer", "nwk"] and isinstance(val, int):
                        val = f"0x{val:04X}"

                    fields.append(d[c])

            LOGGER.debug("Device %r", fields)
            u.append_to_csvfile(
                fields,
                "csv",
                params[p.CSV_FILE],
                f"device_dump[{d['ieee']}]",
                listener=listener,
            )
