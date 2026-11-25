import json
import logging
import os
import pathlib
from glob import glob

import aiohttp
import zigpy

from . import DEFAULT_OTAU
from . import utils as u
from .params import INTERNAL_PARAMS as p

LOGGER = logging.getLogger(__name__)
KOENKK_LIST_URL = (
    "https://raw.githubusercontent.com/Koenkk/zigbee-OTA/master/index.json"
)

SONOFF_LIST_URL = "https://zigbee-ota.sonoff.tech/releases/upgrade.json"


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
        for path in [
            os.path.basename(x) for x in glob(os.path.join(ota_dir, glob_expr))
        ]:
            ota_files_on_disk[path] = True

    # LOGGER.debug(f"OTA files on disk {ota_files_on_disk!r}")

    # Get manufacturers
    manfs = {}
    for info in [
        device.zha_device_info for device in u.get_zha_devices(listener)
    ]:
        manfs[info["manufacturer_code"]] = True

    LOGGER.debug(f"Get Koenkk FW list and check for manfs {manfs.keys()!r}")
    new_fw_info = {}
    async with aiohttp.ClientSession() as req:
        async with req.get(KOENKK_LIST_URL) as rsp:
            data = json.loads(await rsp.read())
            for fw_info in data:
                if fw_info["url"]:
                    filename = fw_info["url"].split("/")[-1]
                    # Try to get fw corresponding to device manufacturers
                    fw_manf = fw_info["manufacturerCode"]

                    if fw_manf in manfs and filename not in ota_files_on_disk:
                        LOGGER.debug(
                            "OTA file to download for manf %u (0x%04X): '%s'",
                            fw_manf,
                            fw_manf,
                            filename,
                        )
                        new_fw_info[filename] = fw_info

    for filename, fw_info in new_fw_info.items():
        async with aiohttp.ClientSession() as req:
            url = fw_info["url"]
            try:
                out_filename = os.path.join(ota_dir, filename)

                LOGGER.debug("Download '%s' to '%s'", url, out_filename)
                async with req.get(url) as rsp:
                    data = await rsp.read()

                with open(out_filename, "wb") as ota_file:
                    LOGGER.debug("Try to write '%s'", out_filename)
                    ota_file.write(data)
            except Exception as e:
                LOGGER.warning("Exception getting '%s': %s", url, e)


async def download_sonoff_ota(listener, ota_dir):
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
        for path in [
            os.path.basename(x) for x in glob(os.path.join(ota_dir, glob_expr))
        ]:
            ota_files_on_disk[path] = True

    # LOGGER.debug(f"OTA files on disk {ota_files_on_disk!r}")

    # Get manufacturers
    manfs = {}
    for info in [
        device.zha_device_info for device in u.get_zha_devices(listener)
    ]:
        manfs[info["manufacturer_code"]] = True

    LOGGER.debug(f"Get SONOFF FW list and check for manfs {manfs.keys()!r}")
    new_fw_info = {}
    async with aiohttp.ClientSession() as req:
        async with req.get(SONOFF_LIST_URL) as rsp:
            data = json.loads(await rsp.read())
            for fw_info in data:
                if fw_info["fw_binary_url"]:
                    filename = fw_info["fw_binary_url"].split("/")[-1]
                    # Try to get fw corresponding to device manufacturers
                    fw_manf = fw_info["fw_manufacturer_id"]
                    fw_model_id = fw_info["model_id"]

                    # Note: could check against model id in the future
                    if fw_manf in manfs and filename not in ota_files_on_disk:
                        LOGGER.debug(
                            "OTA file to download for manf %u (0x%04X)"
                            " Model:'%s': '%s'",
                            fw_manf,
                            fw_manf,
                            fw_model_id,
                            filename,
                        )
                        new_fw_info[filename] = fw_info

    for filename, fw_info in new_fw_info.items():
        async with aiohttp.ClientSession() as req:
            url = fw_info["fw_binary_url"]
            try:
                out_filename = os.path.join(ota_dir, filename)

                LOGGER.debug("Download '%s' to '%s'", url, out_filename)
                async with req.get(url) as rsp:
                    data = await rsp.read()

                with open(out_filename, "wb") as ota_file:
                    LOGGER.debug("Try to write '%s'", out_filename)
                    ota_file.write(data)
            except Exception as e:
                LOGGER.warning("Exception getting '%s': %s", url, e)


