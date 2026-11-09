# Target `web`

Public Vue single-page shop front-end; shows cart contents and totals.

## Where things are

- Source: `src/**`. Components: `src/components/`. Money helpers: `src/utils/money.ts`.
- Tests: `src/**/__tests__/**`, Vitest with `@vue/test-utils` in jsdom.

## Gate

```sh
npm run build
npm test
```

## Oracle sources

`docs/specifications/cart.md`.

## Emphasis

Money formatting and rounding, what the customer sees in the cart.
