"""check pm — the active PM tree's statuses do not contradict each other.

Every rule asks a CATEGORY (`todo`/`in_progress`/`done`), never a word, off the same
predicates in `repo/pm/model` that `pm` writes with. Which rules run is `[pm] checks`
(default: D1-D6 + V1-V5; V6, D9/D10 and R5 are opt-in).

DRIFT (each FAILs, naming the path):
  D1  a `reviewed:` pointer naming a file that is not there
  D4  a status the project never declared, for any grain kind
  R5  the version file equals the CURRENT release in `order` ([pm] version_at)
  D9  an `in_progress` milestone declares a `branch:`
  D10 that branch is not the mainline (`[repo_hygiene] mainline`, `origin/`-stripped)
WARN (a line, never the exit code; both grains and both categories named):
  D2  a feature in `todo` while all its stories are `done`
  D3  a milestone in `done` with a feature that is not
  D5  a story out of `todo` under a feature still in it
  D6  a milestone in `todo` whose features are all `done`
  READY  a grain past `todo` with an empty scaffolded section, no stories, no `phase:` or no `branch:`

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
        # declared none is refused at the first category question.
        print(f'[check:pm] ERROR — {err}', file=sys.stderr)
        return 2


def _run() -> int:
    cfg = model.load()
    # Validated here, not in `model.load()`, so a stale rule id cannot take `pm status` down.
    stale = model.config_complaints(cfg)
    if stale:
        for msg in stale:
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

    mdirs = model.milestone_dirs(cfg)
    if not mdirs:
        print()
        print(f'[check:pm] FAIL — no milestones found under {cfg.roadmap_dir}/ '
              f'(wrong [pm] roadmap_dir, or an empty tree?)')
        return 1

    # Never gated by `checks`: this is the scan saying it could not see part of the tree.
    for path, why in model.orphan_dirs(cfg):
        report(f'{cfg.rel(path)}/ is a {why} — every grain under it was SKIPPED '
               f'by this scan')

    # Always walked for the census; reported only under D4.
    bug_findings, n_bugs = model.bug_status_findings(cfg)
    if 'D4' in enabled:
        for path, why in bug_findings:
            report(f'{cfg.rel(path)}: {why}')

    n_features, n_stories = _drift_walk(cfg, enabled, mdirs, report, warn)

    _flow_findings(cfg, enabled, report)
    _release_findings(cfg, enabled, report, warn)

    # --- V1-V6: structural + referential integrity ------------------------
    v_on = enabled & set(model.VALIDATE_CHECKS)
    v_census: dict = {}
    if v_on:
        from agentic_sdlc.repo.pm import validate as _validate
        v_findings, v_census = _validate.run(cfg, v_on)
        for msg in v_findings:
            report(msg)

    return _verdict(cfg, findings, warnings, len(mdirs), n_features,
                    n_stories, n_bugs, v_on, v_census)


# D2's and D6's shared tail; neither rule has an opinion about which state is next.
ADVANCE_IT = 'advance it (`done` is the LAST state, not the next one)'


def _cat(cfg: model.PmConfig, kind: str, status: str) -> str:
    """The category a WARN line prints beside a word, or 'undeclared'."""
    return model.category_of(cfg, kind, status) or 'undeclared'


def _drift_walk(cfg: model.PmConfig, enabled: set[str], mdirs,
                report, warn) -> tuple[int, int]:
    """D1-D6 over every grain plus the READY warnings; returns the (feature, story) census."""
    n_features = 0
    n_stories = 0

    for mdir in mdirs:
        mfile = mdir / model.MILESTONE_DOC
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

        views = [model.read_feature(cfg, ffile)
                 for ffile in model.feature_files(mdir)]
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


def _flow_findings(cfg: model.PmConfig, enabled: set[str], report) -> None:
    """D8/D9/D10 over every `in_progress` milestone; two in progress is two answers."""
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


def _release_findings(cfg: model.PmConfig, enabled: set[str], report, warn) -> None:
    """R5 — the version file equals the CURRENT release's version.

    Current is a POSITION in `order`, never a parse, so this rule fits both
    bump-at-start and bump-at-close ([pm] version_at) and has no opinion about
    what a version string looks like.
    """
    if 'R5' not in enabled:
        return
    order = model.declared_order(cfg)
    if not order:
        # A tree mid-adoption has no plan yet. Reddening it would be milestone
        # risk 1: a rule that fails every fresh consumer gets switched off.
        warn(f'R5 is enabled and {cfg.rel(model.releases_file(cfg))} declares '
             f'no `order` — nothing to grade {cfg.version_file} against; '
             f'`agentic-sdlc pm order --append <version>` writes the plan')
        return
    current = model.current_release(cfg)
    if current is None:
        at = cfg.version_at
        why = ('every entry in `order` has shipped'
               if at == model.VERSION_AT_START else 'no entry in `order` has shipped yet')
        warn(f'R5 has no current release: {why} under [pm] version_at = '
             f'{at!r} — nothing to grade {cfg.version_file} against')
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


def _verdict(cfg: model.PmConfig, findings: list[str], warnings: list[str],
             n_milestones: int, n_features: int, n_stories: int, n_bugs: int,
             v_on: set[str], v_census: dict) -> int:
    """The census + verdict; warnings are counted separately and never decide the code."""
    print()
    census = (f'{n_milestones} milestone(s), {n_features} feature(s), '
              f'{n_stories} story/ies')
    # `Walk` renders every narrowing itself, so a new filter discloses without an edit here.
    census += model.tree_walk(cfg).disclosures()
    census += f', {n_bugs} bug(s)'
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
