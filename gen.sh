#!/bin/bash

# Usage ./gen.sh prompt|podcast|video <task_name>

cmd=$1
task_name=$2

if [ -z "$task_name" ]; then
    echo "Usage: ./gen.sh <cmd> <task_name>"
    exit 1
fi

if [ "$cmd" == "prompt" ]; then
    python gen_prompt.py -n $task_name
elif [ "$cmd" == "podcast" ]; then
    python gen_podcast.py -n $task_name
elif [ "$cmd" == "video" ]; then
    python gen_video.py -n $task_name
fi