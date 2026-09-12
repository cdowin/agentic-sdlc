"""The preamble a dispatched agent gets BEFORE its first tool call.

Measured in this repo: nothing repo-specific reaches an agent at spawn. Not
`CLAUDE.md`, not a `paths:`-scoped rule (it loads on a file match the agent has
not made yet), not a skill body. ~35 agents were dispatched during 0.5.0 and
every brief hand-pasted the house rules; that was the only carrier they had,
and retyping is how five shipped sentences came to contradict shipped behaviour
in one day.

**RENDERED, never restated.** Everything below the pointers is read from the
same declaration the verb it describes reads — `[verify]`, `[checks]`,
`[pm.states.*]`. The project's own authored contracts are POINTED AT, not
copied: copying puts a 163-line paste in every brief, and the answer is
placement, not volume. Naming them is the rule 11 fix — the measured failure
was not disobedience, it was no signal they existed.

Re-measured in 0.9.0: `CLAUDE.md` DOES reach a dispatched agent now, and the
rest of a declared contract (~32KB here) is mostly nothing a builder needs. So
the preamble says `CLAUDE.md` is loaded, names the rest as reference, and
inlines the handful of rules the gates and hooks hold a builder to.
"""
from __future__ import annotations

import re
import shlex
import sys
from typing import NamedTuple

from agentic_sdlc.core.config import (ConfigError, config_section,
                                      section_declared)
from agentic_sdlc.core.project import repo_root
from agentic_sdlc.repo import vehicle

SECTION = 'dispatch'
PROJECT_KEY = 'project'
CONTRACTS_KEY = 'contracts'
# What the harness loads into every agent at spawn: named as loaded, not listed.
AUTOLOADED = ('CLAUDE.md', '.claude/CLAUDE.md')
# The worktree tool's installed name, the one `install-hooks` writes.
WORKTREE_TOOL = 'agent-worktree.sh'
# `agent-worktree.sh`'s `validate_slug`: what a branch suffix and a directory
# name may both hold.
_NOT_SLUG = re.compile(r'[^A-Za-z0-9._-]')

USAGE = """usage: agentic-sdlc dispatch [--grain <id>] [--role <name>] [--mode serial|parallel]

  --grain <id>   name the grain in the preamble, with its status and document
                 path, and render its GDK-STAMP line, which attributes this
                 dispatch's ledger rows, beside the `pm ledger record` line
                 for its return
  --role <name>  name the role the brief is for; the header, and --agent-type
                 on the record line
  --mode <m>     serial or parallel, overriding the `mode:` the grain's
                 milestone declares (absent or empty is serial). Parallel
                 renders the loop the AGENT owns: agent-worktree.sh new on the
                 milestone's `branch:`, build, commit by pathspec, report the
                 branch and hash; the orchestrator merges. It needs a
                 --grain whose milestone declares a `branch:`, or exit 2.

Renders the contract preamble to STDOUT. Paste it at the top of a dispatch, or
pipe it. It spawns nothing, reads no network and writes no file — the command
under RECORDING is rendered for the operator to run (D1).

WHAT IS RENDERED is read from `devkit.toml` — the ladder from [verify], both
lists `make check` runs from [checks] all (or the stock roster) and [gates]
extra, the state vocabulary from [pm.states.*] — so none of it is retyped and
none of it can drift. Every command in it is spelled through the stock wiring,
`make pm ARGS=…` or `make sdlc ARGS=…`, because that is what reaches the pin.
So are the builder's git and scope rules, which follow the mode.

WHAT IS POINTED AT is `[dispatch] contracts`, the project's own authored files:
CLAUDE.md is named as already loaded, the rest as reference, never copied. A
declared path that resolves to nothing is exit 2: a preamble naming a file
nobody can open is worse than one naming none."""

HELP_WORDS = ('-h', '--help', 'help')


