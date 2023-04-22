#!/bin/bash
cd config/
(
    git clone -n --depth=1 --filter=tree:0 https://github.com/mdeweerd/zha-toolkit.git
    cd zha-toolkit
    git sparse-checkout set --no-cone custom_components
    git checkout
)
(
    [[ -r custom_components ]] && cd custom_components && ln -s ../zha-toolkit/custom_components/zha_toolkit .
)
# To update:
(
    cd zha-toolkit
    cd git pull
)
