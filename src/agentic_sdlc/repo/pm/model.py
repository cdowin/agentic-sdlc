"""model.py — the PM-tree invariants, single-sourced for the CLI and the gate.

`[pm]` in devkit.toml; every gate key has a stock default, the flow
(`[pm.states.<kind>]`) has none — `pm init` writes it. Every question is
asked of a status's category (`holds`), every move checked by
`move_defect`, and no state word is spelled outside the seed
(`tests/test_pm_flow.py`).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from agentic_sdlc.core import apply, walk
from agentic_sdlc.core.walk import Kind, SkipReason, Walk
from agentic_sdlc.core.project import load_config, repo_root
from agentic_sdlc.core.config import (ConfigError, config_section, relpath,
                                       section_declared, flag, str_tuple,
                                       str_tuple_table, text)

# --- the flow a project DECLARES ----------------------------------------------
# The closed set, and the engine's whole opinion about states: three categories
# answering "does work remain". `obe` is a `done` state — delivered-vs-not is
# an outcome on a different axis, not a fourth category.
TODO = 'todo'
IN_PROGRESS = 'in_progress'
DONE_CATEGORY = 'done'
CATEGORIES = (TODO, IN_PROGRESS, DONE_CATEGORY)

# Per kind, so a bug's flow is one more declaration rather than a special case.
FLOW_KINDS = ('milestone', 'feature', 'story', 'bug')


@dataclass(frozen=True)
class Flow:
    """One grain kind's declared states and their categories, read from
    `[pm.states.<kind>]` every run with no runtime fallback. `order` is
    category-major, then the project's own list order; no gate keys on it.
    """

    kind: str
    by_category: dict[str, tuple[str, ...]]
    category_of: dict[str, str]

    @property
    def order(self) -> tuple[str, ...]:
        return tuple(st for cat in CATEGORIES
                     for st in self.by_category.get(cat, ()))

    def category(self, status: str) -> str | None:
        """This state's category, or None when the project never declared it
        (the D4 drift) — never a guess.
        """
        return self.category_of.get(status)


# The seed: what `init` materialises into devkit.toml, not a fallback the
# reader assumes. It is the only place in this package a state word is spelled;
# each kind seeds only the states its belt writes, plus `obe` in `done`
# wherever work can be abandoned. `LIFECYCLE`, `BUILDING` and `REVIEWING`
# survive for the frozen dispatch-snapshot keys in `pm/cli.py` (D7).
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
    'milestone': dict(_LIFECYCLE_CATEGORIES),
    'feature': {TODO: LIFECYCLE[:2], IN_PROGRESS: LIFECYCLE[2:4],
                DONE_CATEGORY: LIFECYCLE[6:] + ('obe',)},
    'story': {TODO: LIFECYCLE[:2], IN_PROGRESS: LIFECYCLE[2:3],
              DONE_CATEGORY: LIFECYCLE[6:] + ('obe',)},
    'bug': {TODO: ('open',), IN_PROGRESS: ('fixed',),
            DONE_CATEGORY: ('closed',)},
}


def render_seed(flows=None) -> str:
    """The seed as the TOML `init` writes — one renderer for the fresh-tree
    and append paths. Live TOML, not commentary: there is no runtime
    fallback behind it.
    """
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
    the input, exit 2, never a finding.
    """
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
DEFAULT_CHECKS = ('D1', 'D2', 'D3', 'D4', 'D5', 'D6',
                  'V1', 'V2', 'V3', 'V4', 'V5')
# D7 (a declared state no grain has ever held) is OPT-IN, like every other
# flow-shaped rule. It is a WARN and could not redden anyone, but stock-on it
# adds three lines to every consumer's `check pm` output, and those line shapes
# are grepped (rule 6). The place a project MEETS this fact is `pm init`, which
# prints the ladder against the tree unconditionally; D7 is how a project that
# wants it kept visible afterwards asks for that.
USAGE_CHECKS = ('D7',)
# D9/D10 read an `in_progress` milestone's `branch:`; D8 read its id as the
# version and RETIRED into R5, which grades against a position in `order`.
FLOW_CHECKS = ('D9', 'D10')
# The release family: the plan and the tree held to each other. Opt-in, because
# a tree with no plan yet has nothing for them to grade.
RELEASE_CHECKS = ('R1', 'R2', 'R3', 'R4', 'R5', 'R6')
# V1-V5 are ON: an unsatisfied one is a malformed tree. V6 is opt-in: a
# generated view going stale is not a defect in the tree.
VALIDATE_CHECKS = ('V1', 'V2', 'V3', 'V4', 'V5', 'V6')
KNOWN_CHECKS = tuple(dict.fromkeys(
    DEFAULT_CHECKS + USAGE_CHECKS + FLOW_CHECKS + RELEASE_CHECKS
    + VALIDATE_CHECKS))

# A rule id that WAS shipped and is not any more. Reported by name, never as
# "unknown": a consumer whose config still lists it is told where the rule
# went, rather than being silently ungated by a typo-shaped message.
RETIRED_CHECKS = {
    'D8': 'became R5 — the version file is graded against the CURRENT entry in '
          'pm/roadmap/releases.md `order` ([pm] version_at selects which), not '
          'against the id of whichever milestone happens to be in progress. '
          'D8 welded the version to the id; `version:` separates them',
}

ARCHIVE_DIR_NAME = 'zz_archive'

