#!/usr/bin/env python3
"""check doc — the checkable claims in the always-loaded docs resolve against the tree.

Over `[doc] scope` (default CLAUDE.md, .claude/rules/*.md, .claude/agents/*.md): a dead
path in a backtick span, a `make <target>` no Makefile or include declares, a dead
markdown link, a flat `.claude/skills/<name>.md` that never loads. Fenced blocks are
skipped; an unterminated fence is reported and masks nothing. A backtick span is
read across the line breaks of its paragraph and reported on the line it starts on.
A line ending in `<!-- doc-scan:allow -->` is never flagged, and neither is a span
starting on it. `[doc] ephemeral` names directories whose cited files are expected
to be gone.

    agentic-sdlc check doc
"""
from __future__ import annotations

import argparse
import re
from collections.abc import Iterator
from pathlib import Path
from agentic_sdlc.core import makefile
from agentic_sdlc.core.markdown import (
    code_span_matches, non_fenced_lines, paragraphs, span_text)
from agentic_sdlc.core import walk
from agentic_sdlc.core.walk import Kind
from agentic_sdlc.core.project import repo_root
from agentic_sdlc.core.config import config_section, relpath_tuple, str_tuple
from agentic_sdlc.repo import vehicle

REPO_ROOT = repo_root()
# Read per run, never at import, or a config error depends on import order.
DEFAULT_SCOPE = ('CLAUDE.md', '.claude/rules/*.md', '.claude/agents/*.md')
def scope_globs() -> tuple[str, ...]:
    return relpath_tuple(config_section('doc'), 'doc', 'scope', DEFAULT_SCOPE)
ALLOW_MARKER = 'doc-scan:allow'
# A skill is `<name>/SKILL.md`; only a `.md` at depth 1 is the defect.
SKILL_DIR = '.claude/skills'
SKILL_FILENAME = 'SKILL.md'

MD_LINK = re.compile(r'\[[^\]]*\]\(([^)]+)\)')
# `make` opening the span or a command (`;&|(`, a quote, `$ `, `X=y `): read
# anywhere, a wrapped `No rule to make target` read as `make target`.
MAKE_INVOCATION = re.compile(
    r'(?:^|[;&|(`"\'$])\s*(?:[A-Za-z_][A-Za-z0-9_]*=\S*\s+)*'
    r'make\s+([a-zA-Z][a-zA-Z0-9_-]*)')
PATH_CANDIDATE = re.compile(r'^[A-Za-z0-9_./-]+\.(gd|tscn|tres|py|sh|md)$')
PLACEHOLDER_CHARS = ('<', '>', '*', '$')
URL_PREFIXES = ('http://', 'https://', 'mailto:')
# Review records are create-resolve-delete by design.
# A DECISION citation. D-numbers restart per milestone, so a bare `D<n>` is
# unambiguous only inside the decisions file that owns it; the tree's
# convention for everywhere else is `<version>/D<n>`. This rule resolves the
# QUALIFIED form and deliberately says nothing about the bare one: `check pm`'s
# own rule ids are D1..D12 in a FLAT namespace, so the two spellings are
# indistinguishable by shape — 32 of the 33 bare `D<n>` in `[doc] scope` are
# gate rule ids, where bare is correct. See 0.7.0/D1.
DECISION_CITATION = re.compile(r'\b([0-9]+\.[0-9]+\.[0-9]+)/D([0-9]+)\b')
DECISION_HEADING = re.compile(r'^##\s+D([0-9]+)\b')
DECISIONS_SUFFIX = '-decisions.md'
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


def grain_documents() -> list[Path]:
    """Every markdown document in the PM tree.

    NOT `[doc] scope`, and only the decision-citation rule reads it: a `D<n>`
    is a claim about the tree wherever it is written, and the grain is where
    the defect that filed this rule was found. The path, link and `make` rules
    stay on the configured scope, which is the surface they were written for.
    """
    cfg = pm_config()
    if cfg is None:
        return []
    return sorted(walk.matching(cfg.roadmap, '**/*.md', Kind.FILE).kept)


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


