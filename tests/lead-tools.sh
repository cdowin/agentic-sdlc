#!/bin/sh
# tests/lead-tools.sh - the self-test of plugin/bin/cloud-worker and plugin/bin/wait-reports.
# LEAD_SH is the shell that runs each tool (default sh): run.sh passes sh, bash and
# `zsh --emulate sh` when present. A dry-run worker launches against a local bare origin, a planted
# report is found, and a planted stale branch fires the stall alarm. Prints FAIL lines; exit 0 when all pass.
# shellcheck disable=SC2015,SC2016 # ok() cannot fail, so A && ok || bad is safe; backticks are literal
set -u
root=$(cd "$(dirname "$0")/.." && pwd)
bin=$root/plugin/bin
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
trap 'exit 1' INT TERM
export GIT_CONFIG_GLOBAL=/dev/null # a user push.negotiate breaks a push to a local bare repo
# The caller's CLOUD_WORKER_* never reach a tool: each case sets its own, and none starts a real session.
for v in $(env | sed -n 's/^\(CLOUD_WORKER_[A-Za-z0-9_]*\)=.*/\1/p'); do unset "$v"; done
fail=0
ok() { :; }
bad() { fail=$((fail + 1)); printf 'FAIL [%s] %s\n' "${LEAD_SH:-sh}" "$*"; }
# shellcheck disable=SC2086 # LEAD_SH may hold flags
run() { t=$1; shift; exec ${LEAD_SH:-sh} "$bin/$t" "$@"; } # call it in a subshell

# cloud-worker: a clone of a bare origin; the gate holds characters sed and awk would mangle.
git init -q --bare "$tmp/origin.git"
git init -q "$tmp/w" && git -C "$tmp/w" -c user.name=t -c user.email=t@t commit -q --allow-empty -m base
git -C "$tmp/w" remote add origin "$tmp/origin.git" && git -C "$tmp/w" push -q origin HEAD:refs/heads/main
base=$(git -C "$tmp/w" rev-parse HEAD)
printf 'Fix the save menu.\n' > "$tmp/brief.txt"
gate='make test && echo "a|b" & \1 /x/'
out=$(cd "$tmp/w" && run cloud-worker --dry-run --gate "$gate" --gate 'sh tests/run.sh' 'o/r#7' 7-save main "$tmp/brief.txt" 2>&1)
case $out in
  "dry-run: would push $base to origin 7-save"*'Fix the save menu.'*'Repo o/r, issue #7, branch `7-save` (pushed, cut from '"$base"*'`WORKER STARTED branch=7-save session='*"- \`$gate\`
