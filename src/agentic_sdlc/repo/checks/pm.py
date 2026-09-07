"""check pm — the active PM tree's statuses do not contradict each other.

Every rule asks a CATEGORY (`todo`/`in_progress`/`done`), never a word, off the same
predicates in `repo/pm/model` that `pm` writes with. Which rules run is `[pm] checks`
(default: D1-D6 + V1-V5; V6, U1, D9/D10 and the R family are opt-in).

DRIFT (each FAILs, naming the path):
  D1  a `reviewed:` pointer naming a file that is not there
  D4  a status the project never declared, for any grain kind
  R1  an `order` entry no milestone claims (WARN), or a `version:` on no plan (FAIL)
  R3  two milestones claiming one `version:`
  R4  history is a prefix — a shipped release sitting after an unshipped one
  R5  the version file equals the CURRENT release in `order` ([pm] version_at)
  R6  a release behind the last shipped one whose milestone never closed, and a
      `done` milestone whose version is on no plan
  D9  an `in_progress` milestone declares a `branch:`
  D10 that branch is not the mainline (`[repo_hygiene] mainline`, `origin/`-stripped)
WARN (a line, never the exit code; both grains and both categories named):
  D2  a feature in `todo` while all its stories are `done`
  D3  a milestone in `done` with a feature that is not
  D5  a story out of `todo` under a feature still in it
  D6  a milestone in `todo` whose features are all `done`
  U1  a DECLARED state no grain of that kind has ever held, with the count in use
  U2  the ledger couriers are wired in `.claude/settings.json` and the tree holds
      no row at all — recording that goes nowhere, which is silent by construction
  V7  a binding (`milestone:`/`feature:`) naming a grain that is not in the tree,
      or one of the wrong kind. An EMPTY binding is UNBOUND — a counted line
      below, never a finding
  READY  a grain past `todo` with an empty scaffolded section (`## Ship criterion`,
         `## Acceptance criteria`, `## Proof budget`), a story in progress with no
         `owner:`, no stories, no `phase:`, no `branch:`, or (a milestone) no
         `handoff.md` — never auto-minted, so `pm new handoff <id>` is the fix
  R2  the BACKLOG census — milestones declaring no `version:`; a counted line, never a finding
  UNBOUND  the same family one level down (V7): features naming no `milestone:`,
      stories naming no `feature:`, bugs naming no `milestone:`. Counted, never a
      finding — *nothing said* is a plan, *something wrong said* is drift

Archived milestones are out of scope; a zero census FAILS.
"""
from __future__ import annotations

import sys

from agentic_sdlc.repo.pm import model


def run() -> int:
    try:
        return _run()
    except model.ConfigError as err:
        # Exit 2 for the whole walk: the flow is read lazily, so a tree that
        # declared none is refused at the first category question. EVERY
        # defect, not the first, and the FLOW first among them — a real
        # adoption is wrong in more than one way at once.
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

    mfiles = [g.path for g in model.milestones(cfg)]
    if not mfiles:
        print()
        print(f'[check:pm] FAIL — no milestones found under {cfg.roadmap_dir}/ '
              f'(wrong [pm] roadmap_dir, or an empty tree?)')
        return 1

    # A document with no readable `id:`, and two documents claiming one, are
    # V1's — "this frontmatter is well-formed" — and they are reported from
    # `validate.run` below so that `pm validate` and this gate cannot disagree
    # about a file neither of them can key on.

    # Always walked for the census; reported only under D4.
    bug_findings, n_bugs = model.bug_status_findings(cfg)
    if 'D4' in enabled:
        for path, why in bug_findings:
            report(f'{cfg.rel(path)}: {why}')

    n_features, n_stories = _drift_walk(cfg, enabled, mfiles, report, warn)

    _unbound_rows(cfg, enabled)
    _flow_findings(cfg, enabled, report)
    _unused_states(cfg, enabled, warn)
    _recording_findings(cfg, enabled, warn)
    _release_findings(cfg, enabled, report, warn)

    # --- V1-V6: structural + referential integrity ------------------------
    v_on = enabled & set(model.VALIDATE_CHECKS)
    v_census: dict = {}
    if v_on:
        from agentic_sdlc.repo.pm import validate as _validate
        v_findings, v_census = _validate.run(cfg, v_on)
        for msg in v_findings:
            report(msg)

    return _verdict(cfg, findings, warnings,
                    _census(cfg, len(mfiles), n_features, n_stories, n_bugs),
                    v_on, v_census)


