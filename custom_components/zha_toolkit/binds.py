from __future__ import annotations

import logging

import zigpy.zcl.foundation as f
from zigpy import types as t
from zigpy.zdo.types import MultiAddress, ZDOCmd

from . import utils as u
from .params import INTERNAL_PARAMS as p

LOGGER = logging.getLogger(__name__)

BINDABLE_OUT_CLUSTERS = [
    0x0006,  # OnOff
    0x0008,  # Level
    0x0300,  # Color Control
]
BINDABLE_IN_CLUSTERS = [
    0x0402,  # Temperature
]


async def bind_group(
    app, listener, ieee, cmd, data, service, params, event_data
):

    LOGGER.debug("running 'bind group' command: %s", service)
    if ieee is None:
        LOGGER.error("missing ieee")
        return

    src_dev = app.get_device(ieee=ieee)

    if not data:
        LOGGER.error("missing cmd_data")
        return

    group_id = u.str2int(data)
    zdo = src_dev.zdo
    src_out_cls = BINDABLE_OUT_CLUSTERS

    # find src ep_id
    dst_addr = MultiAddress()
    dst_addr.addrmode = t.uint8_t(1)
    dst_addr.nwk = t.uint16_t(group_id)
    results: dict[int, list[dict[str, int]]] = {}
    for src_out_cluster in src_out_cls:
        src_epid = None
        for ep_id, ep in src_dev.endpoints.items():
            if ep_id == 0:
                continue
            if src_out_cluster in ep.out_clusters:
                src_epid = ep_id
                break
        if not src_epid:
            LOGGER.debug(
                "0x%04x: skipping %s cluster as non present",
                src_dev.nwk,
                src_out_cluster,
            )
            continue
        if src_epid not in results:
            results[src_epid] = []
        LOGGER.debug(
            "0x%04x: binding %s, ep: %s, cluster: %s",
            src_dev.nwk,
            str(src_dev.ieee),
            src_epid,
            src_out_cluster,
        )
        bind_result = {"endpoint_id": src_epid, "cluster_id": src_out_cluster}

        res = await zdo.request(
            ZDOCmd.Bind_req, src_dev.ieee, src_epid, src_out_cluster, dst_addr
        )
        bind_result["result"] = res
        results[src_epid].append(bind_result)
        LOGGER.debug(
            "0x%04x: binding group 0x%04x: %s", src_dev.nwk, group_id, res
        )

    event_data["result"] = results


async def unbind_group(
    app, listener, ieee, cmd, data, service, params, event_data
):
    from zigpy.zdo.types import MultiAddress

    LOGGER.debug("running 'unbind group' command: %s", service)
    if ieee is None:
        LOGGER.error("missing ieee")
        return
    if not data:
        LOGGER.error("missing data (destination ieee)")
        return

    src_dev = app.get_device(ieee=ieee)

    group_id = u.str2int(data)

    zdo = src_dev.zdo
    src_out_cls = BINDABLE_OUT_CLUSTERS

    dst_addr = MultiAddress()
    dst_addr.addrmode = t.uint8_t(1)
    dst_addr.nwk = t.uint16_t(group_id)
    results: dict[int, list[dict[str, int]]] = {}
    for src_out_cluster in src_out_cls:
        src_ep = None
        for ep_id, ep in src_dev.endpoints.items():
            if ep_id == 0:
                continue
            if src_out_cluster in ep.out_clusters:
                src_ep = ep_id
                break
        if not src_ep:
            LOGGER.debug(
                "0x%04x: skipping %s cluster as non present",
                src_dev.nwk,
                src_out_cluster,
            )
            continue

        if src_ep not in results:
            results[src_ep] = []

        LOGGER.debug(
            "0x%04x: unbinding %s, ep: %s, cluster: %s",
            src_dev.nwk,
            str(src_dev.ieee),
            src_ep,
            src_out_cluster,
        )

        unbind_result = {"endpoint_id": src_ep, "cluster_id": src_out_cluster}
        res = await zdo.request(
            ZDOCmd.Unbind_req, src_dev.ieee, src_ep, src_out_cluster, dst_addr
        )
        unbind_result["result"] = res
        results[src_ep].append(unbind_result)
        LOGGER.debug(
            "0x%04x: unbinding group 0x%04x: %s", src_dev.nwk, group_id, res
        )

    event_data["result"] = results