# --- the canonical grain slots ------------------------------------------------
# One shape, every grain, all lowercase. `handoff.md` and `bugs/` are
# milestone-only; every shared doc is optional and minted on first write; there
# are no directory slots, since git stores no empty directory.
DECISION_FILE_NAME = 'decisions.md'
REVIEW_FILE_NAME = 'review.md'
HANDOFF_FILE_NAME = 'handoff.md'
# The id<->path convention is this module's, so the names are spelled here
# once.
# The plan: `order` is a declared sequence of versions, not a sort. It lives in
# the roadmap dir beside the milestones it sequences, and it is grain-shaped so
# the byte-preserving frontmatter writer can edit it (0.3.0).
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
# Retired in 0.3.0: `pm roadmap` derives the live index and `releases.md`
# `order` carries what outlives a retired milestone. The NAME stays so a tree
# that still has the file is recognised rather than walked as a grain.
ROADMAP_DOC = 'ROADMAP.md'
# The slot directories, spelled once: a grain's kind is read from which slot
# its document sits in.
FEATURES_DIR = 'features'
STORIES_DIR = 'stories'
BUGS_DIR = 'bugs'

# Permitted, never required, minted on first write; an absent one means nothing
# was recorded, which is not a finding.
# What a grain MUST carry: its own frontmatter file, and nothing else.
MILESTONE_FILE_SLOTS = (MILESTONE_DOC,)
MILESTONE_OPTIONAL_SLOTS = (HANDOFF_FILE_NAME, DECISION_FILE_NAME,
                            REVIEW_FILE_NAME)
FEATURE_FILE_SLOTS = (FEATURE_DOC,)
# No handoff.md: a feature is never picked up cold on its own.
FEATURE_OPTIONAL_SLOTS = (DECISION_FILE_NAME, REVIEW_FILE_NAME)

# slot -> the template that mints it.
SLOT_TEMPLATE = {
    MILESTONE_DOC: 'milestone', FEATURE_DOC: 'feature',
    'handoff.md': 'handoff', 'decisions.md': 'decisions',
}

# The instruction line each shared doc opens with, restored by `pm new`: a
# file's own first line is the one channel that reaches a dispatched subagent.
SLOT_HEADER = {
    'decisions.md': 'Append with `agentic-sdlc pm decide <grain-id>` — never by '
                    'hand; the command stamps the date and the next ordinal.',
    'handoff.md': 'Cold-start only. Never restate what `pm status` computes.',
}


def dir_entries(path: Path) -> dict[str, str]:
    """{exact name: 'file'|'dir'} for one directory — exact names, through
    `core.walk.entries`.
    """
    return walk.entries(path)


def case_variants(entries: dict[str, str], name: str) -> list[str]:
    """Names in `entries` that differ from `name` only by case (excluding it)."""
    low = name.lower()
    return sorted(n for n in entries if n != name and n.lower() == low)


@dataclass(frozen=True)
class PmConfig:
    root: Path
    roadmap_dir: str = 'pm/roadmap'
    review_dir: str = 'docs/reviews'
    story_ordinal_prefix: bool = False
    # The declared order per kind, copied out by `load`; empty when the tree
    # declared nothing, which `flow_of` refuses. Never read from the retired
    # `[pm] <kind>_states`.
    milestone_states: tuple[str, ...] = ()
    feature_states: tuple[str, ...] = ()
    story_states: tuple[str, ...] = ()
    bug_states: tuple[str, ...] = ()
    checks: tuple[str, ...] = DEFAULT_CHECKS
    # R5 and `version-sync`: where the shipped version lives, and the line
    # that carries it. Both halves are configurable.
    template_dir: str = ''
    version_file: str = 'pyproject.toml'
    version_pattern: str = r'^version = "(.*)"$'
    # R5 only: which milestone in the declared `order` the version file is
    # graded against. Never a parse — a position in a list.
    version_at: str = VERSION_AT_START
    # What the project declared, per kind; empty is the absence itself, which
    # `flow_of` turns into a refusal naming the fix (hard rule 5: a workflow
    # ships no default).
    flows: dict[str, Flow] = field(default_factory=dict)

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

    flows = _load_flows(sect)

    return PmConfig(
        root=repo_root(),
        # The three path keys go through `relpath`, not `text`: an absolute or
        # `../` value would move the whole PM surface outside the checkout
        # (hard rule 8).
        roadmap_dir=relpath(sect, 'pm', 'roadmap_dir', 'pm/roadmap'),
        review_dir=relpath(sect, 'pm', 'review_dir', 'docs/reviews'),
        story_ordinal_prefix=flag(sect, 'pm', 'story_ordinal_prefix', False),
        milestone_states=_order_of(flows, 'milestone'),
        feature_states=_order_of(flows, 'feature'),
        story_states=_order_of(flows, 'story'),
        bug_states=_order_of(flows, 'bug'),
        checks=checks,
        template_dir=relpath(sect, 'pm', 'template_dir', ''),
        version_file=text(sect, 'pm', 'version_file', 'pyproject.toml'),
        version_pattern=version_pattern,
        version_at=version_at,
        flows=flows,
    )


def reload() -> PmConfig:
    """`load()` against the file as it is NOW, caches dropped.

    For the one caller that WROTE devkit.toml in this process and then has to
    read it back: `pm init` appends the flow and then reports what it means
    against the tree. The cache lives in `core.project`, and this module is the
    one place in `repo/` that may reach it — every other reader goes through the
    guards in `core/config.py`.
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
    never the seed; malformed is exit 2 before anything else happens.
    """
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


# --- the engine's two verbs ---------------------------------------------------
# The engine's two verbs: `move` (is the target a declared state?) and `holds`
# (are they all in the category, and who is not?). They are functions rather
# than a convention because two call sites of one convention once disagreed
# about whether an `obe` story was finished (D6).


