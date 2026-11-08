---
type: llm
focus: { source: file, path: target-map.json }
weight: 2
---

PASS if the map has (at least) two separate targets: one covering `src/Api` whose packs include an ASP.NET Core app
model and not WPF, and one covering `src/Desktop` whose packs include a WPF app model and not ASP.NET Core; both
share a C# language pack; the tests under `tests/Api.Tests` belong to the API target (as test paths), not to a target
of their own with an app model.
FAIL if the two projects are merged into one target, if either target carries the other's app model, or if the test
project is treated as an application.
