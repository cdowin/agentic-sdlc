"""test_gate_library.py — the shell gate library, RUN rather than read.

`gdk_gate.sh` is the library every gate in a consumer routes through — this
package's own `Makefile` included. It is not Python, so the contract is proven
the way the hook corpus is: the script carries a `--self-test`, and this file
drives it through a subprocess and holds it to its published shape.

The verb that writes it is `install-gates`, and the other file it writes is
`Makefile.devkit` — `tests/test_makefile_include.py`.

Three things this file adds on top of firing the corpus:

  - it MUTATES the verdict format and re-runs, so "the self-test passes" is
    evidence rather than a claim. A corpus that cannot fail is a green light
    wired to nothing.
  - it exercises the verdict line and its log path END TO END — sourcing the
    library into a scratch cwd and running a fake gate through
    gate_log -> gate_capture -> gate_verdict. That line shape is grepped by
    consumer Makefiles, so it is contract (CLAUDE.md rule 6), not cosmetics.
  - it holds the library to being LANGUAGE-NEUTRAL: what stayed after the
    0.2.0 split is the framework that reads an exit code, a stream and the
    clock (decision D2 — an installable belongs to the kit whose ARTIFACT it
    acts on). A toolchain name creeping back in is that split un-doing itself
    one helper at a time.
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
from support import consumers

pytestmark = pytest.mark.skipif(shutil.which('bash') is None,
                                reason='needs bash')

INSTALLABLES = REPO_ROOT / 'src' / 'agentic_sdlc' / 'repo' / 'installables'
LIBRARY = INSTALLABLES / 'gdk_gate.sh'
SCRIPTS = (LIBRARY,)

# The one line shape a consumer greps. Changing it is a minor bump at least.
VERDICT = '[PARSE] PASS (2 files) — full log: .gate-reports/parse.log'


def run(*argv: str, cwd: Path | None = None, skip_timing: bool = False
        ) -> subprocess.CompletedProcess:
    """Run a script. `skip_timing` sets `GDK_ST_SKIP_TIMING=1`.

    Three cases in the corpus prove a bound by WAITING for it — a recorder that
    hangs, one that forks, one parsed in front of the bound — and only the
    clock can tell a fixed library from a broken one on those. They are ~3 s of
    the corpus's 4.

    NINE mutation tests drive that corpus, each reverting one line and
    asserting one specific case reddens, and SEVEN of them have nothing to do
    with timing. Paying 3 s of sleep to prove a verdict-shape mutant reddens is
    21 s a run spent proving nothing (hard rule 10). The two that ARE about the
    bound run the whole thing, and so does every consumer, because the skip is
    a caller's optimisation and never the default.
    """
    # The installed CI exports VERBOSE=1 for the whole `make milestone` step,
    # and the quiet-by-default cases below are asked of the DEFAULT — VERBOSE
    # unset. A case that wants the stream sets it in its own env.
    env = {k: v for k, v in os.environ.items() if k != 'VERBOSE'}
    if skip_timing:
        env['GDK_ST_SKIP_TIMING'] = '1'
    return subprocess.run(['bash', *argv], cwd=cwd, text=True,
                          capture_output=True, env=env)


# --- the corpus, fired -------------------------------------------------------
@pytest.mark.parametrize('script', SCRIPTS, ids=lambda p: p.stem)
def test_the_self_test_corpus_passes_and_reports_its_case_count(script):
    """The whole corpus, the wall-clock cases included, under an AMBIENT
    `VERBOSE=1` — and its verdict is still one line.

    A corpus proves both settings on its own pinned cases; the value the
    caller exports is not one of them. The library's cap case inherited it and
    streamed its eight bytes INTO the verdict line — `01234567[gdk-gate]
    SELF-TEST OK …` — which is what a `VERBOSE=1` self-test, and so the
    installed CI, then read as the verdict. One run asks both: a second
    replay of the corpus to ask the line alone cost 3 s and proved the pass
    again. The corpus under VERBOSE UNSET is what each mutant below runs."""
    done = subprocess.run(['bash', str(script), '--self-test'], text=True,
                          capture_output=True,
                          env=dict(os.environ, VERBOSE='1'))
    assert done.returncode == 0, done.stdout + done.stderr
    lines = done.stdout.splitlines()
    assert len(lines) == 1, done.stdout
    shape = re.match(r'^\[[A-Za-z][A-Za-z-]*\] SELF-TEST OK — (\d+) case\(s\)$',
                     lines[0])
    assert shape, lines[0]
    assert int(shape.group(1)) > 0, f'a corpus of {shape.group(1)} cases proves nothing'


def test_the_library_corpus_FAILS_when_the_verdict_shape_is_broken(tmp_path):
    """Rule 4, applied to the corpus itself: a self-test that cannot go red is
    a false PASS with extra steps. Swap the em dash for a hyphen — the one
    byte a consumer's grep would feel — and the corpus must catch it."""
    mutant = tmp_path / LIBRARY.name
    mutant.write_text(
        LIBRARY.read_text(encoding='utf-8')
        .replace("'[%s] %s — full log: %s\\n'", "'[%s] %s - full log: %s\\n'"),
        encoding='utf-8')
    # Not a timing mutant: the wall-clock cases prove nothing here.
    done = run(str(mutant), '--self-test', skip_timing=True)
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
    # Not a timing mutant: the wall-clock cases prove nothing here.
    done = run(str(mutant), '--self-test', skip_timing=True)
    assert done.returncode == 1, done.stdout + done.stderr
    assert 'capture reports the command exit code' in done.stderr, done.stderr


