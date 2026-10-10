---
name: visual-layout
description: Use when you design, build or review how a page, slide or document looks (spacing, type, grouping, alignment, line length), before you write CSS or say a page "looks right", or when doc-sdlc needs the layout lens. CRAP and Gestalt rules checkable from screenshots.
---

# Visual layout: a reader sees groups before words

A reader scans a page for shape first. If the shape lies (things that belong together look apart, or everything shouts), the plain words do not save it. These rules make the shape tell the truth. Each has a failure look and a check you can run.

Tokens and themes (colors, font stacks, the actual scale values) belong to the artifact-design guidance for the repo. Use its tokens. This skill sets the rules for how you use them and does not copy them. If the repo has no tokens, make them first (rule 1 and 2), then build.

AI-writing tells in the copy are not this skill's job: use the optional `humanizer` skill.

## How to capture evidence

The main agent takes the screenshots (a reviewer agent has no browser) and passes them as files: a full-page screenshot at **375**, **1000** and **1440** px wide. If no screenshot files are given, mark every check that needs one **n/a** and say "no screenshots supplied"; do not guess from the markup alone. Read the page's CSS or markup for tokens. Keep the file names in your findings. A finding without a screenshot or a token name is not a finding.

## The rules

### 1. Type scale (Contrast)
Use one scale of 5-7 sizes from a fixed ratio (for example 1.25). Body text is one size. Headings step up the scale and are also heavier or a different weight.
- Fails when: two headings differ by 1-2 px, or sizes like 17px and 19px appear beside 18px.
- Check: list every distinct `font-size` value. Each must be a scale token. More than 7 distinct sizes fails.

### 2. Spacing scale (Proximity, Repetition)
Every margin, padding and gap comes from one scale (for example 4, 8, 16, 24, 32, 48, 64 px). No other values.
- Fails when: gaps of 13px or 22px appear, or the same pair of elements has different gaps on two pages.
- Check: list every distinct spacing value. Any value off the scale fails. Report the count of off-scale values.

### 3. Alignment: one grid (Alignment, Continuity)
Pick one grid and one text edge. Left-align running text. Every block snaps to a column edge. A thing placed off the grid needs a reason you can state.
- Fails when: a card is 6 px off its neighbour, or text is centered in one block and left-aligned in the next with no reason.
- Check: at each width, count the distinct left edges of text blocks. A single-column article should show 1-2. Report the count and the odd ones out. Centered body text over 3 lines fails.

### 4. Proximity: space says "these go together"
Space inside a group is smaller than space between groups. A heading sits closer to the text under it than to the text above it.
- Fails when: a heading floats evenly between two paragraphs, or a caption sits nearer the next image than its own.
- Check: measure the gap above and below each heading and caption. The gap to its own content must be smaller (a common test: at most half). Use spacing tokens, not guesses.

