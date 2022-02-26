#!/bin/bash

DEST=$(dirname $0)/../../STATS.md

TEMPLATE='- (![badge VERSION](https://img.shields.io/github/downloads/mdeweerd/zha-toolkit/VERSION/total.svg)'

(
echo '# Badges showing number of downloads per version'
echo
for tag in latest $(git tag -l  --sort=-creatordate v*[0-9]) ; do
   echo ${TEMPLATE//VERSION/$tag}
done
) > "${DEST}"
