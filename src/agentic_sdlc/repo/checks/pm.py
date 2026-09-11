"""check pm — the active PM tree's statuses do not contradict each other.

Every rule asks a CATEGORY (`todo`/`in_progress`/`done`), never a word, off the same
predicates in `repo/pm/model` that `pm` writes with. Which rules run is `[pm] checks`
(default: D1/D2/D4/D5/D6/D11 + U1/U2/U3/U4/U5 + V1/V4/V5/V7; D9/D10 and the R
family are opt-in). D3 retired INTO D11 — `pm vocabulary` names where it went.

DRIFT (each FAILs, naming the path):
  D1  a `reviewed:` pointer naming a file that is not there
  D4  a status the project never declared, for any grain kind
  D11 a parent in `done` over a child that is not, every level off `BINDS_TO`,
      and a retired binding field on any grain. `pm remove` is the opt-out
  D12 (WARN) a grain in `done` carrying no `changelog:` and no `none` — the
      release belt refuses on it; this names it while there is time to write one
  R1  an `order` entry naming no milestone in the tree (WARN); a milestone on
      no plan is UNSEQUENCED, a counted line
  R3  two milestones claiming one `version:`
  R4  history is a prefix — a shipped release sitting after an unshipped one
  R5  the version file equals the CURRENT release in `order` ([pm] version_at)
  R6  an entry behind the last shipped one whose milestone never closed, and a
      `done` milestone that is on no plan
  D9/D10  an `in_progress` milestone declares a `branch:`, and it is not the
      mainline (`[repo_hygiene] mainline`, `origin/`-stripped)
WARN (a line, never the exit code; both grains and both categories named):
  D2  a feature in `todo` while all its stories are `done`
  D5  a story out of `todo` under a feature still in it
  D6  a milestone in `todo` whose features are all `done`
  U1  a DECLARED state no grain of that kind has ever held — ONE line for every
      kind, each naming its unused states beside its count in use
  U2  the ledger couriers are wired in `.claude/settings.json` and the tree holds
      no row at all — recording that goes nowhere, which is silent by construction
  U3  `[emit]` is DECLARED and its sink has never been written to. A tree that
      declares no `[emit]` opted out and gets no line; declared-and-silent is a
      contradiction the tree is holding. The rule READS the sink, never probes it
  U4  the couriers are wired and the LAST hook-written row is named with its age —
      a WARN when there has never been one, a counted RECORDING line when there
      has. Status, decision and gate rows are written from inside this checkout
      and are not evidence a courier ran, which is why U2 passes over a tree that
      records no dispatch at all
  U5  a grain whose CURRENT state was arrived at with no disposition, by name. A
      bare move is allowed and records `answer: none` (D3) — never blocked, and
      never invisible either
  V7  MEMBERSHIP and SEQUENCE, each in both directions. A binding naming a grain
      not in the tree or of the wrong kind FAILS; an `order` entry naming a grain
      its parent does not hold is DANGLING (FAIL), one naming no grain at all
      UNVERIFIABLE (WARN). An EMPTY binding is UNBOUND and a bound child in no
      `order` is UNSEQUENCED — COUNTED lines, never findings, because *nothing
      said* is a plan and *something wrong said* is drift
  READY  an IN_PROGRESS grain with an empty scaffolded section (`## Ship criterion`,
         `## Acceptance criteria`, `## Proof budget`), no stories, no `owner:`, no
         `branch:`, or (a milestone) no `handoff.md` — never auto-minted, so
         `pm new handoff <id>` is the fix. A CLOSED grain's gaps are COUNTED on
         one line rather than named: its criterion is nobody's next action, and
         that was 45 of this repo's 57 warnings
  R2  the BACKLOG census — milestones on no plan that declare no `version:`

Archived milestones are out of scope; a zero census FAILS.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple

from agentic_sdlc.repo.pm import model

# How many row kinds the 'what IS recorded' census names before the fix
# line; thirteen of them once pushed that fix behind 839 characters.
CENSUS_TOP = 3

# One word, so `check pm | grep never` is a consumer's whole reader.
NEVER = 'never'
# The pressure census: its criterion's third surface, after `pm` and a belt.
OPEN_WORK = 'OPEN'
# The third answer, dropped on the floor by a belt that branched on two of
# them. A PREFIX: what could not be read is named after it.
UNVERIFIABLE = 'UNVERIFIABLE'
# A row whose `ts` will not parse is not a row aged zero (rule 4): a ledger is
# `merge=union`, and rows arrive from other branches and other versions.
UNDATEABLE = 'at a timestamp this reader cannot parse'
# The harness's per-user override. `install-hooks` emits ABSOLUTE paths and a
# public repo must not commit a machine path, so the block belongs in a
# gitignored file — a reader of one file calls such a tree unwired.
AGENT_SETTINGS_LOCAL = '.claude/settings.local.json'
SETTINGS_FILES = (model.AGENT_SETTINGS, AGENT_SETTINGS_LOCAL)


def run() -> int:
    try:
        # THE one read-only scope: the walk under every rule is shared rather
        # than repeated per rule per grain, and the scope drops itself on a write.
        with model.reading_tree():
            return _run()
    except model.ConfigError as err:
        # EVERY defect, not the first, and the FLOW first among them: the flow
        # is read lazily, so a tree that declared none is refused at the first
        # category question, and a real adoption is wrong in more ways than one.
        try:
            defects = model.all_config_defects()
        except Exception:  # noqa: BLE001 - the collector must never mask the error
            defects = []
        for msg in defects or [str(err)]:
            print(f'[check:pm] ERROR — {msg}', file=sys.stderr)
        if len(defects) > 1:
            print(f'[check:pm] {len(defects)} config defect(s) — all of them '
                  f'are above, and the first one listed is the one that stops '
                  f'the most', file=sys.stderr)
        return 2


def _run() -> int:
    cfg = model.load()
    # Validated here, not in `model.load()`, so a stale rule id cannot take `pm status` down.
    stale = model.config_complaints(cfg)
    if stale:
        # The flow can be declared and the roster still stale; report the whole
        # set either way, in the same order.
        flow = model.missing_flow_defect()
        for msg in ([flow] if flow else []) + stale:
            print(f'[check:pm] ERROR — {msg}', file=sys.stderr)
        return 2
    findings: list[str] = []
    warnings: list[str] = []

    def report(msg: str) -> None:
        findings.append(msg)
        print(f'  DRIFT  {msg}')

    def warn(msg: str) -> None:
        warnings.append(msg)
        print(f'  WARN  {msg}')

    enabled = set(cfg.checks)
    print(f'[check:pm] scanning active PM tree ({cfg.roadmap_dir}/, '
          f'excluding {model.ARCHIVE_DIR_NAME}/)')

    found_milestones = model.milestones(cfg)
    if not found_milestones:
        print()
        print(f'[check:pm] FAIL — no milestones found under {cfg.roadmap_dir}/ '
              f'(wrong [pm] roadmap_dir, or an empty tree?)')
        return 1

    # Never gated by `checks`: this is the scan saying it found something it
    # cannot place.
    for stray in model.stray_documents(cfg):
        report(f'{cfg.rel(stray.path)} declares `id: '
               f'{stray.field(model.FIELD_ID)}` and sits in no '
               f'pool, so every reader walks past it — move it into '
               f'{cfg.rel(model.pool_dir(cfg, stray.field(model.FIELD_KIND) or model.GRAIN_MILESTONE))}/')

    # No readable `id:`, and two documents claiming one, are V1's and are
    # reported from `validate.run` below, so `pm validate` and this gate cannot
    # disagree about a file neither of them can key on.

    # Always walked for the census; reported only under D4.
    bug_findings, n_bugs = model.bug_status_findings(cfg)
    if 'D4' in enabled:
        for path, why in bug_findings:
            report(f'{cfg.rel(path)}: {why}')

    ready = _Ready(warn)
    n_features, n_stories, seen = _drift_walk(cfg, enabled, found_milestones,
                                              report,
                                              warn, ready)

    _unreached_self(cfg, enabled, seen, report, ready)
    ready.report()
    _containment(cfg, enabled, report)
    _changelog_answered(cfg, enabled, warn)
    _unbound_rows(cfg, enabled, report, warn)
    _flow_findings(cfg, enabled, report)
    _unused_states(cfg, enabled, warn)
    # Read ONCE: U5 gates on it and the line below reports it, so this gate
    # and a `pm` write cannot disagree. `pressure = false` silences both.
    from agentic_sdlc.repo.pm import arrive as _arrive
    open_work = _arrive.census(cfg)
    _unanswered_arrivals(cfg, enabled, warn, open_work)
    _recording_findings(cfg, enabled, warn)
    _hook_recording_findings(cfg, enabled, warn)
    _emit_sink_findings(cfg, enabled, warn)
    _release_findings(cfg, enabled, report, warn)

    # --- V1-V7: structural + referential integrity ------------------------
    v_on = enabled & set(model.VALIDATE_CHECKS)
    v_census: dict = {}
    if v_on:
        from agentic_sdlc.repo.pm import validate as _validate
        v_findings, v_census = _validate.run(cfg, v_on)
        for msg in v_findings:
            report(msg)

    if open_work:
        print(f'  {OPEN_WORK}  {open_work.line}')
    return _verdict(cfg, findings, warnings,
                    _census(cfg, len(found_milestones), n_features,
                            n_stories, n_bugs),
                    v_on, v_census)


# D2's and D6's shared tail; neither rule has an opinion about which state is next.
ADVANCE_IT = 'advance it (`done` is the LAST state, not the next one)'


def _cat(cfg: model.PmConfig, kind: str, status: str) -> str:
    """The category a WARN line prints beside a word, or 'undeclared'."""
    return model.category_of(cfg, kind, status) or 'undeclared'


class _Ready:
    """READY's two audiences: a gap on an `in_progress` grain can still be
    acted on, so it is NAMED; one on a closed grain cannot — a criterion is a
    promise about work that has not happened — so it is COUNTED. D12 drew this
    line first, for the same 351-of-359.
    """

    def __init__(self, warn) -> None:
        self._warn = warn
        self.named = self.counted = self.live = self.closed = 0

    def grading(self, cfg: model.PmConfig, kind: str, status: str) -> bool | None:
        """True while the grain can still act, False once it has closed, None
        in `todo` — where nothing is asked and nothing is counted."""
        category = model.category_of(cfg, kind, status)
        if category is None or category == model.TODO:
            return None
        live = category == model.IN_PROGRESS
        self.live += live
        self.closed += not live
        return live

    def gap(self, live: bool, msg: str) -> None:
        if live:
            self.named += 1
            self._warn(msg)
        else:
            self.counted += 1

    def report(self) -> None:
        # Printed at zero too: a family that graded nothing has to say so, and
        # this count is what makes the narrowing above visible (rule 4).
        print(f'  READY  {self.named} gap(s) named on {self.live} '
              f'{model.IN_PROGRESS} grain(s); {self.counted} on {self.closed} '
              f'closed grain(s) counted rather than named — a closed grain\'s '
              f'scaffolded section is nobody\'s next action (READY)')


def _feature_self(cfg: model.PmConfig, view, ready: _Ready) -> None:
    """The READY warnings a feature earns on its OWN document."""
    live = ready.grading(cfg, model.GRAIN_FEATURE, view.status)
    if live is None:
        return
    frel = cfg.rel(view.path)
    if view.total == 0:
        ready.gap(live, f'feature {view.fid} is {view.status!r} with no '
                        f'stories — past todo, and nothing to build  [{frel}]')
    why = model.empty_section(view.path, model.SHIP_HEADING)
    if why:
        ready.gap(live, f'feature {view.fid} is {view.status!r} and {why} — '
                        f'past todo, and nothing says what done means  [{frel}]')
    # The anti-bloat contract, never verified to exist until here: an empty
    # proof budget is how a feature ships twice its budget with nobody able to
    # say so.
    why = model.empty_section(view.path, model.PROOF_HEADING)
    if why:
        ready.gap(live, f'feature {view.fid} is {view.status!r} and {why} — '
                        f'past todo, and nothing says what it should COST  '
                        f'[{frel}]')


def _story_self(cfg: model.PmConfig, story, sid: str, sstat: str,
                ready: _Ready) -> None:
    """The READY warnings a story earns on its OWN document."""
    srel = cfg.rel(story.path)
    live = ready.grading(cfg, model.GRAIN_STORY, sstat)
    if live is None:
        return
    why = model.empty_section(story.path, model.ACCEPTANCE_HEADING)
    if why:
        ready.gap(live, f'story {sid} is {sstat!r} and {why} — past todo, and '
                        f'nothing says what must be true  [{srel}]')
    if live and not story.field(model.FIELD_OWNER):
        # A LIVE BUG, not a tidy-up: two modules READ `owner:` and nothing
        # asked whether the claim had set it (`pm-execution.md` step 1).
        ready.gap(True, f'story {sid} is {sstat!r} ({model.IN_PROGRESS}) and '
                        f'carries no owner: — somebody is working on it and '
                        f'the tree cannot say who  [{srel}]')


def _unreached_self(cfg: model.PmConfig, enabled: set[str], seen: set[str],
                    report, ready: _Ready) -> None:
    """Every SELF rule, for the grains the descent did not visit.

    **`seen` is RECORDED, never inferred.** "Does this binding resolve" gets a
    story under an UNBOUND feature wrong — its binding resolves and the descent
    still never reaches it, so it fell between both passes at exit 0. SELF
    rules only: D5 and D11 need a parent to compare against.
    """
    if not model.is_pooled(cfg):
        return
    for kind in (model.GRAIN_FEATURE, model.GRAIN_STORY):
        for path in model.pool_walk(cfg, kind):
            grain = model.read_grain(cfg, path, kind)
            if grain is None or grain.gid in seen:
                continue
            rel = cfg.rel(path)
            status = grain.field(model.FIELD_STATUS)
            if 'D4' in enabled:
                reason = model.undeclared_status(cfg, kind, status)
                if reason:
                    report(f'{kind} {grain.gid}: {reason}  [{rel}]')
            if kind == model.GRAIN_FEATURE:
                if 'D1' in enabled:
                    # A fact about ONE document, and it was in the descent only.
                    reason = model.drift_dangling_record(cfg, grain.gid)
                    if reason:
                        report(f'feature {grain.gid}: {reason} — point it at a '
                               f'real file or remove the field  [{rel}]')
                _feature_self(cfg, model.read_feature(cfg, path), ready)
            else:
                _story_self(cfg, grain, grain.gid, status, ready)


def _drift_walk(cfg: model.PmConfig, enabled: set[str], found_milestones,
                report, warn, ready: _Ready) -> tuple[int, int, set[str]]:
    """D1-D6 over every grain the descent reaches, plus the READY warnings.

    The third return is the ids it VISITED, because `_unreached_self` must not
    have to infer them.
    """
    n_features = 0
    n_stories = 0
    seen: set[str] = set()

    for milestone in found_milestones:
        mfile = milestone.path
        mid = milestone.field(model.FIELD_ID)
        mstat = milestone.field(model.FIELD_STATUS)
        m_cat = model.category_of(cfg, model.GRAIN_MILESTONE, mstat)
        m_live = ready.grading(cfg, model.GRAIN_MILESTONE, mstat)

        if 'D4' in enabled:
            reason = model.undeclared_status(cfg, model.GRAIN_MILESTONE, mstat)
            if reason:
                report(f'milestone {mid}: {reason}  [{cfg.rel(mfile)}]')

        if m_live is not None:
            if not milestone.field('branch'):
                ready.gap(m_live, f'milestone {mid} is {mstat!r} with no '
                                  f'branch: — past todo, and a fresh checkout '
                                  f'cannot find where its work lives  '
                                  f'[{cfg.rel(mfile)}]')
            why = model.empty_section(mfile, model.SHIP_HEADING)
            if why:
                ready.gap(m_live, f'milestone {mid} is {mstat!r} and {why} — '
                                  f'past todo, and nothing says what done '
                                  f'means  [{cfg.rel(mfile)}]')
            # Never auto-minted, so its ABSENCE is the signal. IN_PROGRESS only:
            # a handoff is a cold-start aid, so warning on `done` would fire
            # once per historical milestone on every consumer's tree.
            handoff = model.shared_doc(cfg, mfile, model.HANDOFF_FILE_NAME)
            if m_live and not handoff.is_file():
                ready.gap(True, f'milestone {mid} is {mstat!r} with no '
                                f'{model.HANDOFF_FILE_NAME} — past todo, and a '
                                f'cold session has nowhere to start; `pm new '
                                f'handoff {mid}` mints one  '
                                f'[{cfg.rel(handoff)}]')

        views = [model.read_feature(cfg, ffile)
                 for ffile in model.feature_files(cfg, mid)]
        # D6's census. The per-feature half went to D11 with D3.
        finished = model.holds(cfg, model.GRAIN_FEATURE,
                               ((v.fid, v.status) for v in views),
                               model.DONE_CATEGORY)
        for view in views:
            frel = cfg.rel(view.path)
            seen.add(view.fid)
            n_features += 1
            n_stories += view.total

            if 'D4' in enabled:
                reason = model.undeclared_status(cfg, model.GRAIN_FEATURE,
                                                 view.status)
                if reason:
                    report(f'feature {view.fid}: {reason}  [{frel}]')

            if 'D1' in enabled:
                reason = model.drift_dangling_record(cfg, view.fid)
                if reason:
                    report(f'feature {view.fid}: {reason} — point it at a real '
                           f'file or remove the field  [{frel}]')

            _feature_self(cfg, view, ready)

            for story in view.stories:
                sid = story.field(model.FIELD_ID)
                seen.add(sid)
                sstat = story.field(model.FIELD_STATUS)
                srel = cfg.rel(story.path)
                if 'D4' in enabled:
                    reason = model.undeclared_status(cfg, model.GRAIN_STORY,
                                                     sstat)
                    if reason:
                        report(f'story {sid}: {reason}  [{srel}]')
                _story_self(cfg, story, sid, sstat, ready)
                if 'D5' in enabled and model.drift_ahead_of_parent(
                        cfg, sstat, view.status):
                    warn(f'story {sid} is {sstat!r} '
                         f'({_cat(cfg, model.GRAIN_STORY, sstat)}) but its feature '
                         f'{view.fid} is still {view.status!r} '
                         f'({_cat(cfg, model.GRAIN_FEATURE, view.status)}) — the story '
                         f'is at work and the feature says it has not '
                         f'started (two places in this tree disagree, D5)'
                         f'  [{srel}]')

            if 'D2' in enabled:
                reason = model.drift_stalled(cfg, view)
                if reason:
                    warn(f'feature {view.fid}: {reason} '
                         f'({_cat(cfg, model.GRAIN_FEATURE, view.status)}) — all '
                         f'{view.total} stories are {model.DONE_CATEGORY}; '
                         f'{ADVANCE_IT} (D2)  [{frel}]')

        if ('D6' in enabled and m_cat == model.TODO
                and finished.counted > 0 and finished):
            warn(f'milestone {mid} is {mstat!r} ({m_cat}) but all '
                 f'{finished.counted} features are {model.DONE_CATEGORY} — '
                 f'you finished the features and the milestone still calls '
                 f'itself {mstat!r}; {ADVANCE_IT} (D6)  [{cfg.rel(mfile)}]')

    return n_features, n_stories, seen


def _unused_states(cfg: model.PmConfig, enabled: set[str], warn) -> None:
    """U1 — a state the project DECLARED and no grain has ever held.

    A WARN with the count, never a finding: a tree mid-adoption legitimately has
    unused states, and a rule that reddens every fresh consumer is undone within
    a version. What it buys is the fact staying VISIBLE after the install
    scrolls away.

    ONE line for every kind: three near-identical paragraphs saying one sentence
    about `[pm.states.*]` is how a line somebody could act on gets scrolled past.
    """
    if 'U1' not in enabled:
        return
    clauses, unused_total, declared_total = [], 0, 0
    for kind in model.FLOW_KINDS:
        counts = model.state_usage(cfg).get(kind)
        if not counts:
            continue
        unused = [state for state, n in counts.items() if n == 0]
        if not unused or len(unused) == len(counts):
            # All unused means the tree holds no grain of this kind — a
            # different fact, and not this rule's to report.
            continue
        unused_total += len(unused)
        declared_total += len(counts)
        clauses.append(f'{kind}: {len(counts) - len(unused)} of {len(counts)} '
                       f'in use, {", ".join(unused)} never held')
    if not clauses:
        return
    warn(f'{unused_total} of {declared_total} declared state(s) have never been '
         f'held by any grain in this tree — {"; ".join(clauses)} — declared and '
         f'unused is a flow the project is not running; `[pm.states.<kind>]` '
         f'declares each one (U1)')


def _asks_something(cfg: model.PmConfig, kind: str, state: str) -> bool:
    """Does `[pm.arrive.<kind>.<state>]` type any answer to record?"""
    arrival = model.arrival_at(cfg, kind, state)
    return bool(arrival and arrival.answers)


def _unanswered_arrivals(cfg: model.PmConfig, enabled: set[str], warn,
                         census) -> None:
    """U5 — a grain whose CURRENT state was arrived at with no disposition.

    A bare move still writes the status and records `answer: none` (D3), so
    "no action" is never blocked — just never invisible, and this is where it
    stays visible after the move's own line scrolls away. `arrive.census` is
    the GUARD and is handed IN, so this rule, the line below it and a `pm`
    write are one derivation; the grains are NAMED, never tallied (rule 11).

    A state that declares no answers has nothing to be unanswered about
    (0.6.0/D5, with the rejected alternative).
    """
    if 'U5' not in enabled:
        return
    from agentic_sdlc.repo.pm import arrive, ledger
    if census is None or not census.unanswered:
        return
    # The LAST disposition per (grain, state): a grain that bounced back has
    # arrived again, so the question is asked again (D3).
    answered: dict[tuple[object, object], object] = {}
    for _path, row in sorted(_ledger_rows(cfg)[0],
                             key=lambda pair: str(pair[1].get(ledger.TS_FIELD) or '')):
        if arrive.disposition_of(row):
            answered[(row.get(ledger.GRAIN_FIELD),
                      row.get('state'))] = row.get('answer')
    quiet = [g.gid for g in sorted(model.grain_index(cfg).values(),
                                   key=lambda g: g.gid)
             if g.kind in model.FLOW_KINDS
             and model.category_of(cfg, g.kind, g.status) == model.IN_PROGRESS
             and _asks_something(cfg, g.kind, g.status)
             and answered.get((g.gid, g.status)) in (None,
                                                     ledger.NO_DISPOSITION)]
    if not quiet:
        return
    warn(f'{len(quiet)} of {census.open_count} {model.IN_PROGRESS} grain(s) '
         f'reached the state they are in with no disposition: '
         f'{", ".join(quiet)} — a bare move is allowed and records '
         f'`answer: {ledger.NO_DISPOSITION}`; re-running the move with the '
         f'answer its state declares records one, and `pm vocabulary` prints '
         f'what each state asks (U5)')


# --- the RECORDING family (U2/U3/U4) ------------------------------------------
# One question — did anything land — asked of three sinks (see the U2/U3/U4
# entries above). They share the walk below because a rule that opened the same
# files a second time would answer off a different read than the rule beside it.
#
# **Every one of them READS.** None writes a probe row to find out, because a
# gate that mutates to measure is a gate that lies about what it measured.


def _ledger_rows(cfg: model.PmConfig) -> tuple[list[tuple[Path, dict]], list[str]]:
    """An unreadable or unparseable ledger is NEITHER answer — it is named and
    the scan continues, so one damaged file cannot make the tree look silent.
    """
    from agentic_sdlc.repo.pm import ledger
    rows: list[tuple[Path, dict]] = []
    unreadable: list[str] = []
    for path in ledger.ledger_paths(cfg):
        if not path.is_file():
            continue
        try:
            rows.extend((path, row.data) for row in ledger.read_rows(path))
        except ledger.LedgerError:
            unreadable.append(cfg.rel(path))
    return rows, unreadable


class Wiring(NamedTuple):
    """Which couriers a settings file REGISTERS, and which file said so.

    PUBLIC: `telemetry-live` asks this too, and two readers of one config is
    how a belt and a gate come to disagree."""

    couriers: tuple[str, ...]   # the couriers a `hooks` entry actually fires
    where: str                  # the settings file(s) that fire them
    unread: str                 # why a settings file could not be read


def _settings_couriers(path: Path) -> tuple[tuple[str, ...], str]:
    """(the couriers this one file registers, why it could not be read).

    The reader is `checks.hooks.settings_commands`: `check hooks` asks the same
    file the same question about the whole guard corpus, and two readers of one
    settings file is the pair this milestone kept finding."""
    from agentic_sdlc.repo.checks import hooks as check_hooks
    commands, why = check_hooks.settings_commands(path)
    return tuple(sorted(name for name in model.LEDGER_COURIERS
                        if any(name in command for command in commands))), why


def wired_couriers(root: Path) -> Wiring:
    """Which ledger couriers this checkout's settings files fire.

    **No settings file at all is an empty tuple, not a defect** — a tree that
    wires nothing opted out (0.4.0/D5). A ROOT, not a config: the belt asks
    before it has resolved a PM tree."""
    found: set[str] = set()
    where: list[str] = []
    unread: list[str] = []
    for rel in SETTINGS_FILES:
        couriers, why = _settings_couriers(root / rel)
        if why:
            unread.append(f'{rel} could not be read ({why})')
        elif couriers:
            found.update(couriers)
            where.append(rel)
    return Wiring(tuple(sorted(found)), ' and '.join(where),
                  '; '.join(unread))



def _age_of(row: dict) -> str:
    """`3h ago`, or the named non-answer for a row this reader cannot date."""
    from agentic_sdlc.repo.pm import ledger
    when = ledger.parse_ts(row.get(ledger.TS_FIELD))
    if when is None:
        return UNDATEABLE
    # Clamped: a row stamped in the future is a clock disagreement, and
    # rendering it as a negative age would read as a defect in this line.
    seconds = max(0, int((datetime.now(timezone.utc) - when).total_seconds()))
    return f'{ledger.human_duration(seconds)} ago'


def _recording_span(rows: list[tuple[Path, dict]]) -> str:
    """How long `never` has been true, off the OLDEST row these ledgers hold:
    five milestones and one afternoon read alike. No stamp, no number."""
    from agentic_sdlc.repo.pm import ledger
    stamps = [when for when in (ledger.parse_ts(row.get(ledger.TS_FIELD))
                                for _path, row in rows) if when is not None]
    if not stamps:
        return ''
    seconds = max(0, int((datetime.now(timezone.utc)
                          - min(stamps)).total_seconds()))
    return (f' in the {ledger.human_duration(seconds)} these ledgers have '
            f'been recording')


def _kind_of(row: dict) -> str:
    """The row's `kind`, or '' — type-checked, see `UNDATEABLE` above."""
    from agentic_sdlc.repo.pm import ledger
    kind = row.get(ledger.KIND_FIELD)
    return kind if isinstance(kind, str) else ''


