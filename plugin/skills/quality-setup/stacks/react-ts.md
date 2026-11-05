# Stack pack: react-ts

- Status: full

This pack maps each gate rule of the lenses to a tool rule of React and TypeScript. It sets starter limits only. The ratchet (#374) sets the real limits from the repo.

## Tools

- ESLint: lints code. Reads `eslint.config.js`.
- typescript-eslint: type-aware rules such as `no-floating-promises`. Reads `eslint.config.js` and `tsconfig.json`.
- eslint-plugin-jsx-a11y: static accessibility lint of JSX. It assists AC-4 to AC-20 but gates none of them. Reads `eslint.config.js`.
- jscpd: finds duplicate code. Reads `.jscpd.json`.
- stylelint: checks CSS for colours, type scale and spacing scale. Reads `.stylelintrc.json`.
- axe-core with `@axe-core/playwright`: runs accessibility rules in a real browser. Reads the Playwright test.

## Rules

| ID | Tool rule | Starter limit | False positives |
|---|---|---|---|
| CP-7 | `max-lines-per-function` and `max-lines` (eslint) | 40 lines per function, 300 per file | generated code, long switch tables, JSX components |
| CP-8 | `jscpd` | 8 lines, 1 percent | generated code, markup that repeats on purpose |
| CQ-3 | `max-depth` (eslint) | 3 | nested JSX ternaries are not counted, so a reviewer still reads them |
| CQ-4 | `max-params` (eslint) | 4 | a framework callback with a fixed signature |
| CQ-6 | `no-empty` (eslint) | no empty catch block | a catch with only a comment: the rule allows it, a reviewer must read it |
| CQ-8 | `complexity` (eslint) | 10 | a long but flat `switch` over an enum |
| DS-1 | `no-restricted-imports` (eslint) | no import of a widget library the kit replaces | the kit's own wrapper file imports it |
| DS-2 | `color-no-hex` and `function-disallowed-list` (stylelint) | no hex, rgb or hsl value | the token file itself: turn the rules off there |
| UI-9 | `target-size` (axe-core) | 24 by 24 CSS px | an inline link in a sentence: the rule exempts it |
| VL-1 | `declaration-property-value-allowed-list` for `font-size` (stylelint) | values from the type scale tokens only | `inherit` or `1em` in a reset: add them to the list |
| VL-2 | `declaration-property-value-allowed-list` for spacing (stylelint) | values from the spacing scale tokens only | `0` and `auto`: add them to the list |
| AC-4 | `color-contrast` (axe-core) | 4.5:1, large text 3:1 | text over an image or gradient: axe reports "incomplete", a person checks it |
| AC-11 | `target-size` (axe-core) | 24 by 24 CSS px, or spaced | the same as UI-9 |
| AC-15 | `html-has-lang`, `html-lang-valid` and `valid-lang` (axe-core) | a valid `lang` on the page and on foreign passages | a passage of a name or a code in another script |
| AC-20 | `AxeBuilder.analyze()` (`@axe-core/playwright`) | 0 serious or critical violations | a violation in a third-party widget: record it and name the owner |
| CP-4 | assist: `@typescript-eslint/no-magic-numbers` | review only | array indexes, HTTP status codes, test values |

AC-4 needs a real browser. A jsdom test cannot compute colour, so it skips `color-contrast`.

## Config

File: `eslint.config.js`
```js
export default [
  {
    files: ['**/*.{ts,tsx}'],
    rules: {
      'max-lines-per-function': ['error', { max: 40, skipBlankLines: true, skipComments: true }],
      'max-lines': ['error', { max: 300, skipBlankLines: true, skipComments: true }],
      'max-depth': ['error', 3],
      'max-params': ['error', 4],
      'no-empty': ['error', { allowEmptyCatch: false }],
      complexity: ['error', 10],
      'no-restricted-imports': ['error', { paths: [{ name: 'react-select', message: 'Use Select from the kit.' }] }],
    },
  },
];
```

File: `.jscpd.json`
```json
{ "minLines": 8, "threshold": 1, "ignore": ["**/node_modules/**", "**/dist/**"] }
```

File: `.stylelintrc.json`
```json
{
  "rules": {
    "color-no-hex": true,
    "function-disallowed-list": ["rgb", "rgba", "hsl", "hsla"],
    "declaration-property-value-allowed-list": {
      "font-size": ["/^var\\(--font-size-/"],
      "/^(margin|padding|gap)/": ["/^var\\(--space-/", "0", "auto"]
    }
  }
}
```

File: `e2e/a11y.spec.ts`
```ts
import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

test('no serious or critical axe violation', async ({ page }) => {
  await page.goto('/');
  const { violations } = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag22aa'])
    .analyze();
  const bad = violations.filter((v) => v.impact === 'serious' || v.impact === 'critical');
  expect(bad).toEqual([]);
});
```
