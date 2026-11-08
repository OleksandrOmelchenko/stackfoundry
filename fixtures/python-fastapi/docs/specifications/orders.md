# Orders

**Category:** commerce

## Status

Built.

## Behaviour

- Every request carries the caller's customer id in the `X-Customer-Id` header (set by the gateway after sign-in).
- `GET /orders/{id}` returns the order **only when it belongs to the caller**; otherwise `404` (never `403`, so
  order ids cannot be probed).
- `GET /orders?page=N&size=M` lists the caller's orders, newest first. **Pages start at 1**; page 1 holds the
  first `size` orders. `size` is between 1 and 50.

## Follow-ups (not yet implemented)

- Order cancellation.
