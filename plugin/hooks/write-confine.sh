#!/bin/sh
# write-confine.sh - agentic-sdlc PreToolUse hook for Write, Edit, MultiEdit
# and NotebookEdit. OPT-IN: runs only when AGENTIC_SDLC_WRITE_CONFINE=1.
# Refuses a file write into a different git repository than the session's.
# Passes: a target in no repository, a worktree of the same repository, the
# Claude Code auto-memory store, and a root listed in AGENTIC_SDLC_WRITE_ROOTS
# (colon-separated repository toplevels). AGENTIC_SDLC_WRITE_SCOPE sets the
# allowed toplevel; the default is the toplevel of the session cwd.
# Bash is not confined. Stdin: hook JSON (tool_input.file_path or
# notebook_path, cwd). Exit 0 = allow. Exit 2 = refuse, with a reason on
# stderr. Fails open.

[ "${AGENTIC_SDLC_WRITE_CONFINE:-0}" = 1 ] || exit 0
input=$(cat) || exit 0

# A path or a cwd holds no quote, so a grep reader is enough here.
field() {
  printf '%s' "$input" | grep -oE "\"$1\"[[:space:]]*:[[:space:]]*\"[^\"]*\"" | head -n 1 |
    sed -E 's/.*:[[:space:]]*"([^"]*)"/\1/'
}
toplevel() { git -C "$1" rev-parse --show-toplevel 2>/dev/null; }
common() { git -C "$1" rev-parse --path-format=absolute --git-common-dir 2>/dev/null; }

target=$(field file_path)
[ -n "$target" ] || target=$(field notebook_path)
[ -n "$target" ] || exit 0
case $target in */.claude/projects/*/memory/*) exit 0 ;; esac

cwd=$(field cwd)
[ -n "$cwd" ] || cwd=$PWD
allowed=${AGENTIC_SDLC_WRITE_SCOPE:-$(toplevel "$cwd")}
[ -n "$allowed" ] || exit 0

# The file may not exist yet: walk up to the nearest directory that does.
dir=$(dirname "$target")
while [ ! -d "$dir" ] && [ "$dir" != / ]; do dir=$(dirname "$dir"); done
top=$(toplevel "$dir")
[ -n "$top" ] || exit 0
[ "$top" = "$allowed" ] && exit 0

# Same repository, other worktree: they share one git common dir.
a=$(common "$allowed")
[ -n "$a" ] && [ "$a" = "$(common "$top")" ] && exit 0

# Granted roots match exactly, so /x/repo never admits /x/repo-evil.
old_ifs=$IFS
IFS=:
for root in ${AGENTIC_SDLC_WRITE_ROOTS:-}; do
  [ "$root" = "$top" ] && exit 0
done
IFS=$old_ifs

printf 'agentic-sdlc write-confine: %s is in repo %s, outside this session (%s); add it to AGENTIC_SDLC_WRITE_ROOTS or work from that repo\n' \
  "$target" "$top" "$allowed" >&2
exit 2
