# Modified from : https://raw.githubusercontent.com/bramstroker/homeassistant-zha_custom/master/.github/scripts/update_hacs_manifest.py
# 
# MIT License
# 
# Copyright (c) 2021 Bram Gerritsen
# Copyright (c) 2022 Mario DE WEERD
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Update the manifest file."""
import json
import os
import sys


def update_manifest():
    """Update the manifest file."""
    version = "0.0.0"
    for index, value in enumerate(sys.argv):
        if value in ["--version", "-V"]:
            version = sys.argv[index + 1]

    with open(
        f"{os.getcwd()}/custom_components/zha_custom/manifest.json"
    ) as manifestfile:
        manifest = json.load(manifestfile)

    manifest["version"] = version

    with open(
        f"{os.getcwd()}/custom_components/zha_custom/manifest.json", "w"
    ) as manifestfile:
        manifestfile.write(json.dumps(manifest, indent=4, sort_keys=True))


update_manifest()

