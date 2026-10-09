---
name: ui-patterns
description: Use when you build, design or review a user interface - web app, front end, menu, HUD, toolbar, form, login, editor screen, settings or game UI (web or Godot) - or run a usability review. Gives the named patterns (ISO 9241, Nielsen heuristics, W3C COGA, WCAG 2.2, Game Accessibility Guidelines) as one shared vocabulary.
---

# UI patterns

Names and 1-line meanings with links. Cite the name in a brief, a commit or a review finding
("fails Nielsen 3, WCAG 2.5.8"). The linked source holds the full text; open it when a name
is not enough. This skill copies no standard text.

## ISO 9241-110:2020 interaction principles (7)
Source: [ISO 9241-110:2020, Interaction principles](https://www.iso.org/standard/75258.html); names checked on [a public summary](https://en.wikipedia.org/wiki/ISO_9241).

- Suitability for the user's tasks: the UI supports the task the user came to do.
- Self-descriptiveness: the user sees what the UI is and what to do next.
- Conformity with user expectations: it behaves as users know similar systems behave.
- Learnability: a new user learns it fast and a returning user remembers it.
- Controllability: the user sets the pace, order and direction, and can interrupt.
- Use error robustness: the UI prevents mistakes and makes recovery cheap.
- User engagement: the UI motivates and holds the user's interest in a useful way.

## ISO 9241-112:2017 presentation principles
Source: [ISO 9241-112:2017](https://www.iso.org/standard/64840.html).
- Detectability: the user notices the information is there.
- Freedom from distraction: nothing pulls attention from the needed item.
- Discriminability: the user tells similar items apart.
- Interpretability: the meaning is clear without guessing.
- Conciseness: only the needed information is shown.
- Consistency, internal and external: the same within the product, and as users know from elsewhere.

## Nielsen's 10 usability heuristics
Source: https://www.nngroup.com/articles/ten-usability-heuristics/ (one article, numbered 1-10).

1. Visibility of system status: show what is happening, now.
2. Match between the system and the real world: use the user's words and order.
3. User control and freedom: give a clear exit, undo and redo.
4. Consistency and standards: same word, same action; follow platform conventions.
5. Error prevention: remove the error-prone step or confirm it.
6. Recognition rather than recall: show options; do not make the user remember.
7. Flexibility and efficiency of use: shortcuts for experts, a plain path for novices.
8. Aesthetic and minimalist design: no information that does not serve the task.
9. Help users recognize, diagnose and recover from errors: plain words, name the fix.
10. Help and documentation: short, searchable, task-based, and rarely needed.

## W3C COGA interface patterns
Source: Making Content Usable for People with Cognitive and Learning Disabilities (https://www.w3.org/TR/coga-usable/). Each link is a design pattern.
**Forms**
- [Design forms to prevent mistakes](https://www.w3.org/TR/coga-usable/#design-forms-to-prevent-mistakes-pattern): validate early, constrain input.
- [Use clear visible labels](https://www.w3.org/TR/coga-usable/#use-clear-visible-labels-pattern): a label per field, always on screen.
- [Clearly identify controls and their use](https://www.w3.org/TR/coga-usable/#clearly-identify-controls-and-their-use-pattern): a control looks like what it does.
**Login and authentication**
- [Provide a login that does not rely on memory or other cognitive skills](https://www.w3.org/TR/coga-usable/#provide-a-login-that-does-not-rely-on-memory-or-other-cognitive-skills-pattern): paste, password manager, passkey.
- [Allow the user a simple single-step login](https://www.w3.org/TR/coga-usable/#allow-the-user-a-simple-single-step-login-pattern): one step where you can.
**Timeouts, interruptions and motion**
- [Avoid data loss and timeouts](https://www.w3.org/TR/coga-usable/#avoid-data-loss-and-timeouts-pattern): warn, extend, save the draft.
- [Limit interruptions](https://www.w3.org/TR/coga-usable/#limit-interruptions-pattern): no pop-up that is not needed.
- [Let users control when the content moves or changes](https://www.w3.org/TR/coga-usable/#let-users-control-when-the-content-moves-or-changes-pattern): pause, stop, no auto-advance.
**Menus, navigation and search**
- [Make the site hierarchy easy to understand and navigate](https://www.w3.org/TR/coga-usable/#make-the-site-hierarchy-easy-to-understand-and-navigate-pattern): shallow, labelled, same place.
- [Make short critical paths](https://www.w3.org/TR/coga-usable/#make-short-critical-paths-pattern): fewest steps to the main goal.
- [Provide search](https://www.w3.org/TR/coga-usable/#provide-search-pattern): a search box that tolerates typos and shows what it searched.
**Help**
- [Make it easy to find help and give feedback](https://www.w3.org/TR/coga-usable/#make-it-easy-to-find-help-and-give-feedback-pattern): help in the same place on every screen.
**Errors, feedback and undo**
- [Provide feedback](https://www.w3.org/TR/coga-usable/#provide-feedback-pattern): confirm each action, name the result.
- [Clearly state the results and disadvantages of actions, options and selections](https://www.w3.org/TR/coga-usable/#clearly-state-the-results-and-disadvantages-of-actions-options-and-selections-pattern): say what a choice costs before it happens.
- [Make it easy to undo form errors](https://www.w3.org/TR/coga-usable/#make-it-easy-to-undo-form-errors-pattern): edit one field; keep the rest.
- [Let users go back](https://www.w3.org/TR/coga-usable/#let-users-go-back-pattern): a back path that keeps the data.

## WCAG 2.2 criteria for interactive screens
Source: https://www.w3.org/TR/WCAG22/ (number, name, link). Level A and AA unless noted.

- [1.4.3 Contrast (Minimum)](https://www.w3.org/TR/WCAG22/#contrast-minimum): text 4.5:1.
- [2.1.1 Keyboard](https://www.w3.org/TR/WCAG22/#keyboard): all functions by keyboard.
- [2.2.1 Timing Adjustable](https://www.w3.org/TR/WCAG22/#timing-adjustable): turn off, adjust or extend.
- [2.3.3 Animation from Interactions](https://www.w3.org/TR/WCAG22/#animation-from-interactions): motion can be turned off (AAA).
- [2.4.3 Focus Order](https://www.w3.org/TR/WCAG22/#focus-order): order keeps the meaning.
- [2.4.7 Focus Visible](https://www.w3.org/TR/WCAG22/#focus-visible): the focus shows.
- [2.4.11 Focus Not Obscured (Minimum)](https://www.w3.org/TR/WCAG22/#focus-not-obscured-minimum): sticky bars hide no focus.
- [2.5.7 Dragging Movements](https://www.w3.org/TR/WCAG22/#dragging-movements): a single-pointer alternative to drag.
- [2.5.8 Target Size (Minimum)](https://www.w3.org/TR/WCAG22/#target-size-minimum): 24 by 24 CSS px.
- [3.3.1 Error Identification](https://www.w3.org/TR/WCAG22/#error-identification): say what failed, in text.
- [3.3.8 Accessible Authentication (Minimum)](https://www.w3.org/TR/WCAG22/#accessible-authentication-minimum): no cognitive test to log in.
- [4.1.2 Name, Role, Value](https://www.w3.org/TR/WCAG22/#name-role-value): custom controls expose all 3.
- [4.1.3 Status Messages](https://www.w3.org/TR/WCAG22/#status-messages): announce status without moving focus.

## Game Accessibility Guidelines (UI-relevant)
Source: https://gameaccessibilityguidelines.com/full-list/ (3 levels). Basic is the floor for any shipped game.
**Basic**
- [Ensure that all areas of the user interface can be accessed using the same input method as the gameplay](https://gameaccessibilityguidelines.com/ensure-that-all-areas-of-the-user-interface-can-be-accessed-using-the-same-input-method-as-the-gameplay/)
- [Allow controls to be remapped / reconfigured](https://gameaccessibilityguidelines.com/allow-controls-to-be-remapped-reconfigured/)
- [Use an easily readable default font size](https://gameaccessibilityguidelines.com/use-an-easily-readable-default-font-size/)
- [Provide high contrast between text/UI and background](https://gameaccessibilityguidelines.com/provide-high-contrast-between-text-ui-and-background/)
- [Ensure no essential information is conveyed by a fixed colour alone](https://gameaccessibilityguidelines.com/ensure-no-essential-information-is-conveyed-by-a-fixed-colour-alone/)
- [Allow the game to be started without the need to navigate through multiple levels of menus](https://gameaccessibilityguidelines.com/allow-the-game-to-be-started-without-the-need-to-navigate-through-multiple-levels-of-menus/)
- [Provide subtitles for all important speech](https://gameaccessibilityguidelines.com/provide-subtitles-for-all-important-speech/)
- [If any subtitles / captions are used, present them in a clear, easy to read way](https://gameaccessibilityguidelines.com/if-any-subtitles-captions-are-used-present-them-in-a-clear-easy-to-read-way/)
**Intermediate**
- [Allow interfaces to be resized](https://gameaccessibilityguidelines.com/allow-interfaces-to-be-resized/)
- [Avoid / provide alternatives to requiring buttons to be held down](https://gameaccessibilityguidelines.com/avoid-provide-alternatives-to-requiring-buttons-to-be-held-down/)
- [Provide a choice of text colour, low/high contrast choice as a minimum](https://gameaccessibilityguidelines.com/provide-a-choice-of-text-colour-low-high-contrast-choice-as-a-minimum/)
- [Allow subtitle/caption presentation to be customised](https://gameaccessibilityguidelines.com/allow-subtitle-caption-presentation-to-be-customised/)
- [Avoid (or provide option to disable) any difference between controller movement and camera movement](https://gameaccessibilityguidelines.com/avoid-or-provide-option-to-disable-any-difference-between-controller-movement-and-camera-movement/)
**Advanced**
- [Allow the font size to be adjusted](https://gameaccessibilityguidelines.com/allow-the-font-size-to-be-adjusted/)
- [Do not make precise timing essential to gameplay](https://gameaccessibilityguidelines.com/do-not-make-precise-timing-essential-to-gameplay-offer-alternatives-actions-that-can-be-carried-out-while-paused-or-a-skip-mechanism/)

What each asks of the UI: the whole menu works on controller and on keyboard, not only
mouse; every action can be remapped; text size is a setting; subtitles are readable and
customisable; motion (shake, parallax, flash) has an off switch.

## Consistency and expectation
Rules a capture can check. Each cites the standard it applies. CRAP is Robin Williams' contrast, repetition, alignment, proximity.

- A panel keeps its size and place when its state or selection changes (ISO 9241-112 consistency; Nielsen 4).
- The same control is in the same place on every screen. Example: unlink and deploy buttons stay at the bottom (ISO 9241-112 consistency; Nielsen 4; ISO 9241-110 conformity with user expectations).
- Items align to 1 grid with the same padding (CRAP alignment).
- A set of the same element (bubbles, toggles, cards) uses 1 style (CRAP repetition; Nielsen 4).
- Text never overflows its box (ISO 9241-112 interpretability; WCAG 1.4.4 Resize Text, 1.4.10 Reflow and 1.4.12 Text Spacing).
- The built UI matches the sizes of the approved wireframe (Nielsen 4; ISO 9241-110 conformity with user expectations).

Reviewer: capture 1 screen in 2 states (for example nothing selected and 1 item selected). Compare the two captures for changes in size and position. Any change that the state does not need is a finding.

## Platform notes
**Web**
- Focus order follows reading order (2.4.3). Show the focus (2.4.7) and never hide it under a sticky bar (2.4.11).
- Targets are 24 by 24 CSS px at least (2.5.8); 44 px is better on touch.
- Honour `prefers-reduced-motion` (2.3.3). Use native elements before ARIA (4.1.2).
- Canvas and WebGL games draw no DOM: give the menu real buttons or an accessible layer.
**Godot**
- `Control` focus: set `focus_mode`, `focus_neighbor_*` and `focus_next`/`focus_previous`; call `grab_focus()` on the first control of each screen.
- Read input through `ui_*` actions (`ui_accept`, `ui_cancel`, `ui_up` ...), not raw keys, so the player can remap them in the Input Map.
- Set font sizes through the `Theme` (one place), not per node, so a text-size setting changes all text.
- Keep a visible focus style in the theme. Test the screen with keyboard and controller only.