@dataclass(frozen=True)
class Held:
    """`holds`' answer: whether they are all there, and who is not — the half
    a caller prints.
    """

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
    The caller supplies the pairs, because scope is the caller's question.
    An undeclared status is a blocker carrying the word, never a silent
    pass (rule 4).
    """
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
    whole opinion is "is the target declared?"; there is no edge graph,
    since a `sed` reaches any state anyway, and D3/D4/D5 check the end
    state.
    """
    flow = flow_of(cfg, kind)
    if to_state in flow.category_of:
        return ''
    return (f'{to_state!r} is not a {kind} state — this project declares '
            f'{", ".join(flow.order)} in [pm.states.{kind}]')


# The workflow refusal, in one place; the gates never come through here (hard
# rule 5).
def flow_of(cfg: PmConfig, kind: str) -> Flow:
    """This grain kind's declared flow, or exit 2 naming the command that
    writes it — a command copies correctly where forty lines of TOML do
    not.
    """
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

    Read straight off `[pm.states.*]` rather than off a loaded config, because
    a config that failed to load for some OTHER reason must still be able to
    report this one — that ordering is the whole feature.
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

    A real adoption is wrong in more than one way at once, and reporting one
    defect per run makes the consumer pay a round trip to learn the next. The
    ORDER is the point: a retired key is cosmetic and a missing flow stops
    every work-moving verb in the package, and the tree that motivated this was
    told about the retired key.
    """
    section = config_section('pm') if sect is None else sect
    out: list[str] = []

    flow = missing_flow_defect(section)
    if flow:
        out.append(flow)

    for key in VOCABULARY_KEYS:
        if key in section:
            out.append(f'[pm] {key} was retired and is refused — '
                       f'{RETIRED_KEYS[key]}. Remove the key.')

    # Everything `load()` refuses, collected rather than raised at the first.
    try:
        load()
    except ConfigError as err:
        said = str(err)
        if said not in out and not any(said in seen for seen in out):
            out.append(said)
    else:
        # `load()` succeeded, so the stale-rule and retired-key sweep is the
        # only reader left with anything to say.
        try:
            out.extend(m for m in config_complaints(load(), section)
                       if m not in out)
        except ConfigError:
            pass
    return out


def config_complaints(cfg: PmConfig, sect: dict | None = None) -> list[str]:
    """Everything `[pm]` names that this package does not ship — a stale rule
    id or a retired key — empty when clean. Raised by the gates, not by
    `load()`, so a pin bump cannot take `pm status` down.
    """
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


# --- frontmatter --------------------------------------------------------------
# Split on '\n' only: `splitlines()` also breaks on U+2028, U+2029, form feed
# and lone CR, and would rewrite them on join (rule 3).
_FENCE = re.compile(r'^---[ \t]*\r?$')


def _split(text: str) -> list[str]:
    return text.split('\n')


# `newline=''` disables universal-newline translation both ways, so a CRLF file
# stays CRLF; `Path.read_text` only gained the parameter in 3.13.
def read_raw(path: Path) -> str:
    with path.open('r', encoding='utf-8', newline='') as fh:
        return fh.read()


def write_raw(path: Path, text: str) -> None:
    """The grain-file write, through `core.apply` with the same disabled
    newline translation; a failure comes back as `OSError`.
    """
    apply.raise_on_error(apply.write(path, text))


def _eol(line: str) -> str:
    """The CR half of a CRLF terminator, so a rewritten line keeps the file's
    convention.
    """
    return '\r' if line.endswith('\r') else ''


def _fence_bounds(lines: list[str]) -> tuple[int, int] | None:
    """Index of the opening and closing `---` of the leading block, or None."""
    if not lines or not _FENCE.match(lines[0]):
        return None
    for i in range(1, len(lines)):
        if _FENCE.match(lines[i]):
            return 0, i
    return None


def field_of(path: Path, key: str) -> str:
    """Scalar value of `key` inside the leading frontmatter block, or '' —
    never from the prose body.
    """
    try:
        lines = _split(read_raw(path))
    except (OSError, UnicodeDecodeError):
        return ''
    bounds = _fence_bounds(lines)
    if bounds is None:
        return ''
    for line in lines[bounds[0] + 1:bounds[1]]:
        if line.startswith(f'{key}:'):
            # .strip() also removes the CRLF carriage return.
            return unquote(line[len(key) + 1:].strip())
    return ''


def unquote(value: str) -> str:
    """Strip the quotes a milestone id carries (`id: "0.28"` -> `0.28`)."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        return value[1:-1]
    return value


# A block-style list is the only non-scalar frontmatter this package reads:
# `order` is edited constantly and reordering is the main edit, so one entry per
# line keeps a diff showing what MOVED, where an inline `[a, b, c]` rewrites the
# whole line.
_LIST_ITEM = re.compile(r'^[ \t]+-[ \t]*(?P<value>.*?)[ \t]*\r?$')


def list_field_of(path: Path, key: str) -> list[str]:
    """Block-style list under `key` in the leading frontmatter, or [].

    `key:` must carry nothing but a comment on its own line; a scalar on it is
    a different shape and reads as no list at all, never as a one-element one.
    """
    try:
        lines = _split(read_raw(path))
    except (OSError, UnicodeDecodeError):
        return []
    bounds = _fence_bounds(lines)
    if bounds is None:
        return []
    open_i, close_i = bounds
    for i in range(open_i + 1, close_i):
        if not lines[i].startswith(f'{key}:'):
            continue
        rest = lines[i][len(key) + 1:].strip()
        if rest and not rest.startswith('#'):
            return []
        out: list[str] = []
        for line in lines[i + 1:close_i]:
            if not line.strip():
                # Spacing a long plan is the obvious thing a human does to it;
                # truncating there would drop every entry below the gap.
                continue
            m = _LIST_ITEM.match(line)
            if m is None:
                break
            out.append(unquote(m.group('value')))
        return out
    return []