async def bind_ieee(
    app, listener, ieee, cmd, data, service, params, event_data
):
    from zigpy.zdo.types import MultiAddress

    if ieee is None or not data:
        LOGGER.error("missing ieee")
        return
    LOGGER.debug("running 'bind ieee' command: %s", service)
    src_dev = app.get_device(ieee=ieee)

    dst_dev = await u.get_device(app, listener, data)

    zdo = src_dev.zdo
    src_out_clusters = BINDABLE_OUT_CLUSTERS
    src_in_clusters = BINDABLE_IN_CLUSTERS

    # TODO: Filter according to params[p.CLUSTER_ID]

    results: dict[int, dict] = {}

    for src_out_cluster in src_out_clusters:
        src_endpoints = [
            ep_id
            for ep_id, ep in src_dev.endpoints.items()
            if ep_id != 0 and src_out_cluster in ep.out_clusters
        ]
        LOGGER.debug(
            "0x%04x: got the %s endpoints for %s cluster",
            src_dev.nwk,
            src_endpoints,
            src_out_cluster,
        )

        if not src_endpoints:
            LOGGER.debug(
                "0x%04x: skipping %0x04X cluster as non present",
                src_dev.nwk,
                src_out_cluster,
            )
            continue
        dst_addr = MultiAddress()
        dst_addr.addrmode = t.uint8_t(3)
        dst_addr.ieee = dst_dev.ieee

        # find dest ep
        dst_epid = None
        for ep_id, ep in dst_dev.endpoints.items():
            if ep_id == 0:
                continue
            if src_out_cluster in ep.in_clusters:
                dst_epid = ep_id
                break
        if not dst_epid:
            continue
        dst_addr.endpoint = t.uint8_t(dst_epid)

        for src_ep in src_endpoints:
            LOGGER.debug(
                "0x%04x: binding %s, ep: %s, cluster: 0x%04X to %s dev %s ep",
                src_dev.nwk,
                str(src_dev.ieee),
                src_ep,
                src_out_cluster,
                str(dst_dev.ieee),
                dst_epid,
            )
            res = await zdo.request(
                ZDOCmd.Bind_req,
                src_dev.ieee,
                src_ep,
                src_out_cluster,
                dst_addr,
            )
            LOGGER.debug(
                "0x%04x: binding ieee %s: %s",
                src_dev.nwk,
                str(dst_dev.ieee),
                res,
            )

    for src_in_cluster in src_in_clusters:
        src_endpoints = [
            ep_id
            for ep_id, ep in src_dev.endpoints.items()
            if ep_id != 0 and src_in_cluster in ep.in_clusters
        ]
        LOGGER.debug(
            "0x%04x: got the %s endpoints for %s cluster",
            src_dev.nwk,
            src_endpoints,
            src_in_cluster,
        )

        if not src_endpoints:
            LOGGER.debug(
                "0x%04x: skipping %0x04X cluster as non present",
                src_dev.nwk,
                src_in_cluster,
            )
            continue
        dst_addr = MultiAddress()
        dst_addr.addrmode = t.uint8_t(3)
        dst_addr.ieee = dst_dev.ieee

        # find dest ep
        dst_epid = None
        for ep_id, ep in dst_dev.endpoints.items():
            if ep_id == 0:
                continue
            if src_in_cluster in ep.out_clusters:
                dst_epid = ep_id
                break
        if not dst_epid:
            continue
        dst_addr.endpoint = t.uint8_t(dst_epid)

        for src_ep in src_endpoints:
            LOGGER.debug(
                "0x%04x: binding %s, ep: %s, cluster: 0x%04X to %s dev %s ep",
                src_dev.nwk,
                str(src_dev.ieee),
                src_ep,
                src_in_cluster,
                str(dst_dev.ieee),
                dst_epid,
            )
            if src_ep not in results:
                results[src_ep] = {}

            bind_result = {
                "src_endpoint_id": src_ep,
                "dst_endpoint_id": dst_epid,
                "cluster_id": src_in_cluster,
            }
            res = await zdo.request(
                ZDOCmd.Bind_req, src_dev.ieee, src_ep, src_in_cluster, dst_addr
            )
            bind_result["result"] = res
            results[src_ep] = bind_result
            LOGGER.debug(
                "0x%04x: binding ieee %s: %s",
                src_dev.nwk,
                str(dst_dev.ieee),
                res,
            )

    event_data["result"] = results


async def unbind_coordinator(
    app, listener, ieee, cmd, data, service, params, event_data
):

    LOGGER.debug("running 'unbind coordinator' command: %s", service)
    if ieee is None or not data:
        LOGGER.error("missing ieee and/or data")
        return
    src_dev = app.get_device(ieee=ieee)
    cluster_id = params[p.CLUSTER_ID]

    for ep_id, ep in src_dev.endpoints.items():
        if not ep_id:
            continue

        out_cluster = None
        in_cluster = None

        if cluster_id not in ep.out_clusters:
            out_cluster = ep.out_clusters[ep_id]
        if cluster_id not in ep.in_clusters:
            in_cluster = ep.in_clusters[ep_id]

        cluster = None
        if in_cluster is not None and cluster_id in BINDABLE_IN_CLUSTERS:
            # Prefer in cluster
            cluster = in_cluster
        elif out_cluster is not None and cluster_id in BINDABLE_OUT_CLUSTERS:
            cluster = out_cluster

        if cluster is None:
            cluster = out_cluster
        if cluster is None:
            cluster = in_cluster

        if cluster is None:
            continue

        LOGGER.debug(
            "0x%04x: unbinding ep: %s, cluster: %s",
            src_dev.nwk,
            ep_id,
            cluster_id,
        )
        res = await ep.out_clusters[cluster_id].unbind()
        LOGGER.debug(
            "0x%04x: unbinding 0x%04x: %s", src_dev.nwk, cluster_id, res
        )


