#!/usr/bin/env python3
"""check doc — the checkable claims in the always-loaded docs resolve against the tree.

Over `[doc] scope` (default CLAUDE.md, .claude/rules/*.md, .claude/agents/*.md): a dead
path in a backtick span, a `make <target>` no Makefile or include declares, a dead
markdown link, a flat `.claude/skills/<name>.md` that never loads. Fenced blocks are
skipped; an unterminated fence is reported and masks nothing. A line ending in
`<!-- doc-scan:allow -->` is never flagged. `[doc] ephemeral` names directories whose
cited files are expected to be gone.

    agentic-sdlc check doc
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path
from agentic_sdlc.core import makefile
from agentic_sdlc.core.markdown import non_fenced_lines
from agentic_sdlc.core import walk
from agentic_sdlc.core.walk import Kind
from agentic_sdlc.core.project import repo_root
from agentic_sdlc.core.config import config_section, relpath_tuple, str_tuple

REPO_ROOT = repo_root()
# Read per run, never at import, or a config error depends on import order.
DEFAULT_SCOPE = ('CLAUDE.md', '.claude/rules/*.md', '.claude/agents/*.md')
def scope_globs() -> tuple[str, ...]:
    return relpath_tuple(config_section('doc'), 'doc', 'scope', DEFAULT_SCOPE)
ALLOW_MARKER = 'doc-scan:allow'
# A skill is `<name>/SKILL.md`; only a `.md` at depth 1 is the defect.
SKILL_DIR = '.claude/skills'
SKILL_FILENAME = 'SKILL.md'

INLINE_CODE = re.compile(r'`([^`]+)`')
MD_LINK_TEXT = re.compile(r'`[^`]+`\]\(')  # [`text`](href): the claim is the href
MD_LINK = re.compile(r'\[[^\]]*\]\(([^)]+)\)')
MAKE_INVOCATION = re.compile(r'\bmake\s+([a-zA-Z][a-zA-Z0-9_-]*)')
PATH_CANDIDATE = re.compile(r'^[A-Za-z0-9_./-]+\.(gd|tscn|tres|py|sh|md)$')
PLACEHOLDER_CHARS = ('<', '>', '*', '$')
URL_PREFIXES = ('http://', 'https://', 'mailto:')
# Review records are create-resolve-delete by design.
DEFAULT_EPHEMERAL = ('docs/reviews/',)
def ephemeral_dirs() -> tuple[str, ...]:
    return str_tuple(config_section('doc'), 'doc', 'ephemeral',
                     DEFAULT_EPHEMERAL)


def scope_files() -> list[Path]:
    files: list[Path] = []
    for pattern in scope_globs():
        if '*' in pattern:
            files.extend(walk.matching(REPO_ROOT, pattern, Kind.FILE).kept)
        else:
            literal = REPO_ROOT / pattern
            if literal.is_file():
                files.append(literal)
    return files


def real_make_targets() -> set[str]:
    """Every recipe name `make` would resolve, includes followed (shared with `verify --check`)."""
    return set(makefile.targets(REPO_ROOT))
def rel(path: Path) -> str:
    """A finding's path, relative to the checkout where it is under it.

    `REPO_ROOT` is captured at import, so `relative_to` RAISES on a scratch
    tree — which is why this gate had no test module. Degrading here made one
    possible; converting the constant is the vocabulary sweep's job.
    """
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def is_allowed(line: str) -> bool:
    return ALLOW_MARKER in line


# A project-local `<scheme>://` names a resource; the path after it is what is on disk.
_SCHEME = re.compile(r'^[a-z][a-z0-9+.-]*://')


def resolve_path(candidate: str, relative_to: Path) -> bool:
    candidate = _SCHEME.sub('', candidate, count=1)
    if candidate.startswith(ephemeral_dirs()):
        return True
    if (relative_to.parent / candidate).exists():
        return True
    return (REPO_ROOT / candidate).exists()


def check_links(doc: Path, lines: list[tuple[int, str]]) -> list[str]:
    findings: list[str] = []
    for lineno, line in lines:
        if is_allowed(line):
            continue
        for target in MD_LINK.findall(line):
            path_part = target.split('#', 1)[0].strip()
            if not path_part or target.startswith(URL_PREFIXES):
                continue
            if not resolve_path(path_part, doc):
                findings.append(f'{rel(doc)}:{lineno}  dead link target: {target}')
    return findings


def check_make_targets(doc: Path, lines: list[tuple[int, str]], real_targets: set[str]) -> list[str]:
    findings: list[str] = []
    for lineno, line in lines:
        if is_allowed(line):
            continue
        for span in INLINE_CODE.findall(line):
            for match in MAKE_INVOCATION.finditer(span):
                target = match.group(1)
                if target not in real_targets:
                    findings.append(f'{rel(doc)}:{lineno}  unknown make target: `make {target}`')
    return findings


def check_backtick_paths(doc: Path, lines: list[tuple[int, str]]) -> list[str]:
    findings: list[str] = []
    for lineno, line in lines:
        if is_allowed(line):
            continue
        link_text_ends = {m.end() for m in MD_LINK_TEXT.finditer(line)}
        for match in INLINE_CODE.finditer(line):
            if match.end() + 2 in link_text_ends:  # `text`](  — the '](' follows right after
                continue
            span = match.group(1)
            if '/' not in span or any(ch in span for ch in PLACEHOLDER_CHARS):
                continue
            if not PATH_CANDIDATE.match(span):
                continue
            if not resolve_path(span, doc):
                findings.append(f'{rel(doc)}:{lineno}  dead path: `{span}`')
    return findings


# `pm <kind> <status> <id>` — the form whose STATUS is the project's own word.
# 0.6.0: the auto-loaded rule said `pm story reviewing`, which exits 2 because
# the seed declares no review word for a STORY. A make target and a path were
# already checked here; an INVOCATION is the same claim and nobody read it.
_STATUS_FORM = re.compile(r'^pm\s+(story|feature|milestone|bug)\s+([a-z-]+)')


def declared_states() -> dict[str, tuple[str, ...]]:
    """{kind: every state the project declared}, or {} when the tree has no
    flow — then this rule reports nothing rather than inventing a vocabulary."""
    from agentic_sdlc.repo.pm import model
    try:
        cfg = model.load()
    except SystemExit:
        return {}
    return {kind: flow.order for kind, flow in cfg.flows.items()}


def check_invocations(doc: Path, lines: list[tuple[int, str]],
                      states: dict[str, tuple[str, ...]]) -> list[str]:
    """A shipped sentence naming a CLI call the CLI would refuse.

    Only the STATUS form, and only against words the project declared: this
    rule reads what the tree says rather than deciding what a verb should do
    (rule 9). A kind the project never declared is skipped, not guessed at.
    """
    findings: list[str] = []
    if not states:
        return findings
    for lineno, line in lines:
        if is_allowed(line):
            continue
        for span in INLINE_CODE.findall(line):
            match = _STATUS_FORM.match(span.strip())
            if match is None:
                continue
            kind, status = match.group(1), match.group(2)
            declared = states.get(kind)
            if not declared or status in declared:
                continue
            findings.append(
                f'{rel(doc)}:{lineno}  `{span.strip()}` '
                f'names a state [pm.states.{kind}] does not declare — this '
                f'exits 2. Declared: {" ".join(declared)}')
    return findings


def skill_entries() -> tuple[list[Path], list[Path]]:
    """(everything listed under `.claude/skills/`, the flat `.md` files in it)."""
    listed = list(walk.children(REPO_ROOT / SKILL_DIR).kept)
    return listed, [p for p in listed if p.is_file() and p.suffix == '.md']


def run() -> int:
    real_targets = real_make_targets()
    states = declared_states()
    findings: list[str] = []
    defects: list[str] = []
    skipped = 0
    docs = scope_files()
    for doc in docs:
        text = doc.read_text(encoding='utf-8', errors='replace')
        lines, unterminated = non_fenced_lines(text)
        skipped += len(text.split('\n')) - len(lines)
        if unterminated:
            defects.append(
                f'{rel(doc)}:{unterminated}  opens a code '
                f'fence that is never terminated — the rest of the file was '
                f'scanned UNMASKED; close the fence, or shorten the run of '
                f'backticks if you meant an inline span')
        findings.extend(check_links(doc, lines))
        findings.extend(check_make_targets(doc, lines, real_targets))
        findings.extend(check_backtick_paths(doc, lines))
        findings.extend(check_invocations(doc, lines, states))

    listed, flat = skill_entries()
    for skill in flat:
        findings.append(
            f'{rel(skill)}  a skill must be '
            f'<name>/{SKILL_FILENAME}; a flat .md does NOT load as a skill '
            f'(its description never fires)')

    if findings or defects:
        counts = ', '.join(
            part for part in (
                f'{len(findings)} unresolved claim(s)' if findings else '',
                f'{len(defects)} malformed doc(s)' if defects else '') if part)
        print(f'[check:doc] FAIL — {counts}, across {len(docs)} doc(s), '
              f'{skipped} fenced line(s) skipped, {len(listed)} {SKILL_DIR}/ entr(ies)')
        for finding in sorted(defects) + sorted(findings):
            print(f'  {finding}')
        print(f'\nA genuine exception (a deliberate retired-thing citation) gets a trailing '
              f'<!-- {ALLOW_MARKER} --> on its line, not a code change.')
        return 1

    if not docs:
        print('[check:doc] FAIL — scanned 0 docs; check [doc] scope')
        return 1
    print(f'[check:doc] PASS — {len(docs)} doc(s), {skipped} fenced line(s) '
          f'skipped, {len(listed)} {SKILL_DIR}/ entr(ies), 0 unresolved claims')
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.parse_args(argv)
    return run()


if __name__ == '__main__':
    raise SystemExit(main())
