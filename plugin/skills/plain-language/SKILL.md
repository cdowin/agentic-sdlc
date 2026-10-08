---
name: plain-language
description: Load this skill whenever you write, edit or review a document a person will read - a web page, blog post, README, guide, email, release note, store text, help text or book blurb. Use it before you hand over any first draft, and when asked to "make it clearer", "simplify", "plain English", "check readability" or "review the writing". It encodes ISO 24495-1 (relevant, findable, understandable, usable) with a scored checklist. Do not skip it because the draft "reads fine": the first draft almost never meets these checks.
---

# Plain language: the reader finds it, gets it, uses it

Public documents follow this skill.
It is the writing lens of the document SDLC: brief, base document, then lenses and reviewers.

## Why

A reader came to do something. A document is plain when its words, structure and design let
the reader find what they need, understand it and use it (PLAIN's public definition of the
standard). Plain is not dumb. Experts also read faster and make fewer errors in plain text.
People scan: Nielsen Norman Group found 79% of test users always scanned a new page and
16% read word by word. So the structure must work for a scanner.

## The four principles (ISO 24495-1:2023, our words)

1. **Relevant.** Give the reader what they need, and no more. Name the reader and their goal first.
2. **Findable.** The reader can locate it fast. Main point first. Headings match the reader's questions.
3. **Understandable.** The reader grasps it on the first read. Short sentences, common words, terms defined once.
4. **Usable.** The reader can act on it. Steps in order, examples, and a clear next action.

## How to apply

1. **Write the reader line first.** One line: who reads this, what they want, what they know.
   Put it in the brief or the review notes. Cut any section that serves no reader goal.
2. **Main point first (inverted pyramid).** The first paragraph says what this is, the answer, and what to do.
   Background goes after. Cut the warm-up ("In today's world...").
3. **Headings are the reader's questions.** "How do I install it?" beats "Installation overview".
   A scanner should get the whole story from the headings alone.
4. **Short sentences.** Mean about 15-20 words, none over 30-35 (PLAIN guidance). One idea each.
5. **Active voice.** Name who does what. Passive is fine when the doer is unknown or unimportant.
6. **Common words.** "Use", not "utilize". "Start", not "commence". Say numbers, not "many".
7. **One word per thing.** Pick "workflow" or "pipeline" and keep it. A new word reads as a new thing.
8. **Define a term once**, at first use, in plain words. Do not stack jargon. Expand each acronym once.
9. **Lists and tables where they help.** Steps are a numbered list. Options with traits are a table.
   Do not bullet a story that needs connected reasoning.
10. **Short paragraphs.** Three or four sentences. One topic each. Bold only what a scanner must catch.
11. **Test with the reader's task.** Give the doc to a fresh agent (or a person) with no context.
    Ask it to do the task the reader would do. Every stumble is a fix. Log what you tested.

## Reading level

Target about grade 8 for a broad audience (Nielsen Norman Group). Several grades below the audience's
schooling for a specialist one. A formula (Flesch-Kincaid) is a smoke alarm, not the goal:
a low score on a bad document is still a bad document.

## How it relates to other standards

- **`humanizer`** (optional skill, see the plugin README) removes AI-writing tells:
  stock phrases, rule-of-three, inflated praise. Plain language fixes the reader fit.
  Run plain-language for structure and clarity, then `humanizer` for voice. Use both on public text.
  This skill does not copy its list.
- **A house style** such as ASD-STE100 (20 words max, one fact per sentence) is stricter on sentence
  length and wins where a document sets it. Plain language governs everything else a person reads:
  sites, posts, READMEs, books, store text.
- **`accessible-content`, `visual-layout`, `multimedia-design`, `usability-review`** cover the
  other lenses. This one owns words and structure only.

## Checklist (score each: pass / fail / n/a, with evidence)

Reviewers fill every line. Evidence is a quote, a count or a location. "Looks fine" is not evidence.
Checks 1 and 2 follow PLAIN. The limits in checks 1 (22 words), 3 and 11 are house rules.

