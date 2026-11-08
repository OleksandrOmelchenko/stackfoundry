# Known answers: dotnet-web-and-wpf

## Target map

| Target | Paths | Stack |
|---|---|---|
| `api` | `src/Api/**`, tests `tests/Api.Tests/**` | language-csharp, app-model-aspnet-core, tooling-xunit |
| `desktop` | `src/Desktop/**` | language-csharp, app-model-wpf, capability-mvvm-toolkit |

The two targets share the `csharp` language pack and nothing else. A map that gives `desktop` the ASP.NET Core
pack, or merges the two targets, is wrong.

## Planted defects

- **Pricing boundary** (`src/Api/Pricing.cs`, `Pricing.Total`): the spec (`docs/specifications/pricing.md`) says an
  order of **100.00 or more** gets 10% off; the code uses `>`, so exactly 100.00 pays full price.
- **Stale command state** (`src/Desktop/ViewModels/LabelViewModel.cs`, `Barcode` setter): `PrintCommand`'s
  `CanExecute` depends on `Barcode`, but the setter never calls `PrintCommand.NotifyCanExecuteChanged()`, so the
  Print button stays disabled after a barcode is typed.
- **Swallowed failure** (`LabelViewModel.PrintAsync`): the `catch` ignores the exception, so a failed print looks
  like success.

## Weak tests

- `tests/Api.Tests/PricingTests.cs`, `Pricing_CanBeCreated`: asserts only `NotNull` (UNCLEAR/WEAK).
- `Total_AppliesDiscount`: computes the expected value with the production formula (tautology, WRONG-ORACLE
  smell), and tests 150 only, so the 100.00 boundary mutant survives (WEAK).

## Outdated or vulnerable pin

- `Newtonsoft.Json` 12.0.1 in `Directory.Packages.props`: a known high-severity advisory (deep nesting DoS), fixed
  in 13.0.1.
