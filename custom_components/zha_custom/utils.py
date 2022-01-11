import logging
from enum import Enum
from zigpy import types as t


LOGGER = logging.getLogger(__name__)

# Convert string to int if possible or return original string
#  (Returning the original string is usefull for named attributes)
def str2int(s):
    if not type(s) == str:
        return s
    elif s.lower() == "false":
        return 0
    elif s.lower() == "true":
        return 1
    elif s.startswith("0x") or s.startswith("0X"):
        return int(s, 16)
    elif s.startswith("0") and s.isnumeric():
        return int(s, 8)
    elif s.startswith("b") and s[1:].isnumeric():
        return int(s[1:], 2)
    elif s.isnumeric():
        return int(s)
    else:
        return s



class RadioType(Enum):
    UNKNOWN = 0
    ZNP = 1

def get_radiotype(app):
    if app._znp is not None:
        return RadioType.ZNP
    LOGGER.debug("Type recognition for '%s' not implemented", type(app))
    return RadioType.UNKNOWN

    
# Get zigbee IEEE address (EUI64) for the reference.
#  Reference can be entity, device, or IEEE address
async def get_ieee(app, listener, ref):
    # LOGGER.debug("Type IEEE: %s", type(ref))
    if type(ref) == str:
        # Check if valid ref address
        if (ref.count(':') == 7):
            return t.EUI64.convert(ref)

        # Check if network address
        nwk=str2int(ref)
        if (type(nwk) == int) and nwk>=0x0000 and nwk<=0xFFF7:
            device=app.get_device(nwk=nwk)
            if device is None:
                return None
            else:
                LOGGER.debug("NWK addr 0x04x -> %s", nwk, device.ieee)
                return device.ieee
      
        # Todo: check if NWK address
        entity_registry = await listener._hass.helpers.entity_registry.async_get_registry()
        #LOGGER.debug("registry %s",entity_registry)
        registry_entity = entity_registry.async_get(ref)
        LOGGER.debug("registry_entity %s",registry_entity)
        if registry_entity is None:
            return None
        if registry_entity.platform != "zha":
            LOGGER.error("Not a ZHA device : '%s'", ref)
            return None

        device_registry = await listener._hass.helpers.device_registry.async_get_registry()
        registry_device = device_registry.async_get(registry_entity.device_id)
        LOGGER.debug("registry_device %s",registry_device)
        for identifier in registry_device.identifiers:
            if identifier[0]=='zha':
                return t.EUI64.convert(identifier[1])
        return None

    # Other type, suppose it's already an EUI64
    return ref


# Get a zigbee device instance for the reference.
#  Reference can be entity, device, or IEEE address
async def get_device(app, listener, reference):
    # Method is called get 
    ieee=await get_ieee(app, listener, reference)
    LOGGER.debug("IEEE for get_device: %s", ieee)
    return app.get_device(ieee)