| # | Check | Pass when | How to measure |
|---|---|---|---|
| 1 | Mean sentence length | 15-20 words (up to 22 for a technical doc) | Words / sentences. Report the number. |
| 2 | Longest sentences | None over 35 words | List each sentence over 30 words. |
| 3 | Passive voice share | 10% of sentences or fewer; present tense, speaks to "you" ([COGA: simple tense and voice](https://www.w3.org/TR/coga-usable/#use-a-simple-tense-and-voice-pattern)) | Count passive sentences / total. Quote 3 worst. |
| 4 | Main point in first paragraph | What it is, the answer and the next step are all there. A long document opens with a short summary ([COGA](https://www.w3.org/TR/coga-usable/#provide-summary-of-long-documents-and-media-pattern)) | Quote the first paragraph. |
| 5 | Reader named | Reader line exists, and every section serves that goal | Quote the reader line. List any section that does not serve it. |
| 6 | Headings are questions or clear labels | A scan of headings alone tells the story, and the title says the purpose ([COGA](https://www.w3.org/TR/coga-usable/#make-the-purpose-of-your-page-clear-pattern)) | List the headings. |
| 7 | Terms defined once | Each jargon term and acronym is explained at first use | List terms with first-use location. |
| 8 | One word per thing | No synonym swaps for a key term | List key terms and count variants. |
| 9 | Common words, simple sentences | No stock jargon or long words where a short one fits; no double negative or clause inside a clause ([COGA: clear words](https://www.w3.org/TR/coga-usable/#use-clear-words-pattern), [COGA: nested clauses](https://www.w3.org/TR/coga-usable/#avoid-double-negatives-or-nested-clauses-pattern)) | Quote up to 5 swaps and any double negative. |
| 10 | Lists and tables fit | Steps are numbered and none is skipped as "obvious" ([COGA](https://www.w3.org/TR/coga-usable/#separate-each-instruction-pattern)), comparisons are tables, no bullet that hides logic | Cite each list or table. |
| 11 | Paragraph length | No paragraph over 5 sentences, one topic each, aim first ([COGA](https://www.w3.org/TR/coga-usable/#keep-text-succinct-pattern)) | List offenders. |
| 12 | Reading level | At or below the target grade for the audience | Report the score and tool. Smoke alarm only. |
| 13 | Task test | A fresh reader did the task without help | Give the task, the result and each stumble. |
| 14 | Style fit | This skill, or the house style the document names | Name which applies. |
| 15 | Literal language | No metaphor, simile, joke or sarcasm without a plain explanation beside it ([COGA: literal language](https://www.w3.org/TR/coga-usable/#use-literal-language-pattern), [COGA: implied content](https://www.w3.org/TR/coga-usable/#explain-implied-content-pattern)) | Quote each figure of speech and its gloss. |
| 16 | Numbers | Familiar units; one unit per quantity; a key number also has a plain-words gloss ("about half") ([COGA: numbers](https://www.w3.org/TR/coga-usable/#provide-alternatives-for-numerical-concepts-pattern), [COGA: units](https://www.w3.org/TR/coga-usable/#use-familiar-metrics-and-units-pattern)) | List each key number and its gloss. |
| 17 | Plain opening | The first sentence says what happened or what this is in plain words, matching the brief's `opening`; numbers and glosses come after. Fail: "Build time fell 38% (from 14 to 9 minutes, a 5-minute gain)." Fix: "The build got faster. It now takes 9 minutes, down from 14." | Quote the first sentence and the brief's `opening`. |
| 18 | Prose, not bullets in disguise | Sentences in a paragraph link to each other. Test: if every sentence could be a bullet and the order could change, it fails. A real list stays a list. Fail: "The tool is fast. It has three modes. It runs on Linux." Fix: "The tool is fast because it has three modes, and each runs on Linux." | Quote each paragraph that fails the shuffle test. |
| 19 | No leaps | Each conclusion comes after its evidence. Test: for each conclusion, quote the evidence before it; none found means it fails. Fail: "So the cache is the cause." with no measurement shown. Fix: add the timing first, then the conclusion. | List each conclusion with its quoted evidence. |

A document passes when no check fails. Ship rule (workflow `doc-sdlc` owns the mapping): a fail on check 1, 2, 3, 4, 13 or 19 **blocks**. For kind `post`, a fail on check 17 or 18 also blocks. Any other fail is should-fix. A fail on check 12 (reading level) or 14 is a note.

For AI-writing tells, run `humanizer` after this skill. Workflow `doc-sdlc` scores it with its own short list.

## Sources

- ISO 24495-1:2023, Plain language - Part 1: Governing principles and guidelines (iso.org/standard/78907.html). Paywalled. Cited, not copied.
- Plain Language Association International (PLAIN), "What is plain language?" https://plainlanguagenetwork.org/plain-language/what-is-plain-language/
- plainlanguage.gov, federal plain language guidelines: https://www.plainlanguage.gov/guidelines/
- W3C, *Making Content Usable for People with Cognitive and Learning Disabilities* (COGA, W3C Group Note): https://www.w3.org/TR/coga-usable/ . Document patterns only; each check links its pattern.
- Nielsen Norman Group: "How Users Read on the Web", "Inverted Pyramid: Writing for Comprehension", "Legibility, Readability, and Comprehension" (nngroup.com/articles/).
