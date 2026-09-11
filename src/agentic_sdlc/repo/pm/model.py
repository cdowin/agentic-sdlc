"""model.py — the PM-tree invariants, single-sourced for the CLI and the gate.

`[pm]` in devkit.toml, under hard rule 5: every gate key has a stock default,
the flow (`[pm.states.<kind>]`) has none and `pm init` writes it. Every question
is asked of a status's category (`holds`), every move checked by `move_defect`,
and no state word is spelled outside the seed (`tests/test_pm_flow.py`).
"""
from __future__ import annotations

import re
from collections.abc import Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from agentic_sdlc.core import apply, frontmatter, walk
from agentic_sdlc.core.walk import Kind, SkipReason, Walk
from agentic_sdlc.core.project import load_config, repo_root
from agentic_sdlc.core.config import (ConfigError, config_section, number,
                                       relpath, section_declared, flag,
                                       str_tuple, str_tuple_table, table, text)

# --- the flow a project DECLARES ----------------------------------------------
# The closed set, and the engine's whole opinion about states: three categories
# answering "does work remain". `obe` is a `done` state — delivered-vs-not is
# an outcome on a different axis, not a fourth category.
TODO = 'todo'
IN_PROGRESS = 'in_progress'
DONE_CATEGORY = 'done'
CATEGORIES = (TODO, IN_PROGRESS, DONE_CATEGORY)

# THE GRAIN VOCABULARY, SPELLED ONCE — 300 bare literals and five parallel
# declarations before this feature, and a second spelling is what shipped the
# `at`/`ts` defect. `tests/test_pm_flow.py` names every other one with its why.
GRAIN_MILESTONE = 'milestone'
GRAIN_FEATURE = 'feature'
GRAIN_STORY = 'story'
GRAIN_BUG = 'bug'
# Per kind, so a bug's flow is one more declaration rather than a special case.
FLOW_KINDS = (GRAIN_MILESTONE, GRAIN_FEATURE, GRAIN_STORY, GRAIN_BUG)

# THE FRONTMATTER FIELD NAMES this package reads by name. Gated in the
# `field_of` / `field_in` / `set_field` argument, which is where a second
# spelling returns '' rather than failing.
FIELD_ID = 'id'
FIELD_KIND = 'kind'
FIELD_STATUS = 'status'
FIELD_NAME = 'name'
FIELD_OWNER = 'owner'

# The ROOT is a container like any other: `releases.md` declares `id:`/`kind:`
# and holds an `order` of milestone ids. Not a FLOW kind — nothing moves it, so
# it declares no states and has no status.
ROOT_KIND = 'roadmap'
ROOT_ID = 'roadmap'
CONTAINER_KINDS = (ROOT_KIND, *FLOW_KINDS)

# WHICH KINDS MAY HOLD WHICH — one mapping read by `pm add`, instead of a check
# per level. A GATE key (hard rule 5).
DEFAULT_CONTAINS = {'roadmap': (GRAIN_MILESTONE,),
                    GRAIN_MILESTONE: (GRAIN_FEATURE, GRAIN_BUG),
                    GRAIN_FEATURE: (GRAIN_STORY,)}


def contains_defect(mapping: dict[str, tuple[str, ...]]) -> str:
    """Why `[pm.contains]` is not a containment mapping, or ''. It NARROWS:
    `BINDS_TO` says which field a child names its parent with, so a pairing
    there is no field for is a mapping nothing could ever write."""
    for parent, kinds in sorted(mapping.items()):
        if parent not in CONTAINER_KINDS:
            return (f'[pm.contains] declares {parent!r} as a container, which '
                    f'is not a kind this project has — '
                    f'{" ".join(CONTAINER_KINDS)}')
        for kind in kinds:
            if kind not in FLOW_KINDS:
                return (f'[pm.contains] {parent} names {kind!r} as a child, '
                        f'which is not a kind this project has — '
                        f'{" ".join(FLOW_KINDS)}')
            wants, field_name = BINDS_TO.get(kind, (ROOT_KIND, ''))
            if wants != parent:
                return (f'[pm.contains] {parent} names {kind}, and a {kind} '
                        f'names its parent with '
                        + (f'`{field_name}:`, which holds a {wants} id'
                           if field_name else
                           f'no field at all — only the {wants} holds one')
                        + f'. This key narrows the mapping; it cannot '
                          f're-parent a kind')
    return ''


def may_hold(cfg: 'PmConfig', parent_kind: str, kind: str) -> str:
    """'' when a `parent_kind` may hold a `kind`, else why not — naming BOTH.
    Asked of the kinds the two ids DECLARE, so one mapping answers for every
    level and no verb carries a per-level check."""
    allowed = cfg.contains.get(parent_kind, ())
    if kind in allowed:
        return ''
    return (f'a {parent_kind} does not hold a {kind} — [pm.contains] says a '
            f'{parent_kind} holds '
            + (f'{" and ".join(allowed)}' if allowed else 'nothing')
            + f', and the pair is read off the two ids rather than from the '
              f'command')


@dataclass(frozen=True)
class Flow:
    """One grain kind's declared states and their categories, read from
    `[pm.states.<kind>]` every run with no runtime fallback. `order` is
    category-major, then the project's own list order; no gate keys on it."""

    kind: str
    by_category: dict[str, tuple[str, ...]]
    category_of: dict[str, str]

    @property
    def order(self) -> tuple[str, ...]:
        return tuple(st for cat in CATEGORIES
                     for st in self.by_category.get(cat, ()))

    def category(self, status: str) -> str | None:
        """This state's category, or None when it was never declared (D4)."""
        return self.category_of.get(status)


# The seed: what `init` materialises into devkit.toml, not a fallback the
# reader assumes. It is the only place in this package a state word is spelled;
# each kind seeds only the states its belt writes, plus `obe` in `done`
# wherever work can be abandoned. `LIFECYCLE`, `BUILDING` and `REVIEWING`
# survive for the frozen dispatch-snapshot keys in `pm/cli.py` (U1).
LIFECYCLE = ('planning', 'ready', 'building', 'reviewing', 'accepted',
             'packaging', 'done')
BUILDING = LIFECYCLE[2]
REVIEWING = LIFECYCLE[3]
_LIFECYCLE_CATEGORIES = {
    TODO: LIFECYCLE[:2],
    IN_PROGRESS: LIFECYCLE[2:6],
    DONE_CATEGORY: LIFECYCLE[6:] + ('obe',),
}

DEFAULT_FLOWS: dict[str, dict[str, tuple[str, ...]]] = {
    GRAIN_MILESTONE: dict(_LIFECYCLE_CATEGORIES),
    GRAIN_FEATURE: {TODO: LIFECYCLE[:2], IN_PROGRESS: LIFECYCLE[2:4],
                DONE_CATEGORY: LIFECYCLE[6:] + ('obe',)},
    GRAIN_STORY: {TODO: LIFECYCLE[:2], IN_PROGRESS: LIFECYCLE[2:3],
              DONE_CATEGORY: LIFECYCLE[6:] + ('obe',)},
    GRAIN_BUG: {TODO: ('open',), IN_PROGRESS: ('fixed',),
            DONE_CATEGORY: ('closed',)},
}


def render_seed(flows=None) -> str:
    """The seed as the TOML `init` writes — one renderer for the fresh-tree
    and append paths. Live TOML, not commentary: nothing falls back to it."""
    flows = DEFAULT_FLOWS if flows is None else flows
    out: list[str] = []
    for kind in FLOW_KINDS:
        by_category = flows[kind]
        out.append(f'[pm.states.{kind}]')
        for category in CATEGORIES:
            states = by_category.get(category, ())
            rendered = ', '.join(f'"{st}"' for st in states)
            out.append(f'{category:<11} = [{rendered}]')
        out.append('')
    return '\n'.join(out)


def _flow_defect(kind: str, by_category: dict[str, tuple[str, ...]]) -> str:
    """'' when this declaration is readable, else why it is not — a fact about
    the input, exit 2, never a finding."""
    unknown = [c for c in by_category if c not in CATEGORIES]
    if unknown:
        return (f'[pm.states.{kind}] names categor(ies) '
                f'{", ".join(sorted(unknown))} — the set is closed and is '
                f'exactly {" ".join(CATEGORIES)}')
    missing = [c for c in CATEGORIES if not by_category.get(c)]
    if missing:
        return (f'[pm.states.{kind}] declares no state in '
                f'{", ".join(missing)} — every category needs at least one '
                f'state, or a grain can never be in it')
    seen: dict[str, str] = {}
    for category in CATEGORIES:
        for state in by_category.get(category, ()):
            if state in seen:
                return (f'[pm.states.{kind}] maps {state!r} to both '
                        f'{seen[state]!r} and {category!r} — every state maps '
                        f'to exactly one category')
            seen[state] = category
    return ''


# D9/D10 encode branch-per-milestone and are OFF by default; a trunk-shipping
# project is not drifting. D10 is stricter than D9. R5 is off for the same
# reason: a tree with no plan yet has nothing for it to grade.
# D11 replaced D3, STOCK-ON in its place: containment is the tool's mapping.
DEFAULT_CHECKS = ('D1', 'D2', 'D4', 'D5', 'D6', 'D11', 'D12', 'U1',
                  'V1', 'V4', 'V5', 'V7')
# The USAGE family: what the tree DOES with the vocabulary (U1) and the
# capabilities (U2) it declared, as opposed to whether a word is declared at
# all (D4). A NEW LETTER on purpose — see RETIRED_CHECKS['D7'] below. Both are
# STOCK-ON: an opt-in rule nobody enables answers "is this flow being used"
# with silence, which is the failure they were filed to end, and a WARN cannot
# redden anyone; a tree that wires nothing stays quiet either way (0.4.0/D5).
# U5 (0.5.0) is the same question asked of the EDGE: a grain whose current
# state was arrived at with no disposition. A bare move records `answer: none`
# and is never refused (D3), so the rule names what nobody answered.
USAGE_CHECKS = ('U1', 'U2', 'U3', 'U4', 'U5')  # named for the family
# D9/D10 read an `in_progress` milestone's `branch:`; D8 read its id as the
# version and RETIRED into R5, which grades against a position in `order`.
FLOW_CHECKS = ('D9', 'D10')
# The release family: the plan and the tree held to each other. Opt-in.
RELEASE_CHECKS = ('R1', 'R2', 'R3', 'R4', 'R5', 'R6')
# V1, V4, V5 and V7 are ON: an unsatisfied one is a malformed tree. V2, V3 and
# V6 RETIRED in 0.4.0 — each kept two copies of one fact in agreement, and
# RETIRED_CHECKS below says which copy went. What can still be wrong is a
# document nothing can key on (`unkeyed_documents`) and a binding naming no
# grain (V7, which walks the POOLS rather than descending).
VALIDATE_CHECKS = ('V1', 'V4', 'V5', 'V7')
KNOWN_CHECKS = tuple(dict.fromkeys(
    DEFAULT_CHECKS + USAGE_CHECKS + FLOW_CHECKS + RELEASE_CHECKS
    + VALIDATE_CHECKS))

# A rule id that WAS shipped and is not any more. Reported by name, never as
# "unknown": a consumer whose config still lists it is told where the rule
# went, rather than being silently ungated by a typo-shaped message.
RETIRED_CHECKS = {
    'V2': 'retired in 0.4.0 — it kept `id:` in agreement with the path, and a '
          'path is no longer part of a grain\'s identity. `id:` IS the '
          'identity; a document with none is reported by name',
    'V3': 'retired in 0.4.0 — it kept `milestone:`/`feature:` in agreement '
          'with the directory a document sat in, and membership is now the '
          'field itself. A binding naming a grain that is not in the tree is '
          'still a finding',
    'V6': 'retired in 0.4.0 with the generated execution list it graded. A '
          'rendered roster of a parent\'s children was a second scoreboard, '
          'and keeping it in agreement with the tree was V2\'s defect one '
          'level down. The SEQUENCE it carried is now `order:` on the parent '
          'itself, written by `pm add` and read by `pm status` and '
          '`pm roadmap`; `check pm` counts what is unsequenced and names what '
          'dangles',
    'D7': 'was retired before 0.3.0 and did not come back. U1 is the '
          'declared-but-unused state rule and it took a NEW letter precisely '
          'so that a config still naming D7 is told it is gone rather than '
          'silently given a different rule',
    'D3': 'became D11 in 0.6.0, which asks the same question at EVERY level '
          'off `BINDS_TO` — milestone/feature, milestone/bug and '
          'feature/story — and FAILS rather than warning. D3 warned about one '
          'pair, so a milestone could close over an open bug and print PASS. '
          'Containment is unconditional: the opt-out is `pm remove <parent> '
          '<child>`, which returns the child to its pool',
    'D8': 'became R5 — the version file is graded against the CURRENT entry in '
          'pm/roadmap/releases.md `order` ([pm] version_at selects which), not '
          'against the id of whichever milestone happens to be in progress. '
          'D8 welded the version to the id; `version:` separates them',
}

# RETIRED_CHECKS' frontmatter sibling, named where it survives.
RETIRED_FIELDS = {
    'fix_milestone': 'retired in 0.6.0. It was a second binding that nothing '
                     'wrote, so the release gate filtered on it and matched '
                     'nothing for four releases. `milestone:` is the parent '
                     'and the only one; `pm remove <milestone> <bug>` is the '
                     'opt-out',
    'caught_in': 'retired in 0.6.0. `pm new bug` stamped its argument into '
                 'this AND `milestone:`, one value in two fields with '
                 'different meanings. Where a bug was found is history, and '
                 '`git log` holds it',
}

