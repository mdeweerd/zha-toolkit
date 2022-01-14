import logging

from zigpy import types as t
from zigpy.zcl import foundation
# import zigpy.zcl as zcl
from . import utils as u
from homeassistant.util import dt as dt_util

LOGGER = logging.getLogger(__name__)


async def conf_report(app, listener, ieee, cmd, data, service):
    # Data format is endpoint, cluster_id, attr_id, min_interval,
    #                 max_interval,reportable_change,manufacturer

    # Default manf value
    manf = None
    ep_id_str = None

    if data is not None:
        # Split command_data and assign to string variables
        params = data.split(',')
        i = 0
        # addr_str=params[i] ; i+=1
        if i in params:
            ep_id_str = params[i] ; i += 1
        if i in params:
            cluster_id_str = params[i] ; i += 1
        if i in params:
            attr_id_str = params[i] ; i += 1
        if i in params:
            min_interval_str = params[i] ; i += 1
        if i in params:
            max_interval_str = params[i] ; i += 1
        if i in params:
            reportable_change_str = params[i] ; i += 1
        if i in params:
            manf = u.str2int(params[i]) ; i += 1

    # Get more parameters from "extra"
    # extra = service.data.get('extra')
    # Take extra parameters from "data" level
    extra=service.data  #.get('extra')
    LOGGER.info( "Extra '%s'", type(extra) )
    if "endpoint" in extra:
        ep_id_str = extra["endpoint"]
    if "cluster" in extra:
        cluster_id_str = extra["cluster"]
    if "attribute" in extra:
        attr_id_str = extra["attribute"]
    if "min_interval" in extra:
        min_interval_str = extra["min_interval"]
    if "max_interval" in extra:
        max_interval_str = extra["max_interval"]
    if "reportable_change" in extra:
        reportable_change_str = extra["reportable_change"]
    if "manf" in extra:
        manf = u.str2int(extra["manf"])

    # Decode the variables

    # Decode cluster id
    cluster_id = u.str2int(cluster_id_str)


    dev = app.get_device(ieee=ieee)

    # Decode endpoint
    if ep_id_str is None or ep_id_str == "":
        ep_id = u.find_endpoint(dev, cluster_id)
    else:
        ep_id = u.str2int(ep_id_str)


    attr_id = u.str2int(attr_id_str)
    min_interval = u.str2int(min_interval_str)
    max_interval = u.str2int(max_interval_str)
    reportable_change = u.str2int(reportable_change_str)


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


async def attr_read(app, listener, ieee, cmd, data, service):
    if 'attr_val' in service.data:
        # avoid writing when value is present
        del service.data['attr_val']
    await attr_write(app, listener, ieee, cmd, data, service)


