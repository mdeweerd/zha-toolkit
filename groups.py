import logging

LOGGER = logging.getLogger(__name__)


async def get_groups(app, listener, ieee, cmd, data, service):
    LOGGER.debug("running 'get_groups' command: %s", service)
    if ieee is None:
        LOGGER.error("missing ieee")
        return
    src_dev = app.get_device(ieee=ieee)

    for ep_id, ep in src_dev.endpoints.items():
        if ep_id == 0:
            continue
        try:
            name_support = await ep.groups.read_attributes(['name_support'])
            LOGGER.debug("Group on 0x%04x name support: %s", src_dev.nwk,
                         name_support)

            all_groups = await ep.groups.get_membership([])
            LOGGER.debug("Groups on 0x%04x : %s", src_dev.nwk, all_groups)
        except AttributeError:
            LOGGER.debug("0x%04x: no group cluster found", src_dev.nwk)


async def add_group(app, listener, ieee, cmd, data, service):
    LOGGER.debug("running 'add group' command: %s", service)
    if ieee is None or not data:
        return
    src_dev = app.get_device(ieee=ieee)
    group_id = int(data, base=16)

    for ep_id, ep in src_dev.endpoints.items():
        if ep_id == 0:
            continue
        try:
            res = await ep.groups.add(group_id, 'group {}'.format(group_id))
            LOGGER.debug("0x%04x: Setting group 0x%04x: %s",
                         src_dev.nwk, group_id, res)
        except AttributeError:
            LOGGER.debug("0x%04x: no group cluster found", src_dev.nwk)


async def remove_group(app, listener, ieee, cmd, data, service):
    LOGGER.debug("running 'remove group' command: %s", service)
    if ieee is None or not data:
        LOGGER.error("missing ieee")
        return
    src_dev = app.get_device(ieee=ieee)
    group_id = int(data, base=16)
    for ep_id, ep in src_dev.endpoints.items():
        if ep_id == 0:
            continue
        try:
            res = await ep.groups.remove(group_id)
            LOGGER.debug("0x%04x: Removing group 0x%04x: %s",
                         src_dev.nwk, group_id, res)
        except AttributeError:
            LOGGER.debug("0x%04x: no group cluster found", src_dev.nwk)


async def remove_all_groups(app, listener, ieee, cmd, data, service):
    LOGGER.debug("running 'remove all group' command: %s", service)
    if ieee is None:
        return
    src_dev = app.get_device(ieee=ieee)
    for ep_id, ep in src_dev.endpoints.items():
        if ep_id == 0:
            continue
        try:
            res = await ep.groups.remove_all()
            LOGGER.debug("0x%04x: Removing all groups: %s",
                         src_dev.nwk, res)
        except AttributeError:
            LOGGER.debug("0x%04x: no group cluster on endpoint #%d",
                         src_dev.nwk, ep_id)


async def add_to_group(app, listener, ieee, cmd, data, service):
    if data is None or ieee is None:
        LOGGER.error("invalid arguments for subscribe_group()")
        return

    dev = app.get_device(ieee)
    grp_id = int(data, base=16)
    LOGGER.debug("Subscribing EZSP to %s group: %s", grp_id, service)
    res = await dev.add_to_group(grp_id, 'Group {}'.format(data))
    LOGGER.info("Subscribed NCP to %s group: %s", grp_id, res)


async def remove_from_group(app, listener, ieee, cmd, data, service):
    if data is None or ieee is None:
        LOGGER.error("invalid arguments for unsubscribe_group()")
        return

    dev = app.get_device(ieee)
    grp_id = int(data, base=16)
    LOGGER.debug("Unsubscribing EZSP to %s group: %s", grp_id, service)
    res = await dev.remove_from_group(grp_id)
    LOGGER.info("Unsubscribed NCP to %s group: %s", grp_id, res)


async def get_zll_groups(app, listener, ieee, cmd, data, service):
    from zigpy.zcl.clusters.lightlink import LightLink

    if ieee is None:
        LOGGER.error("missine ieee")
        return
    LOGGER.debug("Getting ZLL groups: %s", service)
    dev = app.get_device(ieee=ieee)

    clusters = [
        ep.in_clusters[LightLink.cluster_id] for epid, ep in dev.endpoints.items()
        if epid and LightLink.cluster_id in ep.in_clusters
    ]
    zll_cluster = next(iter(clusters))
    if not zll_cluster:
        LOGGER.warning("Couldn't find ZLL Commissioning cluster on %s",
                        dev.ieee)
        return

    res = await zll_cluster.get_group_identifiers(0)
    groups = res[2]
    LOGGER.debug("Get group identifiers response: %s", [g.group_id for g in groups])
