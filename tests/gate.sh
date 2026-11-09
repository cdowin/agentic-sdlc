#!/bin/sh
# tests/gate.sh - plugin/bin/gate wide: two concurrent calls run one after the other, a dead
# holder's lock is taken over (with no stale copy left), and a load above the cap refuses with exit 75.
g=$(cd "$(dirname "$0")/.." && pwd)/plugin/bin/gate
d=$(mktemp -d)
trap 'rm -rf "$d"' EXIT INT TERM
export TMPDIR="$d" AGENTIC_SDLC_MAX_LOAD=1000 AGENTIC_SDLC_GATE_POLL=0.1
# shellcheck disable=SC2016 # expands in the child sh
run='echo start $1 >> "$0"; sleep 1; echo end $1 >> "$0"'
sh "$g" wide sh -c "$run" "$d/log" a 2>/dev/null &
sleep 0.3
sh "$g" wide sh -c "$run" "$d/log" b 2>/dev/null &
wait
[ "$(tr '\n' ' ' < "$d/log")" = "start a end a start b end b " ] || { echo "FAIL not serial: $(cat "$d/log")"; exit 1; }
[ ! -e "$d/agentic-sdlc-gate-wide.lock" ] || { echo "FAIL lock left behind"; exit 1; }
mkdir "$d/agentic-sdlc-gate-wide.lock" && echo 999999 > "$d/agentic-sdlc-gate-wide.lock/pid"
sh "$g" wide -- true 2>/dev/null || { echo "FAIL stale lock not taken"; exit 1; }
for x in "$d"/agentic-sdlc-gate-wide.lock*; do [ -e "$x" ] && { echo "FAIL stale lock left: $x"; exit 1; }; done
sh "$g" wide sh -c 'exit 7' 2>/dev/null; [ $? = 7 ] || { echo "FAIL exit code"; exit 1; }
AGENTIC_SDLC_MAX_LOAD=0 sh "$g" wide true 2>/dev/null; [ $? = 75 ] || { echo "FAIL a load refusal is not exit 75"; exit 1; }
[ ! -e "$d/agentic-sdlc-gate-wide.lock" ] || { echo "FAIL lock left after refusal"; exit 1; }
exit 0
