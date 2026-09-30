#!/usr/bin/env bash
# FIXTURE, not the shipped courier: it replays a corpus and never blocks. This
# header says `exit 2` would block a stop; that is prose, not a blocking exit.
set -eu
if [ "${1:-}" = "--self-test" ]; then
	echo "SELF-TEST OK"
	exit 0
fi
cat >/dev/null
exit 0
