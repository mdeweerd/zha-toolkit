from __future__ import annotations

import logging

from homeassistant.helpers.template import Template
from homeassistant.util import dt as dt_util

from . import utils as u
from .params import INTERNAL_PARAMS as p

LOGGER = logging.getLogger(__name__)


async def ha_set_state(  # noqa: C901
    app, listener, ieee, cmd, data, service, params, event_data
):
    success = True

    val = params[p.ATTR_VAL]
    state_field = None

    state_template_str = params[p.STATE_VALUE_TEMPLATE]
    if state_template_str is not None:
        template = Template(
            "{{ " + state_template_str + " }}", u.get_hass(listener)
        )
        new_value = template.async_render(value=val, attr_val=val)
        val = new_value

    # Write value to provided state or state attribute
    if params[p.STATE_ID] is None:
        raise ValueError("'state_id' is required")

    if params[p.STATE_ATTR] is not None:
        state_field = f"{params[p.STATE_ID]}[{params[p.STATE_ATTR]}]"
    else:
        state_field = f"{params[p.STATE_ID]}"

    LOGGER.debug(
        "Set state '%s' -> %s",
        state_field,
        val,
    )
    u.set_state(
        u.get_hass(listener),
        params[p.STATE_ID],
        val,
        key=params[p.STATE_ATTR],
        allow_create=params[p.ALLOW_CREATE],
    )

    event_data["success"] = success

    if success and (params[p.CSV_FILE] is not None):
        fields = []
        label = params[p.CSV_LABEL]

        fields.append(dt_util.utcnow().isoformat())
        fields.append(state_field)
        fields.append(val)
        fields.append(label)

        u.append_to_csvfile(
            fields,
            "csv",
            params[p.CSV_FILE],
            f"{state_field}={val}",
            listener=listener,
        )
        LOGGER.debug(f"ha_set_state info Written to CSV {params[p.CSV_FILE]}")

    if u.isJsonable(val):
        val = repr(val)

    # For internal use
    return success
