"""Typed `devkit.toml` reading: every coercion refuses rather than converts.

A bare string is iterable, so a `tuple(...)` over `exclude_prefixes = "addons/"` would
exclude the whole tree and let a gate print PASS over nothing.
"""
from __future__ import annotations

from agentic_sdlc.core.project import load_config


class ConfigError(Exception):
    """A malformed `devkit.toml` value; exit 2, because a typo is not a finding."""


def config_section(name: str) -> dict:
    """One `devkit.toml` section, or {}. Refuses a non-table."""
    value = load_config().get(name, {})
    if not isinstance(value, dict):
        raise ConfigError(f'[{name}] must be a table, got {value!r}')
    return value


def section_declared(name: str) -> bool:
    """Is `[name]` present at all; `config_section` reads absent and empty both as {}."""
    return name in load_config()


def str_tuple(sect: dict, name: str, key: str,
              fallback: tuple[str, ...]) -> tuple[str, ...]:
    """A list-of-strings setting. A bare string is refused, never iterated."""
    value = sect.get(key)
    if value is None:
        return fallback
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ConfigError(
            f'[{name}] {key} must be a list of strings, got {value!r}'
            + (f' — write {key} = [{value!r}]' if isinstance(value, str) else ''))
    if not value:
        # An empty pathspec downstream usually means the ENTIRE repo, not nothing.
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
    """Why this value names a path outside the checkout, by shape alone, or None.

    Only what actually leaves is refused; `.`, a trailing slash and `*` stay inside.
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
    """A path setting: `text`, plus "inside this checkout" (hard rule 8)."""
    value = text(sect, name, key, fallback)
    defect = _escapes_checkout(value)
    if defect is not None:
        raise ConfigError(
            f'[{name}] {key} must name a path inside this checkout, got '
            f'{value!r} — it {defect}')
    return value


def relpath_tuple(sect: dict, name: str, key: str,
                  fallback: tuple[str, ...]) -> tuple[str, ...]:
    """`str_tuple`, plus "every entry is inside this checkout"; the message names which."""
    values = str_tuple(sect, name, key, fallback)
    for index, value in enumerate(values, start=1):
        defect = _escapes_checkout(value)
        if defect is not None:
            raise ConfigError(
                f'[{name}] {key} entry {index} of {len(values)} must name a '
                f'path inside this checkout, got {value!r} — it {defect}')
    return values


def flag(sect: dict, name: str, key: str, fallback: bool) -> bool:
    value = sect.get(key, fallback)
    if not isinstance(value, bool):
        raise ConfigError(f'[{name}] {key} must be true/false, got {value!r}')
    return value


def table(sect: dict, name: str, key: str, fallback: dict) -> dict:
    """A table-of-tables setting. A string or list is refused, never walked."""
    value = sect.get(key, fallback)
    if not isinstance(value, dict):
        raise ConfigError(f'[{name}] {key} must be a table, got {value!r}')
    return value


def table_array(sect: dict, name: str, key: str,
                fallback: tuple[dict, ...] = ()) -> tuple[dict, ...]:
    """An array of tables (`[[section.key]]`), in declaration order; an empty list is refused."""
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
    """A table of name -> list of strings; a bare-string value is the one-element shorthand."""
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
    """A table of name -> integer; a bool is refused because `True` would arrive as 1."""
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
    """A regex setting, compiled at load so a bad one is exit 2, not a finding."""
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
