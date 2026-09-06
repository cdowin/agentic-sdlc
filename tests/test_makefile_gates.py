"""test_makefile_gates.py — this repo's own gates ARE the shipped framework.

The devkit is the first consumer of what it ships: `Makefile` is a consumer's
Makefile — `DEVKIT` set to this working tree installed on itself, then
`include Makefile.devkit` — and `Makefile.tiers` is the tier file a language
kit would write. The include is proven on fixtures in test_makefile_include.py;
what is proven HERE is this tree: `make check` runs for real through the real
funnel and prints ONE verdict line naming `.gate-reports/check.log`; every tier
target routes through `$(call gdk_gate,…)`; the installed framework files are
byte-current with their source; and the matrix hands each interpreter the
right command, proven against a stand-in `uv`.

Every case spawns `make` against REPO_ROOT rather than a scratch tree, because
what it tests IS this repo's Makefile. That makes them the only tests in the
suite that share one mutable thing — `.gate-reports/` and the ledger — so they
carry `xdist_group` and serialise against each other and nothing else.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import REPO_ROOT  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / 'src'))
from agentic_sdlc.repo import install  # noqa: E402

pytestmark = [
    pytest.mark.skipif(shutil.which('make') is None
                       or shutil.which('bash') is None,
                       reason='needs make and bash'),
    # A LIST: `pytestmark` is one name, and two assignments is one assignment.
    pytest.mark.xdist_group(name='the-real-repo'),
]

MAKEFILE = REPO_ROOT / 'Makefile'
TIERS = REPO_ROOT / 'Makefile.tiers'
VERDICT = re.compile(r'^\[CHECK\] .+ — full log: \.gate-reports/check\.log$')


def make(*args: str, **env_extra: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    # Under `make test` the recipe's shell carries MAKELEVEL/MAKEFLAGS, and a
    # sub-make that inherits them announces itself ahead of the one verdict
    # line these tests read. VERBOSE is the same shape one layer up: the
    # installed CI exports it for the whole `make milestone` step. The default
    # these tests speak of is VERBOSE UNSET.
    for leaked in ('MAKELEVEL', 'MAKEFLAGS', 'MFLAGS', 'VERBOSE'):
        env.pop(leaked, None)
    # The cost recorder is OFF unless a case asks for it: `make check` files a
    # real `kind: gate` row through GDK_LEDGER_CMD, and a suite that left it on
    # would append one to this repo's own ledger on every run. ASSIGNED, not
    # `setdefault` — the include EXPORTS it, so under `make test` the recipe's
    # environment already carries the real recorder. An EMPTY value is still a
    # defined make variable, so the include's `?=` keeps it.
    env['GDK_LEDGER_CMD'] = ''
    env.update(env_extra)
    return subprocess.run(['make', *args], cwd=REPO_ROOT, text=True,
                          capture_output=True, env=env)


def recipes(path: Path) -> dict[str, str]:
    """Every target in one makefile mapped to its recipe body, asked of the
    file rather than of a list here: a second roster is a roster that goes
    stale, and the point is to catch a target nobody told this file about."""
    found: dict[str, list[str]] = {}
    current = None
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.startswith('\t'):
            if current is not None:
                found[current].append(line)
            continue
        match = re.match(r'^([a-z][a-z0-9_-]*):(?!=)', line)
        current = match.group(1) if match else None
        if current is not None:
            found.setdefault(current, [])
    return {name: '\n'.join(body) for name, body in found.items()}


# --- the shape: a consumer's Makefile, and the framework byte-current ---------
def test_this_repo_is_a_consumer_of_the_framework_it_ships():
    """The bug this closed: the root Makefile hand-wrote a parallel framework,
    so `make precommit` here and in a consumer were two programs sharing a
    name. Now it is the include and the tiers, and both installed files are
    the installables — a copy edited in place is the invisible fork."""
    text = MAKEFILE.read_text(encoding='utf-8')
    assert re.search(r'^include Makefile\.devkit$', text, re.M), text
    assert re.search(r'^DEVKIT\s*:?=\s*(\$\(UV\)|uv) run', text, re.M), (
        'DEVKIT must be this working tree installed on itself')
    assert 'PYTHONPATH' not in text, 'the gates run an installed package, never a path hack'
    for name, rel in install.PLANS['install-gates']:
        target = REPO_ROOT / rel
        assert target.is_file(), f'{rel} is not installed here'
        assert target.read_text(encoding='utf-8') == install.body_of(name), (
            f'{rel} differs from installables/{name} — edit the source and '
            f're-install with --force')


def test_every_tier_target_routes_through_the_shipped_helper():
    """The census: no target in the tier file gets to stay loud."""
    gates = {name: body for name, body in recipes(TIERS).items() if body.strip()}
    assert len(gates) >= 5, (
        f'census collapsed to {sorted(gates)} — a parse that finds no targets '
        f'would pass this file vacuously')
    loud = sorted(name for name, body in gates.items()
                  if 'gdk_gate_verdict' not in body
                  and '$(call gdk_gate,' not in body)
    assert not loud, (
        f'{loud} print whatever their tool prints instead of one verdict line; '
        f'route them through $(call gdk_gate,...) or gdk_gate_verdict')


# --- the behavior, on the one target fast enough to prove it -----------------
def test_a_gate_prints_exactly_one_verdict_line_naming_its_log():
    done = make('check')
    assert done.returncode == 0, done.stdout + done.stderr
    lines = done.stdout.splitlines()
    assert len(lines) == 1, done.stdout
    assert VERDICT.match(lines[0]), lines[0]
    log = REPO_ROOT / '.gate-reports' / 'check.log'
    assert log.exists(), 'the verdict named a log that was never written'
    assert '[check:doc]' in log.read_text(encoding='utf-8'), (
        'the transcript the verdict points at does not hold the run')


def test_an_ambient_verbose_does_not_turn_the_quiet_run_loud(monkeypatch):
    monkeypatch.setenv('VERBOSE', '1')
    test_a_gate_prints_exactly_one_verdict_line_naming_its_log()


def test_verbose_streams_the_transcript_and_still_ends_with_the_verdict():
    done = make('check', VERBOSE='1')
    assert done.returncode == 0, done.stdout + done.stderr
    lines = done.stdout.splitlines()
    assert len(lines) > 1, 'VERBOSE=1 printed no more than the verdict'
    assert '[check:doc]' in done.stdout
    assert VERDICT.match(lines[-1]), lines[-1]


def test_a_failing_gate_shows_what_broke_and_exits_nonzero():
    """The quiet default is only safe if a FAILURE is still legible without
    going to find the log."""
    done = make('check', 'DEVKIT=uv run -q agentic-sdlc check nosuchcheck')
    assert done.returncode != 0
    assert 'nosuchcheck' in done.stdout + done.stderr, done.stdout + done.stderr
    verdict = [ln for ln in done.stdout.splitlines() if ln.startswith('[CHECK]')]
    assert len(verdict) == 1, done.stdout
    assert 'FAIL' in verdict[0], verdict[0]


# --- the cost row, on a REAL gate run through the real funnel -----------------
# The include exports GDK_LEDGER_CMD, `gdk_gate_log` opens the slot,
# `gdk_gate_verdict` closes it, and one row lands. The recorder is a STUB, so
# the case asserts the argv the funnel handed on and never touches this repo's
# own ledger.
RECORDER = """#!/usr/bin/env bash
{ printf 'CALL'; for a in "$@"; do printf ' ARG[%s]' "$a"; done; printf '\\n'
} >> "$GDK_TEST_ROWS"
exit "${GDK_TEST_EXIT:-0}"
"""


@pytest.fixture()
def recorder(tmp_path):
    script = tmp_path / 'recorder.sh'
    script.write_text(RECORDER, encoding='utf-8')
    rows = tmp_path / 'rows.txt'
    rows.write_text('', encoding='utf-8')
    return script, rows


def test_a_real_gate_run_files_exactly_one_cost_row(recorder):
    script, rows = recorder
    done = make('check', GDK_LEDGER_CMD=f'bash {script}', GDK_TEST_ROWS=str(rows))
    assert done.returncode == 0, done.stdout + done.stderr
    filed = rows.read_text(encoding='utf-8').splitlines()
    assert len(filed) == 1, filed
    assert 'ARG[ledger] ARG[record]' in filed[0], filed[0]
    assert 'ARG[--gate] ARG[check]' in filed[0], filed[0]
    assert 'ARG[--verdict] ARG[PASS]' in filed[0], filed[0]
    assert re.search(r'ARG\[--duration-ms\] ARG\[[0-9]+\]', filed[0]), filed[0]
    # No census was set by this gate, so the flag is OMITTED — never a `0`.
    assert 'ARG[--census]' not in filed[0], filed[0]
    lines = done.stdout.splitlines()
    assert len(lines) == 1 and VERDICT.match(lines[0]), done.stdout


@pytest.mark.parametrize('broken', ['exits-nonzero', 'does-not-exist'])
def test_a_broken_recorder_never_changes_the_gates_verdict(recorder, broken,
                                                           tmp_path):
    """This funnel is on the path of every gate in every consumer, so a ledger
    that cannot be written is never a gate failure."""
    script, rows = recorder
    env = {'GDK_TEST_ROWS': str(rows)}
    if broken == 'exits-nonzero':
        env['GDK_LEDGER_CMD'] = f'bash {script}'
        env['GDK_TEST_EXIT'] = '3'
    else:
        env['GDK_LEDGER_CMD'] = str(tmp_path / 'no-such-recorder')
    done = make('check', **env)
    assert done.returncode == 0, done.stdout + done.stderr
    lines = done.stdout.splitlines()
    assert len(lines) == 1 and VERDICT.match(lines[0]), done.stdout


def test_an_unset_recorder_spawns_nothing_at_all(recorder):
    """A consumer with no PM tree pays zero — no subprocess, no sentinel."""
    script, rows = recorder
    done = make('check', GDK_TEST_ROWS=str(rows))
    assert done.returncode == 0, done.stdout + done.stderr
    assert rows.read_text(encoding='utf-8') == ''


# --- the matrix: which interpreter was handed which command ------------------
# `make matrix` is four real interpreters and a quarter of an hour, so the
# recipe is proven against a STAND-IN `uv` that records the argv it was handed
# and exits 0. The question here is not whether pytest passes on 3.13 — the
# matrix itself answers that — it is WHICH COMMAND each interpreter got, and
# that is the one thing a census over the Makefile text cannot answer. `-m "not
# shell"` has to survive make's expansion, a backslash-continued recipe line and
# the shell's word splitting as ONE argv element; a grep for the string in the
# recipe body would pass just as happily on a recipe that hands pytest `-m not`
# and a positional path called `shell`.
#
# PY_FLOOR / PY_MATRIX are operator configuration, not untrusted input: the
# refusal rows below are the plausible MISTAKE (bumping one without the other,
# a floor that is a prefix of a listed version), not shell injection through a
# make variable, which no recipe in this file survives and none pretends to.
UV_RECORDER = """\
#!/usr/bin/env python3
"a stand-in `uv`: record the argv, run nothing, exit 0."
import json
import os
import sys



