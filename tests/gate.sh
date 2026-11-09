#!/bin/sh
# tests/gate.sh - plugin/bin/gate wide: concurrent calls run one after the other (2, then 3 at once),
# a holder that dies frees the lock, the command's exit code comes back, and a load above the cap refuses with exit 75.
g=$(cd "$(dirname "$0")/.." && pwd)/plugin/bin/gate
d=$(mktemp -d)
trap 'rm -rf "$d"' EXIT INT TERM
export TMPDIR="$d" AGENTIC_SDLC_MAX_LOAD=1000
# shellcheck disable=SC2016 # expands in the child sh
run='echo start $1 >> "$0"; sleep 1; echo end $1 >> "$0"'
sh "$g" wide sh -c "$run" "$d/log" a 2>/dev/null &
sleep 0.3
sh "$g" wide sh -c "$run" "$d/log" b 2>/dev/null &
wait
[ "$(tr '\n' ' ' < "$d/log")" = "start a end a start b end b " ] || { echo "FAIL not serial: $(cat "$d/log")"; exit 1; }
# 3 at once: the runs never overlap.
# shellcheck disable=SC2016 # expands in the child sh
run3='echo start >> "$0"; sleep 0.4; echo end >> "$0"'
for _ in 1 2 3; do sh "$g" wide sh -c "$run3" "$d/log3" 2>/dev/null & done
wait
[ "$(tr '\n' ' ' < "$d/log3")" = "start end start end start end " ] || { echo "FAIL 3 at once overlap: $(tr '\n' ' ' < "$d/log3")"; exit 1; }
# A holder killed with -9 frees the lock: the next call runs at once.
sh "$g" wide sh -c 'kill -9 $$' 2>/dev/null
start=$(date +%s); sh "$g" wide true 2>/dev/null || { echo "FAIL after a killed holder"; exit 1; }
[ $(($(date +%s) - start)) -lt 5 ] || { echo "FAIL a killed holder kept the lock"; exit 1; }
sh "$g" wide sh -c 'exit 7' 2>/dev/null; [ $? = 7 ] || { echo "FAIL exit code"; exit 1; }
AGENTIC_SDLC_MAX_LOAD=0 sh "$g" wide true 2>/dev/null; [ $? = 75 ] || { echo "FAIL a load refusal is not exit 75"; exit 1; }
exit 0
