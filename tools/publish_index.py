#!/usr/bin/env python3
"""publish_index.py — add a build's wheel and sdist to a static PEP 503 index.

    python3 tools/publish_index.py --dist dist --site <gh-pages checkout>

Copies each `*.whl` and `*.tar.gz` under --dist into `<site>/simple/<project>/`
and regenerates the two index pages, the root and the project's, each file
linked with its `#sha256=` fragment. `.github/workflows/release.yml` runs it on
every `v*` tag; a `file://` URL at `<site>/simple/` is the same index locally.

A published file is immutable. A version already in the index is REFUSED,
naming the file, unless the build is the same set, byte for byte — so a rerun
of the same tag is a no-op and writes nothing. Stdlib only (CLAUDE.md rule 1).

Exit codes: 0 written or already current, 1 refused, 2 usage error.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import re
import shutil
import sys
import zipfile
from pathlib import Path

SIMPLE = 'simple'
INDEX = 'index.html'
WHEEL = '.whl'
SDIST = '.tar.gz'
# PEP 427 `{name}-{version}(-{build})?-{py}-{abi}-{platform}.whl`; the sdist
# is `{name}-{version}.tar.gz`. The name never holds a `-` (PEP 625).
_WHEEL_NAME = re.compile(r'^(?P<name>[^-]+)-(?P<version>[^-]+)-.+\.whl$')
_SDIST_NAME = re.compile(r'^(?P<name>[^-]+)-(?P<version>[^-]+)\.tar\.gz$')
_REQUIRES = re.compile(r'^Requires-Python:\s*(.+?)\s*$', re.MULTILINE)


class Refused(Exception):
    """The index cannot take this build; the message names why."""


def normalize(name: str) -> str:
    """PEP 503's project name: lower case, each run of `-_.` one `-`."""
    return re.sub(r'[-_.]+', '-', name).lower()


def parse(filename: str) -> tuple[str, str]:
    """(normalized project, version) of a distribution file, or Refused."""
    found = _WHEEL_NAME.match(filename) or _SDIST_NAME.match(filename)
    if not found:
        raise Refused(f'{filename} is not a wheel or an sdist')
    return normalize(found['name']), found['version']


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def requires_python(wheel: Path) -> str:
    """The wheel's `Requires-Python`, or '' when it declares none."""
    with zipfile.ZipFile(wheel) as archive:
        for member in archive.namelist():
            if member.endswith('.dist-info/METADATA'):
                text = archive.read(member).decode('utf-8', 'replace')
                found = _REQUIRES.search(text)
                return found.group(1) if found else ''
    return ''


def plan(dist: Path, site: Path) -> tuple[str, list[Path]]:
    """(project, the files to copy); Refused when the build cannot go in."""
    files = sorted(p for p in dist.iterdir()
                   if p.is_file() and p.name.endswith((WHEEL, SDIST)))
    if not files:
        raise Refused(f'{dist} holds no wheel and no sdist — nothing to publish')
    parsed = {path: parse(path.name) for path in files}
    projects = {project for project, _ in parsed.values()}
    if len(projects) != 1:
        raise Refused(f'{dist} holds more than one project: {sorted(projects)}')
    project = projects.pop()
    home = site / SIMPLE / project
    incoming = {path.name: path for path in files}
    for version in sorted({version for _, version in parsed.values()}):
        present = sorted(p.name for p in home.glob('*')
                         if p.is_file() and p.name != INDEX
                         and parse(p.name)[1] == version) if home.is_dir() else []
        if not present:
            continue
        mine = sorted(name for name, path in incoming.items()
                      if parsed[path][1] == version)
        differ = [name for name in mine
                  if name not in present
                  or sha256(home / name) != sha256(incoming[name])]
        extra = [name for name in present if name not in mine]
        if differ or extra:
            raise Refused(
                f'{project} {version} is already in the index and a published '
                f'file is immutable: {", ".join(differ + extra)} would change '
                f'— publish a new version instead')
    return project, [path for name, path in incoming.items()
                     if not (home / name).is_file()]


def page(title: str, links: list[tuple[str, str, str]]) -> str:
    """A PEP 503 page: one anchor per (href, text, data-requires-python)."""
    rows = ''.join(
        f'    <a href="{html.escape(href)}"'
        + (f' data-requires-python="{html.escape(requires)}"' if requires
           else '')
        + f'>{html.escape(text)}</a><br/>\n'
        for href, text, requires in links)
    return (f'<!DOCTYPE html>\n<html>\n  <head>\n'
            f'    <meta name="pypi:repository-version" content="1.0">\n'
            f'    <title>{html.escape(title)}</title>\n  </head>\n'
            f'  <body>\n{rows}  </body>\n</html>\n')


def _write_if_changed(path: Path, text: str) -> bool:
    if path.is_file() and path.read_text(encoding='utf-8') == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    return True


def render(site: Path) -> list[Path]:
    """Regenerate every index page from the files on disk; the pages written."""
    root = site / SIMPLE
    projects = sorted(p.name for p in root.iterdir() if p.is_dir())
    written = []
    for project in projects:
        home = root / project
        files = sorted(p for p in home.iterdir()
                       if p.is_file() and p.name.endswith((WHEEL, SDIST)))
        requires = {parse(p.name)[1]: requires_python(p)
                    for p in files if p.name.endswith(WHEEL)}
        links = [(f'{p.name}#sha256={sha256(p)}', p.name,
                  requires.get(parse(p.name)[1], '')) for p in files]
        if _write_if_changed(home / INDEX, page(f'Links for {project}', links)):
            written.append(home / INDEX)
    if _write_if_changed(root / INDEX, page(
            'Simple index', [(f'{name}/', name, '') for name in projects])):
        written.append(root / INDEX)
    return written


def publish(dist: Path, site: Path) -> list[str]:
    """Copy the new files in and regenerate the pages; the paths written,
    relative to `site`. Refused, before any byte is written."""
    project, new = plan(dist, site)
    home = site / SIMPLE / project
    home.mkdir(parents=True, exist_ok=True)
    for path in new:
        shutil.copyfile(path, home / path.name)
    return ([(home / p.name).relative_to(site).as_posix() for p in new]
            + [p.relative_to(site).as_posix() for p in render(site)])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog='publish_index.py',
        description='Add a build to a static PEP 503 index; refuse a '
                    'version already published.')
    parser.add_argument('--dist', required=True, type=Path,
                        help='the directory `uv build` wrote')
    parser.add_argument('--site', required=True, type=Path,
                        help='the root the index is served from; the pages '
                             f'go under {SIMPLE}/')
    args = parser.parse_args(argv)
    if not args.dist.is_dir():
        print(f'publish_index: --dist {args.dist} is not a directory',
              file=sys.stderr)
        return 2
    try:
        written = publish(args.dist, args.site)
    except Refused as err:
        print(f'publish_index: REFUSED — {err}', file=sys.stderr)
        return 1
    if not written:
        print('publish_index: already current — nothing written')
    for rel in written:
        print(f'publish_index: wrote {rel}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
