"""test_runners_installable.py — the shell gate library, RUN rather than read.

`gdk_gate.sh` is the library every gate in a consumer routes through — this
package's own `Makefile` included. It is not Python, so the contract is proven
the way the hook corpus is: the script carries a `--self-test`, and this file
drives it through a subprocess and holds it to its published shape.

Three things this file adds on top of firing the corpus:

  - it MUTATES the verdict format and re-runs, so "the self-test passes" is
    evidence rather than a claim. A corpus that cannot fail is a green light
    wired to nothing.
  - it exercises the verdict line and its log path END TO END — sourcing the
    library into a scratch cwd and running a fake gate through
    gate_log -> gate_capture -> gate_verdict. That line shape is grepped by
    consumer Makefiles, so it is contract (CLAUDE.md rule 6), not cosmetics.
  - it holds the library to being LANGUAGE-NEUTRAL. 0.2.0 split this file in
    two: everything that acted on a Godot artifact — the `user://` HOME
    sandbox, the `project.godot` restore, the compile-sweep transcript readers
    and the import-cache rebuild — left with `godot-devkit`, and what stayed is
    the framework that reads an exit code, a stream and the clock. Decision D2:
    an installable belongs to the kit whose ARTIFACT it acts on, not the kit
    whose STRUCTURE it borrows. A toolchain name creeping back in is that split
    un-doing itself one helper at a time.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import REPO_ROOT  # noqa: E402

pytestmark = pytest.mark.skipif(shutil.which('bash') is None,
                                reason='needs bash')

INSTALLABLES = REPO_ROOT / 'src' / 'agentic_sdlc' / 'repo' / 'installables'
LIBRARY = INSTALLABLES / 'gdk_gate.sh'
SCRIPTS = (LIBRARY,)

# The one line shape a consumer greps. Changing it is a minor bump at least.
VERDICT = '[PARSE] PASS (2 files) — full log: .gate-reports/parse.log'


def run(*argv: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    # The installed CI exports VERBOSE=1 for the whole `make milestone` step,
    # and the quiet-by-default cases below are asked of the DEFAULT — VERBOSE
    # unset. A case that wants the stream sets it in its own env.
    env = {k: v for k, v in os.environ.items() if k != 'VERBOSE'}
    return subprocess.run(['bash', *argv], cwd=cwd, text=True,
                          capture_output=True, env=env)


# --- the corpus, fired -------------------------------------------------------
@pytest.mark.parametrize('script', SCRIPTS, ids=lambda p: p.stem)
def test_the_self_test_corpus_passes_and_reports_its_case_count(script):
    done = run(str(script), '--self-test')
    assert done.returncode == 0, done.stdout + done.stderr
    assert 'SELF-TEST OK' in done.stdout, done.stdout
    count = done.stdout.split('—')[1].split('case')[0].strip()
    assert int(count) > 0, f'a corpus of {count} cases proves nothing'


def test_the_library_corpus_FAILS_when_the_verdict_shape_is_broken(tmp_path):
    """Rule 4, applied to the corpus itself: a self-test that cannot go red is
    a false PASS with extra steps. Swap the em dash for a hyphen — the one
    byte a consumer's grep would feel — and the corpus must catch it."""
    mutant = tmp_path / LIBRARY.name
    mutant.write_text(
        LIBRARY.read_text(encoding='utf-8')
        .replace("'[%s] %s — full log: %s\\n'", "'[%s] %s - full log: %s\\n'"),
        encoding='utf-8')
    done = run(str(mutant), '--self-test')
    assert done.returncode == 1, done.stdout + done.stderr
    assert 'SELF-TEST FAIL' in done.stderr, done.stderr
    assert 'the verdict line shape' in done.stderr, done.stderr


def test_the_library_corpus_FAILS_when_capture_stops_reading_PIPESTATUS(tmp_path):
    """The load-bearing function, held to being able to go red. `head -c` is
    the last pipe element and exits 0, so a capture that reads `$?` reports
    every gate as passing — rule 4's read-side cardinal sin, in the one helper
    every target in this repo and every consumer Makefile runs through."""
    mutant = tmp_path / LIBRARY.name
    mutant.write_text(
        LIBRARY.read_text(encoding='utf-8')
        .replace('GDK_GATE_EXIT="${PIPESTATUS[0]}"', 'GDK_GATE_EXIT="$?"'),
        encoding='utf-8')
    done = run(str(mutant), '--self-test')
    assert done.returncode == 1, done.stdout + done.stderr
    assert 'capture reports the command exit code' in done.stderr, done.stderr


