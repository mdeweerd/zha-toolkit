"""Service-level regression tests for Zigbee handler timeouts."""

import asyncio
from unittest import mock

import voluptuous as vol

from custom_components import zha_toolkit as toolkit
from custom_components.zha_toolkit.params import INTERNAL_PARAMS as p


def _call_failing_service(error, fail_exception):
    """Run the registered service with a handler that raises *error*."""
    hass = mock.Mock()
    hass.data = {"zha": object()}
    gateway = mock.Mock()
    gateway.application_controller = mock.Mock()

    async def failing_handler(*args, **kwargs):
        raise error

    params = {
        p.EVT_SUCCESS: None,
        p.EVT_FAIL: "read_failed",
        p.EVT_DONE: "read_done",
        p.FAIL_EXCEPTION: fail_exception,
    }
    with (
        mock.patch.object(
            toolkit, "SERVICE_SCHEMAS", {toolkit.S.EXECUTE: vol.Schema({})}
        ),
        mock.patch.object(
            toolkit, "command_handler_timeout", failing_handler, create=True
        ),
        mock.patch.object(toolkit.u, "is_ha_ge", return_value=True),
        mock.patch.object(toolkit.u, "get_zha_gateway", return_value=gateway),
        mock.patch.object(
            toolkit.u, "get_zha_gateway_hass", return_value=hass
        ),
        mock.patch.object(
            toolkit.u, "get_ieee", new_callable=mock.AsyncMock
        ) as get_ieee,
        mock.patch.object(
            toolkit.u, "getVersion", new_callable=mock.AsyncMock
        ) as get_version,
        mock.patch.object(toolkit.u, "getZigpyVersion", return_value="test"),
        mock.patch.object(
            toolkit.u, "get_radio_version", new_callable=mock.AsyncMock
        ) as get_radio_version,
        mock.patch.object(toolkit.u, "extractParams", return_value=params),
        mock.patch.object(toolkit.u, "get_hass", return_value=hass),
    ):
        get_ieee.return_value = "00:11:22:33:44:55:66:77"
        get_version.return_value = "test"
        get_radio_version.return_value = "test"
        asyncio.run(toolkit.register_services(hass))
        callback = hass.services.async_register.call_args.args[2]
        service = mock.Mock()
        service.data = {
            toolkit.ATTR_IEEE: "00:11:22:33:44:55:66:77",
            toolkit.ATTR_COMMAND: "timeout",
        }
        service.service = toolkit.S.EXECUTE
        service.return_response = True

        try:
            result = asyncio.run(callback(service))
            raised = None
        except Exception as exc:  # noqa: BLE001 - inspect service contract
            result = None
            raised = exc

    events = [call.args[0] for call in hass.bus.fire.call_args_list]
    return result, raised, events


def test_timeout_without_fail_exception_returns_failed_response():
    """A radio timeout is a failed transaction, not a service exception."""
    result, raised, events = _call_failing_service(
        asyncio.TimeoutError("radio timeout"), fail_exception=False
    )

    assert raised is None
    assert result["success"] is False
    assert result["errors"] == ["TimeoutError('radio timeout')"]
    assert events == ["read_failed", "read_done"]


def test_timeout_with_fail_exception_still_raises():
    """Callers explicitly requesting an exception retain that contract."""
    result, raised, events = _call_failing_service(
        asyncio.TimeoutError("radio timeout"), fail_exception=True
    )

    assert result is None
    assert isinstance(raised, asyncio.TimeoutError)
    assert str(raised) == "radio timeout"
    assert events == ["read_failed", "read_done"]


def test_unexpected_handler_error_still_raises():
    """The nonfatal case must remain limited to transport timeouts."""
    result, raised, events = _call_failing_service(
        ValueError("invalid attribute"), fail_exception=False
    )

    assert result is None
    assert isinstance(raised, ValueError)
    assert str(raised) == "invalid attribute"
    assert events == ["read_failed", "read_done"]
