#!/bin/sh
# NOTE: you can now download by using the HA Service `zha-toolkit/ota_notify`.
#
# Important:
#  Requires `jq` (https://stedolan.github.io/jq/)
#  If not available on your system, on alpine you just
#  need to add the [jq package](https://pkgs.alpinelinux.org/package/edge/main/x86/jq).
#
# In configuration.yaml, set the fw directory:
# (Note: only the otau_directory option is shown)
#
# ```yaml
# zha:
#   zigpy_config:
#     ota:
#       otau_directory: /config/zb_ota
# ```
#
# Create the directory you have chosen (`/config/zb_ota`
# in the example).  Then add this script in that directory.
# Make the script executable (`chmod +x fetchOTAfw.sh`) and
# run it.
#
#
# If you find FW that is not in that list, check out the
# [instructions](https://github.com/Koenkk/zigbee-OTA#adding-new-and-updating-existing-ota-files)
# to add them.
#

# List all FW files that were already downloaded.
# The files usually have the FW version in their name, making them unique.
ls *.ZIGBEE *.OTA *.sbl-ota *.bin *.ota *.zigbee > existing.list

# Get and filter the list from Koenk's list, download the files
curl https://raw.githubusercontent.com/Koenkk/zigbee-OTA/master/index.json |\
    jq -r '.[] |.url' |\
    grep -v -f existing.list |\
    xargs bash -c 'for f do wget --no-clobber $f || rm ${f##*/} ; done'

# Delete the helper file used to filter already downloaded files
rm existing.list
