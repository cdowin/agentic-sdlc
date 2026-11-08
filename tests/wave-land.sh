#!/bin/sh
# shellcheck disable=SC2015 # A && B || fail: the checks cannot fail after a pass
# tests/wave-land.sh - wave-land lands 2 planted branches into a scratch repo and cleans up, and
# stops on a conflict outside the generated files. gh is the stub in tests/fixtures/wave-land.
# POSIX sh; needs git and jq. Exit 0 when all pass.
root=$(cd "$(dirname "$0")/.." && pwd)
tmp=$(mktemp -d)
tmp=$(cd "$tmp" && pwd -P) # git prints real paths (/private/var on macOS)
trap 'rm -rf "$tmp"' EXIT INT TERM
fail=0
bad() { echo "FAIL $*"; fail=1; }
export GIT_CONFIG_GLOBAL=/dev/null GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@t GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@t
g() { git -C "$tmp/w" "$@"; }
mkdir "$tmp/bin" "$tmp/fx" && cp "$root/tests/fixtures/wave-land/gh" "$tmp/bin/gh"
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
land() { (cd "$tmp/w" && PATH="$tmp/bin:$PATH" WL_FX=$tmp/fx WL_REMOTE=$tmp/remote.git WAIT_CI_INTERVAL=0 WAVE_LAND_REPO=o/r \
  WAVE_LAND_REGEN="cat gen.txt >> '$tmp/seen'; cat src/* > gen.txt" WAVE_LAND_GENERATED='gen.txt' WAVE_LAND_CHECK='grep -qx b src/b' \
  sh "$root/plugin/bin/wave-land" "$@"); }
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
[ -z "$(git -C "$tmp/w" branch --list 1-a 2-b 'wave*')" ] || bad "local branches left: $(git -C "$tmp/w" branch)"
grep -qx 'body=Closes #1' "$tmp/fx/pr" && grep -qx 'Closes #2' "$tmp/fx/pr" && grep -qx 'head=wave-1-2' "$tmp/fx/pr" ||
  bad "the PR should close #1 and #2 from wave-1-2: $(cat "$tmp/fx/pr")"
# 3-c and 4-d change the same source file: the run stops, names it and leaves nothing.
g fetch -q origin && g checkout -q -B main origin/main
plant 3-c base c main && plant 4-d base d main && g checkout -q main
before=$(git -C "$tmp/remote.git" rev-parse main)
out=$(land 3-c 4-d 2>&1) && bad "a conflict in src/base should stop the run"
case $out in *'merge of 4-d conflicts in: src/base'*) ;; *) bad "the stop should name src/base: $out" ;; esac
[ "$(git -C "$tmp/remote.git" rev-parse main)" = "$before" ] && ! git -C "$tmp/remote.git" rev-parse -q --verify wave-3-4 > /dev/null &&
  [ "$(git -C "$tmp/w" worktree list | wc -l | tr -d " ")" = 1 ] && [ -z "$(git -C "$tmp/w" branch --list 'wave*')" ] ||
  bad "a stopped run should push nothing and leave no worktree or wave branch"
# A queue of 3 waves: wave 2 goes red, so the run stops there with the check named; a rerun resumes
# at wave 2 on its open PR. Wave 3 is a slice of parent 164, so its PR says "Part of #164".
rm "$tmp/fx/noauto" && touch "$tmp/fx/red-w2"
g fetch -q origin && g checkout -q -B main origin/main
plant 5-e e e main && plant 6-f f f main && plant 164-g g g main && plant 9-h h h main && g checkout -q main
printf '%s\n' '# tonight' 5-e '--wave w2 6-f' '--part-of 164 164-g 9-h' > "$tmp/q"
# shellcheck disable=SC2010  # counts fixture names, plain names
prs() { ls "$tmp/fx" | grep -c '^pr-'; }
n0=$(prs)
out=$(land --queue "$tmp/q" 2>&1) && bad "a red wave 2 should stop the queue"
case $out in *'red: lint FAILURE'*'queue stopped at line 3 (--wave w2 6-f)'*) ;; *) bad "the stop should name lint and line 3: $out" ;; esac
[ "$(cat "$tmp/q.landed")" = 5-e ] && [ "$(prs)" = $((n0 + 2)) ] || bad "only wave 1 should land and wave 3 should not start: $(cat "$tmp/q.landed")"
rm "$tmp/fx/red-w2"
out=$(land --queue "$tmp/q" 2>&1) || bad "the rerun should land waves 2 and 3: $out"
case $out in *'line 2 already landed'*'pushed w2 to the open PR'*'queue done, 2 wave(s) landed'*) ;; *) bad "the rerun should resume at wave 2: $out" ;; esac
[ "$(prs)" = $((n0 + 3)) ] || bad "the rerun should reuse the PR of w2"
grep -qx 'body=Closes #9' "$tmp/fx/pr" && grep -qx 'Part of #164' "$tmp/fx/pr" && ! grep -q 'Closes #164' "$tmp/fx/pr" ||
  bad "a slice of parent 164 should write Part of #164: $(cat "$tmp/fx/pr")"
# The base moves after the PR opens: the PR is BEHIND with auto-merge set. wave-land merges the base,
# regenerates gen.txt (src/m arrives without it), pushes and waits; auto-merge then lands it.
cat > "$tmp/fx/on-open" << EOF
rm -f "$tmp/fx/on-open"
{ git clone -q "$tmp/remote.git" "$tmp/c" && echo m > "$tmp/c/src/m" && git -C "$tmp/c" add . &&
  git -C "$tmp/c" commit -q -m m && git -C "$tmp/c" push -q origin HEAD:main; } > /dev/null 2>&1
EOF
g fetch -q origin && g checkout -q -B main origin/main && plant 10-j j j main && g checkout -q main
out=$(land 10-j 2>&1) || bad "a BEHIND PR with auto-merge should be updated and land: $out"
case $out in *'merged main into wave-10'*) ;; *) bad "wave-land should merge main into the BEHIND wave: $out" ;; esac
git -C "$tmp/remote.git" show main:gen.txt | grep -qx m || bad "gen.txt should be regenerated after the base merge"
exit $fail