ARCHIVE_DIR_NAME = 'zz_archive'

# U2's two halves, both readable without running anything. The settings file is
# the consumer's own and hand-maintained (`install.py` says why it is printed
# and never written); these are the script names that block wires.
AGENT_SETTINGS = '.claude/settings.json'
LEDGER_COURIERS = ('cc-ledger-session.sh', 'cc-ledger-subagent.sh')

# --- the canonical grain slots ------------------------------------------------
# One shape, every grain, all lowercase. `handoff.md` and `bugs/` are
# milestone-only; every shared doc is optional and minted on first write; there
# are no directory slots, since git stores no empty directory.
DECISION_FILE_NAME = 'decisions.md'
REVIEW_FILE_NAME = 'review.md'
HANDOFF_FILE_NAME = 'handoff.md'
# The plan: `order` is a declared sequence of versions, not a sort. It lives in
# the roadmap dir beside the milestones it sequences, and it is grain-shaped so
# the byte-preserving frontmatter writer can edit it.
RELEASES_DOC = 'releases.md'
ORDER_KEY = 'order'

# R5: which entry in `order` the version file must match. `start` is
# bump-at-START (the first entry not yet shipped) and the seed default;
# `ship` is bump-at-CLOSE (the last entry that has).
VERSION_AT_START = 'start'
VERSION_AT_SHIP = 'ship'
VERSION_AT_CHOICES = (VERSION_AT_START, VERSION_AT_SHIP)

MILESTONE_DOC = 'milestone.md'
FEATURE_DOC = 'feature.md'
# The slot directories: a grain's kind is read from the slot it sits in.
FEATURES_DIR = 'features'
STORIES_DIR = 'stories'
BUGS_DIR = 'bugs'

# An optional slot is minted on first write, and an absent one recorded
# nothing, which is not a finding. A grain MUST carry only its own document.
MILESTONE_FILE_SLOTS = (MILESTONE_DOC,)
MILESTONE_OPTIONAL_SLOTS = (HANDOFF_FILE_NAME, DECISION_FILE_NAME,
                            REVIEW_FILE_NAME)
FEATURE_FILE_SLOTS = (FEATURE_DOC,)
# No handoff.md: a feature is never picked up cold on its own.
FEATURE_OPTIONAL_SLOTS = (DECISION_FILE_NAME, REVIEW_FILE_NAME)

SLOT_TEMPLATE = {
    MILESTONE_DOC: GRAIN_MILESTONE, FEATURE_DOC: GRAIN_FEATURE,
    'handoff.md': 'handoff', 'decisions.md': 'decisions',
}

# The instruction line each shared doc opens with, restored by `pm new`: a
# file's own first line is the one channel that reaches a dispatched subagent.
SLOT_HEADER = {
    'decisions.md': 'Append with `agentic-sdlc pm decide <grain-id>` — never by '
                    'hand; the command stamps the date and the next ordinal.',
    'handoff.md': 'Cold-start only. Everything derivable is a command — never '
                  'restate `pm status`, `git log` or `pm ledger report`.',
}

# Wordings that shipped before and still open real documents. RECOGNISED, never
# written: `_header_wanted` treats any known header as present, so rewording an
# entry above can neither stack a second line onto an existing doc nor red a
# consumer's tree on upgrade day.
RETIRED_SLOT_HEADERS = frozenset({
    'Cold-start only. Never restate what `pm status` computes.',
})

KNOWN_SLOT_HEADERS = frozenset(SLOT_HEADER.values()) | RETIRED_SLOT_HEADERS


def dir_entries(path: Path) -> dict[str, str]:
    """{exact name: 'file'|'dir'} for one directory, through `core.walk`."""
    return walk.entries(path)


def case_variants(entries: dict[str, str], name: str) -> list[str]:
    """Names in `entries` that differ from `name` only by case (excluding it)."""
    low = name.lower()
    return sorted(n for n in entries if n != name and n.lower() == low)


@dataclass(frozen=True)
class PmConfig:
    root: Path
    roadmap_dir: str = 'pm/roadmap'
    # THE POOLS — one directory per kind, the tables of the database.
    # Empty means "derive `<roadmap_dir>/<kind>s`", so adopting costs zero
    # edits. Four keys rather than one folded into `roadmap_dir`, because **the
    # shape of the config is the shape of the model**: this block says there are
    # four kinds and that they are peers, which one root never could.
    milestone_dir_key: str = ''
    feature_dir_key: str = ''
    story_dir_key: str = ''
    bug_dir_key: str = ''
    # The ledgers are a table too (`ledger.LEDGERS_POOL`).
    ledger_dir_key: str = ''
    review_dir: str = 'docs/reviews'
    contains: dict[str, tuple[str, ...]] = field(
        default_factory=lambda: dict(DEFAULT_CONTAINS))
    # Stock ON: a breadcrumb nobody sees teaches nobody, and the failure it
    # exists to prevent is a move nobody followed up on. Off in one line for a
    # consumer parsing `pm` output strictly (rule 6).
    breadcrumbs: bool = True
    # Stock ON, and OFF in one line for a consumer parsing `pm` output strictly
    # (rule 6). It silences the FORK and the CENSUS a write reports — never the
    # disposition row, which is a fact the tree records about itself whether or
    # not anybody is reading the stream.
    pressure: bool = True
    # THE PROJECT'S OWN NUMBER, never this package's: 0 is "declared nothing",
    # and there is no stock ceiling on how much work somebody may have open.
    # Reported when exceeded and NEVER a refusal — `--force` is the deviation,
    # and this is not even a gate (rule 9).
    wip: int = 0
    # The declared order per kind, copied out by `load`; empty when the tree
    # declared nothing, which `flow_of` refuses.
    milestone_states: tuple[str, ...] = ()
    feature_states: tuple[str, ...] = ()
    story_states: tuple[str, ...] = ()
    bug_states: tuple[str, ...] = ()
    checks: tuple[str, ...] = DEFAULT_CHECKS
    # R5 and `version-sync`: where the shipped version lives, and the line
    # that carries it.
    template_dir: str = ''
    version_file: str = 'pyproject.toml'
    version_pattern: str = r'^version = "(.*)"$'
    # R5 only, and never a parse — a position in `order` (VERSION_AT_*).
    version_at: str = VERSION_AT_START
    # What the project declared, per kind; empty is the absence itself, which
    # `flow_of` turns into a refusal naming the fix (hard rule 5).
    flows: dict[str, Flow] = field(default_factory=dict)
    # `[pm.arrive.<kind>.<state>]`, keyed by the pair it is declared under.
    # Empty is NOT an absence to refuse: a move with no declared action prints
    # no question (0.5.0/D3).
    arrivals: dict[tuple[str, str], 'Arrival'] = field(default_factory=dict)

    @property
    def roadmap(self) -> Path:
        return self.root / self.roadmap_dir

    def rel(self, path: Path) -> str:
        """Repo-relative display path (findings name a path a human can open)."""
        try:
            return str(path.relative_to(self.root))
        except ValueError:
            return str(path)


def load() -> PmConfig:
    """Build the config from `[pm]` in devkit.toml, defaults where unset."""
    sect = config_section('pm')

    def tup(key: str, fallback: tuple[str, ...]) -> tuple[str, ...]:
        out = str_tuple(sect, 'pm', key, fallback)
        if not out:
            raise ConfigError(
                f'[pm] {key} is empty — remove the key to take the default '
                f'({" ".join(fallback)}) rather than declaring nothing')
        return out

    checks = tup('checks', DEFAULT_CHECKS)

    # A retired vocabulary key is refused at load, not left to
    # `config_complaints`: it is a second declaration of the words.
    for key in VOCABULARY_KEYS:
        if key in sect:
            raise ConfigError(f'[pm] {key} was retired and is refused — '
                              f'{RETIRED_KEYS[key]}. Remove the key.')

    # Compile here, not at use: an invalid regex is a config error (exit 2),
    # never a finding.
    version_pattern = text(sect, 'pm', 'version_pattern',
                           r'^version = "(.*)"$')
    try:
        compiled = re.compile(version_pattern)
    except re.error as err:
        raise ConfigError(f'[pm] version_pattern is not a valid regex: {err}') from err
    if compiled.groups < 1:
        raise ConfigError('[pm] version_pattern needs one capture group around '
                          'the version itself')

    # `[pm.scaffold.*]` was retired by template files; a key that silently does
    # nothing is worse than one that errors.
    if 'scaffold' in sect:
        raise ConfigError(
            '[pm.scaffold.*] was replaced by template FILES — set [pm] '
            'template_dir and run `pm templates` to copy them out, then edit '
            'the markdown (a template can change a grain\'s whole shape, not '
            'just its frontmatter defaults)')

    # A position, not a parse. An unknown value is exit 2 rather than a
    # silent fallback to `start`, which would grade against the wrong entry.
    version_at = text(sect, 'pm', 'version_at', VERSION_AT_START)
    if version_at not in VERSION_AT_CHOICES:
        raise ConfigError(
            f'[pm] version_at must be one of '
            f'{" ".join(VERSION_AT_CHOICES)}, got {version_at!r} — '
            f'{VERSION_AT_START!r} is the first entry in `order` that has not '
            f'shipped (bump at start), {VERSION_AT_SHIP!r} the last that has')

    contains = str_tuple_table(sect, 'pm', 'contains', DEFAULT_CONTAINS)
    defect = contains_defect(contains)
    if defect:
        raise ConfigError(defect)

    flows = _load_flows(sect)
    arrivals = _load_arrivals(sect, flows)

    return PmConfig(
        root=repo_root(),
        # `relpath`, not `text`: an absolute or `../` value would move the
        # whole PM surface outside the checkout (hard rule 8).
        roadmap_dir=relpath(sect, 'pm', 'roadmap_dir', 'pm/roadmap'),
        review_dir=relpath(sect, 'pm', 'review_dir', 'docs/reviews'),
        contains=contains,
        milestone_dir_key=relpath(sect, 'pm', 'milestone_dir', ''),
        feature_dir_key=relpath(sect, 'pm', 'feature_dir', ''),
        story_dir_key=relpath(sect, 'pm', 'story_dir', ''),
        bug_dir_key=relpath(sect, 'pm', 'bug_dir', ''),
        ledger_dir_key=relpath(sect, 'pm', 'ledger_dir', ''),
        breadcrumbs=flag(sect, 'pm', 'breadcrumbs', True),
        pressure=flag(sect, 'pm', 'pressure', True),
        wip=number(sect, 'pm', 'wip', 0),
        milestone_states=_order_of(flows, GRAIN_MILESTONE),
        feature_states=_order_of(flows, GRAIN_FEATURE),
        story_states=_order_of(flows, GRAIN_STORY),
        bug_states=_order_of(flows, GRAIN_BUG),
        checks=checks,
        template_dir=relpath(sect, 'pm', 'template_dir', ''),
        version_file=text(sect, 'pm', 'version_file', 'pyproject.toml'),
        version_pattern=version_pattern,
        version_at=version_at,
        flows=flows,
        arrivals=arrivals,
    )


def reload() -> PmConfig:
    """`load()` against the file as it is NOW, caches dropped.

    For the one caller that WROTE devkit.toml in this process and then reads
    it back: `pm init`. The cache lives in `core.project`, and this module is
    the one place in `repo/` that may reach it — every other reader goes
    through the guards in `core/config.py`.
    """
    repo_root.cache_clear()
    load_config.cache_clear()
    return load()


def _order_of(flows: dict[str, Flow], kind: str) -> tuple[str, ...]:
    """The declared order for `kind`, or () when the tree declared nothing."""
    flow = flows.get(kind)
    return flow.order if flow is not None else ()


# `[pm.transitions.<kind>]` is retired and refused by name rather than ignored.
TRANSITIONS_KEY = 'transitions'


def _load_flows(sect: dict) -> dict[str, Flow]:
    """`[pm.states.<kind>]`, read and validated. Absent is an empty dict,
    never the seed; malformed is exit 2 before anything else happens."""
    if TRANSITIONS_KEY in sect:
        kinds = sect[TRANSITIONS_KEY]
        named = (', '.join(f'[pm.{TRANSITIONS_KEY}.{k}]' for k in kinds)
                 if isinstance(kinds, dict) and kinds
                 else f'[pm.{TRANSITIONS_KEY}]')
        raise ConfigError(
            f'{named} was retired and is refused — there is no step-to-state '
            f'table: a belt writes the FIRST state of its kind\'s '
            f'[pm.states.<kind>] done list, and `pm <kind> <state>` reaches '
            f'any declared state directly. Remove the table.')
    states = sect.get('states')
    if states is None:
        return {}
    if not isinstance(states, dict):
        raise ConfigError(f'[pm.states] must be a table of grain kinds, got '
                          f'{states!r}')

    unknown = sorted(set(states) - set(FLOW_KINDS))
    if unknown:
        raise ConfigError(
            f'[pm.states] names grain kind(s) {", ".join(unknown)} — this '
            f'package knows {" ".join(FLOW_KINDS)}, and a flow for a kind it '
            f'never walks would never be read')

    out: dict[str, Flow] = {}
    for kind in FLOW_KINDS:
        if kind not in states:
            continue
        by_category = str_tuple_table(states, 'pm.states', kind, {})
        defect = _flow_defect(kind, by_category)
        if defect:
            raise ConfigError(defect)
        category_of = {st: cat for cat, sts in by_category.items()
                       for st in sts}
        out[kind] = Flow(kind=kind, by_category=by_category,
                         category_of=category_of)
    missing = [k for k in FLOW_KINDS if k not in out]
    if missing:
        raise ConfigError(
            f'[pm.states] declares {", ".join(sorted(out))} and not '
            f'{", ".join(missing)} — a partial flow is worse than none, '
            f'because the kinds it omits fall back to words the project '
            f'never chose. Run `agentic-sdlc pm init` to write the rest.')
    return out


