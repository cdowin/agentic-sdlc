Cold-start only. Everything derivable is a command — never restate `pm status`, `git log` or `pm ledger report`.

# {id} {name} — handoff

## 1. Where the work lives

| | |
|---|---|
| **Branch** | <!-- the integration branch; `milestone.md` `branch:` is the stamp --> |
| **Version** | <!-- what project version this milestone carries, and when it bumps --> |
| **Tree** | <!-- the ABSOLUTE path of the checkout. A branch name is not a location when
     worktrees are in play, and no command prints where you were supposed to be. Say
     here if anything is isolated, and who else is working nearby. --> |

## 2. Where to pick up

<!-- The next action, and what unblocks after it. Not a status dump: delete any line
     below that does not apply, and add none that a command already answers. -->

```bash
git log --oneline <base>..HEAD    # the commit messages carry the arguments
pm status <id>                    # every grain, its state, its story count
pm ledger report                  # spend per grain, and what the gates cost
pm validate                       # refs resolve; the tree is not contradicting itself
make help                         # the authoritative target list
verify --plan                     # the rungs, with the cost each last took
```

<!-- Then the reading order — decisions.md before any feature, so its rejected
     alternatives are not re-argued. -->

## 3. Traps this milestone has already sprung

<!-- Every one of these was paid for. Write it so the next session does not
     pay again: what looked true, what was actually true, how it surfaced.

     This section is the reason the file exists. Sections 1 and 2 point at
     things; this one is the only part no command can regenerate. -->
