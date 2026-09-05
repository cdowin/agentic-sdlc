"""Hard rule 8, as a gate — this package knows nothing about its consumers.

The rule in one line: no file here names a consuming project, reads a path
outside this checkout, or gates on another repo's content or working state.

It is a gate rather than a convention because the alternative was measured. The
package was extracted from two private game repos, kept their names in its
prose as worked examples, and then grew a release gate (`tools/consumer_smoke.py`,
971 lines) that ran every verb against whichever of those two checkouts happened
to be cloned on the machine. In CI, where neither is, it SKIPPED — so a tag's
verdict depended on whose laptop asked, and somebody else's uncommitted work
could redden it. A release gate that can be reddened by another repo's working
state is not a gate.

WHY THE BANNED NAMES LIVE HERE. Naming them is itself consumer knowledge, so
there is exactly one place in the tree allowed to hold them: this file, as a
tombstone. `tests/` is the harness, not the package — nothing shipped imports
this — and a regression guard that cannot say what regressed cannot fire. Three
narrower guards predate it and stay, because each also pins a claim of its own
about the file set it reads: test_ci_workflows (workflows), test_makefile_include
(the include), test_runners_installable and test_install (the installables).
This one is the whole-tree form.

WHAT IS DELIBERATELY OUT OF SCOPE. `pm/`, `CHANGELOG.md` and `docs/reviews/` are
the LOG: dated records of what was measured on a given day. Rewriting a record
to say something other than what was measured is falsifying it, so they are
excluded by path, out loud, here. The rule governs what is WRITTEN from now on —
a new CHANGELOG bullet describes behaviour generically ("a 251-story tree"),
never by naming a private repo.

HOW THE CENSUS IS SCOPED, AND WHY IT IS A DENY LIST. Everything under the
checkout is scanned; the exclusions are enumerated, reasoned, and asserted to
account for every file the walk saw. It was an ALLOWLIST of fifteen suffixes
until this release, which meant a file type nobody had thought of arrived
UNSCANNED and stayed that way until somebody remembered to add it — measured at
21 files dropped in silence, 18 of them tracked, including all ten fixture
`project.godot`, which is exactly the artifact a fixture gets vendored FROM a
consumer. A planted name there passed the whole suite. The default is now
SCANNED and the deny list holds only bytes-not-prose, each entry with its
reason. For the same reason a file this gate cannot DECODE is a finding rather
than a skip: one stray non-UTF-8 byte used to remove a whole file from the scan
without a word, so a deny list that forgets a binary type fails loudly instead
of quietly (CLAUDE.md rule 4).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import NamedTuple

import pytest

from support import REPO_ROOT

# The projects this package was extracted from. Word-bounded on purpose: the
# committed corpus is a hiking game's data and legitimately spells `trail_mile`
# and `c_on_trail`, which are domain vocabulary and not a project reference.
CONSUMER_NAMES = (r'\bnullbound\b', r'\bNullBound\b', r'\bNULLBOUND\b',
                  r'\btrail\b', r'\bTrail\b', r'\bTRAIL\b',
                  r'\bappalachian\b', r'\bAppalachian\b')

# Reaching OUTSIDE the checkout, as literals. A path handed in on the command
# line is the caller's choice and is not this (`pm ledger record
# --from-transcript` takes an absolute path under ~/.claude/ by design); what is
# banned is the package deciding on its own to go looking somewhere else.
#
# The `[w]orkspace` spelling is load-bearing, not a typo: it matches the same
# text while keeping THIS line out of its own census, so the file needs no
# exemption and a real literal added here later is still caught. The rest are
# already escaped enough not to match themselves.
OUTSIDE_READS = (r'~/[w]orkspace', r'Path\.home\(\)',
                 r'os\.path\.expanduser\(\s*[\'"]~',
                 r'\$HOME/[w]orkspace',
                 r'os\.environ\[[\'"]HOME[\'"]\]\s*\)?\s*/')

# The OTHER KIT'S ARTIFACTS. Decision D2 of 0.2.0: an installable belongs to
# the kit whose ARTIFACT it acts on, not to the kit whose STRUCTURE it borrows.
# `Makefile.devkit` carried the gate framework and one language's target roster
# in one file, which is what blocked splitting this package in two — so this is
# the gate that keeps the roster out, the way CONSUMER_NAMES keeps consumer
# names out.
#
# THESE ARE OPERATIVE TOKENS, NOT THE WORD. A file that spells `project.godot`
# or `--headless` is ACTING on an engine artifact; a comment that says the word
# "Godot" while explaining why the split happened is doing the opposite, and
# CLAUDE.md wants that prose kept. Banning the word would make every historical
# note an exemption, and a scanner whose allowlist grows every release is a
# scanner somebody eventually switches off.
ENGINE_ARTIFACTS = (r'project\.godot', r'\.tscn\b', r'\.tres\b',
                    r'\.gd\.uid\b', r'\bres://', r'GDK_GODOT',
                    r'--headless', r'\bgdlint\b', r'\bgut_cmdln\b',
                    r'\bResourceUID\b', r'compile_sweep', r'gdk_runners')

# Where a leak would actually SHIP. Narrower than the consumer-name scan on
# purpose: `docs/`, `pm/` and `CHANGELOG.md` are the record of the split and
# have to be able to say what left. `tests/` is excluded for the same reason
# this file is — the guards spell what they guard.
SHIPPING_ROOTS = ('src/', 'tools/', '.github/')

# The LOG. Dated records of what was measured; not rewritable without lying.
LOG_PATHS = ('pm/', 'docs/reviews/', 'CHANGELOG.md')

# Directories that are not the repo's content. The one exclusion taken on
# trust, and it has to be: `.venv` installs third-party code whose names are
# nobody's business here, and `.git` holds every byte the tree ever had. Each
# is tool output, none is authored, and adding a name to this set is a visible
# act in a diff — unlike the suffix filter this replaced, which excluded by
# forgetting.
NOT_CONTENT = {'.git', '.gate-reports', '.pytest_cache', '.ruff_cache', '.venv',
               '__pycache__', 'node_modules', '.mypy_cache'}

# The tombstones: files allowed to spell a banned name, because banning it is
# what they do. Every entry carries its reason — an allowlist without one is
# how a scanner gets narrowed until it reports nothing.
# This file is NOT among them: it spells the names only inside `\b...\b`
# regexes, which the same regexes do not match, so it needs no exemption and a
# bare name added here in future is caught like anywhere else.
TOMBSTONES = {
    'tests/test_ci_workflows.py': 'guards the workflows against the same names',
    'tests/test_makefile_include.py': 'guards Makefile.devkit against them',
    'tests/test_install.py': 'guards every installed hook',
}

# The same discipline, for ENGINE_ARTIFACTS. Empty, and that is the assertion:
# every engine token left this package in 0.2.0 and nothing under
# SHIPPING_ROOTS needs to spell one. An entry added here has to carry the
# sentence saying why the file ACTS on an engine artifact — at which point the
# honest answer is usually that the file belongs to the other kit.
ENGINE_TOMBSTONES: dict[str, str] = {}

# THE MIGRATION DOCUMENT — one file, one clause, and both halves of the
# exemption written down.
#
# This package was split out of a larger one, and the record of that split has
# to say which repo each step happens in. A migration plan written in SHAPES
# ("the repo the verbs stayed in") is not a plan anybody can follow. So exactly
# one path is exempt, and the exemption is deliberately the narrowest thing
# that works:
#
#   * ONE EXACT PATH, compared with `==`. Not a prefix, not a glob, not a
#     directory — nothing can arrive inside it, and a sibling file one
#     character away is scanned like everything else (asserted below).
#   * ONE CLAUSE. Only the consumer-NAME clause. The migration doc is scanned
#     for outside-checkout reads like every other file, which is why the
#     home-relative path literal it used to open with was REWRITTEN, not
#     exempted.
#   * IT CANNOT REACH CODE. A single top-level `.md` is not package source, not
#     an installable, not a workflow, not a hook — the four places a leak would
#     actually ship. Structural, and asserted rather than asserted-in-prose.
#   * IT DECLARES ITSELF. The file carries the marker below, so the exemption
#     is visible from the document as well as from the gate: taking it means
#     editing both sides, in one diff.
#   * IT EXPIRES. The gate fails if the entry outlives the file, and fails if
#     the file stops needing it.
#
# When the migration lands, both halves go. Until then this is the one place in
# the tree, other than the tombstones, where a repo may be named.
MIGRATION_DOC = 'HANDOFF.md'
MIGRATION_DOC_MARKER = 'rule-8: migration document'

# Rule 4: a census that collapses must FAIL, not pass over nothing. The tree is
# ~330 content files today; the floor is well under that and still far above
# zero.
FILE_FLOOR = 120

# The exceptions to "everything is scanned", by lowercased SUFFIX, each with
# its reason. Bytes, not prose: none of these can hold a sentence naming a
# consumer. This list is a convenience, never a correctness dependency — a
# binary type that is NOT here does not slip through, it fails to decode and
# that is a finding. Adding a type here is therefore a comfort measure taken
# after the gate has already shouted, which is the right order.
DENY_SUFFIXES = {
    '.png': 'raster image', '.jpg': 'raster image', '.jpeg': 'raster image',
    '.gif': 'raster image', '.webp': 'raster image', '.ico': 'icon binary',
    '.ttf': 'font binary', '.otf': 'font binary', '.woff': 'font binary',
    '.woff2': 'font binary',
    '.wav': 'audio binary', '.ogg': 'audio binary',
    '.zip': 'archive', '.gz': 'archive', '.tar': 'archive', '.whl': 'built wheel',
    '.pyc': 'compiled bytecode', '.pyo': 'compiled bytecode',
    '.so': 'compiled extension', '.dylib': 'compiled extension',
    '.dll': 'compiled extension',
    '.res': 'Godot binary resource', '.scn': 'Godot binary scene',
    '.ctex': 'Godot compressed texture',
}

# The same, by exact file NAME rather than suffix.
DENY_NAMES = {
    '.DS_Store': 'Finder metadata, written into any directory macOS opens',
}

# The marker every unreadable-file finding carries, so the tombstone test can
# tell "this file names a consumer" from "this file could not be read at all".
UNREADABLE = 'UNREADABLE'


class Census(NamedTuple):
    """What the walk saw, split four ways with nothing left over.

    `walked` is every file, and the other four partition it. A census that
    cannot report its own exclusions is how both of this gate's 0.24.0 holes
    hid: the old one counted what the walk KEPT and never asked what it
    dropped.
    """

    walked: list[Path]
    scanned: list[Path]
    log: list[Path]
    denied: list[tuple[Path, str]]
    tool_output: list[Path]

    def classified(self) -> set[Path]:
        return (set(self.scanned) | set(self.log) | set(self.tool_output)
                | {path for path, _ in self.denied})

    def content(self) -> set[Path]:
        """Everything but the tool output — the files somebody here authored."""
        return set(self.scanned) | set(self.log) | {path for path, _ in self.denied}

    def summary(self) -> str:
        return (f'{len(self.walked)} walked = {len(self.scanned)} scanned + '
                f'{len(self.log)} log + {len(self.denied)} denied + '
                f'{len(self.tool_output)} tool output')

    def denied_report(self) -> str:
        if not self.denied:
            return '(nothing denied)'
        return '\n'.join(f'  {path.name}: {reason}' for path, reason in self.denied)


def _is_log(rel: str) -> bool:
    return any(rel == path or rel.startswith(path) for path in LOG_PATHS)


def deny_reason(path: Path) -> str | None:
    """Why this file is bytes rather than prose, or None — meaning scan it."""
    if path.name in DENY_NAMES:
        return DENY_NAMES[path.name]
    return DENY_SUFFIXES.get(path.suffix.lower())


def take_census(root: Path = REPO_ROOT) -> Census:
    """Every file under `root`, classified — nothing dropped in silence.

    The worktree rather than `git ls-files`, deliberately: a rule-8 violation
    arrives as a NEW file, and a census taken from the index would not see it
    until somebody staged it — which is one commit too late.

    `root` is a parameter so the classifier can be exercised on a scratch tree
    holding the shapes this repo does not (and must not) contain: a planted
    consumer name, a non-UTF-8 tail, an unclassified binary.
    """
    census = Census([], [], [], [], [])
    for path in sorted(root.rglob('*')):
        if not path.is_file() or path.is_symlink():
            continue
        census.walked.append(path)
        rel = path.relative_to(root).as_posix()
        if set(Path(rel).parts) & NOT_CONTENT:
            census.tool_output.append(path)
        elif _is_log(rel):
            census.log.append(path)
        elif (reason := deny_reason(path)) is not None:
            census.denied.append((path, reason))
        else:
            census.scanned.append(path)
    return census


def scanned_files(root: Path = REPO_ROOT) -> list[Path]:
    """The files the name/path clauses below read."""
    return take_census(root).scanned


def offending_lines(path: Path, patterns: tuple[str, ...],
                    root: Path = REPO_ROOT) -> list[str]:
    """Findings for one file — including "I could not read it".

    A file this gate cannot decode is a file it cannot CLEAR, so the decode
    failure is a finding rather than a skip. This returned `[]` on
    `UnicodeDecodeError` until this release, which meant one stray byte
    anywhere in a file removed the whole file from the scan without a word: the
    planted name plus a two-byte tail passed the suite. Same shape as the write
    plane's own refusal (`godot/write.utf8_refusal_reason` — "not valid UTF-8
    (… at byte N) — refusing to rewrite bytes this tool cannot read"), stated
    here rather than imported, because nothing in the repo family may reach
    into the godot family (CLAUDE.md § Where things live).
    """
    rel = path.relative_to(root).as_posix()
    try:
        text = path.read_text(encoding='utf-8')
    except UnicodeDecodeError as err:
        return [f'{rel}:0: {UNREADABLE} — not valid UTF-8 ({err.reason} at byte '
                f'{err.start}); this gate cannot clear bytes it cannot read. If '
                f'the file is genuinely binary, give it a reason in '
                f'DENY_SUFFIXES or DENY_NAMES.']
    except OSError as err:
        return [f'{rel}:0: {UNREADABLE} — {err.strerror or err}; this gate '
                f'cannot clear a file it cannot open.']
    return [f'{rel}:{n}: {line.strip()[:120]}'
            for n, line in enumerate(text.splitlines(), 1)
            if any(re.search(p, line) for p in patterns)]


def _unreadable(hits: list[str]) -> list[str]:
    return [hit for hit in hits if f': {UNREADABLE} — ' in hit]


def test_the_census_is_not_empty_and_covers_the_package_and_the_harness():
    """The scan itself, before anything it claims. A glob that matched nothing
    would make every assertion below vacuously true — this package's cardinal
    sin wearing a green tick (CLAUDE.md rule 4)."""
    census = take_census()
    files = census.scanned
    assert len(files) >= FILE_FLOOR, (
        f'census collapsed to {len(files)} file(s), floor {FILE_FLOOR} — the '
        f'walk broke, or the tree shrank and this floor is now a lie. '
        f'{census.summary()}')
    tops = {path.relative_to(REPO_ROOT).parts[0] for path in files}
    for required in ('src', 'tests', 'CLAUDE.md', 'README.md', 'Makefile'):
        assert required in tops, f'{required} is outside the scan: {sorted(tops)}'


def test_the_census_accounts_for_every_file_it_walked():
    """The question the old census could not answer: what did you DROP?

    Both holes this gate shipped with hid behind a count of what the walk KEPT
    — 313 files, floor 120, green — while 21 files left the scan unnamed. The
    walk is repeated INDEPENDENTLY here rather than read off the census, so a
    silent `continue` growing back inside `take_census` stops covering this one
    and that is the failure.

    The comparison is over content only: the tool-output directories churn
    (`.pytest_cache` is written by the very run making this assertion), and a
    file that appears between the two walks would fail an equality that means
    nothing. Their accounting is still asserted — by the partition below, which
    is taken from a single snapshot.
    """
    census = take_census()
    independent = {path for path in REPO_ROOT.rglob('*')
                   if path.is_file() and not path.is_symlink()
                   and not set(path.relative_to(REPO_ROOT).parts) & NOT_CONTENT}
    unclassified = sorted(independent - census.content())
    assert not unclassified, (
        f'{len(unclassified)} file(s) left the census unclassified — the walk '
        f'dropped them without naming them, which is how a suffix allowlist '
        f'hides 18 files. {census.summary()}\n'
        + '\n'.join(str(path.relative_to(REPO_ROOT)) for path in unclassified[:25]))
    parts = (len(census.scanned) + len(census.log) + len(census.denied)
             + len(census.tool_output))
    assert parts == len(census.walked), (
        f'the four buckets do not partition the walk: {census.summary()}')
    assert len(census.classified()) == len(census.walked), (
        f'a file is in two buckets at once: {census.summary()}')


def test_nothing_that_reads_as_text_is_excluded_as_binary():
    """The deny list may only hold bytes, never prose.

    An exclusion that covers a readable file is a hole with a reason attached,
    and it would be permanent — nothing else looks at what this list drops.
    The tree denies nothing today, which `Census.summary()` reports out loud
    rather than leaving to be inferred; the live case is exercised on the
    scratch tree below, where a `.png` is both written and denied.
    """
    census = take_census()
    prose = []
    for path, reason in census.denied:
        try:
            path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        prose.append(f'{path.relative_to(REPO_ROOT).as_posix()} (excluded as {reason})')
    assert not prose, (
        'these files are excluded from the rule-8 scan as binary and decode as '
        'UTF-8 — scan them instead of exempting them:\n' + '\n'.join(prose))


@pytest.mark.parametrize('rel, why', sorted(TOMBSTONES.items()))
def test_every_tombstone_still_earns_its_exemption(rel, why):
    """An allowlist entry that no longer needs to be there is an entry that
    will one day cover a real violation. Each must still spell a banned name —
    and must still be READABLE, because an exemption earned by a file nobody
    can decode is the skip this gate just stopped taking."""
    path = REPO_ROOT / rel
    assert path.is_file(), f'{rel} is allowlisted and does not exist ({why})'
    hits = offending_lines(path, CONSUMER_NAMES)
    assert not _unreadable(hits), (
        f'{rel} is allowlisted ({why}) and cannot be read:\n'
        + '\n'.join(_unreadable(hits)))
    assert hits, (
        f'{rel} no longer names a consumer, so its exemption ({why}) covers '
        f'nothing and must be deleted from TOMBSTONES')


def names_a_consumer(root: Path = REPO_ROOT) -> list[str]:
    """The rule's first clause over any tree, exemptions applied.

    A function rather than a loop inside the test, so the hostile cases at the
    bottom attack THE CODE THE REPO RUNS. An exemption proven on a
    re-implementation of itself proves nothing about the gate.
    """
    hits = []
    for path in scanned_files(root):
        rel = path.relative_to(root).as_posix()
        if rel in TOMBSTONES or rel == MIGRATION_DOC:
            continue
        hits.extend(offending_lines(path, CONSUMER_NAMES, root))
    return hits


def test_no_file_names_a_consuming_project():
    """The rule's first clause. A worked example names a SHAPE — "a project
    whose `check` carries extra gates" — never a repo: the reader of a generic
    example learns the rule, and the reader of a named one learns that this
    tool has favourites."""
    hits = names_a_consumer()
    assert not hits, (
        'a consuming project is named in the tool (CLAUDE.md hard rule 8). '
        'Rewrite the sentence generically — do not delete it and leave a '
        f'dangling explanation:\n' + '\n'.join(hits[:25]))


def test_the_migration_doc_still_earns_its_exemption():
    """Same contract the tombstones carry: an entry that no longer covers
    anything is an entry waiting to cover something real. It must exist, be
    readable, still name a repo, and still be a file the gate would otherwise
    have SCANNED — an exemption shadowed by the LOG or the deny list would be
    doing nothing while looking like it does."""
    path = REPO_ROOT / MIGRATION_DOC
    assert path.is_file(), (
        f'{MIGRATION_DOC} is exempt and does not exist — the migration landed, '
        f'so delete MIGRATION_DOC too')
    hits = offending_lines(path, CONSUMER_NAMES)
    assert not _unreadable(hits), (
        f'{MIGRATION_DOC} is exempt and cannot be read:\n'
        + '\n'.join(_unreadable(hits)))
    assert hits, (
        f'{MIGRATION_DOC} no longer names a repo, so its exemption covers '
        f'nothing and must be deleted')
    assert path in set(scanned_files()), (
        f'{MIGRATION_DOC} is not in the SCANNED bucket, so exempting it is a '
        f'no-op dressed as a decision — {take_census().summary()}')


def test_the_migration_doc_declares_its_own_exemption():
    """Both halves, in one diff. A file cannot be quietly moved under this
    exemption: it has to say so itself, where the next reader of the document
    will see it."""
    text = (REPO_ROOT / MIGRATION_DOC).read_text(encoding='utf-8')
    assert MIGRATION_DOC_MARKER in text, (
        f'{MIGRATION_DOC} is exempt and does not say so. Add the '
        f'{MIGRATION_DOC_MARKER!r} note, or drop the exemption')


def test_the_exemption_cannot_reach_anything_that_ships():
    """The structural argument, checked instead of trusted.

    The exemption is safe because of WHERE it points, so that is the thing to
    assert: one top-level markdown file. Package source, the installables, the
    workflows and the hooks are all at depth, so no spelling of this constant
    can cover a file that ships to a consumer — and a `packages` root read out
    of pyproject.toml says the same thing a second way.
    """
    parts = Path(MIGRATION_DOC).parts
    assert len(parts) == 1, (
        f'{MIGRATION_DOC} is not top-level; a nested exemption can sit inside '
        f'src/, tools/ or .github/, which is the whole thing this rules out')
    assert MIGRATION_DOC.endswith('.md'), f'{MIGRATION_DOC} is not markdown'
    for shipped in ('src/', 'tools/', '.github/', 'tests/fixtures/'):
        assert not MIGRATION_DOC.startswith(shipped), MIGRATION_DOC
    pyproject = (REPO_ROOT / 'pyproject.toml').read_text(encoding='utf-8')
    assert 'packages = ["src/agentic_sdlc"]' in pyproject, (
        'the wheel root moved — re-derive what "does not ship" means before '
        'trusting this exemption')
    assert MIGRATION_DOC not in pyproject, (
        f'{MIGRATION_DOC} is named in pyproject.toml, so it may be packaged')


def test_nothing_reaches_for_a_path_outside_this_checkout():
    """The rule's second clause, and the one the deleted smoke gate broke. A
    verdict computed from a directory that may or may not exist on the machine
    running it is a different verdict on every machine."""
    hits = []
    for path in scanned_files():
        rel = path.relative_to(REPO_ROOT).as_posix()
        if rel in TOMBSTONES:
            continue  # MIGRATION_DOC is NOT skipped here: it buys one clause
        hits.extend(offending_lines(path, OUTSIDE_READS))
    assert not hits, (
        'something reads a path outside this checkout (CLAUDE.md hard rule 8). '
        'A check that needs realistic data VENDORS it under tests/fixtures/:\n'
        + '\n'.join(hits[:25]))


def test_the_full_gate_is_a_composition_of_self_contained_targets():
    """`make milestone` must not acquire a member that needs another repo. The
    three it has all read this checkout alone, which is why CI and a laptop
    reach the same verdict."""
    body = (REPO_ROOT / 'Makefile').read_text(encoding='utf-8')
    match = re.search(r'^milestone:(.*)$', body, re.M)
    assert match, 'the Makefile no longer declares a `milestone` target'
    members = match.group(1).split()
    assert members == ['gates', 'hooks-self-test', 'matrix'], members
    for member in members:
        recipe = re.search(rf'^{member}:.*?\n((?:\t.*\n|\n)*)', body, re.M)
        assert recipe, f'{member} has no recipe in this Makefile'
        assert not re.search(r'\.\./|~/|\$\(HOME\)|\$\$HOME', recipe.group(1)), (
            f'`{member}` reaches outside the checkout: {recipe.group(1)!r}')


# --------------------------------------------------------------------------
# The census, attacked on a scratch tree.
#
# The two holes this gate shipped with were both proven by planting a consumer
# name in THIS repo and watching the suite stay green, which is a measurement
# nothing here can repeat: the repo must not contain a violation. So the
# classifier and the reader are pointed at a tree built to hold every shape
# that used to escape — an allowlist miss, a non-UTF-8 tail, a binary nobody
# classified — and each is asserted to produce a finding rather than a skip.
# --------------------------------------------------------------------------

# The planted violation, assembled from the pattern rather than spelled out.
# This file's whole exemption is that it holds no BARE consumer name (see the
# docstring), so a literal here would end it and force an entry in TOMBSTONES —
# which would then cover a real name added later. Same reason as the
# `[w]orkspace` spelling above: load-bearing, not a flourish.
PLANT = CONSUMER_NAMES[0].replace(r'\b', '') + ' is the consumer'

# The same trick for the SECOND clause: the outside-read plant is unescaped
# from its own pattern rather than typed, so this file still spells no literal
# either clause matches and still needs no exemption of its own.
OUTSIDE_PLANT = OUTSIDE_READS[1].replace('\\', '') + ' / "x"'


def _scratch_tree(root: Path) -> None:
    """A miniature of this repo's shapes, with no violation in it."""
    (root / 'src').mkdir()
    (root / 'pm').mkdir()
    (root / '.git').mkdir()
    (root / 'tests' / 'fixtures' / 'canon_repo').mkdir(parents=True)
    (root / 'src' / 'tool.py').write_text('print("hello")\n', encoding='utf-8')
    (root / 'README.md').write_text('a project whose check carries extra gates\n',
                                    encoding='utf-8')
    (root / 'tests' / 'fixtures' / 'canon_repo' / 'project.godot').write_text(
        '[application]\n\nconfig/name="props fixture"\n', encoding='utf-8')
    (root / 'tests' / 'fixtures' / 'canon_repo' / 'icon.svg.uid').write_text(
        'uid://abc\n', encoding='utf-8')
    (root / 'pm' / 'review.md').write_text(f'{PLANT}\n', encoding='utf-8')
    (root / '.git' / 'COMMIT_EDITMSG').write_text(f'{PLANT}\n', encoding='utf-8')


