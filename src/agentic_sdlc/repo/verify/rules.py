"""rules.py — `[verify]` read once, into three rungs, or refused with exit 2.

Three rungs, `story`, `feature` and `milestone`, each naming a make target
the project already has (D3): `story = "make unit"`. `milestone` is required;
the other two may be absent, and the verb names the absence rather than
running the rung above. A retired key — `wide`, or the `narrow` table that
was the story rung when it selected commands by changed path — is refused by
name. Spawns nothing, reads no file.
"""
from __future__ import annotations

from dataclasses import dataclass

from agentic_sdlc.core.config import ConfigError, text
from agentic_sdlc.repo import gates_extra

SECTION = 'verify'

# The ladder, narrow to wide. Every rung is a make target.
STORY = 'story'
FEATURE = 'feature'
MILESTONE = 'milestone'
RUNGS = (STORY, FEATURE, MILESTONE)

# A repo with no `milestone` has no close; `story` and `feature` may be absent.
REQUIRED_RUNG = MILESTONE

# Refused by name, so an author is not left guessing at "unknown key". `narrow`
# is both `[verify] narrow = …` and `[[verify.narrow]]`: TOML lands them on
# the same key.
NARROW = 'narrow'
RETIRED = {
    'wide': (f'[{SECTION}] wide was renamed to {MILESTONE} (decision D3) — '
             f'and {MILESTONE} names a make target the project already has, '
             f'not a command of its own: `{MILESTONE} = "make {MILESTONE}"`. '
             f'Left as wide this section declares no close at all'),
    NARROW: (f'[{SECTION}] {NARROW} is retired: the story rung is a make '
             f'target now, `{STORY} = "make <target>"`, run the way the other '
             f'two rungs are — it no longer selects commands by changed path. '
             f'Delete every [[{SECTION}.{NARROW}]] table and declare the one '
             f'line'),
}

# A rung that could name any program could drift from the Makefile (D3).
RUNG_PROGRAM = 'make'

# Rule 6: a `[verify]` mistake is always 2, never 1.
EXIT_CONFIG = 2

SECTION_KEYS = frozenset(RUNGS)


@dataclass(frozen=True)
class Ladder:
    """The three rungs' commands. `story` and `feature` are None when
    unconfigured, so the verb can name that rather than skip it."""

    milestone: str
    story: str | None = None
    feature: str | None = None

    def rung(self, name: str) -> str | None:
        """One rung's command by rung name, or None when unconfigured."""
        return getattr(self, name)


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
            f'{", ".join(RUNGS)}; a typo here is a setting that never applies')
    rungs = {name: _rung(section, name, problems) for name in RUNGS}
    if problems:
        raise ConfigError(_message(problems))
    return Ladder(milestone=rungs[MILESTONE] or '', story=rungs[STORY],
                  feature=rungs[FEATURE])


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