with open(os.environ['GDK_ARGV_LOG'], 'a', encoding='utf-8') as handle:
    handle.write(json.dumps(sys.argv[1:]) + '\\n')
"""


def declared(name: str) -> str:
    """A `?=` default read out of Makefile.tiers, like `recipes()` reads
    bodies — a second copy of PY_FLOOR here is a copy that goes stale."""
    match = re.search(rf'^{name}\s*\?=\s*(.*?)\s*$',
                      TIERS.read_text(encoding='utf-8'), re.M)
    assert match, f'{name} is no longer declared in Makefile.tiers'
    return match.group(1)


def pytest_argv(argv: list[str]) -> list[str]:
    """What pytest itself was handed: everything after `-m pytest`.

    The split matters — `python -m pytest` puts a `-m` in the argv that has
    nothing to do with marker selection, and a naive `'-m' in argv` reads it.
    """
    for i in range(len(argv) - 1):
        if argv[i] == '-m' and argv[i + 1] == 'pytest':
            return argv[i + 2:]
    raise AssertionError(f'no `-m pytest` in the recorded argv: {argv}')


def interpreter_of(argv: list[str]) -> str:
    """The `--python <version>` this `uv run` was given."""
    return argv[argv.index('--python') + 1]


def marker_of(argv: list[str]) -> str | None:
    """The marker expression pytest was given, as ONE argv element, or None."""
    args = pytest_argv(argv)
    return args[args.index('-m') + 1] if '-m' in args else None


def matrix_run(tmp_path: Path, *args: str) -> tuple[subprocess.CompletedProcess,
                                                    list[list[str]]]:
    """`make matrix` against the recording stand-in. Returns (proc, argv rows)."""
    recorder = tmp_path / 'uv-recorder'
    recorder.write_text(UV_RECORDER, encoding='utf-8')
    recorder.chmod(0o755)
    argv_log = tmp_path / 'argv.jsonl'
    reports = tmp_path / 'reports'
    done = make('matrix', f'UV={recorder}', *args,
                GDK_ARGV_LOG=str(argv_log), GDK_GATE_REPORT_DIR=str(reports))
    rows = ([json.loads(line) for line in
             argv_log.read_text(encoding='utf-8').splitlines()]
            if argv_log.exists() else [])
    return done, rows


def test_the_floor_is_handed_the_whole_suite_and_the_others_not_shell(tmp_path):
    """~85% of this suite's wall clock is `subprocess`, and a spawn is not
    something a Python version changes. One interpreter runs all of it; the
    others run the part an interpreter can break."""
    done, rows = matrix_run(tmp_path)
    assert done.returncode == 0, done.stdout + done.stderr
    floor, versions = declared('PY_FLOOR'), declared('PY_MATRIX').split()

    assert [interpreter_of(row) for row in rows] == versions, (
        f'the matrix ran {[interpreter_of(r) for r in rows]}, not {versions}')
    full = [interpreter_of(row) for row in rows if marker_of(row) is None]
    assert full == [floor], (
        f'{full} were handed the whole suite; exactly the floor ({floor}) '
        f'should be. Two full passes waste the minutes this exists to save; '
        f'none means the shell slice ran nowhere.')
    for row in rows:
        version = interpreter_of(row)
        if version == floor:
            continue
        assert marker_of(row) == 'not shell', (
            f'python {version} was handed {pytest_argv(row)} — the marker '
            f'expression must arrive as one argv element, or pytest reads '
            f'`shell` as a path and collects nothing')


def test_the_floor_is_the_declared_one_not_merely_the_first_listed(tmp_path):
    """The rule is `== PY_FLOOR`, and a recipe that just gave the first
    iteration the full pass would be green on this repo's own defaults."""
    done, rows = matrix_run(tmp_path, 'PY_FLOOR=3.12', 'PY_MATRIX=3.11 3.12 3.13')
    assert done.returncode == 0, done.stdout + done.stderr
    assert [interpreter_of(row) for row in rows] == ['3.11', '3.12', '3.13']
    assert [interpreter_of(r) for r in rows if marker_of(r) is None] == ['3.12']


