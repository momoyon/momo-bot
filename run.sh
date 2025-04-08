#!/bin/sh

VENV_PATH=./.venv
PYTHON=python

if [ ! $(command -v $PYTHON) ]; then
    PYTHON=python3
    if [ ! $(command -v $PYTHON ]; then
        echo "ERROR: `python` nor `python3` is in PATH!"
        exit 1
    fi
fi

if [ ! -d "$VENV_PATH" ]; then
    echo WARNING: Python venv dir not found...
    echo INFO: Creating Python venv in $VENV_PATH...
    $PYTHON -m venv $VENV_PATH
fi

. $VENV_PATH/bin/activate

pip install discord.py pynacl yt_dlp python-dotenv coloredlogs aiofile

python ./bot.py $*

deactivate
