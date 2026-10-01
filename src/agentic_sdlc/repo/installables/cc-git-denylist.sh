#!/usr/bin/env bash
# cc-git-denylist.sh — Claude Code PreToolUse Bash hook: refuse only the git
# that cannot be undone or that harms another tree. Refused: a force push
# (--force, -f, --force-with-lease, --mirror, a +refspec); a push whose
# destination is a PROTECTED_BRANCHES branch; reset --hard; clean -f / -x
# (bar a dry run); a whole-tree discard (`checkout .`, `checkout -- .`,
# `restore .`); an alias or include set by `-c`, `--config-env` or a `git config`
# write; any command, git or not, that assigns, exports, `declare`s or
# `env`s GIT_CONFIG_PARAMETERS, _COUNT, _KEY_* or _VALUE_*; and stash bar
# list/show/apply/create, as every worktree shares one stash. All else passes.
# Each `;` `&&` `|` `$(...)` part, `git -C <dir>`, `bash -c '...'` and `eval` is
# read. A push with no refspec is pre-push's to judge. `bash cc-git-denylist.sh
# --self-test` replays the corpus. Stdin: the PreToolUse JSON. Exit 0 = allow,
# 2 = block; failures exit 0.
set -u
trap 'exit 0' ERR

# --- project config (yours to edit after install — the file is your repo's) --
# Branches (exact, space-separated) no `git push` may name as its destination.
PROTECTED_BRANCHES="main master"
# -----------------------------------------------------------------------------

# A header carried from an older install may lack a key: it runs at its stock value.
declare -p PROTECTED_BRANCHES >/dev/null 2>&1 || PROTECTED_BRANCHES="main master"

read -r -d '' JUDGE <<'PY' || true
import json, os, re, shlex, sys
PROTECTED = os.environ.get('PROTECTED_BRANCHES', '').split()
GLOBAL_ARG = ('-C', '-c', '--git-dir', '--work-tree', '--namespace', '--config-env')
PUSH_ARG = ('-o', '--push-option', '--repo', '--receive-pack', '--exec')
HEREDOC = re.compile(r"(?<!<)<<-?(?!<)\s*['\"]?([A-Za-z_][A-Za-z0-9_]*)")
FORCE = 'a force push rewrites history others may hold; push a new commit instead'
CONF_KEY = re.compile(r'(alias|include|includeif)(\.|$)', re.I)  # a key that runs or pulls in unread config
CONF_ARG = ('-f', '--file', '--blob', '--type', '--default', '--comment', '--value')
CONF_WRITE = ('set', 'unset', 'unset-all', 'add', 'replace-all', 'rename-section', 'remove-section')
GIT_ENV = re.compile(r'GIT_CONFIG_(PARAMETERS|COUNT|KEY_\w*|VALUE_\w*)(=|$)')
ENV_MSG = 'GIT_CONFIG_* in the environment sets config this hook cannot read; use git -c with a plain key'

def segments(text):  # heredoc bodies dropped; split on ; & | ( ) ` and newline
    lines, end = [], None
    for line in text.split('\n'):
        if end is None:
            lines.append(line)
            end = (HEREDOC.search(line) or [None, None])[1]
        elif line.strip() == end:
            end = None
    lex = shlex.shlex('\n'.join(lines).replace('`', ' ; '), posix=True, punctuation_chars=';&|()<>\n')
    lex.whitespace, lex.whitespace_split, lex.commenters = ' \t\r', True, ''
    seg, drop, skip = [], False, False
    for w in list(lex) + [';']:
        if w and set(w) <= set(';&|()\n'):
            if seg:
                yield seg
            seg, drop, skip = [], False, False
        elif drop or skip or w.startswith('#'):
            drop, skip = drop or w.startswith('#'), False
        elif w and set(w) <= set('<>&'):  # a redirect: drop its fd and its target
            seg, skip = seg[:-1] if seg and seg[-1].isdigit() else seg, True
        else:
            seg.append(w)

