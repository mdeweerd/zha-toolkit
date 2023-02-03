#!/bin/bash

DEST=$(dirname $0)/../../STATS.md

TEMPLATE='- ![badge VERSION](https://img.shields.io/github/downloads/mdeweerd/zha-toolkit/VERSION/total.svg)'

# Exclude stuff that results in invalid badges
EXCLUDES="v0.7.9 v0.7.7 v0.7.6 v0.7.5 v0.7.3 v0.7.2 v0.7.1 v0.7.23 v0.7.24, v0.8.30"

(
    echo '# Badges showing number of downloads per version'
    echo
    for tag in latest $(git tag -l  --sort=-creatordate v*[0-9]) ; do
        if [[ "$EXCLUDES" != *"$tag"* ]] ; then
            echo ${TEMPLATE//VERSION/$tag}
        fi
    done
) > "${DEST}"
