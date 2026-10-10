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
# --args: the copy adds 1 merge of the file after the meta literal, and the script reads its graph.
printf '{"graph": {"repo": "x/y",\n "branch": "b", "base": {"ref": "main", "sha": "0123456789abcdef0123456789abcdef01234567"}, "tasks": [{"id": "a"}]}}\n' > "$tmp/args.json"
a=$(sh "$root/plugin/bin/name-workflow" --args "$tmp/args.json" wave "big graph" "$tmp/a") || { echo "FAIL --args: exit $?"; fail=1; }
added=$(diff "$root/plugin/workflows/wave.js" "$a" | grep -c '^>')
[ "$added" = 4 ] || { echo "FAIL --args: $added lines differ, want the name line and 3 merge lines"; fail=1; }
if command -v node > /dev/null 2>&1; then
  # The graph comes from the file, so the run stops at the next check: args.started_at.
  err=$(node -e 'const s = require("fs").readFileSync(process.argv[1], "utf8").replace(/^export /m, "");
    new (async () => {}).constructor("args", "log", s)({}, () => {}).catch((e) => console.log(e.message))' "$a")
  case $err in *started_at*) ;; *) echo "FAIL --args: the copy did not read the graph from the file: $err"; fail=1 ;; esac
  # A call with no args at all (args undefined) works the same.
  err=$(node -e 'const s = require("fs").readFileSync(process.argv[1], "utf8").replace(/^export /m, "");
    new (async () => {}).constructor("args", "log", s)(undefined, () => {}).catch((e) => console.log(e.message))' "$a")
  case $err in *started_at*) ;; *) echo "FAIL --args: a call with no args failed: $err"; fail=1 ;; esac
fi
if command -v jq > /dev/null 2>&1; then
  echo '[1]' > "$tmp/list.json"
  sh "$root/plugin/bin/name-workflow" --args "$tmp/list.json" wave x "$tmp" >/dev/null 2>&1; [ "$?" = 2 ] || { echo "FAIL an args file that is no object should exit 2"; fail=1; }
fi
sh "$root/plugin/bin/name-workflow" --args "$tmp/none.json" wave x "$tmp" >/dev/null 2>&1; [ "$?" = 2 ] || { echo "FAIL a missing args file should exit 2"; fail=1; }
sh "$root/plugin/bin/name-workflow" nope x "$tmp" >/dev/null 2>&1; [ "$?" = 2 ] || { echo "FAIL unknown workflow should exit 2"; fail=1; }
sh "$root/plugin/bin/name-workflow" wave >/dev/null 2>&1; [ "$?" = 2 ] || { echo "FAIL no goal should exit 2"; fail=1; }
exit $fail
