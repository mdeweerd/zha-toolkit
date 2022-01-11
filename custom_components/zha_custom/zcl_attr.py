import logging

from zigpy import types as t
from zigpy.zcl import foundation
# import zigpy.zcl as zcl
from . import utils as u

LOGGER = logging.getLogger(__name__)


async def conf_report(app, listener, ieee, cmd, data, service):
    # Data format is endpoint, cluster_id, attr_id, min_interval,
    #                 max_interval,reportable_change,manufacturer

    # Split command_data and assign to string variables
    params = data.split(',')
    i = 0
    # addr_str=params[i] ; i+=1
     
    ep_id_str = params[i] ; i += 1
    cluster_id_str = params[i] ; i += 1
    attr_id_str = params[i] ; i += 1
    min_interval_str = params[i] ; i += 1
    max_interval_str = params[i] ; i += 1
    reportable_change_str = params[i] ; i += 1

    if i in params:
        manf = u.str2int(params[i]) ; i += 1
    else:
        manf = None

    # Decode the variables

    # Decode endpoint
    ep_id = u.str2int(ep_id_str)

    # Decode cluster id
    cluster_id = u.str2int(cluster_id_str)

    attr_id = u.str2int(attr_id_str)
    min_interval = u.str2int(min_interval_str)
    max_interval = u.str2int(max_interval_str)
    reportable_change = u.str2int(reportable_change_str)

    dev = app.get_device(ieee=ieee)

    for key, value in dev.endpoints.items():
        LOGGER.info("Endpoint %s" % (key))
        if key == 0:
            continue
        for cl, v in value.in_clusters.items():
            LOGGER.info("InCluster 0x%04X" % (cl))
        for cl, v in value.out_clusters.items():
            LOGGER.info("OutCluster 0x%04X" % (cl))
    if ep_id not in dev.endpoints:
        LOGGER.error("Endpoint %s not found for '%s'", ep_id, repr(ieee))

    if cluster_id not in dev.endpoints[ep_id].in_clusters:
        LOGGER.error("Cluster 0x%04X not found for '%s', endpoint %s",
                      cluster_id, repr(ieee), ep_id)

    cluster = dev.endpoints[ep_id].in_clusters[cluster_id]

    # await cluster.bind()   -> commented, not performing bind to coordinator
    LOGGER.info("Configure report %u, %s, %u, %u, %u",
                ep_id, attr_id, min_interval, max_interval, reportable_change)
    result = await cluster.configure_reporting(
        attr_id,
        min_interval, max_interval,
        reportable_change,
        manufacturer=manf)
    LOGGER.info("Configure report result: %s", result)


async def attr_write(app, listener, ieee, cmd, data, service):
    # Data format is endpoint,cluster_id,attr_id,attr_type,attr_value

    # Default
    manf = None

    # Split command_data and assign to string variables
    if data is not None:
      params = data.split(',')
      i = 0
      if i in params:
        ep_id_str = params[i] ; i += 1
      if i in params:
        cluster_id_str = params[i] ; i += 1
      if i in params:
        attr_id_str = params[i] ; i += 1
      if i in params:
        attr_type_str = params[i] ; i += 1
      if i in params:
        attr_val_str = params[i] ; i += 1
      if i in params:
        manf = u.str2int(params[i]) ; i += 1

    # Get more parameters from "extra"
    # extra = service.data.get('extra')
    # Take extra parameters from "data" level
    extra=service.data  #.get('extra')
    LOGGER.info( "Extra '%s'", type(extra) )
    if "endpoint" in extra:
        ep_id_str = extra["endpoint"]
    if "cluster_id" in extra:
        cluster_id_str = extra["cluster_id"]
    if "attr_id" in extra:
        attr_id_str = extra["attr_id"]
    if "attr_type" in extra:
        attr_type_str = extra["attr_type"]
    if "attr_val" in extra:
        attr_val_str = extra["attr_val"]
    if "manf" in extra:
        manf = u.str2int(extra["manf"])


    # Decode the variables

    # Decode endpoint
    ep_id = u.str2int(ep_id_str)

    # Decode cluster id
    cluster_id = u.str2int(cluster_id_str)

    dev = app.get_device(ieee=ieee)

    for key, value in dev.endpoints.items():
        print("Endpoint %s" % (key))
        if key == 0:
            continue
        for cl, v in value.in_clusters.items():
            LOGGER.info("InCluster 0x%04X" % (cl))
        for cl, v in value.out_clusters.items():
            LOGGER.info("OutCluster 0x%04X" % (cl))
    if ep_id not in dev.endpoints:
        LOGGER.error("Endpoint %s not found for '%s'", ep_id, repr(ieee))

    if cluster_id not in dev.endpoints[ep_id].in_clusters:
        LOGGER.error("Cluster 0x%04X not found for '%s', endpoint %s",
                      cluster_id, repr(ieee), ep_id)

    cluster = dev.endpoints[ep_id].in_clusters[cluster_id]

    # Prepare read and write lists
    attr_write_list = []
    attr_read_list = []

    # Decode attribute(s)
    #  Currently only one attribute is possible, but the parameter
    #  format could allow for multiple attributes for instance by
    #  adding a split character such as ':' for attr_id, attr_type
    #  and attr_value
    # Then the match should be in a loop

    # Decode attribute id
    # Could accept name for attribute, but extra code to check
    attr_id = u.str2int(attr_id_str)

    # Decode attribute type
    attr_type = u.str2int(attr_type_str)

    # Convert attribute value (provided as a string) to appropriate
    # attribute value
    # If the attr_type is not set, then the attribute will be only read.
    attr_val = None
    if attr_type == 0x10:
        attr_val = foundation.TypeValue(
            attr_type, t.Bool(u.str2int(attr_val_str)))
    elif attr_type == 0x20:
        attr_val = foundation.TypeValue(
            attr_type, t.uint8_t(u.str2int(attr_val_str)))
    elif attr_type <= 0x31 and attr_type >= 0x08:
        # uint, int, bool, bitmap and enum
        attr_val = foundation.TypeValue(
            attr_type, t.FixedIntType(u.str2int(attr_val_str)))
    elif attr_type == 0x41:  # Octet string
        # Octet string requires length -> LVBytes

        if isinstance(attr_val_str, list):
            # Convert list to List of uint8_t
            attr_val_str = t.List[t.uint8_t]([t.uint8_t(i) for i in attr_val_str])

        attr_val = foundation.TypeValue(
            attr_type, t.LVBytes(attr_val_str))

    attr_read_list.append(attr_id)  # Read before write list

    if attr_val is not None:
        attr = foundation.Attribute(attr_id, value=attr_val)
        attr_write_list.append(attr)  # Write list

    if True:
        LOGGER.info("Request attr read")
        result = await cluster.read_attributes(
            attr_read_list, manufacturer=manf)
        LOGGER.info("Reading attr status: %s", result)

    if len(attr_write_list) != 0:
        LOGGER.info("Request attr write")
        result = await cluster._write_attributes(
            attr_write_list, manufacturer=manf)
        LOGGER.info("Write attr status: %s", result)

    if True:
        LOGGER.info("Request attr read")
        result = await cluster.read_attributes(
            attr_read_list, manufacturer=manf)
        LOGGER.info("Reading attr status: %s", result)

    # Example where attributes are not types
    # (supposed typed by the internals):
    #   attrs = {0x0009: 0b00001000, 0x0012: 1400, 0x001C: 0xFF}
    #   result = await cluster.write_attributes(attrs)
