# Stack pack: node-ts

- Status: full

This pack maps each gate rule of the lenses to a tool rule of Node and TypeScript. It sets starter limits only. The ratchet (#374) sets the real limits from the repo.

## Tools

- ESLint: lints code. Reads `eslint.config.js`.
- typescript-eslint: type-aware rules such as `no-floating-promises`. Reads `eslint.config.js` and `tsconfig.json`.
- eslint-plugin-sql: finds unsafe SQL built from input. Reads `eslint.config.js`.
- jscpd: finds duplicate code. Reads `.jscpd.json`.
- gitleaks: finds secrets in files and history. Reads its built-in rules.
- Semgrep: finds a plain `http://` URL with a rule of our own. Reads `.semgrep.yml`.
- Checkov: scans Dockerfiles for unsafe defaults. Reads the command line.
- `npm audit` or `pnpm audit`: lists known CVEs of dependencies. Reads the lock file.

## Rules

| ID | Tool rule | Starter limit | False positives |
|---|---|---|---|
| CP-7 | `max-lines-per-function` and `max-lines` (eslint) | 40 lines per function, 300 per file | generated code, long switch tables, a test file with many cases |
| CP-8 | `jscpd` | 8 lines, 1 percent | generated code, test set-up that repeats on purpose |
| CQ-3 | `max-depth` (eslint) | 3 | a flat `switch` with nested ifs in each case |
| CQ-4 | `max-params` (eslint) | 4 | a framework callback with a fixed signature |
| CQ-6 | `no-empty` (eslint) | no empty catch block | a catch with only a comment: the rule allows it, a reviewer must read it |
| CQ-8 | `complexity` (eslint) | 10 | a long but flat `switch` over an enum |
| SEC-4 | `sql/no-unsafe-query` (eslint-plugin-sql) | no template with input in a `sql` tag | a query built outside the `sql` tag: the rule cannot see it |
| SEC-5 | `gitleaks detect` | no finding | a fake key in a test; allow it by path in `.gitleaksignore` |
| SEC-6 | `plain-http-url` (semgrep, our rule) | no `http://` URL except localhost | an XML namespace URI such as `http://www.w3.org/...` |
| SEC-7 | `CKV_DOCKER_7` (checkov) | no `latest` base image tag | a tag that is a name only, such as a local build stage |
| SEC-8 | `audit --audit-level=critical` (npm or pnpm) | no critical advisory | an advisory in a dev-only tool that never ships |
| RB-1 | `no-restricted-globals` on `fetch` (eslint) | use the repo client, which sets a timeout | the client file itself: turn the rule off there |
| RB-3 | `@typescript-eslint/no-floating-promises` | no unhandled promise | a deliberate fire and forget: mark it with `void` |
| CP-4 | assist: `@typescript-eslint/no-magic-numbers` | review only | array indexes, HTTP status codes, test values |

## Config

File: `eslint.config.js`
```js
export default [
  {
    files: ['**/*.ts'],
    rules: {
      'max-lines-per-function': ['error', { max: 40, skipBlankLines: true, skipComments: true }],
      'max-lines': ['error', { max: 300, skipBlankLines: true, skipComments: true }],
      'max-depth': ['error', 3],
      'max-params': ['error', 4],
      'no-empty': ['error', { allowEmptyCatch: false }],
      complexity: ['error', 10],
      'sql/no-unsafe-query': 'error',
      'no-restricted-globals': ['error', { name: 'fetch', message: 'Use the repo client: it sets a timeout.' }],
      '@typescript-eslint/no-floating-promises': 'error',
    },
  },
];
```

File: `.jscpd.json`
```json
{ "minLines": 8, "threshold": 1, "ignore": ["**/node_modules/**", "**/dist/**"] }
```

File: `.semgrep.yml`
```yaml
rules:
  - id: plain-http-url
    message: Use https. A plain http URL sends data in the clear.
    severity: ERROR
    languages: [generic]
    pattern-regex: 'http://'
    pattern-not-regex: 'http://(localhost|127\.0\.0\.1)'
```