# --- [pm.arrive.<kind>.<state>] — what ARRIVING at a state ASKS (0.5.0/D3) ----
# THERE IS ONE EVENT IN THIS SYSTEM AND IT IS ARRIVAL: a grain reaches a state.
# `[pm.states.<kind>]` declares the NODES; this declares the ACTION tied to one.
#
# It is NOT a transition table and it can never become one: the unit is the
# state ARRIVED AT, never the pair `(from, to)`. A second pass through a state
# asks the same question — which is correct, because it is the question, and
# the answer genuinely may have changed — and backwards costs nothing to
# support because it was never a special case. Rule 9 already says the tool has
# no opinion about which state may follow which; making arrival the unit means
# it never needs one.
#
# A WORKFLOW key (hard rule 5): nothing is behind it, and each half refuses BY
# NAME when its partner is absent — a question with no answers typed is advice,
# and rule 9 forbids the tool having one.
ARRIVE_KEY = 'arrive'
ASK_KEY = 'ask'
ANSWERS_KEY = 'answers'
HAVE_KEY = 'have'
ARRIVE_NODE_KEYS = (ASK_KEY, ANSWERS_KEY, HAVE_KEY)
# Every declared answer opens with a FLAG. Refused by name when it does not, so
# that the word a row uses for "nobody answered" can never collide with an
# answer somebody declared.
ANSWER_PREFIX = '--'


@dataclass(frozen=True)
class Arrival:
    """One `[pm.arrive.<kind>.<state>]` node — the question arriving at this
    state asks, both answers already typed, and the capabilities that apply.

    `have` is a CENSUS and `ask`/`answers` are a FORK; they are separate keys
    because they are separate claims. Nothing here is ordered against anything
    else, because there is no edge.
    """

    kind: str
    state: str
    ask: str = ''
    answers: tuple[str, ...] = ()
    have: tuple[tuple[str, str], ...] = ()

    @property
    def flags(self) -> tuple[str, ...]:
        """The distinct flag each declared answer opens with, in order."""
        return tuple(dict.fromkeys(a.split()[0] for a in self.answers))

    def carries_value(self, name: str) -> bool:
        """Does EVERY answer opening with `name` spell something after it?

        So a bare `--by` refuses when the project declared `--by me`, and a
        one-word answer stays complete on its own. Asked of the DECLARATION,
        never of a flag's spelling.
        """
        spellings = [a.split() for a in self.answers if a.split()[0] == name]
        return bool(spellings) and all(len(s) > 1 for s in spellings)


def _arrive_node_defect(kind: str, state: str, node: object) -> str:
    """'' when one `[pm.arrive.<kind>.<state>]` node is readable, else why not
    — a fact about the input, exit 2, never a finding."""
    where = f'[pm.{ARRIVE_KEY}.{kind}.{state}]'
    if not isinstance(node, dict):
        return f'{where} must be a table, got {node!r}'
    unknown = sorted(k for k in node if k not in ARRIVE_NODE_KEYS)
    if unknown:
        return (f'{where} names {", ".join(unknown)} — the keys an arrival '
                f'declares are {" ".join(ARRIVE_NODE_KEYS)}')
    ask = node.get(ASK_KEY)
    answers = node.get(ANSWERS_KEY)
    if ask is not None and not isinstance(ask, str):
        return f'{where} {ASK_KEY} must be a string, got {ask!r}'
    if ask is not None and not ask.strip():
        return (f'{where} {ASK_KEY} is empty — remove the key rather than '
                f'declaring a question with no words in it')
    if (ask is None) != (answers is None):
        missing, present = ((ANSWERS_KEY, ASK_KEY) if answers is None
                            else (ASK_KEY, ANSWERS_KEY))
        return (f'{where} declares {present} and not {missing} — a question '
                f'with no answers typed is advice, and both answers spelled '
                f'with no question is a list nobody asked for. Declare both, '
                f'or neither.')
    if answers is not None:
        if (not isinstance(answers, list) or not answers
                or not all(isinstance(a, str) for a in answers)):
            return (f'{where} {ANSWERS_KEY} must be a non-empty list of '
                    f'strings, got {answers!r}')
        for answer in answers:
            if not answer.split() or not answer.startswith(ANSWER_PREFIX):
                return (f'{where} {ANSWERS_KEY} names {answer!r}, which does '
                        f'not open with {ANSWER_PREFIX!r} — an answer is a '
                        f'flag the move accepts, and one that is not is a '
                        f'sentence nobody can paste')
    have = node.get(HAVE_KEY)
    if have is not None:
        if not isinstance(have, dict) or not have:
            return (f'{where} {HAVE_KEY} must be a non-empty table of '
                    f'path = "why", got {have!r}')
        for path, why in have.items():
            if not isinstance(why, str) or not why.strip():
                return (f'{where} {HAVE_KEY}.{path} must say what the '
                        f'capability is for, got {why!r} — a path with no '
                        f'sentence beside it is a line nobody can act on')
            if not path or pointer_escapes(path):
                return (f'{where} {HAVE_KEY} names {path!r}, which is not a '
                        f'path inside this checkout — this package reads no '
                        f'path outside its own tree (hard rule 8)')
    return ''


def _load_arrivals(sect: dict,
                   flows: dict[str, Flow]) -> dict[tuple[str, str], Arrival]:
    """`[pm.arrive.<kind>.<state>]`, read and validated against the flow.

    Absent is an empty mapping and NOT a refusal: a tree that declared no
    arrival action still moves, and a move with no fork prints no question. A
    node naming a state `[pm.states.<kind>]` never declared IS a refusal, by
    name — it is the same drift D4 reports one level down, and a question
    nothing can reach would be silent forever.
    """
    raw = sect.get(ARRIVE_KEY)
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ConfigError(f'[pm.{ARRIVE_KEY}] must be a table of grain kinds, '
                          f'got {raw!r}')
    unknown = sorted(set(raw) - set(FLOW_KINDS))
    if unknown:
        raise ConfigError(
            f'[pm.{ARRIVE_KEY}] names grain kind(s) {", ".join(unknown)} — '
            f'this package knows {" ".join(FLOW_KINDS)}, and an arrival at a '
            f'kind it never walks would never be read')
    out: dict[tuple[str, str], Arrival] = {}
    for kind in FLOW_KINDS:
        if kind not in raw:
            continue
        states = raw[kind]
        if not isinstance(states, dict):
            raise ConfigError(f'[pm.{ARRIVE_KEY}.{kind}] must be a table of '
                              f'states, got {states!r}')
        flow = flows.get(kind)
        if flow is None:
            raise ConfigError(
                f'[pm.{ARRIVE_KEY}.{kind}] declares what arriving asks, and '
                f'[pm.states.{kind}] declares no states for it to arrive at — '
                f'run `agentic-sdlc pm init` to write the flow first')
        for state, node in states.items():
            if flow.category(state) is None:
                raise ConfigError(
                    f'[pm.{ARRIVE_KEY}.{kind}.{state}] names a state '
                    f'[pm.states.{kind}] does not declare — the words this '
                    f'project chose are {" ".join(flow.order)}, and a '
                    f'question nothing can reach is one nobody is ever asked')
            defect = _arrive_node_defect(kind, state, node)
            if defect:
                raise ConfigError(defect)
            ask = text(node, f'pm.{ARRIVE_KEY}.{kind}.{state}', ASK_KEY, '')
            answers = (str_tuple(node, f'pm.{ARRIVE_KEY}.{kind}.{state}',
                                 ANSWERS_KEY, ())
                       if ANSWERS_KEY in node else ())
            have = tuple((path, why) for path, why
                         in table(node, f'pm.{ARRIVE_KEY}.{kind}.{state}',
                                  HAVE_KEY, {}).items())
            out[(kind, state)] = Arrival(kind=kind, state=state, ask=ask,
                                         answers=answers, have=have)
    return out


def arrival_at(cfg: PmConfig, kind: str, state: str) -> Arrival | None:
    """What this project declared for arriving at one state, or None.

    None is the common answer and it is not a finding: a move with no declared
    action prints no question, which is the difference between this and a nag.
    """
    return cfg.arrivals.get((kind, state))


# --- the engine's two verbs ---------------------------------------------------
# `move` (is the target a declared state?) and `holds` (are they all in the
# category, and who is not?). Functions rather than a convention because two
# call sites of one convention once disagreed about whether an `obe` story was
# finished (D6).


@dataclass(frozen=True)
class Held:
    """`holds`' answer: are they all there, and who is not."""

    category: str
    blockers: tuple[tuple[str, str], ...]
    """(id, the status the file ACTUALLY holds), for everything not there."""
    counted: int

    def __bool__(self) -> bool:
        return not self.blockers

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(f'{gid} is {status}' for gid, status in self.blockers)


def category_of(cfg: PmConfig, kind: str, status: str) -> str | None:
    """This status's category under the project's declaration, or None when
    the word was never declared (D4's drift) — never a guess.
    """
    return flow_of(cfg, kind).category(status)


def holds(cfg: PmConfig, kind: str, grains, category: str) -> Held:
    """Are all these `(id, status)` grains in `category`, and which are not?
    The caller supplies the pairs, because scope is the caller's question. An
    undeclared status is a blocker carrying the word, never a silent pass
    (rule 4)."""
    if category not in CATEGORIES:
        raise ConfigError(
            f'{category!r} is not a category — the set is closed and is '
            f'exactly {" ".join(CATEGORIES)}')
    flow = flow_of(cfg, kind)
    pairs = [(gid, status) for gid, status in grains]
    blockers = [(gid, status) for gid, status in pairs
                if flow.category(status) != category]
    # The census travels with the answer (rule 4): an empty set and a satisfied
    # set must not print the same sentence.
    return Held(category=category, blockers=tuple(blockers),
                counted=len(pairs))


def move_defect(cfg: PmConfig, kind: str, to_state: str) -> str:
    """'' when this grain kind may be moved to `to_state`, else why not. The
    whole opinion is "is the target declared?" — no edge graph, since a `sed`
    reaches any state anyway and D3/D4/D5 check the end state."""
    flow = flow_of(cfg, kind)
    if to_state in flow.category_of:
        return ''
    return (f'{to_state!r} is not a {kind} state — this project declares '
            f'{", ".join(flow.order)} in [pm.states.{kind}]')


# The workflow refusal, in one place; the gates never come through here (hard
# rule 5).
def flow_of(cfg: PmConfig, kind: str) -> Flow:
    """This grain kind's declared flow, or exit 2 naming the command that
    writes it — a command copies correctly where forty lines of TOML do not."""
    flow = cfg.flows.get(kind)
    if flow is None:
        raise ConfigError(
            f'this tree declares no flow: [pm.states.{kind}] is not in '
            f'devkit.toml, and there is no default — the states are how '
            f'THIS project works, so the engine reads them and never '
            f'assumes them (CLAUDE.md hard rule 5). Run '
            f'`agentic-sdlc pm init` to write them; it appends to a '
            f'devkit.toml it did not create and rewrites nothing.')
    return flow


# `[pm]` keys this package used to honour, named so they error rather than
# silently do nothing.
RETIRED_KEYS = {
    'place_branch_on_building':
        '`pm milestone building` no longer runs `git checkout` in your trunk '
        'worktree — a PM tracker does not move your VCS checkout',
    'trunk_branches': 'read only by the retired branch-placement flow — the '
                      'id D10 was later reused for a different rule (branch '
                      'discipline: a building milestone off the mainline)',
    'bug_open_states': 'read only by the retired D14; [pm.states.bug] still '
                       'gates a bug\'s status through D4',
    'milestone_transitions': 'there is no edge graph and no step-to-state '
                             'table — a belt writes the first state of '
                             '[pm.states.milestone] done',
    'feature_transitions': 'there is no edge graph and no step-to-state '
                           'table — a belt writes the first state of '
                           '[pm.states.feature] done',
    'story_transitions': 'there is no edge graph and no step-to-state table '
                         '— a belt writes the first state of '
                         '[pm.states.story] done',
    # The vocabulary is declared once; a flat list beside `[pm.states.<kind>]`
    # would be a second declaration to reconcile.
    'milestone_states': 'the vocabulary is [pm.states.milestone], with each '
                        'word in its category — run `pm init` to write it',
    'feature_states': 'the vocabulary is [pm.states.feature], with each word '
                      'in its category — run `pm init` to write it',
    'story_states': 'the vocabulary is [pm.states.story], with each word in '
                    'its category — run `pm init` to write it',
    'bug_states': 'the vocabulary is [pm.states.bug], with each word in its '
                  'category — run `pm init` to write it',
    'also_done': 'the `done` category is [pm.states.<kind>] done = [...] — '
                 'list `obe` (or any word for abandoned work) there',
    'story_ordinal_prefix':
        'a story\'s FILE name is not its identity — `id:` is, and the file may '
        'be called anything. What the `NN-` prefix was sequencing is now the '
        'feature\'s own `order:` list, written by `agentic-sdlc pm add '
        '<feature-id> <story-id> [--position N | --before <id> | --after <id>]`',
    'review_slug_fallback': 'a review record is the `reviewed:` pointer and '
                            'nothing else — a record found by glob was the '
                            'engine guessing which file a review was',
}

