#!/usr/bin/env bash

DATA_DIR="/md/nasdaq_pcaps"
OUT_DIR="extracted_messages"

START=20250201
END=20250203

MAX_JOBS=10
running=0

for day in $(seq $START $END); do
    ./message_extraction.sh \
        --data-dir "$DATA_DIR" \
        --out-dir "$OUT_DIR" \
        --start-day "$day" \
        --end-day "$day" &

    ((running++))

    if [[ $running -ge $MAX_JOBS ]]; then
        wait -n
        ((running--))
    fi
done

wait
echo "All jobs finished"