def test_the_library_corpus_FAILS_when_the_recorder_is_read_through_a_pipe(tmp_path):
    """The recorder bound, held to being able to go red ON TIME.

    Twelve hostile `GDK_LEDGER_CMD` values in the 0.2.0 review moved neither
    the verdict line nor the exit code — fail-open on OUTCOME was proven. Two
    of them cost 120 s against a 3 s bound anyway, because the output was read
    through `$( )` and a recorder that backgrounds anything leaves the
    substitution's pipe open behind it. `timeout` never saw a deadline to fire:
    its direct child exited 0 immediately.

    So this mutant restores exactly that one line. An output-only corpus cannot
    tell the two libraries apart — the mutant prints every verdict this one
    does — and the case it must redden is the wall-clock one.
    """
    mutant = tmp_path / LIBRARY.name
    source = LIBRARY.read_text(encoding='utf-8')
    piped = '\t\tsaid="$(_gdk_ledger_run "${cmd[@]}" 2>&1)" || rc=$?'
    redirected = '\t\t_gdk_ledger_run "${cmd[@]}" > "$scratch" 2>&1 || rc=$?'
    assert source.count(redirected) == 1, 'the redirect this mutant reverts moved'
    mutant.write_text(source.replace(redirected, piped), encoding='utf-8')
    done = run(str(mutant), '--self-test')
    assert done.returncode == 1, done.stdout + done.stderr
    assert 'does not hold the gate open' in done.stderr, done.stderr


def test_the_library_corpus_FAILS_when_the_value_is_parsed_in_front_of_the_bound(
        tmp_path):
    """G1, held to being able to go red — the SECOND way the recorder escaped
    its bound, and not the one above.

    `eval "prefix=($GDK_LEDGER_CMD)"` executes every `$( )` in the value as the
    array is built. That build used to happen in the gate's own shell, before
    `timeout` was ever invoked, so `GDK_LEDGER_CMD='true $(sleep 20)'` cost
    20062 ms against a 3 s bound — and unlike the pipe case it left no note
    behind, because the eval SUCCEEDED and the row that followed looked normal.

    The mutant puts the parse back where it was, in front of the bound, and
    hands the recorder on the same way. Every verdict line and every exit code
    is identical under it; only the clock can tell them apart.
    """
    mutant = tmp_path / LIBRARY.name
    source = LIBRARY.read_text(encoding='utf-8')
    bounded = ('\tcmd=("${BASH:-bash}" -c "$_GDK_LEDGER_SHIM" _ \\\n'
               '\t\t"$GDK_LEDGER_CMD" "$_GDK_LEDGER_PARSE_REFUSAL" "${argv[@]}")\n')
    in_front = ('\tlocal -a prefix\n'
                '\tprefix=()\n'
                '\teval "prefix=($GDK_LEDGER_CMD)" 2>/dev/null || return 0\n'
                '\t[ "${#prefix[@]}" -gt 0 ] || return 0\n'
                '\tcmd=("${prefix[@]}" "${argv[@]}")\n')
    assert source.count(bounded) == 1, 'the shim this mutant reverts moved'
    mutant.write_text(source.replace(bounded, in_front), encoding='utf-8')
    done = run(str(mutant), '--self-test')
    assert done.returncode == 1, done.stdout + done.stderr
    assert 'is parsed UNDER the bound' in done.stderr, done.stderr


def test_the_library_corpus_FAILS_when_the_quoting_in_the_value_is_dropped(tmp_path):
    """The other half of G1, and the reason it is not fixed by refusing to
    parse: `GDK_LEDGER_CMD` is `$(DEVKIT)`, which a project may set to a
    command carrying a QUOTED word (the `uvx` spec it was through 0.x), so a
    bare word split hands the recorder a word with literal quote characters
    in it. The mutant makes the shim split instead of parse."""
    mutant = tmp_path / LIBRARY.name
    source = LIBRARY.read_text(encoding='utf-8')
    parsed = ('eval "prefix=($1)" 2>/dev/null'
              ' || { printf "%s\\n" "$2" >&2; exit 121; }')
    assert source.count(parsed) == 1, 'the shim eval this mutant reverts moved'
    mutant.write_text(source.replace(parsed, 'prefix=($1)'), encoding='utf-8')
    # Not a timing mutant: the wall-clock cases prove nothing here.
    done = run(str(mutant), '--self-test', skip_timing=True)
    assert done.returncode == 1, done.stdout + done.stderr
    assert 'ONE argv element' in done.stderr, done.stderr