def _kind_census(rows: list[tuple[Path, dict]], top: int = 0) -> str:
    """`'2 status, 1 gate'`, most-seen first — what the tree DID record, said
    beside what it did not. An unreadable kind is counted, never dropped.
    `top` caps the names and rolls the tail into a count — a thirteen-kind
    census was most of a warning nobody finished reading."""
    counts: dict[str, int] = {}
    for _path, row in rows:
        kind = _kind_of(row) or '(no kind)'
        counts[kind] = counts.get(kind, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    tail = ranked[top:] if top else []
    named = ', '.join(f'{n} {kind}' for kind, n in (ranked[:top] if top
                                                    else ranked))
    if not tail:
        return named
    return (f'{named} and {sum(n for _kind, n in tail)} row(s) across '
            f'{len(tail)} more kind(s)')


class Recording(NamedTuple):
    """What this tree's ledgers say about rows a COURIER wrote.

    PUBLIC, because `adopt`'s `telemetry-live` reports the same fact: two
    readers of it is how a belt and a gate come to disagree.
    """

    last: dict                      # the newest hook-written row, or {}
    where: str                      # the ledger it sits in, repo-relative
    written: int                    # how many rows a courier wrote
    total: int                      # how many rows the ledgers hold at all
    unreadable: tuple[str, ...]     # the ledgers this could not read


def hook_recording(cfg: model.PmConfig) -> Recording:
    """Every ledger in the tree, read for the LAST row a courier wrote.

    Ordered by the row's own `ts`, never the file's mtime or line order: a
    ledger is merged `union`, so the last line is not the last event in time.
    """
    from agentic_sdlc.repo.pm import ledger
    rows, unreadable = _ledger_rows(cfg)
    written = [(path, row) for path, row in rows if _hook_written(row)]
    if not written:
        return Recording({}, '', 0, len(rows), tuple(unreadable))
    path, last = max(written,
                     key=lambda pair: str(pair[1].get(ledger.TS_FIELD, '')))
    return Recording(last, cfg.rel(path), len(written), len(rows),
                     tuple(unreadable))


def recording_phrase(rec: Recording) -> str:
    """`'dispatch, 3h ago'`, `'never'`, or why neither could be answered — the
    sentence every surface that reports recording prints, spelled once."""
    if rec.unreadable:
        return (f'{UNVERIFIABLE} ({", ".join(rec.unreadable)} could not be '
                f'read)')
    if not rec.written:
        return NEVER
    return f'{_kind_of(rec.last)}, {_age_of(rec.last)}'


def _tree_has_a_row(cfg: model.PmConfig) -> tuple[bool, list[str]]:
    """(does any ledger hold a row, the ledgers this could not read).

    Both homes (0.4.0/D3), and existence is not enough — an empty file is what
    a courier leaves when it created the file and then refused the row. **An
    unreadable ledger is neither answer**, so it is named and the scan goes on.

    Raw text rather than `_ledger_rows`: a line this package cannot parse is
    still something a courier wrote, and U2 asks whether anything landed.
    """
    from agentic_sdlc.repo.pm import ledger
    paths = ledger.ledger_paths(cfg)
    found, unreadable = False, []
    for path in paths:
        if not path.is_file():
            continue
        try:
            if path.read_text(encoding='utf-8').strip():
                found = True
        except (OSError, UnicodeDecodeError):
            unreadable.append(cfg.rel(path))
    return found, unreadable


def _recording_findings(cfg: model.PmConfig, enabled: set[str], warn) -> None:
    """U2 — the ledger couriers are wired and the tree holds no row.

    **This rule exists because the telemetry was off for a whole milestone and
    nobody could tell**: a courier fails open by design, so its refusals go to
    a stderr nobody reads. A tree that wires nothing opted out (0.4.0/D5).
    """
    if 'U2' not in enabled:
        return
    wiring = wired_couriers(cfg.root)
    if wiring.unread:
        warn(f'{wiring.unread}, so whether the ledger couriers are '
             f'wired is UNVERIFIABLE — not a finding, and not a pass either '
             f'(U2)')
        return
    if not wiring.couriers:
        return
    wired = list(wiring.couriers)
    found, unreadable = _tree_has_a_row(cfg)
    if unreadable:
        warn(f'{", ".join(unreadable)} could not be read, so whether this tree '
             f'is recording is UNVERIFIABLE — not a finding, and not a pass '
             f'either (U2)')
        return
    if found:
        return
    warn(f'{" and ".join(wired)} {"is" if len(wired) == 1 else "are"} wired in '
         f'{wiring.where} and {cfg.roadmap_dir} holds no ledger row at '
         f'all — this tree is recording NOTHING, silently, because a courier '
         f'fails open by design. Four causes, in the order they cost people '
         f'time: the `pm` make target is not .PHONY (a PM tree IS a `pm/` '
         f'directory, so make exits 0 without reaching the verb); '
         f'`[pm.states.*]` is undeclared, so every work-moving verb refuses; '
         f'`python3` or the transcript path does not resolve; the entries name '
         f'a script that is not there. **`bash tools/hooks/'
         f'cc-ledger-session.sh --self-test` answers all four**. A fifth is '
         f'outside this tree: a session rooted elsewhere loads its own '
         f'settings file and derives its own root, which is what '
         f'`install-hooks --write-settings` and `GDK_LEDGER_ROOT` are for '
         f'(U2)')


def _hook_written(row: dict) -> bool:
    """Did a COURIER write this row?

    The kind AND a `session_id`. The kind is off `ledger.EVENT_KINDS`, the
    writer's own vocabulary — but alone it is not enough: `pm ledger record
    SubagentStop` mints exactly those kinds by hand from inside the checkout,
    and this repo counted sixteen of them as evidence a courier ran when none
    ever had. The session id comes from the hook payload; a hand row has none.
    A courier row lacking one reads as `never` — noisy, never blind.
    """
    from agentic_sdlc.repo.pm import ledger
    if _kind_of(row) not in set(ledger.EVENT_KINDS.values()):
        return False
    session = row.get('session_id')
    return isinstance(session, str) and bool(session.strip())


def _hook_recording_findings(cfg: model.PmConfig, enabled: set[str],
                             warn) -> None:
    """U4 — the couriers are wired, and the last row THEY wrote, with its age.

    **This rule was found by this build recording nothing.** Every wiring
    answer was green and U2 did not fire, because the ledgers were not empty —
    they held the rows this checkout writes itself. **No rule counted row
    KINDS**, so the one fact separating a wired path from a working one went
    unasked; the trap itself is spelled in the WARN below.

    `wired` alone is the tool asserting an outcome it did not observe (rule 4).
    A WARN, never a finding, and a tree that wires nothing stays silent
    (0.4.0/D5).
    """
    if 'U4' not in enabled:
        return
    from agentic_sdlc.repo.pm import ledger
    wiring = wired_couriers(cfg.root)
    if wiring.unread:
        warn(f'{wiring.unread}, so the last hook-written row cannot be read '
             f'beside its wiring — UNVERIFIABLE, not a finding and not a pass '
             f'either (U4)')
        return
    rec = hook_recording(cfg)
    wired = list(wiring.couriers)
    # THE OPT-OUT, and the whole of it: wires nothing AND records nothing.
    # Gating on the config alone went silent on a tree holding an hour-old
    # courier row, wired in a settings file above the repo — the topology this
    # package now ships. The ledger proves the path wherever the config is.
    if not wired and not rec.written:
        return
    if rec.unreadable:
        warn(f'{", ".join(rec.unreadable)} could not be read, so the last '
             f'hook-written row is UNVERIFIABLE — not a finding, and not a '
             f'pass either (U4)')
        return
    events = ' and '.join(sorted(ledger.EVENT_KINDS))
    kinds = '/'.join(dict.fromkeys(ledger.EVENT_KINDS.values()))
    if not rec.written:
        rows, _ = _ledger_rows(cfg)
        held = _kind_census(rows, top=CENSUS_TOP) or 'no rows at all'
        # THE FIX FIRST. It used to sit at the end of 839 characters, behind a
        # thirteen-kind census — the eleven wrapped lines this feature measured.
        warn(f'{" and ".join(wired)} {"is" if len(wired) == 1 else "are"} '
             f'wired in {wiring.where} and no {kinds} row has EVER '
             f'landed in {cfg.roadmap_dir}/ — last hook-written row: '
             f'{recording_phrase(rec)}{_recording_span(rows)}. '
             f'`install-hooks --write-settings` lands '
             f'the block here, and `GDK_LEDGER_ROOT` points a session rooted '
             f'elsewhere at this tree: whether a harness fires the {events} '
             f'hook depends on the session\'s project root, not on '
             f'{wiring.where}. The ledgers hold {held}, which this checkout '
             f'writes itself; `agentic-sdlc pm ledger report` breaks them '
             f'down (U4)')
        return
    # COUNTED, never a finding: the age is what tells live telemetry from
    # telemetry that stopped.
    seen = (f'wired in {wiring.where}' if wiring.where else
            f'wired in no settings file in this checkout, so the config a '
            f'harness loaded lives above it')
    print(f'  RECORDING  last hook-written row: {recording_phrase(rec)} — '
          f'{rec.written} of {rec.total} row(s) in {cfg.roadmap_dir}/ came '
          f'from a courier; {seen}  [{rec.where}] (U4)')


def _emit_sink_findings(cfg: model.PmConfig, enabled: set[str], warn) -> None:
    """U3 — `[emit]` is declared and its sink has never been written to.

    **The same trap as `recording-is-on-or-the-gate-is-red` on a fresh
    surface**: a declared `[emit]` whose sink was never written to looks exactly
    like a tree that opted out. Opting out stays quiet — a tree with no
    `[emit]` gets no line at all.

    A malformed `[emit]` value is exit 2 through `emit.settings()`, never a
    finding — a fact about the input, the way every other config refusal is.
    """
    if 'U3' not in enabled:
        return
    from agentic_sdlc.repo import emit
    if not emit.declared():
        return
    # A malformed value raises here — including `kinds = []`, refused by name
    # rather than read as "no tap emits". So every section this rule reaches
    # emits SOMETHING, and silence is never what the project asked for.
    conf = emit.settings()
    taps = ', '.join(conf.kinds)
    if conf.sink == emit.SINK_STDOUT:
        warn(f'[{emit.SECTION}] declares {emit.SINK_KEY} = '
             f'{emit.SINK_STDOUT!r} (stdout) and {emit.KINDS_KEY} = {taps}, '
             f'and stdout leaves nothing in the tree — whether a tap has ever '
             f'emitted is UNVERIFIABLE here, not a finding and not a pass '
             f'either. A courier reading the stream is what proves it (U3)')
        return
    if conf.sink == emit.SINK_LEDGER:
        rows, unreadable = _ledger_rows(cfg)
        if unreadable:
            warn(f'{", ".join(unreadable)} could not be read, so whether the '
                 f'[{emit.SECTION}] sink has ever been written to is '
                 f'UNVERIFIABLE — not a finding, and not a pass either (U3)')
            return
        emitted = [row for _path, row in rows if _emitted(row, emit.TAPS)]
        if emitted:
            return
        held = _kind_census(rows) or 'no rows at all'
        warn(f'[{emit.SECTION}] declares {emit.SINK_KEY} = '
             f'{emit.SINK_LEDGER!r} and {emit.KINDS_KEY} = {taps}, and no '
             f'event from any of those taps has ever landed in '
             f'{cfg.roadmap_dir}/ — a sink that is DECLARED and silent is a '
             f'contradiction this tree is holding. What the ledgers hold is '
             f'{held}; none of it names a tap. A tree that declares no '
             f'[{emit.SECTION}] emits nothing and is owed no line — this one '
             f'declared one (U3)')
        return
    target = cfg.root / conf.sink
    try:
        written = target.is_file() and bool(
            target.read_text(encoding='utf-8').strip())
    except (OSError, UnicodeDecodeError) as err:
        warn(f'the [{emit.SECTION}] {emit.SINK_KEY} {conf.sink!r} could not be '
             f'read ({err.__class__.__name__}), so whether it has ever been '
             f'written to is UNVERIFIABLE — not a finding, and not a pass '
             f'either  [{cfg.rel(target)}] (U3)')
        return
    if written:
        return
    warn(f'[{emit.SECTION}] declares {emit.SINK_KEY} = {conf.sink!r} and '
         f'{emit.KINDS_KEY} = {taps}, and that sink '
         f'{"is empty" if target.is_file() else "is not in this checkout"} — '
         f'a sink that is DECLARED and silent is a contradiction this tree is '
         f'holding, and it looks exactly like a tree that opted out. A tree '
         f'that declares no [{emit.SECTION}] emits nothing and is owed no '
         f'line; this one declared one  [{cfg.rel(target)}] (U3)')


def _emitted(row: dict, taps: tuple[str, ...]) -> bool:
    """Did a TAP write this row?

    A tap's row NAMES its tap in `kind`, bare (`enter`) or dotted
    (`rung.enter`), so the last dotted segment is the tap. Read off `emit.TAPS`
    rather than a copy of the row-kind list: a rule keyed on a second spelling
    of the schema goes blind the day the copy goes stale.
    """
    return _kind_of(row).rsplit('.', 1)[-1] in taps


def _flow_findings(cfg: model.PmConfig, enabled: set[str], report) -> None:
    """D9/D10 over every `in_progress` milestone; two in progress is two answers."""
    live = (model.in_progress_milestones(cfg)
            if enabled & set(model.FLOW_CHECKS) else [])


    mainline = model.mainline_branch() if 'D10' in enabled and live else ''

    for mid, branch, mfile in live:
        if 'D9' in enabled and not branch:
            report(f'in-progress milestone {mid} declares no branch: — a fresh '
                   f'checkout cannot find where its work lives  [{cfg.rel(mfile)}]')
        if 'D10' in enabled:
            if not branch:
                report(f'in-progress milestone {mid} declares no branch: — D10 '
                       f'needs a branch off the mainline ({mainline!r}) to '
                       f'declare  [{cfg.rel(mfile)}]')
            elif branch == mainline:
                report(f'in-progress milestone {mid} declares branch: {branch!r}, '
                       f'the mainline itself — work must live off '
                       f'{mainline!r}, not on it (D10)  [{cfg.rel(mfile)}]')


def _changelog_answered(cfg: model.PmConfig, enabled: set[str], warn) -> None:
    """D12 — a grain in `done` that answered the changelog question neither way.

    A WARN: the release belt refuses at the rung that ships, and reddening
    every inner-loop gate over an unwritten sentence is how a surface gets
    scrolled past. `none` is an ANSWER; this names silence.

    SHIPPED MILESTONES ARE OUT OF SCOPE — not history rewriting. 168 grains
    closed before the field existed, and asking them all for a sentence nobody
    will write is 351-of-359 again.
    """
    if 'D12' not in enabled:
        return
    from agentic_sdlc.repo.pm import changelog as clog
    graded = silent = 0
    for gid, grain in sorted(model.grain_index(cfg).items()):
        if grain.kind not in model.FLOW_KINDS:
            continue
        status = grain.field(model.FIELD_STATUS)
        if model.category_of(cfg, grain.kind, status) != model.DONE_CATEGORY:
            continue
        if _shipped_parent(cfg, grain):
            continue
        graded += 1
        if grain.field(clog.FIELD).strip():
            continue
        silent += 1
        warn(f'{grain.kind} {gid} is {status!r} ({model.DONE_CATEGORY}) and '
             f'carries no `{clog.FIELD}:` — `agentic-sdlc pm set {gid} '
             f'{clog.FIELD} "<sentence>"`, or `{clog.NEEDS_NONE}` to say it '
             f'earned no consumer-visible line (D12)  [{cfg.rel(grain.path)}]')
    print(f'  CHANGELOG  {graded - silent} of {graded} closed grain(s) '
          f'answered, shipped milestones excluded (D12)')


def _shipped_parent(cfg: model.PmConfig, grain) -> bool:
    """Is this grain's milestone in `done`? Followed through the bindings."""
    mid = model.milestone_of(cfg, grain.gid)
    if not mid:
        return False
    parent = model.grain_index(cfg).get(mid)
    if parent is None:
        return False
    return model.category_of(cfg, model.GRAIN_MILESTONE,
                             parent.field(model.FIELD_STATUS)
                             ) == model.DONE_CATEGORY


def _containment(cfg: model.PmConfig, enabled: set[str], report) -> None:
    """D11 — a parent in `done` over a child that is not, at every level.

    ONE walk off `BINDS_TO`; a FINDING unconditionally, because a parent
    closing over an open child makes its own census a lie (rule 4). No opt-out
    FIELD — `fix_milestone:` was one and defaulted to opted-out, silently. The
    opt-out is the BINDING, and V7 counts what it returns to the pool.
    """
    if 'D11' not in enabled:
        return
    index = model.grain_index(cfg)
    graded = 0
    for child in sorted(index.values(), key=lambda g: g.gid):
        bind = model.BINDS_TO.get(child.kind)
        if bind is None or not child.binding:
            continue
        parent = index.get(child.binding)
        if parent is None:
            continue
        graded += 1
        p_status = parent.field(model.FIELD_STATUS)
        if model.category_of(cfg, parent.kind, p_status) != model.DONE_CATEGORY:
            continue
        c_status = child.field(model.FIELD_STATUS)
        if model.category_of(cfg, child.kind, c_status) == model.DONE_CATEGORY:
            continue
        report(f'{parent.kind} {parent.gid} is {p_status!r} '
               f'({model.DONE_CATEGORY}) but {child.kind} {child.gid} is '
               f'{c_status!r} ({_cat(cfg, child.kind, c_status)}) — a parent '
               f'does not close over an unresolved child; finish it, or '
               f'`agentic-sdlc pm remove {parent.gid} {child.gid}` returns it '
               f'to the pool (D11)  [{cfg.rel(child.path)}]')
    print(f'  CONTAINMENT  {graded} bound child/ren graded against their '
          f'parent (D11)')
    for gid, grain in sorted(index.items()):
        # PRESENCE, not value: an empty one is the shape that gated nothing.
        for field, why in sorted(model.RETIRED_FIELDS.items()):
            if not grain.declares(field):
                continue
            report(f'{grain.kind} {gid} carries `{field}:` — {why} (D11)  '
                   f'[{cfg.rel(grain.path)}]')


def _unbound_rows(cfg: model.PmConfig, enabled: set[str], report, warn) -> None:
    """The unbound family one level down from R1, in both directions (V7 at the
    top of this module). COUNTED, never a finding, because a tree mid-planning
    legitimately has many and a gate that reddens on planning gets switched off.
    """
    if 'V7' not in enabled:
        return
    for kind, ids in sorted(model.unbound_grains(cfg).items()):
        field = model.BINDS_TO[kind][1]
        print(f'  UNBOUND  {len(ids)} {kind}(s) name no {field}: — '
              f'{", ".join(ids)}; `agentic-sdlc pm add <{field}-id> <id>` '
              f'binds and sequences one (V7)')
    _sequence_rows(cfg, report, warn)


def _sequence_rows(cfg: model.PmConfig, report, warn) -> None:
    """Every container's `order` against what it holds — one walk, every level."""
    index = model.grain_index(cfg)
    # The ROOT is R1's, not this walk's: the plan has carried its own rule and
    # its own line, and two lines for one fact is a second
    # scoreboard.
    #
    # `BINDS_TO` and NOT `[pm.contains]`: that key says what `pm add` may
    # WRITE, and reading it here let a narrowed mapping ungate the level it
    # dropped. No config narrows what an `order` says about what it holds.
    holds = {parent for parent, _field in model.BINDS_TO.values()}
    parents = [g for g in index.values()
               if g.kind in holds and g.kind != model.ROOT_KIND]
    unsequenced: dict[str, int] = {}
    for parent in sorted(parents, key=lambda g: g.gid):
        seq = model.sequence_census(cfg, parent, index)
        for gid in seq.dangling:
            child = index[gid]
            bind = model.BINDS_TO.get(child.kind)
            report(f'DANGLING: {parent.gid} sequences {gid} in its `order` and '
                   f'does not hold it — {gid} names '
                   + (f'{child.binding or "no " + bind[0]}' if bind
                      else 'no parent')
                   + f'; `agentic-sdlc pm add {parent.gid} {gid}` binds it, '
                     f'`pm remove` takes the entry out (V7)')
        for gid in seq.unverifiable:
            warn(f'UNVERIFIABLE: {parent.gid} sequences {gid} in its `order` '
                 f'and no grain in this tree declares that id — DANGLING if it '
                 f'was never written, UNVERIFIABLE if it was retired (V7)')
        for gid in seq.unsequenced:
            unsequenced[index[gid].kind] = unsequenced.get(index[gid].kind, 0) + 1
    # Rule 4: a walk that graded nothing says so, and the count is what made
    # the narrowing above invisible for as long as it lasted.
    graded = len(parents)
    if graded:
        print(f'  SEQUENCE  {graded} container(s) graded against their `order`')
    for kind, n in sorted(unsequenced.items()):
        # COUNTED: `order` is optional per container, so a child nobody has
        # placed is a decision not taken — never a finding.
        print(f'  UNSEQUENCED  {n} {kind}(s) are bound and in no parent\'s '
              f'`order` — `agentic-sdlc pm add <parent-id> <id> [--position N '
              f'| --before <id> | --after <id>]` places one (V7)')


def _unbound_family(cfg: model.PmConfig, enabled: set[str], order: list[str],
                    report, warn) -> None:
    """R1-R4 and R6 — the plan and the tree held to each other.

    **This is THE UNBOUND FAMILY, whose first member is the milestone-to-release
    edge**, not a set of milestone-specific rules: every level has the same pair
    — a binding that names nothing, and a grain that names no binding. Naming
    the family here costs a sentence; naming it later costs a rename in every
    consumer's output that greps these lines.
    """
    claims = model.version_claims(cfg)
    scheduled = set(order)
    root = model.root_grain(cfg)

    if 'R1' in enabled and root is not None:
        # The root's half of the sequence pair, spelled here because the plan
        # is the one container a config can turn off on its own.
        seq = model.sequence_census(cfg, root)
        for mid in seq.unverifiable:
            # Never a failure: the row survives its milestone on purpose.
            warn(f'UNBOUND: {mid} is in '
                 f'{cfg.rel(model.releases_file(cfg))} `order` and no milestone '
                 f'in this tree declares that id — DANGLING if it was never '
                 f'written, UNVERIFIABLE if it was retired (R1)')
        if seq.unsequenced:
            # COUNTED, not a finding: authoring a milestone and scheduling it
            # are separate acts.
            print(f'  UNSEQUENCED  {len(seq.unsequenced)} milestone(s) are on '
                  f'no plan — {", ".join(seq.unsequenced)}; `agentic-sdlc pm '
                  f'add {root.gid} <milestone-id>` schedules one (R1)')

    if 'R2' in enabled:
        # Backlog: a named, counted line, never a finding — a healthy tree has
        # many (the same reason as `_unbound_rows`).
        backlog = [mid for _, mid in model.known_milestones(cfg)
                   if mid and mid not in scheduled
                   and not model.milestone_version(cfg, mid)]
        if backlog:
            print(f'  BACKLOG  {len(backlog)} milestone(s) declare no '
                  f'version: and are not proposed as releases — '
                  f'{", ".join(sorted(backlog))} (R2)')

    if 'R3' in enabled:
        seen: dict[str, list[str]] = {}
        for version, mid in claims:
            seen.setdefault(version, []).append(mid)
        for version, mids in seen.items():
            if len(mids) > 1:
                report(f'version: {version} is claimed by {len(mids)} '
                       f'milestones — {", ".join(sorted(mids))}; a version '
                       f'names one release, and which one ships is otherwise '
                       f'decided by whichever document was read first (R3)')

    if 'R4' in enabled and order:
        # History is a prefix. This is the invariant that makes "next = the
        # first unshipped entry" CORRECT rather than merely usual, and it is
        # what lets version_at = "start" mean anything.
        first_open = None
        for mid in order:
            if model.entry_is_shipped(cfg, mid):
                if first_open is not None:
                    report(f'history is not a prefix: {mid} has shipped and '
                           f'sits AFTER {first_open}, which has not — '
                           f'`agentic-sdlc pm add` re-sequences the plan (R4)')
            elif first_open is None and not model.entry_is_dangling(cfg, mid):
                first_open = mid

    if 'R6' in enabled:
        last = model.last_shipped_index(cfg)
        for i, mid in enumerate(order):
            if i > last or model.entry_is_shipped(cfg, mid):
                continue
            milestone = model.grain(cfg, mid, model.GRAIN_MILESTONE)
            if milestone is None:
                continue
            status = milestone.field(model.FIELD_STATUS)
            report(f'{mid} sits at position {i + 1}, behind the last '
                   f'shipped release, and is {status!r} — its work went out '
                   f'under someone else\'s version and the record never '
                   f'moved (R6)')
        for version, mid in claims:
            milestone = model.grain(cfg, mid, model.GRAIN_MILESTONE)
            status = milestone.field(model.FIELD_STATUS) if milestone else ''
            done = model.category_of(cfg, model.GRAIN_MILESTONE,
                                     status) == model.DONE_CATEGORY
            if done and mid not in scheduled:
                report(f'milestone {mid} is {status!r}, claims version '
                       f'{version} and is on no plan — a milestone that '
                       f'finished without ever being scheduled as a '
                       f'release (R6)')


def _release_findings(cfg: model.PmConfig, enabled: set[str], report, warn) -> None:
    """The release family. R1-R4 and R6 are in `_unbound_family`; R5, below, is
    the version file against the CURRENT release — a POSITION in `order`, never
    a parse, so it fits bump-at-start and bump-at-close both ([pm] version_at)
    and has no opinion about what a version string looks like.
    """
    if not enabled & set(model.RELEASE_CHECKS):
        return
    # A plan that is THERE and unreadable is a finding, not the absence of one:
    # "declares no `order`" over a BOM-damaged file is rule 4's first sin.
    defect = model.plan_defect(cfg)
    if defect is not None:
        report(f'{cfg.rel(model.releases_file(cfg))} {defect} — R5 cannot read '
               f'the plan, so {cfg.version_file} was NOT graded (R5)')
        return
    order = model.declared_order(cfg)
    _unbound_family(cfg, enabled, order, report, warn)
    if 'R5' not in enabled:
        return
    if not order:
        # A tree mid-adoption has no plan yet; a rule that fails every fresh
        # consumer gets switched off.
        warn(f'R5 is enabled and {cfg.rel(model.releases_file(cfg))} declares '
             f'no `order` — nothing to grade {cfg.version_file} against; '
             f'`agentic-sdlc pm add {model.root_id(cfg)} <milestone-id>` '
             f'writes the plan')
        return
    accepted, why = model.graded_release_accepts(cfg)
    current = accepted[0] if accepted else None
    if current is None:
        # The reason is READ, never invented: "every entry has shipped" over a
        # tree where none had was a confident wrong answer at exit 0 (B3).
        warn(f'R5 has nothing to grade {cfg.version_file} against — {why} '
             f'(under [pm] version_at = {cfg.version_at!r})')
        return
    version = model.shipped_version(cfg)
    if version is None:
        report(f'no version found in {cfg.version_file} — R5 cannot verify it '
               f'against the current release {current!r} (R5)')
        return
    if version in accepted:
        return
    mid = model.milestone_of_version(cfg, current)
    claims = (f'the milestone {mid!r} claims it'
              if mid is not None
              else 'no milestone claims it — an `order` entry nothing carries')
    named = ' or '.join(repr(v) for v in accepted)
    report(f'{cfg.version_file} version {version!r} does not match '
           f'{named} ({claims}), which is the '
           f'{"first unshipped" if cfg.version_at == model.VERSION_AT_START else "last shipped"} '
           f'entry in {cfg.rel(model.releases_file(cfg))} under [pm] '
           f'version_at = {cfg.version_at!r} (R5)')


def _census(cfg: model.PmConfig, n_milestones: int, n_features: int,
            n_stories: int, n_bugs: int) -> str:
    """`'4 milestone(s), 44 feature(s), 79 story/ies, 11 bug(s)'` — with every
    narrowing each walk made, rendered beside the count it narrowed.

    Pooled counts are the POOL's rather than the drift walk's on purpose: a
    document with damaged frontmatter declares no `id:`, so no descent reaches
    it, and a census counting only what the descent saw would quietly drop the
    document `unkeyed_documents` just reported by name.
    """
    if model.is_pooled(cfg):
        return ', '.join(model.pool_census(cfg, kind, label) for kind, label in
                         ((model.GRAIN_MILESTONE, 'milestone(s)'),
                          (model.GRAIN_FEATURE, 'feature(s)'),
                          (model.GRAIN_STORY, 'story/ies'),
                          (model.GRAIN_BUG, 'bug(s)')))
    census = (f'{n_milestones} milestone(s), {n_features} feature(s), '
              f'{n_stories} story/ies')
    # `Walk` renders every narrowing itself, so a new filter discloses without an edit here.
    census += model.tree_walk(cfg).disclosures()
    return census + f', {n_bugs} bug(s)'


def _verdict(cfg: model.PmConfig, findings: list[str], warnings: list[str],
             census: str, v_on: set[str], v_census: dict) -> int:
    """The census + verdict; warnings are counted separately and never decide the code."""
    print()
    if v_census:
        census += f', {v_census["refs"]} ref(s)'
        if v_census['unverifiable']:
            census += (f' ({v_census["unverifiable"]} UNVERIFIABLE — the ref '
                       f'names a milestone no longer in the tree)')
    what = 'status-drift / integrity violation(s)' if v_on else 'status-drift violation(s)'
    warned = f'; {len(warnings)} warning(s)' if warnings else ''
    if findings:
        print(f'[check:pm] FAIL — {len(findings)} {what} across {census}'
              f'{warned}')
        return 1
    clean = 'no PM-tree drift or integrity problems' if v_on else 'no PM-tree status drift'
    print(f'[check:pm] PASS — {clean}; scanned {census}{warned}')
    return 0