def _names_found(root: Path) -> list[str]:
    hits = []
    for path in scanned_files(root):
        hits.extend(offending_lines(path, CONSUMER_NAMES, root))
    return hits


class TestTheCensusOnAScratchTree:

    def test_a_name_in_a_project_godot_is_a_finding(self, tmp_path):
        """The exact file the suffix allowlist dropped, and the exact artifact
        a fixture gets vendored from. Ten of them are in this repo; a planted
        name in one passed all 1,761 tests before this release."""
        _scratch_tree(tmp_path)
        target = tmp_path / 'tests' / 'fixtures' / 'canon_repo' / 'project.godot'
        assert not _names_found(tmp_path), 'the scratch tree started dirty'
        target.write_text(target.read_text(encoding='utf-8') + f'\n; {PLANT}\n',
                          encoding='utf-8')
        hits = _names_found(tmp_path)
        assert any('project.godot' in hit for hit in hits), hits

    def test_a_name_in_a_uid_sidecar_is_a_finding(self, tmp_path):
        """`.uid` was the other dropped suffix — eight tracked files of it."""
        _scratch_tree(tmp_path)
        target = tmp_path / 'tests' / 'fixtures' / 'canon_repo' / 'icon.svg.uid'
        target.write_text(f'{PLANT}\n', encoding='utf-8')
        assert any('icon.svg.uid' in hit for hit in _names_found(tmp_path))

    def test_a_suffix_nobody_has_ever_seen_is_scanned_not_dropped(self, tmp_path):
        """The inversion, as a property: coverage by default, not by memory."""
        _scratch_tree(tmp_path)
        (tmp_path / 'src' / 'notes.wat').write_text(f'{PLANT}\n', encoding='utf-8')
        assert any('notes.wat' in hit for hit in _names_found(tmp_path))

    def test_a_non_utf8_tail_does_not_remove_a_file_from_the_scan(self, tmp_path):
        """Hole two, and the worse one: it is not suffix-bounded. The same
        planted name plus `\\xff\\xfe` turned one failure into eight passes."""
        _scratch_tree(tmp_path)
        target = tmp_path / 'src' / 'notes.md'
        target.write_bytes(PLANT.encode() + b'\n\xff\xfe binary tail\n')
        hits = _names_found(tmp_path)
        assert hits, 'a non-UTF-8 byte silently emptied the scan for this file'
        assert _unreadable(hits), hits
        assert 'not valid UTF-8' in hits[0] and 'src/notes.md' in hits[0], hits

    def test_an_unclassified_binary_is_a_finding_rather_than_a_skip(self, tmp_path):
        """A deny list that forgets a type must fail LOUDLY. This is what makes
        the list a convenience instead of a correctness dependency."""
        _scratch_tree(tmp_path)
        (tmp_path / 'src' / 'blob.dat').write_bytes(b'\x00\x01\xff\xfe\x00')
        hits = _names_found(tmp_path)
        assert _unreadable(hits) and 'blob.dat' in hits[0], hits

    def test_a_classified_binary_is_excluded_with_its_reason(self, tmp_path):
        """And a type that IS classified drops out quietly, carrying why."""
        _scratch_tree(tmp_path)
        (tmp_path / 'src' / 'logo.png').write_bytes(b'\x89PNG\r\n\x1a\n\xff\xfe')
        census = take_census(tmp_path)
        denied = {path.name: reason for path, reason in census.denied}
        assert denied == {'logo.png': 'raster image'}, denied
        assert not _names_found(tmp_path)

    def test_the_log_and_the_tool_output_stay_out_of_the_scan(self, tmp_path):
        """Both scratch plants live in excluded trees, and both must stay
        excluded — the LOG is a dated record and `.git` is not content."""
        _scratch_tree(tmp_path)
        census = take_census(tmp_path)
        assert [path.name for path in census.log] == ['review.md']
        assert [path.name for path in census.tool_output] == ['COMMIT_EDITMSG']
        assert not _names_found(tmp_path)

    def test_every_walked_file_lands_in_exactly_one_bucket(self, tmp_path):
        """The accounting property, on a tree small enough to enumerate."""
        _scratch_tree(tmp_path)
        (tmp_path / 'src' / 'logo.png').write_bytes(b'\x89PNG\r\n')
        census = take_census(tmp_path)
        assert len(census.walked) == 7, census.summary()
        assert len(census.classified()) == len(census.walked), census.summary()
        assert (len(census.scanned) + len(census.log) + len(census.denied)
                + len(census.tool_output)) == len(census.walked), census.summary()

    def test_the_census_reports_what_it_dropped(self, tmp_path):
        """A census that cannot name its exclusions is how both holes hid."""
        _scratch_tree(tmp_path)
        (tmp_path / 'src' / 'logo.png').write_bytes(b'\x89PNG\r\n')
        census = take_census(tmp_path)
        assert census.denied_report() == '  logo.png: raster image'
        assert '1 denied' in census.summary()


