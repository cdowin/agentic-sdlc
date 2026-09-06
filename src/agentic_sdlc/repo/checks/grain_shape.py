"""check grain-shape — grain documents stay inside the caps THIS KIT defines.

This package defines the grain schema, mints every grain from its own
templates, and documents the shape a milestone/feature/story/bug is supposed to
hold. The cap on how long one of those documents may run is therefore this
package's rule — so the gate that measures it belongs here, where every
consumer gets it on a pin bump, rather than in whichever consumer happened to
write the script first.

That is not hypothetical. A prose-cap script enforcing this schema was authored
by a CONSUMER and lives in one game repo; the other consumer does not have it
at all. A rule this package defines was enforced in one tree of two by accident
of where a file was written. And it cost 34.8 s there — half that consumer's
whole gate set — because it spawned four subprocesses per file across 683
markdown files. Here it is one pass, in process: each document is read ONCE,
and the same list of lines answers "is this a grain?" and "how long is it?".

WHAT IS MEASURED — the BODY, not the file. Frontmatter is schema, and
`check pm` already owns every question about it; counting it here would make a
grain's cap depend on how many fields the template mints. Body = the lines
after the closing `---`, with trailing blank lines trimmed, so a file that ends
with a newline does not read one line longer than it looks. A grain whose
frontmatter is DAMAGED (no closing fence — `check pm`'s finding, not this
gate's) has no body boundary to find, so the WHOLE file is measured: the
alternative is measuring 0 and printing PASS over a document nothing else here
can see.

WHAT COUNTS AS WHICH KIND — from `repo/pm/model`'s own names and slots, never a
second spelling of them:

  milestone   `milestone.md`          feature     `feature.md`
  story       under a `stories/`      bug         under a `bugs/` slot
  decisions   `decisions.md`          handoff     `handoff.md`
  note        every other document that carries frontmatter

SCOPE IS WHAT THIS KIT DEFINES. A grain IS its frontmatter, so a `.md` without
one is a note parked beside a grain and is out of scope — disclosed in the
census, never subtracted from it. The two exceptions are the shared docs this
kit MINTS, `decisions.md` and `handoff.md`: neither template opens a
frontmatter block, so a cap on either would be a knob that could never fire,
and `decisions.md` is the one document here that grows for a whole milestone by
design. `review.md` stays out — this kit permits the slot and does not define
its content, and a floor under somebody's review prose is the mistake
`review_min_content_bytes` was retired for. Dot-prefixed paths and the
`zz_archive/` tree are out too, both disclosed.

devkit.toml:

    [grain_shape]
    caps = { story = 300 }   # every kind not named keeps its shipped default

CAPS ARE THE ADOPTION MECHANISM. This gate is in the stock `check all` roster,
so it lands in trees that never had a prose cap — and a gate that cannot fail
is a gate that never gates, which is CLAUDE.md rule 4's cardinal sin shipped on
purpose. So it ENFORCES from day one and a tree that cannot meet a default
raises its own ceiling here, in its own devkit.toml, in a value a reviewer can
see and ratchet down. A repo with no devkit.toml behaves byte-identically to
one declaring the defaults (rule 5): a partial `caps` table is merged OVER the
defaults, so naming one kind never silently un-caps the other five.

WHOSE QUESTION IS "IS THERE A TREE?" — not this gate's. A repo with no PM tree,
and a PM tree with no grain written yet, are both NO-OPS THAT SAY SO. That
looks like rule 4 being softened and it is the opposite: **`check pm` is the
gate that fails a PM tree it cannot find**, and two gates over one directory
must not both answer the same question or a consumer gets two findings for one
fact. This gate owns "are these documents within their caps", and a tree with no
document in it has no answer to give.

The zero census that MUST fail is the one where the scope lost files that are
there — and that is measurable rather than inferred: the walk carries what it
SKIPPED as well as what it kept (`core.walk`), so a roadmap holding markdown
this gate did not measure fails loudly, while a roadmap holding nothing at all
is a fresh `pm init` and is exactly as green as it should be. Measured
2026-09-05: a stock `agentic-sdlc init` writes `ROADMAP.md` and no grain, and
this gate in the default roster failed that project on its first `make check` —
the newest possible consumer, reddened on day one, which is the failure mode the
feature's own risk 2 names.
"""
from __future__ import annotations

