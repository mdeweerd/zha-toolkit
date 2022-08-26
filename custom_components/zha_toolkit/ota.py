import json
import logging
import os
import asyncio
from glob import glob
from zigpy import __version__ as zigpy_version
from zigpy.util import retryable
from zigpy.exceptions import DeliveryError
from pkg_resources import parse_version
import aiohttp

from . import DEFAULT_OTAU
from .params import INTERNAL_PARAMS as p

LOGGER = logging.getLogger(__name__)
KOENKK_LIST_URL = (
    "https://raw.githubusercontent.com/Koenkk/zigbee-OTA/master/index.json"
)

@retryable(
    (DeliveryError, asyncio.CancelledError, asyncio.TimeoutError), tries=3
    )
async def wrapper(cmd, *args, **kwargs):
    return await cmd(*args, **kwargs)


async def download_koenkk_ota(listener, ota_dir):
    # Get all FW files that were already downloaded.
    # The files usually have the FW version in their name, making them unique.
    ota_glob_expr = [
        "*.ZIGBEE",
        "*.OTA",
        "*.sbl-ota",
        "*.bin",
        "*.ota",
        "*.zigbee",
    ]

    # Dictionary to do more efficient lookups
    LOGGER.debug("List OTA files available on file system")
    ota_files_on_disk = {}
    for glob_expr in ota_glob_expr:
        for path in [os.path.basename(x) for x in glob(os.path.join(ota_dir,glob_expr))]:
            ota_files_on_disk[path] = True

    # LOGGER.debug(f"OTA files on disk {ota_files_on_disk!r}")

    # Get manufacturers
    manfs = {}
    for info in [
        device.zha_device_info for device in listener.devices.values()
    ]:
        manfs[info["manufacturer_code"]] = True


    LOGGER.debug("Get Koenkk FW list")
    new_fw_info = {}
    async with aiohttp.ClientSession() as req:
        async with req.get(KOENKK_LIST_URL) as rsp:
            data = json.loads(await rsp.read())
            for fw_info in data:
                if fw_info["url"]:
                    filename = fw_info["url"].split("/")[-1]
                    # Try to get fw corresponding to device manufacturers
                    if (
                        fw_info["manufacturerCode"] in manfs
                        and filename not in ota_files_on_disk
                    ): 
                        LOGGER.debug("OTA file to download: '%s'", filename)
                        new_fw_info[filename] = fw_info

    for filename, fw_info in new_fw_info.items():
        async with aiohttp.ClientSession() as req:
            url = fw_info["url"]
            try:
                LOGGER.debug("Get '%s'", url)
                async with req.get(url) as rsp:
                    data = await rsp.read()

                out_filename = os.path.join(ota_dir, filename)

                with open(out_filename, "wb") as ota_file:
                    LOGGER.debug("Try to write '%s'", out_filename)
                    ota_file.write(data)
            except Exception as e:
                LOGGER.warning("Exception getting '%s': %s", url, e)


async def ota_update_images(
    app, listener, ieee, cmd, data, service, params, event_data
):
    for _, (ota, _) in app.ota._listeners.items():
        await ota.refresh_firmware_list()


async def ota_notify(
    app, listener, ieee, cmd, data, service, params, event_data
):
    event_data["PAR"]=params
    if params[p.DOWNLOAD]:
        LOGGER.debug("OTA image download requested")
        # Download FW from koenkk's list
        if params[p.PATH]:
            ota_dir = params[p.PATH]
        else:
            ota_dir = DEFAULT_OTAU

        await download_koenkk_ota(listener, ota_dir)

    # Update internal image database
    await ota_update_images(
        app, listener, ieee, cmd, data, service, params, event_data
    )

    if ieee is None:
        LOGGER.error("missing ieee")
        return

    LOGGER.debug("running 'image_notify' command: %s", service)

    device = app.get_device(ieee=ieee)

    cluster = None
    for epid, ep in device.endpoints.items():
        if epid == 0:
            continue
        if 0x0019 in ep.out_clusters:
            cluster = ep.out_clusters[0x0019]
            break
    if cluster is None:
        LOGGER.debug("No OTA cluster found")
        return
    basic = device.endpoints[cluster.endpoint.endpoint_id].basic
    await basic.bind()
    ret = await basic.configure_reporting("sw_build_id", 0, 1800, 1)
    LOGGER.debug("Configured reporting: %s", ret)

    ret = None
    if parse_version(zigpy_version) < parse_version("0.45.0"):
        ret = await cluster.image_notify(0, 100)
    else:
        cmd_args = [0, 100]
        ret = await wrapper(cluster.client_command,
           0, # cmd_id
           *cmd_args,
           # expect_reply = True,
           tries=params[p.TRIES]
        )

    LOGGER.debug("Sent image notify command to 0x%04x: %s", device.nwk, ret)
    event_data['result'] = ret