- \`sh tests/run.sh\`"*'`WORKER REPORT branch=7-save head=<sha>`'*'**Done when**'*'`WORKER BLOCKED branch=7-save`'*'`timeout 900 <cmd>`'*'naming the command that hung'*) ok ;;
  *) bad "cloud-worker --dry-run: wanted the push line, the brief and the filled tail, got: $out" ;;
esac
case $out in *@[A-Z]*@*) bad "cloud-worker --dry-run: a placeholder is left: $out" ;; esac
[ -z "$(git -C "$tmp/origin.git" for-each-ref refs/heads/7-save)" ] && ok || bad 'cloud-worker --dry-run pushed a branch'
(cd "$tmp/w" && run cloud-worker 'o/r#7' 7-save main "$tmp/brief.txt" > /dev/null 2>&1); [ "$?" = 2 ] && ok ||
  bad 'cloud-worker: no CLOUD_WORKER_START and no --dry-run should exit 2'
# cw <start command> <args>: cloud-worker in the clone, with a stub gh that logs each argument to $tmp/gh.log.
mkdir "$tmp/cwbin" && printf '#!/bin/sh\nprintf "%%s\\n" "$@" >> "%s/gh.log"\n' "$tmp" > "$tmp/cwbin/gh" && chmod +x "$tmp/cwbin/gh"
printf 'cat > "%s/prompt.txt"; echo "session at https://example.test/s/1"\n' "$tmp" > "$tmp/start-ok"
printf 'cat > /dev/null; echo "started in the background"\n' > "$tmp/start-nourl"
# shellcheck disable=SC2030 # PATH holds the stub gh in this subshell only
cw() { (cd "$tmp/w" && PATH=$tmp/cwbin:$PATH CLOUD_WORKER_START=$1 && export PATH CLOUD_WORKER_START && shift && run cloud-worker "$@"); }
cw "sh $tmp/start-ok" --gate "$gate" 'o/r#7' 7-save main "$tmp/brief.txt" > /dev/null 2>&1 &&
  [ "$(git -C "$tmp/origin.git" rev-parse refs/heads/7-save)" = "$base" ] &&
  grep -qF "Push after every commit to \`7-save\`" "$tmp/prompt.txt" && ok ||
  bad "cloud-worker: should push 7-save at the base and pipe the prompt to CLOUD_WORKER_START"
grep -qx 'WORKER LAUNCHED branch=7-save session=https://example.test/s/1' "$tmp/gh.log" && grep -qx 'o/r' "$tmp/gh.log" && ok ||
  bad "cloud-worker: should post WORKER LAUNCHED with the session URL on o/r#7, gh got: $(cat "$tmp/gh.log" 2> /dev/null)"
# A start is real only when CLOUD_WORKER_START prints a session URL: a failed or URL-less start exits 1 and posts nothing (#406).
rm -f "$tmp/gh.log"
for st in false "sh $tmp/start-nourl"; do
  out=$(cw "$st" 'o/r#7' 7-save main "$tmp/brief.txt" 2>&1); rc=$?
  [ "$rc" = 1 ] && [ ! -e "$tmp/gh.log" ] && case $out in *'no worker started'*) ;; *) false ;; esac && ok ||
    bad "cloud-worker: start '$st' should exit 1 with no worker started and post nothing, got $rc: $out"
done

# wait-reports: the stub gh reads $WR_FX/<api path with / as _>.json.
fx=$tmp/fx && mkdir "$fx" "$tmp/ghbin" && cp "$root/tests/fixtures/wait-reports/gh" "$tmp/ghbin/gh"
now=$(date -u +%Y-%m-%dT%H:%M:%SZ)
issue() { printf '{"state":"%s","created_at":"2000-01-01T00:00:00Z"}' "$2" > "$fx/repos_o_r_issues_$1.json"; }
commit() { printf '{"sha":"%s","commit":{"committer":{"date":"%s"}}}' "$2" "$3" > "$fx/repos_o_r_commits_$1.json"; }
issue 7 open; issue 8 open; issue 9 open; issue 10 closed
printf '[{"id":1,"created_at":"2000-01-01T00:00:00Z","html_url":"u1","body":"claim"},{"id":2,"created_at":"%s","html_url":"u2","body":"WORKER REPORT head abc"}]' "$now" > "$fx/repos_o_r_issues_7_comments.json"
printf '{"body":"WORKER REPORT head abc"}' > "$fx/repos_o_r_issues_comments_2.json"
for n in 8 9 10; do echo '[]' > "$fx/repos_o_r_issues_${n}_comments.json"; done
commit old s8 2000-01-01T00:00:00Z; commit fresh s9 "$now"
printf '{"default_branch":"main"}' > "$fx/repos_o_r.json"; printf '{"ahead_by":3}' > "$fx/repos_o_r_compare_main...s8.json"
# wr runs wait-reports with a 20 s watchdog, so a missed event fails the test instead of hanging it.
wr() {
  (
    # shellcheck disable=SC2031 # each subshell sets its own PATH
    PATH=$tmp/ghbin:$PATH WR_FX=$fx WAIT_REPORTS_SEEN=${WR_SEEN:-$tmp/seen} WAIT_REPORTS_INTERVAL=0
    export PATH WR_FX WAIT_REPORTS_SEEN WAIT_REPORTS_INTERVAL
    run wait-reports "$@"
  ) &
  p=$!
  (sleep 20; kill "$p") > /dev/null 2>&1 &
  w=$!
  wait "$p"; rc=$?
  kill "$w" 2> /dev/null
  return "$rc"
}
out=$(wr 'o/r#7' 2>&1)
[ "$out" = "o/r#7: REPORT u2
WORKER REPORT head abc" ] && ok || bad "wait-reports: should print the planted report, got: $out"
out=$(wr 'o/r#7' 'o/r#8@old' 'o/r#9@fresh' 2>&1)
case $out in
  'o/r#8: STALL silent '*' min, no report (branch old at s8)') ok ;;
  *) bad "wait-reports: only the stale branch should fire, got: $out" ;;
esac
out=$(wr --status 'o/r#7' 'o/r#8@old' 'o/r#9@fresh' 'o/r#10' 2>&1)
case $out in
  'o/r#7: reported 0 min ago
o/r#8: silent '*' min, branch old ahead 3
o/r#9: silent 0 min, branch fresh ahead ?
o/r#10: closed') ok ;;
  *) bad "wait-reports --status: got: $out" ;;
esac
out=$(wr 'o/r#10' 'o/r#7' 2>&1)
[ "$out" = "o/r#10: CLOSED" ] && ok || bad "wait-reports: a closed issue is an event once, got: $out"
wr > /dev/null 2>&1; [ "$?" = 2 ] && ok || bad 'wait-reports: no args should exit 2'
wr 'o/r#7x' > /dev/null 2>&1; [ "$?" = 2 ] && ok || bad 'wait-reports: a bad issue spec should exit 2'

# Two workers on 1 issue: each @branch watcher wakes only on the report whose first line names its branch.
issue 11 open
printf '[{"id":4,"created_at":"%s","html_url":"u4","body":"WORKER REPORT branch=11-a head=sa\\nfiles"},{"id":5,"created_at":"%s","html_url":"u5","body":"WORKER REPORT branch=11-b head=sb"}]' "$now" "$now" > "$fx/repos_o_r_issues_11_comments.json"
printf '{"body":"WORKER REPORT branch=11-a head=sa"}' > "$fx/repos_o_r_issues_comments_4.json"
printf '{"body":"WORKER REPORT branch=11-b head=sb"}' > "$fx/repos_o_r_issues_comments_5.json"
commit 11-a sa "$now"; commit 11-b sb "$now"; commit 11-c sc "$now"
out=$(wr 'o/r#11@11-a' 2>&1)
[ "$out" = "o/r#11: REPORT u4
WORKER REPORT branch=11-a head=sa" ] && ok || bad "wait-reports @branch: should print only its own report, got: $out"
out=$(wr 'o/r#11@11-a' 'o/r#11@11-b' 2>&1)
[ "$out" = "o/r#11: REPORT u5
WORKER REPORT branch=11-b head=sb" ] && ok || bad "wait-reports @branch: a restarted watcher should print the other branch's report once, got: $out"
out=$(wr --status 'o/r#11@11-a' 'o/r#11@11-c' 2>&1)
case $out in
  'o/r#11: reported 0 min ago, branch 11-a ahead ?
o/r#11: silent 0 min, branch 11-c ahead ?') ok ;;
  *) bad "wait-reports --status: should read per branch, got: $out" ;;
esac
out=$(wr 'o/r#11@nope' 2>&1); rc=$?
[ "$rc" = 2 ] && [ "$out" = "wait-reports: no such branch 'nope' on o/r" ] && ok || bad "wait-reports: a missing branch should exit 2, got $rc: $out"
out=$(wr --status 'o/r#11@nope' 2>&1); rc=$?
[ "$rc" = 2 ] && [ "$out" = "wait-reports: no such branch 'nope' on o/r" ] && ok || bad "wait-reports --status: a missing branch should exit 2, got $rc: $out"
# A report with no branch= (an older tail) counts by its **Branch** line (a), or for the only watched branch (b) (#397).
issue 15 open; issue 16 open
printf '[{"id":6,"created_at":"%s","html_url":"u6","body":"WORKER REPORT head s15\\n**Branch** `15-a`"}]' "$now" > "$fx/repos_o_r_issues_15_comments.json"
printf '{"body":"WORKER REPORT head s15"}' > "$fx/repos_o_r_issues_comments_6.json"
printf '[{"id":7,"created_at":"%s","html_url":"u7","body":"WORKER REPORT head s16"}]' "$now" > "$fx/repos_o_r_issues_16_comments.json"
printf '{"body":"WORKER REPORT head s16"}' > "$fx/repos_o_r_issues_comments_7.json"
commit 15-a s15 "$now"; commit 15-b s15 "$now"; commit 16-a s16 "$now"; commit 16-b s16 "$now"
out=$(wr --status 'o/r#15@15-a' 'o/r#15@15-b' 'o/r#16@16-a' 'o/r#16@16-b' 2>&1)
case $out in
  'o/r#15: reported 0 min ago, branch 15-a ahead ?
o/r#15: silent 0 min, branch 15-b ahead ?
o/r#16: silent 0 min, branch 16-a ahead ?
o/r#16: silent 0 min, branch 16-b ahead ?') ok ;;
  *) bad "wait-reports @branch: a **Branch** line names the branch; 2 watched branches ignore a bare report, got: $out" ;;
esac
out=$(wr 'o/r#16@16-a' 2>&1)
[ "$out" = "o/r#16: REPORT u7
WORKER REPORT head s16" ] && ok || bad "wait-reports @branch: the only watched branch counts a bare report, got: $out"
# A relaunch on a branch whose last commit is old: silence counts from the WORKER LAUNCHED comment (#400).
issue 12 open; issue 13 closed; echo '[]' > "$fx/repos_o_r_issues_13_comments.json"; commit 12-r s12 2000-01-01T00:00:00Z
printf '[{"id":8,"created_at":"%s","html_url":"u8","body":"WORKER LAUNCHED branch=12-r"}]' "$now" > "$fx/repos_o_r_issues_12_comments.json"
out=$(WR_SEEN=$tmp/seen12 wr 'o/r#13' 'o/r#12@12-r' 2>&1)
[ "$out" = "o/r#13: CLOSED" ] && ok || bad "wait-reports: a fresh relaunch should not stall, got: $out"
printf '[{"id":8,"created_at":"%s","html_url":"u8","body":"WORKER LAUNCHED branch=12-other"}]' "$now" > "$fx/repos_o_r_issues_12_comments.json"
out=$(WR_SEEN=$tmp/seen12b wr 'o/r#13' 'o/r#12@12-r' 2>&1)
case $out in
  *'o/r#12: STALL silent '*) ok ;;
  *) bad "wait-reports: a launch of another branch should not re-arm 12-r, got: $out" ;;
esac
# A launch with no WORKER STARTED, report or newer commit within WAIT_REPORTS_START fires NOT-STARTED once (#406).
issue 14 open; commit 14-n s14 1999-12-31T00:00:00Z
printf '[{"id":9,"created_at":"2000-01-01T00:00:00Z","html_url":"u9","body":"WORKER LAUNCHED branch=14-n session=https://example.test/s/2"}]' > "$fx/repos_o_r_issues_14_comments.json"
out=$(WR_SEEN=$tmp/seen14 wr 'o/r#14@14-n' 2>&1)
case $out in
  'o/r#14: NOT-STARTED launched '*' min ago, no WORKER STARTED and no commit on 14-n since') ok ;;
  *) bad "wait-reports: a launch with no sign of life should fire NOT-STARTED, got: $out" ;;
esac
out=$(wr --status 'o/r#14@14-n' 2>&1)
case $out in 'o/r#14: not started '*' min, branch 14-n ahead ?') ok ;; *) bad "wait-reports --status: should read not started, got: $out" ;; esac
printf '[{"id":9,"created_at":"%s","html_url":"u9","body":"WORKER LAUNCHED branch=14-n"},{"id":10,"created_at":"%s","html_url":"u10","body":"WORKER STARTED branch=14-n session=unknown"}]' "$now" "$now" > "$fx/repos_o_r_issues_14_comments.json"
out=$(WR_SEEN=$tmp/seen14b WAIT_REPORTS_START=0 wr 'o/r#13' 'o/r#14@14-n' 2>&1)
[ "$out" = "o/r#13: CLOSED" ] && ok || bad "wait-reports: a WORKER STARTED comment means started, got: $out"
# A failed branch lookup (gh prints its 422 JSON on stdout) is no branch activity, never a timestamp (#376).
out=$(wr --status 'o/r#10@nope' 2>&1); rc=$?
[ "$rc" = 0 ] && [ "$out" = "o/r#10: closed, branch nope ahead ?" ] && ok || bad "wait-reports --status: a missing branch on a closed issue, got $rc: $out"
[ "$fail" = 0 ]