from pathlib import Path

from agentic_sdlc.core import walk
from agentic_sdlc.core.config import (ConfigError, config_section, number_table,
                                      relpath)
from agentic_sdlc.core.project import repo_root
from agentic_sdlc.core.walk import Kind, SkipReason, Walk
from agentic_sdlc.repo.pm import model

SECTION = 'grain_shape'
CAPS_KEY = 'caps'

MILESTONE = 'milestone'
FEATURE = 'feature'
STORY = 'story'
BUG = 'bug'
DECISIONS = 'decisions'
HANDOFF = 'handoff'
NOTE = 'note'

# The shared docs this kit MINTS whose templates open no frontmatter block, so
# the grain filter would drop them and their caps could never fire. Asked of
# `model`, so a slot renamed there is renamed here. `REVIEW_FILE_NAME` is
# deliberately absent — see the module docstring.
FRONTMATTERLESS_SLOTS = (model.DECISION_FILE_NAME, model.HANDOFF_FILE_NAME)

# The shipped ceilings, in BODY lines. Set where a grain stops being readable in
# one sitting, not where the template ends — the templates mint 17-30 lines and
# a cap there would refuse every real document this package has ever written.
# Every grain in this package's own tree at 0.2.0 is under these (the longest is
# 157), so the gate ships green on its author and a consumer's number is its own
# to declare. `decisions` runs highest because it is APPEND-ONLY: it grows for
# the whole life of a milestone by design, and capping it like a story would
# punish a tree for recording its reasoning.
DEFAULT_CAPS: dict[str, int] = {
    BUG: 150,
    DECISIONS: 500,
    FEATURE: 200,
    HANDOFF: 120,
    MILESTONE: 200,
    NOTE: 250,
    STORY: 200,
}

# The finding column, wide enough for the longest label.
LABEL_WIDTH = len('UNREADABLE')


def _caps() -> dict[str, int]:
    """The ceiling per kind — defaults, with `[grain_shape] caps` over them.

    Every value crosses `core/config.py` (`number_table` refuses a string, a
    float and a bool — `true` is an `int` in Python and would arrive as 1).
    Three further refusals, all exit 2, because each would otherwise be a knob
    that silently did nothing or the reverse of what it says:

      * a kind this package does not ship — `caps = { storys = 300 }` reads as
        a raised ceiling and raises nothing;
      * a cap below 1 — no document can be shorter than nothing, so every grain
        in the tree becomes a finding;
      * `caps = {}` — an empty table reads as "no caps" and would silently mean
        "all of them", the same reversal `str_tuple` refuses one dimension up.
    """
    sect = config_section(SECTION)
    declared = number_table(sect, SECTION, CAPS_KEY, DEFAULT_CAPS)
    if CAPS_KEY in sect and not declared:
        raise ConfigError(
            f'[{SECTION}] {CAPS_KEY} is empty — remove the key to take the '
            f'shipped caps rather than declaring nothing')
    unknown = sorted(set(declared) - set(DEFAULT_CAPS))
    if unknown:
        raise ConfigError(
            f'[{SECTION}] {CAPS_KEY} names unknown grain kind(s) '
            f'{", ".join(unknown)} — the kinds are '
            f'{" ".join(sorted(DEFAULT_CAPS))}')
    for kind, value in sorted(declared.items()):
        if value < 1:
            raise ConfigError(
                f'[{SECTION}] {CAPS_KEY}.{kind} must be at least 1, got '
                f'{value} — a cap below one line fails every document')
    # MERGED over the defaults, never replacing them: a table naming one kind
    # must not un-cap the other five. This is also what makes a repo with no
    # devkit.toml byte-identical to one declaring the defaults (rule 5).
    return {**DEFAULT_CAPS, **declared}


