"""test_check_reuse.py — a static gate reused by the hash of what it reads (#98).

`verify/gates.py` keys each gate `check all` runs on the inputs its module
declares, records a PASS in the tree's local ledger, and prints that PASS again
while the inputs are byte-identical. The rule-4 half is what these cases hold:
an edit to any input re-runs the gate, a FAIL is never reused, a gate over 0
files is never keyed. The listing git would give is handed in, so nothing here
spawns; the Makefile half (no cost row for a reused run, a declared `[gates]
extra` target reused) spawns make and lives in tests/test_makefile_include.py.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import types
from pathlib import Path

import pytest

from support.pm import with_flow

from agentic_sdlc.core.project import load_config, repo_root
from agentic_sdlc.repo.verify import gates

LOCAL = 'pm/roadmap/ledger.local.jsonl'
PASS_LINE = '[check:fake] PASS — 2 file(s) read'

FILES = {
    'src/a.txt': 'a\n',
    'src/b.txt': 'b\n',
    'docs/other.md': 'elsewhere\n',
    'devkit.toml': with_flow(),
    'pm/roadmap/.keep': '',
}


@contextlib.contextmanager
def tree():
    """A throwaway tree with a PM config, cwd'd into; `.git` is a marker."""
    with tempfile.TemporaryDirectory() as tmp:
        root = (Path(tmp) / 'repo').resolve()
        for rel, body in FILES.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding='utf-8')
        (root / '.git').mkdir()
        previous = Path.cwd()
        os.chdir(root)
        repo_root.cache_clear()
        load_config.cache_clear()
        try:
            yield root
        finally:
            os.chdir(previous)
            repo_root.cache_clear()
            load_config.cache_clear()


def listed(root: Path) -> bytes:
    """What `git ls-files -z --cached --others` would name: every file but
    the marker and the local ledger, which a real tree ignores."""
    names = sorted(p.relative_to(root).as_posix() for p in root.rglob('*')
                   if p.is_file() and '.git' not in p.parts
                   and p.name != 'ledger.local.jsonl')
    return b''.join(name.encode() + b'\0' for name in names)


def fake(scope=('src',), also=(), facts=(), said=PASS_LINE, code=0):
    """A gate module: its declaration, and a run that counts itself."""
    calls = []

    def run() -> int:
        calls.append(1)
        print(said)
        return code

    module = types.SimpleNamespace(inputs=lambda: gates.Inputs(
        scope=scope, also=also, facts=facts))
    return module, run, calls


def check(root: Path, module, run, marker: Path | None = None) -> tuple[int, str]:
    """One gate through one session, as `check all` runs it."""
    out = io.StringIO()
    env = {gates.UNMEASURED_ENV: str(marker)} if marker else {}
    with contextlib.redirect_stdout(out), _env(env):
        session = gates.Session(root, listed)
        code = session.gate('fake', module, run)
        session.close(1)
    return code, out.getvalue()


@contextlib.contextmanager
def _env(values: dict):
    saved = {key: os.environ.get(key) for key in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def rows(root: Path) -> list[dict]:
    path = root / LOCAL
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line]


# A gate's whole output: the reuse prints every line of it again, and the WARN
# lines most of all — a reuse that dropped them silenced `check pm` (rule 11).
SAID = ('[check:fake] WARN — a courier is wired and wrote nothing\n'
        '  READY  ms-one is building\n'
        f'{PASS_LINE}\n'
        '  CENSUS  2 file(s)')


def test_a_second_run_on_unchanged_inputs_prints_the_same_output_and_runs_nothing():
    with tree() as root:
        module, run, calls = fake(said=SAID)
        marker = root / 'unmeasured'
        code, fresh = check(root, module, run, marker)
        assert code == 0
        assert not marker.exists(), 'a run that did all its work is measured'
        code, out = check(root, module, run, marker)
        assert marker.exists(), 'a reused run must tell the gate library'
        recorded = [r for r in rows(root) if r['kind'] == 'verify']
    assert code == 0 and len(calls) == 1, out
    lines = out.splitlines()
    assert lines[2].startswith(PASS_LINE + '; reused — green at '), out
    assert ' on inputs ' in lines[2], out
    # Every line but the PASS line is the fresh run's, byte for byte.
    assert [line for line in lines if '[check:cache]' not in line
            and not line.startswith(PASS_LINE)] == \
        [line for line in fresh.splitlines() if line != PASS_LINE], out
    assert '[check:cache] reused 1 of 1 gate(s)' in out, out
    assert [(r['rung'], r['gate'], r['said']) for r in recorded] == [
        ('check', 'check:fake', SAID + '\n')]


