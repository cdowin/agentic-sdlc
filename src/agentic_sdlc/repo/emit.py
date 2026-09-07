"""emit.py — one event, WRITTEN to a declared sink; nothing here is ever run.

0.5.0/D1. Declaring `[emit]` turns emission ON; a tree with no section emits
nothing, and a courier the consumer arms carries the rows onward. Nothing here
spawns, imports a module named in config or resolves a string to a callable —
held shut by AST in `tests/test_boundaries.py` — and an unreachable sink is a
FINDING (rule 11), never a crash, never silence, never a verdict."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import NamedTuple

from agentic_sdlc.core.config import (ConfigError, config_section,
                                      relpath, section_declared, str_tuple)
from agentic_sdlc.repo.pm import ledger

SECTION = 'emit'
SINK_KEY = 'sink'
KINDS_KEY = 'kinds'

# The sink WORDS; anything else is a path under the root (`./ledger` for a file).
SINK_LEDGER = 'ledger'
SINK_STDOUT = '-'

# Literal and UNPACKED rather than restated: a config default is folded with
# `ast.literal_eval` by `tests/test_config_seed.py`, and names do not fold.
TAPS = ('enter', 'verdict', 'leave')
TAP_ENTER, TAP_VERDICT, TAP_LEAVE = TAPS

FINDING_PREFIX = f'[{SECTION}]'

# What a SINK may go wrong with, all of it a finding: the filesystem (routing
# walk, append) and `dumps` refusing a row. A malformed `[emit]` is exit 2 (9).
SINK_ERRORS = (OSError, TypeError, ValueError)


class Settings(NamedTuple):
    """Where events go, and which taps make one."""
    sink: str
    kinds: tuple[str, ...]


def declared() -> bool:
    """Is `[emit]` in devkit.toml at all — which is not "did anything land"."""
    return section_declared(SECTION)


def settings() -> Settings:
    """`[emit]`, through the guards; a malformed value is exit 2, never a
    finding, and `relpath` holds a path sink inside the checkout (rule 8)."""
    sect = config_section(SECTION)
    sink = relpath(sect, SECTION, SINK_KEY, SINK_LEDGER)
    kinds = str_tuple(sect, SECTION, KINDS_KEY, TAPS)
    unknown = [kind for kind in kinds if kind not in TAPS]
    if unknown:
        raise ConfigError(
            f'[{SECTION}] {KINDS_KEY} names {len(unknown)} tap(s) this '
            f'version does not emit: {", ".join(repr(k) for k in unknown)} — '
            f'the taps are {", ".join(TAPS)}. A tap named and never emitted '
            f'is a sink a consumer waits on forever.')
    return Settings(sink, kinds)


def emit(cfg, tap: str, row: dict) -> str:
    """Write ONE event to the declared sink; '' when there is nothing to
    report, else the finding, already said on stderr. `row` is a whole row from
    the minters, whose `grain` ROUTES it (0.4.0/D1). A tree that declared no
    `[emit]` is silent HERE rather than at each caller — a guarantee every tap
    has to remember is one a tap forgets — and nothing a sink does raises."""
    if tap not in TAPS:
        raise ValueError(f'refusing to emit an event for {tap!r}: the taps '
                         f'are {", ".join(TAPS)}')
    if not declared():
        return ''
    conf = settings()
    if tap not in conf.kinds:
        return ''
    where = repr(conf.sink)
    try:
        if conf.sink == SINK_STDOUT:
            print(ledger.dumps(row), flush=True)
            return ''
        grain = _grain_of(row)
        target = _sink_file(cfg, conf.sink, grain)
        if target is None:
            return _finding(f'no milestone owns {grain}, so the {SINK_LEDGER} '
                            f'sink has nowhere to file its {tap} event; the '
                            f'command itself is unaffected')
        where = f'{conf.sink!r} ({cfg.rel(target)})'
        ledger.append_to(target, row)
    except SINK_ERRORS as err:
        return _finding(f'the {SINK_KEY} {where} could not be written '
                        f'({type(err).__name__}: {err}); the {tap} event was '
                        f'NOT recorded and the command itself is unaffected')
    return ''


def _sink_file(cfg, sink: str, grain: str) -> Path | None:
    """The file this sink names, or None when the ledger owns none: the word
    routes by GRAIN, and a row naming none lands in the tree's own ledger."""
    if sink != SINK_LEDGER:
        return cfg.root / sink
    if not grain:
        return ledger.grainless_path(cfg.roadmap)
    return ledger.ledger_of_grain(cfg, grain)


def _grain_of(row: dict) -> str:
    """The grain this row names, or '' — a merged row may hold any type."""
    grain = row.get('grain')
    return grain if isinstance(grain, str) else ''


def _finding(text: str) -> str:
    """Said on stderr AND handed back, so ignoring it does not swallow it."""
    line = f'{FINDING_PREFIX} WARNING — {text}'
    print(line, file=sys.stderr)
    return line