def settings(section: dict | None = None) -> tuple[str, tuple[str, ...]]:
    """`(project line, contract paths)`, typed, with NOTHING behind either key.

    A DECLARATION (hard rule 5): no guard call here carries a literal fallback,
    because a fallback IS a default and a default would make this a knob. Every
    absence raises BY NAME instead — the same shape `verify_rules.read` uses.
    """
    if section is None:
        if not section_declared(SECTION):
            raise ConfigError(
                f'[{SECTION}] is not declared in devkit.toml — this verb '
                f'renders YOUR project\'s contracts and cannot invent them '
                f'(hard rule 8). Declare `{PROJECT_KEY} = "<one line: what '
                f'this is>"` and `{CONTRACTS_KEY} = ["CLAUDE.md", ...]`')
        section = config_section(SECTION)
    if not isinstance(section, dict):
        raise ConfigError(f'[{SECTION}] must be a table, got {section!r}')
    problems = []
    project = section.get(PROJECT_KEY)
    if not isinstance(project, str) or not project.strip():
        problems.append(
            f'[{SECTION}] {PROJECT_KEY} must be one non-empty line saying what '
            f'this project is — the sentence an agent has no other way to '
            f'learn, got {project!r}')
        project = ''
    raw = section.get(CONTRACTS_KEY)
    if not isinstance(raw, list) or not all(isinstance(v, str) for v in raw):
        problems.append(
            f'[{SECTION}] {CONTRACTS_KEY} must be a list of strings, got '
            f'{raw!r}' + (f' — write {CONTRACTS_KEY} = [{raw!r}]'
                          if isinstance(raw, str) else ''))
        raw = []
    elif not raw:
        problems.append(
            f'[{SECTION}] {CONTRACTS_KEY} names no file — a dispatch preamble '
            f'with no contract is the silence this verb exists to end')
    contracts = tuple(raw)
    if contracts:
        # Inside the checkout (hard rule 8), then actually there.
        for path in contracts:
            defect = _escapes(path)
            if defect:
                problems.append(f'[{SECTION}] {CONTRACTS_KEY} entry {path!r} '
                                f'{defect}')
        root = repo_root()
        missing = [c for c in contracts if not _escapes(c)
                   and not (root / c).is_file()]
        if missing:
            problems.append(
                f'[{SECTION}] {CONTRACTS_KEY} names {len(missing)} path(s) '
                f'that resolve to nothing: {", ".join(missing)} — a pointer to '
                f'a file nobody can open is worse than naming none')
    if problems:
        raise ConfigError(problems[0] if len(problems) == 1
                          else '; '.join(problems))
    return project.strip(), contracts


def _escapes(value: str) -> str:
    """Why this path leaves the checkout, or ''. `relpath_tuple`'s guard,
    reached without its fallback."""
    from agentic_sdlc.core.config import _escapes_checkout
    return _escapes_checkout(value) or ''


def _rung(name: str) -> str:
    """One `[verify]` rung's command, or '' where none is declared."""
    from agentic_sdlc.repo.verify import rules
    if not section_declared(rules.SECTION):
        return ''
    return rules.read(config_section(rules.SECTION)).rung(name) or ''


def _ladder() -> list[str]:
    """The rungs, from `[verify]` — the same reader `verify --plan` uses."""
    from agentic_sdlc.repo.verify import rules
    if not section_declared(rules.SECTION):
        return [f'  (no [{rules.SECTION}] declared — this project has no ladder)']
    out = []
    for name in rules.RUNGS:
        command = _rung(name)
        out.append(f'  {name:<10} {command}' if command
                   else f'  {name:<10} (not declared)')
    return out


class Mode(NamedTuple):
    """What `mode:` the dispatch runs in, and what the parallel loop needs."""

    parallel: bool
    milestone: str = ''
    branch: str = ''
    declared: bool = False      # the milestone said so, not `--mode`