def _kind_of(rel: Path) -> str:
    """Which kind a grain document is, from `model`'s names and slots."""
    name = rel.name
    if name == model.MILESTONE_DOC:
        return MILESTONE
    if name == model.FEATURE_DOC:
        return FEATURE
    if name == model.DECISION_FILE_NAME:
        return DECISIONS
    if name == model.HANDOFF_FILE_NAME:
        return HANDOFF
    # The slot directories, asked of every component: `slot_walk` is recursive,
    # so `bugs/<topic>/<doc>.md` and `stories/<topic>/<doc>.md` are real shapes
    # and a check of the parent alone would file both under `note`.
    parts = rel.parts[:-1]
    if model.STORIES_DIR in parts:
        return STORY
    if model.BUGS_DIR in parts:
        return BUG
    return NOTE


def _body_lines(lines: list[str]) -> int:
    """Body length in lines: after the closing fence, trailing blanks trimmed.

    `model._fence_bounds` is the STRICT reader — the one `check pm` uses to
    decide whether a frontmatter block is well-formed — and it is asked here
    rather than re-implemented, because a second frontmatter parser is a second
    chance to disagree about where a document's prose starts. It answers None
    for a damaged block, and then the whole file is the body: a grain nothing
    can measure must not measure as zero.
    """
    bounds = model._fence_bounds(lines)
    body = list(lines) if bounds is None else lines[bounds[1] + 1:]
    while body and not body[-1].strip():
        body.pop()
    return len(body)


def _walk(roadmap: Path, lines_of: dict[Path, list[str] | None]) -> Walk:
    """Every grain document under the PM tree, and everything the walk skipped.

    ONE read per file: `lines_of` is filled here, by the frontmatter filter, and
    the measurement below reads it back rather than opening anything twice.
    A file that cannot be read stays IN scope, exactly as `model._is_grain_doc`
    keeps it — "this is not a grain" and "this cannot be opened" are different
    facts, and only the second one is a finding.
    """
    def readable(path: Path) -> list[str] | None:
        if path not in lines_of:
            try:
                lines_of[path] = model._split(model.read_raw(path))
            except (OSError, UnicodeDecodeError):
                lines_of[path] = None
        return lines_of[path]

    def in_scope(path: Path) -> bool:
        # READ FIRST, unconditionally: `run()` reads `lines_of` back for every
        # document the walk kept, and a short-circuit here would leave a shared
        # slot in the census with no entry to measure.
        lines = readable(path)
        if path.name in FRONTMATTERLESS_SLOTS:
            return True
        return True if lines is None else model._opens_frontmatter(lines)

    return (walk.descendants(roadmap, Kind.FILE, suffix='.md')
            .filter(lambda p: not any(part.startswith('.')
                                      for part in p.relative_to(roadmap).parts),
                    SkipReason.DOTTED_NAME)
            .filter(lambda p: model.ARCHIVE_DIR_NAME
                    not in p.relative_to(roadmap).parts,
                    SkipReason.EXCLUDED_PATH)
            .filter(in_scope, SkipReason.NO_FRONTMATTER))


def _measured_line(seen: dict[str, int], caps: dict[str, int]) -> str:
    """`bug 1/150, decisions 1/500, …` — how many of each kind were measured,
    and the cap each was measured AGAINST. Every kind renders, including the
    ones with nothing in them: the cap set in force is part of the verdict, and
    a reader must not have to guess which ceilings were absent versus empty."""
    return ', '.join(f'{kind} {seen.get(kind, 0)}/{caps[kind]}'
                     for kind in sorted(caps))


