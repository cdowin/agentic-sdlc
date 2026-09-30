#!/usr/bin/env bash
# FIXTURE, not the shipped guard: a cc-* hook that can block, and that replays
# its own one-case corpus.
set -eu
if [ "${1:-}" = "--self-test" ]; then
	self_test_rc=0
	if printf block | bash "$0"; then
		echo "the corpus says block and the hook allowed" >&2
		self_test_rc=1
	else
		echo "SELF-TEST OK"
	fi
	exit "$self_test_rc"
fi
if [ "$(cat)" = block ]; then
	exit 2
fi
exit 0
