---
name: accessible-content
description: Use whenever you write, edit, build or review anything a person will read or use on a screen - a web page, blog post, site template, HTML artifact, PDF, ebook, slide, email or form. Load it before you ship and when a doc-sdlc run needs the accessibility lens. Triggers - "accessible", "WCAG", "a11y", "contrast", "alt text", "heading order", "mobile reflow", "screen reader", "keyboard", "reduced motion". It encodes WCAG 2.2 Level A and AA in plain words, with a check an agent can run for each rule and a scored checklist. Load it even if the task does not say accessibility; a page that fails these rules fails real readers.
---

# Accessible content: WCAG 2.2 A and AA, in plain words

The target is WCAG 2.2 Level AA. Accessible content also reads better for everyone: on a phone, in sun glare, with one hand, with a screen reader.

Plain language for the reader is skill `plain-language`. Layout is `visual-layout`. For AI-writing tells use the optional `humanizer` skill; this skill does not copy it.

The rules below paraphrase W3C text. The SC number and level are in each line. Read the Understanding page for a rule you are unsure of: `https://www.w3.org/WAI/WCAG22/Understanding/<slug>.html`.

## Why rules, not taste

A rule is testable. "Looks readable" is not. Each rule has a check you can run, so a reviewer agent can score it with evidence.

## Perceivable: can the reader take it in?

- **Text alternatives (1.1.1, A).** Every meaningful image gets alt text that says what the image is for. A decorative image gets empty alt (`alt=""`). A chart gets its data in text nearby.
- **Structure (1.3.1, A).** Use real headings, lists, tables and labels, not bold text that only looks like them. One `h1`. Never skip a level (h2 then h4). Headings must say what the section holds (2.4.6, AA).
- **Sensory words (1.3.3, A).** Do not rely on shape, colour or place alone: not "click the green button on the right".
- **Orientation (1.3.4, AA).** Work in portrait and landscape.
- **Contrast (1.4.3, AA).** Body text needs 4.5:1 against its background. Large text (18 pt, or 14 pt bold) needs 3:1.
- **Non-text contrast (1.4.11, AA).** Input borders, icons that carry meaning, focus rings and chart marks need 3:1 against their neighbours.
- **Colour is not the only signal (1.4.1, A).** A link inside body text needs an underline or other cue besides colour. An error needs words or an icon, not just red.
- **Resize and reflow (1.4.4, 1.4.10, AA).** Text zooms to 200% without loss. At 320 CSS px wide (400% zoom on a 1280 px screen) the page scrolls down only, with no sideways scroll, except for data tables, maps and code.
- **Text spacing (1.4.12, AA).** If a user sets line height 1.5, paragraph gap 2x, letter gap 0.12 em and word gap 0.16 em, nothing clips or overlaps. Do not fix heights in px.
- **Hover and focus popups (1.4.13, AA).** A tooltip can be dismissed, hovered over, and stays until the user leaves it.
- **Media (1.2.2, A; 1.2.5, AA).** Recorded video has captions and audio description. See `multimedia-design`.
- **Images of text (1.4.5, AA).** Use real text, not a picture of text, except for logos.

## Operable: can the reader act on it?

- **Keyboard (2.1.1, A).** Everything works without a mouse. No trap (2.1.2, A).
- **Focus visible (2.4.7, AA).** The focused item shows a clear outline. Never `outline: none` without a replacement.
- **Focus not obscured (2.4.11, AA, new in 2.2).** A sticky header or cookie bar must not fully hide the focused item.
- **Target size (2.5.8, AA, new in 2.2).** Click and tap targets are at least 24 by 24 CSS px, or have enough clear space around them. Inline links in a sentence are exempt. Aim for 44 px on phones as best practice.
- **Dragging (2.5.7, AA, new in 2.2).** Anything done by dragging also works by click or tap (a button, a menu).
- **Link purpose (2.4.4, A).** Link text makes sense in its sentence. No "click here", no bare "read more".
- **Page title (2.4.2, A)** says what the page is. A skip link to main content helps (2.4.1, A).
- **Moving content (2.2.2, A).** Anything that moves, blinks or scrolls for over 5 seconds has a pause control. Nothing flashes more than 3 times a second (2.3.1, A).
- **Motion (2.3.3, AAA - best practice, not required for AA).** Respect the user's setting: wrap animation in `@media (prefers-reduced-motion: no-preference)` or switch it off under `reduce`. We do this anyway; vestibular disorders are common.

## Understandable: will it behave as expected?

- **Language (3.1.1, A; 3.1.2, AA).** Set `<html lang="en">`. Mark a passage in another language with `lang`.
- **Labels (3.3.2, A).** Every form field has a visible label, not just placeholder text. Autofill purpose is set on personal fields (1.3.5, AA).
- **Consistent help (3.2.6, A, new in 2.2).** If a page offers help (contact link, chat), it sits in the same place on every page.
- **Redundant entry (3.3.7, A, new in 2.2).** Do not make people retype what they already gave in the same process. Prefill it or offer to reuse it.
- **Accessible authentication (3.3.8, AA, new in 2.2).** A login must not need a memory, puzzle or transcription test unless there is another way: paste into password fields, allow a password manager, offer a link or passkey.

## Robust: will tools understand it?

