# Specifications

Living specs of built or in-flight features. A spec is the first **oracle** for tests (`.stackfoundry/rules/testing.md`
§1): keep its behaviours precise.

## What a spec holds

1. Title, then `**Category:** <word>` on line 3 (vocabulary in `../plans/README.md`).
2. **Status**: built / partly built / in flight, in one line.
3. **Why**: the motivation; the only place for history.
4. **Behaviour**: what it does, precisely enough to test, with the rules and edge cases.
5. **Design**: the shape in code, by path + symbol.
6. **Verification**: what was exercised and that the gate was green (no suite totals).
7. **Follow-ups (not yet implemented)**: bullets; removed in the change that resolves them.

## Index

| Spec | Category | Status |
|---|---|---|
| [Context budgets per assistant](context-budgets.md) | cli | built |
