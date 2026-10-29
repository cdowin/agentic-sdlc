#!/bin/sh
# tests/wave-land.sh - wave-land lands 2 planted branches into a scratch repo and cleans up, and
# stops on a conflict outside the generated files. gh is the stub in tests/fixtures/wave-land.
# POSIX sh; needs git and jq. Exit 0 when all pass.
root=$(cd "$(dirname "$0")/.." && pwd)
tmp=$(mktemp -d)
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
[ "$(git -C "$tmp/w" worktree list | wc -l)" = 1 ] || bad "worktrees left: $(git -C "$tmp/w" worktree list)"
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
  [ "$(git -C "$tmp/w" worktree list | wc -l)" = 1 ] && [ -z "$(git -C "$tmp/w" branch --list 'wave*')" ] ||
  bad "a stopped run should push nothing and leave no worktree or wave branch"
exit $fail
