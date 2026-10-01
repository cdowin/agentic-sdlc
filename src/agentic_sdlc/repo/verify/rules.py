"""rules.py — `[verify]` read once, into two rungs, or refused with exit 2.

Two rungs, `spot` and `milestone`, each naming a make target the project
already has (D3): `spot = "make unit"`. `spot` is the builder's one command;
`milestone` is CI's, and required. `spot` may be absent, and the verb names
the absence. A retired key is refused by name: `story` (renamed `spot` in
2.0.0), `feature` (retired in 2.0.0: `integrate` proves the batch), `wide`,
and the `narrow` table. Spawns nothing, reads no file.

`[verify.inputs]` names, per rung, the paths a rung's tree state is taken
over: `spot = ["src", "tests"]`. A rung with no entry is keyed on the whole
tree. Every entry is a repo-relative path prefix; a rung name the ladder does
not know, a non-list value or a path outside the checkout is exit 2.

`reuse_ignores_status` (stock `true`) is a GATE key: every rung's state
leaves out what a belt writes — each grain's `status:` line and the ledger
rows a belt files about its own run — so one green run serves every close on
one commit. A project whose rung target READS statuses sets it `false`, and
every rung keys on every byte.

`static` (stock `make check`) is the other GATE key: the rung `verify
--milestone` asks on the CURRENT tree before it reuses a PASS under that
exclusion, because the stock milestone target runs `check`, `check pm` grades
statuses, and a reused state cannot say which status its run saw (#87). It
is spelled the way a rung is, `make <target>`.

`history_independent` is an opt-in table of rung booleans. A true rung omits
Git HEAD from its key, but still hashes every declared input and the installed
tool version. Gates that read Git history must leave this false (the default).
`environment` names process variables that affect a rung; their values are
hashed but never printed.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from agentic_sdlc.core.config import (ConfigError, flag, relpath_tuple,
                                      str_tuple, table, text)
from agentic_sdlc.repo import gates_extra

SECTION = 'verify'

# The ladder, narrow to wide. Every rung is a make target.
SPOT = 'spot'
MILESTONE = 'milestone'
RUNGS = (SPOT, MILESTONE)

# A repo with no `milestone` has no CI rung; `spot` may be absent.
REQUIRED_RUNG = MILESTONE

# The 2.0.0 rungs that left, refused by name wherever a rung name is read.
RETIRED_RUNGS = {
    'story': f'renamed: [{SECTION}] story → {SPOT} (2.0.0) — '
             f'`{SPOT} = "make <target>"` is the builder\'s one command',
    'feature': f'retired: [{SECTION}] feature (2.0.0) — `integrate` proves the '
               f'batch once; delete the key',
}

# Refused by name, so an author is not left guessing at "unknown key". `narrow`
# is both `[verify] narrow = …` and `[[verify.narrow]]`: TOML lands them on
# the same key.
NARROW = 'narrow'
RETIRED = {
    'wide': (f'[{SECTION}] wide was renamed to {MILESTONE} (decision D3) — '
             f'and {MILESTONE} names a make target the project already has, '
             f'not a command of its own: `{MILESTONE} = "make {MILESTONE}"`. '
             f'Left as wide this section declares no close at all'),
    NARROW: (f'[{SECTION}] {NARROW} is retired: the {SPOT} rung is a make '
             f'target, `{SPOT} = "make <target>"` — it no longer selects '
             f'commands by changed path. Delete every [[{SECTION}.{NARROW}]] '
             f'table and declare the one line'),
    **RETIRED_RUNGS,
}

# A rung that could name any program could drift from the Makefile (D3).
RUNG_PROGRAM = 'make'

# Rule 6: a `[verify]` mistake is always 2, never 1.
EXIT_CONFIG = 2

# The sub-table naming what each rung's state is taken over.
INPUTS = 'inputs'

# The gate key with a stock value behind it (rule 5): does a rung's state
# leave out what a belt writes? `false` keys every rung on every byte.
REUSE_IGNORES_STATUS = 'reuse_ignores_status'
REUSE_IGNORES_STATUS_STOCK = True

# The other gate key: what a milestone reuse under that exclusion asks of the
# tree first. A make target, like the rungs, so the Makefile stays the
# authority on what it runs.
STATIC = 'static'
STATIC_STOCK = 'make check'

# History independence is deliberately opt-in per rung. A gate that reads Git
# history must retain HEAD in its state key.
HISTORY_INDEPENDENT = 'history_independent'
ENVIRONMENT = 'environment'

SECTION_KEYS = frozenset((*RUNGS, INPUTS, REUSE_IGNORES_STATUS, STATIC,
                          HISTORY_INDEPENDENT, ENVIRONMENT))


@dataclass(frozen=True)
class Ladder:
    """The two rungs' commands. `spot` is None when unconfigured, so the verb
    can name that rather than skip it. `inputs`
    holds each rung's declared path prefixes; a rung absent from it is keyed
    on the whole tree. `reuse_ignores_status` says whether every rung's state
    leaves out what a belt writes; `static` is what a milestone reuse under
    that exclusion asks of the current tree first."""

    milestone: str
    spot: str | None = None
    inputs: dict[str, tuple[str, ...]] = field(default_factory=dict)
    reuse_ignores_status: bool = REUSE_IGNORES_STATUS_STOCK
    static: str = STATIC_STOCK
    history_independent: dict[str, bool] = field(default_factory=dict)
    environment: tuple[str, ...] = ()

    def rung(self, name: str) -> str | None:
        """One rung's command by rung name, or None when unconfigured."""
        return getattr(self, name)

    def scope(self, name: str) -> tuple[str, ...]:
        """The path prefixes a rung's state covers; () means the whole tree."""
        return self.inputs.get(name, ())

    def omits_history(self, name: str) -> bool:
        """Whether this rung explicitly declares that it does not read HEAD."""
        return self.history_independent.get(name, False)


