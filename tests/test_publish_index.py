"""test_publish_index.py — `tools/publish_index.py`, the static index writer (#101).

The kit ships as a wheel on a PEP 503 index `release.yml` rebuilds at each tag.
What a consumer's lock depends on is what this script writes: each file once,
linked with the sha256 uv checks, and never replaced. So the contract is the
three things a publish can get wrong — the pages, a version republished with
other bytes, and a rerun that is not a no-op. Function calls on scratch trees;
`test_makefile_include.py` resolves a real `uv build` through the pages.
"""
from __future__ import annotations

import hashlib
import re
import importlib.util
import zipfile
from pathlib import Path

import pytest

from support import REPO_ROOT

_SPEC = importlib.util.spec_from_file_location(
    'publish_index', REPO_ROOT / 'tools' / 'publish_index.py')
publish_index = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(publish_index)

PROJECT = 'agentic-sdlc'


def build(dist: Path, version: str, salt: str = '') -> list[Path]:
    """A wheel carrying METADATA and an sdist, as `uv build` names them."""
    dist.mkdir(parents=True, exist_ok=True)
    wheel = dist / f'agentic_sdlc-{version}-py3-none-any.whl'
    with zipfile.ZipFile(wheel, 'w') as archive:
        archive.writestr(f'agentic_sdlc-{version}.dist-info/METADATA',
                         f'Name: agentic-sdlc\nVersion: {version}\n'
                         f'Requires-Python: >=3.11\n{salt}')
    sdist = dist / f'agentic_sdlc-{version}.tar.gz'
    sdist.write_bytes(f'sdist {version}{salt}'.encode())
    return [wheel, sdist]


def snapshot(site: Path) -> dict[str, bytes]:
    return {p.relative_to(site).as_posix(): p.read_bytes()
            for p in site.rglob('*') if p.is_file()}


def test_a_build_lands_with_its_hashes_and_a_rerun_writes_nothing(tmp_path):
    """Write, then idempotence: the pages link every file with the sha256 of
    the bytes on disk, and the same set again changes no byte."""
    site = tmp_path / 'site'
    files = build(tmp_path / 'dist', '1.0.0')
    written = publish_index.publish(tmp_path / 'dist', site)
    home = site / 'simple' / PROJECT
    assert sorted(written) == sorted(
        [f'simple/{PROJECT}/{p.name}' for p in files]
        + [f'simple/{PROJECT}/index.html', 'simple/index.html'])
    page = (home / 'index.html').read_text(encoding='utf-8')
    for path in files:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert (home / path.name).read_bytes() == path.read_bytes()
        assert f'href="{path.name}#sha256={digest}"' in page, page
    assert 'data-requires-python="&gt;=3.11"' in page, page
    root = (site / 'simple' / 'index.html').read_text(encoding='utf-8')
    assert f'href="{PROJECT}/"' in root, root
    before = snapshot(site)
    assert publish_index.publish(tmp_path / 'dist', site) == []
    assert snapshot(site) == before


@pytest.mark.parametrize('rebuild', ['other bytes', 'an extra file'])
def test_a_published_version_is_refused_naming_the_file(tmp_path, rebuild):
    """Refusal: a wheel is immutable. The same version with other bytes, or a
    file the published set did not have, is refused by name before any byte
    is written — and a NEW version still lands beside the old one."""
    site = tmp_path / 'site'
    build(tmp_path / 'dist', '1.0.0')
    publish_index.publish(tmp_path / 'dist', site)
    before = snapshot(site)
    again = tmp_path / 'again'
    if rebuild == 'other bytes':
        build(again, '1.0.0', salt='changed')
        named = 'agentic_sdlc-1.0.0-py3-none-any.whl'
    else:
        build(again, '1.0.0')
        (again / 'agentic_sdlc-1.0.0-py3-none-macosx_11_0_arm64.whl').write_bytes(
            (again / 'agentic_sdlc-1.0.0-py3-none-any.whl').read_bytes())
        named = 'agentic_sdlc-1.0.0-py3-none-macosx_11_0_arm64.whl'
    with pytest.raises(publish_index.Refused, match=named):
        publish_index.publish(again, site)
    assert snapshot(site) == before
    assert publish_index.main(['--dist', str(again), '--site', str(site)]) == 1
    build(tmp_path / 'next', '1.0.1')
    publish_index.publish(tmp_path / 'next', site)
    page = (site / 'simple' / PROJECT / 'index.html').read_text(encoding='utf-8')
    assert 'agentic_sdlc-1.0.0.tar.gz' in page and 'agentic_sdlc-1.0.1.tar.gz' in page


def test_a_missing_or_empty_dist_is_not_a_publish(tmp_path, capsys):
    """No build is exit 2 (usage) or 1 (nothing to publish), never exit 0
    over a census of nothing."""
    assert publish_index.main(['--dist', str(tmp_path / 'none'),
                               '--site', str(tmp_path / 'site')]) == 2
    (tmp_path / 'empty').mkdir()
    assert publish_index.main(['--dist', str(tmp_path / 'empty'),
                               '--site', str(tmp_path / 'site')]) == 1
    assert 'no wheel and no sdist' in capsys.readouterr().err


def test_release_keeps_the_token_off_disk_and_asks_ls_remote_with_it():
    """1.0.0-milestone/X3: the clone URL wrote the token into
    site/.git/config, and an unauthenticated `ls-remote` on a private repo
    failed and fell through to an orphan init. Every git call that reaches
    the remote carries the token as a `-c` auth header; only `ls-remote`'s
    exit 2 ("no such branch") starts an orphan, and any other exit stops."""
    text = (REPO_ROOT / '.github' / 'workflows' / 'release.yml').read_text(
        encoding='utf-8')
    assert '@github.com' not in text, 'a credential is back in a URL'
    joined = re.sub(r'\\\n\s*', ' ', text)
    remote = [line.strip() for line in joined.splitlines()
              if re.search(r'\bgit\b.*\b(ls-remote|clone|push)\b', line)
              and not line.lstrip().startswith(('#', 'echo', '*)'))]
    assert len(remote) == 3, remote
    for line in remote:
        assert re.match(r'^(\d\) )?git -c "(\$auth|http\.https://github\.com/'
                        r'\.extraheader=AUTHORIZATION: basic \$basic)"', line), line
    arms = re.findall(r'^ +([0-9*])\) (.*)$', text, re.M)
    assert [arm for arm, _ in arms] == ['0', '2', '*'], arms
    assert 'git init' not in arms[0][1] + arms[2][1], arms
