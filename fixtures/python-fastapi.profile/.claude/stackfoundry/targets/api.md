# Target `api`

Authenticated customer-facing API; carries personal data (orders).

## Stack

| Layer | Pack | Rulebook |
|---|---|---|
| language | language-python | not researched in this fixture |
| app-model | app-model-fastapi | not researched in this fixture |
| capability | capability-pydantic | not researched in this fixture |
| tooling | tooling-pytest | not researched in this fixture |

## Where things are

- Source: `app/**`. Entry point: `app/main.py` (`app`). Generated: `app/generated/**`.
- Tests: `tests/**`, pytest with FastAPI's `TestClient`.

## Gate

```sh
python -m pytest -q
```

## Oracle sources

`docs/specifications/orders.md`.

## Emphasis

Authorization on every order read (IDOR), pagination and input bounds, no order-id probing (404 not 403).
