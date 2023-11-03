from custom_components.zha_toolkit import utils as u
from custom_components.zha_toolkit.params import INTERNAL_PARAMS as p


async def tuya_magic(
    app, listener, ieee, cmd, data, service, params, event_data
):
    """
    Send 'magic spell' sequence to device to try to get 'normal' behavior.
    """

    dev = await u.get_device(app, listener, ieee)
    basic_cluster = dev.endpoints[1].in_clusters[0]

    # The magic spell is needed only once.
    # TODO: Improve by doing this only once (successfully).

    # Magic spell - part 1
    attr_to_read = [4, 0, 1, 5, 7, 0xFFFE]
    res = await u.cluster_read_attributes(
        basic_cluster, attr_to_read, tries=params[p.TRIES]
    )

    event_data["result"] = res

    # Magic spell - part 2 (skipped - does not seem to be needed)
    # attr_to_write={0xffde:13}
    # basic_cluster.write_attributes(attr_to_write, tries=3)
