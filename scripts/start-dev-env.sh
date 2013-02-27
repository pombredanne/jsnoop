#! /usr/bin/env source
# Switch to dev environment
# Sets up the development environment if it does not exist

ENV_DIR=jsnoop.dev
ENV_PROMPT=jsnoop.dev
PYRUS_URL="http://github.com/abn/pyrus/tarball/master#egg=pyrus-0.0.1"

{ command -v easy_install >/dev/null 2>&1 && CMD=easy_install; } ||  { command -v pip >/dev/null 2>&1 && CMD=pip; }

# We know pip is installed, so use it
[ -z $CMD ] && { CMD=pip; }

function vitualize {
    if [ ! -d "$ENV_DIR" ]; then
        virtualenv -p $(which python3) --prompt=${ENV_PROMPT} ${ENV_DIR}
        source ${ENV_DIR}/bin/activate
        $CMD ${PYRUS_URL}
    else
        source ${ENV_DIR}/bin/activate
    fi

    export PYTHONPATH=$PYTHONPATH:$(pwd)/src
}


# We require virtuaenv and (easy_install/pip) to be installed
{ command -v virtualenv >/dev/null 2>&1 && vitualize; } || { echo >&2 "ERROR: virtualenv command not found, not switching"; }