def sets_env(seg):  # a GIT_CONFIG_* assignment, export, declare or env; a read or unexport passes
    i = next((k for k, w in enumerate(seg) if not re.match(r'\w+=', w)), len(seg))
    said = [w for w in seg[:i] if '=' in w]
    cmd, args = (os.path.basename(seg[i]), seg[i + 1:]) if i < len(seg) else ('', [])
    j = next((k for k, w in enumerate(args) if w == '--' or not w.startswith(('-', '+'))), len(args))
    flags = ''.join(w[1:] for w in args[:j])  # only the leading flags count; bash reads a later -n as a name
    names = [w for w in args if not w.startswith(('-', '+'))]
    if cmd == 'export' and 'n' not in flags or cmd in ('declare', 'typeset', 'local', 'readonly') and 'p' not in flags:
        said += names
    elif cmd == 'env':  # its NAME=value words and an -S string, up to its command
        k = 0
        while k < len(args) and (args[k].startswith('-') or '=' in args[k]):
            w = args[k]
            if w in ('-S', '--split-string', '-u', '--unset', '-C', '--chdir') and k + 1 < len(args):
                k, w = k + 1, (args[k + 1] if w in ('-S', '--split-string') else '')
            said += re.sub(r'^(-S|--split-string=)', '', w).split()
            k += 1
    return any(GIT_ENV.match(w) for w in said)

def git(args):
    i = 0
    while i < len(args) and args[i].startswith('-'):
        key = args[i + 1] if args[i] in ('-c', '--config-env') and i + 1 < len(args) else re.sub(r'^(-c|--config-env=)', '', args[i])
        m = CONF_KEY.match(key)
        if m:
            what = 'runs a command' if m[1].lower() == 'alias' else 'pulls in config'
            return f'git -c {m[1].lower()}.* {what} this hook cannot read; run that command itself'
        i += 2 if args[i] in GLOBAL_ARG else 1
    sub, rest = (args[i], args[i + 1:]) if i < len(args) else ('', [])
    opts = rest[:rest.index('--')] if '--' in rest else rest
    longs = [o[2:].split('=')[0] for o in opts if o.startswith('--') and len(o) > 3]
    shorts = ''.join(o[1:] for o in opts if o.startswith('-') and not o.startswith('--'))
    has = lambda full, letter='': bool(letter and letter in shorts) or any(full.startswith(n) for n in longs)
    if sub == 'push':
        if has('force', 'f') or has('force-with-lease') or has('mirror'):
            return FORCE
        pos = [w for k, w in enumerate(rest) if not w.startswith('-') and (k == 0 or rest[k - 1] not in PUSH_ARG)]
        for spec in pos[1:]:
            dst = re.sub(r'^refs/heads/', '', spec.split(':')[-1])
            if spec.startswith('+') or dst in PROTECTED:
                return FORCE if spec.startswith('+') else f'{dst} is a protected branch; push your feat/ branch and let the lead merge it'
    if sub == 'reset' and has('hard'):
        return 'reset --hard discards uncommitted work; commit it, or restore one named path'
    if sub == 'clean' and not has('dry-run', 'n') and (has('force', 'f') or 'x' in shorts.lower()):
        return 'clean -f deletes untracked files for good; rm the paths you mean'
    if sub in ('checkout', 'restore'):
        paths = rest[rest.index('--') + 1:] if '--' in rest else [w for w in rest if not w.startswith('-')]
        staged = sub == 'restore' and has('staged', 'S') and not has('worktree', 'W')
        if not staged and set(paths) & {'.', './', ':/', ':/.', '*', ':(top)'}:
            return 'a whole-tree discard drops every uncommitted change; name the paths'
    if sub == 'config':  # a write under alias./include. hides a command from a later git
        pos = [w for k, w in enumerate(rest) if not w.startswith('-') and (k == 0 or rest[k - 1] not in CONF_ARG)]
        verb = pos.pop(0) if pos and pos[0] in CONF_WRITE + ('get', 'list', 'edit') else ''
        read = verb in ('get', 'list') or any(n.startswith('get') for n in longs)
        keys = pos[:2] if 'rename-section' in longs + [verb] else pos[:1]
        m = next(filter(None, map(CONF_KEY.match, keys)), None)
        if m and not read and (len(pos) > 1 or verb in CONF_WRITE or set(longs) & set(CONF_WRITE)):
            return f'git config {m[1].lower()}.* sets config a later git runs unread; run that command itself'
    if sub == 'stash' and (rest[0] if rest and not rest[0].startswith('-') else 'push') not in ('list', 'show', 'apply', 'create'):
        return 'every worktree shares one stash; commit on your branch instead (stash list/show/apply pass)'