# The retired keys that declared words; `load()` refuses these outright.
VOCABULARY_KEYS = ('milestone_states', 'feature_states', 'story_states',
                   'bug_states', 'also_done')

_RETIRED_KEYS_REST = {
    # The close ceremony stopped judging content; each of these is read by
    # nothing and would otherwise pass silently.
    'review_min_content_bytes':
        'a review record is a pointer that RESOLVES — the byte floor refused an '
        'honest 15-byte "LGTM. Ship it.", which is the tool judging whether your '
        'prose was long enough. D1 checks the pointer',
    'prose_grandfather': 'read only by the retired prose ratchet (D17/D18)',
    'changelog_grandfather': 'read only by the retired prose ratchet (D17/D18)',
    'decision_grandfather': 'read only by the retired prose ratchet (D17/D18)',
    'story_lines_max': 'the six line caps went with the prose ratchet — this '
                       'package does not manage the length of your markdown',
    'feature_lines_max': 'the six line caps went with the prose ratchet — this '
                         'package does not manage the length of your markdown',
    'bug_lines_max': 'the six line caps went with the prose ratchet — this '
                     'package does not manage the length of your markdown',
    'decisions_lines_max': 'the six line caps went with the prose ratchet — this '
                           'package does not manage the length of your markdown',
    'changelog_lines_max': 'the six line caps went with the prose ratchet — this '
                           'package does not manage the length of your markdown',
    'closed_log_lines_max': 'the six line caps went with the prose ratchet — this '
                            'package does not manage the length of your markdown',
}
RETIRED_KEYS.update(_RETIRED_KEYS_REST)

# Whole sections a release retired; a section is exactly as silent as a key.
RETIRED_SECTIONS = {
    'agents': '`check agents` is removed — A1/A2/A4 failed a build because a '
              'markdown file DESCRIBED a workflow, inferring a line\'s subject '
              'from "one grain word appears". The flat-skill rule it also held '
              'survives in `check doc`',
}


def missing_flow_defect(sect: dict | None = None) -> str:
    """The one defect that stops every work-moving verb, or ''.

    Read straight off `[pm.states.*]` rather than off a loaded config: a config
    that failed to load for some OTHER reason must still report this one, and
    that ordering is the whole feature.
    """
    section = config_section('pm') if sect is None else sect
    states = section.get('states')
    declared = [k for k in FLOW_KINDS
                if isinstance(states, dict) and k in states]
    if len(declared) == len(FLOW_KINDS):
        return ''
    absent = [k for k in FLOW_KINDS if k not in declared]
    return (f'this tree declares no flow: '
            f'{", ".join(f"[pm.states.{k}]" for k in absent)} '
            f'{"is" if len(absent) == 1 else "are"} not in devkit.toml, and '
            f'there is no default — the states are how THIS project works, so '
            f'the engine reads them and never assumes them (CLAUDE.md hard '
            f'rule 5). Run `agentic-sdlc pm init` to write them; it appends to '
            f'a devkit.toml it did not create and rewrites nothing.')


def all_config_defects(sect: dict | None = None) -> list[str]:
    """EVERY defect in `[pm]`, flow first — not the first one encountered.

    A real adoption is wrong in more than one way at once, and one defect per
    run makes the consumer pay a round trip to learn the next. The ORDER is the
    point: a retired key is cosmetic, a missing flow stops every work-moving
    verb, and the tree that motivated this was told about the retired key. Each
    reader is asked SEPARATELY and its refusal collected, so one `load()`
    defect cannot hide the retired-key sweep behind it (review D2, D3).
    """
    section = config_section('pm') if sect is None else sect
    out: list[str] = []

    def add(msg: str) -> None:
        if msg and msg not in out:
            out.append(msg)

    flow = missing_flow_defect(section)
    if flow:
        add(flow)

    for key in VOCABULARY_KEYS:
        if key in section:
            add(f'[pm] {key} was retired and is refused — '
                f'{RETIRED_KEYS[key]}. Remove the key.')

    def probe(reader) -> None:
        try:
            reader()
        except ConfigError as err:
            add(str(err))

    def contains_probe() -> None:
        defect = contains_defect(
            str_tuple_table(section, 'pm', 'contains', DEFAULT_CONTAINS))
        if defect:
            raise ConfigError(defect)

    probe(lambda: str_tuple(section, 'pm', 'checks', DEFAULT_CHECKS))
    probe(lambda: text(section, 'pm', 'version_file', 'pyproject.toml'))
    probe(contains_probe)
    probe(lambda: flag(section, 'pm', 'breadcrumbs', True))
    probe(lambda: flag(section, 'pm', 'pressure', True))
    probe(lambda: number(section, 'pm', 'wip', 0))
    # Read against the flow this same section declares, so a node naming an
    # undeclared state is reported beside the flow defect rather than after a
    # second round trip.
    probe(lambda: _load_arrivals(section, _load_flows(section)))
    for _kind in FLOW_KINDS:
        probe(lambda k=_kind: relpath(section, 'pm', f'{k}_dir', ''))
    for key, fallback in (('roadmap_dir', 'pm/roadmap'),
                          ('review_dir', 'docs/reviews'),
                          ('template_dir', '')):
        probe(lambda k=key, f=fallback: relpath(section, 'pm', k, f))

    pattern = section.get('version_pattern')
    if isinstance(pattern, str):
        try:
            compiled = re.compile(pattern)
        except re.error as err:
            add(f'[pm] version_pattern is not a valid regex: {err}')
        else:
            if compiled.groups < 1:
                add('[pm] version_pattern needs one capture group around '
                    'the version itself')

    at = section.get('version_at')
    if at is not None and at not in VERSION_AT_CHOICES:
        add(f'[pm] version_at must be one of {" ".join(VERSION_AT_CHOICES)}, '
            f'got {at!r} — {VERSION_AT_START!r} is the first entry in `order` '
            f'that has not shipped (bump at start), {VERSION_AT_SHIP!r} the '
            f'last that has')

    if 'scaffold' in section:
        add("[pm.scaffold.*] was replaced by template FILES — set [pm] "
            "template_dir and run `pm templates` to copy them out, then edit "
            "the markdown")

    # Read off the section rather than off a config that may not have loaded
    # (review D3).
    raw_checks = section.get('checks')
    named = tuple(c for c in raw_checks
                  if isinstance(c, str)) if isinstance(raw_checks, list) else DEFAULT_CHECKS
    for check in named:
        if check in RETIRED_CHECKS:
            add(f'[pm] checks names {check}, which was retired — '
                f'{RETIRED_CHECKS[check]}. Remove it from the list.')
    unknown = [c for c in named
               if c not in KNOWN_CHECKS and c not in RETIRED_CHECKS]
    if unknown:
        add(f'[pm] checks names unknown rule(s) {", ".join(unknown)} — '
            f'known rules are {" ".join(KNOWN_CHECKS)}')
    for key, why in RETIRED_KEYS.items():
        if key in section and key not in VOCABULARY_KEYS:
            add(f'[pm] {key} was retired and does nothing — {why}. '
                f'Remove the key.')
    for name, why in RETIRED_SECTIONS.items():
        if section_declared(name):
            add(f'[{name}] was retired and does nothing — {why}. '
                f'Remove the section.')
    return out


def config_complaints(cfg: PmConfig, sect: dict | None = None) -> list[str]:
    """Everything `[pm]` names that this package does not ship — a stale rule
    id or a retired key — empty when clean. Raised by the gates, not by
    `load()`, so a pin bump cannot take `pm status` down."""
    out: list[str] = []
    for check in cfg.checks:
        if check in RETIRED_CHECKS:
            out.append(f'[pm] checks names {check}, which was retired — '
                       f'{RETIRED_CHECKS[check]}. Remove it from the list.')
    unknown = [c for c in cfg.checks
               if c not in KNOWN_CHECKS and c not in RETIRED_CHECKS]
    if unknown:
        out.append(f'[pm] checks names unknown rule(s) {", ".join(unknown)} — '
                   f'known rules are {" ".join(KNOWN_CHECKS)}')
    section = config_section('pm') if sect is None else sect
    for key, why in RETIRED_KEYS.items():
        if key in section:
            out.append(f'[pm] {key} was retired and does nothing — {why}. '
                       f'Remove the key.')
    # `sect` is the `[pm]` table a caller may inject; a retired section is read
    # from the file either way.
    for name, why in RETIRED_SECTIONS.items():
        if section_declared(name):
            out.append(f'[{name}] was retired and does nothing — {why}. '
                       f'Remove the section.')
    return out


# --- id <-> path --------------------------------------------------------------
# Milestone dirs carry a human suffix (`0.28-chronicle`); the id is the
# version, globbed active tree first, then the archive.
# Ids reach glob() as patterns, so an id must be a literal, never a pattern.
_GLOB_CHARS = set('*?[]!')


def id_is_literal(value: str) -> bool:
    return bool(value) and not (_GLOB_CHARS & set(value))


def segment_is_literal(value: str) -> bool:
    """One id segment the resolvers may join onto a directory — the resolution
    twin of `_check_slug`: no `.`/`..`/empty segment, separator or glob."""
    return (id_is_literal(value) and value not in ('.', '..')
            and not any(c in value for c in '/\\'))


# --- THE GRAIN LAYER: identity is frontmatter, location is convention -------
# `id:` and `kind:` are read from the document; the pools are where documents
# live; nothing interprets a path. The ~20 functions this replaced each joined
# an id onto a directory or into a `glob()` pattern — what `segment_is_literal`
# was written to make safe. Match-by-field builds no path from user input.

# The kind prefix a human reads off a bare id, without its location; `kind:` is
# what the TOOL reads. NOT a namespace: it does not make ids unique across
# repos, and cross-repo disambiguation is a display concern, never a filename.
KIND_PREFIX = {GRAIN_MILESTONE: 'ms', GRAIN_FEATURE: 'ft', GRAIN_STORY: 'st',
               GRAIN_BUG: 'bg'}

# What joins the prefix to the slug. Named because `mint_id` and every reader
# that asks "does this already carry its prefix" must agree on the byte.
PREFIX_SEPARATOR = '-'


def mint_id(kind: str, slug: str) -> str:
    """`<prefix>-<slug>` — THE ONE MINTING PATH, for `pm new` and for
    `tools/dev/pm_migrate.py`, so a migrated tree grows one id vocabulary and
    not two (`bg-the-new-verbs-mint-a-compound-id`).
    No parent in it: a binding is the child's own field, and an id restating it
    made re-parenting a `pm rename` plus a ref sweep. It MINTS and nothing else;
    no check grades an id against this (rule 9).
    """
    prefix = KIND_PREFIX[kind] + PREFIX_SEPARATOR
    return slug if slug.startswith(prefix) else f'{prefix}{slug}'


# The pool directory each kind DERIVES when the config names none. Spelled out
# rather than `f'{kind}s'` — English is not a rule to infer, and `storys` is
# what that inference produces.
POOL_NAME = {GRAIN_MILESTONE: 'milestones', GRAIN_FEATURE: 'features',
             GRAIN_STORY: 'stories', GRAIN_BUG: 'bugs'}

# The child's field that names its parent, per kind. **Membership is the
# child's field** — the northstar, as one mapping.
BINDS_TO = {GRAIN_FEATURE: (GRAIN_MILESTONE, GRAIN_MILESTONE),
            GRAIN_STORY: (GRAIN_FEATURE, GRAIN_FEATURE),
            GRAIN_BUG: (GRAIN_MILESTONE, GRAIN_MILESTONE)}


@dataclass(frozen=True)
class Grain:
    """One grain document, read once: what it says it is and what it says it
    belongs to. Nothing here is derived from `path`."""

    gid: str
    kind: str
    path: Path
    status: str = ''
    binding: str = ''

    # --- THE READ ADDRESSED BY IDENTITY ---------------------------------------
    # `grain(cfg, gid)` resolves an id to one of these and `.field(key)` asks
    # what it SAYS — so a caller that knows an id never names a file, and the
    # day a grain is not a file on disk this method is the only thing that has
    # to learn it. 102 callers handed `field_of` a `Path` before this existed;
    # `tests/test_boundaries.py::TheEngineAsksByIdNotByPath` holds the roster
    # of the ones that legitimately still hold a file.
    def field(self, key: str) -> str:
        """What this grain says under `key`, or ''."""
        return frontmatter.field_of(self.path, key)

    def list_field(self, key: str) -> list[str]:
        """The block list this grain declares under `key`, or []."""
        return frontmatter.list_field_of(self.path, key)

    def declares(self, key: str) -> bool:
        """Does this grain carry `key:` at ALL — presence, not value, for the
        fields whose mere existence is the finding (`RETIRED_FIELDS`). Raises
        what the read raises, as the parse does: a grain nobody can read is not
        an absence (rule 4)."""
        return key in frontmatter.document(self.path).fields

    def sequence_defect(self, key: str) -> str:
        """Why this grain's block list under `key` cannot be rewritten, or ''."""
        return frontmatter.sequence_defect(self.path, key)


def pool_dir(cfg: PmConfig, kind: str) -> Path:
    """Where documents of one kind live. Configured, or `<roadmap>/<kind>s`,
    relative to the repo root the tool already discovers: an absolute root in a
    committed config is wrong in every worktree, on every other machine and in
    CI, which is why there is no `project_root_dir` key.
    """
    declared = getattr(cfg, f'{kind}_dir_key', '')
    if declared:
        return cfg.root / declared
    return cfg.roadmap / POOL_NAME[kind]