def test_a_floor_listed_twice_still_buys_exactly_one_full_pass(tmp_path):
    done, rows = matrix_run(tmp_path, 'PY_FLOOR=3.11', 'PY_MATRIX=3.11 3.11 3.12')
    assert done.returncode == 0, done.stdout + done.stderr
    assert len(rows) == 3
    assert [marker_of(row) for row in rows] == [None, 'not shell', 'not shell'], (
        'the FIRST occurrence of the floor takes the full pass; a repeat is '
        'another interpreter run, not a second full suite')


def test_the_transcript_says_what_each_interpreter_ran(tmp_path):
    """`matrix.log` is what a red run gets read for. A header that says only
    `=== python 3.13 ===` leaves the reader unable to tell a count that dropped
    because the slice skipped it from a count that dropped because tests
    vanished."""
    done, _ = matrix_run(tmp_path)
    assert done.returncode == 0, done.stdout + done.stderr
    transcript = (tmp_path / 'reports' / 'matrix.log').read_text(encoding='utf-8')
    floor = declared('PY_FLOOR')
    for version in declared('PY_MATRIX').split():
        ran = 'the whole suite' if version == floor else '-m "not shell"'
        assert f'=== python {version} ({ran}) ===' in transcript, transcript


def test_the_verdict_line_did_not_move(tmp_path):
    """The consumer-visible shape. CI reads this line and nothing else, so the
    slice is invisible from outside: same tag, same message, same log clause."""
    done, _ = matrix_run(tmp_path)
    assert done.returncode == 0, done.stdout + done.stderr
    lines = done.stdout.splitlines()
    assert len(lines) == 1, done.stdout
    assert lines[0] == (f'[MATRIX] PASS on {declared("PY_MATRIX")} '
                        f'— full log: {tmp_path / "reports" / "matrix.log"}')