def _mode(gid: str, override: str) -> Mode:
    """The grain's milestone's `mode:`, READ — absent or empty is serial, a
    word outside `MODES` is refused by name (rule 9) — unless `--mode` names
    one. Parallel refuses without a `branch:` to base the worktree on: a loop
    based on the default branch is the 0.8.0 failure this renders away."""
    from agentic_sdlc.repo.pm import inventory, vocabulary
    milestone = None
    declared = ''
    if gid:
        cfg = vocabulary.load()
        index = inventory.grain_index(cfg)
        milestone = index.get(inventory.milestone_of(cfg, gid))
        if milestone is not None:
            declared = milestone.field(vocabulary.FIELD_MODE).strip()
            if declared and declared not in vocabulary.MODES:
                raise ConfigError(
                    f'{cfg.rel(milestone.path)}: {vocabulary.FIELD_MODE}: '
                    f'{declared!r} is not one of {", ".join(vocabulary.MODES)}'
                    f' — absent or empty is {vocabulary.MODE_SERIAL}')
    if (override or declared) != vocabulary.MODE_PARALLEL:
        return Mode(False)
    if not gid:
        raise ConfigError('--mode parallel needs --grain <id>: the loop is '
                          'rendered against the grain\'s milestone `branch:`')
    if milestone is None:
        raise ConfigError(f'--grain {gid!r} belongs to no milestone, so a '
                          f'parallel loop has no `branch:` to base on')
    branch = milestone.field('branch').strip()
    if not branch:
        set_it = vehicle.command('pm', 'set', milestone.gid, 'branch',
                                 vehicle.Slot('<branch>'))
        raise ConfigError(f'milestone {milestone.gid} declares no `branch:`, '
                          f'so a parallel worktree has nothing to base on — '
                          f'`{set_it}`')
    return Mode(True, milestone.gid, branch, declared=not override)


def _contract(contracts: tuple[str, ...]) -> list[str]:
    """`CLAUDE.md` named as loaded, the rest as reference — never a reading
    list: the harness already delivered the one, and the rest is volume."""
    loaded = [c for c in contracts if c in AUTOLOADED]
    rest = [c for c in contracts if c not in AUTOLOADED]
    out = [f'{c} is already in your context: the harness loads it.'
           for c in loaded]
    if rest:
        out.append('Reference, open when a question needs it: '
                   + ', '.join(rest))
    return out


def _rules(mode: Mode) -> list[str]:
    """The builder's git and scope rules, the ones the gates and hooks hold —
    inlined because the documents that carry them are ~32KB of mostly else."""
    from agentic_sdlc.repo.pm import vocabulary
    from agentic_sdlc.repo.verify import rules
    story, milestone = _rung(rules.STORY), _rung(rules.MILESTONE)
    commit = ('commit only by pathspec: git add <paths>; git commit -m "…" '
              '-- <paths>' + ('' if mode.parallel else
                              ' — serial: on the milestone branch, your files only'))
    out = ['', 'THE GRAIN FILE IS THE BRIEF: build it; do not write a plan.',
           '', 'GIT AND SCOPE — the gates and hooks hold you to these:',
           '  never a repo-wide git command: no stash, reset, checkout -- ., '
           'restore, clean, bisect',
           f'  {commit}']
    try:
        roadmap = vocabulary.load().roadmap_dir
    except SystemExit:
        roadmap = ''
    if roadmap:
        out.append(f'  never touch {roadmap.rstrip("/")}/ — the PM tree is the '
                   f'orchestrator\'s')
    rung = f'the story rung, `{story}`' if story else 'the narrowest rung below'
    wide = f', never `{milestone}`' if milestone else ''
    out.append(f'  verify with {rung} — a tier target, never a test file named '
               f'by path{wide}')
    return out


