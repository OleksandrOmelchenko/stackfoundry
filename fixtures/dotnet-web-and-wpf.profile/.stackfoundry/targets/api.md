# Target `api`

Public HTTP API; computes order totals, so it carries money.

## Stack

| Layer | Pack | Rulebook |
|---|---|---|
| language | language-csharp | not researched in this fixture |
| app-model | app-model-aspnet-core | not researched in this fixture |
| tooling | tooling-xunit | not researched in this fixture |

## Where things are

- Source: `src/Api/**`. Entry point: `src/Api/Program.cs`. Pricing: `Pricing.Total`.
- Tests: `tests/Api.Tests/**`, xUnit v3.

## Gate

```sh
dotnet build src/Api -c Release
dotnet test tests/Api.Tests -c Release
```

## Oracle sources

`docs/specifications/pricing.md`, then the rulebooks.

## Emphasis

Money: boundaries of discounts and rounding, input validation of order lines.