def rung_target(command: str) -> str:
    """The make target a rung command names — `"make unit"` -> `unit`. Not
    re-validated: `_rung` already accepted the value."""
    return command.split()[1]


def read(section: dict) -> Ladder:
    """The `[verify]` section, typed; raises ConfigError (exit 2) naming
    every problem found."""
    if not isinstance(section, dict):
        raise ConfigError(f'[{SECTION}] must be a table, got {section!r}')
    problems = [why for key, why in RETIRED.items() if key in section]
    unknown = sorted(set(section) - SECTION_KEYS - set(RETIRED))
    if unknown:
        problems.append(
            f'[{SECTION}] has unknown key(s) '
            f'{", ".join(repr(key) for key in unknown)} — the section takes '
            f'{", ".join(RUNGS)}, {REUSE_IGNORES_STATUS}, {STATIC} and the '
            f'`{INPUTS}`, `{HISTORY_INDEPENDENT}` and `{ENVIRONMENT}` '
            f'table; a typo here is a setting that never applies')
    rungs = {name: _rung(section, name, problems) for name in RUNGS}
    inputs = _inputs(section, problems)
    try:
        ignores = flag(section, SECTION, REUSE_IGNORES_STATUS,
                       REUSE_IGNORES_STATUS_STOCK)
    except ConfigError as err:
        problems.append(str(err))
        ignores = REUSE_IGNORES_STATUS_STOCK
    static = _static(section, problems)
    history_independent = _history_independent(section, problems)
    environment = _environment(section, problems)
    if problems:
        raise ConfigError(_message(problems))
    return Ladder(milestone=rungs[MILESTONE] or '', spot=rungs[SPOT],
                  inputs=inputs,
                  reuse_ignores_status=ignores, static=static,
                  history_independent=history_independent,
                  environment=environment)


def _environment(section: dict, problems: list[str]) -> tuple[str, ...]:
    """`[verify] environment`: names of process variables that affect gates."""
    try:
        values = str_tuple(section, SECTION, ENVIRONMENT, (), allow_empty=True)
    except ConfigError as err:
        problems.append(str(err))
        return ()
    invalid = [name for name in values
               if not name.isascii() or not name.isidentifier()]
    if invalid:
        problems.append(f'[{SECTION}] {ENVIRONMENT} has invalid environment '
                        f'name(s): {", ".join(repr(name) for name in invalid)}')
    return tuple(name for name in values if name not in invalid)


def _history_independent(section: dict, problems: list[str]) -> dict[str, bool]:
    """`[verify.history_independent]`: rung -> bool, false when absent."""
    where = f'[{SECTION}.{HISTORY_INDEPENDENT}]'
    try:
        values = table(section, SECTION, HISTORY_INDEPENDENT, {})
    except ConfigError as err:
        problems.append(str(err))
        return {}
    _unknown_rungs(values, where, problems)
    out: dict[str, bool] = {}
    for name, value in values.items():
        if name not in RUNGS:
            continue
        if not isinstance(value, bool):
            problems.append(f'{where} {name} must be true/false, got {value!r}')
        else:
            out[name] = value
    return out