def code_spans(lines: list[tuple[int, str]]) -> Iterator[tuple[int, str, bool]]:
    """(the line a span STARTS on, its text, is it a link's text) for every
    code span the three span rules read — undeclared state, path, make target.

    Paired across a PARAGRAPH, never a line (#26): `pm feature` + newline +
    `reviewing <id>` is one span, and a line-at-a-time reader both missed it
    and paired every backtick after it with the wrong partner. A finding names
    the line the span starts on, and so does `doc-scan:allow`: a span starting
    on a marked line is not read, and a marker on any other line it covers
    suppresses nothing — the line a finding names is the line its marker goes on.
    """
    for para in paragraphs(lines):
        for start, end, raw in code_span_matches(para.text):
            lineno, line = para.at(start)
            if is_allowed(line):
                continue
            # [`text`](href): the claim is the href, read by the link rule
            yield lineno, span_text(raw), para.text.startswith('](', end)


def check_make_targets(doc: Path, lines: list[tuple[int, str]], real_targets: set[str]) -> list[str]:
    findings: list[str] = []
    for lineno, span, _ in code_spans(lines):
        for match in MAKE_INVOCATION.finditer(span):
            target = match.group(1)
            if target not in real_targets:
                fix = (f' — `Makefile.devkit` defines it; '
                       f'`{vehicle.pinned("install-gates", "--force")}` '
                       f'writes the one that does'
                       if target in vehicle.TARGETS else '')
                findings.append(f'{rel(doc)}:{lineno}  unknown make target: '
                                f'`make {target}`{fix}')
    return findings


def check_backtick_paths(doc: Path, lines: list[tuple[int, str]]) -> list[str]:
    findings: list[str] = []
    for lineno, span, link_text in code_spans(lines):
        if link_text:
            continue
        if '/' not in span or any(ch in span for ch in PLACEHOLDER_CHARS):
            continue
        if not PATH_CANDIDATE.match(span):
            continue
        if not resolve_path(span, doc):
            findings.append(f'{rel(doc)}:{lineno}  dead path: `{span}`')
    return findings


# `pm <kind> <status> <id>` — the form whose STATUS is the project's own word.
# The auto-loaded rule said `pm story reviewing`, which exits 2 because
# the seed declares no review word for a STORY. A make target and a path were
# already checked here; an INVOCATION is the same claim and nobody read it.
# The `agentic-sdlc ` prefix is OPTIONAL because both forms ship: the
# auto-loaded rule writes `pm story reviewing`, the README and the agent
# definitions write it out in full, and a rule anchored at `pm` read the
# fuller half as prose. Found beside 0.6.0 review B1, which is the same
# defect one layer out — a rule that is correct and cannot reach.
# 0.8.0 spelled every shipped call through the stock wiring's vehicle, `make pm
# ARGS='story building <id>'` (or `pm` and its words handed to `make sdlc`), and
# a rule anchored at `pm` read none of them: the sweep would have blinded it (C2).
# So a vehicle span is read as the argv the verb receives, both parses undone
# by the helper that spells it — either quote style, since both reach the verb.
_STATUS_FORM = re.compile(
    rf'^(?:{re.escape(vehicle.PROGRAM)}\s+)?pm\s+(story|feature|milestone|bug)'
    r'\s+([a-z-]+)')


def _as_invoked(span: str) -> str:
    """The span as the CLI would receive it: a vehicle line becomes its argv,
    joined; anything else is itself. A `make` line the vehicle cannot read is
    not an invocation this rule can name, so it is returned unread."""
    if span.split(None, 1)[:1] != [vehicle.MAKE]:
        return span
    try:
        return ' '.join(vehicle.argv_of(span))
    except ValueError:
        return span


def declared_states() -> dict[str, tuple[str, ...]]:
    """{kind: every state the project declared}, or {} when the tree has no
    flow — then this rule reports nothing rather than inventing a vocabulary."""
    from agentic_sdlc.repo.pm import vocabulary
    try:
        cfg = vocabulary.load()
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
    for lineno, span, _ in code_spans(lines):
        match = _STATUS_FORM.match(_as_invoked(span.strip()))
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


def pm_config():
    """The project's PM config, or None when the tree declares no flow."""
    from agentic_sdlc.repo.pm import vocabulary
    try:
        return vocabulary.load()
    except SystemExit:
        return None


