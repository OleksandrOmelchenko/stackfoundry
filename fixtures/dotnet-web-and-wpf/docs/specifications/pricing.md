# Pricing

**Category:** commerce

## Status

Built.

## Behaviour

- An order total is the sum of `unit price × quantity` over its lines, in euros, rounded to cents.
- **An order of 100.00 or more gets 10% off the whole total.** Below 100.00 there is no discount.
- A line with a quantity below 1 is rejected (`ArgumentOutOfRangeException`).

## Follow-ups (not yet implemented)

- Per-customer discount codes.
