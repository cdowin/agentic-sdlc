#!/bin/sh
# tests/queue-state.sh - plugin/bin/queue-state reads the tracker by fixed rules: only trusted WORKER lines with a
# safe branch count, a report lands only with passed and at head, a later BLOCKED (a refused landing) wins, groups
# are stable, and the group PR's Closes list and the open holds findings are read. The stub gh of wait-reports
# reads $WR_FX/<api path with / as _>.json. Needs jq (the stub). Prints FAIL lines; exit 0 when all pass.
# shellcheck disable=SC2015,SC2016 # ok() cannot fail; $(id) is a literal in a fixture
set -u
root=$(cd "$(dirname "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
trap 'exit 1' INT TERM
fail=0
bad() { fail=$((fail + 1)); printf 'FAIL %s\n' "$*"; }
fx=$tmp/fx && mkdir "$fx" "$tmp/bin" && cp "$root/tests/fixtures/wait-reports/gh" "$tmp/bin/gh"
w() { printf '%s\n' "$2" > "$fx/$(printf '%s' "$1" | tr / _).json"; }
A=$(printf 'a%.0s' 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40)
B=$(printf '%s' "$A" | tr a b) C=$(printf '%s' "$A" | tr a c)
iss() { w "repos/o/r/issues/$1" "{\"state\":\"open\",\"title\":\"$2\",\"labels\":[$3],\"body\":\"$4\"}"; }
com() { # com <author_association> <time> <body>
  printf '{"author_association":"%s","created_at":"%s","body":"%s"}' "$1" "$2" "$3"
}
iss 20 'Save System, Rework!' '' ''
iss 19 'Old blocker' '' ''
iss 30 'Menu' '' ''
w repos/o/r/git/matching-refs/heads/20- '[{"ref":"refs/heads/20-save"}]'
w repos/o/r/git/matching-refs/heads/30- '[]'
# 21: a trusted STARTED; an untrusted passed REPORT is ignored.
iss 21 'Save the game' '{"name":"tier:bounded"}' 'Parent: #20\nBlocked by #19'
w repos/o/r/issues/21/comments "[$(com COLLABORATOR 2026-10-08T11:00:00Z 'WORKER STARTED branch=21-save session=x'),$(com NONE 2026-10-08T11:10:00Z "WORKER REPORT branch=21-save head=$A passed")]"
w repos/o/r/git/ref/heads/21-save "{\"object\":{\"sha\":\"$A\"}}"
w "repos/o/r/commits/$A" '{"commit":{"committer":{"date":"2026-10-08T11:05:00Z"}}}'
# 22: a passed REPORT at head, not yet in the group.
iss 22 'Load the game' '' 'Parent: #20'
w repos/o/r/issues/22/comments "[$(com MEMBER 2026-10-08T11:00:00Z "WORKER REPORT branch=22-load head=$B passed")]"
w repos/o/r/git/ref/heads/22-load "{\"object\":{\"sha\":\"$B\"}}"
w "repos/o/r/compare/20-save...$B" '{"status":"ahead"}'
# 23: a REPORT without passed is a question.
iss 23 'Delete a save' '' 'Parent: #20'
w repos/o/r/issues/23/comments "[$(com OWNER 2026-10-08T11:00:00Z "WORKER REPORT branch=23-del head=$C")]"
w repos/o/r/git/ref/heads/23-del "{\"object\":{\"sha\":\"$C\"}}"
# 24: a passed REPORT, then the lander's refusal: the refusal wins.
iss 24 'Copy a save' '' 'Parent: #20'
w repos/o/r/issues/24/comments "[$(com MEMBER 2026-10-08T11:00:00Z "WORKER REPORT branch=24-copy head=$C passed"),$(com MEMBER 2026-10-08T11:30:00Z 'WORKER BLOCKED branch=24-copy\nlanding refused: 1 failed')]"
w repos/o/r/git/ref/heads/24-copy "{\"object\":{\"sha\":\"$C\"}}"
w "repos/o/r/compare/20-save...$C" '{"status":"diverged"}'
# 25: a passed REPORT already in the group: landed.
iss 25 'Name a save' '' 'Parent: #20'
w repos/o/r/issues/25/comments "[$(com MEMBER 2026-10-08T11:00:00Z "WORKER REPORT branch=25-name head=$A passed")]"
w repos/o/r/git/ref/heads/25-name "{\"object\":{\"sha\":\"$A\"}}"
w "repos/o/r/compare/20-save...$A" '{"status":"behind"}'
# 26: a branch with shell characters is ignored, so the branch is the default.
iss 26 'Open the menu' '' 'Parent: #30'
w repos/o/r/issues/26/comments "[$(com MEMBER 2026-10-08T11:00:00Z 'WORKER STARTED branch=x;rm$(id) session=y')]"
# 27: only in the PR's Closes list.
iss 27 'Export a save' '' 'Parent: #20'
w repos/o/r/issues/27/comments '[]'
w 'repos/o/r/pulls?state=open&head=o:20-save' '[{"html_url":"https://x/pull/7","body":"Refs #20\n\nCloses #21\nCloses #27"}]'
w 'repos/o/r/pulls?state=open&head=o:30-menu' '[]'
w 'repos/o/r/issues?state=open&labels=sev:holds' '[{"html_url":"https://x/issues/90","body":"Severity holds.\nGroup: 20-save\nEvidence: x"},{"html_url":"https://x/issues/91","body":"Group: 20-save-x"}]'

out=$(PATH=$tmp/bin:$PATH WR_FX=$fx sh "$root/plugin/bin/queue-state" o/r '21 22,23 24 25 26') || bad "queue-state exited $?: $out"
printf '%s' "$out" | jq -e . > /dev/null 2>&1 || bad "not JSON: $out"
printf '%s' "$out" | node "$root/plugin/contract/check.js" tracker - > "$tmp/chk" || bad "not a contract tracker: $(cat "$tmp/chk")"
printf '%s' "$out" | node "$root/plugin/contract/check.js" tracker - > "$tmp/chk" || bad "not a contract tracker: $(cat "$tmp/chk")"
is() { # is <jq test> <why>
  printf '%s' "$out" | jq -e "$1" > /dev/null 2>&1 || bad "$2: $(printf '%s' "$out" | jq -c "$3" 2>/dev/null)"
}
I() { printf '.issues[] | select(.issue == %s)' "$1"; }
is "[$(I 21) | .group, .branch, .tier, .blocked_by, (.report == null), .activity_at] == [\"20-save\", \"21-save\", \"bounded\", [19], true, \"2026-10-08T11:05:00Z\"]" '21: group from the existing branch, trusted STARTED, untrusted REPORT ignored' "$(I 21)"
is "$(I 22) | .report == {\"branch\": \"22-load\", \"sha\": \"$B\", \"passed\": true} and .landed == false" '22: a passed report at head is landable' "$(I 22)"
is "$(I 23) | .report == null and (.question | test(\"without passed\"))" '23: a report without passed is not landable' "$(I 23)"
is "$(I 24) | .report == null and .question == \"landing refused: 1 failed\"" '24: a later refusal wins over the report' "$(I 24)"
is "$(I 25) | .landed == true" '25: a report in the group is landed' "$(I 25)"
is "$(I 26) | .branch == \"26-open-the-menu\" and .group == \"30-menu\" and .activity_at == null" '26: a branch with shell characters is ignored' "$(I 26)"
is "$(I 27) | .group == \"20-save\"" '27: an issue of the Closes list is read into that group' '.issues | map(.issue)'
is '.groups[] | select(.group == "20-save") | .pr == "https://x/pull/7" and .closes == [21, 27] and .holds == ["https://x/issues/90"]' 'groups: the PR, its Closes list and only the holds of the group' '.groups'
# --group-pr: every issue lands in the head branch of that PR.
w repos/o/r/pulls/7 '{"state":"open","html_url":"https://x/pull/7","head":{"ref":"v5"},"body":"Closes #22"}'
out=$(PATH=$tmp/bin:$PATH WR_FX=$fx sh "$root/plugin/bin/queue-state" --group-pr 7 o/r '21 26')
is '[.issues[].group] == ["v5", "v5", "v5"] and .groups == [{"group": "v5", "pr": "https://x/pull/7", "closes": [22], "holds": []}]' '--group-pr: 1 group for every issue' '.'
# A queue command: the first integer of each line.
out=$(PATH=$tmp/bin:$PATH WR_FX=$fx sh "$root/plugin/bin/queue-state" o/r "printf '25\n26 x\n'")
is '[.issues[].issue][:2] == [25, 26]' 'a queue command is not read' '[.issues[].issue]'
sh "$root/plugin/bin/queue-state" 'o/r;x' 21 > /dev/null 2>&1; [ $? = 2 ] || bad 'a repo with shell characters should exit 2'
exit "$fail"