# --------------------------------------------------------------------------
# The exemption, attacked on the same scratch tree.
#
# An exemption is a hole with a reason attached, and the reason is only worth
# anything if the hole is the size it claims. These cases plant the SAME name
# the migration doc is allowed to spell in the four places a leak would
# actually ship — package source, an installable, a workflow, a hook — plus the
# Makefile and three near-miss spellings of the exempt path itself, and assert
# every one of them is still reported. They run `names_a_consumer`, the
# function the repo-wide test runs, so an exemption widened later is caught
# here rather than proven safe against a copy of itself.
# --------------------------------------------------------------------------

# Where a rule-8 leak would reach a consumer. Not an arbitrary list: `src/` is
# the wheel, `installables/` is copied verbatim into consumer repos,
# `.github/workflows/` and `tools/hooks/` are installed and then RUN there.
SHIPPING_PATHS = (
    'src/agentic_sdlc/cli.py',
    'src/agentic_sdlc/repo/installables/gdk_runners.sh',
    'src/agentic_sdlc/repo/installables/ci-verify.yml',
    'tools/hooks/pre-push',
    '.github/workflows/verify.yml',
    'Makefile',
    'devkit.toml',
    'CLAUDE.md',
    'tests/support/__init__.py',
)

# Spellings one character or one directory away from the exempt path. The
# exemption is an `==` on a relative posix path; each of these proves it is not
# quietly a prefix, a basename, a glob or a case-fold.
NEAR_MISSES = ('HANDOFF.md.bak', 'HANDOFF.markdown', 'docs/HANDOFF.md',
               'HANDOFF', 'MY-HANDOFF.md')