### 5. Common region: a box says "one thing"
A card, panel or background tint groups items by region. Use it for a real group, not for decoration. Do not nest more than 2 levels of boxes.
- Also: sections are told apart by space, a rule or a tint, with white space around boxes and headings ([COGA: page structure](https://www.w3.org/TR/coga-usable/#use-a-clear-and-understandable-page-structure-pattern), [COGA: white space](https://www.w3.org/TR/coga-usable/#use-white-spacing-pattern)).
- Fails when: unrelated items share a card, or related items are split across cards, or boxes sit inside boxes inside boxes.
- Check: for each box, name in one line what its contents share. If you cannot, it fails.

### 6. Similarity and Repetition: same job, same look
Items that do the same job look the same (all links, all buttons, all cards). Items that do different jobs look different. A repeated component keeps one structure, one padding, one radius, one type style.
- Fails when: two buttons for the same action differ, or a link looks like body text, or a plain label looks like a link.
- Check: group components by role. Compare their computed styles. Any difference inside a role fails. Any two roles with identical style fails.

### 7. Continuity and closure
The eye follows lines and edges. Keep rows and columns on a straight path (continuity). A reader fills small gaps, so you need no full border around every item (closure): space or a single rule is enough.
- Fails when: a row of cards has uneven top edges, or a list is boxed item by item so the page reads as a grid of cages.
- Check: at 1000 and 1440 px, compare top and left edges of repeated items; they must match. Count borders: if each item has its own full border and space would do, fail.

### 8. Figure-ground and contrast
The thing that matters must stand out from its background by size, weight, color or space. The contrast ratios (4.5:1 and 3:1) and the colour-alone rule belong to skill `accessible-content` (checks 3, 4 and 5). Score the ratios there, not here.
- Fails when: the key item blends into its surroundings, text sits on a busy image with no overlay, or light grey on white "looks clean".
- Check: in the screenshot, the key item is clearly the strongest by size, weight or space. Name the cue. For text over an image, confirm an overlay or plain panel exists (COGA: "Use solid backgrounds for blocks of text", [foreground not obscured](https://www.w3.org/TR/coga-usable/#ensure-foreground-content-is-not-obscured-by-background-pattern)).

### 9. One focal point per screen
At each of the three widths, one thing is the loudest: the main heading, the key claim or the one call to action. At most one primary button in view.
- Fails when: two or more elements fight for first look, or nothing leads and the page is a flat wash.
- Check: in each screenshot, squint (blur it) and name the first thing you see. It must be the intended one. Key actions and warnings are in view without scrolling ([COGA](https://www.w3.org/TR/coga-usable/#make-it-easy-to-find-the-most-important-actions-and-information-on-the-page-pattern)). Count primary-style buttons in the first screen: more than 1 fails.

### 10. Line length near 65 characters
Body lines run 45-75 characters, 65 as the target. WCAG 1.4.8 (AAA) caps lines at 80. Set a `max-width` in `ch` (about 65ch to 70ch) on text columns. Line height for body text is at least 1.5. Reflow and text spacing (WCAG 1.4.10, 1.4.12) are scored in `accessible-content` only.
- Fails when: text runs the full width of a 1440 px screen, or a mobile column breaks every 20 characters.
- Check: count characters in 3 long lines at 1000 and 1440 px (or read `max-width`). Mobile at 375 may be shorter, but at least 30.

## Scored checklist

Fill one line per item: **pass**, **fail** or **n/a**, then the evidence (screenshot name, token, count, measured value). n/a needs a reason.

- [ ] Evidence: screenshots at 375, 1000, 1440 px exist and are named (n/a when none were supplied).
- [ ] 1 Type scale: distinct font sizes counted (max 7, all tokens).
- [ ] 2 Spacing scale: off-scale values counted (0 allowed).
- [ ] 3 Alignment: distinct left edges counted per width; odd ones explained.
- [ ] 4 Proximity: every heading and caption closer to its own content.
- [ ] 5 Common region: each box has a one-line reason; nesting at most 2.
- [ ] 6 Similarity: same role, same style; different role, different style.
- [ ] 7 Continuity and closure: repeated items share edges; borders not overused.
- [ ] 8 Figure-ground: the key item stands out; ratios are scored in `accessible-content`.
- [ ] 9 Focal point: one at each width; at most 1 primary button per screen.
- [ ] 10 Line length: measured 45-75 characters (target 65).
- [ ] Tokens come from the repo's artifact-design guidance, not invented here.

Score line: `passed / (total minus n/a)`. Any fail goes back to the author with its evidence.

Ship rule (workflow `doc-sdlc` owns the mapping). **Blocks:** a fail on rule 8 (figure-ground) or rule 9 (focal point). Any other fail is should-fix. A fail on rule 5 or 7 that is only a taste call is a note.

## Sources

- Robin Williams, *The Non-Designer's Design Book* (CRAP: contrast, repetition, alignment, proximity).
- Wikipedia, "Principles of grouping" (proximity, similarity, continuity, closure, connectedness; Gestalt laws). Common region is Stephen Palmer's 1992 addition. Focal point (emphasis) is a general design principle, not a classic Gestalt law; it is listed here because it fixes where the eye lands.
- NN/g, "Proximity Principle in Visual Design" (nngroup.com/articles/gestalt-proximity/).
- W3C WCAG 2.2 Understanding: 1.4.8 Visual Presentation (80 characters). Contrast, reflow and text spacing: see `accessible-content`.
- W3C, *Making Content Usable for People with Cognitive and Learning Disabilities* (COGA, W3C Group Note): https://www.w3.org/TR/coga-usable/ . Document patterns only; each check links its pattern.
- Wikipedia, "Line length" (45-75 characters, 66 ideal, from print research).
