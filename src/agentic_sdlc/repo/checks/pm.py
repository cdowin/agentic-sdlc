"""check pm — tier-1 guard against PM-tree status DRIFT.

The status CLI (`agentic-sdlc pm ...`) moves a `status:` through code; this
makes an INCONSISTENT tree loud. Nothing checks an EDGE — a status move is a
write, and what these rules read is the END STATE it left behind. It imports
the review-record definition and the feature-grain drift predicates from
`agentic_sdlc.repo.pm.model`, so the gate and the tool can never describe
"reviewed" or "drift" differently — one definition, two readers.

EVERY RULE ASKS A CATEGORY, NEVER A WORD. `todo` / `in_progress` / `done` are
the engine's three opinions; which words a project puts in each is
`[pm.states.<kind>]` in its devkit.toml, and a project that renames every word
gets this gate's answers unchanged (`tests/test_pm_gate.py` proves it on a
vendored tree). `model.holds` is the one predicate; `model.category_of` the
one lookup. The words below are the SEED's, for reading, and the gate never
compares against them.

DRIFT RULES (each FAILs, naming the offending path) are facts about the INPUT
— a dangling record, a word outside the declaration, the branch flow:
  D1  a `reviewed:` pointer naming a file that is not there. The
      dangling-POINTER half only — the same shape V4 checks for `depends_on`.
      "This feature carries no `reviewed:` at all" is not drift; it is the
      absence of a document, which is a fact about a team rather than a tree.
  D4  a status the project never declared — in no category — for milestone,
      feature, story AND bug. It matters most for a bug: every reader that
      asks "is this one still open" tests for a NAME, so a typo reads as
      closed and passes in silence.

CROSS-LEVEL DISAGREEMENTS are `  WARN  ` lines — story 03 of
the-code-knows-entry-and-exit; Chris, 2026-09-05: *"If I do a check on a
feature and it shows to-do and a story in progress, that's a warn. Not a fail,
no action, just messaging."* Each names BOTH grains and BOTH categories, is
counted separately on the verdict line, and never moves the exit code. Nothing
moves a parent on a child's account: the caller reads the line and decides.
  D2  a feature still in `todo` while ALL its stories are in `done` (a
      forgotten advance). In `in_progress` it has advanced, whatever the word.
  D3  a milestone in `done` with a feature child that is not. `done` means
      every thing inside this tree's authority is finished, so it cannot be
      true of a milestone while one of its features says otherwise.
  D5  a story that has LEFT `todo` under a feature still IN it. Not "a done
      story under a non-done feature": a story reaches `done` while its
      feature is still in `in_progress`, and that is the normal path — the
      feature's remaining work is not story work. The disagreement is that
      the work has started in one place and not the other.
  D6  a milestone in `todo` whose features are ALL in `done` (the milestone
      analogue of D2). A milestone in `in_progress` over finished features is
      the shape of a milestone being reviewed, accepted and packaged, and the
      release gate RUNS over it — which is the whole point: the gate that
      informs the ship decision has to run while that decision is still open.
  The four still answer to `[pm] checks` — a project that does not want the
  line names the id off — but an id that is on prints a warning, not a
  finding.
  D8  the shipped version equals an `in_progress` milestone's id
      (bump-at-START: the version names what is being built, so every crash
      report, save file and dev build carries that fact for free). EXACT
      string equality — the milestone id IS the version — or a hotfix of a
      RELEASED milestone: a `done` id in the tree plus one positive integer
      (0.90.3 -> 0.90.3.1). Asked of EVERY in-progress milestone (decision
      D5): two in progress is two answers, never the engine picking one.
  D9  an `in_progress` milestone declares the `branch:` its work lives on. A
      fresh checkout of the trunk sees the PM records but not the code;
      without the stamp the only recourse is guessing at `git branch -a`.
  D10 an `in_progress` milestone's `branch:` is empty, or equals the
      configured mainline (`[repo_hygiene] mainline`, `origin/`-stripped —
      stock `origin/main` reads as `main`). D9 only requires SOME stamp; D10
      also refuses the trunk itself, so a repo may run D9 alone (branch
      declared, wherever it points) or add D10 for the stricter guarantee. A
      repo may also rely on D9 without D10.
  D8/D9/D10 encode the branch-per-milestone / bump-at-start flow and are OFF
  by default; a project shipping from the trunk and bumping at close is
  running a different valid flow, not drifting. Opt in via `[pm] checks`.

Which rules run is `[pm] checks` in devkit.toml (default: D1-D6 + V1-V5).
V6 is known but OPT-IN, as are the three flow rules named just above.

OTHER WARNINGS (same line shape, same counting, same exit code):
  READY  `pm <kind> ready <id>` is the only stamp, and what it MEANS is asked
      here: a grain past its kind's first `todo` state whose scaffolded
      section is empty — a story's `## Acceptance criteria`, a feature's or a
      milestone's `## Ship criterion` — a feature with no stories, a milestone
      with a feature carrying no `phase:` or with no `branch:`. Nothing new is
      parsed: the three headings are the ones `pm new` writes.

Scope: the ACTIVE tree only — archived milestones predate the convention. This
MUST pass on the legitimate mid-build state: an in-progress milestone with
mixed children, a feature under review with its stories still in progress
(nothing moves a story until a close does, and the story cascade is opt-in,
so a closed feature over unfinished stories is a state a team chooses), and a
milestone walking through its `in_progress` states with every feature already
finished.
"""
from __future__ import annotations