@pytest.mark.parametrize('edit, runs', [
    # An input's content moves: the gate runs.
    (lambda root, **_: (root / 'src/a.txt').write_text('A\n'), True),
    # A new file under the scope: the gate runs.
    (lambda root, **_: (root / 'src/c.txt').write_text('c\n'), True),
    # An edit outside every input: reused.
    (lambda root, **_: (root / 'docs/other.md').write_text('moved\n'), False),
    # A fact no file carries (a config value, a binary): the gate runs.
    (lambda root, facts, **_: facts.append('shellcheck 0.12.0'), True),
    # This tool itself: a new version or a rule edited in place.
    (lambda root, tool, **_: tool.append('0.0.0+other'), True),
])
def test_an_edit_to_any_input_re_runs_the_gate_and_no_other_edit_does(
        edit, runs, monkeypatch):
    facts, tool = ['shellcheck 0.11.0'], [gates.tool()]
    monkeypatch.setattr(gates, 'tool', lambda: tool[-1])
    with tree() as root:
        module, run, calls = fake()
        module.inputs = lambda: gates.Inputs(scope=('src',),
                                             facts=(facts[-1],))
        check(root, module, run)
        edit(root, facts=facts, tool=tool)
        _, out = check(root, module, run)
    assert len(calls) == (2 if runs else 1), out
    assert ('; reused — ' in out) is not runs, out


def test_a_file_read_outside_the_listing_is_an_input_too():
    """A gitignored settings file is not in git's listing and is still read."""
    with tree() as root:
        (root / 'local.json').write_text('{}\n')
        module, run, calls = fake(also=('local.json',))
        check(root, module, run)
        (root / 'local.json').write_text('{"hooks": {}}\n')
        _, out = check(root, module, run)
    assert len(calls) == 2, out


@pytest.mark.parametrize('said, code', [
    ('[check:fake] FAIL — 1 finding(s)', 1),
    # Exit 0 and no PASS line (a gate that SKIPs) is no PASS to replay.
    ('[check:fake] SKIP — shellcheck not on PATH', 0),
])
def test_only_a_pass_is_recorded_so_nothing_else_is_ever_reused(said, code):
    with tree() as root:
        module, run, calls = fake(said=said, code=code)
        check(root, module, run)
        again, out = check(root, module, run)
        recorded = [r for r in rows(root) if r['kind'] == 'verify']
    assert again == code and len(calls) == 2, out
    assert 'reused' not in out, out
    assert recorded == []


def test_a_gate_over_zero_files_runs_and_is_never_keyed():
    """Rule 4: a state over 0 files would match every other empty scan."""
    with tree() as root:
        module, run, calls = fake(scope=('nowhere',))
        check(root, module, run)
        check(root, module, run)
        assert rows(root) == []
    assert len(calls) == 2


def test_a_gate_that_declares_nothing_always_runs():
    with tree() as root:
        _, run, calls = fake()
        check(root, types.SimpleNamespace(), run)
        check(root, types.SimpleNamespace(), run)
    assert len(calls) == 2


def test_a_declared_extra_target_is_reused_with_the_line_it_printed():
    with tree() as root:
        ran = []

        def target() -> tuple[int, str]:
            ran.append(1)
            print('[LINT] PASS (3 files)')
            return 0, '[LINT] PASS (3 files)'

        for _ in range(2):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = gates.Session(root, listed).extra(
                    'lint', ('src',), target)
            assert code == 0
        (root / 'src/a.txt').write_text('A\n')
        with contextlib.redirect_stdout(io.StringIO()):
            gates.Session(root, listed).extra('lint', ('src',), target)
    assert len(ran) == 2, 'the edit re-runs it; the unchanged run reuses it'
    assert out.getvalue().startswith('[LINT] PASS (3 files); reused — green at ')


def test_a_hook_replay_is_keyed_on_that_hook_alone():
    """`check hooks` re-running for one hook's change replays that hook only."""
    with tree() as root:
        hooks = root / 'tools/hooks'
        hooks.mkdir(parents=True)
        for name in ('one.sh', 'two.sh'):
            (hooks / name).write_text(f'echo {name}\n')
        replayed = []

        def replay_all() -> None:
            session = gates.Session(root, listed)
            for name in ('one.sh', 'two.sh'):
                session.replay(hooks / name,
                               lambda n=name: replayed.append(n) or '')

        replay_all()
        (hooks / 'two.sh').write_text('echo changed\n')
        replay_all()
    assert replayed == ['one.sh', 'two.sh', 'two.sh']


def test_the_tool_key_carries_the_package_version():
    import agentic_sdlc
    assert gates.tool().startswith(agentic_sdlc.__version__ + '+')


def test_no_cache_runs_every_gate_and_reads_and_records_nothing():
    """`check all --no-cache` — what `adopt` runs, since it writes nothing."""
    with tree() as root:
        module, run, calls = fake()
        check(root, module, run)
        before = rows(root)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = gates.run_all(root, ('fake',), lambda _: module,
                                 lambda _: run(), reuse=False)
        assert rows(root) == before
    assert code == 0 and len(calls) == 2, out.getvalue()
    assert 'reused — ' not in out.getvalue()
    assert out.getvalue().rstrip().endswith(gates.NO_CACHE), out.getvalue()
