import logging

LOGGER = logging.getLogger(__name__)


async def bind_group(src_dev, group_id):
    from zigpy.zdo.types import MultiAddress
    from zigpy import types as t

    zdo = src_dev.zdo
    src_cls = [6, 8, 768]

    # find src ep_id
    dst_addr = MultiAddress()
    dst_addr.addrmode = t.uint8_t(1)
    dst_addr.nwk = t.uint16_t(group_id)
    for src_cluster in src_cls:
        src_epid = None
        for ep_id, ep in src_dev.endpoints.items():
            if ep_id == 0:
                continue
            if src_cluster in ep.out_clusters:
                src_epid = ep_id
                break
        if not src_epid:
            LOGGER.debug("0x%04x: skipping %s cluster as non present",
                         src_dev.nwk, src_cluster)
            continue
        LOGGER.debug("0x%04x: binding %s, ep: %s, cluster: %s",
                     src_dev.nwk, str(src_dev.ieee), src_epid, src_cluster)
        res = await zdo.request(0x0021, src_dev.ieee, src_epid, src_cluster,
                                dst_addr)
        LOGGER.debug("0x%04x: binding group 0x%04x: %s",
                     src_dev.nwk, group_id, res)


async def unbind_group(src_dev, group_id):
    from zigpy.zdo.types import MultiAddress
    from zigpy import types as t

    zdo = src_dev.zdo
    src_cls = [6, 8, 768]

    dst_addr = MultiAddress()
    dst_addr.addrmode = t.uint8_t(1)
    dst_addr.nwk = t.uint16_t(group_id)
    for src_cluster in src_cls:
        src_ep = None
        for ep_id, ep in src_dev.endpoints.items():
            if ep_id == 0:
                continue
            if src_cluster in ep.out_clusters:
                src_ep = ep_id
                break
        if not src_ep:
            LOGGER.debug("0x%04x: skipping %s cluster as non present",
                         src_dev.nwk, src_cluster)
            continue
        LOGGER.debug("0x%04x: unbinding %s, ep: %s, cluster: %s",
                     src_dev.nwk, str(src_dev.ieee), src_ep, src_cluster)
        res = await zdo.request(0x0022, src_dev.ieee, src_ep, src_cluster,
                                dst_addr)
        LOGGER.debug("0x%04x: unbinding group 0x%04x: %s",
                     src_dev.nwk, group_id, res)


async def bind_ieee(src_dev, dst_dev):
    from zigpy import types as t
    from zigpy.zdo.types import MultiAddress

    zdo = src_dev.zdo
    src_clusters = [6, 8, 768]

    for src_cluster in src_clusters:
        src_endpoints = [
            ep_id for ep_id, ep in src_dev.endpoints.items()
            if ep_id != 0 and src_cluster in ep.out_clusters
        ]
        LOGGER.debug("0x%04x: got the %s endpoints for %s cluster",
                     src_dev.nwk, src_endpoints, src_cluster)

        if not src_endpoints:
            LOGGER.debug("0x%04x: skipping %s cluster as non present",
                         src_dev.nwk, src_cluster)
            continue
        dst_addr = MultiAddress()
        dst_addr.addrmode = t.uint8_t(3)
        dst_addr.ieee = dst_dev.ieee

        # find dest ep
        dst_epid = None
        for ep_id, ep in dst_dev.endpoints.items():
            if ep_id == 0:
                continue
            if src_cluster in ep.in_clusters:
                dst_epid = ep_id
                break
        if not dst_epid:
            continue
        dst_addr.endpoint = t.uint8_t(dst_epid)

        for src_ep in src_endpoints:
            LOGGER.debug(
                "0x%04x: binding %s, ep: %s, cluster: %s to %s dev %s ep",
                src_dev.nwk, str(src_dev.ieee), src_ep, src_cluster,
                str(dst_dev.ieee), dst_epid)
            res = await zdo.request(0x0021, src_dev.ieee, src_ep, src_cluster,
                                    dst_addr)
            LOGGER.debug("0x%04x: binding ieee %s: %s",
                         src_dev.nwk, str(dst_dev.ieee), res)