def _is_shared_doc(path: Path) -> bool:
    """A grain's own decisions/handoff/review doc, rather than a grain. BOTH
    halves: a pooled slug is free-form, so a story named like a shared doc is
    not one, and it says so by opening frontmatter — which the two minted
    shared docs never do.
    """
    if not any(path.name.endswith(f'-{slot}') for slot in SLOT_HEADER):
        return False
    return not _is_grain_doc(path)


# --- ONE WALK PER SCAN --------------------------------------------------------
# `document` answers *what does this file say* once; this answers *what is in
# the tree* once. `check pm` asked that question about 330 times over a
# 700-document tree, and every ask was four `rglob`s and a sort.
#
# SCOPED, never a global memo: a verb that writes must see its own write on the
# next read, so the snapshot lives only inside `reading_tree()`. Belt and
# braces, it is dropped the instant anything in this process mutates a file —
# `core.apply` counts every write this package is allowed to make.
_SNAPSHOT: dict | None = None
_MUTATIONS_KEY = 'mutations'


@contextmanager
def reading_tree():
    """Walk the pools ONCE for the length of this block — for a caller that
    only reads. Nested scopes share the outer one; leaving drops it.
    """
    global _SNAPSHOT
    outer = _SNAPSHOT
    if outer is None:
        _SNAPSHOT = {_MUTATIONS_KEY: apply.mutations()}
    try:
        yield
    finally:
        _SNAPSHOT = outer


def _held(key, produce):
    """`produce()`, held for the rest of the scope when there is one and
    nothing has written since it opened."""
    snap = _SNAPSHOT
    if snap is None:
        return produce()
    mutations = apply.mutations()
    if snap.get(_MUTATIONS_KEY) != mutations:
        snap.clear()
        snap[_MUTATIONS_KEY] = mutations
    if key not in snap:
        snap[key] = produce()
    return snap[key]


def pool_scan(cfg: PmConfig, kind: str) -> Walk:
    """One pool as a `Walk` — the kept documents AND what it narrowed away.
    `slot_walk` for a table: a dot prefix is a deliberate hide and a `.md` that
    opens no frontmatter is a note, and both are COUNTED (rule 4).
    """
    base = pool_dir(cfg, kind)
    return _held(('pool', str(base)), lambda: _pool_scan(base))


def _pool_scan(base: Path) -> Walk:
    if not base.is_dir():
        return Walk(())
    return (walk.descendants(base, Kind.FILE, suffix='.md')
            .filter(lambda p: not _is_hidden(base, p), SkipReason.DOTTED_NAME)
            .filter(lambda p: not _is_shared_doc(p), SkipReason.SHARED_DOC)
            .filter(_is_grain_doc, SkipReason.NO_FRONTMATTER))


def pool_walk(cfg: PmConfig, kind: str) -> list[Path]:
    """Every document in one pool, sorted."""
    return sorted(pool_scan(cfg, kind).kept)


def pool_census(cfg: PmConfig, kind: str, label: str) -> str:
    """One pool's count WITH its narrowings. A bare number is not available on
    purpose: the count and what the walk left out render together, or the count
    is a claim about the filter rather than about the tree (rule 4).
    """
    return pool_scan(cfg, kind).census(label)


def pool_skipped(cfg: PmConfig, kind: str) -> int:
    """How many candidates a narrowing removed from one pool."""
    return sum(pool_scan(cfg, kind).counts().values())


def doc_grain(path: Path, kind: str = '') -> Grain:
    """One document as a `Grain`, whatever it declares — `read_grain`'s TOTAL
    sibling, for a walk that must not drop the document it just found.

    `gid` is '' when the document declares no `id:` or cannot be read, which is
    exactly what a reader of the field got; `read_grain` answers None there
    instead, and `check pm` counts those SKIPPED rather than dropping them
    (`ft-identity-lives-in-frontmatter`). The two answers are different
    questions and both have callers, so both are spelled.
    """
    try:
        doc = frontmatter.document(path)
    except (OSError, UnicodeDecodeError):
        return Grain(gid='', kind=kind, path=path)
    declared = doc.field(FIELD_KIND) or kind
    field = BINDS_TO.get(declared, ('', ''))[1]
    return Grain(gid=doc.field(FIELD_ID), kind=declared, path=path,
                 status=doc.field(FIELD_STATUS),
                 binding=doc.field(field) if field else '')


def read_grain(cfg: PmConfig, path: Path, kind: str) -> Grain | None:
    """One document as a `Grain`, or None when it declares no id.

    `kind` is the POOL it was found in, and it is only a default: a document
    that declares `kind:` is that kind wherever it sits, because the location
    is convention the tool does not interpret. A document that cannot be read
    declares no id.
    """
    found = doc_grain(path, kind)
    return found if found.gid else None


def is_pooled(cfg: PmConfig) -> bool:
    """Has this tree been migrated? True when any pool holds a document.

    The one place the two layouts are told apart, and a fact about the tree
    rather than a config key: a key would be a second copy of what the
    directory already says, to be kept in agreement mid-migration.
    """
    return any(pool_dir(cfg, kind).is_dir() and pool_walk(cfg, kind)
               for kind in FLOW_KINDS)


def is_nested(cfg: PmConfig) -> bool:
    """Does this tree still hold grain DIRECTORIES? The question a WRITE asks:
    a reader tells the layouts apart by what it finds, a writer has to choose
    before anything exists."""
    return bool(milestone_dirs(cfg))


def mint_dir(cfg: PmConfig, kind: str, parent: Path | None = None) -> Path:
    """Where `pm new` puts a NEW document of `kind` — the pool, unless the tree
    is still nested, in which case it keeps its shape. Minting into a pool on a
    nested tree flips `is_pooled` and hides every other grain behind it."""
    if not is_nested(cfg):
        return pool_dir(cfg, kind)
    if kind == GRAIN_MILESTONE:
        return cfg.roadmap
    if parent is None:
        return pool_dir(cfg, kind)
    if kind == GRAIN_FEATURE:
        return parent / FEATURES_DIR
    if kind == GRAIN_STORY:
        return parent / STORIES_DIR
    return parent / BUGS_DIR


def _nested_index(cfg: PmConfig) -> dict[str, Grain]:
    """The pre-0.4.0 layout, read the way it was always read: kind from the
    slot the document sits in, parent from the directory above.

    Kept so a consumer's tree keeps working the day they bump and before it is
    moved — the alternative reads nothing until a migration lands, which is a
    breaking change wearing a minor number. The ONLY code left that treats a
    path as schema; `tools/dev/pm_migrate.py` is the mover.
    """
    out: dict[str, Grain] = {}

    def take(path: Path, kind: str, binding: str) -> str:
        gid = frontmatter.field_of(path, FIELD_ID)
        if not gid:
            return ''
        out.setdefault(gid, Grain(gid=gid, kind=kind, path=path,
                                  status=frontmatter.field_of(path, FIELD_STATUS),
                                  binding=binding))
        return gid

    for mdir in milestone_dirs(cfg):
        mid = take(mdir / MILESTONE_DOC, GRAIN_MILESTONE, '')
        for ffile in _nested_feature_files(mdir):
            fid = take(ffile, GRAIN_FEATURE, mid)
            for sfile in _nested_story_files(ffile):
                take(sfile, GRAIN_STORY, fid)
        for bfile in _nested_bug_files(mdir):
            take(bfile, GRAIN_BUG, mid)
    return out


def grain_index(cfg: PmConfig) -> dict[str, Grain]:
    """Every grain in the tree, by id — the pools plus the ROOT container. The
    one walk every resolver goes through.

    A duplicate id is NOT resolved here — the first one read wins and V1 names
    every file that shares one. Uniqueness is a gate FINDING and never a
    runtime lock (0.4.0/D4).

    Held for the length of a `reading_tree()` scope; built afresh outside one.
    Every caller READS the mapping — inside a scope, editing it would be
    editing the next reader's answer.
    """
    return _held(('index', str(cfg.roadmap),
                  tuple(str(pool_dir(cfg, k)) for k in FLOW_KINDS)),
                 lambda: _grain_index(cfg))


def _grain_index(cfg: PmConfig) -> dict[str, Grain]:
    if is_pooled(cfg):
        out: dict[str, Grain] = {}
        for kind in FLOW_KINDS:
            for path in pool_walk(cfg, kind):
                grain = read_grain(cfg, path, kind)
                if grain is not None:
                    out.setdefault(grain.gid, grain)
    else:
        out = _nested_index(cfg)
    root = root_grain(cfg)
    if root is not None:
        # LAST: a pool document claiming the plan's id is a duplicate the gate
        # reports, and the resolver must not answer it with the plan.
        out.setdefault(root.gid, root)
    return out


# The characters an id cannot carry in EITHER layout. NOT the security guard —
# match-by-field is, and no id reaches a path. This is CHEAPNESS: an id that
# cannot be a grain's is refused before the tree is walked, so a hostile string
# is answered without reading a document, which the resolvers this replaced did.
_ID_FORBIDDEN = set('*?[]!\\:~\n\t\r\x00')
ID_MAX = 200


def id_defect(gid: str) -> str:
    """'' when `gid` could name a grain, else why not. Never opens a file."""
    if not gid or not gid.strip():
        return 'an id may not be empty'
    if len(gid) > ID_MAX:
        return f'an id of {len(gid)} characters is past the {ID_MAX} limit'
    if _ID_FORBIDDEN & set(gid):
        return f'{gid!r} carries a character no id may hold'
    parts = gid.split('/')
    if any(p in ('', '.', '..') for p in parts):
        return f'{gid!r} has an empty or dot segment'
    return ''


def kind_of(cfg: PmConfig, gid: str) -> str:
    """The kind a grain declares, or '' when nothing in the tree claims the id.
    The id's SHAPE is not consulted: `ft-x` and `0.1/x` are both just ids, and
    reading a kind out of either is the derivation 0.4.0 deleted.
    """
    found = grain_index(cfg).get(gid)
    return found.kind if found is not None else ''


def grain(cfg: PmConfig, gid: str, kind: str = '') -> Grain | None:
    """THE ID-ADDRESSED HANDLE: the grain an id names, or None; `kind` narrows
    when a caller knows it.

    `grain(cfg, gid).field(key)` is how a module that knows an id asks what
    that grain SAYS, and it is the whole of what such a module needs — the six
    resolvers this replaced each joined an id onto a directory, and every
    caller then had a `Path` and asked storage directly. This reads `id:` and
    matches, so no user input reaches a path and no caller names a file.
    """
    if id_defect(gid):
        return None
    found = grain_index(cfg).get(gid)
    if found is None or (kind and found.kind != kind):
        return None
    return found


def grain_file(cfg: PmConfig, gid: str, kind: str = '') -> Path | None:
    """The DOCUMENT for an id, or None — for the callers that need the file
    itself (a shared doc beside it, a path in a message). A caller that wants
    a FIELD asks `grain(cfg, gid).field(key)` instead.
    """
    found = grain(cfg, gid, kind)
    return None if found is None else found.path


def children(cfg: PmConfig, kind: str, parent_id: str) -> list[Grain]:
    """Grains of `kind` whose binding field names `parent_id` — found by their
    BINDING, not by which directory they sit in."""
    return [g for g in grain_index(cfg).values()
            if g.kind == kind and g.binding == parent_id]


def unbound(cfg: PmConfig, kind: str) -> list[Grain]:
    """Grains of `kind` that name no parent. Normal and expected: a grain
    written and not yet bound is what separating authoring from binding is
    FOR, and it is a census line, never a finding."""
    return [g for g in grain_index(cfg).values()
            if g.kind == kind and BINDS_TO.get(kind) and not g.binding]


def milestone_of(cfg: PmConfig, gid: str) -> str:
    """Which milestone a grain belongs to, followed through its bindings — a
    story takes one hop more than a feature. `milestone_dir_of(path)` used to
    answer this by counting path components: the same fact, derived from where
    a file sat.
    """
    index = grain_index(cfg)
    seen: set[str] = set()
    while gid and gid not in seen:
        seen.add(gid)
        grain = index.get(gid)
        if grain is None:
            return ''
        if grain.kind == GRAIN_MILESTONE:
            return grain.gid
        gid = grain.binding
    return ''


def duplicate_ids(cfg: PmConfig) -> dict[str, list[Path]]:
    """{id: every document claiming it}, for the ids more than one claims. Per
    KIND is the uniqueness rule: the same slug in two different kinds is fine,
    because the prefix distinguishes them.
    """
    seen: dict[tuple[str, str], list[Path]] = {}
    for kind in FLOW_KINDS:
        for path in pool_walk(cfg, kind):
            grain = read_grain(cfg, path, kind)
            if grain is not None:
                seen.setdefault((grain.kind, grain.gid), []).append(path)
    return {gid: paths for (_kind, gid), paths in seen.items()
            if len(paths) > 1}


def undeclared_kinds(cfg: PmConfig) -> list[tuple[Path, str]]:
    """(document, the `kind:` it declares) for kinds this project does not
    have. A fact about the INPUT — refused by name where a verb reads one,
    reported by the gate over a tree."""
    out = []
    for kind in FLOW_KINDS:
        for path in pool_walk(cfg, kind):
            declared = frontmatter.field_of(path, FIELD_KIND)
            if declared and declared not in FLOW_KINDS:
                out.append((path, declared))
    return out


# --- the nested layout, read only by the migration ----------------------------
def milestone_dir(cfg: PmConfig, mid: str) -> Path | None:
    if not segment_is_literal(mid):
        return None
    for base in (cfg.roadmap, cfg.roadmap / ARCHIVE_DIR_NAME):
        if not base.is_dir():
            continue
        for d in walk.matching(base, f'{mid}-*', Kind.DIR).kept:
            return d
    return None