def set_field(path: Path, key: str, value: str) -> bool:
    """Set-or-insert one frontmatter scalar, preserving every other byte;
    False without writing when there is no frontmatter block or the write
    fails. One key through `set_fields`.
    """
    return set_fields(path, {key: value})


def set_fields(path: Path, updates: dict[str, str]) -> bool:
    """Set-or-insert several frontmatter scalars in one read and one write, so
    a multi-key rewrite (`pm move`'s three) cannot land half (rule 3). Same
    per-key contract as `set_field`.
    """
    try:
        text = read_raw(path)
    except (OSError, UnicodeDecodeError):
        return False
    lines = _split(text)
    bounds = _fence_bounds(lines)
    if bounds is None:
        return False
    open_i, close_i = bounds
    for key, value in updates.items():
        for i in range(open_i + 1, close_i):
            if lines[i].startswith(f'{key}:'):
                lines[i] = f'{key}: {value}{_eol(lines[i])}'
                break
        else:
            lines.insert(close_i, f'{key}: {value}{_eol(lines[close_i])}')
            close_i += 1
    try:
        write_raw(path, '\n'.join(lines))
    except OSError:
        return False
    return True


def set_list_field(path: Path, key: str, values: list[str]) -> bool:
    """Rewrite the block list under `key`, preserving every other byte.

    The list-aware sibling to `set_field`. `order` is edited constantly — every
    ship, insertion and re-sequence — so this is the writer that has to be
    byte-honest: a diff that shows what MOVED is the whole reason the plan is a
    grain and not TOML.

    The file's own conventions are kept rather than normalised: the indent and
    the quote character come from the first item already there, so a hand-edited
    plan is not reformatted underneath its author. An empty `values` leaves the
    key with no items, which is a plan that declares nothing — never the key's
    deletion, because a caller that wanted the key gone would say so.
    """
    try:
        text = read_raw(path)
    except (OSError, UnicodeDecodeError):
        return False
    lines = _split(text)
    bounds = _fence_bounds(lines)
    if bounds is None:
        return False
    open_i, close_i = bounds

    key_i = None
    for i in range(open_i + 1, close_i):
        if lines[i].startswith(f'{key}:'):
            rest = lines[i][len(key) + 1:].strip()
            if rest and not rest.startswith('#'):
                # A scalar sits there. Rewriting it as a block would be this
                # writer deciding the file meant something else.
                return False
            key_i = i
            break

    indent, quote, eol = '  ', '"', ''
    if key_i is None:
        # A plan that has no `order` yet: mint the key at the end of the block.
        eol = _eol(lines[close_i])
        key_i = close_i
        head = [f'{key}:{eol}']
        tail_from = close_i
    else:
        eol = _eol(lines[key_i])
        end_i = key_i
        for j in range(key_i + 1, close_i):
            m = _LIST_ITEM.match(lines[j])
            if m is None:
                break
            if end_i == key_i:
                # Copy the file's own shape off its first item.
                raw = lines[j]
                indent = raw[:len(raw) - len(raw.lstrip(' \t'))]
                value = m.group('value')
                if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                    quote = value[0]
                else:
                    quote = ''
            end_i = j
        head = [lines[key_i]]
        tail_from = end_i + 1

    items = [f'{indent}- {quote}{v}{quote}{eol}' for v in values]
    rewritten = lines[:key_i] + head + items + lines[tail_from:]
    try:
        write_raw(path, '\n'.join(rewritten))
    except OSError:
        return False
    return True


# --- id <-> path --------------------------------------------------------------
# Milestone dirs carry a human suffix (`0.28-chronicle`); the id is the
# version, globbed active tree first, then the archive.
# Ids reach glob() as patterns, so an id must be a literal, never a pattern.
_GLOB_CHARS = set('*?[]!')


def id_is_literal(value: str) -> bool:
    return bool(value) and not (_GLOB_CHARS & set(value))


def segment_is_literal(value: str) -> bool:
    """One id segment the resolvers may join onto a directory — the resolution
    twin of `_check_slug`: no `.`/`..`/empty segment, no separator, no
    absolute path, no glob.
    """
    return (id_is_literal(value) and value not in ('.', '..')
            and not any(c in value for c in '/\\'))


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
    d = milestone_dir(cfg, mid)
    if d is None:
        return None
    f = d / MILESTONE_DOC
    return f if f.is_file() else None


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
    d = feature_dir(cfg, fid)
    if d is None:
        return None
    f = d / FEATURE_DOC
    return f if f.is_file() else None


_ORDINAL_STEM = re.compile(r'^[0-9][0-9]-(?P<slug>.*)$')


def story_slug_of(cfg: PmConfig, stem: str) -> str:
    """The id segment a story file named `stem` must carry — one rule for
    `story_file`, V2 and `pm new story`. The ordinal prefix sequences the
    build; it is not identity.
    """
    if not cfg.story_ordinal_prefix:
        return stem
    match = _ORDINAL_STEM.match(stem)
    return match.group('slug') if match is not None else stem