# --- the refusal matrix: no configuration silently skips the full pass --------
@pytest.mark.parametrize('why, floor, versions', [
    ('the floor was bumped and the matrix was not', '3.99', '3.11 3.12 3.13 3.14'),
    ('an empty matrix has nowhere to run anything', '3.11', ''),
    ('an empty floor names no interpreter at all', '', '3.11 3.12'),
    ('a floor that is only a PREFIX of a listed version', '3.1', '3.11 3.12'),
    ('a floor that is only a SUFFIX of a listed version', '11', '3.11 3.12'),
    ('a floor glued to its neighbour', '3.11 3.12', '3.11 3.12'),
    ('a glob is not an interpreter roster', '3.11', '*'),
])
def test_a_floor_outside_the_matrix_is_refused_before_anything_runs(
        tmp_path, why, floor, versions):
    """The failure this whole change could introduce: a matrix in which nobody
    runs the `shell` slice, printing PASS over a suite that never ran. It is
    refused by name, ahead of the first interpreter, and NOTHING is spawned."""
    done, rows = matrix_run(tmp_path, f'PY_FLOOR={floor}', f'PY_MATRIX={versions}')
    assert done.returncode == 2, (
        f'{why}: exited {done.returncode}\n{done.stdout}{done.stderr}')
    assert rows == [], f'{why}: refused, but {len(rows)} interpreter(s) ran anyway'
    output = done.stdout + done.stderr
    assert f'PY_FLOOR "{floor}"' in output, f'{why}: the floor is unnamed\n{output}'
    assert f'PY_MATRIX "{versions}"' in output, f'{why}: the matrix is unnamed\n{output}'


def test_the_refusal_is_one_verdict_line_like_every_other_gate(tmp_path):
    done, _ = matrix_run(tmp_path, 'PY_FLOOR=3.99')
    lines = done.stdout.splitlines()
    assert len(lines) == 1, done.stdout
    assert lines[0].startswith('[MATRIX] '), lines[0]
    assert lines[0].endswith(f'— full log: {tmp_path / "reports" / "matrix.log"}')
