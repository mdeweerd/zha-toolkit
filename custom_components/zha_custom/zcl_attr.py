import asyncio
import logging

from zigpy import types as t
from zigpy.zcl import foundation as f
from zigpy.exceptions import DeliveryError
# import zigpy.zcl as zcl
from . import utils as u
from homeassistant.util import dt as dt_util


LOGGER = logging.getLogger(__name__)


async def conf_report(app, listener, ieee, cmd, data, service):
    event_data={}
    # Decode parameters
    params = u.extractParams(service)

    dev = app.get_device(ieee=ieee)

    # Get best endpoint
    if params['endpoint_id'] is None or params['endpoint_id'] == "":
        params['endpoint_id'] = u.find_endpoint(dev, params['cluster_id'])

    if params['endpoint_id'] not in dev.endpoints:
        LOGGER.error("Endpoint %s not found for '%s'", params['endpoint_id'], repr(ieee))

    if params['cluster_id'] not in dev.endpoints[params['endpoint_id']].in_clusters:
        LOGGER.error("Cluster 0x%04X not found for '%s', endpoint %s",
                      params['cluster_id'], repr(ieee), params['endpoint_id'])

    cluster = dev.endpoints[params['endpoint_id']].in_clusters[params['cluster_id']]

    # await cluster.bind()   -> commented, not performing bind to coordinator

    triesToGo=params['tries']
    success=False
    result_conf=None

    while triesToGo>=1:
        triesToGo=triesToGo-1
        try:
            LOGGER.debug('Try configure report(%s,%s,%s,%s,%s) Try %s/%s',
                params['attr_id'],
                params['min_interval'],
                params['max_interval'],
                params['reportable_change'],
                params['manf'],
                params['tries']-triesToGo,params['tries'])
            result_conf = await cluster.configure_reporting(
                params['attr_id'],
                params['min_interval'],
                params['max_interval'],
                params['reportable_change'],
                manufacturer=params['manf']
            )
            event_data["params"]=params
            event_data["result_conf"]=result_conf
            triesToGo=0 # Stop loop
            LOGGER.info("Configure report result: %s", result_conf)
            success=(result_conf[0][0].status==f.Status.SUCCESS)
        except (DeliveryError, asyncio.TimeoutError) as e:
            continue
        except Exception as e:
            triesToGo=0 # Stop loop
            LOGGER.debug("Configure report exception %s,%s,%s,%s,%s,%s",
                e,
                params['attr_id'],
                params['min_interval'],
                params['max_interval'],
                params['reportable_change'],
                params['manf'])


    # Write value to provided state or state attribute
    if False and state_id is not None:
        if len(result_conf[1]) == 0 and len(result_conf[0]) == 1:
             # No error and one result
             for id,val in result_conf[0].items():
                 if state_attr is not None:
                     LOGGER.debug("Set state %s[%s] -> %s from attr_id %s", state_id, state_attr, val, id)
                 else:
                     LOGGER.debug("Set state %s -> %s from attr_id %s", state_id, val, id)
                 u.set_state(listener._hass, state_id, val, key=state_attr, allow_create=allow_create) 
                 LOGGER.debug("STATE is set")

    # Fire events
    if success: 
        if params['event_success'] is not None:
            LOGGER.debug("Fire %s -> %s", params['event_success'], event_data)
            listener._hass.bus.fire(params['event_success'], event_data)
    else:
        if params['event_fail'] is not None:
            LOGGER.debug("Fire %s -> %s", params['event_fail'], event_data)
            listener._hass.bus.fire(params['event_fail'], event_data)
    if params['event_done'] is not None:
        LOGGER.debug("Fire %s -> %s", params['event_done'], event_data)
        listener._hass.bus.fire(params['event_done'], event_data)

    


async def attr_read(app, listener, ieee, cmd, data, service):
    await attr_write(app, listener, ieee, cmd, data, service)

