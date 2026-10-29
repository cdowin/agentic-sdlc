#!/bin/sh
# tests/ratio.sh - spec for the ratio budgets of checks/checks.sh (warning level and limit):
# SUITE_WARN_RATIO, CODE_GLOBS and the comment-budget check. Run: sh tests/ratio.sh
root=$(cd "$(dirname "$0")/.." && pwd)
tmp=$(mktemp -d) && trap 'rm -rf "$tmp"' EXIT
fail=0
ok() { :; }
bad() { echo "FAIL $*"; fail=1; }
g() { git -C "$tmp/c" -c user.name=t -c user.email=t@t "$@"; }
# Fixture: 9 test lines (tests/t.sh), 1009 code lines (a/goldens/page.txt 1000, a/golden.txt 9).
git init -q "$tmp/c" && printf 'a\nb\nc\n' > "$tmp/c/CLAUDE.md"
mkdir -p "$tmp/c/tests" "$tmp/c/a/goldens" "$tmp/c/src"
seq 1 9 > "$tmp/c/tests/t.sh"; seq 1 1000 > "$tmp/c/a/goldens/page.txt"; seq 1 9 > "$tmp/c/a/golden.txt"
g add . && g commit -q -m base
chk() { # chk <want-exit> <label> [VAR=value ...]; output in $tmp/chk.out
  want=$1 label=$2; shift 2
  got=$(cd "$tmp/c" && env -i PATH="$PATH" EVENT=push "$@" sh "$root/checks/checks.sh" > "$tmp/chk.out" 2>&1; echo $?)
  [ "$got" = "$want" ] && ok || bad "$label (exit $got, want $want)"
}
has() { grep -qF -- "$1" "$tmp/chk.out" && ok || bad "$2: missing '$1' in: $(cat "$tmp/chk.out")"; }
hasnt() { grep -qF -- "$1" "$tmp/chk.out" && bad "$2: unexpected '$1'" || ok; }

# suite warning level: 9/1009 = 0.00892
chk 0 'suite under the warning level' CHECKS=test-budget SUITE_WARN_RATIO=0.009 SUITE_RATIO=0.02
hasnt '::warning title=test-budget::The suite' 'suite under warning'
chk 0 'suite between warning and limit passes' CHECKS=test-budget SUITE_WARN_RATIO=0.008 SUITE_RATIO=0.009
has '::warning title=test-budget::The suite has 9 test lines for 1009 code lines' 'suite warning'
chk 1 'suite over the limit fails' CHECKS=test-budget SUITE_WARN_RATIO=0.001 SUITE_RATIO=0.008
has '::error title=test-budget::The suite has 9' 'suite limit'
hasnt '::warning title=test-budget::The suite' 'no warning when the limit also fires'
chk 1 'bad warning ratio fails' CHECKS=test-budget SUITE_WARN_RATIO=half
has "SUITE_WARN_RATIO is 'half', not a number" 'suite bad warn value'
chk 0 'warning alone runs the suite check' CHECKS=test-budget SUITE_WARN_RATIO=0.001
has '::warning title=test-budget::The suite has 9 test lines' 'warn only'

# CODE_GLOBS: only matching non-test files are code (1000 lines).
chk 0 'CODE_GLOBS narrows code' CHECKS=test-budget CODE_GLOBS='a/goldens/**' SUITE_RATIO=0.009
chk 1 'CODE_GLOBS ratio over the limit fails' CHECKS=test-budget CODE_GLOBS='a/goldens/**' SUITE_RATIO=0.0089
has 'for 1000 code lines' 'CODE_GLOBS count'

