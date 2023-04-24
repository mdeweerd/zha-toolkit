#!/bin/bash
# To update / install :
cd config
(
    mkdir -p custom_components/zha_toolkit
    cd custom_components/zha_toolkit
    rm zha-toolkit.zip >& /dev/null
    curl -s https://api.github.com/repos/mdeweerd/zha-toolkit/releases/latest \
        | grep "browser_download_url.*/zha-toolkit.zip" \
        | cut -d : -f 2,3 \
        | tr -d \" \
        | wget -qi -
    unzip -o zha-toolkit.zip
    rm zha-toolkit.zip
)
