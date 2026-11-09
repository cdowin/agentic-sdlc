---
name: usability-review
description: Use when you review, audit or design a page, tool, form, menu or UI for ease of use: a heuristic evaluation, or "is this clear". Nielsen's 10 heuristics, severity scale 0-4 and ISO 9241-112 principles.
---

# Usability review: find what trips a person up

For a game, a project's own games accessibility baseline, when it names one, replaces this skill's WCAG scoring on gameplay screens, and a game's menus are judged by that baseline too.

A heuristic evaluation is an expert walk through a page or tool against named rules. It finds problems fast and cheap. It does not replace a test with real people. Say so in the report.

Why: a first draft looks fine to its author. The author knows what it means. The rules below make you read it as a stranger who is in a hurry.

Plain language governs public text. For AI-writing tells, use the optional `humanizer` skill. This skill copies neither.

## Lens

- Prefix: UX
- Owner: UX designer
- Trigger: a change to a task a person does on a page, tool, form or menu
- Packs: none

## How to run it

1. **Name the user and the task.** One line: who is this person, and what must they get done? Without it, you cannot rate anything.
2. **Walk the task start to finish** at least twice. Pass 1: do the task. Pass 2: check each heuristic below against each screen, section or step.
3. **Log each problem** with: where, which rule ID (`UX-5`), what a person would do wrong or feel, a severity, and a fix.
4. **Rate it** (below). Report the worst first.
5. **Do not repeat other lenses.** Where a problem is really about contrast, alt text or focus, log it once and point to the skill.

## Rules

UX-1 to UX-10 are Nielsen's 10 usability heuristics. Source: Jakob Nielsen, nngroup.com, "10 Usability Heuristics for User Interface Design". The names are his. The checks are ours.

UX-11 to UX-17 are the principles of ISO 9241-112:2017 for presenting information. Source: ISO 9241-112:2017, "Ergonomics of human-system interaction, Part 112: Principles for the presentation of information" (iso.org). The standard is paywalled. These are our own words and a paraphrase of its aims. Read the standard for exact wording.

Severity is the default. The Nielsen rating of each finding (below) sets its severity: 3 or 4 is critical, 2 is major, 0 or 1 is minor. The shape of a lens is in `LENSES.md`.