import re

import sys

from agentic_sdlc.repo.pm import model


def run() -> int:
    try:
        return _run()
    except model.ConfigError as err:
        # Exit 2, never 1: a config typo is not a finding, and CI must not read
        # it as "drift found" (the contract project.py states). The whole walk
        # is inside this, not just `load()`: the flow is read lazily, so a tree
        # that declared none is refused by `flow_of` at the first question
        # asked of a category, and that refusal is a fact about the INPUT.
        print(f'[check:pm] ERROR — {err}', file=sys.stderr)
        return 2


def _run() -> int:
    cfg = model.load()
    # The roster is validated HERE rather than in `model.load()`: a stale rule
    # id must not take `pm status` down with the gate. This is the reader a
    # narrowed roster would lie to, so this is where it has to be loud.
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

    # A WARN is a fact worth a line and not an exit code (rule 9): it names
    # what it saw and what the reader might do, and the caller decides.
    def warn(msg: str) -> None:
        warnings.append(msg)
        print(f'  WARN  {msg}')

    enabled = set(cfg.checks)
    print(f'[check:pm] scanning active PM tree ({cfg.roadmap_dir}/, '
          f'excluding {model.ARCHIVE_DIR_NAME}/)')

    mdirs = model.milestone_dirs(cfg)
    # Rule 4 — a gate that scans nothing must say so. A misconfigured
    # roadmap_dir would otherwise print a serene PASS over zero files.
    if not mdirs:
        print()
        print(f'[check:pm] FAIL — no milestones found under {cfg.roadmap_dir}/ '
              f'(wrong [pm] roadmap_dir, or an empty tree?)')
        return 1

    # Always on, never gated by `checks`: these are not a drift RULE, they are
    # the scan telling you it could not see part of the tree.
    for path, why in model.orphan_dirs(cfg):
        report(f'{cfg.rel(path)}/ is a {why} — every grain under it was SKIPPED '
               f'by this scan')

    # Always walked, so the census can state how many bug files this scan
    # opened whatever the roster says; only REPORTED under D4, which owns
    # "a status outside the vocabulary" for every grain.
    bug_findings, n_bugs = model.bug_status_findings(cfg)
    if 'D4' in enabled:
        for path, why in bug_findings:
            report(f'{cfg.rel(path)}: {why}')

    n_features, n_stories = _drift_walk(cfg, enabled, mdirs, report, warn)

    _flow_findings(cfg, enabled, report)

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


# D2's and D6's shared tail. Both used to name `done` as the state to move to —
# D2 said "should be review/done", D6 "should be done" — and D6's version was
# the deadlock this vocabulary exists to break: it demanded the close BEFORE
# the gate that informs the close could run. `done` is the LAST state now, not
# the next one, and neither rule has an opinion about which state is. It is a
# suggestion on a WARN line, and the caller may have a reason not to take it.
ADVANCE_IT = 'advance it (`done` is the LAST state, not the next one)'


def _cat(cfg: model.PmConfig, kind: str, status: str) -> str:
    """The category a WARN line prints beside a word — or that it has none."""
    return model.category_of(cfg, kind, status) or 'undeclared'


