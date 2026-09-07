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
"""
from __future__ import annotations

import sys

from agentic_sdlc.core.config import (ConfigError, config_section,
                                      section_declared)
from agentic_sdlc.core.project import repo_root

SECTION = 'dispatch'
PROJECT_KEY = 'project'
CONTRACTS_KEY = 'contracts'

USAGE = """usage: agentic-sdlc dispatch [--grain <id>] [--role <name>]

  --grain <id>   name the grain in the preamble, with its status and document
                 path, so the agent's first read is the brief and not a guess
  --role <name>  name the role the brief is for; recorded in the header only

Renders the contract preamble to STDOUT. Paste it at the top of a dispatch, or
pipe it. It spawns nothing, reads no network and writes no file.

WHAT IS RENDERED is read from `devkit.toml` — the ladder from [verify], the
gate roster from [checks], the state vocabulary from [pm.states.*] — so none of
it is retyped and none of it can drift.

WHAT IS POINTED AT is `[dispatch] contracts`, the project's own authored files.
They are named, never copied. A declared path that resolves to nothing is exit
2: a preamble naming a file nobody can open is worse than one naming none."""

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


def _ladder() -> list[str]:
    """The rungs, from `[verify]` — the same reader `verify --plan` uses."""
    from agentic_sdlc.repo.verify import rules
    if not section_declared(rules.SECTION):
        return [f'  (no [{rules.SECTION}] declared — this project has no ladder)']
    ladder = rules.read(config_section(rules.SECTION))
    out = []
    for name in rules.RUNGS:
        command = ladder.rung(name)
        out.append(f'  {name:<10} {command}' if command
                   else f'  {name:<10} (not declared)')
    return out


def _vocabulary() -> list[str]:
    """Each kind's states by CATEGORY, off `[pm.states.*]`."""
    from agentic_sdlc.repo.pm import model
    try:
        cfg = model.load()
    except SystemExit:
        return ['  (no [pm.states.*] declared — `pm` cannot run here)']
    out = []
    for kind, flow in sorted(cfg.flows.items()):
        words = ' | '.join(' '.join(flow.by_category[c])
                           for c in model.CATEGORIES if flow.by_category.get(c))
        out.append(f'  {kind:<10} {words}')
    return out


def _grain(gid: str) -> list[str]:
    from agentic_sdlc.repo.pm import model
    cfg = model.load()
    grain = model.grain_index(cfg).get(gid)
    if grain is None:
        raise ConfigError(f'--grain {gid!r} resolves to no grain in this tree')
    status = model.field_of(grain.path, 'status')
    return [f'  id       {gid}',
            f'  kind     {grain.kind}',
            f'  status   {status or "(none)"}',
            f'  brief    {cfg.rel(grain.path)}   <- READ THIS FIRST']


def render(grain: str = '', role: str = '') -> str:
    project, contracts = settings()
    who = f' — for: {role}' if role else ''
    out = [f'=== PROJECT CONTRACT{who} ===', '', project, '',
           'READ THESE BEFORE YOUR FIRST EDIT. They are this project\'s own '
           'rules and',
           'they are enforceable — the gates below fail on them:']
    out += [f'  {path}' for path in contracts]
    if grain:
        out += ['', 'THE GRAIN YOU ARE WORKING ON:'] + _grain(grain)
    out += ['', 'THE LADDER — never run a rung wider than what you changed:']
    out += _ladder()
    roster = _roster()
    if roster:
        out += ['', 'STATIC GATES (`agentic-sdlc check <name>`):',
                '  ' + ' '.join(roster)]
    out += ['', 'THE PM VOCABULARY — every question is asked of a CATEGORY, '
                'never a word:']
    out += _vocabulary()
    out += ['', 'EXIT CODES ARE CONTRACT:  0 pass   1 findings   '
                '2 usage or config error', '=== END CONTRACT ===']
    return '\n'.join(out)


def _roster() -> tuple[str, ...]:
    """`[checks] all`, read as a config VALUE — not through `cli.all_roster`.

    This package's layers point downward and `repo/` reaching up into the
    router is the import `test_boundaries.py` refuses. Validating the NAMES
    stays the router's job; a preamble that named an unknown gate is a typo
    the operator sees, not a gate that silently stopped running.
    """
    from agentic_sdlc.core.config import str_tuple
    try:
        return str_tuple(config_section('checks'), 'checks', 'all', ())
    except ConfigError:
        return ()


def main(argv: list[str]) -> int:
    if argv and argv[0] in HELP_WORDS:
        print(USAGE)
        return 0
    grain = role = ''
    rest = list(argv)
    while rest:
        flag = rest.pop(0)
        if flag in ('--grain', '--role'):
            if not rest:
                print(f'agentic-sdlc dispatch: {flag} needs a value',
                      file=sys.stderr)
                return 2
            value = rest.pop(0)
            if flag == '--grain':
                grain = value
            else:
                role = value
            continue
        print(f'agentic-sdlc dispatch: unexpected argument {flag!r}',
              file=sys.stderr)
        return 2
    try:
        print(render(grain, role))
    except ConfigError as err:
        print(f'agentic-sdlc dispatch: {err}', file=sys.stderr)
        return 2
    return 0
