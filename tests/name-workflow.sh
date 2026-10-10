#!/bin/sh
# tests/name-workflow.sh - name-workflow copies each workflow and changes only the meta name line.
# POSIX sh. Exit 0 when all pass.
root=$(cd "$(dirname "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT INT TERM
fail=0
for src in "$root"/plugin/workflows/*.js; do
  wf=$(basename "$src" .js)
  out=$(sh "$root/plugin/bin/name-workflow" "$wf" "team model, HQ skills" "$tmp") || { echo "FAIL $wf: exit $?"; fail=1; continue; }
  [ "$out" = "$tmp/$wf.js" ] || { echo "FAIL $wf: printed '$out'"; fail=1; continue; }
  d=$(diff "$src" "$out" | grep '^[<>]')
  want="< $(sed -n '2p' "$src")
> $(printf "  name: '%s: team model, HQ skills'," "$wf")"
  [ "$d" = "$want" ] || { echo "FAIL $wf: diff is not the name line only: $d"; fail=1; }
done
long=$(sh "$root/plugin/bin/name-workflow" wave "a goal that is far too long to fit in fifty characters" "$tmp/l")
n=$(sed -n "2s/^  name: '\(.*\)',\$/\1/p" "$long" | awk '{ print length($0) }')
[ "$n" = 50 ] || { echo "FAIL long goal: name is $n characters, want 50"; fail=1; }
q=$(sh "$root/plugin/bin/name-workflow" wave "it's" "$tmp/q")
[ "$(sed -n 2p "$q")" = "  name: 'wave: it\\'s'," ] || { echo "FAIL quote not escaped"; fail=1; }
sh "$root/plugin/bin/name-workflow" nope x "$tmp" >/dev/null 2>&1; [ "$?" = 2 ] || { echo "FAIL unknown workflow should exit 2"; fail=1; }
sh "$root/plugin/bin/name-workflow" wave >/dev/null 2>&1; [ "$?" = 2 ] || { echo "FAIL no goal should exit 2"; fail=1; }
exit $fail
