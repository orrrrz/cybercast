#!/bin/bash

# Usage ./gen.sh script|podcast|video|all [args...]

cmd=$1
shift  # Remove the first argument (cmd) from the argument list

if [ -z "$cmd" ]; then
    echo "Usage: ./gen.sh <cmd> [args...]"
    exit 1
fi

if [ "$cmd" == "script" ]; then
    python gen_script.py $@
elif [ "$cmd" == "podcast" ]; then
    python gen_podcast.py $@
elif [ "$cmd" == "video" ]; then
    python gen_video.py $@
elif [ "$cmd" == "all" ]; then
    python gen_script.py $@
    python gen_podcast.py $@
    python gen_video.py $@
fi