def _loop(gid: str, mode: Mode) -> list[str]:
    """The loop a parallel builder owns, end to end, against the milestone's
    `branch:` — every command spelled, so nothing is improvised per dispatch.
    The builder stops at a committed branch; merging stays with the one holding
    integration (0.11.0: N builders merging into one checkout race each other)."""
    from agentic_sdlc.repo import install
    tool = dict(install.PLANS['install-hooks'])[WORKTREE_TOOL]
    root = shlex.quote(str(repo_root()))
    slug = _NOT_SLUG.sub('-', gid)
    branch = shlex.quote(mode.branch)
    why = (f'milestone {mode.milestone} declares `mode: parallel`'
           if mode.declared else '`--mode parallel`')
    return ['', f'THE LOOP — {why}. You own your branch; the orchestrator '
            f'merges it:',
            f'  1. cd {root} && bash {tool} new {slug} {branch}',
            '     it prints your worktree\'s path (work ONLY there) and names '
            'your branch',
            '  2. build; verify with the story rung; commit there by pathspec',
            '  3. report your branch and commit hash(es); do not merge, do not '
            f'run `{tool} done` — the orchestrator merges into {branch} and '
            'tears the worktree down']


def _vocabulary() -> list[str]:
    """Each kind's states by CATEGORY, off `[pm.states.*]`."""
    from agentic_sdlc.repo.pm import vocabulary
    try:
        cfg = vocabulary.load()
    except SystemExit:
        return ['  (no [pm.states.*] declared — `pm` cannot run here)']
    out = []
    for kind, flow in sorted(cfg.flows.items()):
        words = ' | '.join(' '.join(flow.by_category[c])
                           for c in vocabulary.CATEGORIES if flow.by_category.get(c))
        out.append(f'  {kind:<10} {words}')
    return out


def _grain(gid: str) -> list[str]:
    from agentic_sdlc.repo.pm import inventory, vocabulary
    cfg = vocabulary.load()
    grain = inventory.grain_index(cfg).get(gid)
    if grain is None:
        raise ConfigError(f'--grain {gid!r} resolves to no grain in this tree')
    status = grain.field(vocabulary.FIELD_STATUS)
    return [f'  id       {gid}',
            f'  kind     {grain.kind}',
            f'  status   {status or "(none)"}',
            f'  brief    {cfg.rel(grain.path)}',
            '', _stamp(gid, grain.field(ISSUE_FIELD))]


ISSUE_FIELD = 'issue'


def _stamp(gid: str, raw: str) -> str:
    """The line `record --from-transcript` copies grain and issue back from.
    `issue:` is split on commas and spaces, `[]`, quotes and `#` dropped."""
    from agentic_sdlc.repo.pm import ledger
    issues = [one.strip('\'"').lstrip('#') for one in
              (raw or '').strip('[]').replace(',', ' ').split()]
    defect = next(filter(None, map(ledger.issue_defect, issues)), '')
    if defect:
        raise ConfigError(f'{gid} declares {ISSUE_FIELD}: {raw!r} — {defect}')
    return ledger.stamp_line(gid, issues)


def _recording(gid: str, role: str) -> list[str]:
    """The row for the return, RENDERED — only ever with a grain, because a
    `pm ledger record` naming none refuses and a printed command that errors
    is worse than one nobody printed. No `GDK_LEDGER_GRAIN` export: the
    GDK-STAMP line above already attributes the dispatch (review R4)."""
    argv = ['pm', 'ledger', 'record', '--grain', gid]
    if role:
        argv += ['--agent-type', role]
    record = vehicle.command(*argv)
    return ['', 'RECORDING THIS DISPATCH — rendered here, run by you:',
            '  # on return, add inside the quotes what the agent reported: '
            '--agent-id <the id the Agent tool returned> '
            '--tokens-total N --duration-s N --tool-calls N --outcome landed|superseded|stopped:<why>',
            f'  {record}']


