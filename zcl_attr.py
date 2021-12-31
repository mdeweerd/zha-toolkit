import logging

from zigpy import types as t
from zigpy.zcl import foundation
import zigpy.zcl as zcl

LOGGER = logging.getLogger(__name__)


def str2int(s):
    if s.startswith("0x") or s.startswith("0X"):
        return int(s, 16)
    elif s.startswith("0"):
        return int(s, 8)
    else:
        return int(s)


async def attr_write(app, listener, ieee, cmd, data, service):
    # Data format is addr,endpoint,cluster_id,attr_id,attr_type,attr_value

    # Split command_data and assign to string variables
    params = data.split(',')
    i = 0
    # addr_str=params[i] ; i+=1
    addr_str = ieee
    ep_id_str = params[i] ; i += 1
    cluster_id_str = params[i] ; i += 1
    attr_id_str = params[i] ; i += 1
    attr_type_str = params[i] ; i += 1
    attr_val_str = params[i] ; i += 1
    if i in params:
        manf = str2int(params[i]) ; i += 1
    else:
        manf = None

    # Decode the variables

    # # Decode address
    if (addr_str.count(':') == 7):
        ieee = t.EUI64.convert(addr_str)

    # # Decode endpoint
    ep_id = str2int(ep_id_str)

    # # Decode cluster id
    cluster_id = str2int(cluster_id_str)

    dev = app.get_device(ieee)

    for key, value in dev.endpoints.items():
        print("Endpoint %s" % (key))
        if key == 0:
            continue
        for cl, v in value.in_clusters.items():
            print("InCluster 0x%04X" % (cl))
        for cl, v in value.out_clusters.items():
            print("OutCluster 0x%04X" % (cl))
    if ep_id not in dev.endpoints:
        LOGGER.error("Endpoint %s not found for '%s'", ep_id, repr(ieee))

    if cluster_id not in dev.endpoints[ep_id].in_clusters:
        LOGGER.error("Cluster 0x%0x04X not found for '%s', endpoint %s", cluster_id, repr(ieee), ep_id)

    cluster = dev.endpoints[ep_id].in_clusters[cluster_id]
 
    # Prepare read and write lists
    attr_write_list = []
    attr_read_list = []

    # # Decode attribute(s)
    # #  Currently only one attribute is possible, but the parameter
    # #  format could allow for multiple attributes for instance by
    # #  adding a split character such as ':' for attr_id, attr_type and attr_value
    # # Then the match should be in a loop 

    # # Decode attribute id
    # # Could accept name for attribute, but extra code to check
    attr_id = str2int(attr_id_str)

    # # Decode attribute type
    attr_type = str2int(attr_type_str)

    # Convert attribute value (provided as a string) to appropriate attribute value
    # If the attr_type is not set, then the attribute will be only read.
    attr_val = None
    if attr_type==0x10:
        attr_val = foundation.TypeValue(attr_type, t.Bool(str2int(attr_val_str)))
    elif attr_type==0x20:
        attr_val = foundation.TypeValue(attr_type, t.uint8_t(str2int(attr_val_str)))
    elif attr_type <= 0x31 and attr_type >= 0x08:
        # uint, int, bool, bitmap and enum
        attr_val = foundation.TypeValue(attr_type, FixedIntType(str2int(attr_val_str)))
    elif attr_type == 0x41:  # Octet string
        # Not tested 
        attr_val = foundation.TypeValue(attr_type, t.LVBytes(attr_val_str))

    attr_read_list.append(attr_id)  # Read before write list
        
    if attr_val is not None:
        attr = foundation.Attribute(attr_id, value=attr_val)
        attr_write_list.append(attr)  # Write list

    if True:    
        LOGGER.info("Request attr read")
        result = await cluster.read_attributes(attr_read_list, manufacturer=manf)
        LOGGER.info("Reading attr status: %s", result)

    if len(attr_write_list)!=0:
        LOGGER.info("Request attr write")
        result = await cluster._write_attributes(attr_write_list, manufacturer=manf)
        LOGGER.info("Write attr status: %s", result)

    if True:    
        LOGGER.info("Request attr read")
        result = await cluster.read_attributes(attr_read_list, manufacturer=manf)
        LOGGER.info("Reading attr status: %s", result)

    # Example where attributes are not types (supposed typed by the internals)
    # attrs = {0x0009: 0b00001000, 0x0012: 1400, 0x001C: 0xFF}
    # result = await cluster.write_attributes(attrs)
