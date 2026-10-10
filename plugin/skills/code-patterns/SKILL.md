---
name: code-patterns
description: Use when you plan, write or review code in any project - a game, a CLI, a site, a service. Load it before you plan a task, before you add a class or a file, and when a reviewer runs the pattern lens. Triggers - "pattern", "singleton", "manager", "registry", "inheritance", "magic number", "duplicate", "dead code", "god class". It lists the good code patterns, each with a meaning and a smell to grep for.
---

# Code patterns: the same good habits in every project

Good code patterns are good code patterns, whatever the product. Apply them in games, CLIs and sites.

## The patterns

Each row: the pattern, what it means, and a smell to grep for.

| Pattern | Meaning | Smell to grep |
|---|---|---|
| Composition over inheritance | A thing is what behaviours it holds, not what kind it is. | `extends` or `class X(Base)` chains 3 deep; a subclass per kind; `if kind ==`. |
| No world-state holder | No Manager, Registry or global singleton holds world state. State has one owner. | `Manager`, `Registry`, `Singleton`, `get_instance`, module-level mutable dicts. |
| Owner pushes | An actor does not query the world. The owner of the state tells the actor (Tell, Don't Ask). | An actor calls `get_world()`, `find_all` or `global.state` to decide. |
| Data over code | Config and data files carry values. No magic numbers or strings in logic. | Numeric literals in conditions other than 0, 1, -1 and 2 (look, do not report on sight: ask whether a name or a data file should hold it); the same string literal in 2 files. |
| Declarative tools | A tool reads what a file declares and infers nothing from names, paths or order. | Path-sniffing and "guess the type" branches. `endswith(` or `startswith(` only when the result picks behaviour (look, do not report on sight: parsing and display are fine). |
| Delete, do not keep | Remove old concepts and dead code. Git keeps history. | "used to be", "legacy", "deprecated", "TODO remove", commented-out code. |
| Single responsibility | One function or file does one job. Keep them small. | A file over about 300 lines; a function over about 40 lines; "and" in a name. |
| No duplicate code | One rule lives in one place. | Two blocks that differ by one name; copied helpers. |
| Same thing, same call | The same task uses the same call everywhere. No bespoke path. | A second way to load, save, spawn or log what the first way already does. |

## Sources

- Composition over inheritance: Gamma et al., *Design Patterns* (1994); Nystrom, *Game Programming Patterns*, Component.
- Tell, Don't Ask: Hunt and Thomas, *The Pragmatic Programmer*.
- Single responsibility: Martin, *Clean Code*.
- No duplicate code: DRY, Hunt and Thomas.
- Delete dead code: Fowler, *Refactoring*, "Remove Dead Code".

## In a plan

A plan names which known pattern each task uses. If no pattern serves, the plan says "New pattern: <name>. Why no known pattern serves: <reason>". A reviewer checks the names against the diff.

## In review

Grep for each smell in the diff. A smell is a finding only when the change adds it. Cite this skill by name.