def render(grain: str = '', role: str = '', *,
           stock_gates: tuple[str, ...], mode: str = '') -> str:
    """The preamble. `stock_gates` is what `check all` runs when `[checks]
    all` is undeclared, handed down by the router that owns the roster:
    `repo/` reaching up for it is the import `test_boundaries.py` refuses."""
    project, contracts = settings()
    named = _grain(grain) if grain else []
    chosen = _mode(grain, mode)
    who = f' — for: {role}' if role else ''
    out = [f'=== PROJECT CONTRACT{who} ===', '', project, '']
    out += _contract(contracts)
    out += _rules(chosen)
    if grain:
        out += ['', 'THE GRAIN YOU ARE WORKING ON:'] + named
        out += _recording(grain, role)
        if chosen.parallel:
            out += _loop(grain, chosen)
    out += ['', 'THE LADDER — never run a rung wider than what you changed:']
    out += _ladder()
    out += ['', 'STATIC GATES — `make check` runs the devkit gates, then this '
                'project\'s own:']
    out += _static_gates(stock_gates)
    out += ['', 'THE PM VOCABULARY — every question is asked of a CATEGORY, '
                'never a word:']
    out += _vocabulary()
    out += ['', 'EXIT CODES ARE CONTRACT:  0 pass   1 findings   '
                '2 usage or config error',
            f'  through `{vehicle.MAKE} {vehicle.PM_TARGET}` and '
            f'`{vehicle.MAKE} {vehicle.SDLC_TARGET}`, any nonzero exit is '
            f'make\'s 2 — the verb\'s own code is the N in make\'s `Error N` '
            f'line',
            '=== END CONTRACT ===']
    return '\n'.join(out)


def _static_gates(stock: tuple[str, ...]) -> list[str]:
    """Both lists `make check` runs, in its order: `[checks] all`, else the
    stock roster, then `[gates] extra`.

    Validating the NAMES stays each list's own reader's job; a preamble naming
    an unknown gate is a typo the operator sees, not a gate that silently
    stopped running. A list that cannot be read is NAMED, never dropped (m4):
    an agent that trusts a short list runs a short gate.
    """
    from agentic_sdlc.core.config import str_tuple
    from agentic_sdlc.repo import gates_extra
    try:
        section = config_section('checks')
        devkit = ' '.join(str_tuple(section, 'checks', 'all', stock))
        if 'all' not in section:
            devkit += '   (the stock roster: devkit.toml declares no [checks] all)'
    except ConfigError as err:
        devkit = f'(unreadable, and `make check` refuses it: {err})'
    try:
        extra = gates_extra.targets()
        own = ' '.join(extra) if extra else '(none declared)'
    except ConfigError as err:
        own = f'(unreadable, and `make check` refuses it: {err})'
    return [f'  [checks] all   {devkit}',
            f'  [gates] extra  {own}',
            '  one devkit gate alone: '
            + vehicle.command('check', vehicle.Slot('<name>'))]


def main(argv: list[str], stock_gates: tuple[str, ...]) -> int:
    if argv and argv[0] in HELP_WORDS:
        print(USAGE)
        return 0
    from agentic_sdlc.repo.pm import vocabulary
    given = {'--grain': '', '--role': '', '--mode': ''}
    rest = list(argv)
    while rest:
        flag = rest.pop(0)
        if flag in given:
            if not rest:
                print(f'agentic-sdlc dispatch: {flag} needs a value',
                      file=sys.stderr)
                return 2
            given[flag] = rest.pop(0)
            continue
        print(f'agentic-sdlc dispatch: unexpected argument {flag!r}',
              file=sys.stderr)
        return 2
    if given['--mode'] and given['--mode'] not in vocabulary.MODES:
        print(f'agentic-sdlc dispatch: --mode {given["--mode"]!r} is not one '
              f'of {", ".join(vocabulary.MODES)}', file=sys.stderr)
        return 2
    try:
        print(render(given['--grain'], given['--role'],
                     stock_gates=stock_gates, mode=given['--mode']))
    except ConfigError as err:
        print(f'agentic-sdlc dispatch: {err}', file=sys.stderr)
        return 2
    return 0