async def attr_write(app, listener, ieee, cmd, data, service):
    # Data format is endpoint,cluster_id,attr_id,attr_type,attr_value
    event_data = { "ieee": str(ieee), "command" : cmd, "start_time": dt_util.utcnow().isoformat() }


    # Default
    manf = None
    ep_id_str = None
    attr_type_str = None

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
    if "cluster" in extra:
        cluster_id_str = extra["cluster"]
    if "attribute" in extra:
        attr_id_str = extra["attribute"]
    if "attr_type" in extra:
        attr_type_str = extra["attr_type"]
    if "attr_val" in extra:
        attr_val_str = extra["attr_val"]
    if "manf" in extra:
        manf = u.str2int(extra["manf"])

    if "state_id" in extra:
        state_id = extra["state_id"]
    else:
        state_id = None

    if "read_before_write" in extra:
        read_before_write = u.str2bool(extra["read_before_write"])==1
    else:
        read_before_write = True

    if "read_after_write" in extra:
        read_after_write = u.str2bool(extra["read_after_write"])==1
    else:
        read_after_write = True

    if "write_if_equal" in extra:
        write_if_equal = u.str2bool(extra["write_if_equal"])==1
    else:
        write_if_equal = True

    if "state_attr" in extra:
        state_attr = extra["state_attr"]
    else:
        state_attr = None

    allow_create = False
    if "allow_create" in extra:
        allow = u.str2int(extra["allow_create"])
        allow_create = ( allow is not None ) and ( (allow == True ) or (allow == 1) )

    if "event_done" in extra:
        event_done = extra["event_done"]
    else:
        event_done = None

    if "event_fail" in extra:
        event_fail = extra["event_fail"]
    else:
        event_fail = None

    if "event_success" in extra:
        event_success = extra["event_success"]
    else:
        event_success = None

    success = True

    # Decode the variables

    # Decode cluster id
    cluster_id = u.str2int(cluster_id_str)

    dev = app.get_device(ieee=ieee)

    # Decode endpoint
    if ep_id_str is None or ep_id_str == "":
        ep_id = u.find_endpoint(dev, cluster_id)
    else:
        ep_id = u.str2int(ep_id_str)



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

    attr_read_list.append(attr_id)  # Read before write list

    # Type only needed for write
    if attr_type_str is not None:
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
  
        if attr_val is not None:
            attr = foundation.Attribute(attr_id, value=attr_val)
            attr_write_list.append(attr)  # Write list


    result_read = None
    if read_before_write or (len(attr_write_list) == 0):
        LOGGER.debug("Request attr read %s", attr_read_list)
        result_read = await cluster.read_attributes(
            attr_read_list, manufacturer=manf)
        LOGGER.debug("Reading attr result (attrs, status): %s", result_read)
        success = (len(result_read[1]) == 0 and len(result_read[0]) == 1)


    if ( len(attr_write_list) != 0  and
        ( 
             not(read_before_write)
             or write_if_equal
             or ( not attr_id in result_read[0] or result_read[0][attr_id] == attr_val.serialize())
        )
        ):
        if result_read is not None:
            event_data["read_before"] = result_read
            result_read is None

        LOGGER.debug("Request attr write %s", attr_write_list)
        result_write = await cluster._write_attributes(
            attr_write_list, manufacturer=manf)
        LOGGER.debug("Write attr status: %s", result_write)
        event_data["result_write"] = result_write

        if read_after_write:
            LOGGER.debug("Request attr read %s", attr_read_list)
            result_read = await cluster.read_attributes(
                attr_read_list, manufacturer=manf)
            LOGGER.debug("Reading attr result (attrs, status): %s", result_read)
            success = success and (len(result_read[1]) == 0 and len(result_read[0]) == 1) and (result_read == attr_val.serialize())

    if result_read is not None:
        event_data["result_read"] = result_read


    event_data["success"] = success


    # Write value to provided state or state attribute
    if state_id is not None:
        if len(result_read[1]) == 0 and len(result_read[0]) == 1:
             # No error and one result
             for id,val in result_read[0].items():
                 if state_attr is not None:
                     LOGGER.debug("Set state %s[%s] -> %s from attr_id %s", state_id, state_attr, val, id)
                 else:
                     LOGGER.debug("Set state %s -> %s from attr_id %s", state_id, val, id)
                 u.set_state(listener._hass, state_id, val, key=state_attr, allow_create=allow_create) 
                 LOGGER.debug("STATE is set")

    # Fire events
    if success: 
        if type(event_success) == str:
            LOGGER.debug("Fire %s -> %s", event_success, event_data)
            listener._hass.bus.fire(event_success, event_data)
    else:
        if type(event_fail) == str:
            LOGGER.debug("Fire %s -> %s", event_fail, event_data)
            listener._hass.bus.fire(event_fail, event_data)
    if type(event_done) == str:
        LOGGER.debug("Fire %s -> %s", event_done, event_data)
        listener._hass.bus.fire(event_done, event_data)

    
    # For internal use
    return result_read 

    # Example where attributes are not types
    # (supposed typed by the internals):
    #   attrs = {0x0009: 0b00001000, 0x0012: 1400, 0x001C: 0xFF}
    #   result = await cluster.write_attributes(attrs)
