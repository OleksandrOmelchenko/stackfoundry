# Target `desktop`

WPF label-printing app used by staff; a wrong or silently failed print costs a relabel.

## Stack

| Layer | Pack | Rulebook |
|---|---|---|
| language | language-csharp | not researched in this fixture |
| app-model | app-model-wpf | not researched in this fixture |
| capability | capability-mvvm-toolkit | not researched in this fixture |

## Where things are

- Source: `src/Desktop/**`. View models: `src/Desktop/ViewModels/`.
- Tests: none yet.

## Gate

```sh
dotnet build src/Desktop -c Release
```

## Emphasis

Command state (CanExecute refresh), errors surfaced to the user, UI-thread use of async code.