def _plant(root: Path, rel: str) -> Path:
    """Write the banned name into `root/rel`, making its parents."""
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f'{PLANT}\n', encoding='utf-8')
    return target


def _exempt_doc(root: Path) -> Path:
    """The migration doc as it really is: the marker AND a banned name."""
    return _plant(root, MIGRATION_DOC)


class TestTheMigrationExemptionOnAScratchTree:

    def test_the_exempt_doc_is_the_only_thing_it_covers(self, tmp_path):
        """The live case, both halves at once: the doc names a consumer and is
        not reported, and the tree it sits in is otherwise clean."""
        _scratch_tree(tmp_path)
        _exempt_doc(tmp_path)
        assert _names_found(tmp_path), (
            'the raw scan no longer sees the planted name — this case would '
            'pass for the wrong reason')
        assert names_a_consumer(tmp_path) == []

    @pytest.mark.parametrize('rel', SHIPPING_PATHS)
    def test_a_leak_in_something_that_ships_is_still_reported(self, tmp_path, rel):
        """The load-bearing property. The exemption exists so a migration
        record can name repos; if it ever covered code, an installable, a
        workflow or a hook, the gate would be off in exactly the places a
        consumer runs this package's bytes."""
        _scratch_tree(tmp_path)
        _exempt_doc(tmp_path)
        _plant(tmp_path, rel)
        hits = names_a_consumer(tmp_path)
        assert any(hit.startswith(f'{rel}:') for hit in hits), (
            f'a consumer name in {rel} was not reported: {hits}')

    @pytest.mark.parametrize('rel', NEAR_MISSES)
    def test_a_path_one_step_from_the_exempt_one_is_still_reported(
            self, tmp_path, rel):
        """`==` on the relative path, proven rather than read. A prefix match
        would exempt `HANDOFF.md.bak`; a basename match would exempt a copy in
        any directory; a glob would exempt both."""
        _scratch_tree(tmp_path)
        _exempt_doc(tmp_path)
        _plant(tmp_path, rel)
        hits = names_a_consumer(tmp_path)
        assert any(hit.startswith(f'{rel}:') for hit in hits), (
            f'{rel} was swept up by the exemption for {MIGRATION_DOC}: {hits}')

    def test_the_exempt_doc_is_still_scanned_for_outside_reads(self, tmp_path):
        """One clause, not two. The second clause is what the deleted smoke
        gate broke, and the migration doc buys no cover from it — which is why
        the real file names the workspace in words instead of as a path."""
        _scratch_tree(tmp_path)
        doc = _exempt_doc(tmp_path)
        assert re.search(OUTSIDE_READS[1], OUTSIDE_PLANT), (
            'the plant no longer matches the pattern it was built from')
        doc.write_text(doc.read_text(encoding='utf-8')
                       + f'reads {OUTSIDE_PLANT}\n', encoding='utf-8')
        hits = [hit for path in scanned_files(tmp_path)
                for hit in offending_lines(path, OUTSIDE_READS, tmp_path)]
        assert any(hit.startswith(f'{MIGRATION_DOC}:') for hit in hits), hits

    def test_the_exemption_is_one_path_not_a_container(self):
        """A str compared with `==`. If this ever becomes a tuple or a set,
        `rel == MIGRATION_DOC` silently stops matching anything and the doc
        reds — but a `in` rewritten alongside it would widen the hole in
        silence, so the shape is pinned here."""
        assert isinstance(MIGRATION_DOC, str)
        for wildcard in ('*', '?', '[', ']', '\\'):
            assert wildcard not in MIGRATION_DOC, MIGRATION_DOC

    def test_an_unreadable_exempt_doc_is_not_a_free_pass(self, tmp_path):
        """The decode failure this gate stopped skipping. A file exempted from
        the name clause is still walked, still classified and still readable —
        the repo-level guard above asserts the real one decodes, and this is
        the shape it guards against."""
        _scratch_tree(tmp_path)
        (tmp_path / MIGRATION_DOC).write_bytes(PLANT.encode() + b'\n\xff\xfe\n')
        hits = offending_lines(tmp_path / MIGRATION_DOC, CONSUMER_NAMES, tmp_path)
        assert _unreadable(hits), hits


