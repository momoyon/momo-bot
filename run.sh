#!/bin/sh

VENV_PATH=./.venv

if [ ! -d "$VENV_PATH" ]; then
    echo WARNING: Python venv dir not found...
    echo INFO: Creating Python venv in $VENV_PATH...
    python -m venv $VENV_PATH
fi

. $VENV_PATH/bin/activate

pip install discord.py pynacl yt_dlp python-dotenv coloredlogs aiofile

python ./bot.py $*

deactivate
