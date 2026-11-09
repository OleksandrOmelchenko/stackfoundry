# Shop: repo profile

## The product

A small shop: a public web site prices orders through `src/Api`; staff print shelf labels with the `src/Desktop`
WPF app.

## What is at stake

Money (`api`: order totals and discounts) and data integrity (`desktop`: labels must match the barcode typed).

## Working agreements

- Git: writes only when the user asks.
- Docs root: `docs`. Specs in `docs/specifications/` are the first oracle for expected values.