def run() -> int:
    caps = _caps()
    root = repo_root()
    # WHERE the PM tree is has one name already — `[pm] roadmap_dir`. Read
    # through the same guard rather than given a second spelling here, because
    # a gate looking somewhere else than the tracker does would answer about a
    # directory nobody maintains.
    #
    # `relpath`, not `text`, and it is the SAME call `repo/pm/model.load` makes
    # — this key has two readers and they must not disagree about which trees
    # exist. Until 0.2.0 `text` had no opinion about paths and both of rule 8's
    # halves went through here: `roadmap_dir = "../tmp.XXXX"` printed OVER CAP
    # findings about documents outside the checkout, and the absolute spelling
    # reached `path.relative_to(root)` below and raised an uncaught ValueError
    # at exit 1 — a traceback where rule 6 says exit 2, which a consumer's CI
    # reads as drift found. The refusal is one layer down so it cannot be half
    # applied; what is left here is the reason it is asked for.
    roadmap_dir = relpath(config_section('pm'), 'pm', 'roadmap_dir', 'pm/roadmap')
    roadmap = root / roadmap_dir

    if not roadmap.is_dir():
        # Not every consumer has a PM tree, and this gate is in the stock
        # roster: a FAIL here would red every such repo on the day it upgraded.
        # It says so rather than staying quiet — a gate that prints PASS
        # without saying it measured nothing is the same lie one step down.
        print(f'[check:grain-shape] PASS — no {roadmap_dir}/ in this repo, so '
              f'there are no grain documents to measure')
        return 0

    lines_of: dict[Path, list[str] | None] = {}
    found = _walk(roadmap, lines_of)
    docs = list(found)
    census = found.census(f'PM document(s) under {roadmap_dir}/')
    if not docs:
        # THE CENSUS GOES IN BOTH LINES. It was computed here and dropped from
        # the PASS, so a roadmap holding fourteen markdown files reported
        # "holds no grain document yet" — true about grains, and silent about
        # everything it had just walked past. A verdict that omits what it
        # scanned is the half-truth rule 4 is about.
        #
        # UNEXAMINED, not merely skipped. A file opened and classified as a
        # note IS examined — a fresh `pm init` writes exactly one of those and
        # is honestly empty. A symlinked directory nobody descended, or a path
        # config removed, was never looked at, and a walk that kept nothing
        # while leaving something unlooked-at cannot tell an empty tree from a
        # scope that lost one.
        if found.unexamined():
            print(f'[check:grain-shape] FAIL — {census}, and this kept nothing '
                  f'while leaving {found.unexamined()} entr(ies) unexamined, so '
                  f'it cannot tell an empty tree from a scope that lost one')
            return 1
        print(f'[check:grain-shape] PASS — {census}; {roadmap_dir}/ holds no '
              f'grain document yet, so there is nothing to measure. `check pm` '
              f'is the gate with an opinion about a PM tree being there')
        return 0

    findings: list[tuple[str, str]] = []
    seen: dict[str, int] = {}
    for path in docs:
        rel = path.relative_to(root)
        kind = _kind_of(path.relative_to(roadmap))
        seen[kind] = seen.get(kind, 0) + 1
        lines = lines_of[path]
        if lines is None:
            findings.append((
                'UNREADABLE',
                f'{rel} is a grain document this gate cannot open, so its '
                f'length is unknown — it is counted, never assumed to fit'))
            continue
        length = _body_lines(lines)
        if length > caps[kind]:
            findings.append((
                'OVER CAP',
                f'{rel} — {length} body line(s), {kind} cap {caps[kind]} '
                f'(raise it in [{SECTION}] {CAPS_KEY} or split the document)'))

    scope = f'{census}; measured {_measured_line(seen, caps)}'
    if findings:
        for label, said in findings:
            print(f'  {label:<{LABEL_WIDTH}} {said}')
        print(f'[check:grain-shape] FAIL — {len(findings)} finding(s) across '
              f'{scope}')
        return 1
    print(f'[check:grain-shape] PASS — {scope}')
    return 0