def story_file(cfg: PmConfig, sid: str) -> Path | None:
    """Resolve <milestone>/<feature-slug>/<story-slug> to its .md over
    `story_files`, the walk the gates use. Exact stem first, then the
    ordinal-prefixed form; two files at one precedence refuse.
    """
    mid, _, rest = sid.partition('/')
    fslug, _, sslug = rest.partition('/')
    if not fslug or not segment_is_literal(sslug):
        return None
    fdir = feature_dir(cfg, f'{mid}/{fslug}')
    if fdir is None:
        return None
    exact: list[Path] = []
    prefixed: list[Path] = []
    for path in grain_docs(fdir / STORIES_DIR):
        stem = path.name[:-len(path.suffix)]
        if stem == sslug:
            exact.append(path)
        elif story_slug_of(cfg, stem) == sslug:
            prefixed.append(path)
    matches = exact or prefixed
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
def orphan_dirs(cfg: PmConfig) -> list[tuple[Path, str]]:
    """Directories that look like a grain but carry no grain file — reported
    rather than silently dropped, since a dropped directory takes every
    descendant with it (rule 4).
    """
    out: list[tuple[Path, str]] = []
    candidates = _milestone_candidates(cfg.roadmap, exclude_archive=True)
    _, orphan_milestones = candidates.partition(_has_milestone_file,
                                                SkipReason.NO_GRAIN_FILE)
    orphaned = set(orphan_milestones)
    for d in candidates.kept:
        if d in orphaned:
            out.append((d, 'milestone dir with no milestone.md'))
            continue
        _, orphan_features = walk.children(d / FEATURES_DIR, Kind.DIR).partition(
            _has_feature_file, SkipReason.NO_GRAIN_FILE)
        out += [(f, 'feature dir with no feature.md') for f in orphan_features]
    return out


def _has_milestone_file(d: Path) -> bool:
    return (d / MILESTONE_DOC).is_file()


def _has_feature_file(d: Path) -> bool:
    return (d / FEATURE_DOC).is_file()


def _milestone_candidates(base: Path, exclude_archive: bool) -> Walk:
    """Directories under one roadmap base that a milestone could be — the one
    walk `milestone_dirs` and `orphan_dirs` share.
    """
    found = walk.children(base, Kind.DIR)
    if exclude_archive:
        found = found.filter(lambda d: d.name != ARCHIVE_DIR_NAME,
                             SkipReason.EXCLUDED_PATH)
    return found


def milestone_walk(cfg: PmConfig) -> Walk:
    """Milestone dirs in the active tree, with the scaffold-only dirs the walk
    dropped beside them.
    """
    return _milestone_candidates(cfg.roadmap, exclude_archive=True).filter(
        _has_milestone_file, SkipReason.NO_GRAIN_FILE)


def milestone_dirs(cfg: PmConfig) -> list[Path]:
    """Milestone dirs in the ACTIVE tree (archived ones predate the schema)."""
    return list(milestone_walk(cfg).kept)


def milestone_dir_of(cfg: PmConfig, path: Path) -> Path | None:
    """The milestone directory that contains this grain document, or None —
    the twin of `milestone_dir`, asked of a resolved path. Structural: the
    first component under `roadmap/` (or `roadmap/zz_archive/`), whether or
    not it still holds a `milestone.md`.
    """
    base = cfg.roadmap
    try:
        here = path.resolve()
        base = base.resolve()
    except OSError:
        return None
    if not here.is_relative_to(base):
        return None
    parts = here.relative_to(base).parts
    if parts[:1] == (ARCHIVE_DIR_NAME,):
        base, parts = base / ARCHIVE_DIR_NAME, parts[1:]
    if len(parts) < 2:
        return None
    return base / parts[0]


def known_milestones(cfg: PmConfig) -> list[tuple[Path, str]]:
    """Every milestone dir with its declared id (unquoted; '' when absent) —
    the one enumeration `pm status`, `pm list` and retire read.
    """
    return [(mdir, unquote(field_of(mdir / MILESTONE_DOC, 'id')))
            for mdir in milestone_dirs(cfg)]


BOM = '﻿'


def _opens_frontmatter(lines: list[str]) -> bool:
    """True when this text attempts a leading `---` block — lenient on a BOM,
    blank lines and fence indent, so a damaged grain is a finding rather
    than a note, but never past prose.
    """
    for line in lines:
        probe = line.lstrip(BOM)
        if not probe.strip():
            continue
        return _FENCE.match(probe.lstrip(' \t')) is not None
    return False


def _is_grain_doc(path: Path) -> bool:
    """True when this file is a grain document rather than a note beside one:
    it opens a frontmatter block, well-formed or not. Detection is lenient
    and parsing strict, so a damaged grain stays in scope for the rules; so
    does a file that cannot be read.
    """
    try:
        return _opens_frontmatter(_split(read_raw(path)))
    except (OSError, UnicodeDecodeError):
        return True