# D2's and D6's shared tail; neither rule has an opinion about which state is next.
ADVANCE_IT = 'advance it (`done` is the LAST state, not the next one)'


def _cat(cfg: model.PmConfig, kind: str, status: str) -> str:
    """The category a WARN line prints beside a word, or 'undeclared'."""
    return model.category_of(cfg, kind, status) or 'undeclared'


def _drift_walk(cfg: model.PmConfig, enabled: set[str], mfiles,
                report, warn) -> tuple[int, int]:
    """D1-D6 over every grain plus the READY warnings; returns the (feature, story) census."""
    n_features = 0
    n_stories = 0

    for mfile in mfiles:
        # The DOCUMENT, not a directory: a pooled tree has no per-milestone
        # directory, and the two lines below that wanted one now take the
        # document's own parent, which is the pool.
        mdir = mfile.parent
        mid = model.field_of(mfile, 'id')
        mstat = model.field_of(mfile, 'status')
        m_cat = model.category_of(cfg, 'milestone', mstat)
        m_started = model.left_todo(cfg, 'milestone', mstat)

        if 'D4' in enabled:
            reason = model.undeclared_status(cfg, 'milestone', mstat)
            if reason:
                report(f'milestone {mid}: {reason}  [{cfg.rel(mfile)}]')

        if m_started:
            if not model.unquote(model.field_of(mfile, 'branch')):
                warn(f'milestone {mid} is {mstat!r} with no branch: — past '
                     f'todo, and a fresh checkout cannot find where its work '
                     f'lives  [{cfg.rel(mfile)}]')
            why = model.empty_section(mfile, model.SHIP_HEADING)
            if why:
                warn(f'milestone {mid} is {mstat!r} and {why} — past todo, '
                     f'and nothing says what done means  [{cfg.rel(mfile)}]')
            # The doc is deliberately never auto-minted, so its ABSENCE is the
            # signal; the hint names the one verb that fills it. IN_PROGRESS
            # only, not every started milestone: a handoff is a cold-start aid
            # and nobody picks up a finished milestone, so warning on `done`
            # would fire once per historical milestone on every consumer's tree.
            handoff = model.shared_doc(cfg, mfile, model.HANDOFF_FILE_NAME)
            if m_cat == model.IN_PROGRESS and not handoff.is_file():
                warn(f'milestone {mid} is {mstat!r} with no '
                     f'{model.HANDOFF_FILE_NAME} — past todo, and a cold '
                     f'session has nowhere to start; `pm new handoff {mid}` '
                     f'mints one  [{cfg.rel(handoff)}]')

        views = [model.read_feature(cfg, ffile)
                 for ffile in model.feature_files(cfg, mid)]
        # One `holds` answers both D6's census and D3's per-feature question.
        finished = model.holds(cfg, 'feature',
                               ((v.fid, v.status) for v in views),
                               model.DONE_CATEGORY)
        unfinished = {fid for fid, _ in finished.blockers}
        for view in views:
            frel = cfg.rel(view.path)
            n_features += 1
            n_stories += view.total

            if 'D4' in enabled:
                reason = model.undeclared_status(cfg, 'feature', view.status)
                if reason:
                    report(f'feature {view.fid}: {reason}  [{frel}]')

            if ('D3' in enabled and m_cat == model.DONE_CATEGORY
                    and view.fid in unfinished):
                warn(f'milestone {mid} is {mstat!r} ({m_cat}) but feature '
                     f'{view.fid} is {view.status!r} '
                     f'({_cat(cfg, "feature", view.status)}) — the milestone '
                     f'says everything inside it is finished and this '
                     f'feature says otherwise (D3)  [{frel}]')

            if 'D1' in enabled:
                reason = model.drift_dangling_record(cfg, view.fid)
                if reason:
                    report(f'feature {view.fid}: {reason} — point it at a real '
                           f'file or remove the field  [{frel}]')

            if m_started and not view.phase:
                warn(f'milestone {mid} is {mstat!r} and feature {view.fid} '
                     f'carries no phase: — past todo, and the board cannot '
                     f'order it  [{frel}]')
            if model.left_todo(cfg, 'feature', view.status):
                if view.total == 0:
                    warn(f'feature {view.fid} is {view.status!r} with no '
                         f'stories — past todo, and nothing to build  [{frel}]')
                why = model.empty_section(view.path, model.SHIP_HEADING)
                if why:
                    warn(f'feature {view.fid} is {view.status!r} and {why} — '
                         f'past todo, and nothing says what done means'
                         f'  [{frel}]')
                # The anti-bloat contract, and it had never been verified to
                # exist: the template carries the section, the milestone's own
                # rules call it "where test bloat is stopped, not at review",
                # and an empty one is how a feature ships twice its budget with
                # nobody able to say so. `empty_section` already answers this
                # question for two other headings; this is one constant and one
                # call in the loop that already runs.
                why = model.empty_section(view.path, model.PROOF_HEADING)
                if why:
                    warn(f'feature {view.fid} is {view.status!r} and {why} — '
                         f'past todo, and nothing says what it should COST'
                         f'  [{frel}]')

            for sfile in view.stories:
                sid = model.field_of(sfile, 'id')
                sstat = model.field_of(sfile, 'status')
                srel = cfg.rel(sfile)
                if 'D4' in enabled:
                    reason = model.undeclared_status(cfg, 'story', sstat)
                    if reason:
                        report(f'story {sid}: {reason}  [{srel}]')
                if model.left_todo(cfg, 'story', sstat):
                    why = model.empty_section(sfile, model.ACCEPTANCE_HEADING)
                    if why:
                        warn(f'story {sid} is {sstat!r} and {why} — past todo, '
                             f'and nothing says what must be true  [{srel}]')
                if (_cat(cfg, 'story', sstat) == model.IN_PROGRESS
                        and not model.unquote(model.field_of(sfile, 'owner'))):
                    # A LIVE BUG, not a tidy-up. `pm-execution.md` step 1 says
                    # to set `owner:` in the same edit as the claim, two
                    # modules READ the field, and nothing asked whether it was
                    # there — so a tree could run for a milestone with every
                    # story unowned.
                    warn(f'story {sid} is {sstat!r} '
                         f'({model.IN_PROGRESS}) and carries no owner: — '
                         f'somebody is working on it and the tree cannot say '
                         f'who  [{srel}]')
                if 'D5' in enabled and model.drift_ahead_of_parent(
                        cfg, sstat, view.status):
                    warn(f'story {sid} is {sstat!r} '
                         f'({_cat(cfg, "story", sstat)}) but its feature '
                         f'{view.fid} is still {view.status!r} '
                         f'({_cat(cfg, "feature", view.status)}) — the story '
                         f'is at work and the feature says it has not '
                         f'started (two places in this tree disagree, D5)'
                         f'  [{srel}]')

            if 'D2' in enabled:
                reason = model.drift_stalled(cfg, view)
                if reason:
                    warn(f'feature {view.fid}: {reason} '
                         f'({_cat(cfg, "feature", view.status)}) — all '
                         f'{view.total} stories are {model.DONE_CATEGORY}; '
                         f'{ADVANCE_IT} (D2)  [{frel}]')

        if ('D6' in enabled and m_cat == model.TODO
                and finished.counted > 0 and finished):
            warn(f'milestone {mid} is {mstat!r} ({m_cat}) but all '
                 f'{finished.counted} features are {model.DONE_CATEGORY} — '
                 f'you finished the features and the milestone still calls '
                 f'itself {mstat!r}; {ADVANCE_IT} (D6)  [{cfg.rel(mfile)}]')

    return n_features, n_stories