def decision_index() -> dict[str, tuple[str, set[str]]]:
    """{version: (milestone id, every D-number its decisions file records)}.

    Keyed on the VERSION, because that is what a citation spells. A milestone
    declaring no `version:` is unreachable by citation and is skipped rather
    than guessed at; `shared_doc` answers where the file lives, so a nested
    tree and a pooled one are read the same way.
    """
    index: dict[str, tuple[str, set[str]]] = {}
    cfg = pm_config()
    if cfg is None:
        return index
    from agentic_sdlc.repo.pm import inventory, vocabulary
    for grain in inventory.milestones(cfg):
        version = grain.field('version').strip()
        decisions = inventory.shared_doc(cfg, grain, vocabulary.DECISION_FILE_NAME)
        if not version or not decisions.is_file():
            continue
        kept, _ = non_fenced_lines(
            decisions.read_text(encoding='utf-8', errors='replace'))
        index[version] = (grain.gid, {
            match.group(1) for _, line in kept
            if (match := DECISION_HEADING.match(line))})
    return index


def check_decision_citations(doc: Path, lines: list[tuple[int, str]],
                             index: dict[str, tuple[str, set[str]]]) -> list[str]:
    """A `<version>/D<n>` naming a ruling the tree does not record.

    The citation is a claim about the tree exactly as `make <target>` is, and
    nothing read it until 0.7.0 — which is how a grain shipped a `D1` pointing
    at a real decision that said something else.
    """
    findings: list[str] = []
    if not index:
        return findings
    for lineno, line in lines:
        if is_allowed(line):
            continue
        for match in DECISION_CITATION.finditer(line):
            version, number = match.group(1), match.group(2)
            known = index.get(version)
            if known is None:
                findings.append(
                    f'{rel(doc)}:{lineno}  `{match.group(0)}` names a version '
                    f'with no decisions file. Recorded: '
                    f'{" ".join(sorted(index))}')
                continue
            milestone_id, numbers = known
            if number not in numbers:
                records = (f'D{" D".join(sorted(numbers, key=int))}'
                           if numbers else 'nothing')
                findings.append(
                    f'{rel(doc)}:{lineno}  `{match.group(0)}` names a decision '
                    f'{milestone_id} does not record — it records {records}')
    return findings


def skill_entries() -> tuple[list[Path], list[Path]]:
    """(everything listed under `.claude/skills/`, the flat `.md` files in it)."""
    listed = list(walk.children(REPO_ROOT / SKILL_DIR).kept)
    return listed, [p for p in listed if p.is_file() and p.suffix == '.md']


def run() -> int:
    real_targets = real_make_targets()
    states = declared_states()
    decisions = decision_index()
    cited = 0
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
        findings.extend(check_decision_citations(doc, lines, decisions))
        cited += sum(len(DECISION_CITATION.findall(line)) for _, line in lines)

    grains = grain_documents()
    for grain in grains:
        lines, _ = non_fenced_lines(
            grain.read_text(encoding='utf-8', errors='replace'))
        findings.extend(check_decision_citations(grain, lines, decisions))
        cited += sum(len(DECISION_CITATION.findall(line)) for _, line in lines)

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
              f'{skipped} fenced line(s) skipped, {len(listed)} {SKILL_DIR}/ entr(ies), '
              f'{cited} decision citation(s) over {len(grains)} grain(s) '
              f'and {len(decisions)} decisions file(s)')
        for finding in sorted(defects) + sorted(findings):
            print(f'  {finding}')
        print(f'\nA genuine exception (a deliberate retired-thing citation) gets a trailing '
              f'<!-- {ALLOW_MARKER} --> on its line, not a code change.')
        return 1

    if not docs:
        print('[check:doc] FAIL — scanned 0 docs; check [doc] scope')
        return 1
    print(f'[check:doc] PASS — {len(docs)} doc(s), {skipped} fenced line(s) '
          f'skipped, {len(listed)} {SKILL_DIR}/ entr(ies), '
          f'{cited} decision citation(s) over {len(grains)} grain(s) and '
          f'{len(decisions)} decisions file(s), 0 unresolved claims')
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.parse_args(argv)
    return run()


if __name__ == '__main__':
    raise SystemExit(main())
