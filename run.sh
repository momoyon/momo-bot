#!/bin/sh

. ./.venv/bin/activate

python ./bot.py $*

deactivate