def judge(text, depth=0):
    for seg in segments(text):
        shell = [k for k, w in enumerate(seg) if os.path.basename(w) in ('bash', 'sh', 'zsh', 'dash', 'ksh')]
        inner = [seg[k + 1] for k in range(shell[0] + 1 if shell else len(seg), len(seg) - 1)
                 if re.fullmatch(r'-[a-z]*c[a-z]*', seg[k])][:1] + ([' '.join(seg[1:])] if seg[0] == 'eval' else [])
        gits = [k for k, w in enumerate(seg) if os.path.basename(w) == 'git'][:1]
        env = [ENV_MSG] if sets_env(seg) else []
        for said in [judge(t, depth + 1) for t in inner if depth < 3] + env + [git(seg[k + 1:]) for k in gits]:
            if said:
                return said

if sys.argv[1:] == ['--self-test']:
    rows = [r.replace('\\n', '\n') for line in sys.stdin.read().splitlines() for r in line.split(' ;; ') if r.strip()]
    bad = [f'  wanted {r[0]}: {r[2:]}' for r in rows if (judge(r[2:]) is not None) != (r[0] == 'B')]
    print('\n'.join(bad) or f'{len(rows)} case(s)')
    sys.exit(1 if bad else 0)
data = json.load(sys.stdin)
if data.get('tool_name') == 'Bash':
    print(judge(str((data.get('tool_input') or {}).get('command') or '')) or '')
PY

if [ "${1:-}" = "--self-test" ]; then
	trap - ERR
	# Rows are `B|A <command>`, ` ;; `-separated; `\n` is a newline. Stock header values.
	out="$(PROTECTED_BRANCHES="main master" python3 -c "$JUDGE" --self-test <<'ROWS'