def milestone_file(cfg: PmConfig, mid: str) -> Path | None:
    """The milestone's document, in either layout — `grain_file` reads `id:`
    and matches, so no id reaches a path."""
    return grain_file(cfg, mid, GRAIN_MILESTONE)


def feature_dir(cfg: PmConfig, fid: str) -> Path | None:
    mid, _, slug = fid.partition('/')
    if not segment_is_literal(slug):
        return None
    d = milestone_dir(cfg, mid)
    if d is None:
        return None
    fdir = d / FEATURES_DIR / slug
    return fdir if fdir.is_dir() else None


def feature_file(cfg: PmConfig, fid: str) -> Path | None:
    """The feature's document, in either layout."""
    return grain_file(cfg, fid, GRAIN_FEATURE)


def story_grain(cfg: PmConfig, sid: str) -> Grain | None:
    """The story an id names, in either layout — `grain(cfg, sid, 'story')` on a
    pooled tree, and `story_file`'s own slug resolution on a nested one, where
    the index cannot answer because a nested story's id is its path.
    """
    if is_pooled(cfg):
        return grain(cfg, sid, GRAIN_STORY)
    path = story_file(cfg, sid)
    return None if path is None else doc_grain(path, GRAIN_STORY)


def story_file(cfg: PmConfig, sid: str) -> Path | None:
    """The story's document, in either layout.

    `AmbiguousStory` — *two files claim one story id* — cannot happen against a
    pooled tree: the index is keyed by id and `check pm` reports a duplicate as
    a finding. It survives for the nested layout, where a slug plus an ordinal
    prefix could resolve two ways.
    """
    if is_pooled(cfg):
        return grain_file(cfg, sid, GRAIN_STORY)
    # The nested layout keeps its own resolution WHOLE: the index answers by
    # id and `setdefault`, so consulting it first would silently pick one of
    # two files claiming a slug — a refusal turned into a wrong answer.
    mid, _, rest = sid.partition('/')
    fslug, _, sslug = rest.partition('/')
    if not fslug or not segment_is_literal(sslug):
        return None
    fdir = feature_dir(cfg, f'{mid}/{fslug}')
    if fdir is None:
        return None
    matches = [path for path in grain_docs(fdir / STORIES_DIR)
               if path.name[:-len(path.suffix)] == sslug]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise AmbiguousStory(sid, [cfg.rel(p) for p in matches])
    return None


class AmbiguousStory(Exception):
    """Two files claim one story id — an authoring error, never auto-resolved."""

    def __init__(self, sid: str, paths: list[str]) -> None:
        super().__init__(f'story id {sid!r} matches {len(paths)} files: {", ".join(paths)}')
        self.sid = sid
        self.paths = paths


# --- children -----------------------------------------------------------------
def shared_doc(cfg: PmConfig, grain: 'Grain | Path', name: str) -> Path:
    """Where a grain's shared document lives. Pooled: beside the grain, under
    the grain's own stem, because a pool is flat and a bare `decisions.md`
    would be one file for every grain of that kind. Nested: inside the grain's
    directory.
    """
    path = grain if isinstance(grain, Path) else grain.path
    # `is_pooled` and not the parent's NAME: a tree that configured its pools
    # elsewhere is still pooled, and the name would put its shared docs back
    # inside directories that do not exist.
    if is_pooled(cfg):
        return path.with_name(f'{path.stem}-{name}')
    return path.parent / name


def milestone_doc(handle: Path) -> Path:
    """The milestone's DOCUMENT from whatever `known_milestones` handed back —
    a document when pooled, a directory when nested. One function, so the
    `handle / MILESTONE_DOC` join, which is the path being schema, exists in
    one place instead of a dozen.
    """
    return handle if handle.is_file() else handle / MILESTONE_DOC


def milestones(cfg: PmConfig) -> list[Grain]:
    """Every milestone, by id — for a caller that wants the grains."""
    return sorted((g for g in grain_index(cfg).values()
                   if g.kind == GRAIN_MILESTONE), key=lambda g: g.gid)


def _children_grains(cfg: PmConfig, kind: str, parent_id: str) -> list[Grain]:
    """The grains of one kind bound to one parent, in the parent's declared
    `order` where it has one and by id after that. **Sequence is the parent's
    list and membership is the child's field** — the two questions the nested
    layout answered with one directory.
    """
    found = {g.gid: g for g in children(cfg, kind, parent_id)}
    parent = grain_index(cfg).get(parent_id)
    declared = parent.list_field(ORDER_KEY) if parent is not None else []
    out = [found.pop(gid) for gid in declared if gid in found]
    return out + [found[gid] for gid in sorted(found)]


# A nested tree keeps its SLOT walk, whole: the index is keyed by `id:`, so a
# damaged document has no key and would silently leave the census, and the slot
# walk sees it either way (rule 4). A POOLED tree has no slot, so a document
# with no id is reported by `check pm` on its own line instead.
# The GRAIN walk and the PATH walk of the same children. The grains are what a
# caller reads fields from; the paths are what `report.Source` declares, since
# a rev-addressed source hands back handles that are not files at all. The path
# list is DERIVED from the grain list, so the two cannot answer differently
# about what is in the tree.
#
# `doc_grain`, not `read_grain`: a child document declaring no `id:` is in the
# parent's slot and is COUNTED, and `read_grain` would have dropped it — the
# census loss `check pm` reports as SKIPPED instead (rule 4).
def feature_grains(cfg: PmConfig, mid: str) -> list[Grain]:
    """The features bound to one milestone, in its declared order."""
    if not is_pooled(cfg):
        mdir = milestone_dir(cfg, mid)
        return [doc_grain(p, GRAIN_FEATURE)
                for p in (_nested_feature_files(mdir) if mdir is not None
                          else [])]
    return _children_grains(cfg, GRAIN_FEATURE, mid)


def story_grains(cfg: PmConfig, fid: str) -> list[Grain]:
    """The stories bound to one feature, in its declared order."""
    if not is_pooled(cfg):
        ffile = feature_file(cfg, fid)
        return [doc_grain(p, GRAIN_STORY)
                for p in (_nested_story_files(ffile) if ffile is not None
                          else [])]
    return _children_grains(cfg, GRAIN_STORY, fid)


def bug_grains(cfg: PmConfig, mid: str) -> list[Grain]:
    """The bugs bound to one milestone, in its declared order."""
    if not is_pooled(cfg):
        mdir = milestone_dir(cfg, mid)
        return [doc_grain(p, GRAIN_BUG)
                for p in (_nested_bug_files(mdir) if mdir is not None else [])]
    return _children_grains(cfg, GRAIN_BUG, mid)


def feature_files(cfg: PmConfig, mid: str) -> list[Path]:
    """The feature DOCUMENTS bound to one milestone, in its declared order."""
    return [g.path for g in feature_grains(cfg, mid)]


def story_files(cfg: PmConfig, fid: str) -> list[Path]:
    """The story DOCUMENTS bound to one feature, in its declared order."""
    return [g.path for g in story_grains(cfg, fid)]


def bug_files(cfg: PmConfig, mid: str) -> list[Path]:
    """The bug DOCUMENTS bound to one milestone, in its declared order."""
    return [g.path for g in bug_grains(cfg, mid)]


def duplicate_ids(cfg: PmConfig) -> list[tuple[str, list[Path]]]:
    """[(id, every document claiming it)] for each id claimed more than once.
    The other half of D4: `grain_index` keeps the first document read, so the
    second is in the tree, is counted, and is addressable by nothing.
    """
    seen: dict[str, list[Path]] = {}
    for kind in FLOW_KINDS:
        for path in pool_walk(cfg, kind):
            gid = frontmatter.field_of(path, FIELD_ID)
            if gid:
                seen.setdefault(gid, []).append(path)
    return [(gid, paths) for gid, paths in sorted(seen.items())
            if len(paths) > 1]


def unbound_grains(cfg: PmConfig) -> dict[str, list[str]]:
    """{'feature': [ids naming no milestone], 'story': [...], 'bug': [...]}.
    Only kinds that BIND, and only an EMPTY binding — a binding naming a grain
    that is not in the tree is V7's, because that is drift rather than a
    decision nobody has made yet.
    """
    out: dict[str, list[str]] = {}
    for gid, grain in sorted(grain_index(cfg).items()):
        bind = BINDS_TO.get(grain.kind)
        if bind is None:
            continue
        if not frontmatter.field_of(grain.path, bind[1]):
            out.setdefault(grain.kind, []).append(gid)
    return out


def stray_documents(cfg: PmConfig) -> list[Grain]:
    """Grain documents under the roadmap that sit in no pool: every pooled
    reader walks the pools, so a document outside all four is read by NOTHING
    while `check grain-shape`, which walks the roadmap whole, counts it. Shared
    docs and the plan are expected outside a pool.

    As GRAINS, because the one caller reports what each one DECLARES and a
    stray is only a stray because it declares an `id:` nothing indexes.
    """
    if not is_pooled(cfg):
        return []
    pools = {pool_dir(cfg, kind) for kind in FLOW_KINDS}
    known = {releases_file(cfg)}
    out: list[Path] = []
    for path in walk.descendants(cfg.roadmap, Kind.FILE, suffix='.md').kept:
        if path in known or _is_hidden(cfg.roadmap, path):
            continue
        if any(pool == path.parent or pool in path.parents for pool in pools):
            continue
        if _is_grain_doc(path) and frontmatter.field_of(path, FIELD_ID):
            out.append(path)
    return [doc_grain(path) for path in sorted(out)]


def unkeyed_documents(cfg: PmConfig) -> list[tuple[Path, str]]:
    """Documents in a pool that the index cannot key on, and why. `orphan_dirs`'
    successor: a document with no readable `id:` has no key, is in no index,
    and would leave the census silently.
    """
    out: list[tuple[Path, str]] = []
    for kind in FLOW_KINDS:
        for path in pool_walk(cfg, kind):
            if not frontmatter.field_of(path, FIELD_ID):
                out.append((path, 'declares no `id:`, so nothing can key on '
                                  'it'))
                continue
            if not frontmatter.field_of(path, FIELD_STATUS):
                out.append((path, 'declares no `status:` — it is in the tree '
                                  'and no question about it can be answered'))
                continue
            declared = frontmatter.field_of(path, FIELD_KIND)
            if declared and declared not in FLOW_KINDS:
                out.append((path, f'declares kind {declared!r}, which this '
                                  f'project does not have '
                                  f'({" ".join(FLOW_KINDS)})'))
    return out


def _has_milestone_file(d: Path) -> bool:
    return (d / MILESTONE_DOC).is_file()


def _has_feature_file(d: Path) -> bool:
    return (d / FEATURE_DOC).is_file()


def _milestone_candidates(base: Path, exclude_archive: bool) -> Walk:
    """Directories under one roadmap base that a milestone could be."""
    found = walk.children(base, Kind.DIR)
    if exclude_archive:
        found = found.filter(lambda d: d.name != ARCHIVE_DIR_NAME,
                             SkipReason.EXCLUDED_PATH)
    return found


def milestone_walk(cfg: PmConfig) -> Walk:
    """Milestone dirs in the active tree, with the scaffold-only dirs the walk
    dropped beside them."""
    return _milestone_candidates(cfg.roadmap, exclude_archive=True).filter(
        _has_milestone_file, SkipReason.NO_GRAIN_FILE)


def milestone_dirs(cfg: PmConfig) -> list[Path]:
    """Milestone dirs in the ACTIVE tree (archived ones predate the schema)."""
    return list(milestone_walk(cfg).kept)


def known_milestones(cfg: PmConfig) -> list[tuple[Path, str]]:
    """(a handle, the declared id) per milestone — the one enumeration
    `pm status`, `pm list` and `retire` read.

    The handle is the milestone's own DIRECTORY in a nested tree and its
    DOCUMENT in a pooled one; a caller that needs a directory asks
    `milestone_dir`.
    """
    if is_pooled(cfg):
        return [(g.path, g.gid) for g in milestones(cfg)]
    return [(mdir, frontmatter.field_of(mdir / MILESTONE_DOC, FIELD_ID))
            for mdir in milestone_dirs(cfg)]


def known_milestone_grains(cfg: PmConfig) -> list[tuple[Path, Grain]]:
    """(`known_milestones`' handle, that milestone's GRAIN) — for the readers
    that go on to ask the milestone what it SAYS.

    The handle stays beside the grain because it is the nested tree's
    DIRECTORY, which `shared_doc` and `ledger_for` need and a document cannot
    replace; the grain is `milestone_doc(handle)` read once, so a milestone
    declaring no `id:` is still in the list with an empty one — the id the
    handle-and-id pairing returned for it.
    """
    return [(handle, doc_grain(milestone_doc(handle), GRAIN_MILESTONE))
            for handle, _ in known_milestones(cfg)]


BOM = '﻿'


def _opens_frontmatter(lines: Sequence[str]) -> bool:
    """True when this text attempts a leading `---` block — lenient on a BOM,
    blank lines and fence indent, so a damaged grain is a finding rather than
    a note, but never past prose.
    """
    for line in lines:
        probe = line.lstrip(BOM)
        if not probe.strip():
            continue
        return frontmatter._FENCE.match(probe.lstrip(' \t')) is not None
    return False


def _is_grain_doc(path: Path) -> bool:
    """True when this file is a grain document rather than a note beside one.
    Detection is lenient and parsing strict, so a damaged grain stays in scope
    for the rules; so does a file that cannot be read.
    """
    try:
        return _opens_frontmatter(frontmatter.document(path).lines)
    except (OSError, UnicodeDecodeError):
        return True


