# Known answers: vue-spa

## Target map

| Target | Paths | Stack |
|---|---|---|
| `web` | `src/**`, tests `src/**/__tests__/**` | language-typescript, app-model-vue-spa, tooling-vite, tooling-vitest |

## Planted defects

- **Badge counts lines, not items** (`src/components/CartBadge.vue`, `count`): the spec
  (`docs/specifications/cart.md`) says the badge shows the total quantity; the code shows `items.length`.
- **Float money** (`src/utils/money.ts`, `lineTotal`): multiplies floats and rounds with `toFixed`, so
  `lineTotal(1.005, 1)` gives `"1.00"` instead of the spec's `"1.01"` (round half up on cents).

## Weak test

- `src/components/__tests__/CartBadge.spec.ts`, `renders`: asserts only that the wrapper exists.

## Outdated pins

- `vitest` and `vite` are several majors behind; `vue` is behind on the 3.x line.