def slot_walk(gdir: Path) -> Walk:
    """The walk of one slot directory (`bugs/`, `stories/`) — the single
    definition every reader shares. Recursive, `.md` compared
    case-insensitively, and two disclosed narrowings: dot-prefixed
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


def feature_files(mdir: Path) -> list[Path]:
    return [d / FEATURE_DOC for d in walk.children(mdir / FEATURES_DIR, Kind.DIR)
            .filter(_has_feature_file, SkipReason.NO_GRAIN_FILE).kept]


def story_files(ffile: Path) -> list[Path]:
    """Every story document under one feature, in reading order."""
    return grain_docs(ffile.parent / STORIES_DIR)


def tree_walk(cfg: PmConfig) -> Walk:
    """Every slot document in the active tree and everything the walk skipped;
    `Walk.census` is the only way to a number here.
    """
    found = Walk(())
    for mdir in milestone_dirs(cfg):
        found = found.merge(slot_walk(mdir / BUGS_DIR))
        for ffile in feature_files(mdir):
            found = found.merge(slot_walk(ffile.parent / STORIES_DIR))
    return found


# --- THE review-record definition --------------------------------------------
def record_resolves(path: Path) -> bool:
    """True if the pointer names a file that is there — the whole definition;
    how much a reviewer wrote is not a fact about anything.
    """
    return path.is_file()


def _pointer_escapes(pointer: str) -> bool:
    """Does a `reviewed:` pointer name somewhere outside the checkout? The
    shapes `core.config.relpath` refuses, as a predicate: a bad pointer is
    a finding about one feature, not a config error.
    """
    return (pointer.startswith(('/', '~', '\\'))
            or ':' in pointer.split('/', 1)[0]
            or '..' in Path(pointer).parts)


def review_record_for(cfg: PmConfig, fid: str) -> str | None:
    """The feature's resolved review record, or None; the `reviewed:` pointer
    is the whole mechanism, with no filename fallback.
    """
    ffile = feature_file(cfg, fid)
    if ffile is None:
        return None
    pointer = unquote(field_of(ffile, 'reviewed'))
    if pointer and pointer != 'null':
        # Repo-relative, always: an absolute pointer is a record nobody
        # reviewing this repo can read (hard rule 8), and `ready-for tag`
        # already refused it by shape.
        if _pointer_escapes(pointer):
            return None
        if record_resolves(cfg.root / pointer):
            return pointer
    return None


# --- flow helpers (D9/D10, and the ledger's home) -----------------------------
def in_progress_milestones(cfg: PmConfig) -> list[tuple[str, str, Path]]:
    """(id, branch, milestone.md) for every active milestone in `in_progress`.
    There is no "the building milestone" (D5): readers report over every
    one or refuse naming them all.
    """
    out = []
    for mdir in milestone_dirs(cfg):
        mfile = mdir / MILESTONE_DOC
        status = field_of(mfile, 'status')
        if category_of(cfg, 'milestone', status) != IN_PROGRESS:
            continue
        out.append((field_of(mfile, 'id'), field_of(mfile, 'branch'), mfile))
    return out


def mainline_branch() -> str:
    """D10's trunk name — `[repo_hygiene] mainline`, `origin/`-stripped, since
    a milestone's authored `branch:` is never remote-qualified.
    """
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
        for line in read_raw(path).split('\n'):
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
    """`pm/roadmap/releases.md` — the plan. Absent until `pm order` writes it."""
    return cfg.roadmap / RELEASES_DOC


def plan_defect(cfg: PmConfig) -> str | None:
    """Why `releases.md` cannot be read as a plan, or None.

    An ABSENT plan is not a defect — a tree mid-adoption has none. A plan that
    is THERE and unreadable is: reporting "declares no `order`" over a
    BOM-damaged, fence-eaten, misspelled or undecodable file is rule 4's first
    cardinal sin, a gate passing over what it did not measure.
    """
    path = releases_file(cfg)
    if not path.is_file():
        return None
    try:
        text = read_raw(path)
    except (OSError, UnicodeDecodeError) as err:
        return f'could not be read as UTF-8 text ({err.__class__.__name__})'
    lines = _split(text)
    if _fence_bounds(lines) is None:
        opens = bool(lines) and _FENCE.match(lines[0]) is not None
        return ('has an opening `---` with no closing one'
                if opens else
                'has no frontmatter block — the plan is a grain, and `order` '
                'lives in its frontmatter')
    open_i, close_i = _fence_bounds(lines)
    for i in range(open_i + 1, close_i):
        if not lines[i].startswith(f'{ORDER_KEY}:'):
            continue
        rest = lines[i][len(ORDER_KEY) + 1:].strip()
        if rest and not rest.startswith('#'):
            return (f'`{ORDER_KEY}:` carries a scalar ({rest!r}) rather than a '
                    f'block list — one `- "<version>"` per line')
        return None
    return (f'declares no `{ORDER_KEY}:` key — the file is there, so this is a '
            f'plan that lost its list rather than a tree that has none')


def declared_order(cfg: PmConfig) -> list[str]:
    """The declared sequence of versions, or [] when the tree has no plan."""
    return list_field_of(releases_file(cfg), ORDER_KEY)


def milestone_version(cfg: PmConfig, mid: str) -> str:
    """The version a milestone declares it ships as, or '' — it is optional,
    and a milestone without one is BACKLOG, never a finding (R2).
    """
    mfile = milestone_file(cfg, mid)
    return field_of(mfile, 'version') if mfile is not None else ''


def version_claims(cfg: PmConfig) -> list[tuple[str, str]]:
    """(version, milestone id) for every milestone that declares one, in tree
    order. A list rather than a dict: R3 asks whether two milestones claim the
    same version, and a dict would have eaten the duplicate.
    """
    out = []
    for mdir, mid in known_milestones(cfg):
        version = field_of(mdir / MILESTONE_DOC, 'version')
        if version:
            out.append((version, mid))
    return out


def milestones_of_version(cfg: PmConfig, version: str) -> list[str]:
    """Every milestone claiming `version`, in tree order.

    A list, because two milestones claiming one version is a real tree defect
    (R3) and answering with the first would make the verdict depend on a
    directory NAME.
    """
    return [mid for claimed, mid in version_claims(cfg) if claimed == version]


def milestone_of_version(cfg: PmConfig, version: str) -> str | None:
    """The one milestone claiming `version`, or None when none or several do."""
    claimants = milestones_of_version(cfg, version)
    return claimants[0] if len(claimants) == 1 else None


def release_is_shipped(cfg: PmConfig, version: str) -> bool:
    """Has the one milestone claiming `version` finished?"""
    mid = milestone_of_version(cfg, version)
    if mid is None:
        return False
    mfile = milestone_file(cfg, mid)
    if mfile is None:
        return False
    return category_of(cfg, 'milestone', field_of(mfile, 'status')) == DONE_CATEGORY


def release_is_unverifiable(cfg: PmConfig, version: str) -> bool:
    """Can this entry's state not be established from the tree?

    Two shapes, and neither may be read as "not shipped": a milestone that was
    RETIRED (its record deleted, though the work shipped) and one that has not
    been written yet look identical from here, and so does a version two
    milestones both claim. Calling any of them unshipped is what made `pm
    retire` roll the current release BACKWARD and demand a version regression.
    """
    return len(milestones_of_version(cfg, version)) != 1


def last_shipped_index(cfg: PmConfig) -> int:
    """Position of the last entry in `order` whose milestone is `done`, or -1.

    "Behind us" is a POSITION, which is the whole reason order is declared: no
    comparator is asked whether 0.90.10 follows 0.90.4.
    """
    order = declared_order(cfg)
    last = -1
    for i, version in enumerate(order):
        if release_is_shipped(cfg, version):
            last = i
    return last


def current_release(cfg: PmConfig) -> str | None:
    """The version this tree is at, by POSITION in `order` — the first entry
    not yet shipped under `version_at = "start"`, the last that has under
    `"ship"`. None when the tree declares no order, or when the position it
    names does not exist (everything shipped / nothing has).

    Unlike "the one milestone in progress" this cannot be SEVERAL — a position
    in a list is one place. It can be None, and it does read `status`, one call
    away in `release_is_shipped`; what it never does is read a version string
    as a structure.
    """
    order = declared_order(cfg)
    if not order:
        return None
    if cfg.version_at == VERSION_AT_START:
        for version in order:
            if release_is_shipped(cfg, version):
                continue
            if release_is_unverifiable(cfg, version):
                # Cannot be established, so it is not answered: a retired
                # milestone's entry is history, and guessing it is the future
                # grades the tree against a version regression.
                continue
            return version
        return None
    shipped = [v for v in order if release_is_shipped(cfg, v)]
    return shipped[-1] if shipped else None


def release_ledger_dir(cfg: PmConfig) -> tuple[Path | None, str]:
    """(the milestone directory holding the current release's ledger, or None,
    plus why not).

    **Gate cost is a fact about a RUN**, and the run happened whether or not
    anybody had flipped a status. Binding the ledger to "the one milestone in
    `in_progress`" refused on none and on several, and this tree spent a week
    planning two milestones with every cost row silently dropped.

    `order` plus `version_at` answer with exactly one BY CONSTRUCTION — a
    position in a list is one place — and read no status field to do it.

    The in-progress fallback is deliberate and is recorded as a decision: a
    consumer bumping the pin has a building milestone and no plan yet, and
    refusing every cost row on the bump would be a breaking change wearing a
    minor version. A tree with neither is refused naming `pm order`, which is
    then the one honest reason left.
    """
    version = current_release(cfg)
    if version is not None:
        mid = milestone_of_version(cfg, version)
        mdir = milestone_dir(cfg, mid) if mid else None
        if mdir is not None:
            return mdir, ''
        return None, (f'the current release {version} is claimed by no '
                      f'milestone directory in {cfg.roadmap_dir} — '
                      f'`agentic-sdlc pm roadmap` shows the plan against the '
                      f'tree')
    live = in_progress_milestones(cfg)
    if len(live) == 1:
        return live[0][2].parent, ''
    if not declared_order(cfg):
        return None, (f'{cfg.rel(releases_file(cfg))} declares no `order`, so '
                      f'there is no current release to file against — '
                      f'`agentic-sdlc pm order --append <version>` writes the '
                      f'plan')
    return None, (f'every release in {cfg.rel(releases_file(cfg))} has shipped '
                  f'(or none has, under [pm] version_at = {cfg.version_at!r}), '
                  f'so there is no current release to file against')


def drift_dangling_record(cfg: PmConfig, fid: str) -> str | None:
    """D1 — a `reviewed:` pointer naming a file that is not there. An absent
    pointer is not a finding; only a dangling one is.
    """
    ffile = feature_file(cfg, fid)
    if ffile is None:
        return None
    pointer = unquote(field_of(ffile, 'reviewed'))
    if not pointer or pointer == 'null':
        return None
    target = Path(pointer) if pointer.startswith('/') else cfg.root / pointer
    if record_resolves(target):
        return None
    return f'reviewed: {pointer!r} resolves to nothing'


def drift_stalled(cfg: PmConfig, view: 'FeatureView') -> str | None:
    """D2 — every story finished but the feature still in `todo` (a forgotten
    flip). A feature at any `in_progress` state over finished stories is
    the valid shape of one that has advanced.
    """
    if view.total == 0 or view.done_n != view.total:
        return None
    if category_of(cfg, 'feature', view.status) == TODO:
        return f'all stories done, feature still {view.status}'
    return None


def drift_ahead_of_parent(cfg: PmConfig, child: str, parent: str) -> bool:
    """D5 — a story has left `todo` under a feature still in it: work started
    in one place and not the other. A story `done` under a `reviewing`
    feature is the normal path. Asked of the categories, so it places in
    every vocabulary.
    """
    child_cat = category_of(cfg, 'story', child)
    parent_cat = category_of(cfg, 'feature', parent)
    if child_cat is None or parent_cat is None:
        return False
    return parent_cat == TODO and child_cat != TODO


@dataclass
class FeatureView:
    """One feature plus the tallies every reader needs; `done_n` counts the
    `done` category through `holds`, the predicate `ready-for feature`
    uses.
    """
    fid: str
    status: str
    phase: str
    path: Path
    stories: list[Path] = field(default_factory=list)
    done_n: int = 0

    @property
    def total(self) -> int:
        return len(self.stories)


def read_feature(cfg: PmConfig, ffile: Path) -> FeatureView:
    view = FeatureView(
        fid=unquote(field_of(ffile, 'id')),
        status=field_of(ffile, 'status'),
        phase=unquote(field_of(ffile, 'phase')),
        path=ffile,
        stories=story_files(ffile),
    )
    finished = holds(cfg, 'story',
                     ((s, field_of(s, 'status')) for s in view.stories),
                     DONE_CATEGORY)
    view.done_n = finished.counted - len(finished.blockers)
    return view


def phase_key(phase: str) -> tuple:
    """The board's reading order for a feature's `phase:`: numbered phases
    numerically, then named ones alphabetically, then the unphased. The
    engine knows no phase word.
    """
    if phase.isdigit():
        return (0, int(phase), '')
    if phase:
        return (1, 0, phase)
    return (2, 0, '')


def phase_label(phase: str) -> str:
    """How `pm status` and the execution list head a phase bucket."""
    if phase.isdigit():
        return f'phase {phase}'
    return phase or 'unphased'

# --- shared-doc headers -------------------------------------------------------
def header_of(path: Path) -> str:
    """The file's first non-blank line, stripped — its canonical header slot."""
    try:
        for line in _split(read_raw(path)):
            if line.strip():
                return line.strip()
    except (OSError, UnicodeDecodeError):
        return ''
    return ''


