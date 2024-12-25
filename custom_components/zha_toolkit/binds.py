from __future__ import annotations

import logging

import zigpy.zcl.foundation as f
from zigpy import types as t
from zigpy.zdo.types import MultiAddress, ZDOCmd

from . import utils as u
from .params import INTERNAL_PARAMS as p

LOGGER = logging.getLogger(__name__)

BINDABLE_OUT_CLUSTERS = [
    0x0005,  # Scenes
    0x0006,  # OnOff
    0x0008,  # Level
    0x0102,  # Window Covering
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

    src_dev = await u.get_device(app, listener, ieee)

    # Get tries
    tries = params[p.TRIES]

    if not data:
        LOGGER.error("missing cmd_data")
        return

    group_id = u.str2int(data)
    zdo = src_dev.zdo
    src_out_cls = BINDABLE_OUT_CLUSTERS
    src_in_cls = BINDABLE_IN_CLUSTERS

    # find src ep_id
    dst_addr = MultiAddress()
    dst_addr.addrmode = t.uint8_t(1)
    dst_addr.nwk = t.uint16_t(group_id)
    u_epid = params[p.EP_ID]
    u_cluster_id = params[p.CLUSTER_ID]

    if u_cluster_id is not None:
        src_out_cls = [u_cluster_id]
        src_in_cls = [u_cluster_id]

    results: dict[int, list[dict[str, int]]] = {}
    for src_out_cluster in src_out_cls:
        src_epid = None
        for ep_id, ep in src_dev.endpoints.items():
            if u_epid is not None and ep_id != u_epid:
                # Endpoint not selected
                continue
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

        res = await u.retry_wrapper(
            zdo.request,
            ZDOCmd.Bind_req,
            src_dev.ieee,
            src_epid,
            src_out_cluster,
            dst_addr,
            tries=tries,
        )
        bind_result["result"] = res
        results[src_epid].append(bind_result)
        LOGGER.debug(
            "0x%04x/0x%02x/0x%04x(OUT): binding group 0x%04x: %s",
            src_dev.nwk,
            src_epid,
            src_out_cluster,
            group_id,
            res,
        )

    # find src ep_id
    dst_addr = MultiAddress()
    dst_addr.addrmode = t.uint8_t(1)
    dst_addr.nwk = t.uint16_t(group_id)

    for src_in_cluster in src_in_cls:
        src_epid = None
        for ep_id, ep in src_dev.endpoints.items():
            if u_epid is not None and ep_id != u_epid:
                # Endpoint not selected
                continue
            if ep_id == 0:
                continue
            if src_in_cluster in ep.in_clusters:
                src_epid = ep_id
                break
        if not src_epid:
            LOGGER.debug(
                "0x%04x: skipping %s cluster (not present)",
                src_dev.nwk,
                src_in_cluster,
            )
            continue
        if src_epid not in results:
            results[src_epid] = []
        LOGGER.debug(
            "0x%04x: binding %s, ep: %s, cluster: %s(IN)",
            src_dev.nwk,
            str(src_dev.ieee),
            src_epid,
            src_in_cluster,
        )
        bind_result = {"endpoint_id": src_epid, "cluster_id": src_in_cluster}

        res = await u.retry_wrapper(
            zdo.request,
            ZDOCmd.Bind_req,
            src_dev.ieee,
            src_epid,
            src_in_cluster,
            dst_addr,
            tries=tries,
        )
        bind_result["result"] = res
        results[src_epid].append(bind_result)
        LOGGER.debug(
            "0x%04x/0x%02x/0x%04x(IN): binding group 0x%04x: %s",
            src_dev.nwk,
            src_epid,
            src_in_cluster,
            group_id,
            res,
        )
    event_data["result"] = results


async def unbind_group(
    app, listener, ieee, cmd, data, service, params, event_data
):
    LOGGER.debug("running 'unbind group' command: %s", service)
    if ieee is None:
        LOGGER.error("missing ieee")
        return
    if not data:
        LOGGER.error("missing data (destination ieee)")
        return

    src_dev = await u.get_device(app, listener, ieee)

    group_id = u.str2int(data)

    # Get tries
    tries = params[p.TRIES]

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
        res = await u.retry_wrapper(
            zdo.request,
            ZDOCmd.Unbind_req,
            src_dev.ieee,
            src_ep,
            src_out_cluster,
            dst_addr,
            tries=tries,
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
    if ieee is None:
        raise ValueError("'ieee' required")

    src_dev = await u.get_device(app, listener, ieee)
    if data in [0, False, "0", None]:
        # when command_data is set to 0 or false, bind to coordinator
        data = app.ieee

    dst_dev = await u.get_device(app, listener, data)

    # Get tries
    tries = params[p.TRIES]

    # Coordinator has nwk address 0
    isCoordinatorTarget = dst_dev.nwk == 0x0000

    zdo = src_dev.zdo
    src_out_clusters = BINDABLE_OUT_CLUSTERS
    src_in_clusters = BINDABLE_IN_CLUSTERS

    u_epid = params[p.EP_ID]
    u_dst_epid = params[p.DST_EP_ID]

    u_cluster_id = params[p.CLUSTER_ID]
    if u_cluster_id is not None:
        src_out_clusters = [u_cluster_id]
        src_in_clusters = [u_cluster_id]

    # TODO: Filter according to params[p.CLUSTER_ID]

    results: dict[int, dict] = {}

    for src_out_cluster in src_out_clusters:
        src_endpoints = [
            ep_id
            for ep_id, ep in src_dev.endpoints.items()
            if ep_id != 0
            and src_out_cluster in ep.out_clusters
            and (u_epid is None or u_epid == ep_id)
        ]
        LOGGER.debug(
            "0x%04X: got endpoints %s for out-cluster 0x%04X",
            src_dev.nwk,
            src_endpoints,
            src_out_cluster,
        )

        if not src_endpoints:
            LOGGER.debug(
                "0x%04X: skipping out-cluster 0x%04X as non present",
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
            if (
                isCoordinatorTarget or (src_out_cluster in ep.in_clusters)
            ) and (u_dst_epid is None or u_dst_epid == ep_id):
                dst_epid = ep_id
                break
        if not dst_epid:
            continue
        dst_addr.endpoint = t.uint8_t(dst_epid)

        for src_ep in src_endpoints:
            LOGGER.debug(
                "0x%04x: binding %s/EP:%s, out-cluster 0x%04X to %s/EP:%s"
                " (%r)",
                src_dev.nwk,
                str(src_dev.ieee),
                src_ep,
                src_out_cluster,
                str(dst_dev.ieee),
                dst_epid,
                dst_addr,
            )
            res = await u.retry_wrapper(
                zdo.request,
                ZDOCmd.Bind_req,
                src_dev.ieee,
                src_ep,
                src_out_cluster,
                dst_addr,
                tries=tries,
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
            if ep_id != 0
            and src_in_cluster in ep.in_clusters
            and (u_epid is None or u_epid == ep_id)
        ]
        LOGGER.debug(
            "0x%04X: got endpoints %s for in cluster 0x%04X",
            src_dev.nwk,
            src_endpoints,
            src_in_cluster,
        )

        if not src_endpoints:
            LOGGER.debug(
                "0x%04X: skipping in-cluster 0x%04X as non present",
                src_dev.nwk,
                src_in_cluster,
            )
            continue
        dst_addr = MultiAddress()
        dst_addr.addrmode = t.uint8_t(3)
        dst_addr.ieee = dst_dev.ieee

        # Find dest ep, accept first EP if coordinator
        dst_epid = None
        for ep_id, ep in dst_dev.endpoints.items():
            if ep_id == 0:
                continue
            if (
                isCoordinatorTarget
                or (src_in_cluster in ep.out_clusters)
                and (u_dst_epid is None or u_dst_epid == ep_id)
            ):
                dst_epid = ep_id
                break
        if not dst_epid:
            continue
        dst_addr.endpoint = t.uint8_t(dst_epid)

        for src_ep in src_endpoints:
            LOGGER.debug(
                "0x%04X: binding %s/EP:%s, in-cluster: 0x%04X to %s/EP:%s"
                " (%r)",
                src_dev.nwk,
                str(src_dev.ieee),
                src_ep,
                src_in_cluster,
                str(dst_dev.ieee),
                dst_epid,
                dst_addr,
            )
            if src_ep not in results:
                results[src_ep] = {}

            bind_result = {
                "src_endpoint_id": src_ep,
                "dst_endpoint_id": dst_epid,
                "cluster_id": src_in_cluster,
            }
            res = await u.retry_wrapper(
                zdo.request,
                ZDOCmd.Bind_req,
                src_dev.ieee,
                src_ep,
                src_in_cluster,
                dst_addr,
                tries=tries,
            )
            bind_result["result"] = res
            results[src_ep] = bind_result
            LOGGER.debug(
                "0x%04X: binding ieee %s: %s",
                src_dev.nwk,
                str(dst_dev.ieee),
                res,
            )

    event_data["result"] = results
    event_data["success"] = len(results) != 0


async def unbind_coordinator(
    app, listener, ieee, cmd, data, service, params, event_data
):
    # Unbind bindings towards the coordinator:
    data = app.ieee

    # Use binds_remove_all with parameters
    await binds_remove_all(
        app, listener, ieee, cmd, data, service, params, event_data
    )


async def binds_remove_all(
    app, listener, ieee, cmd, data, service, params, event_data
):
    if ieee is None:
        LOGGER.error("missing ieee")
        return
    src_dev = await u.get_device(app, listener, ieee)
    zdo = src_dev.zdo

    # Get target ieee filter
    tgt_ieee = None
    if data is not None and data != "":
        try:
            tgt_ieee = t.EUI64.convert(data)
            # Get destination device if set
        except (ValueError, AttributeError):
            pass

        if tgt_ieee is None:
            # Conversion did not succeed, try other method
            # If this fails, then we do not catch the exception
            # as the field is not ok.
            tgt_ieee = (await u.get_device(app, listener, data)).ieee

    # Determine endpoints to unbind
    endpoints = []

    u_endpoint_id = params[p.EP_ID]
    if u_endpoint_id is not None and u_endpoint_id != "":
        if not isinstance(u_endpoint_id, list):
            u_endpoint_id = [u_endpoint_id]

        # unbind user provided endpoints instead
        endpoints = u_endpoint_id

    # Determine clusters to unbind
    clusters = []

    u_cluster_id = params[p.CLUSTER_ID]
    if u_cluster_id is not None and u_cluster_id != "":
        if not isinstance(u_cluster_id, list):
            u_cluster_id = [u_cluster_id]

        # unbind user provided clusters instead
        clusters = u_cluster_id

    await binds_get(
        app, listener, ieee, cmd, data, service, params, event_data
    )
    # Bindings in event_data["result"]

    errors: list[str] = []
    bindings_removed = []
    bindings_skipped = []
    try:
        for _i, binding in event_data["result"].items():
            LOGGER.debug(f"Remove bind {binding!r}")
            addr_mode = binding["dst"]["addrmode"]

            res = None
            # Note, the code below is essentially two times the same
            #       but the goal is to make a distincion between group
            #       and ieee addressing for testing/evolutions.
            if addr_mode == 1:
                # group
                src_ieee = t.EUI64.convert(binding["src"])
                ep_id = u.str2int(binding["src_ep"])
                cluster_id = u.str2int(binding["cluster_id"])

                dst_addr = MultiAddress()
                dst_addr.addrmode = addr_mode
                dst_addr.nwk = t.uint16_t(u.str2int(binding["dst"]["group"]))
                if "dst_ieee" in binding["dst"]:
                    # Probably not useful, but for backward "compatibility"
                    dst_ieee = t.EUI64.convert(binding["dst"]["dst_ieee"])
                    dst_addr.ieee = dst_ieee

                match_filter = (
                    (tgt_ieee is None or dst_ieee == tgt_ieee)
                    and (len(endpoints) == 0 or ep_id in endpoints)
                    and (len(clusters) == 0 or cluster_id in clusters)
                )

                if match_filter:
                    res = await u.retry_wrapper(
                        zdo.request,
                        ZDOCmd.Unbind_req,
                        src_ieee,
                        ep_id,
                        cluster_id,
                        dst_addr,
                        tries=params[p.TRIES],
                    )
                    # TODO: check success status
                    bindings_removed.append(binding)
                    event_data["replies"].append(res)
            elif addr_mode == 3:
                # direct
                src_ieee = t.EUI64.convert(binding["src"])
                dst_ieee = t.EUI64.convert(binding["dst"]["dst_ieee"])
                dst_addr = MultiAddress()
                dst_addr.addrmode = addr_mode
                dst_addr.ieee = dst_ieee
                dst_addr.endpoint = t.uint8_t(binding["dst"]["dst_ep"])
                ep_id = u.str2int(binding["src_ep"])
                cluster_id = u.str2int(binding["cluster_id"])
                # LOGGER.debug(
                #     f"filter {tgt_ieee} {dst_ieee} {clusters} {cluster_id}"
                # )

                match_filter = (
                    (tgt_ieee is None or dst_ieee == tgt_ieee)
                    and (len(endpoints) == 0 or ep_id in endpoints)
                    and (len(clusters) == 0 or cluster_id in clusters)
                )

                if match_filter:
                    res = await u.retry_wrapper(
                        zdo.request,
                        ZDOCmd.Unbind_req,
                        src_ieee,
                        ep_id,
                        cluster_id,
                        dst_addr,
                        tries=params[p.TRIES],
                    )
                    # TODO: check success status
                    bindings_removed.append(binding)
                    event_data["replies"].append(res)

            if res is None:
                msg = f"Binding not supported or not selected: {binding!r}"
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
    src_dev = await u.get_device(app, listener, ieee)
    zdo = src_dev.zdo

    # Get tries
    tries = params[p.TRIES]

    idx = 0
    done = False

    event_data["replies"] = []
    bindings = {}
    success = False

    while not done:
        # Todo: continue when reply is incomplete (update start index)
        reply = await u.retry_wrapper(
            zdo.request, ZDOCmd.Mgmt_Bind_req, idx, tries=tries
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
                        "group": f"0x{binding.DstAddress.nwk:04X}",
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

            if next_idx >= total:
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

    LOGGER.debug("Bindings for ieee {ieee!r}: %s", bindings)
