"""config.py — typed `devkit.toml` reading.

Separate from `project.py` because they answer different questions: project.py
finds the repo and loads the file, this decides what a value is allowed to be.

Every coercion here refuses rather than converts. That is the whole point: a
BARE STRING is iterable, so `exclude_prefixes = "addons/"` under a plain
`tuple(...)` becomes ('a','d','d','o','n','s','/') and excludes almost the
entire tree — after which the gate scans nothing and prints PASS. That defect
shipped in v0.9.0 in seven of eight config sections, because the guard was
written once for `[pm]` and never carried across. One reader is the fix.
"""
from __future__ import annotations

from agentic_sdlc.core.project import load_config


class ConfigError(Exception):
    """A malformed `devkit.toml` value. Exit 2 — a typo is NOT a finding.

    Exit 1 is reserved for findings, so CI must never read a config mistake as
    "drift found". Worse is the silent case this class exists to prevent: a
    BARE STRING is iterable, so `exclude_prefixes = "addons/"` coerced with
    `tuple(...)` becomes ('a','d','d','o','n','s','/') and excludes almost the
    whole tree — the gate then scans nothing and prints PASS.
    """


def config_section(name: str) -> dict:
    """One `devkit.toml` section, or {}. Refuses a non-table."""
    value = load_config().get(name, {})
    if not isinstance(value, dict):
        raise ConfigError(f'[{name}] must be a table, got {value!r}')
    return value


def section_declared(name: str) -> bool:
    """Is `[name]` PRESENT in devkit.toml at all — even declared empty?

    `config_section` cannot answer this: an absent table and an empty one both
    read as {}. A section a release RETIRED has to be named on either spelling,
    because the author of the empty one believes it took effect just as much.
    """
    return name in load_config()


def str_tuple(sect: dict, name: str, key: str,
              fallback: tuple[str, ...]) -> tuple[str, ...]:
    """A list-of-strings setting. A bare string is REFUSED, never iterated."""
    value = sect.get(key)
    if value is None:
        return fallback
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ConfigError(
            f'[{name}] {key} must be a list of strings, got {value!r}'
            + (f' — write {key} = [{value!r}]' if isinstance(value, str) else ''))
    if not value:
        # An empty list reads as "nothing", but downstream it usually means the
        # opposite: `git ls-files` with no pathspec is the ENTIRE repo. Refuse
        # rather than let a value mean the reverse of what it looks like.
        raise ConfigError(
            f'[{name}] {key} is empty — remove the key to take the default '
            f'({" ".join(fallback) or "none"}) rather than declaring nothing')
    return tuple(value)


def text(sect: dict, name: str, key: str, fallback: str) -> str:
    value = sect.get(key, fallback)
    if not isinstance(value, str):
        raise ConfigError(f'[{name}] {key} must be a string, got {value!r}')
    return value


def _escapes_checkout(value: str) -> str | None:
    """Why this config value names a path outside the checkout, by SHAPE alone.

    Decided before anything is opened, for `ready_for._pointer_defect`'s
    reason: hard rule 8 is a claim about what this package READS, and a claim
    tested by reading is not the claim. That function is the peer of this one
    one layer up — it grades a `reviewed:` pointer written in a grain document
    and answers with a BLOCKER string at exit 1, because a malformed document
    is a finding. This grades a devkit.toml VALUE and answers with a
    `ConfigError` at exit 2, because a malformed config is not a finding
    (rule 6). Same shapes, two different verdicts, and the difference is which
    of the two is a fact about the tree.

    Only what actually leaves the checkout is refused. A `.` segment, a
    trailing slash and a `*` all stay inside, and every one of them is a
    spelling somebody's `devkit.toml` may already carry — refusing them would
    break trees this package has no finding against.
    """
    if '://' in value or value.lower().startswith('file:'):
        return 'is a URL, and nothing here is fetched'
    if value.startswith('/'):
        return 'is absolute; every path key is relative to the repo root'
    if value.startswith('~'):
        return 'is home-relative, and nothing here is expanded'
    if '\\' in value:
        return 'carries a backslash, which is not a path separator here'
    if len(value) > 1 and value[1] == ':' and value[0].isalpha():
        return 'names a drive; every path key is relative to the repo root'
    if '..' in value.split('/'):
        return 'climbs out with a `..` segment'
    return None


def relpath(sect: dict, name: str, key: str, fallback: str) -> str:
    """A path setting: `text`, plus "and it is inside this checkout".

    `text` has no opinion about paths, so every key naming one — `[pm]
    roadmap_dir`, `review_dir`, `template_dir` — took an absolute or `../`
    value and this package went and read there. Measured 2026-09-05:
    `roadmap_dir = "../tmp.XXXX"` made `check grain-shape` report OVER CAP
    findings about two documents outside the checkout, `check pm` PASS over a
    tree in /tmp, and `template_dir = "../tmp.XXXX/tpl"` made `pm templates`
    WRITE six files outside it. The absolute spelling of the same value did not
    even get that far: it reached `Path.relative_to` and raised an uncaught
    `ValueError` at exit **1**, which a consumer's CI reads as drift found.
    Rule 8 and rule 6, from one unguarded `text()`.

    ONE validator, called at each read site — the same shape `text` itself has.
    A second implementation for the second reader of a key is a second answer,
    and `roadmap_dir` has two readers (`repo/pm/model` and `checks/grain_shape`)
    that must not disagree about which trees exist.
    """
    value = text(sect, name, key, fallback)
    defect = _escapes_checkout(value)
    if defect is not None:
        raise ConfigError(
            f'[{name}] {key} must name a path inside this checkout, got '
            f'{value!r} — it {defect}')
    return value