# --- bug status vocabulary (D4) -----------------------------------------------
# A bug is never moved by this tool; what is checkable is D4's fact, a status
# outside the vocabulary — and every "is it open" reader tests a name, so a
# typo would pass in silence.
def bug_files(mdir: Path) -> list[Path]:
    """Every bug document under one milestone, in reading order."""
    return grain_docs(mdir / BUGS_DIR)


def bug_status_findings(cfg: PmConfig) -> tuple[list[tuple[Path, str]], int]:
    """(findings, bugs scanned) — every bug whose status the project never
    declared. The walk is recursive and case-insensitive on the extension,
    so the census cannot undercount silently.
    """
    out: list[tuple[Path, str]] = []
    scanned = 0
    for mdir in milestone_dirs(cfg):
        for bfile in bug_files(mdir):
            scanned += 1
            bstat = field_of(bfile, 'status')
            if category_of(cfg, 'bug', bstat) is None:
                # The bug line's shape is grepped (rule 6), so it is kept
                # verbatim.
                out.append((bfile, f'bug status {bstat!r} is not in '
                                   f'({" ".join(flow_of(cfg, "bug").order)})'))
    return out, scanned


def state_usage(cfg: PmConfig) -> dict[str, dict[str, int]]:
    """Per kind, how many grains hold each DECLARED state — zero included.

    D4 asks "is this word declared", never "is this word used", so a tree using
    two of eight states is indistinguishable, to every gate, from one using all
    eight. That is how a project adopted the conveyor as a CONFIG FIX and never
    noticed: `building`, `reviewing`, `accepted` and `packaging` appeared zero
    times across 85 grains, and every gate was green the whole time.
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

    for mdir in milestone_dirs(cfg):
        count('milestone', field_of(mdir / MILESTONE_DOC, 'status'))
        for bf in bug_files(mdir):
            count('bug', field_of(bf, 'status'))
        for ff in feature_files(mdir):
            count('feature', field_of(ff, 'status'))
            for sf in story_files(ff):
                count('story', field_of(sf, 'status'))
    return used


def undeclared_status(cfg: PmConfig, kind: str, status: str) -> str | None:
    """D4's one sentence: the word, and the words the project did declare;
    None when `status` is in some category. One wording for every grain
    kind.
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