def _static(section: dict, problems: list[str]) -> str:
    """`[verify] static`, held to the rung grammar; the stock when absent."""
    try:
        value = text(section, SECTION, STATIC, STATIC_STOCK)
    except ConfigError as err:
        problems.append(str(err))
        return STATIC_STOCK
    problems.extend(_rung_grammar(value, f'[{SECTION}] {STATIC}', STATIC))
    return value


def _inputs(section: dict, problems: list[str]) -> dict[str, tuple[str, ...]]:
    """`[verify.inputs]`: rung name -> path prefixes, or {} when absent. A key
    that is not a rung, a value that is not a list of strings, an empty list
    and a path outside the checkout are each a named problem."""
    where = f'[{SECTION}.{INPUTS}]'
    if INPUTS not in section:
        return {}
    table = section[INPUTS]
    if not isinstance(table, dict):
        problems.append(f'{where} must be a table of `<rung> = [paths]`, got '
                        f'{table!r}')
        return {}
    _unknown_rungs(table, where, problems)
    scopes: dict[str, tuple[str, ...]] = {}
    for name in RUNGS:
        if name not in table:
            continue
        try:
            paths = relpath_tuple(table, f'{SECTION}.{INPUTS}', name, ())
        except ConfigError as err:
            problems.append(str(err))
            continue
        cleaned = tuple(_prefix(path) for path in paths)
        if not cleaned or any(not path for path in cleaned):
            problems.append(
                f'{where} {name} must name at least one path, each non-empty '
                f'— an empty scope would key a verdict on nothing, and a '
                f'state over 0 files is refused (hard rule 4). Delete the '
                f'key to scope the rung on the whole tree')
            continue
        scopes[name] = cleaned
    return scopes


def _unknown_rungs(keys, where: str, problems: list[str]) -> None:
    """A sub-table key that is not a rung; a retired rung is named as such."""
    for key in sorted(set(keys) - set(RUNGS)):
        problems.append(
            f'{where} {key}: {RETIRED_RUNGS[key]}' if key in RETIRED_RUNGS
            else f'{where} names {key!r}, and the rungs are '
                 f'{", ".join(RUNGS)} — a setting for a rung that does not '
                 f'exist never applies')


def _prefix(path: str) -> str:
    """One scope entry as a prefix: no leading `./` and no trailing slash."""
    path = path.strip()
    while path.startswith('./'):
        path = path[2:]
    return path.rstrip('/')


def _message(problems: list[str]) -> str:
    """One problem reads as itself; several read as a list, all of them named."""
    if len(problems) == 1:
        return problems[0]
    return (f'[{SECTION}] {len(problems)} problems:\n  - '
            + '\n  - '.join(problems))


def _rung(section: dict, key: str, problems: list[str]) -> str | None:
    """One rung: `milestone` is required, the other two legally absent."""
    where = f'[{SECTION}] {key}'
    if key not in section:
        if key != REQUIRED_RUNG:
            return None
        problems.append(
            f'{where} is required — it is the close, the rung that verifies '
            f'everything, and a ladder without it would fall back to running '
            f'nothing')
        return None
    try:
        value = text(section, SECTION, key, '')
    except ConfigError as err:
        problems.append(str(err))
        return None
    problems.extend(_rung_grammar(value, where, key))
    return value


def _rung_grammar(value: str, where: str, key: str) -> list[str]:
    """`make <target>` — exactly two words, the second a make goal (D3)."""
    words = value.split()
    if len(words) == 2 and words[0] == RUNG_PROGRAM and value == ' '.join(words) \
            and gates_extra.TARGET.fullmatch(words[1]) \
            and len(words[1]) <= gates_extra.MAX_LENGTH:
        return []
    return [
        f'{where} is {value!r} — a rung NAMES a make target the project '
        f'already has, spelled `{RUNG_PROGRAM} <target>` and nothing else '
        f'(for example `{key} = "{RUNG_PROGRAM} {key}"`). D3 rejected a rung '
        f'that carries its own command string: the Makefile stays the '
        f'authority on what a target RUNS, and two answers to "did the full '
        f'gate pass" is a second scoreboard. A target is '
        f'{gates_extra.TARGET.pattern} and at most {gates_extra.MAX_LENGTH} '
        f'characters']
