"""ship — a release with no milestone to close, in one verb.

    agentic-sdlc ship <version> "<changelog line>"

`release <version>` is the close of a MILESTONE: features done, a review record
with dispositions, the full gate. A release that is "two merged PRs, cut so a
consumer can pin them" has no feature and no finding, and measured on
2026-09-16 the belt cost seven minutes of invented records for one minute of
work. This verb is that minute:

1. refuse a dirty tree (outside the roadmap), a version the plan would refuse,
   a mainline branch, or a release grain that already exists;
2. mint the milestone grain the plan needs — `ms-release-<version>`, at the
   version, with the changelog line, scheduled last in `order` — so R5 and
   `changelog` read the release the way they read every other;
3. bump every `[release.version_files]` entry (`[pm] version_file` when none
   is declared) to `<version>`, on the one line its pattern names;
4. run the feature rung, `[verify] feature`;
5. write the grain `done`, and print what is yours next: commit, push, PR.
   The tag is the mainline's auto-tag on merge; nothing here pushes or tags.

A refusal in step 1 writes nothing. A red rung in step 4 leaves the bump and
the grain in the tree and SAYS so: the fix is in the code, and the two
remaining acts are named. Exit: 0 shipped | 1 refused or a red rung | 2 usage
or config.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from agentic_sdlc.core import apply
from agentic_sdlc.core.config import (ConfigError, config_section,
                                      section_declared)
from agentic_sdlc.core.project import git_lines, repo_root
from agentic_sdlc.repo import vehicle
from agentic_sdlc.repo.pm import vocabulary

VERB = 'ship'
HELP_WORDS = ('-h', '--help', 'help')
MAINLINES = ('main', 'master')
GRAIN_PREFIX = 'ms-release-'

USAGE = """usage: agentic-sdlc ship <version> "<changelog line>"

  <version>          the release, e.g. 0.13.1
  <changelog line>   what a consumer reads for it, one line

