---
name: multimedia-design
description: Use when you write, draft, edit or review any document that mixes words with diagrams, screenshots, charts, photos, icons, slides, video or narration - blog posts, web pages, READMEs, wiki pages, guides, books, decks. Load it before you add, place, caption or cut an image, and whenever a reviewer must judge whether pictures help the reader. Triggers - "add a diagram", "does this image help", "caption", "figure", "illustration", "screenshot", "explainer video", "multimedia", "Mayer", "cognitive load", "doc-sdlc". Encodes Mayer's principles of multimedia learning as rules and a scored checklist. Pairs with plain-language, accessible-content and visual-layout.
---

# Multimedia design: every picture earns its place

This is one lens of the document standards. Word choice is `plain-language`. Alt text, contrast and captions for access are `accessible-content`. Spacing, grouping and alignment are `visual-layout`. This skill covers one question: do the words and the pictures work together? For AI-writing tells in captions and text, use the optional `humanizer` skill.

## Why

People learn through two channels: one for pictures, one for words. Each channel holds little at once. Extra material, or material in the wrong place, uses up that space and the reader learns less. Richard Mayer built the cognitive theory of multimedia learning on this (Mayer 2001, 2009, 2021). He grouped his design principles by the load they manage:

- **Cut waste** (extraneous load): material that does not help the goal.
- **Manage the core** (essential load): the unavoidable difficulty of the idea itself.
- **Help the reader make sense** (generative load): the effort of building understanding.

## Which principles are the core 12 and which are later

The 2nd edition of *Multimedia Learning* (Mayer 2009) lists **12 principles**. Mayer's 2024 review says the 3rd edition (2021) lists **15**. The first edition (2001) had fewer. Use the 12 as the base. Treat the extra three as newer and less settled.

| Group | Core 12 (Mayer 2009) |
|---|---|
| Cut waste | coherence, signalling, redundancy, spatial contiguity, temporal contiguity |
| Manage the core | segmenting, pre-training, modality |
| Help sense-making | multimedia, personalisation, voice, image |

Later additions (3rd edition, 2021): embodiment, immersion and generative activity. Check the exact names against Table 6 of Mayer (2024) before you cite them in public. Do not score a document against them. Mayer also reports that boundary conditions matter: a principle can weaken for expert readers or easy material.

## The rules, in plain words

Each rule names where it applies. **Page** means static pages (web, print, PDF, slides read alone). **Media** means video, animation or narration.

### Cut waste

