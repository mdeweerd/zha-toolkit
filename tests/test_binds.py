"""Regression tests for binds_remove_all / unbind_coordinator.

Covers issue #352: unbind_coordinator could remove group bindings or
raise UnboundLocalError depending on the binding table order.
"""

import asyncio
from unittest import mock

from zigpy import types as t

from custom_components.zha_toolkit import binds
from custom_components.zha_toolkit.params import INTERNAL_PARAMS as p

DEVICE_IEEE = "aa:bb:cc:dd:ee:ff:00:11"
COORDINATOR_IEEE = "00:11:22:33:44:55:66:77"
OTHER_IEEE = "00:11:22:33:44:55:66:99"


def _ieee_binding(dst_ieee, cluster_id=0x0006, src_ep=1, dst_ep=1):
    return {
        "src": DEVICE_IEEE,
        "src_ep": src_ep,
        "cluster_id": f"0x{cluster_id:04X}",
        "dst": {
            "addrmode": 3,
            "dst_ieee": repr(t.EUI64.convert(dst_ieee)),
            "dst_ep": dst_ep,
        },
    }


def _group_binding(cluster_id=0x0000, group=0x0002, src_ep=1):
    return {
        "src": DEVICE_IEEE,
        "src_ep": src_ep,
        "cluster_id": f"0x{cluster_id:04X}",
        "dst": {
            "addrmode": 1,
            "group": f"0x{group:04X}",
        },
    }


class _UnbindRecorder:  # pylint: disable=too-few-public-methods
    """Replacement for u.retry_wrapper recording Unbind_req calls."""

    def __init__(self):
        self.calls = []

    async def __call__(self, func, *args, **kwargs):
        self.calls.append(args)
        # Non-None reply: the binding counts as removed, not skipped
        return [0]


def _run(func, bindings, data="", extra_params=None):
    """Run a binds command with the device/zdo layer mocked out."""
    recorder = _UnbindRecorder()
    event_data: dict = {}
    src_dev = mock.Mock()
    src_dev.zdo = mock.Mock()

    async def fake_get_device(app, listener, ieee):
        return src_dev

    async def fake_binds_get(
        app, listener, ieee, cmd, data, service, params, event_data
    ):
        event_data["replies"] = []
        event_data["result"] = dict(enumerate(bindings))

    params = {p.EP_ID: None, p.CLUSTER_ID: None, p.TRIES: 1}
    params.update(extra_params or {})

    with (
        mock.patch.object(binds.u, "get_device", fake_get_device),
        mock.patch.object(binds, "binds_get", fake_binds_get),
        mock.patch.object(binds.u, "retry_wrapper", recorder),
    ):
        asyncio.run(
            func(
                mock.Mock(),
                None,
                DEVICE_IEEE,
                "test",
                data,
                None,
                params,
                event_data,
            )
        )
    return event_data, recorder


def test_group_binding_first_is_preserved():
    """Group binding processed before any IEEE binding (issue #352).

    Previously raised UnboundLocalError because dst_ieee was unassigned.
    """
    bindings = [
        _group_binding(),
        _ieee_binding(COORDINATOR_IEEE),
    ]
    event_data, recorder = _run(
        binds.binds_remove_all, bindings, data=COORDINATOR_IEEE
    )
    assert event_data["result"]["removed"] == [bindings[1]]
    assert event_data["result"]["skipped"] == []
    assert event_data["result"]["ignored"] == [bindings[0]]
    assert event_data["success"] is True
    assert len(recorder.calls) == 1


def test_group_binding_after_ieee_binding_is_preserved():
    """IEEE binding processed first must not leak dst_ieee (issue #352).

    Previously the stale dst_ieee matched the coordinator filter and the
    group binding was removed as well.
    """
    bindings = [
        _ieee_binding(COORDINATOR_IEEE),
        _group_binding(),
    ]
    event_data, recorder = _run(
        binds.binds_remove_all, bindings, data=COORDINATOR_IEEE
    )
    assert event_data["result"]["removed"] == [bindings[0]]
    assert event_data["result"]["skipped"] == []
    assert event_data["result"]["ignored"] == [bindings[1]]
    assert event_data["success"] is True
    assert len(recorder.calls) == 1


def test_cluster_filter_keeps_group_binding():
    """Explicit cluster filter must not fail or remove group bindings."""
    bindings = [
        _group_binding(cluster_id=0x0005),
        _ieee_binding(COORDINATOR_IEEE, cluster_id=0x0005),
        _ieee_binding(OTHER_IEEE, cluster_id=0x0005),
    ]
    event_data, recorder = _run(
        binds.binds_remove_all,
        bindings,
        data=COORDINATOR_IEEE,
        extra_params={p.CLUSTER_ID: [0x0005]},
    )
    assert event_data["result"]["removed"] == [bindings[1]]
    assert event_data["result"]["skipped"] == []
    assert event_data["result"]["ignored"] == [bindings[0], bindings[2]]
    assert event_data["success"] is True
    assert len(recorder.calls) == 1


def test_unbind_coordinator_preserves_group_bindings():
    """unbind_coordinator only removes coordinator IEEE bindings."""
    bindings = [
        _group_binding(),
        _ieee_binding(COORDINATOR_IEEE),
    ]
    with mock.patch.object(
        binds.u, "get_coordinator_ieee", lambda app: COORDINATOR_IEEE
    ):
        event_data, recorder = _run(binds.unbind_coordinator, bindings)
    assert event_data["result"]["removed"] == [bindings[1]]
    assert event_data["result"]["skipped"] == []
    assert event_data["result"]["ignored"] == [bindings[0]]
    assert event_data["success"] is True
    assert len(recorder.calls) == 1


def test_remove_all_without_target_removes_group_bindings():
    """Without a target IEEE, all bindings are removed (incl. groups)."""
    bindings = [
        _group_binding(),
        _ieee_binding(COORDINATOR_IEEE),
    ]
    event_data, recorder = _run(binds.binds_remove_all, bindings)
    assert event_data["result"]["removed"] == bindings
    assert event_data["result"]["skipped"] == []
    assert event_data["result"]["ignored"] == []
    assert event_data["success"] is True
    assert len(recorder.calls) == 2
    # The group binding is unbound towards its group address
    group_call = recorder.calls[0]
    assert group_call[4].addrmode == 1
    assert group_call[4].nwk == 0x0002


def test_unsupported_addrmode_is_skipped():
    """A binding with an unsupported address mode is an error, not neutral."""
    bindings = [
        {
            "src": DEVICE_IEEE,
            "src_ep": 1,
            "cluster_id": "0x0006",
            "dst": {"addrmode": 2},
        },
        _ieee_binding(COORDINATOR_IEEE),
    ]
    event_data, recorder = _run(
        binds.binds_remove_all, bindings, data=COORDINATOR_IEEE
    )
    assert event_data["result"]["removed"] == [bindings[1]]
    assert event_data["result"]["skipped"] == [bindings[0]]
    assert event_data["result"]["ignored"] == []
    assert event_data["success"] is False
    assert len(recorder.calls) == 1