Mints `ms-release-<version>` at that version, bumps the version file(s), runs
the feature rung, writes the grain done, and prints the commit, push and PR
that are yours. Refuses a dirty tree, a mainline branch and an existing grain
before it writes anything. Exit: 0 shipped | 1 refused or a red rung | 2 usage."""

EXIT_OK, EXIT_REFUSED, EXIT_USAGE = 0, 1, 2


def main(argv: list[str]) -> int:
    if argv and argv[0] in HELP_WORDS:
        print(USAGE)
        return EXIT_OK
    if len(argv) < 2:
        return _usage('a version and a changelog line are both required')
    if any(arg.startswith('-') for arg in argv):
        return _usage(f'unknown flag {next(a for a in argv if a.startswith("-"))!r} '
                      f'— this verb takes no flags')
    version, line = argv[0], ' '.join(argv[1:]).strip()
    if not line:
        return _usage('the changelog line is empty — a release nobody can read '
                      'is a tag with no meaning')
    from agentic_sdlc.repo.conveyor import driver
    defect = driver.subject_defect('release', version)
    if defect:
        return _usage(f'{version!r}: {defect}')
    try:
        root = repo_root()
        cfg = vocabulary.load()
        done = driver.done_state(cfg, vocabulary.GRAIN_MILESTONE)
        files = _version_files(cfg)
    except ConfigError as err:
        print(f'agentic-sdlc {VERB}: {err}', file=sys.stderr)
        return EXIT_USAGE

    grain = f'{GRAIN_PREFIX}{_slug(version)}'
    why = _refusal(root, cfg, grain, files)
    if why:
        print(f'[{VERB}] refused — {why}; nothing written', file=sys.stderr)
        return EXIT_REFUSED

    branch = _branch()
    from agentic_sdlc.repo.pm import cli as pm_cli
    for act in (
        ('new', vocabulary.GRAIN_MILESTONE, grain[len('ms-'):],
         f'release {version}', '--version', version),
        ('set', grain, 'branch', branch),
        ('set', grain, 'changelog', line),
        ('add', vocabulary.ROOT_ID, grain),
    ):
        if pm_cli.main(list(act)) != 0:
            print(f'[{VERB}] `pm {" ".join(act[:2])}` refused; the tree holds '
                  f'what landed before it', file=sys.stderr)
            return EXIT_REFUSED
    for rel, pattern in files.items():
        bumped = _bump(root / rel, pattern, version)
        print(f'[{VERB}] {rel}: {bumped}')

    from agentic_sdlc.repo.verify import main as verify_main
    print(f'[{VERB}] feature rung:')
    code = verify_main.main(['--feature'], _verify_section)
    if code != 0:
        print(f'[{VERB}] the feature rung is red (exit {code}); the bump and '
              f'{grain} are in the tree. Fix, then `'
              f'{vehicle.command("verify", "--feature")}` and `'
              f'{vehicle.command("pm", vocabulary.GRAIN_MILESTONE, done, grain)}`',
              file=sys.stderr)
        return EXIT_REFUSED
    if pm_cli.main([vocabulary.GRAIN_MILESTONE, done, grain]) != 0:
        return EXIT_REFUSED
    print(f'[{VERB}] ok — {version} → {done} ({grain})')
    print(f'next: git add {cfg.roadmap_dir} {" ".join(files)} && '
          f'git commit -m "release({version}): {line.split(".")[0].strip("*")}" '
          f'-- {cfg.roadmap_dir} {" ".join(files)}')
    print(f'next: git push -u origin {branch}')
    print(f'next: gh pr create --base main --head {branch} --title '
          f'"Release {version}" — the mainline tags v{version} on merge')
    return EXIT_OK


def _verify_section() -> dict | None:
    """The `[verify]` table, or None when absent (exit 2 in the rung)."""
    return config_section('verify') if section_declared('verify') else None


def _usage(why: str) -> int:
    print(f'agentic-sdlc {VERB}: {why}', file=sys.stderr)
    print(USAGE, file=sys.stderr)
    return EXIT_USAGE


def _slug(version: str) -> str:
    return version.replace('.', '-')


def _branch() -> str:
    lines = git_lines('rev-parse', '--abbrev-ref', 'HEAD')
    return lines[0].strip() if lines else ''


def _version_files(cfg: vocabulary.PmConfig) -> dict[str, str]:
    """`[release.version_files]`, or `[pm] version_file` + pattern alone."""
    section = config_section('release')
    raw = section.get('version_files') if section else None
    if raw is None:
        return {cfg.version_file: cfg.version_pattern}
    if not isinstance(raw, dict) or not raw \
            or not all(isinstance(k, str) and isinstance(v, str)
                       for k, v in raw.items()):
        raise ConfigError('[release.version_files] must be a non-empty table '
                          'of `"<path>" = "<regex with one group>"`')
    return dict(raw)


def _refusal(root: Path, cfg: vocabulary.PmConfig, grain: str,
             files: dict[str, str]) -> str:
    branch = _branch()
    if not branch:
        return 'git could not name the current branch'
    if branch in MAINLINES:
        return (f'HEAD is {branch!r}, and the mainline takes a release by '
                f'merge — cut a branch first')
    dirty = [line[3:] for line in git_lines('status', '--porcelain')
             if line.strip() and not line[3:].startswith(cfg.roadmap_dir)]
    if dirty:
        return (f'{len(dirty)} modified path(s) outside {cfg.roadmap_dir}: '
                f'{", ".join(dirty[:5])}')
    if (root / cfg.roadmap_dir / 'milestones' / f'{grain}.md').is_file():
        return f'{grain} already exists — this version was shipped, or minted'
    for rel, pattern in files.items():
        path = root / rel
        if not path.is_file():
            return f'{rel} is named in [release.version_files] and is not a file'
        try:
            re.compile(pattern)
        except re.error as err:
            return f'{rel}: {pattern!r} is not a valid regex ({err})'
        if not any(re.match(pattern, line)
                   for line in path.read_text(encoding='utf-8').splitlines()):
            return f'{rel}: no line matches {pattern!r}, so no version to bump'
    return ''


def _bump(path: Path, pattern: str, version: str) -> str:
    """Rewrite the ONE line the pattern's group names; every other byte stays."""
    text = path.read_text(encoding='utf-8')
    ending = '\r\n' if '\r\n' in text else '\n'
    out, before = [], ''
    for line in text.split(ending):
        found = re.match(pattern, line)
        if found and not before:
            before = found.group(1)
            line = line[:found.start(1)] + version + line[found.end(1):]
        out.append(line)
    apply.raise_on_error(apply.write(path, ending.join(out)))
    return f'{before} -> {version}'