def _unused_states(cfg: model.PmConfig, enabled: set[str], warn) -> None:
    """U1 — a state the project DECLARED and no grain has ever held.

    A WARN with the count, never a finding: a tree mid-adoption legitimately has
    unused states, and a rule that reddens every fresh consumer is undone within
    a version. What it buys is that the fact stays VISIBLE after the install
    scrolls away — the tool's most valuable idea, the conveyor, was invisible to
    the tool.
    """
    if 'U1' not in enabled:
        return
    for kind in model.FLOW_KINDS:
        counts = model.state_usage(cfg).get(kind)
        if not counts:
            continue
        unused = [state for state, n in counts.items() if n == 0]
        if not unused or len(unused) == len(counts):
            # All of them unused means the tree holds no grain of this kind at
            # all, which is a different fact and not this rule's to report.
            continue
        warn(f'{kind}: {len(counts) - len(unused)} of {len(counts)} declared '
             f'state(s) are in use; {", ".join(unused)} '
             f'{"has" if len(unused) == 1 else "have"} never been held by any '
             f'{kind} in this tree — declared and unused is a flow the project '
             f'is not running (U1)')


def _tree_has_a_row(cfg: model.PmConfig) -> tuple[bool, list[str]]:
    """(does any ledger hold a row, the ledgers this could not read).

    Both homes (0.4.0/D3), because the question is whether recording happens at
    all. Existence is not enough: an empty file is what a courier leaves when it
    created the file and then refused the row.

    **An unreadable ledger is neither answer.** Returning `True` silenced this
    rule for the WHOLE tree on the first path that raised, with no line
    printed; it is reported as unverifiable and the scan continues.
    """
    from agentic_sdlc.repo.pm import ledger
    paths = [ledger.grainless_path(cfg.roadmap)]
    paths += [ledger.ledger_for(cfg, g.gid) for g in model.milestones(cfg)]
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
    nobody could tell.** A courier fails open by design, so its refusals go to
    a stderr nobody reads — entries never pasted, a `pm` target that is not
    `.PHONY`, an undeclared `[pm.states.*]`, no `python3`: every one produces
    zero rows and zero complaint.

    **A tree that wires nothing is SILENT.** It opted out, and this package
    does not conscript (0.4.0/D5). A settings file that will not parse is
    UNVERIFIABLE, not a failure.
    """
    if 'U2' not in enabled:
        return
    settings = cfg.root / model.AGENT_SETTINGS
    if not settings.is_file():
        return
    try:
        text = model.read_raw(settings)
    except (OSError, UnicodeDecodeError) as err:
        warn(f'{model.AGENT_SETTINGS} could not be read '
             f'({err.__class__.__name__}), so whether the ledger couriers are '
             f'wired is UNVERIFIABLE — not a finding, and not a pass either '
             f'(U2)')
        return
    wired = sorted(name for name in model.LEDGER_COURIERS if name in text)
    if not wired:
        return
    found, unreadable = _tree_has_a_row(cfg)
    if unreadable:
        warn(f'{", ".join(unreadable)} could not be read, so whether this tree '
             f'is recording is UNVERIFIABLE — not a finding, and not a pass '
             f'either (U2)')
        return
    if found:
        return
    warn(f'{" and ".join(wired)} {"is" if len(wired) == 1 else "are"} wired in '
         f'{model.AGENT_SETTINGS} and {cfg.roadmap_dir} holds no ledger row at '
         f'all — this tree is recording NOTHING, silently, because a courier '
         f'fails open by design. Four causes, in the order they cost people '
         f'time: the `pm` make target is not .PHONY (a PM tree IS a `pm/` '
         f'directory, so make exits 0 without reaching the verb); '
         f'`[pm.states.*]` is undeclared, so every work-moving verb refuses; '
         f'`python3` or the transcript path does not resolve; the entries name '
         f'a script that is not there. **`bash tools/hooks/'
         f'cc-ledger-session.sh --self-test` answers all four** (U2)')


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


def _unbound_rows(cfg: model.PmConfig, enabled: set[str]) -> None:
    """The unbound family one level down from R1: a feature naming no
    milestone, a story naming no feature, a bug naming no milestone.

    Counted lines, never findings and never in the exit code — a tree
    mid-planning legitimately has many, and a gate that reddens on planning is
    a gate people switch off. The BROKEN half is V7's own finding.

    Called from the run rather than from `_unbound_family`, which only executes
    when an R rule is enabled and none is by default.
    """
    if 'V7' not in enabled:
        return
    for kind, ids in sorted(model.unbound_grains(cfg).items()):
        field = model.BINDS_TO[kind][1]
        print(f'  UNBOUND  {len(ids)} {kind}(s) name no {field}: — '
              f'{", ".join(ids)}; `agentic-sdlc pm set <id> {field} '
              f'<{field}-id>` binds one (V7)')


def _unbound_family(cfg: model.PmConfig, enabled: set[str], order: list[str],
                    report, warn) -> None:
    """R1-R4 and R6 — the plan and the tree held to each other.

    **This is THE UNBOUND FAMILY, whose first member is the milestone-to-release
    edge**, not a set of milestone-specific rules. Every level of the tree has
    the same pair: a binding that names nothing, and a grain that names no
    binding. When 0.4.0 makes authoring separate from binding everywhere, a
    feature with no milestone and a story with no feature join this census as
    further ROWS rather than as new rules — naming the family now costs a
    sentence, and naming it later costs a rename in every consumer's output
    that greps these lines.
    """
    claims = model.version_claims(cfg)
    scheduled = set(order)

    if 'R1' in enabled:
        for version in order:
            claimants = model.milestones_of_version(cfg, version)
            if claimants:
                continue
            # The concept the tree already has for a ref into a milestone that
            # is gone: never a failure, because the row survives its milestone
            # on purpose (ROADMAP.md's only real job, now retired).
            warn(f'UNBOUND: {version} is in '
                 f'{cfg.rel(model.releases_file(cfg))} `order` and no milestone '
                 f'declares version: {version} — DANGLING if it was never '
                 f'written, UNVERIFIABLE if its milestone was retired (R1)')
        for version, mid in claims:
            if version not in scheduled:
                report(f'UNBOUND: milestone {mid} declares version: {version} '
                       f'and {cfg.rel(model.releases_file(cfg))} `order` does '
                       f'not carry it — UNSCHEDULED; `agentic-sdlc pm order '
                       f'--append {version}` puts it on the plan (R1)')

    if 'R2' in enabled:
        # Backlog: a named, counted line, never a finding. A healthy tree has
        # many, and a gate that reddens on planning is a gate people switch off.
        bound = {mid for _, mid in claims}
        backlog = [mid for _, mid in model.known_milestones(cfg)
                   if mid and mid not in bound]
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
                       f'decided by a directory NAME (R3)')

    if 'R4' in enabled and order:
        # History is a prefix. This is the invariant that makes "next = the
        # first unshipped entry" CORRECT rather than merely usual, and it is
        # what lets version_at = "start" mean anything.
        first_open = None
        for version in order:
            if model.release_is_shipped(cfg, version):
                if first_open is not None:
                    report(f'history is not a prefix: {version} has shipped and '
                           f'sits AFTER {first_open}, which has not — '
                           f'`agentic-sdlc pm order` re-sequences the plan (R4)')
            elif first_open is None and not model.release_is_unverifiable(cfg, version):
                first_open = version

    if 'R6' in enabled:
        last = model.last_shipped_index(cfg)
        for i, version in enumerate(order):
            if i > last or model.release_is_shipped(cfg, version):
                continue
            mid = model.milestone_of_version(cfg, version)
            if mid is None:
                continue
            mfile = model.milestone_file(cfg, mid)
            status = model.field_of(mfile, 'status') if mfile else ''
            report(f'{version} sits at position {i + 1}, behind the last '
                   f'shipped release, and its milestone {mid} is {status!r} — '
                   f'its work went out under someone else\'s version and the '
                   f'record never moved (R6)')
        for version, mid in claims:
            mfile = model.milestone_file(cfg, mid)
            status = model.field_of(mfile, 'status') if mfile else ''
            done = model.category_of(cfg, 'milestone', status) == model.DONE_CATEGORY
            if done and version not in scheduled:
                report(f'milestone {mid} is {status!r} and its version '
                       f'{version} is on no plan — a milestone that finished '
                       f'without ever being scheduled as a release (R6)')


def _release_findings(cfg: model.PmConfig, enabled: set[str], report, warn) -> None:
    """The release family: the plan (`order`) and the tree held to each other.

    R1-R4 and R6 are the unbound family, in `_unbound_family`. R5, below, is the
    version file against the CURRENT release — a POSITION in `order`, never a
    parse, so it fits bump-at-start and bump-at-close both ([pm] version_at) and
    has no opinion about what a version string looks like.
    """
    if not enabled & set(model.RELEASE_CHECKS):
        return
    # A plan that is THERE and unreadable is a finding, not the absence of a
    # plan: saying "declares no `order`" over a BOM-damaged or fence-eaten file
    # is rule 4's first sin — passing over what was never measured.
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
        # A tree mid-adoption has no plan yet. Reddening it would be milestone
        # risk 1: a rule that fails every fresh consumer gets switched off.
        warn(f'R5 is enabled and {cfg.rel(model.releases_file(cfg))} declares '
             f'no `order` — nothing to grade {cfg.version_file} against; '
             f'`agentic-sdlc pm order --append <version>` writes the plan')
        return
    current, why = model.graded_release(cfg)
    if current is None:
        # The reason is READ, never invented: saying "every entry has shipped"
        # over a tree where none had was a confident wrong answer at exit 0
        # (review B3).
        warn(f'R5 has nothing to grade {cfg.version_file} against — {why} '
             f'(under [pm] version_at = {cfg.version_at!r})')
        return
    version = model.shipped_version(cfg)
    if version is None:
        report(f'no version found in {cfg.version_file} — R5 cannot verify it '
               f'against the current release {current!r} (R5)')
        return
    if version == current:
        return
    mid = model.milestone_of_version(cfg, current)
    claims = (f'the milestone {mid!r} claims it'
              if mid is not None
              else 'no milestone claims it — an `order` entry nothing carries')
    report(f'{cfg.version_file} version {version!r} does not match the current '
           f'release {current!r} ({claims}), which is the '
           f'{"first unshipped" if cfg.version_at == model.VERSION_AT_START else "last shipped"} '
           f'entry in {cfg.rel(model.releases_file(cfg))} under [pm] '
           f'version_at = {cfg.version_at!r} (R5)')


def _census(cfg: model.PmConfig, n_milestones: int, n_features: int,
            n_stories: int, n_bugs: int) -> str:
    """`'4 milestone(s), 44 feature(s), 79 story/ies, 11 bug(s)'` — with every
    narrowing each walk made, rendered beside the count it narrowed.

    Pooled: each pool renders its OWN census, because that is the walk that
    produced the number. The count is the POOL's rather than the drift walk's
    on purpose: a document with damaged frontmatter declares no `id:`, so no
    descent reaches it, and a census counting only what the descent saw would
    quietly drop the document `unkeyed_documents` just reported by name.

    Nested: the drift walk's own counts, with `tree_walk`'s disclosures.
    """
    if model.is_pooled(cfg):
        return ', '.join(model.pool_census(cfg, kind, label) for kind, label in
                         (('milestone', 'milestone(s)'),
                          ('feature', 'feature(s)'),
                          ('story', 'story/ies'),
                          ('bug', 'bug(s)')))
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
