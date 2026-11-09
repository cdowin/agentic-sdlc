#!/bin/sh
# shellcheck disable=SC2015 # A && B || fail: the checks cannot fail after a pass
# tests/land.sh - land lands 2 planted branches into a scratch repo and cleans up, and
# stops on a conflict outside the generated files. gh is the stub in tests/fixtures/land.
# POSIX sh; needs git and jq. Exit 0 when all pass.
root=$(cd "$(dirname "$0")/.." && pwd)
tmp=$(mktemp -d)
tmp=$(cd "$tmp" && pwd -P) # git prints real paths (/private/var on macOS)
trap 'rm -rf "$tmp"' EXIT INT TERM
fail=0
bad() { echo "FAIL $*"; fail=1; }
export GIT_CONFIG_GLOBAL=/dev/null GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@t GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@t
g() { git -C "$tmp/w" "$@"; }
mkdir "$tmp/bin" "$tmp/fx" && cp "$root/tests/fixtures/land/gh" "$tmp/bin/gh"
git init -q --bare -b main "$tmp/remote.git" && git clone -q "$tmp/remote.git" "$tmp/w" 2> /dev/null
mkdir "$tmp/w/src" && echo base > "$tmp/w/src/base" && echo base > "$tmp/w/gen.txt"
g add . && g commit -q -m base && g push -q origin HEAD:main
# 1-a and 2-b each add a source file and regenerate gen.txt, so gen.txt conflicts.
plant() { # <branch> <file> <text> [from]
  g checkout -q -b "$1" "${4:-main}" && echo "$3" > "$tmp/w/src/$2" && cat "$tmp/w"/src/* > "$tmp/w/gen.txt"
  g add . && g commit -q -m "$1" && g push -q origin "$1"
}
plant 1-a a a && plant 2-b b b && g branch -q claude/old main && g push -q origin claude/old
plant claude/live live live && g checkout -q main
g worktree add -q "$tmp/wt-1a" 1-a
land() { (cd "${LD:-$tmp/w}" && PATH="$tmp/bin:$PATH" WL_FX=$tmp/fx WL_REMOTE=$tmp/remote.git WAIT_CI_INTERVAL=0 LAND_REPO=o/r \
  LAND_REGEN="cat gen.txt >> '$tmp/seen'; cat src/* > gen.txt" LAND_GENERATED="${GEN:-gen.txt}" LAND_CHECK="${CHK:-grep -qx b src/b}" \
  sh "${WL:-$root/plugin/bin/land}" "$@"); }
touch "$tmp/fx/noauto" # auto-merge fails, so wait-ci --merge merges the green PR
out=$(land 1-a 2-b 2>&1) || bad "landing 1-a 2-b: exit $?: $out"
heads=$(git -C "$tmp/remote.git" for-each-ref --format='%(refname:short)' refs/heads | tr '\n' ' ')
[ "$heads" = "claude/live main " ] || bad "origin should keep only claude/live and main, has: $heads"
[ "$(git -C "$tmp/remote.git" show main:gen.txt)" = "a
b
base" ] || bad "gen.txt on main is not regenerated: $(git -C "$tmp/remote.git" show main:gen.txt)"
# The regenerate step at the gen.txt conflict sees our side (1-a merged), not 2-b's.
[ "$(head -n 2 "$tmp/seen")" = "a
base" ] || bad "a conflicted gen.txt should keep our side before regen, saw: $(head -n 2 "$tmp/seen")"
[ "$(git -C "$tmp/w" worktree list | wc -l | tr -d " ")" = 1 ] || bad "worktrees left: $(git -C "$tmp/w" worktree list)"
[ -z "$(git -C "$tmp/w" branch --list 1-a 2-b 'land*')" ] || bad "local branches left: $(git -C "$tmp/w" branch)"
grep -qx 'body=Closes #1' "$tmp/fx/pr" && grep -qx 'Closes #2' "$tmp/fx/pr" && grep -qx 'head=land-1-2' "$tmp/fx/pr" ||
  bad "the PR should close #1 and #2 from land-1-2: $(cat "$tmp/fx/pr")"
# 3-c and 4-d change the same source file: the run stops, names it and leaves nothing.
g fetch -q origin && g checkout -q -B main origin/main
plant 3-c base c main && plant 4-d base d main && g checkout -q main
before=$(git -C "$tmp/remote.git" rev-parse main)
out=$(land 3-c 4-d 2>&1) && bad "a conflict in src/base should stop the run"
case $out in *'merge of 4-d conflicts in: src/base'*) ;; *) bad "the stop should name src/base: $out" ;; esac
[ "$(git -C "$tmp/remote.git" rev-parse main)" = "$before" ] && ! git -C "$tmp/remote.git" rev-parse -q --verify land-3-4 > /dev/null &&
  [ "$(git -C "$tmp/w" worktree list | wc -l | tr -d " ")" = 1 ] && [ -z "$(git -C "$tmp/w" branch --list 'land*')" ] ||
  bad "a stopped run should push nothing and leave no worktree or landing branch"
# A queue of 3 landings: landing 2 goes red, so the run stops there with the check named; a rerun resumes
# at landing 2 on its open PR. Landing 3 is a slice of parent 164, so its PR says "Part of #164".
rm "$tmp/fx/noauto" && touch "$tmp/fx/red-w2"
g fetch -q origin && g checkout -q -B main origin/main
plant 5-e e e main && plant 6-f f f main && plant 164-g g g main && plant 9-h h h main && g checkout -q main
printf '%s\n' '# tonight' 5-e '--branch w2 6-f' '--part-of 164 164-g 9-h' > "$tmp/q"
# shellcheck disable=SC2010  # counts fixture names, plain names
prs() { ls "$tmp/fx" | grep -c '^pr-'; }
n0=$(prs)
out=$(land --queue "$tmp/q" 2>&1) && bad "a red landing 2 should stop the queue"
case $out in *'red: lint FAILURE'*'queue stopped at line 3 (--branch w2 6-f)'*) ;; *) bad "the stop should name lint and line 3: $out" ;; esac
[ "$(cat "$tmp/q.landed")" = 5-e ] && [ "$(prs)" = $((n0 + 2)) ] || bad "only landing 1 should land and landing 3 should not start: $(cat "$tmp/q.landed")"
rm "$tmp/fx/red-w2"
out=$(land --queue "$tmp/q" 2>&1) || bad "the rerun should land landings 2 and 3: $out"
case $out in *'line 2 already landed'*'pushed w2 to the open PR'*'queue done, 2 line(s) landed'*) ;; *) bad "the rerun should resume at landing 2: $out" ;; esac
[ "$(prs)" = $((n0 + 3)) ] || bad "the rerun should reuse the PR of w2"
grep -qx 'body=Closes #9' "$tmp/fx/pr" && grep -qx 'Part of #164' "$tmp/fx/pr" && ! grep -q 'Closes #164' "$tmp/fx/pr" ||
  bad "a slice of parent 164 should write Part of #164: $(cat "$tmp/fx/pr")"
# The base moves after the PR opens: the PR is BEHIND with auto-merge set. land merges the base,
# regenerates gen.txt (src/m arrives without it), pushes and waits; auto-merge then lands it.
cat > "$tmp/fx/on-open" << EOF
rm -f "$tmp/fx/on-open"
{ git clone -q "$tmp/remote.git" "$tmp/c" && echo m > "$tmp/c/src/m" && git -C "$tmp/c" add . &&
  git -C "$tmp/c" commit -q -m m && git -C "$tmp/c" push -q origin HEAD:main; } > /dev/null 2>&1
EOF
g fetch -q origin && g checkout -q -B main origin/main && plant 10-j j j main && g checkout -q main
out=$(land 10-j 2>&1) || bad "a BEHIND PR with auto-merge should be updated and land: $out"
case $out in *'merged main into land-10'*) ;; *) bad "land should merge main into the BEHIND landing: $out" ;; esac
git -C "$tmp/remote.git" show main:gen.txt | grep -qx m || bad "gen.txt should be regenerated after the base merge"
fresh() { g fetch -q origin && g checkout -q -B main origin/main; }
heads() { git -C "$tmp/remote.git" for-each-ref --format='%(refname:short)' refs/heads | tr '\n' ' '; }
# Landing from the issue worktree it removes: both worktrees and the branches go, and it exits 0.
fresh && plant 13-m k13 m main && g checkout -q main && g worktree add -q "$tmp/wt-13m" 13-m
out=$(LD=$tmp/wt-13m land 13-m 2>&1) || bad "landing from the issue worktree: exit $?: $out"
[ ! -d "$tmp/wt-13m" ] && [ ! -d "$tmp/w-land" ] && [ "$(g worktree list | wc -l | tr -d ' ')" = 1 ] &&
  [ -z "$(g branch --list 13-m 'land*')" ] && ! heads | grep -q '13-m\|land-13' || bad "a landing from the issue worktree should clean up: $(g worktree list) $(heads)"
# Cross-repo and same-repo parents: each is written as given, and the issue-link check accepts the body.
fresh && plant 14-n k14 n main && plant 16-p k16 p main && g checkout -q main
out=$(land --part-of org/hub#5 --part-of '#16' 14-n 16-p 2>&1) || bad "--part-of forms should land: $out"
body=$(sed -n '/^body=/,$p' "$tmp/fx/pr" | sed 's/^body=//')
for want in 'Closes #14' 'Part of #16' 'Part of org/hub#5'; do
  printf '%s\n' "$body" | grep -qx "$want" || bad "the PR body should hold '$want': $body"
done
(cd "$root" && BODY="$body" CHECKS=issue-link sh checks/checks.sh > /dev/null 2>&1) || bad "the issue-link check should pass on: $body"
BODY='Part of org/hub#5' CHECKS=issue-link sh "$root/checks/checks.sh" > /dev/null 2>&1 || bad "issue-link rejects Part of org/hub#5"
# A generated pattern is matched unexpanded: dist/** must match a new dist/c.txt even though dist/ exists.
fresh && mkdir -p "$tmp/w/dist" && echo x > "$tmp/w/dist/base.txt" && g add . && g commit -q -m dist && g push -q origin HEAD:main
mkb() { g checkout -q -b "$1" main && echo "$2" > "$tmp/w/dist/c.txt" && g add . && g commit -q -m "$1" && g push -q origin "$1"; }
mkb 18-r r && mkb 19-s s && g checkout -q main
out=$(GEN='dist/**' CHK=true land 18-r 19-s 2>&1) || bad "a dist/** conflict in dist/c.txt should count as generated: $out"
# The landing worktree sits beside the main checkout, and under LAND_WORKDIR when set; the v4 name
# WAVE_LAND_WORKDIR still works for 1 release and prints a deprecation line.
fresh && plant 20-t k20 t main && plant 21-u k21 u main && plant 90-q k90 q main && g checkout -q main
CHK="pwd > '$tmp/pwd'" land 20-t > /dev/null 2>&1 || bad "landing 20-t"
[ "$(cat "$tmp/pwd")" = "$tmp/w-land/land-20" ] || bad "the landing worktree should be beside the checkout: $(cat "$tmp/pwd")"
LAND_WORKDIR=$tmp/wd CHK="pwd > '$tmp/pwd'" land 21-u > /dev/null 2>&1 || bad "landing 21-u with LAND_WORKDIR"
[ "$(cat "$tmp/pwd")" = "$tmp/wd/land-21" ] || bad "LAND_WORKDIR should hold the landing worktree: $(cat "$tmp/pwd")"
unset LAND_WORKDIR # sh keeps an assignment made before a function call
out=$(WAVE_LAND_WORKDIR=$tmp/wd CHK="pwd > '$tmp/pwd'" land 90-q 2>&1) || bad "landing 90-q with WAVE_LAND_WORKDIR: $out"
[ "$(cat "$tmp/pwd")" = "$tmp/wd/land-90" ] || bad "WAVE_LAND_WORKDIR should still hold the landing worktree: $(cat "$tmp/pwd")"
case $out in *'WAVE_LAND_WORKDIR is deprecated; use LAND_WORKDIR'*) ;; *) bad "WAVE_LAND_WORKDIR should print a deprecation line: $out" ;; esac
# A merge call that fails while auto-merge lands the PR a moment later: land waits, prints a
# progress line while CI is read, cleans up only after MERGED, then runs review-due beside it.
fresh && plant 22-v k22 v main && g checkout -q main
mkdir "$tmp/rd" && cp "$root/plugin/bin/land" "$root/plugin/bin/wait-ci" "$tmp/rd/"
printf '#!/bin/sh\necho "review-due $*"\n' > "$tmp/rd/review-due" && chmod +x "$tmp/rd/review-due"
touch "$tmp/fx/noauto" "$tmp/fx/late" "$tmp/fx/slow"
out=$(WL=$tmp/rd/land LAND_BEAT=1 land 22-v 2>&1) || bad "a late merge should still land: $out"
rm -f "$tmp/fx/noauto"
case $out in *'still waiting on o/r#'*'merged after MERGE_FAILED'*'deleted branch 22-v'*'review-due o/r main'*) ;; *) bad "heartbeat, late merge, cleanup and review-due expected: $out" ;; esac
# A failing cleanup step is named, the rest still runs, and the exit is 1.
fresh && plant 23-w k23 w main && g checkout -q main
git -C "$tmp/remote.git" config receive.denyDeletes true
out=$(land 23-w 2>&1) && bad "a refused origin delete should exit non-zero"
git -C "$tmp/remote.git" config --unset receive.denyDeletes
case $out in *'cleanup failed: origin/23-w'*) ;; *) bad "the failed cleanup should be named: $out" ;; esac
[ -z "$(g branch --list 23-w 'land*')" ] && [ "$(g worktree list | wc -l | tr -d ' ')" = 1 ] || bad "the other cleanup steps should still run"
# --wave is a deprecated alias of --branch: it works, names the replacement, and --branch prints no such line.
fresh && plant 24-x k24 x main && g checkout -q main
out=$(land --wave old-name 24-x 2>&1) || bad "--wave should still land: $out"
case $out in *'--wave is deprecated; use --branch'*) ;; *) bad "--wave should print a deprecation line: $out" ;; esac
fresh && plant 25-y k25 y main && g checkout -q main
out=$(land --branch new-name 25-y 2>&1) || bad "--branch should land: $out"
case $out in *deprecated*) bad "--branch should print no deprecation line: $out" ;; esac
exit $fail