| ID | Rule | Severity | Check | Check an agent can run | Overlap |
|---|---|---|---|---|---|
| UX-1 | Visibility of system status | major | review | After any action, does the page say what happened? Are progress, current page and loading shown? In a multi-step guide: steps done, current, next ([COGA](https://www.w3.org/TR/coga-usable/#make-each-step-clear-pattern)). | WCAG 4.1.3 status messages |
| UX-2 | Match between the system and the real world | major | review | Are the words the reader's own? No internal jargon, codes or internal team names. Order follows how people think. | `plain-language` |
| UX-3 | User control and freedom | major | review | Can the person undo, go back, cancel or close? Is there a clear exit from every state? | WCAG 2.2.1, 2.1.2 |
| UX-4 | Consistency and standards | major | review | Same word, same look, same place for the same thing. Links look like links. Follow web conventions ([COGA: familiar design](https://www.w3.org/TR/coga-usable/#use-a-familiar-hierarchy-and-design-pattern), [COGA: consistent look](https://www.w3.org/TR/coga-usable/#use-a-consistent-visual-design-pattern)). | `visual-layout` |
| UX-5 | Error prevention | major | review | Does the design stop the slip before it happens? Confirm risky actions. Give defaults and limits. State the result and downside of each option ([COGA](https://www.w3.org/TR/coga-usable/#clearly-state-the-results-and-disadvantages-of-actions-options-and-selections-pattern)). | WCAG 3.3.4 |
| UX-6 | Recognition rather than recall | major | review | Is what the person needs in view, not in their memory? Labels, not codes. Context shown on each step. No sums or memory across steps ([COGA](https://www.w3.org/TR/coga-usable/#do-not-rely-on-users-calculations-or-memorizing-information-pattern)). | `visual-layout` |
| UX-7 | Flexibility and efficiency of use | major | review | Can an expert go faster (shortcuts, links, search) while a new person is still guided? Optional steps are marked apart from the required path ([COGA](https://www.w3.org/TR/coga-usable/#make-short-critical-paths-pattern)). | WCAG 2.1.1 |
| UX-8 | Aesthetic and minimalist design | major | review | Does every element earn its place? Extra items hide the important ones. About 5 main choices or fewer per screen ([COGA](https://www.w3.org/TR/coga-usable/#avoid-too-much-content-pattern)). | `visual-layout`, `multimedia-design` |
| UX-9 | Help users recognize, diagnose and recover from errors | major | review | Does the error say, in plain words, what went wrong and how to fix it? No bare codes. | WCAG 3.3.1, 3.3.3 |
| UX-10 | Help and documentation | major | review | If help is needed, is it easy to find, short, task-based and searchable? A task opens with time, needs and overview ([COGA: prepare](https://www.w3.org/TR/coga-usable/#provide-information-so-a-user-can-complete-and-prepare-for-a-task-pattern)). Help and contact are easy to find ([COGA: find help](https://www.w3.org/TR/coga-usable/#make-it-easy-to-find-help-and-give-feedback-pattern)). Best case: none needed. | `plain-language` |
| UX-11 | ISO detectability | major | review | Can the person notice that the information is there? Is the important item easy to spot? | `accessible-content`, `visual-layout` |
| UX-12 | ISO freedom from distraction | major | review | Does anything pull the eye from the task: motion, ads, pop-ups, noise, clutter ([COGA: limit interruptions](https://www.w3.org/TR/coga-usable/#limit-interruptions-pattern))? | `visual-layout` |
| UX-13 | ISO discriminability | major | review | Can the person tell items apart? Are two similar things clearly different, and small text legible? | `accessible-content`, `visual-layout` |
| UX-14 | ISO interpretability | major | review | Is the meaning clear without guessing? Is wording, symbol or colour understood by this user? | `plain-language` |
| UX-15 | ISO conciseness | major | review | Is only the needed information shown, and no more? | `plain-language` |
| UX-16 | ISO consistency (internal) | major | review | Is it the same everywhere in this product or document set? | UX-4 |
| UX-17 | ISO consistency (external) | major | review | Does it match what people know from other products and from convention? | UX-4 |
| UX-18 | User and task named | major | review | One line names who the person is and the task they must get done. | - |
| UX-19 | Every finding has a Nielsen rating and a fix | major | review | Each logged problem has a rating 0-4, one sentence why, and a fix. | - |
| UX-20 | The report says it is an expert review | minor | review | The report says it is a heuristic review, not a test with real people. | - |

Overlap: discriminability and detectability lean on contrast and spacing (`accessible-content`, `visual-layout`). Conciseness and interpretability lean on `plain-language`. Internal and external consistency are UX-4 again. Log it once, under the sharper rule.

## Severity scale (Nielsen, 0-4)

Source: nngroup.com, "Severity Ratings for Usability Problems" (Nielsen).

- **0** Not a usability problem.
- **1** Cosmetic. Fix only if time allows.
- **2** Minor. Low priority.
- **3** Major. High priority to fix.
- **4** Catastrophe. Fix before release.

To pick a number, weigh how often it happens, how hard it is to overcome, and whether it keeps bothering people. A rare cosmetic flaw is 1. A flaw that blocks the main task for everyone is 4. Ship rule: severity 3 or 4 **blocks**, severity 2 is should-fix, severity 0 or 1 is a note. Explain each rating in one sentence.

## Limits

- One evaluator misses many problems. When it matters, run two passes with different user personas.
- Do not invent a user. If the audience is unknown, say so and ask.
- Checks on motion, sound and captions belong to `multimedia-design` and `accessible-content`.

## Checklist

Score each line pass, fail or n/a, with evidence. Evidence is a quote, a location or a screenshot note. A fail needs a rating 1-4.

- [ ] UX-18 User and task named in one line
- [ ] UX-1 Status: actions and state are shown
- [ ] UX-2 Real-world match: the reader's words, no insider jargon
- [ ] UX-3 Control: undo, back, cancel, exit exist
- [ ] UX-4 Consistency: same thing looks and reads the same
- [ ] UX-5 Error prevention: risky steps guarded
- [ ] UX-6 Recognition: needed info in view, not recalled
- [ ] UX-7 Flexibility: fast path for experts, guide for new users
- [ ] UX-8 Minimalism: nothing extra competes with the key item
- [ ] UX-9 Errors: plain message, cause, fix
- [ ] UX-10 Help: easy to find, short, task-based (or not needed)
- [ ] UX-11 ISO detectability: key items are noticed
- [ ] UX-12 ISO freedom from distraction: nothing pulls attention away
- [ ] UX-13 ISO discriminability: similar items are told apart
- [ ] UX-14 ISO interpretability: meaning is clear without guessing
- [ ] UX-15 ISO conciseness: only needed information
- [ ] UX-16 ISO internal consistency
- [ ] UX-17 ISO external consistency
- [ ] UX-19 Every finding has a rating 0-4 and a fix
- [ ] UX-20 Report says this is an expert review, not a user test

## Sources

- nngroup.com/articles/ten-usability-heuristics/
- nngroup.com/articles/how-to-rate-the-severity-of-usability-problems/
- W3C, *Making Content Usable for People with Cognitive and Learning Disabilities* (COGA, W3C Group Note): https://www.w3.org/TR/coga-usable/ . Document patterns only; each check links its pattern.
- iso.org/standard/64840.html (ISO 9241-112:2017, abstract only)