B git push --force origin feat/x ;; B git push -f ;; B git push --force-with-lease origin feat/x
B git push origin +feat/x ;; B git push --mirror origin ;; B git push origin main
B git push origin HEAD:refs/heads/master ;; B cd /tmp/x && git -C repo reset --hard origin/feat/x
B git status; git clean -fd ;; B git clean -x -f ;; B git checkout -- . ;; B git checkout .
B git restore . ;; B git stash ;; B git stash push -m wip ;; B git stash save wip ;; B git stash -u
B bash -c 'cd x && git stash' ;; B echo $(git reset --hard) ;; B eval "git stash pop"
B git commit -F - <<'EOF'\nmsg\nEOF\ngit stash ;; B git log # note\ngit stash drop
A git push origin feat/x ;; A git push -u origin feat/x:feat/x ;; A git push origin main:feat/copy
A git reset --soft HEAD~1 ;; A git clean -n -fd ;; A git checkout -- src/a.py ;; A git checkout feat/x
A git restore --staged . ;; A git stash list ;; A git stash show -p stash@{0}
A git worktree add ../x -b feat/x ;; A git worktree remove x ;; A git worktree prune
A git branch -D y ;; A git switch feat/x ;; A git merge feat/x ;; A git bundle create a b
A git commit -m "never git reset --hard" ;; A git commit -F - <<'EOF'\ndo not git stash\nEOF\ngit status
B git -c alias.zz='!git -C /r reset --hard' -C /tmp/x zz ;; B git -calias.zz=status zz ;; B git -c "ALIAS.zz=!rm x" zz
B git --config-env=alias.zz=E zz ;; B git --config-env alias.zz=E zz ;; A git -c user.name=x commit -m alias.y
A git push origin feat/x 2>&1 | tail -3 ;; A echo done
B git -c include.path=/tmp/evil.cfg zz ;; B git -c includeIf.onbranch:main.path=/tmp/e zz ;; B git --config-env INCLUDE.path=E zz
B GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=alias.zz GIT_CONFIG_VALUE_0='!git reset --hard' git zz
B GIT_CONFIG_PARAMETERS="'alias.zz=!git reset --hard'" git zz ;; B env GIT_CONFIG_VALUE_3=x git zz
B git config alias.zz '!git reset --hard'; git zz ;; B git config --global include.path /tmp/e ;; B git config --unset alias.zz
B git config set includeIf.onbranch:main.path /tmp/e ;; B git config --rename-section x alias ;; B git config -f .git/config --add Alias.zz x
A git -c core.pager=less log ;; A git config user.email x ;; A git config --global user.name alias.x ;; A git config alias.zz
A git config --get alias.zz ;; A git config --get-regexp alias.zz x ;; A git config -l ;; A git config --list ;; A git config get alias.zz
A FOO=1 git status ;; A git config -f alias.cfg user.name x
B export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=alias.zz GIT_CONFIG_VALUE_0='!git reset --hard'
B export FOO=1 GIT_CONFIG_PARAMETERS="'alias.zz=!x'" ;; B GIT_CONFIG_COUNT=1; export GIT_CONFIG_COUNT
B declare -x GIT_CONFIG_KEY_0=alias.zz ;; B typeset -x GIT_CONFIG_VALUE_0 ;; B cd x && GIT_CONFIG_COUNT=1 make y
B env -S 'GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=alias.zz bash' ;; B env -i -SGIT_CONFIG_COUNT=1 sh ;; B bash -c 'export GIT_CONFIG_COUNT=1'
A echo $GIT_CONFIG_COUNT ;; A unset GIT_CONFIG_COUNT GIT_CONFIG_KEY_0 ;; A declare -p GIT_CONFIG_COUNT ;; A export FOO=1 BAR=2
A env -u GIT_CONFIG_COUNT make y ;; A git commit -m "export GIT_CONFIG_COUNT=1" ;; A export GIT_CONFIG_GLOBALX
B export GIT_CONFIG_COUNT=1 -n ;; B declare -x -- GIT_CONFIG_COUNT=1 ;; B readonly GIT_CONFIG_COUNT ;; A export -n GIT_CONFIG_COUNT
ROWS
)" || { printf '[cc-git-denylist.sh] SELF-TEST FAIL\n%s\n' "$out" >&2; exit 1; }
	for cmd in 'git reset --hard' 'export GIT_CONFIG_COUNT=1'; do
		printf '{"tool_name":"Bash","tool_input":{"command":"%s"}}' "$cmd" | bash "$0" 2>/dev/null
		[ $? = 2 ] || { echo "[cc-git-denylist.sh] SELF-TEST FAIL — a payload did not block: $cmd" >&2; exit 1; }
	done
	printf 'not json {{{' | bash "$0" || { echo "[cc-git-denylist.sh] SELF-TEST FAIL — garbage did not fail open" >&2; exit 1; }
	echo "[cc-git-denylist.sh] SELF-TEST OK — $out"
	exit 0
fi

INPUT="$(cat)"
case "$INPUT" in *git*|*GIT_CONFIG_*) ;; *) exit 0 ;; esac
command -v python3 >/dev/null 2>&1 || exit 0
VERDICT="$(printf '%s' "$INPUT" | PROTECTED_BRANCHES="$PROTECTED_BRANCHES" python3 -c "$JUDGE" 2>/dev/null || true)"
[ -n "$VERDICT" ] || exit 0
printf 'BLOCKED (cc-git-denylist): %s\n' "$VERDICT" >&2
exit 2
