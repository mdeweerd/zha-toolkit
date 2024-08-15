#!/bin/env python3
#
# Takes --version X.Y.Z or -V X.Y.Z option and sets version in manifest.json.
# Must be launched from the root of the repository.
#
# Modified from : https://raw.githubusercontent.com/bramstroker/homeassistant-zha-toolkit/master/.github/scripts/update_hacs_manifest.py  # noqa: E501
#
# MIT License
#
# Copyright (c) 2021      Bram Gerritsen
# Copyright (c) 2022-2024 Mario DE WEERD
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Update the files with new version."""
import json
import os
import re
import sys


def update_manifest(path=None, version=None):
    """Update the manifest file."""
    if path is None:
        return

    with open(
        path,
        encoding="utf_8",
    ) as manifestfile:
        manifest = json.load(manifestfile)

    manifest["version"] = version

    with open(
        path,
        "w",
        encoding="utf_8",
    ) as manifestfile:
        manifestfile.write(json.dumps(manifest, indent=4, sort_keys=True))


def replace_version_in_file(path: str, regex: str, version: str):
    # Remove any leading 'v' from the provided version
    new_version = version.lstrip("v")

    # Compile the regex pattern
    pattern = re.compile(regex)

    # Function to replace the version part in the match
    def version_replacer(match):
        print("YAS")
        # Extract the original version from the match
        original_version = match.group("version")

        # Determine if the original version started with 'v'
        if original_version.startswith("v"):
            replacement_version = f"v{new_version}"
        else:
            replacement_version = new_version

        # Replace the version in the matched string
        replacement_match = match.group(0).replace(
            original_version, replacement_version
        )

        return replacement_match

    # Read the file content
    with open(path, encoding="utf_8") as file:
        content = file.read()

    # Replace the versions in the content
    new_content = pattern.sub(version_replacer, content)

    # Write the modified content back to the file
    with open(path, "w", encoding="utf_8") as file:
        file.write(new_content)


newVersion = "0.0.0"
for index, value in enumerate(sys.argv):
    if value in ["--version", "-V", "-v"]:
        newVersion = sys.argv[index + 1]


filepath = f"{os.getcwd()}/custom_components/zha_toolkit/manifest.json"
update_manifest(filepath, newVersion)

# Example:
# replace_version_in_file('file.txt', r'(?P<version>v?\d+\.\d+\.\d+)', '2.3.4')

# filepath = f"{os.getcwd()}/README"
# Example1: regex = r'toolkit version \[(?P<version>.*?)]'
# Example2: regex= r'(?P<version>v?\d+\.\d+\.\d+)'
# replace_version_in_file(filepath, regex, newVersion)