def _drift_walk(cfg: model.PmConfig, enabled: set[str], mdirs,
                report, warn) -> tuple[int, int]:
    """D1-D6 over every grain, and the READY warnings beside them.

    Returns the (feature, story) census.
    """
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
        # ONE question of the feature set, asked once: the census D6 needs
        # (all finished, of how many) and the per-feature answer D3 prints
        # both come from the same `holds`, so the two rules cannot disagree
        # about which features are finished.
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


_HOTFIX_N = re.compile(r'[1-9][0-9]*')


def _is_hotfix_of_released(cfg: model.PmConfig, version: str) -> bool:
    """`<id>.N` for a DONE milestone in the tree — a hotfix cut from the mainline.

    A hotfix (0.90.3 -> 0.90.3.1) is the RELEASED milestone plus one positive
    integer, on a release branch off main, while the next milestone keeps
    building under its own id; retire's lag-by-one keeps that released
    milestone in the tree. Only `done` qualifies: a `.N` on a planning or
    building id is not a hotfix of anything, and D8's equality would refuse the
    release branch's version for no reason it can act on.
    """
    for mdir, mid in model.known_milestones(cfg):
        if not mid or not version.startswith(mid + '.'):
            continue
        status = model.field_of(mdir / model.MILESTONE_DOC, 'status')
        if model.category_of(cfg, 'milestone', status) != model.DONE_CATEGORY:
            continue
        if _HOTFIX_N.fullmatch(version[len(mid) + 1:]):
            return True
    return False


def _flow_findings(cfg: model.PmConfig, enabled: set[str], report) -> None:
    """D8/D9/D10 — the branch-per-milestone / bump-at-start flow, opt-in.

    Over EVERY milestone in `in_progress` (decision D5). A tree with two gets
    two answers to each rule, which is a true statement about that tree; the
    engine never picks one, and a project that wants exactly one narrows its
    own declaration.
    """
    live = (model.in_progress_milestones(cfg)
            if enabled & set(model.FLOW_CHECKS) else [])

    if 'D8' in enabled and live:
        version = model.shipped_version(cfg)
        ids = [mid for mid, _, _ in live]
        if version is None:
            report(f'no version found in {cfg.version_file} — D8 cannot verify '
                   f'the in-progress milestone(s) {", ".join(ids)}')
        else:
            # "The version names what is being built" is asked of each one.
            # Two in progress therefore yields at least one finding, which is
            # what a milestone left in progress when the next one started IS.
            for mid in ids:
                if version != mid and not _is_hotfix_of_released(cfg, version):
                    report(f'{cfg.version_file} version {version!r} does not '
                           f'match the in-progress milestone {mid!r} — bump at '
                           f'milestone START, and the id IS the version; a '
                           f'hotfix is a done milestone id in this tree plus '
                           f'one positive integer (D8)')

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


def _verdict(cfg: model.PmConfig, findings: list[str], warnings: list[str],
             n_milestones: int, n_features: int, n_stories: int, n_bugs: int,
             v_on: set[str], v_census: dict) -> int:
    """Render the census + verdict from what the phases reported.

    Warnings are COUNTED SEPARATELY and never decide the code: the line reads
    `… N warning(s)` only when there are any, so a clean tree's verdict line
    is byte-identical to what it was (rule 6).
    """
    print()
    census = (f'{n_milestones} milestone(s), {n_features} feature(s), '
              f'{n_stories} story/ies')
    # A census must never assert the opposite of the filesystem. The grain walk
    # narrows `stories/` and `bugs/` to documents that OPEN frontmatter — a
    # README parked beside a bug is a note, not a bug — and a scan that narrows
    # has to say by how much, or "0 bug(s)" reads as a fact about the directory
    # when it is a fact about the filter.
    #
    # This line is no longer a list of remembered disclosures. `Walk` records
    # every narrowing under a closed-enum reason and renders them all, in enum
    # order, printing nothing for a walk that skipped nothing — so a filter
    # added to `model.slot_walk` next year discloses itself here without
    # anybody editing this file. That is the whole difference between fixing
    # the instance and fixing the shape.
    census += model.tree_walk(cfg).disclosures()
    census += f', {n_bugs} bug(s)'
    if v_census:
        census += f', {v_census["refs"]} ref(s)'
        if v_census['unverifiable']:
            # Named, never hidden: a ref into a pruned milestone is not a pass.
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
