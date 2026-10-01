"""test_check_shell.py — `[shell] shellcheck_version`: a local pass means a CI pass.

Issue #89: `check shell` passed on local shellcheck 0.11.0 and failed on the
runner's apt shellcheck for nine days. The pin makes the version part of the
gate: another version FAILS naming both, and a missing shellcheck FAILS rather
than skips, because a pinned gate that skips is a PASS that never looked.

Unit tier. The gate's processes go through `core/spawn.run`, the one place this
package starts one, so each case replaces that seam with a table of replies
and asserts what a caller sees: the verdict line and the exit code. The fake
`shellcheck` on PATH is an empty executable file, found by `shutil.which` and
never run.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import REPO_ROOT, run_check  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / 'src'))
from agentic_sdlc import cli as top_cli  # noqa: E402
from agentic_sdlc.core import spawn  # noqa: E402
from agentic_sdlc.core.project import load_config, repo_root  # noqa: E402
from agentic_sdlc.repo.checks import shell  # noqa: E402

LOCAL = '0.11.0'


def _tree(tmp_path, monkeypatch, pin: str | None, on_path: bool) -> list[list[str]]:
    """A checkout with one tracked script; returns the argv of every spawn the gate makes."""
    root = tmp_path / 'repo'
    (root / '.git').mkdir(parents=True)
    (root / 'tools').mkdir()
    (root / 'tools' / 'a.sh').write_text('#!/bin/sh\necho hi\n')
    if pin is not None:
        (root / 'devkit.toml').write_text(f'[shell]\nshellcheck_version = "{pin}"\n')
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    if on_path:
        fake = bin_dir / 'shellcheck'
        fake.write_text('')
        fake.chmod(0o755)
    monkeypatch.setenv('PATH', str(bin_dir))
    monkeypatch.chdir(root)
    calls: list[list[str]] = []

    def reply(argv, **_kwargs):
        calls.append(list(argv))
        if argv[:2] == ['shellcheck', '--version']:
            out = f'ShellCheck - shell script analysis tool\nversion: {LOCAL}\n'
        elif argv[:2] == ['git', 'ls-files']:
            out = 'tools/a.sh\n'
        elif argv[:2] == ['shellcheck', '-x']:
            out = ''
        else:
            raise AssertionError(f'unexpected spawn {argv}')
        return spawn.CompletedProcess(argv, 0, stdout=out, stderr='')

    monkeypatch.setattr(spawn, 'run', reply)
    return calls


def test_a_pin_the_local_shellcheck_does_not_match_fails_naming_both(
        tmp_path, monkeypatch, capsys):
    calls = _tree(tmp_path, monkeypatch, pin='0.10.0', on_path=True)
    code, out = run_check(shell)
    assert code == 1, out
    assert '[check:shell] FAIL' in out, out
    assert LOCAL in out and '0.10.0' in out, out
    assert calls == [['shellcheck', '--version']], (
        f'the gate linted under the wrong version: {calls}')
    # The stock verify.yml reads the same key through the tool, never a parser of its own.
    repo_root.cache_clear()
    load_config.cache_clear()
    capsys.readouterr()
    assert top_cli.main(['check', 'shell', '--pin']) == 0
    assert capsys.readouterr().out == '0.10.0\n'


@pytest.mark.parametrize('pin, code, verdict', [
    (LOCAL, 1, '[check:shell] FAIL — shellcheck not on PATH'),
    (None, 0, '[check:shell] SKIP — shellcheck not on PATH'),
])
def test_a_missing_shellcheck_fails_only_when_pinned(
        tmp_path, monkeypatch, pin, code, verdict):
    _tree(tmp_path, monkeypatch, pin=pin, on_path=False)
    got, out = run_check(shell)
    assert got == code, out
    assert out.startswith(verdict), out
    if pin:
        assert pin in out, out


def test_every_verdict_names_the_shellcheck_it_ran(tmp_path, monkeypatch):
    _tree(tmp_path, monkeypatch, pin=None, on_path=True)
    code, out = run_check(shell)
    assert code == 0, out
    assert out == f'[check:shell] PASS — 1 script(s) clean (shellcheck {LOCAL})\n'


@pytest.mark.parametrize('argv', [['check', 'shell'], ['check', 'shell', '--pin']])
def test_a_pin_with_a_leading_v_is_refused_at_exit_2_before_a_spawn(
        tmp_path, monkeypatch, capsys, argv):
    # Stripped, `v0.11.0` would hide a typo; kept, it never matches and CI
    # builds a `vv0.11.0` URL. Refused by name, the operator decides.
    calls = _tree(tmp_path, monkeypatch, pin='v0.11.0', on_path=True)
    repo_root.cache_clear()
    load_config.cache_clear()
    assert top_cli.main(argv) == 2
    captured = capsys.readouterr()
    assert captured.out == '', captured.out
    assert 'shellcheck_version' in captured.err and 'v0.11.0' in captured.err, captured.err
    assert calls == [], f'a refused pin still spawned: {calls}'