def flag(sect: dict, name: str, key: str, fallback: bool) -> bool:
    value = sect.get(key, fallback)
    if not isinstance(value, bool):
        raise ConfigError(f'[{name}] {key} must be true/false, got {value!r}')
    return value


def table(sect: dict, name: str, key: str, fallback: dict) -> dict:
    """A table-of-tables setting. A string or list is REFUSED, never walked."""
    value = sect.get(key, fallback)
    if not isinstance(value, dict):
        raise ConfigError(f'[{name}] {key} must be a table, got {value!r}')
    return value


def table_array(sect: dict, name: str, key: str,
                fallback: tuple[dict, ...] = ()) -> tuple[dict, ...]:
    """An ARRAY OF TABLES setting — TOML's `[[section.key]]`, ordered.

    The list form of `table`, and the same refusals one dimension up. A bare
    string is the dangerous spelling: `narrow = "paths = x"` is what an author
    writes when they forget the double brackets, and iterating it yields its
    CHARACTERS — the v0.9.0 shape this module exists to prevent, which would
    here become one unusable "rule" per letter. Refused whole, never walked.

    Order is preserved and every element keeps its 1-based DECLARATION index,
    because the caller's error messages have to name the entry the author
    wrote: a rule silently dropped from a list is worse than a refusal.

    Absent takes the fallback; an empty list is refused, for `str_tuple`'s
    reason — an empty list reads as "nothing" and downstream usually means the
    opposite of nothing.
    """
    value = sect.get(key)
    if value is None:
        return tuple(fallback)
    if not isinstance(value, list):
        raise ConfigError(
            f'[{name}] {key} must be an array of tables — write '
            f'[[{name}.{key}]] blocks, got {value!r}')
    if not value:
        raise ConfigError(
            f'[{name}] {key} is empty — remove the key (or the whole [{name}] '
            f'section) rather than declaring nothing')
    for index, entry in enumerate(value, start=1):
        if not isinstance(entry, dict):
            raise ConfigError(
                f'[{name}.{key}] #{index} must be a table, got {entry!r}')
    return tuple(value)


def str_tuple_table(sect: dict, name: str, key: str,
                    fallback: dict[str, tuple[str, ...]]) -> dict[str, tuple[str, ...]]:
    """A table mapping names to lists of strings — `str_tuple`, one level down.

    A bare-string VALUE is accepted as a ONE-ELEMENT list: it is the documented
    shorthand (`suffixes = { Manager = "emits" }`) and, taken whole, it cannot
    fall into the character-iteration trap this module exists to prevent —
    nothing here ever iterates it. Anything else non-list is REFUSED, and so is
    an empty list (remove the entry rather than declaring nothing).
    """
    raw = sect.get(key)
    if raw is None:
        return dict(fallback)
    if not isinstance(raw, dict):
        raise ConfigError(f'[{name}] {key} must be a table, got {raw!r}')
    out: dict[str, tuple[str, ...]] = {}
    for entry, names in raw.items():
        if isinstance(names, str):
            out[entry] = (names,)
        elif (isinstance(names, list) and names
              and all(isinstance(n, str) for n in names)):
            out[entry] = tuple(names)
        else:
            raise ConfigError(
                f'[{name}] {key}.{entry} must be a string or a non-empty list '
                f'of strings, got {names!r}')
    return out


def number_table(sect: dict, name: str, key: str,
                 fallback: dict[str, int]) -> dict[str, int]:
    """A table mapping names to INTEGERS — `number`, one level down.

    A ledger (`{path = 956}`) and an arity floor (`{"Save.write" = 2}`) are the
    same shape, and both are read as "how many" by code that would otherwise
    silently compare an int against a string. A bool is refused with everything
    else: `true` is an `int` in Python and would arrive as 1.
    """
    raw = sect.get(key)
    if raw is None:
        return dict(fallback)
    if not isinstance(raw, dict):
        raise ConfigError(f'[{name}] {key} must be a table, got {raw!r}')
    out: dict[str, int] = {}
    for entry, value in raw.items():
        if not isinstance(value, int) or isinstance(value, bool):
            raise ConfigError(
                f'[{name}] {key}.{entry} must be an integer, got {value!r}')
        out[entry] = value
    return out


def pattern(sect: dict, name: str, key: str, fallback: str) -> str:
    """A regex setting, COMPILED at load so a bad one is exit 2, not a finding."""
    import re as _re
    value = text(sect, name, key, fallback)
    try:
        _re.compile(value)
    except _re.error as err:
        raise ConfigError(f'[{name}] {key} is not a valid regex: {err}') from err
    return value


def number(sect: dict, name: str, key: str, fallback: int) -> int:
    value = sect.get(key, fallback)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ConfigError(f'[{name}] {key} must be an integer, got {value!r}')
    return value