1. **Coherence (page, media).** Remove what does not serve the point: decorative images, stock photos, background music, side stories. A picture must teach, show or prove something. Test: delete it. If the reader loses nothing, it stays out. An icon keeps one meaning and sits beside its text ([COGA: icons](https://www.w3.org/TR/coga-usable/#use-icons-that-help-the-user-pattern)).
2. **Signalling (page, media).** Show the structure. Use clear headings, a short opening that names the steps, bold on the one key term, arrows and numbers in diagrams, colour that marks the same thing the same way each time.
3. **Redundancy (media mainly; page in part).** Do not show the same words twice. In video, do not narrate and also print the same sentences on screen. On a page, a caption must not repeat the paragraph above it. A short on-screen label that adds to narration is fine. Alt text is a separate duty (`accessible-content`) and is not a breach.
4. **Spatial contiguity (page, media).** Put a label inside or touching the part it names. Put the caption directly under the figure. Put the figure next to the sentence that needs it. Do not send the reader to a legend or "see Figure 4" two pages away.
5. **Temporal contiguity (media only).** Say it and show it at the same moment. Narration for a step plays while that step is on screen. On a page this becomes rule 4.

### Manage the core

6. **Segmenting (page, media).** Break a long process into steps the reader controls: numbered steps, one idea per figure, short video chapters the reader can pause between, each labelled and reachable ([COGA: chunks](https://www.w3.org/TR/coga-usable/#break-media-into-chunks-pattern)).
7. **Pre-training (page, media).** Name the parts before the process. Define the terms, or show a labelled parts diagram, before the diagram that shows how they interact. Go from coarse to fine: an overview diagram first, then one detail diagram per part.
8. **Modality (media only).** With a moving picture or a busy diagram, use spoken narration, not a block of on-screen text. A still page has only text, so the rule does not bite there.

### Help the reader make sense

9. **Multimedia (page, media).** Words plus a well-made picture beat words alone. Add a diagram wherever you explain a mechanism, a flow, a structure or a comparison that takes a paragraph to describe. Text and picture must say complementary things: the picture shows the shape, the words say what it means. Complex content also gets a table, chart or summary alongside ([COGA: alternatives](https://www.w3.org/TR/coga-usable/#provide-alternative-content-for-complex-information-and-tasks-pattern)).
10. **Personalisation (media).** This skill owns the rule for media. In narration, video and tutorials, speak to "you" in a conversational voice. Mayer's research is on spoken and animated lessons. A still page is n/a here.
11. **Voice (media only).** Use a warm human voice for narration, not a flat machine voice. If you must use synthetic voice, note it in the review.
12. **Image (media only).** A talking head on screen does not by itself help learning. Show it only when it builds trust or the reader needs the face. Do not add it as decoration.

## House rules

- A mechanism gets a diagram. A list of facts does not.
- One figure carries one idea. Split a crowded figure.
- Every figure has: a number or title, a caption that tells the point, labels on the parts, and alt text (`accessible-content`).
- Order the document overview first, detail second.
- Prefer a simple drawn diagram to a screenshot full of noise. Crop screenshots to the part that matters.
- Cut an image you added "to break up the text". Use whitespace or a heading (`visual-layout`).

## How to review a document

1. List every image, diagram, chart and media item. Number them.
2. For each, write what the reader learns from it in one sentence. No sentence means fail on coherence.
3. Read the nearby text. Check the picture and the text do not say the same thing in the same way.
4. Score the checklist. Cite the figure number or line as evidence.

## Sources

- Mayer, R. E. (2001, 2009, 2021). *Multimedia Learning*. Cambridge University Press (1st, 2nd, 3rd editions).
- Mayer, R. E. (2024). The past, present, and future of the cognitive theory of multimedia learning. *Educational Psychology Review*. https://link.springer.com/article/10.1007/s10648-023-09842-1 (the three groups of principles; the 15 in the 3rd edition).
- Mayer, R. E., ed. *The Cambridge Handbook of Multimedia Learning* (2005, 2014, 2022).
- W3C, *Making Content Usable for People with Cognitive and Learning Disabilities* (COGA, W3C Group Note): https://www.w3.org/TR/coga-usable/ . Document patterns only; each check links its pattern.
- Public summaries to cross-check the core 12: Wikipedia, "E-learning (theory)"; university teaching-centre pages on Mayer's principles.

## Checklist (score each: pass / fail / n/a, with evidence)

Score `n/a` for media-only rules when the document is a still page. Say why.

| # | Check | Score | Evidence |
|---|---|---|---|
| 1 | Coherence: every image teaches, shows or proves something; none is decoration | | |
| 2 | Signalling: headings, numbers, arrows or bold mark the structure | | |
| 3 | Redundancy: no caption or on-screen text repeats nearby text or narration | | |
| 4 | Spatial contiguity: labels touch their parts; captions sit by their figures | | |
| 5 | Temporal contiguity: narration and picture match in time (media only) | | |
| 6 | Segmenting: long processes split into steps or chunks | | |
| 7 | Pre-training: terms or parts named before the process; overview before detail | | |
| 8 | Modality: narration, not heavy on-screen text, with moving pictures (media only) | | |
| 9 | Multimedia: each mechanism has a diagram; text and picture complement each other | | |
| 10 | Personalisation: conversational "you" voice (media only) | | |
| 11 | Voice: human narration (media only) | | |
| 12 | Image: no talking head without a reason (media only) | | |
| 13 | Every figure has a title or number, a point-making caption and labels | | |

Ship rule (workflow `doc-sdlc` owns the mapping). **Blocks:** a fail on check 1, 4, 9 or 13. Any other fail is should-fix. List every fail as a finding with a fix.
