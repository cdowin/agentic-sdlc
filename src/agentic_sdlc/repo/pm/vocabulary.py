"""What a project DECLARES, and `PmConfig`, which reads it out of `[pm]`.

The categories and the state words, the rule ids, the document slots; a declaration of the wrong shape is refused by name.

`[pm]` in devkit.toml, under hard rule 5: every gate key has a stock default,
the flow (`[pm.states.<kind>]`) has none and `pm init` writes it. Every question
is asked of a status's category (`holds`), every move checked by `move_defect`,
and no state word is spelled outside the seed (`tests/test_pm_flow.py`).

It reads `devkit.toml` and opens nothing else: no grain, no pool, no walk, no
document — `core.config` and `core.project` are the only modules it imports, and
`CONFIG_IMPORT_ALLOWLIST` names it for that. What a TREE CONTAINS is
`inventory.py`, which imports this module and is never imported by it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from agentic_sdlc.core.project import load_config, repo_root
from agentic_sdlc.core.config import (ConfigError, config_section,
                                      heading_tuple, kind_tables,
                                      line_prefixes, relpath,
                                      section_declared, str_tuple,
                                      str_tuple_table, text)
from agentic_sdlc.repo import vehicle

# The verb that writes the flow, as every refusal below names it.
INIT_COMMAND = vehicle.command('pm', 'init')

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
# A milestone's dispatch mode: one builder at a time on its `branch:`, or one
# worktree per builder merging back into it. Empty or absent is serial.
FIELD_MODE = 'mode'
MODE_SERIAL = 'serial'
MODE_PARALLEL = 'parallel'
MODES = (MODE_SERIAL, MODE_PARALLEL)

# A milestone that changes contracts the plans AHEAD of it were written
# against opts in, per milestone, to a forward reconcile (#92). Absent or empty
# declares nothing; any other word is refused by name (rule 9).
FIELD_RECONCILE = 'reconcile'
RECONCILE_FORWARD = 'forward'
RECONCILE_VALUES = (RECONCILE_FORWARD,)

# The ROOT is a container like any other: `releases.md` declares `id:`/`kind:`
# and holds an `order` of milestone ids. Not a FLOW kind — nothing moves it, so
# it declares no states and has no status.
ROOT_KIND = 'roadmap'
ROOT_ID = 'roadmap'
CONTAINER_KINDS = (ROOT_KIND, *FLOW_KINDS)

# The child's field that names its parent, per kind. **Membership is the
# child's field** — the northstar, as one mapping.
BINDS_TO = {GRAIN_FEATURE: (GRAIN_MILESTONE, GRAIN_MILESTONE),
            GRAIN_STORY: (GRAIN_FEATURE, GRAIN_FEATURE),
            GRAIN_BUG: (GRAIN_MILESTONE, GRAIN_MILESTONE)}

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
# THIS TUPLE IS "STOCK-ON", in so many words: it is what runs with no `[pm]
# checks`, and a declared roster that omits one of these is named on
# `check pm`'s ROSTER line (#19). `check pm --help` states it and a test holds
# the page to it.
DEFAULT_CHECKS = ('D1', 'D2', 'D4', 'D5', 'D6', 'D11', 'D12', 'U1',
                  'V1', 'V4', 'V5', 'V7')
# The USAGE family: what the tree DOES with the vocabulary (U1) and the
# capabilities (U2-U4) it declared, as opposed to whether a word is declared at
# all (D4). A NEW LETTER on purpose — see RETIRED_CHECKS['D7'] below. U1 alone
# is STOCK-ON (it is in DEFAULT_CHECKS above); U2-U4 are OPT-IN and run only
# when `[pm] checks` names them — the seed says the same, and a WARN cannot
# redden anyone; a tree that wires nothing stays quiet either way (0.4.0/D5).
USAGE_CHECKS = ('U1', 'U2', 'U3', 'U4')  # named for the family
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
          'D11 is stock-on, and a declared `[pm] checks` runs only what it '
          'names; the opt-out for one child is `pm remove <parent> <child>`, '
          'which returns it to its pool',
    'D8': 'became R5 — the version file is graded against the CURRENT entry in '
          'pm/roadmap/releases.md `order` ([pm] version_at selects which), not '
          'against the id of whichever milestone happens to be in progress. '
          'D8 welded the version to the id; `version:` separates them',
    'U5': 'retired in 2.0.0 with the arrival questions it counted. A status '
          'write asks nothing and records the status alone, so there is no '
          'disposition to be missing',
}
# The rule a retired id's question moved INTO, where there is one. "Remove D3"
# alone was followed to the letter and left a declared roster with no
# containment at all (#19), so the message names the replacement. D7 and the V
# retirements have none: U1 took a new letter precisely so D7 is not one.
RETIRED_SUCCESSORS = {'D3': 'D11', 'D8': 'R5'}


def retired_check_message(check: str) -> str:
    """The ONE refusal for a retired rule id in `[pm] checks` — both config
    readers print it, so the two cannot drift into different advice."""
    successor = RETIRED_SUCCESSORS.get(check)
    act = (f'Removing it alone turns the question off: replace {check} with '
           f'{successor} in the list'
           if successor else 'Remove it from the list')
    return (f'[pm] checks names {check}, which was retired — '
            f'{RETIRED_CHECKS[check]}. {act}.')

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
# The forward-reconcile record: minted on demand by `pm new reconcile`, read by
# `check pm`, which warns when an opted-in milestone has none.
RECONCILE_FILE_NAME = 'reconcile.md'
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
                            REVIEW_FILE_NAME, RECONCILE_FILE_NAME)
FEATURE_FILE_SLOTS = (FEATURE_DOC,)
# No handoff.md: a feature is never picked up cold on its own.
FEATURE_OPTIONAL_SLOTS = (DECISION_FILE_NAME, REVIEW_FILE_NAME)

SLOT_TEMPLATE = {
    MILESTONE_DOC: GRAIN_MILESTONE, FEATURE_DOC: GRAIN_FEATURE,
    'handoff.md': 'handoff', 'decisions.md': 'decisions',
    RECONCILE_FILE_NAME: 'reconcile',
}

# The instruction line each shared doc opens with, restored by `pm new`: a
# file's own first line is the one channel that reaches a dispatched subagent.
SLOT_HEADER = {
    'decisions.md': ('Append with `'
                     + vehicle.command('pm', 'decide', vehicle.Slot('<grain-id>'))
                     + '` — never by hand; the command stamps the date and the '
                     'next ordinal.'),
    'handoff.md': 'Cold-start only. Everything derivable is a command — never '
                  'restate `pm status`, `git log` or `pm ledger report`.',
    RECONCILE_FILE_NAME: ('Forward reconcile record. `'
                          + vehicle.command('dispatch', '--reconcile',
                                            vehicle.Slot('<milestone-id>'))
                          + '` renders every section.'),
}

# Wordings that shipped before and still open real documents. RECOGNISED, never
# written: `_header_wanted` treats any known header as present, so rewording an
# entry above can neither stack a second line onto an existing doc nor red a
# consumer's tree on upgrade day.
RETIRED_SLOT_HEADERS = frozenset({
    'Cold-start only. Never restate what `pm status` computes.',
    # 0.8.0: the command is spelled through the stock wiring's vehicle.
    'Append with `agentic-sdlc pm decide <grain-id>` — never by hand; the '
    'command stamps the date and the next ordinal.',
    # 2.0.0: `release` reads no record, and `pm ready-for` is retired.
    'Forward reconcile record. `release` and `pm ready-for milestone` read '  # retired
    'every section; `make sdlc ARGS=\'dispatch --reconcile <milestone-id>\'` '
    'renders the pass.',
})

KNOWN_SLOT_HEADERS = frozenset(SLOT_HEADER.values()) | RETIRED_SLOT_HEADERS


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
    # The prefix the agent-worktree branches live under (#52). A milestone
    # `branch:` under it reads, by name, as an agent's branch, so `pm set
    # <ms> branch` and the milestone's START refuse it. Empty declares no
    # agent prefix and refuses nothing.
    agent_branch_prefix: str = 'feat/'
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
    # `[pm.templates.<kind>] extra_sections`: headings `templates.load`
    # appends to whichever template it read. A kind with none is absent.
    extra_sections: dict[str, tuple[str, ...]] = field(default_factory=dict)
    # `[pm.required.<kind>] lines`: the line prefixes a grain body carries. A
    # WORKFLOW key — nothing behind it; a kind that declares none is absent.
    required_lines: dict[str, tuple[str, ...]] = field(default_factory=dict)

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
            'just its frontmatter defaults). To add sections only, declare '
            '[pm.templates.<kind>] extra_sections = ["<heading>"] instead: '
            'nothing is copied, and every kit template change still reaches '
            'you')

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
    extra_sections = _load_extra_sections(sect)
    required_lines = _load_required_lines(sect)

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
        agent_branch_prefix=text(sect, 'pm', 'agent_branch_prefix', 'feat/'),
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
        extra_sections=extra_sections,
        required_lines=required_lines,
    )


def version_source() -> tuple[str, str]:
    """(`[pm] version_file`, `[pm] version_pattern` or '' when undeclared),
    for a reader that needs no flow declared (`install-ci` renders the semver
    gate from them, #51)."""
    sect = config_section('pm')
    declared = 'version_pattern' in sect
    return (text(sect, 'pm', 'version_file', 'pyproject.toml'),
            text(sect, 'pm', 'version_pattern', r'^version = "(.*)"$')
            if declared else '')


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


def _load_extra_sections(sect: dict) -> dict[str, tuple[str, ...]]:
    """`[pm.templates.<kind>] extra_sections`, per kind that declares any.

    Stock empty. The section name is computed, so `tests/test_config_seed.py`
    expands it over FLOW_KINDS in `PER_KIND_READS`.
    """
    out: dict[str, tuple[str, ...]] = {}
    for kind, kind_sect in kind_tables(sect, 'pm', 'templates',
                                       FLOW_KINDS).items():
        unknown = sorted(k for k in kind_sect if k != 'extra_sections')
        if unknown:
            raise ConfigError(f'[pm.templates.{kind}] names {", ".join(unknown)}'
                              f' — the one key it declares is extra_sections')
        names = heading_tuple(kind_sect, f'pm.templates.{kind}',
                              'extra_sections', ())
        if names:
            out[kind] = names
    return out


# `[pm.required.<kind>] lines` (#80, #91, #96): the line prefixes a grain body
# carries. A WORKFLOW key (hard rule 5): no stock default and nothing behind
# it, so absent means nothing is required and nothing is read.
REQUIRED_KEY = 'required'
REQUIRED_LINES_KEY = 'lines'


def _load_required_lines(sect: dict) -> dict[str, tuple[str, ...]]:
    """`[pm.required.<kind>] lines`, per kind that declares any. A key other
    than `lines` is refused by name: a typo there would require nothing and
    look declared (the M1 shape `_load_extra_sections` refuses too)."""
    out: dict[str, tuple[str, ...]] = {}
    for kind, kind_sect in kind_tables(sect, 'pm', REQUIRED_KEY,
                                       FLOW_KINDS).items():
        where = f'pm.{REQUIRED_KEY}.{kind}'
        unknown = sorted(k for k in kind_sect if k != REQUIRED_LINES_KEY)
        if unknown:
            raise ConfigError(f'[{where}] names {", ".join(unknown)} — the one '
                              f'key it declares is {REQUIRED_LINES_KEY}')
        prefixes = line_prefixes(kind_sect, where, REQUIRED_LINES_KEY, ())
        if prefixes:
            out[kind] = prefixes
    return out


def required_key(kind: str) -> str:
    """The key a required-line message names, spelled once."""
    return f'[pm.{REQUIRED_KEY}.{kind}] {REQUIRED_LINES_KEY}'


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
            f'never chose. Run `{INIT_COMMAND}` to write the rest.')
    return out


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
            f'`{INIT_COMMAND}` to write them; it appends to a '
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
        'feature\'s own `order:` list, written by '
        f'`{vehicle.command("pm", "add", vehicle.Slot("<feature-id>"), vehicle.Slot("<story-id>"))}`'
        ', at `--position N`, `--before <id>` or `--after <id>` inside the '
        'quotes',
    'review_slug_fallback': 'a review record is the `reviewed:` pointer and '
                            'nothing else — a record found by glob was the '
                            'engine guessing which file a review was',
    # 2.0.0: a status write prints what it wrote and nothing else.
    'pressure': 'the open-work census a write printed was removed in 2.0.0 — '
                '`pm status` and `pm list` report the tree when you ask',
    'breadcrumbs': 'the `next:` and `have:` lines a write printed were '
                   'removed in 2.0.0 — a write prints what it wrote and '
                   'nothing else',
    'arrival_gates': 'a move no longer runs make targets (2.0.0) — the '
                     'builder runs `[verify] spot` and the integrator proves '
                     'the batch once',
    'wip': 'read only by the open-work census, removed in 2.0.0 — '
           '`pm list --category in_progress` counts what is open',
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