# --- the verdict line and its log, end to end --------------------------------
def test_a_gate_prints_one_verdict_line_naming_a_log_that_holds_the_stream(tmp_path):
    script = tmp_path / 'gate.sh'
    script.write_text(
        f'set -uo pipefail\n'
        f'source "{LIBRARY}"\n'
        'log="$(gdk_gate_log parse)"\n'
        'gdk_gate_capture "$log" -- printf "boot line\\nsweep line\\n"\n'
        'gdk_gate_verdict PARSE "PASS (2 files)" "$log"\n',
        encoding='utf-8')

    done = run(str(script), cwd=tmp_path)
    assert done.returncode == 0, done.stdout + done.stderr
    assert done.stdout.splitlines() == [VERDICT], done.stdout

    log = tmp_path / '.gate-reports' / 'parse.log'
    assert log.exists(), 'the verdict named a log that was never written'
    assert log.read_text(encoding='utf-8') == 'boot line\nsweep line\n'


def test_an_ambient_verbose_does_not_turn_the_quiet_case_loud(tmp_path, monkeypatch):
    """The installed CI (`ci-verify.yml`) exports VERBOSE=1 for the whole
    `make milestone` step, and this suite runs inside it. The quiet case
    above is asked of the DEFAULT, so it must hold whatever the caller's
    environment happens to say — red on every CI run before the helper
    dropped the variable, green under bare pytest on a Mac."""
    monkeypatch.setenv('VERBOSE', '1')
    test_a_gate_prints_one_verdict_line_naming_a_log_that_holds_the_stream(tmp_path)


@pytest.mark.parametrize('script', SCRIPTS, ids=lambda p: p.stem)
def test_a_self_test_verdict_is_one_line_whatever_the_ambient_verbose_says(script):
    """A corpus proves both settings on its own pinned cases; the value the
    caller exports is not one of them. The library's cap case inherited it and
    streamed its eight bytes INTO the verdict line — `01234567[gdk-gate]
    SELF-TEST OK …` — which is what a `VERBOSE=1` self-test, and so the
    installed CI, then read as the verdict."""
    done = subprocess.run(['bash', str(script), '--self-test'], text=True,
                          capture_output=True,
                          env=dict(os.environ, VERBOSE='1'))
    assert done.returncode == 0, done.stdout + done.stderr
    lines = done.stdout.splitlines()
    assert len(lines) == 1, done.stdout
    assert re.match(r'^\[[A-Za-z][A-Za-z-]*\] SELF-TEST OK — \d+ case\(s\)$',
                    lines[0]), lines[0]


def test_verbose_streams_the_same_transcript_the_log_holds(tmp_path):
    """VERBOSE is the escape hatch the quiet default is only safe because of:
    it must add the stream, not replace the verdict or skip the file."""
    script = tmp_path / 'gate.sh'
    script.write_text(
        f'set -uo pipefail\n'
        f'source "{LIBRARY}"\n'
        'log="$(gdk_gate_log parse)"\n'
        'gdk_gate_capture "$log" -- printf "boot line\\n"\n'
        'gdk_gate_verdict PARSE "PASS (2 files)" "$log"\n',
        encoding='utf-8')

    done = subprocess.run(['bash', str(script)], cwd=tmp_path, text=True,
                          capture_output=True, env={'PATH': '/usr/bin:/bin',
                                                    'VERBOSE': '1'})
    assert done.returncode == 0, done.stdout + done.stderr
    assert done.stdout.splitlines() == ['boot line', VERDICT], done.stdout
    assert (tmp_path / '.gate-reports' / 'parse.log').read_text(
        encoding='utf-8') == 'boot line\n'


# --- the argument surface: what the script REFUSES ---------------------------
@pytest.mark.parametrize('script', SCRIPTS, ids=lambda p: p.stem)
@pytest.mark.parametrize('argv', [
    ('--nope',),                 # an unknown verb
    ('-x',),                     # an unknown short flag
    ('--self-test', 'extra'),    # a known verb with an argument it does not take
    ('--help', '--self-test'),   # two verbs
    ('',),                       # an empty argument is not "no argument"
], ids=['unknown', 'short', 'verb-plus-extra', 'two-verbs', 'empty'])
def test_an_argument_the_script_does_not_take_is_refused_as_a_usage_error(script,
                                                                         argv):
    done = run(str(script), *argv)
    assert done.returncode == 2, (
        f'{script.name} {argv} -> {done.returncode}\n{done.stdout}{done.stderr}')
    # Exit 2 for the RIGHT reason: a refusal names the remedy. Without this the
    # empty-argument case passed off a downstream "library not found" as the
    # argument check working.
    assert '--help' in done.stdout + done.stderr, done.stdout + done.stderr