- **Name, role, value (4.1.2, A).** Custom controls expose a name and role to assistive tech. Prefer native `button`, `a`, `input`.
- **Status messages (4.1.3, AA).** Updates that appear without a focus change ("3 results", "Saved") use `role="status"` or `aria-live`.
- **4.1.1 Parsing was removed in WCAG 2.2.** Do not score it or fail a page on it. Still write valid HTML: browsers have long handled the old errors, so the rule no longer helped.

## How to check, from an agent

1. **Contrast.** Compute the WCAG ratio: linearise each sRGB channel (`c/255`, then `((c+0.055)/1.055)^2.4`, or `c/12.92` if `c <= 0.03928`), `L = 0.2126R + 0.7152G + 0.0722B`, ratio `= (Llight+0.05)/(Ldark+0.05)`. Run it for every text and background pair, and for CSS variables in both themes.
2. **axe-core.** Where a browser exists: `npx @axe-core/cli <url-or-file-url> --tags wcag2a,wcag2aa,wcag21aa,wcag22aa`. Record the violation ids. axe cannot find every problem; it never replaces steps 3 to 6.
3. **Heading outline.** Dump `h1` to `h6` in order (`grep -o '<h[1-6][^>]*>.*' file.html`, or in the browser `[...document.querySelectorAll('h1,h2,h3,h4,h5,h6')]`). Check one h1, no skipped level, each heading informative.
4. **320 px screenshot.** Open the page in a 320 px wide viewport, take a full-page screenshot, and look for sideways scroll, clipped text and overlap. Repeat at 200% zoom.
5. **Keyboard pass.** Tab through the page. Each stop shows focus and none is hidden behind a sticky bar. Measure target boxes with `getBoundingClientRect()`.
6. **Source scan.** `grep` for `<img` without `alt`, `outline:\s*none`, `placeholder=` used as the only label, `click here`, a missing `lang`, and animation without `prefers-reduced-motion`.
7. **Documents (PDF, ebook).** Check tags, reading order, title, language and alt text. Where a tool is missing, mark the item n/a and say why.

## Scored checklist

Score each line pass, fail or n/a. Give evidence for every score: the selector, the value, the line, the screenshot path. A fail names the fix. n/a needs a reason (for example "no forms on page").

| # | Check | SC | Score | Evidence |
|---|---|---|---|---|
| 1 | Meaningful images have alt text; decorative have `alt=""` | 1.1.1 | | |
| 2 | One h1, no skipped levels, headings say what follows, real lists and tables | 1.3.1, 2.4.6 | | |
| 3 | No instruction depends on colour, shape or place alone | 1.3.3, 1.4.1 | | |
| 4 | Body text contrast at least 4.5:1, large text 3:1 (list worst pair) | 1.4.3 | | |
| 5 | UI parts and meaningful icons at least 3:1 | 1.4.11 | | |
| 6 | At 320 px: no sideways scroll, no clipped content | 1.4.10 | | |
| 7 | At 200% zoom and with text spacing raised: nothing lost | 1.4.4, 1.4.12 | | |
| 8 | Captions and audio description on recorded video | 1.2.2, 1.2.5 | | |
| 9 | Everything works by keyboard; no trap | 2.1.1, 2.1.2 | | |
| 10 | Focus is visible and not fully hidden by sticky parts | 2.4.7, 2.4.11 | | |
| 11 | Targets at least 24 by 24 px or spaced | 2.5.8 | | |
| 12 | Drag actions have a click alternative | 2.5.7 | | |
| 13 | Link text is meaningful; page has a title | 2.4.4, 2.4.2 | | |
| 14 | Moving content can pause; no flashing; reduced-motion honoured | 2.2.2, 2.3.1, 2.3.3 (best practice) | | |
| 15 | `lang` set on the page and on foreign passages | 3.1.1, 3.1.2 | | |
| 16 | Form fields have visible labels; help is in a consistent place | 3.3.2, 3.2.6 | | |
| 17 | No forced retyping; login has a non-memory path | 3.3.7, 3.3.8 | | |
| 18 | Custom controls have name and role; status messages announced | 4.1.2, 4.1.3 | | |
| 19 | Text reads right aloud and in any font: no Roman numerals or symbols as words, accents and marks kept ([COGA: unambiguous formatting](https://www.w3.org/TR/coga-usable/#use-clear-unambiguous-formatting-and-punctuation-pattern), [COGA: letters and marks](https://www.w3.org/TR/coga-usable/#include-symbols-and-letters-necessary-to-decipher-the-words-pattern)) | COGA (not WCAG) | | |
| 20 | axe-core run recorded with zero serious or critical violations (or n/a, no browser) | all | | |

Ship rule (workflow `doc-sdlc` owns the mapping). **Blocks:** a fail on any rule marked Level A above, and a fail on check 4 (contrast) or check 6 (reflow). Any other fail (the AA rules) is should-fix. A fail on a best-practice line (check 14, reduced motion) is a note.

## Sources

- WCAG 2.2, https://www.w3.org/TR/WCAG22/ (SC numbers, levels, thresholds; 4.1.1 removed).
- Understanding WCAG 2.2, https://www.w3.org/WAI/WCAG22/Understanding/
- What's new in WCAG 2.2, https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/
- W3C, *Making Content Usable for People with Cognitive and Learning Disabilities* (COGA, W3C Group Note): https://www.w3.org/TR/coga-usable/ . Document patterns only; each check links its pattern.
- axe-core rules, https://dequeuniversity.com/rules/axe/