# `[pm.<name>.*]` sub-tables a release retired, spelled as tables because the
# bare name is an English word and a table is what a consumer declared.
RETIRED_TABLES = {
    'arrive': 'the arrival questions were removed in 2.0.0 — a status write '
              'asks nothing, takes no answer flag (`--by`, `--skip`) and '
              'records the status alone',
}


def retired_table_message(name: str) -> str:
    """The ONE refusal for a retired `[pm.<name>.*]` table — both config
    readers print it."""
    return (f'[pm.{name}.*] was retired and does nothing — '
            f'{RETIRED_TABLES[name]}. Remove the tables.')


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
            f'rule 5). Run `{INIT_COMMAND}` to write them; it appends to '
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
    probe(lambda: text(section, 'pm', 'agent_branch_prefix', 'feat/'))
    probe(lambda: _load_extra_sections(section))
    probe(lambda: _load_required_lines(section))
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
            "the markdown. To add sections only, declare "
            "[pm.templates.<kind>] extra_sections = [\"<heading>\"] instead: "
            "nothing is copied, and every kit template change still reaches "
            "you")

    # Read off the section rather than off a config that may not have loaded
    # (review D3).
    raw_checks = section.get('checks')
    named = tuple(c for c in raw_checks
                  if isinstance(c, str)) if isinstance(raw_checks, list) else DEFAULT_CHECKS
    for check in named:
        if check in RETIRED_CHECKS:
            add(retired_check_message(check))
    unknown = [c for c in named
               if c not in KNOWN_CHECKS and c not in RETIRED_CHECKS]
    if unknown:
        add(f'[pm] checks names unknown rule(s) {", ".join(unknown)} — '
            f'known rules are {" ".join(KNOWN_CHECKS)}')
    for key, why in RETIRED_KEYS.items():
        if key in section and key not in VOCABULARY_KEYS:
            add(f'[pm] {key} was retired and does nothing — {why}. '
                f'Remove the key.')
    for name in RETIRED_TABLES:
        if name in section:
            add(retired_table_message(name))
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
            out.append(retired_check_message(check))
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
    for name in RETIRED_TABLES:
        if name in section:
            out.append(retired_table_message(name))
    # `sect` is the `[pm]` table a caller may inject; a retired section is read
    # from the file either way.
    for name, why in RETIRED_SECTIONS.items():
        if section_declared(name):
            out.append(f'[{name}] was retired and does nothing — {why}. '
                       f'Remove the section.')
    return out


# --- [repo_hygiene] mainline, the one value this reads outside [pm] ----------
def mainline_branch() -> str:
    """D10's trunk name — `[repo_hygiene] mainline`, `origin/`-stripped, since
    a milestone's authored `branch:` is never remote-qualified."""
    sect = config_section('repo_hygiene')
    value = text(sect, 'repo_hygiene', 'mainline', 'origin/main')
    if value.startswith('origin/'):
        value = value[len('origin/'):]
    return value