# comment-budget fixture. Code src/c.sh: 7 lines, 4 comments (# x, # x, ## y, indented #; the
# shebang is not one). Test tests/c.js: 4 lines, 2 comments. Totals: 1016 code, 13 test lines.
printf '#!/bin/sh\n# x\n# x\n## y\n  # indented\necho a\necho b\n' > "$tmp/c/src/c.sh"
printf '// a\n// a\nx();\ny();\n' > "$tmp/c/tests/c.js"
g add . && g commit -q -m comments
S='comment-budget: 4 comment lines and 0 doc lines in 1016 code lines, 2 comment lines and 0 doc lines in 13 test lines'
chk 0 'comment-budget with no ratios passes' CHECKS=comment-budget
hasnt 'title=comment-budget' 'comment-budget unset'
chk 0 'comment ratios under the warning level' CHECKS=comment-budget COMMENT_WARN_RATIO=0.01 COMMENT_RATIO=0.02
has "$S" 'summary line (shebang not counted)'
hasnt 'title=comment-budget' 'under warning'
chk 0 'comment ratio between warning and limit passes' CHECKS=comment-budget COMMENT_WARN_RATIO=0.003 COMMENT_RATIO=0.0045
has '::warning title=comment-budget::' 'comment warning'
chk 1 'comment ratio over the limit fails' CHECKS=comment-budget COMMENT_WARN_RATIO=0.001 COMMENT_RATIO=0.003
has '::error title=comment-budget::' 'comment limit'
chk 1 'bad comment ratio fails' CHECKS=comment-budget COMMENT_RATIO=lots
has "COMMENT_RATIO is 'lots', not a number" 'comment bad value'
chk 1 'test comment ratio over the limit fails' CHECKS=comment-budget TEST_COMMENT_RATIO=0.15
has '::error title=comment-budget::' 'test comment limit'
chk 0 'test comment ratio under the limit passes' CHECKS=comment-budget TEST_COMMENT_RATIO=0.16 TEST_COMMENT_WARN_RATIO=0.1
has '::warning title=comment-budget::' 'test comment warning'
chk 0 'comment-budget is in the default checks' COMMENT_RATIO=0.0045 COMMENT_WARN_RATIO=0.003 BODY='Closes #1'
has '::warning title=comment-budget::' 'default CHECKS'

# GDScript: src/d.gd has 1 `##` doc line and 1 `#` comment.
printf '## doc\n# note\nvar x = 1\n' > "$tmp/c/src/d.gd"
g add . && g commit -q -m gd
chk 0 'gd doc comments count as doc lines' CHECKS=comment-budget COMMENT_RATIO=0.5
has 'comment-budget: 5 comment lines and 1 doc lines in 1019 code lines' 'gd ## is a doc line'

# The marker table: r.rs 1 comment, 2 doc; t.ts 1 comment, a 3-line doc block (a ts /* line is not
# in the table); m.lua 2 comments; k.c a 2-line comment block, 1 doc line. Totals: 11, 7, 1036.
printf '//! crate\n/// fn\n// note\nfn f() {}\n' > "$tmp/c/src/r.rs"
printf '/**\n * doc\n */\n// note\n/* no */\nlet x = 1\n' > "$tmp/c/src/t.ts"
printf -- '-- note\n--[[ x ]]\nprint(1)\n' > "$tmp/c/src/m.lua"
printf '/* a\n   b */\n/** d */\nint x;\n' > "$tmp/c/src/k.c"
g add . && g commit -q -m markers
chk 0 'the table counts each language' CHECKS=comment-budget COMMENT_RATIO=0.5
has 'comment-budget: 11 comment lines and 7 doc lines in 1036 code lines' 'marker table'
chk 0 'COMMENT_MARKERS overrides a row' CHECKS=comment-budget COMMENT_RATIO=0.5 COMMENT_MARKERS='gd=# lua=;'
has 'comment-budget: 10 comment lines and 6 doc lines in 1036 code lines' 'override'
chk 1 'a bad COMMENT_MARKERS entry fails' CHECKS=comment-budget COMMENT_RATIO=0.5 COMMENT_MARKERS='lua'
has "COMMENT_MARKERS entry 'lua' is not" 'bad marker entry'
chk 1 'doc ratio over the limit fails' CHECKS=comment-budget DOC_COMMENT_RATIO=0.006
has '::error title=comment-budget::7 doc lines in 1036 code lines' 'doc limit'
chk 0 'doc ratio between warning and limit passes' CHECKS=comment-budget DOC_COMMENT_WARN_RATIO=0.006 DOC_COMMENT_RATIO=0.007
has '::warning title=comment-budget::7 doc lines' 'doc warning'
exit "$fail"