@pytest.mark.parametrize('script', SCRIPTS, ids=lambda p: p.stem)
def test_help_exits_zero_and_names_the_script(script):
    done = run(str(script), '--help')
    assert done.returncode == 0, done.stdout + done.stderr
    assert script.name in done.stdout, done.stdout


# --- D2: the framework half acts on no language's artifacts ------------------
# `0.2.0/the-middle-tier-splits/03-the-godot-roster-leaves`. The library was
# BOTH halves in one file: a gate framework that reads exit codes and streams,
# and a set of helpers that booted an engine and rewrote `project.godot`. The
# whole-tree form of this claim is tests/test_consumer_independence.py; this is
# the one file it was split out of, so it gets its own case with the reason
# attached.
ENGINE_WORDS = (r'godot', r'\.gd\b', r'\bengine\b', r'\bheadless\b',
                r'\bres://', r'\buser://')


def test_the_gate_library_names_no_engine_and_no_engine_artifact():
    body = LIBRARY.read_text(encoding='utf-8')
    hits = {pattern: [line for line in body.splitlines()
                      if re.search(pattern, line, re.IGNORECASE)]
            for pattern in ENGINE_WORDS}
    assert not any(hits.values()), {k: v for k, v in hits.items() if v}


# The names of the projects this library was extracted FROM, kept HERE, in the
# harness, as a tombstone — never in the package. A project name surviving in
# an installable is a fork wearing a library's name: the next consumer reads it
# as configuration it must match, and the fix that reaches one repo stops
# reaching the other. Word-bounded, so `trailing` is prose and `trail` is not.
# The whole-tree form of this claim is tests/test_consumer_independence.py.
CONSUMER_NAMES = (r'\bnullbound\b', r'\bNULLBOUND\b', r'\btrail\b', r'\bTRAIL\b')


@pytest.mark.parametrize('script', SCRIPTS, ids=lambda p: p.stem)
def test_no_installable_names_the_consumer_it_was_extracted_from(script):
    body = script.read_text(encoding='utf-8')
    hits = {pattern: [line for line in body.splitlines()
                      if re.search(pattern, line)]
            for pattern in CONSUMER_NAMES}
    assert not any(hits.values()), {k: v for k, v in hits.items() if v}


# --- lint, from a consumer's seat --------------------------------------------
@pytest.mark.skipif(shutil.which('shellcheck') is None,
                    reason='needs shellcheck')
def test_a_consumer_sourcing_the_library_shellchecks_clean(tmp_path):
    """A consumer's `shellcheck -x` follows the `source` and lints the library
    INLINE, so anything the library does to a name it also publishes lands as a
    finding in the consumer's file. The library's own self-test used to assign
    HOME and GDK_LOG_CAP_BYTES inside subshells, and every consumer script that
    later READ one of them got SC2031 on a line its author wrote correctly —
    three sites in one adoption, each repaired with a local disable comment.
    The self-test scopes those values to a child process instead. This is the
    fixture that keeps it that way."""
    dev = tmp_path / 'tools' / 'dev'
    (dev / 'runners').mkdir(parents=True)
    shutil.copy2(LIBRARY, dev / LIBRARY.name)
    consumer = dev / 'runners' / 'consumer.sh'
    consumer.write_text(
        '#!/usr/bin/env bash\n'
        'set -uo pipefail\n'
        f'# shellcheck source=../{LIBRARY.name}\n'
        f'source "$(dirname "${{BASH_SOURCE[0]}}")/../{LIBRARY.name}"\n'
        'log="$(gdk_gate_log parse)"\n'
        'gdk_gate_capture "$log" -- true\n'
        'echo "cap $GDK_LOG_CAP_BYTES timeout $GDK_TIMEOUT exit $GDK_GATE_EXIT"\n'
        'gdk_gate_verdict PARSE "PASS" "$log"\n',
        encoding='utf-8')

    # cwd is the script's directory so `source=../gdk_gate.sh` resolves.
    done = subprocess.run(['shellcheck', '-x', consumer.name],
                          cwd=consumer.parent, text=True, capture_output=True)
    assert done.returncode == 0, done.stdout + done.stderr


@pytest.mark.skipif(shutil.which('shellcheck') is None,
                    reason='needs shellcheck')
@pytest.mark.parametrize('script', SCRIPTS, ids=lambda p: p.stem)
def test_every_shipped_runner_shellchecks_clean(script):
    """`shellcheck -x` on the installable itself. It lands in consumer trees
    whose own `check shell` gate runs over tools/ — a finding shipped from here
    reddens somebody else's commit gate."""
    done = subprocess.run(['shellcheck', '-x', script.name],
                          cwd=script.parent, text=True, capture_output=True)
    assert done.returncode == 0, done.stdout + done.stderr