# This code is shared with attr_read.
# Can read and write 1 attribute
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
        write_if_equal = False

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


    compare_val=None

    # Type only needed for write
    if attr_type_str is not None:
        # Decode attribute type
        attr_type = u.str2int(attr_type_str)

        # Convert attribute value (provided as a string) to appropriate
        # attribute value
        # If the attr_type is not set, then the attribute will be only read.
        attr_val = None
        if attr_type == 0x10:
            compare_val=u.str2int(attr_val_str)
            attr_val = f.TypeValue(
                attr_type, t.Bool(compare_val))
        elif attr_type == 0x20:
            compare_val=u.str2int(attr_val_str)
            attr_val = f.TypeValue(
                attr_type, t.uint8_t(compare_val))
        elif attr_type <= 0x31 and attr_type >= 0x08:
            compare_val=u.str2int(attr_val_str)
            # uint, int, bool, bitmap and enum
            attr_val = f.TypeValue(
                attr_type, t.FixedIntType(compare_val))
        elif attr_type in [ 0x41, 0x42 ]:  # Octet string
            # Octet string requires length -> LVBytes

            compare_val=attr_val_str;

            if type(attr_val_str) == str:
                attr_val_str = bytes(attr_val_str,'utf-8')
    
            if isinstance(attr_val_str, list):
                # Convert list to List of uint8_t
                attr_val_str = t.List[t.uint8_t]([t.uint8_t(i) for i in attr_val_str])
    
            attr_val = f.TypeValue(
                attr_type, t.LVBytes(attr_val_str))
  
        if attr_val is not None:
            attr = f.Attribute(attr_id, value=attr_val)
            attr_write_list.append(attr)  # Write list
        LOGGER.debug("ATTR TYPE %s, attr_val %s", attr_type, attr_val)


    result_read = None
    if read_before_write or (len(attr_write_list) == 0) or cmd != 'attr_write':
        LOGGER.debug("Request attr read %s", attr_read_list)
        result_read = await cluster.read_attributes(
            attr_read_list, manufacturer=manf)
        LOGGER.debug("Reading attr result (attrs, status): %s", result_read)
        success = (len(result_read[1]) == 0 and len(result_read[0]) == 1)

    # True if value that should be written is the equal to the read one
    write_is_equal = (
            len(attr_write_list) != 0 
            and ( attr_id in result_read[0] and result_read[0][attr_id] == compare_val)
        )
    write_is_equal = False # Test
    LOGGER.debug("Write is equal '%s'=='%s' %s", result_read[0][attr_id], compare_val, write_is_equal)

    if ( len(attr_write_list) != 0  and
        ( 
             not(read_before_write)
             or write_if_equal
             or not(write_is_equal)
        ) and cmd == 'attr_write'
       ):
        if result_read is not None:
            event_data["read_before"] = result_read
            result_read is None

        LOGGER.debug("Request attr write %s", attr_write_list)
        result_write = await cluster._write_attributes(
            attr_write_list, manufacturer=manf)
        LOGGER.debug("Write attr status: %s", result_write)
        event_data["result_write"] = result_write
        success = False
        try:
            #LOGGER.debug("Write attr status: %s", result_write[0][0].status)
            success=(result_write[0][0].status==f.Status.SUCCESS)
            LOGGER.debug("Write success: %s", success)
        except e:
            success = False

        #success = (len(result_write[1])==0)

        if read_after_write:
            LOGGER.debug("Request attr read %s", attr_read_list)
            result_read = await cluster.read_attributes(
                attr_read_list, manufacturer=manf)
            LOGGER.debug("Reading attr result (attrs, status): %s", result_read)
            read_is_equal = (result_read[0][attr_id] == compare_val)
            success = ( 
                    success
                    and (len(result_read[1]) == 0 and len(result_read[0]) == 1)
                         and (result_read[0][attr_id] == compare_val)
                )

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
