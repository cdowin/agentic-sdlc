A `ledger.jsonl` written under the OLD dispatch-row shape — the five frozen
snapshot keys (`milestones_building`, `features_building`, `features_review`,
`stories_wip`, `stories_review`) and none of the category keys 0.2.0 added
beside them (decision D7, "keep and extend"). Vendored per hard rule 8;
`tests/test_pm_ledger_report.py` reads it into a scratch tree.

What it holds, on purpose:

- row 2 names `0.1/alpha/s0` through `stories_wip` — an old row that IS
  readable, and is attributed exactly as it always was;
- rows 4 and 5 name nothing through the frozen keys — either a dispatch over
  an idle tree or a dispatch over a tree whose words that shape could not
  spell, and the rows cannot tell the two apart; the report discloses them
  rather than counting them as empty;
- row 3 moves the story to `review`, a word this package's seed does not
  declare — its stint lands in no category column and is disclosed under the
  table (`unplaced_s` in `--json`).
