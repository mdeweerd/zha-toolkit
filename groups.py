import logging

LOGGER = logging.getLogger(__name__)


async def get_groups(src_dev):
    from zigpy.zcl.clusters.general import Groups

    grp_cluster = None
    for ep_id, ep in src_dev.endpoints.items():
        if ep_id == 0:
            continue
        if Groups.cluster_id in ep.in_clusters:
            grp_cluster = ep.in_clusters[Groups.cluster_id]
            break

    if not grp_cluster:
        LOGGER.debug("0x%04x: no group cluster found", src_dev.nwk)
        return

    name_support = await grp_cluster.read_attributes(['name_support'])
    LOGGER.debug("Group on 0x%04x name support: %s", src_dev.nwk, name_support)

    all_groups = await grp_cluster.get_membership([])
    LOGGER.debug("Groups on 0x%04x : %s", src_dev.nwk, all_groups)


async def set_group(src_dev, group_id):
    from zigpy.zcl.clusters.general import Groups

    for ep_id, ep in src_dev.endpoints.items():
        if ep_id == 0:
            continue
        if Groups.cluster_id in ep.in_clusters:
            grp_cluster = ep.in_clusters[Groups.cluster_id]
            break
    if not grp_cluster:
        LOGGER.debug("0x%04x: no group cluster found", src_dev.nwk)
        return

    res = await grp_cluster.add(group_id, [])
    LOGGER.debug("0x%04x: Setting group 0x%04x: %s", src_dev.nwk, group_id, res)