_HEADING = re.compile(r'^(#{1,2})[ \t]+(.*?)[ \t]*$')


def section_lines(text: str, heading: str) -> list[str] | None:
    """The lines under `## <heading>`, up to the next heading; None when the
    heading is absent, which is a different sentence from "empty".
    """
    lines = _split(text)
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
    template's own prompt is not content.
    """
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
    lines = section_lines(read_raw(path), heading)
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
    prefix follows the last id-shaped heading, a log with none starts at
    `D1`, and numbering is per file by design.
    """
    seen = [m for m in (_ENTRY_ORDINAL.match(line) for line in _split(text)) if m]
    if not seen:
        return f'{DECISION_PREFIX}1'
    prefix = seen[-1].group(1)
    highest = max(int(m.group(2)) for m in seen if m.group(1) == prefix)
    return f'{prefix}{highest + 1}'


def append_heading(text: str, eid: str, when: str, title: str) -> str:
    """`text` with one `## <id> — <date> — <title>` heading appended; the em
    dash is what `next_entry_id` and every log already use.
    """
    eol = '\r\n' if '\r\n' in text else '\n'
    body = text
    if body and not body.endswith(('\n', '\r')):
        body += eol
    if body and not body.endswith(eol * 2):
        body += eol
    return body + f'## {eid} — {when} — {title}{eol}'