# --- the other kit's artifacts ------------------------------------------------

def names_an_engine_artifact(root: Path = REPO_ROOT) -> list[str]:
    """Every `path:line: text` under SHIPPING_ROOTS spelling an engine token."""
    hits: list[str] = []
    for path in scanned_files(root):
        rel = path.relative_to(root).as_posix()
        if not rel.startswith(SHIPPING_ROOTS):
            continue
        if rel in ENGINE_TOMBSTONES:
            continue
        hits.extend(offending_lines(path, ENGINE_ARTIFACTS, root))
    return hits


def test_nothing_that_ships_acts_on_an_engine_artifact():
    """Decision D2, as a gate.

    The middle tier — a gate framework carrying one language's target roster —
    is what blocked splitting this package in two, and it was invisible because
    nothing looked. `Makefile.devkit` named twelve engine targets; `init` refused
    every repo without an engine project file; `install-ci` shipped a workflow
    running `make uid-scan`. Each of those read as normal until somebody asked
    which kit owned it.
    """
    hits = names_an_engine_artifact()
    unreadable = _unreadable(hits)
    assert not unreadable, (
        'files under the shipping roots could not be read:\n'
        + '\n'.join(unreadable))
    assert hits == [], (
        'these ship and act on an engine artifact — they belong to the kit '
        'that owns that artifact (decision D2, 0.2.0):\n' + '\n'.join(hits))


def test_the_engine_scan_covers_the_places_a_leak_would_ship():
    """A scan over an empty census passes vacuously. Rule 4."""
    scanned = [p.relative_to(REPO_ROOT).as_posix() for p in scanned_files()]
    for root in SHIPPING_ROOTS:
        assert any(rel.startswith(root) for rel in scanned), (
            f'{root} contributed no files to the census, so the engine scan '
            f'passed over nothing')


@pytest.mark.parametrize('rel,why', sorted(ENGINE_TOMBSTONES.items()))
def test_every_engine_tombstone_still_earns_its_exemption(rel, why):
    """An exemption that outlives its file is documentation of a lie."""
    path = REPO_ROOT / rel
    assert path.is_file(), f'{rel} is exempt ({why}) and does not exist'
    assert offending_lines(path, ENGINE_ARTIFACTS), (
        f'{rel} is exempt ({why}) and no longer names an engine artifact — '
        f'drop the entry')

