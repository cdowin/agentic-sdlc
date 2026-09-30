Cold-start only. Everything derivable is a command — never restate `pm status`, `git log` or `pm ledger report`.

# Handoff — deterministic parallel development

Three disjoint lanes own blocked belts/dispatch, coordinated landing, and budget/cache context.
Primary owns integration, release review, the final gate, and immutable artifact publication.
Frozen source commits feed a dedicated release checkout; unrelated existing work stays in its original branch.
