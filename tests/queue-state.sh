#!/bin/sh
# tests/queue-state.sh - plugin/bin/queue-state reads the tracker by fixed rules: only trusted WORKER lines with a
# safe branch count, a report lands only as "WORKER REPORT branch=<b> head=<sha> passed" at head, a later BLOCKED
# (a refused landing) wins, groups are stable, the group PR's Closes list and the open holds findings are read,
# text with quotes and newlines comes out as valid JSON, and every failed read exits 1 (fails closed).
# The stub gh (tests/fixtures/queue-state/gh) reads $QS_FX/<api path, / as _>.json. Needs jq.
# Prints FAIL lines; exit 0 when all pass.
# shellcheck disable=SC2015,SC2016 # bad() cannot fail; $(id) and backticks are literal text in fixtures
set -u
root=$(cd "$(dirname "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
trap 'exit 1' INT TERM
fail=0
bad() { fail=$((fail + 1)); printf 'FAIL %s\n' "$*"; }
fx=$tmp/fx && mkdir "$fx" "$tmp/bin" && cp "$root/tests/fixtures/queue-state/gh" "$tmp/bin/gh"
QS_FX=$fx PATH=$tmp/bin:$PATH
export QS_FX PATH
qs() { sh "$root/plugin/bin/queue-state" "$@"; }
path() { printf '%s/%s' "$fx" "$(printf '%s' "$1" | tr / _)"; }
w() { printf '%s\n' "$2" > "$(path "$1").json"; }
A=$(printf '%040d' 0 | tr 0 a) B=$(printf '%040d' 0 | tr 0 b) C=$(printf '%040d' 0 | tr 0 c)
NL='
'
# iss <n> <title> <labels json> <body>: an open issue, with no dependency link.
iss() {
  jq -n --arg t "$2" --argjson l "$3" --arg b "$4" '{state: "open", title: $t, labels: $l, body: $b}' > "$(path "repos/o/r/issues/$1").json"
  w "repos/o/r/issues/$1/dependencies/blocked_by" '[]'
}
# coms <n> <author> <time> <body> [<author> <time> <body>]...: the comments of issue n.
coms() {
  n=$1; shift
  printf '[]' > "$tmp/c.json"
  while [ "$#" -ge 3 ]; do
    jq --arg a "$1" --arg t "$2" --arg b "$3" '. + [{author_association: $a, created_at: $t, body: $b}]' "$tmp/c.json" > "$tmp/c2.json" && mv "$tmp/c2.json" "$tmp/c.json"
    shift 3
  done
  cp "$tmp/c.json" "$(path "repos/o/r/issues/$n/comments").json"
}
head_of() { w "repos/o/r/git/ref/heads/$1" "{\"object\":{\"sha\":\"$2\"}}"; }
T0=2026-10-08T11:00:00Z T1=2026-10-08T11:30:00Z
iss 20 'Save System, Rework!' '[]' ''
iss 19 'Old blocker' '[]' ''
w repos/o/r/git/matching-refs/heads/20- '[{"ref":"refs/heads/20-save"}]'
w repos/o/r/git/matching-refs/heads/30- '[]'
iss 30 'Menu' '[]' ''
# 21: a title and body with a quote and a newline; a trusted STARTED; an untrusted passed REPORT is ignored.
iss 21 "Save \"the\"${NL}game" '[{"name":"tier:bounded"}]' "Parent: #20${NL}Blocked by #19${NL}A \"quoted\" \\ line"
coms 21 COLLABORATOR "$T0" 'WORKER STARTED branch=21-save session=x' NONE "$T1" "WORKER REPORT branch=21-save head=$A passed"
head_of 21-save "$A"
w "repos/o/r/commits/$A" '{"commit":{"committer":{"date":"2026-10-08T11:05:00Z"}}}'
# 22: a passed REPORT at head, not yet in the group.
iss 22 'Load the game' '[]' 'Parent: #20'
coms 22 MEMBER "$T0" "WORKER REPORT branch=22-load head=$B passed"
head_of 22-load "$B"
w "repos/o/r/commits/$B" '{"commit":{"committer":{"date":"2026-10-08T10:00:00Z"}}}'
w "repos/o/r/compare/20-save...$B" '{"status":"ahead"}'
# 23: no passed; 28: "not passed"; 29: passed in another place. None is landable.
iss 23 'Delete a save' '[]' 'Parent: #20'
coms 23 OWNER "$T0" "WORKER REPORT branch=23-del head=$C"
iss 28 'Rename a save' '[]' 'Parent: #20'
coms 28 OWNER "$T0" "WORKER REPORT branch=28-ren head=$C not passed"
iss 29 'Sort saves' '[]' 'Parent: #20'
coms 29 OWNER "$T0" "WORKER REPORT passed branch=29-sort head=$C"
for b in 23-del 28-ren 29-sort; do head_of "$b" "$C"; done
w "repos/o/r/commits/$C" '{"commit":{"committer":{"date":"2026-10-08T10:00:00Z"}}}'
# 24: a passed REPORT, then the lander's refusal with a quote and a newline: the refusal wins, verbatim.
iss 24 'Copy a save' '[]' 'Parent: #20'
coms 24 MEMBER "$T0" "WORKER REPORT branch=24-copy head=$C passed" MEMBER "$T1" "WORKER BLOCKED branch=24-copy${NL}landing refused: \"1 failed\"${NL}at t.js"
head_of 24-copy "$C"
w "repos/o/r/compare/20-save...$C" '{"status":"diverged"}'
# 25: a passed REPORT already in the group: landed.
iss 25 'Name a save' '[]' 'Parent: #20'
coms 25 MEMBER "$T0" "WORKER REPORT branch=25-name head=$A passed"
head_of 25-name "$A"
w "repos/o/r/compare/20-save...$A" '{"status":"behind"}'
# 26: branches with shell characters, a leading - or .. are ignored, so the branch is the default.
iss 26 'Open the menu' '[]' 'Parent: #30'
coms 26 MEMBER "$T0" 'WORKER STARTED branch=x;rm$(id) session=y' MEMBER "$T0" 'WORKER STARTED branch=-rf session=y' MEMBER "$T0" 'WORKER STARTED branch=a/../b session=y'
# 27: only in the PR's Closes list.
iss 27 'Export a save' '[]' 'Parent: #20'
coms 27
w 'repos/o/r/pulls?state=open&head=o:20-save' '[{"html_url":"https://x/pull/7","body":"Refs #20\n\nCloses #21\nCloses #27"}]'
w 'repos/o/r/pulls?state=open&head=o:30-menu' '[]'
w 'repos/o/r/issues?state=open&labels=sev:holds' '[{"html_url":"https://x/issues/90","body":"Severity holds.\nGroup: 20-save\nEvidence: x"},{"html_url":"https://x/issues/91","body":"Group: 20-save-x"}]'

out=$(qs --body o/r '21 22,23 24 25 26 28 29') || bad "queue-state exited $?: $out"
printf '%s' "$out" | jq -e . > /dev/null 2>&1 || bad "not JSON: $out"
printf '%s' "$out" | node "$root/plugin/contract/check.js" tracker - > "$tmp/chk" || bad "not a contract tracker: $(cat "$tmp/chk")"
is() { # is <jq test> <why> <jq to print on a failure>
  printf '%s' "$out" | jq -e "$1" > /dev/null 2>&1 || bad "$2: $(printf '%s' "$out" | jq -c "$3" 2>/dev/null)"
}
I() { printf '.issues[] | select(.issue == %s)' "$1"; }
is "$(I 21) | .title == \"Save \\\"the\\\"\\ngame\" and .body == \"Parent: #20\\nBlocked by #19\\nA \\\"quoted\\\" \\\\ line\"" '21: a title and body with a quote, a newline and a backslash survive' "$(I 21) | [.title, .body]"
is "[$(I 21) | .group, .branch, .tier, .blocked_by, (.report == null), .activity_at] == [\"20-save\", \"21-save\", \"bounded\", [19], true, \"2026-10-08T11:05:00Z\"]" '21: group from the existing branch, trusted STARTED, untrusted REPORT ignored' "$(I 21)"
is "$(I 22) | .report == {\"branch\": \"22-load\", \"sha\": \"$B\", \"passed\": true} and .landed == false" '22: a passed report at head is landable' "$(I 22)"
for n in 23 28; do is "$(I $n) | .report == null and (.question | test(\"without passed\"))" "$n: a report without passed at the end is a question" "$(I $n)"; done
is "$(I 29) | .report == null" "29: a REPORT line in another order is not a report" "$(I 29)"
is "$(I 24) | .report == null and .question == \"landing refused: \\\"1 failed\\\"\\nat t.js\"" '24: a later refusal wins, its text verbatim' "$(I 24)"
is "$(I 25) | .landed == true" '25: a report in the group is landed' "$(I 25)"
is "$(I 26) | .branch == \"26-open-the-menu\" and .group == \"30-menu\" and .activity_at == null" '26: a branch with shell characters, a leading - or .. is ignored' "$(I 26)"
is "$(I 27) | .group == \"20-save\"" '27: an issue of the Closes list is read into that group' '.issues | map(.issue)'
is '.groups[] | select(.group == "20-save") | .pr == "https://x/pull/7" and .closes == [21, 27] and .holds == ["https://x/issues/90"]' 'groups: the PR, its Closes list and only the holds of the group' '.groups'
# --group-pr: every issue lands in the head branch of that PR.
w repos/o/r/pulls/7 '{"state":"open","html_url":"https://x/pull/7","head":{"ref":"v5"},"body":"Closes #22"}'
out=$(qs --group-pr 7 o/r '21 26') || bad "--group-pr exited $?"
is '[.issues[].group] == ["v5", "v5", "v5"] and .groups == [{"group": "v5", "pr": "https://x/pull/7", "closes": [22], "holds": []}]' '--group-pr: 1 group for every issue' '.'
# A queue command: the first integer of each line.
out=$(qs o/r "printf '25\n26 x\n'")
is '[.issues[].issue][:2] == [25, 26]' 'a queue command is not read' '[.issues[].issue]'
qs 'o/r;x' 21 > /dev/null 2>&1; [ $? = 2 ] || bad 'a repo with shell characters should exit 2'
# Fail closed: each read that fails exits 1 and names it; none becomes [] or "".
for r in repos/o/r/issues/21 repos/o/r/issues/21/comments repos/o/r/issues/21/dependencies/blocked_by repos/o/r/issues/19 \
  repos/o/r/git/ref/heads/21-save "repos/o/r/commits/$A" 'repos/o/r/pulls?state=open&head=o:20-save' 'repos/o/r/issues?state=open&labels=sev:holds' \
  repos/o/r/git/matching-refs/heads/20-; do
  : > "$(path "$r").fail"
  err=$(qs o/r 21 2>&1 > /dev/null); rc=$?
  rm -f "$(path "$r").fail"
  [ "$rc" = 1 ] && case $err in *"$r"*) true ;; *) false ;; esac || bad "a failed read of $r should exit 1 naming it (exit $rc: $err)"
done
# A missing dependency list is a failed read too (404 is "none" only for a parent, a branch or a compare).
mv "$(path repos/o/r/issues/21/dependencies/blocked_by).json" "$tmp/dep.json"
qs o/r 21 > /dev/null 2>&1; [ $? = 1 ] || bad 'a 404 on blocked_by should exit 1'
mv "$tmp/dep.json" "$(path repos/o/r/issues/21/dependencies/blocked_by).json"
exit "$fail"