async def register_local_ota_provider(app, ota_dir):
    """Register a toolkit-managed file provider for a local OTA directory.

    Firmware files deposited in (or downloaded to) `ota_dir` are picked up
    from the file system and become available for OTA updates, without
    relying on the zigpy/ZHA OTA provider configuration.
    """
    if not (hasattr(app, "ota") and hasattr(app.ota, "register_provider")):
        LOGGER.warning(
            "Could not get ota object for register_local_ota_provider"
        )
        return
    provider = zigpy.ota.providers.AdvancedFileProvider(
        path=pathlib.Path(ota_dir)
    )
    app.ota.register_provider(provider)
    LOGGER.debug("Registered local OTA file provider for '%s'", ota_dir)


async def download_zigpy_ota(app, listener):
    LOGGER.debug("Zigpy download procedure starting")
    if hasattr(app, "ota") and hasattr(app.ota, "_providers"):
        for provider in app.ota._providers:
            if isinstance(provider, zigpy.ota.providers.AdvancedFileProvider):
                # Skip file-based providers
                continue
            await app.ota._refresh_provider_index(provider)
            for image_meta, image in app.ota._image_cache.get(
                provider, {}
            ).items():
                LOGGER.debug("Try getting %r from %r", image_meta, provider)
                try:
                    img = await app.ota._fetch_image(image)
                    LOGGER.info(
                        "Got image %r",
                        getattr(img.firmware, "header", None),
                    )
                except Exception as e:
                    LOGGER.error("%r while getting %r", e, image_meta)
    else:
        LOGGER.warning(
            "Could not get ota object for download_zigpy_ota, try again"
        )


async def ota_update_images(
    app, listener, ieee, cmd, data, service, params, event_data
):
    if hasattr(app, "ota") and hasattr(app.ota, "_providers"):
        for provider in app.ota._providers:
            await app.ota._refresh_provider_index(provider)
    else:
        LOGGER.warning(
            "Could not get ota object for ota_update_images, try again"
        )


async def ota_notify(
    app, listener, ieee, cmd, data, service, params, event_data
):
    LOGGER.debug("OTA_notify")
    event_data["PAR"] = params
    if params[p.DOWNLOAD]:
        if params[p.PATH]:
            ota_dir = params[p.PATH]
        else:
            ota_dir = DEFAULT_OTAU

        LOGGER.debug(
            "OTA image download to '%s' (Default dir is:'%s')",
            ota_dir,
            DEFAULT_OTAU,
        )

        await download_zigpy_ota(app, listener)
        await download_koenkk_ota(listener, ota_dir)
        await download_sonoff_ota(listener, ota_dir)

        # Make the local files available for OTA updates
        await register_local_ota_provider(app, ota_dir)

    # Get tries
    tries = params[p.TRIES]

    # Update internal image database
    await ota_update_images(
        app, listener, ieee, cmd, data, service, params, event_data
    )

    if ieee is None:
        LOGGER.error("missing ieee")
        return

    LOGGER.debug("running 'image_notify' command: %s", service)

    device = await u.get_device(app, listener, ieee)

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
    await u.retry_wrapper(basic.bind, tries=tries)
    ret = await u.retry_wrapper(
        basic.configure_reporting, "sw_build_id", 0, 1800, 1, tries=tries
    )
    LOGGER.debug("Configured reporting: %s", ret)

    ret = None
    if not u.is_zigpy_ge("0.45.0"):
        ret = await cluster.image_notify(0, 100)
    else:
        cmd_args = [0, 100]
        ret = await u.retry_wrapper(
            cluster.client_command,
            0,  # cmd_id
            *cmd_args,
            # expect_reply = True,
            tries=tries,
        )

    LOGGER.debug("Sent image notify command to 0x%04x: %s", device.nwk, ret)
    event_data["result"] = ret
