from __future__ import annotations

import logging
from typing import Any

from . import utils as u
from .params import INTERNAL_PARAMS as p

LOGGER = logging.getLogger(__name__)


async def zha_devices(
    app, listener, ieee, cmd, data, service, params, event_data
):
    doGenerateCSV = params[p.CSV_FILE] is not None

    # Determine fields to render.
    # If the user provides a list, it is also used to
    # limit the contents of "devices" in the event_data.
    if data is not None and isinstance(data, list):
        selectDeviceFields = True
        columns = data
    else:
        selectDeviceFields = False
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

    devices = [device.zha_device_info for device in listener.devices.values()]

    if ieee is not None:
        ieee = str(ieee)
        # Select only the device with the given address
        devices = [d for d in devices if str(d["ieee"]) == ieee]

    # Set default value for 'devices' in event_data,
    # may be slimmed down.  Ensures that devices is set in case
    # an exception occurs.
    event_data["devices"] = devices
    event_data["selectDeviceFields"] = selectDeviceFields

    if params[p.CSV_LABEL] is not None and isinstance(
        params[p.CSV_LABEL], str
    ):
        try:
            # Lambda function gets column and returns False if None
            # This makes compares possible for ints)
            devices = sorted(
                devices,
                key=lambda item: (  # pylint: disable=C3002
                    lambda a: (
                        a is None,
                        str.lower(a) if isinstance(a, str) else a,
                    )
                )(item[params[p.CSV_LABEL]]),
            )
        except Exception:  # nosec
            pass

    if doGenerateCSV or selectDeviceFields:
        if doGenerateCSV:
            # Write CSV header
            u.append_to_csvfile(
                columns,
                "csv",
                params[p.CSV_FILE],
                "device_dump['HEADER']",
                listener=listener,
                overwrite=True,
            )

        slimmedDevices: list[Any] = []
        for d in devices:
            # Fields for CSV
            csvFields: list[int | str | None] = []
            # Fields for slimmed devices dict
            rawFields: dict[str, Any] = {}

            for c in columns:
                if c not in d.keys():
                    csvFields.append(None)
                else:
                    val = d[c]
                    rawFields[c] = val
                    if c in ["manufacturer", "nwk"] and isinstance(val, int):
                        val = f"0x{val:04X}"

                    csvFields.append(d[c])

            slimmedDevices.append(rawFields)

            if doGenerateCSV:
                LOGGER.debug("Device %r", csvFields)
                u.append_to_csvfile(
                    csvFields,
                    "csv",
                    params[p.CSV_FILE],
                    f"device_dump[{d['ieee']}]",
                    listener=listener,
                )
        if selectDeviceFields:
            event_data["devices"] = slimmedDevices