def slot_walk(gdir: Path) -> Walk:
    """The walk of one slot directory (`bugs/`, `stories/`) — the single
    definition every reader shares, with two disclosed narrowings: dot-prefixed
    components, and a `.md` that opens no frontmatter.
    """
    return (walk.descendants(gdir, Kind.FILE, suffix='.md')
            .filter(lambda p: not _is_hidden(gdir, p), SkipReason.DOTTED_NAME)
            .filter(_is_grain_doc, SkipReason.NO_FRONTMATTER))


def _is_hidden(gdir: Path, p: Path) -> bool:
    """True if any path component under `gdir` is dot-prefixed."""
    return any(part.startswith('.') for part in p.relative_to(gdir).parts)


def grain_docs(gdir: Path) -> list[Path]:
    """Every grain document under one slot directory, in reading order."""
    return list(slot_walk(gdir).kept)


def _nested_feature_files(mdir: Path) -> list[Path]:
    return [d / FEATURE_DOC for d in walk.children(mdir / FEATURES_DIR, Kind.DIR)
            .filter(_has_feature_file, SkipReason.NO_GRAIN_FILE).kept]


def _nested_story_files(ffile: Path) -> list[Path]:
    return grain_docs(ffile.parent / STORIES_DIR)


def tree_walk(cfg: PmConfig) -> Walk:
    """Every slot document in the active tree and everything the walk skipped;
    `Walk.census` is the only way to a number here.
    """
    found = Walk(())
    if is_pooled(cfg):
        # The same two kinds the nested walk disclosed for, through the same
        # narrowings — `pool_scan` IS `slot_walk` for a table.
        for kind in (GRAIN_STORY, GRAIN_BUG):
            found = found.merge(pool_scan(cfg, kind))
        return found
    for mdir in milestone_dirs(cfg):
        found = found.merge(slot_walk(mdir / BUGS_DIR))
        for ffile in _nested_feature_files(mdir):
            found = found.merge(slot_walk(ffile.parent / STORIES_DIR))
    return found


# --- THE review-record definition --------------------------------------------
def record_resolves(path: Path) -> bool:
    """True if the pointer names a file that is there — the whole definition;
    how much a reviewer wrote is not a fact about anything."""
    return path.is_file()


def record_path(cfg: PmConfig, pointer: str) -> Path:
    """The file a record pointer names — `--review-record`'s and `--source`'s
    ONE resolution, so the escape guard beside it is asked at both."""
    return Path(pointer) if pointer.startswith('/') else cfg.root / pointer


def pointer_escapes(pointer: str) -> bool:
    """Outside the checkout? The shapes `core.config.relpath` refuses, as a
    predicate: a bad pointer is a finding, never a config error."""
    return (pointer.startswith(('/', '~', '\\'))
            or ':' in pointer.split('/', 1)[0]
            or '..' in Path(pointer).parts)


def review_record_for(cfg: PmConfig, fid: str) -> str | None:
    """The feature's resolved review record, or None; the `reviewed:` pointer
    is the whole mechanism, with no filename fallback."""
    feature = grain(cfg, fid, GRAIN_FEATURE)
    if feature is None:
        return None
    pointer = feature.field('reviewed')
    if pointer and pointer != 'null':
        # Repo-relative, always (hard rule 8): an absolute pointer is a
        # record nobody reviewing this repo can read.
        if pointer_escapes(pointer):
            return None
        if record_resolves(cfg.root / pointer):
            return pointer
    return None


# --- flow helpers (D9/D10, and the ledger's home) -----------------------------
def in_progress_milestones(cfg: PmConfig) -> list[tuple[str, str, Path]]:
    """(id, branch, milestone.md) for every active milestone in `in_progress`.
    There is no "the building milestone" (D5): readers report over every one or
    refuse naming them all.
    """
    out = []
    for milestone in milestones(cfg):
        if category_of(cfg, GRAIN_MILESTONE, milestone.status) != IN_PROGRESS:
            continue
        out.append((milestone.field(FIELD_ID), milestone.field('branch'),
                    milestone.path))
    return out


def mainline_branch() -> str:
    """D10's trunk name — `[repo_hygiene] mainline`, `origin/`-stripped, since
    a milestone's authored `branch:` is never remote-qualified."""
    sect = config_section('repo_hygiene')
    value = text(sect, 'repo_hygiene', 'mainline', 'origin/main')
    if value.startswith('origin/'):
        value = value[len('origin/'):]
    return value


def shipped_version(cfg: PmConfig) -> str | None:
    """The version string from the project's own manifest, or None."""
    path = cfg.root / cfg.version_file
    if not path.is_file():
        return None
    pattern = re.compile(cfg.version_pattern)
    try:
        for line in frontmatter.read_raw(path).split('\n'):
            m = pattern.match(line.strip())
            if m:
                return m.group(1)
    except (OSError, UnicodeDecodeError):
        return None
    return None


# --- the plan: a declared order of versions, and the grain that claims each ---
# Nothing here parses, compares or increments a version string. "Did it
# increase" is a POSITION in `order`; `"1.1.1"` and `"cow"` are equally valid.
def releases_file(cfg: PmConfig) -> Path:
    """`pm/roadmap/releases.md` — the plan. Absent until `pm add` writes it."""
    return cfg.roadmap / RELEASES_DOC


def root_grain(cfg: PmConfig) -> Grain | None:
    """The plan document as a grain — the ROOT container — or None. A plan
    written before 0.4.0 declares neither `id:` nor `kind:` and answers to
    `roadmap`, so adopting `pm add` costs no edit."""
    path = releases_file(cfg)
    if not path.is_file():
        return None
    return Grain(gid=frontmatter.field_of(path, FIELD_ID) or ROOT_ID,
                 kind=frontmatter.field_of(path, FIELD_KIND) or ROOT_KIND,
                 path=path)


def plan_defect(cfg: PmConfig) -> str | None:
    """Why `releases.md` cannot be read as a plan, or None.

    An ABSENT plan is not a defect — a tree mid-adoption has none. A plan that
    is THERE and unreadable is: reporting "declares no `order`" over a damaged
    file is rule 4's first cardinal sin, a gate passing over what it did not
    measure.
    """
    path = releases_file(cfg)
    if not path.is_file():
        return None
    try:
        doc = frontmatter.document(path)
    except (OSError, UnicodeDecodeError) as err:
        return f'could not be read as UTF-8 text ({err.__class__.__name__})'
    lines = doc.lines
    if doc.bounds is None:
        if lines and lines[0].startswith(BOM):
            # Naming it "no frontmatter" sent the reader looking for a block
            # that is there behind three invisible bytes (review B5).
            return ('opens with a UTF-8 BOM before its `---`, so the '
                    'frontmatter block is not the first line — strip the BOM')
        opens = bool(lines) and frontmatter._FENCE.match(lines[0]) is not None
        return ('has an opening `---` with no closing one'
                if opens else
                'has no frontmatter block — the plan is a grain, and `order` '
                'lives in its frontmatter')
    open_i, close_i = frontmatter._fence_bounds(lines)
    for i in range(open_i + 1, close_i):
        if not lines[i].startswith(f'{ORDER_KEY}:'):
            continue
        rest = lines[i][len(ORDER_KEY) + 1:].strip()
        if rest and not rest.startswith('#'):
            return (f'`{ORDER_KEY}:` carries a scalar ({rest!r}) rather than a '
                    f'block list — one `- "<milestone-id>"` per line')
        return None
    return (f'declares no `{ORDER_KEY}:` key — the file is there, so this is a '
            f'plan that lost its list rather than a tree that has none')


def declared_order(cfg: PmConfig) -> list[str]:
    """The declared sequence of MILESTONE IDS, or [] when there is no plan.
    Ids, not versions (0.4.0/D4): a milestone that re-versions never touches
    the plan, and `pm rename` sweeps the entry with every other reference.
    """
    return frontmatter.list_field_of(releases_file(cfg), ORDER_KEY)


def milestone_version(cfg: PmConfig, mid: str) -> str:
    """The version a milestone declares it ships as, or '' — it is optional,
    and a milestone without one is BACKLOG, never a finding (R2)."""
    milestone = grain(cfg, mid, GRAIN_MILESTONE)
    return milestone.field('version').strip() if milestone is not None else ''


def version_claims(cfg: PmConfig) -> list[tuple[str, str]]:
    """(version, milestone id) for every milestone that declares one, in tree
    order. A list rather than a dict: R3 asks whether two milestones claim the
    same version, and a dict would have eaten the duplicate."""
    out = []
    for handle, mid in known_milestones(cfg):
        mfile = handle if handle.is_file() else handle / MILESTONE_DOC
        # `.strip()`: a whitespace-only `version:` is not a claim.
        version = frontmatter.field_of(mfile, 'version').strip()
        if version:
            out.append((version, mid))
    return out


def milestones_of_version(cfg: PmConfig, version: str) -> list[str]:
    """Every milestone claiming `version`, in tree order. A list, because two
    milestones claiming one version is a real tree defect (R3), and answering
    with the first would make the verdict depend on read order.
    """
    return [mid for claimed, mid in version_claims(cfg) if claimed == version]


def milestone_of_version(cfg: PmConfig, version: str) -> str | None:
    """The one milestone claiming `version`, or None when none or several do."""
    claimants = milestones_of_version(cfg, version)
    return claimants[0] if len(claimants) == 1 else None


def entry_is_shipped(cfg: PmConfig, mid: str) -> bool:
    """Has the milestone this plan entry names finished?"""
    milestone = grain(cfg, mid, GRAIN_MILESTONE)
    if milestone is None:
        return False
    return category_of(cfg, GRAIN_MILESTONE,
                       milestone.field(FIELD_STATUS)) == DONE_CATEGORY


def entry_is_dangling(cfg: PmConfig, mid: str) -> bool:
    """Does this plan entry name no milestone in the tree? Never read as "not
    shipped": a RETIRED milestone and one nobody has written look identical
    from here, and calling either unshipped rolled the release BACKWARD."""
    return milestone_file(cfg, mid) is None


def last_shipped_index(cfg: PmConfig) -> int:
    """Position of the last entry in `order` whose milestone is `done`, or -1.
    "Behind us" is a POSITION, which is the whole reason order is declared: no
    comparator is asked whether 0.90.10 follows 0.90.4.
    """
    last = -1
    for i, mid in enumerate(declared_order(cfg)):
        if entry_is_shipped(cfg, mid):
            last = i
    return last


def current_milestone(cfg: PmConfig) -> str | None:
    """The milestone being WORKED ON: the first entry in `order` not yet done.
    A DANGLING entry is stepped over rather than stopping the walk (it would
    break the belt for every tree that prunes) and R1 names it every run."""
    for mid in declared_order(cfg):
        if entry_is_shipped(cfg, mid) or entry_is_dangling(cfg, mid):
            continue
        return mid
    return None


def current_release(cfg: PmConfig) -> str | None:
    """The VERSION the current milestone declares, or None. Never `[pm]
    version_at`, which answers *which entry should the version FILE equal* — a
    project bumping at CLOSE answers that with the last SHIPPED release, so
    feeding it here re-released a finished milestone.
    """
    mid = current_milestone(cfg)
    return (milestone_version(cfg, mid) or None) if mid is not None else None


def graded_release(cfg: PmConfig) -> tuple[str | None, str]:
    """(the version `[pm] version_file` must equal, or None; why not) — R5's
    question, and R5's only.
    """
    order = declared_order(cfg)
    if not order:
        return None, 'the plan declares no `order`'
    if cfg.version_at == VERSION_AT_START:
        mid = current_milestone(cfg)
        if mid is None:
            return None, ('every entry in `order` has shipped, or the next one '
                          'names no milestone in the tree')
        version = milestone_version(cfg, mid)
        if not version:
            return None, (f'{mid} is the current entry in `order` and declares '
                          f'no `version:` — `agentic-sdlc pm set {mid} version '
                          f'<x.y.z>` says which release it is')
        return version, ''
    shipped = [mid for mid in order if entry_is_shipped(cfg, mid)]
    if not shipped:
        return None, ('no entry in `order` has shipped yet, so there is no '
                      'previous release for the version file to carry')
    version = milestone_version(cfg, shipped[-1])
    if not version:
        return None, (f'{shipped[-1]} is the last shipped entry in `order` and '
                      f'declares no `version:`')
    return version, ''


def graded_release_accepts(cfg: PmConfig) -> tuple[list[str], str]:
    """Every value `[pm] version_file` may hold, and why, for [pm] version_at.

    `start` has one answer. **`ship` has two, and that is what bump-at-CLOSE
    means**: the release COMMIT moves the file, so between that commit and the
    status flip it correctly names a release that has not shipped. Found by
    running the belt — `version-sync` wanted 0.3.0 and R5 wanted 0.2.0 at the
    same instant, and neither was wrong. A file naming NEITHER still fails.
    """
    one, why = graded_release(cfg)
    if one is None:
        return [], why
    if cfg.version_at == VERSION_AT_START:
        return [one], ''
    nxt = current_release(cfg)
    return ([one] if nxt is None or nxt == one else [one, nxt]), ''