async def binds_remove_all(
    app, listener, ieee, cmd, data, service, params, event_data
):
    if ieee is None:
        LOGGER.error("missing ieee")
        return
    src_dev = app.get_device(ieee=ieee)
    zdo = src_dev.zdo

    await binds_get(
        app, listener, ieee, cmd, data, service, params, event_data
    )
    # Bindings in event_data["result"]

    errors: list[str] = []
    bindings_removed = []
    bindings_skipped = []
    try:
        for binding in event_data["result"]:
            if binding.addrmode == 1:
                # group
                src_ieee = t.EUI64.convert(binding.src)
                dst_addr = MultiAddress()
                dst_addr.addrmode = binding.addr_mode
                dst_addr.nwk = t.uint16_t(binding.dst.group)
                dst_addr.endpoint = t.uint8_t(binding.dst.dst_ep)
                res = await zdo.request(
                    ZDOCmd.Unbind_req,
                    src_ieee,
                    binding.src_ep,
                    u.str2int(binding.cluster_id),
                    dst_addr,
                )
                # TODO: check success status
                bindings_removed.append(binding)
                event_data["replies"].append(res)
            elif binding.addrmode == 3:
                # direct
                src_ieee = t.EUI64.convert(binding.src)
                dst_ieee = t.EUI64.convert(binding.dst.dst_ieee)
                dst_addr = MultiAddress()
                dst_addr.addrmode = binding.addr_mode
                dst_addr.ieee = dst_ieee
                dst_addr.endpoint = t.uint8_t(binding.dst.dst_ep)
                res = await zdo.request(
                    ZDOCmd.Unbind_req,
                    src_ieee,
                    binding.src_ep,
                    u.str2int(binding.cluster_id),
                    dst_addr,
                )
                # TODO: check success status
                bindings_removed.append(binding)
                event_data["replies"].append(res)
            else:
                msg = f"Binding not supported {binding!r}"
                bindings_skipped.append(binding)
                LOGGER.error(msg)
                errors.append(msg)
    except Exception as e:
        event_data["result"] = {
            "removed": bindings_removed,
            "skipped": bindings_skipped,
        }
        raise e

    event_data["result"] = {
        "removed": bindings_removed,
        "skipped": bindings_skipped,
    }
    event_data["success"] = len(bindings_skipped) == 0


async def binds_get(
    app, listener, ieee, cmd, data, service, params, event_data
):
    """
    Get bindings from device.
    """

    if ieee is None:
        LOGGER.error("missing ieee")
        return
    src_dev = app.get_device(ieee=ieee)
    zdo = src_dev.zdo

    idx = 0
    done = False

    event_data["replies"] = []
    bindings = {}
    success = False

    while not done:
        # Todo: continue when reply is incomplete (update start index)
        reply = await zdo.request(
            ZDOCmd.Mgmt_Bind_req, idx, tries=params[p.TRIES]
        )
        event_data["replies"].append(reply)

        if (
            isinstance(reply, list)
            and len(reply) >= 3
            and reply[0] == f.Status.SUCCESS
        ):
            total = reply[1]
            next_idx = reply[2]
            for binding in reply[3]:
                if binding.DstAddress.addrmode == 1:
                    dst_info = {
                        "addrmode": binding.DstAddress.addrmode,
                        "group": f"0x{binding.DstAddress.nwk}",
                    }
                elif binding.DstAddress.addrmode == 3:
                    dst_info = {
                        "addrmode": binding.DstAddress.addrmode,
                        "dst_ieee": repr(binding.DstAddress.ieee),
                        "dst_ep": binding.DstAddress.endpoint,
                    }
                else:
                    dst_info = binding.DstAddress

                bind_info = {
                    "src": repr(binding.SrcAddress),
                    "src_ep": binding.SrcEndpoint,
                    "cluster_id": f"0x{binding.ClusterId:04X}",
                    "dst": dst_info,
                }
                bindings[next_idx] = bind_info
                next_idx += 1

            if next_idx + 1 >= total:
                done = True
                success = True
            else:
                if idx >= next_idx:
                    # Not progressing in list
                    success = False
                    done = True
                else:
                    # Continue with next offset
                    idx = next_idx
        else:
            event_data["warning"] = "Unexpected reply format or failure"
            done = True

    event_data["success"] = success
    event_data["result"] = bindings

    LOGGER.debug("0x%04x: bindings ieee {ieee!r}: %s", bindings)