def test_the_library_corpus_FAILS_when_a_slot_files_its_last_captures_code(tmp_path):
    """G2, held to being able to go red: the verdict COLUMN, in the feature
    whose whole job is honest measurement.

    A runner that captures more than once against one `gdk_gate_log` slot (this
    repo's `matrix` target loops one capture per interpreter) used to file the
    LAST command's code — console `[MATRIX] FAIL on first`, row
    `"verdict":"PASS"`. Rule 4's read-side sin, made durable.

    The mutant drops the slot's own code and reads the last one again. Nothing
    a gate PRINTS moves under it, which is why an output-only corpus could not
    see this defect and the case asserts on the recorder's argv.
    """
    mutant = tmp_path / LIBRARY.name
    source = LIBRARY.read_text(encoding='utf-8')
    of_the_slot = 'verdict="$(_gdk_ledger_verdict "$fault")"'
    assert source.count(of_the_slot) == 1, 'the slot verdict this mutant reverts moved'
    mutant.write_text(source.replace(of_the_slot, 'verdict="$(_gdk_ledger_verdict)"'),
                      encoding='utf-8')
    # Not a timing mutant: the wall-clock cases prove nothing here.
    done = run(str(mutant), '--self-test', skip_timing=True)
    assert done.returncode == 1, done.stdout + done.stderr
    assert 'files FAIL, not PASS' in done.stderr, done.stderr


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
def test_an_argument_the_script_does_not_take_is_refused_as_a_usage_error(script):
    for argv in (('--nope',),                 # an unknown verb
                 ('-x',),                     # an unknown short flag
                 ('--self-test', 'extra'),    # a known verb with an extra argument
                 ('--help', '--self-test'),   # two verbs
                 ('',)):                      # an empty argument is not "no argument"
        done = run(str(script), *argv)
        assert done.returncode == 2, (
            f'{script.name} {argv} -> {done.returncode}\n{done.stdout}{done.stderr}')
        # Exit 2 for the RIGHT reason: a refusal names the remedy. Without this
        # the empty-argument case passed off a downstream "library not found"
        # as the argument check working.
        assert '--help' in done.stdout + done.stderr, (argv, done.stdout + done.stderr)


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
# reaching the other. Word-bounded, so a longer word that merely BEGINS with
# a configured name stays prose and only the name itself is a finding.
# The whole-tree form of this claim is tests/test_consumer_independence.py.
CONSUMER_NAMES = tuple(rf'\b{n}\b' for n in consumers.consumer_names())
CONSUMER_NAMES += tuple(p.upper() for p in CONSUMER_NAMES)


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
def test_the_shipped_library_shellchecks_clean(script):
    """`shellcheck -x` on the installable itself. It lands in consumer trees
    whose own `check shell` gate runs over tools/ — a finding shipped from here
    reddens somebody else's commit gate."""
    done = subprocess.run(['shellcheck', '-x', script.name],
                          cwd=script.parent, text=True, capture_output=True)
    assert done.returncode == 0, done.stdout + done.stderr


def test_a_verbose_capture_streams_a_line_before_the_command_ends(tmp_path):
    """CI stamps each line of a streamed gate when it ARRIVES. With `head -c`
    ahead of `tee`, stdio held 4 KB, so a green run read `check hooks` as 82
    seconds that were the `test` tier's. The command below prints one line and
    then waits for the reader to have it: a capture that buffers never lets
    the line through, and the read times out."""
    import select

    flag = tmp_path / 'seen'
    script = tmp_path / 'gate.sh'
    script.write_text(
        f'source "{LIBRARY}"\n'
        'log="$(gdk_gate_log stream)"\n'
        'VERBOSE=1 gdk_gate_capture "$log" -- bash -c '
        '\'echo first; for _ in $(seq 200); do [ -f "$1" ] && break; sleep 0.05; done; '
        'echo second\' _ "$1"\n',
        encoding='utf-8')
    env = {k: v for k, v in os.environ.items() if k != 'VERBOSE'}
    proc = subprocess.Popen(['bash', str(script), str(flag)], cwd=tmp_path,
                            stdout=subprocess.PIPE, env=env)
    try:
        ready, _, _ = select.select([proc.stdout], [], [], 5)
        first = proc.stdout.readline() if ready else b''
    finally:
        flag.touch()
        rest = proc.communicate(timeout=15)[0]
    assert first == b'first\n', 'the line arrived only when the command ended'
    assert rest == b'second\n'
    assert (tmp_path / '.gate-reports' / 'stream.log').read_bytes() == b'first\nsecond\n'