def release_milestone(cfg: PmConfig) -> tuple[Path | None, str]:
    """(the DOCUMENT of the milestone the current release belongs to, or None;
    why not). `order` answers with exactly one BY CONSTRUCTION — a position in
    a list is one place. It does NOT read `[pm] version_at`: conflating the two
    filed cost rows into a shipped milestone's ledger. The in-progress fallback
    covers a consumer who bumped the pin before adopting a plan.
    """
    mid = current_milestone(cfg)
    if mid is not None:
        found = milestone_file(cfg, mid)
        if found is not None:
            return found, ''
    live = in_progress_milestones(cfg)
    if len(live) == 1:
        # The milestone's DOCUMENT, like the branch above: a pooled tree has no
        # per-milestone directory, and every caller wants the grain, not a place.
        return live[0][2], ''
    order = declared_order(cfg)
    if not order:
        return None, (f'{cfg.rel(releases_file(cfg))} declares no `order`, so '
                      f'there is no current release to file against — '
                      f'`agentic-sdlc pm add {root_id(cfg)} <milestone-id>` '
                      f'writes the plan')
    # Read off the plan rather than asserted (review C4): an entry naming
    # nothing is stepped over, and "everything shipped" would be false.
    dangling = [mid for mid in order if entry_is_dangling(cfg, mid)]
    if dangling:
        return None, (f'{dangling[0]} is in {cfg.rel(releases_file(cfg))} '
                      f'`order` and names no milestone in the tree, so there '
                      f'is no ledger to file against — `agentic-sdlc pm '
                      f'roadmap` shows the plan against the tree')
    return None, (f'every release in {cfg.rel(releases_file(cfg))} has shipped, '
                  f'so there is no release in progress to file against')


def root_id(cfg: PmConfig) -> str:
    """The id the plan answers to — its own `id:`, or `roadmap`."""
    root = root_grain(cfg)
    return root.gid if root is not None else ROOT_ID


@dataclass(frozen=True)
class Sequence:
    """One container's `order` against the children it holds — THREE numbers,
    each a different fact (rule 4): `dangling` names a grain the tree HAS and
    this parent does not hold (drift); `unverifiable` names no grain at all (a
    retired one looks the same); `unsequenced` is a child nobody has placed."""

    dangling: list[str]
    unverifiable: list[str]
    unsequenced: list[str]


def sequence_census(cfg: PmConfig, parent: Grain,
                    index: dict[str, Grain] | None = None) -> Sequence:
    """`parent`'s `order` graded against the children bound to it. A caller
    grading MANY parents passes the index it already walked."""
    index = grain_index(cfg) if index is None else index
    held = {g.gid for g in contained(cfg, parent, index)}
    declared = parent.list_field(ORDER_KEY)
    return Sequence(
        dangling=[gid for gid in declared
                  if gid not in held and gid in index],
        unverifiable=[gid for gid in declared if gid not in index],
        unsequenced=sorted(gid for gid in held if gid not in declared))


def contained(cfg: PmConfig, parent: Grain,
              index: dict[str, Grain] | None = None) -> list[Grain]:
    """Every grain `parent` holds — its bound children, per `[pm.contains]`. A
    milestone names no parent (there is one root), so at that level membership
    IS the tree and the plan says which are scheduled."""
    found = grain_index(cfg) if index is None else index
    out: list[Grain] = []
    for kind in cfg.contains.get(parent.kind, ()):
        rootward = BINDS_TO.get(kind) is None
        out.extend(g for g in found.values() if g.kind == kind
                   and (rootward or g.binding == parent.gid))
    return out


def drift_dangling_record(cfg: PmConfig, fid: str) -> str | None:
    """D1 — a `reviewed:` pointer naming a file that is not there. An absent
    pointer is not a finding; only a dangling one is."""
    feature = grain(cfg, fid, GRAIN_FEATURE)
    if feature is None:
        return None
    pointer = feature.field('reviewed')
    if not pointer or pointer == 'null':
        return None
    target = record_path(cfg, pointer)
    if record_resolves(target):
        return None
    return f'reviewed: {pointer!r} resolves to nothing'


def drift_stalled(cfg: PmConfig, view: 'FeatureView') -> str | None:
    """D2 — every story finished but the feature still in `todo` (a forgotten
    flip). A feature at any `in_progress` state over finished stories has
    simply advanced.
    """
    if view.total == 0 or view.done_n != view.total:
        return None
    if category_of(cfg, GRAIN_FEATURE, view.status) == TODO:
        return f'all stories done, feature still {view.status}'
    return None


def drift_ahead_of_parent(cfg: PmConfig, child: str, parent: str) -> bool:
    """D5 — a story has left `todo` under a feature still in it: work started
    in one place and not the other. Asked of the categories, so it places in
    every vocabulary.
    """
    child_cat = category_of(cfg, GRAIN_STORY, child)
    parent_cat = category_of(cfg, GRAIN_FEATURE, parent)
    if child_cat is None or parent_cat is None:
        return False
    return parent_cat == TODO and child_cat != TODO


@dataclass
class FeatureView:
    """One feature plus the tallies every reader needs; `done_n` counts the
    `done` category through `holds`.

    `stories` are GRAINS, not paths: every reader of this view then asks each
    story what it SAYS rather than handing storage a file, and `doc_grain`
    keeps a story declaring no `id:` in the list, so `total` counts the same
    documents it always did.
    """
    fid: str
    status: str
    path: Path
    stories: list[Grain] = field(default_factory=list)
    done_n: int = 0

    @property
    def total(self) -> int:
        return len(self.stories)


def read_feature(cfg: PmConfig, ffile: Path) -> FeatureView:
    feature = doc_grain(ffile, GRAIN_FEATURE)
    view = FeatureView(
        fid=feature.field(FIELD_ID),
        status=feature.field(FIELD_STATUS),
        path=ffile,
        stories=story_grains(cfg, feature.field(FIELD_ID)),
    )
    finished = holds(cfg, GRAIN_STORY,
                     ((s.path, s.field(FIELD_STATUS)) for s in view.stories),
                     DONE_CATEGORY)
    view.done_n = finished.counted - len(finished.blockers)
    return view


# --- shared-doc headers -------------------------------------------------------
def header_of(path: Path) -> str:
    """The file's first non-blank line, stripped — its canonical header slot."""
    try:
        lines = frontmatter.document(path).lines
    except (OSError, UnicodeDecodeError):
        return ''
    for line in lines:
        if line.strip():
            return line.strip()
    return ''


# --- bug status vocabulary (D4) -----------------------------------------------
# A bug is never moved by this tool; what is checkable is D4's fact, a status
# outside the vocabulary — and every "is it open" reader tests a name, so a
# typo would pass in silence.
def _nested_bug_files(mdir: Path) -> list[Path]:
    return grain_docs(mdir / BUGS_DIR)


def bug_status_findings(cfg: PmConfig) -> tuple[list[tuple[Path, str]], int]:
    """(findings, bugs scanned) — every bug whose status the project never
    declared. The walk is recursive and case-insensitive on the extension, so
    the census cannot undercount silently.
    """
    out: list[tuple[Path, str]] = []
    scanned = 0
    # The POOL: a bug nobody has bound was counted and asked nothing.
    for bug in every_grain(cfg, GRAIN_BUG):
        scanned += 1
        bstat = bug.field(FIELD_STATUS)
        if category_of(cfg, GRAIN_BUG, bstat) is None:
            # The bug line's shape is grepped (rule 6), so it is kept verbatim.
            out.append((bug.path, f'bug status {bstat!r} is not in '
                                  f'({" ".join(flow_of(cfg, GRAIN_BUG).order)})'))
    return out, scanned


def every_grain(cfg: PmConfig, kind: str) -> list[Grain]:
    """Every grain of one kind in the tree, bound or not — through `doc_grain`,
    so a document declaring no `id:` is still in the census with an empty one
    rather than silently absent from it (rule 4)."""
    if is_pooled(cfg):
        return [doc_grain(path, kind) for path in pool_walk(cfg, kind)]
    if kind == GRAIN_BUG:
        return [b for m in milestones(cfg) for b in bug_grains(cfg, m.gid)]
    if kind == GRAIN_FEATURE:
        return [f for m in milestones(cfg) for f in feature_grains(cfg, m.gid)]
    return [s for m in milestones(cfg)
            for f in feature_grains(cfg, m.gid)
            for s in story_grains(cfg, f.field(FIELD_ID))]


def state_usage(cfg: PmConfig) -> dict[str, dict[str, int]]:
    """Per kind, how many grains hold each DECLARED state — zero included.

    D4 asks "is this word declared", never "is this word used", so a tree using
    two of eight states is indistinguishable, to every gate, from one using all
    eight. That is how a project adopted the conveyor as a CONFIG FIX and never
    noticed: four of its states appeared zero times across 85 grains, and every
    gate was green the whole time.
    """
    used: dict[str, dict[str, int]] = {
        kind: {state: 0 for state in flow.order}
        for kind, flow in cfg.flows.items()
    }

    def count(kind: str, status: str) -> None:
        bucket = used.get(kind)
        # An undeclared word is D4's finding, not this census's business.
        if bucket is not None and status in bucket:
            bucket[status] += 1

    # Bound or not: U1's claim is that a word is held nowhere in the TREE, and
    # a descent made that sentence false as soon as an unbound grain held it.
    for milestone in milestones(cfg):
        count(GRAIN_MILESTONE, milestone.status)
    for kind in (GRAIN_FEATURE, GRAIN_STORY, GRAIN_BUG):
        for found in every_grain(cfg, kind):
            count(kind, found.field(FIELD_STATUS))
    return used


def undeclared_status(cfg: PmConfig, kind: str, status: str) -> str | None:
    """D4's one sentence: the word, and the words the project did declare; None
    when `status` is in some category. One wording for every grain kind.
    """
    if category_of(cfg, kind, status) is not None:
        return None
    return (f'status {status!r} not in '
            f'({" ".join(flow_of(cfg, kind).order)})')


# --- ready: a stamp, and what `check pm` says about an empty one -------------
# `ready` is one command, `pm <kind> ready <id>`; what leaving `todo` means is
# a `check pm` WARNING, never a gate. Asked of the category: order within
# `todo` is presentation, and an undeclared word is D4's finding, not asked.
def left_todo(cfg: PmConfig, kind: str, status: str) -> bool:
    """True when `status` is declared for `kind` and its category is not `todo`."""
    category = category_of(cfg, kind, status)
    return category is not None and category != TODO


# The three sections `pm new` scaffolds and this reads, spelled once beside the
# templates' headings.
ACCEPTANCE_HEADING = 'Acceptance criteria'
SHIP_HEADING = 'Ship criterion'
# The anti-bloat contract: how many cases a feature should cost, named before it
# is built and compared after. Every feature template carries it and nothing had
# ever checked it was filled in — a contract nobody verifies is a suggestion.
PROOF_HEADING = 'Proof budget'

_HEADING = re.compile(r'^(#{1,2})[ \t]+(.*?)[ \t]*$')


def section_lines(text: str, heading: str) -> list[str] | None:
    """The lines under `## <heading>`, up to the next heading; None when the
    heading is absent, which is a different sentence from "empty"."""
    return section_lines_in(frontmatter._split(text), heading)


def section_lines_in(lines: Sequence[str], heading: str) -> list[str] | None:
    """`section_lines` over lines already read — the body of one parse."""
    start = None
    for i, line in enumerate(lines):
        m = _HEADING.match(line)
        if m is None:
            continue
        if start is None:
            if len(m.group(1)) == 2 and m.group(2) == heading:
                start = i + 1
        else:
            return lines[start:i]
    return None if start is None else lines[start:]


def section_is_empty(lines: list[str]) -> bool:
    """True when nothing but blank lines and HTML comments is under it — the
    template's own prompt is not content."""
    in_comment = False
    for line in lines:
        rest = line
        while rest:
            if in_comment:
                end = rest.find('-->')
                if end < 0:
                    rest = ''
                    break
                in_comment = False
                rest = rest[end + 3:]
                continue
            stripped = rest.strip()
            if not stripped:
                break
            if stripped.startswith('<!--'):
                in_comment = True
                rest = stripped[4:]
                continue
            return False
    return True


def empty_section(path: Path, heading: str) -> str | None:
    """'' when `## <heading>` is present and written; else why it is not."""
    lines = section_lines_in(frontmatter.document(path).lines, heading)
    if lines is None:
        return f'has no `## {heading}` section'
    if section_is_empty(lines):
        return f'has an empty `## {heading}`'
    return None


# --- appending a decision heading (`pm decide`) -------------------------------
# The verb stamps the date and the ordinal, the two things a hand-written
# heading gets wrong, and imposes no field schema.
_ENTRY_ORDINAL = re.compile(r'^##[ \t]+([A-Za-z]{1,4})(\d+)\b')
DECISION_PREFIX = 'D'


def next_entry_id(text: str) -> str:
    """The next ordinal for this log, from the ids the log itself holds: the
    prefix follows the last id-shaped heading, and numbering is per file by
    design.
    """
    seen = [m for m in (_ENTRY_ORDINAL.match(line) for line in frontmatter._split(text)) if m]
    if not seen:
        return f'{DECISION_PREFIX}1'
    prefix = seen[-1].group(1)
    highest = max(int(m.group(2)) for m in seen if m.group(1) == prefix)
    return f'{prefix}{highest + 1}'


def append_heading(text: str, eid: str, when: str, title: str) -> str:
    """`text` with one `## <id> — <date> — <title>` heading appended; the em
    dash is what `next_entry_id` and every log already use."""
    eol = '\r\n' if '\r\n' in text else '\n'
    body = text
    if body and not body.endswith(('\n', '\r')):
        body += eol
    if body and not body.endswith(eol * 2):
        body += eol
    return body + f'## {eid} — {when} — {title}{eol}'
