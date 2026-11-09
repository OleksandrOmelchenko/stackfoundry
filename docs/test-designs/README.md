# Test designs

Risk-ranked test lists written by `/stackfoundry:design-tests` **before** tests exist, then written by
`/stackfoundry:write-tests --design`, reviewed by `/stackfoundry:review-tests` and fixed by
`/stackfoundry:fix-tests`. Each design is a tracker: status lives on each row.

## Row status (last cell)

⬜ to write · ✍️ written (`path::TestName`) · ✅ reviewed SOUND · ⚠️ flagged by review (verdict + reason) ·
❓ question (no source for the expected value) · ⏸ quarantined (owner, issue, expiry) · 🚫 dropped (reason).
Open = anything but ✅ and 🚫.

## Banner

`**Open:** TD-1, TD-4 · **Questions:** Q1`: open ids and open questions, never tallies.
`stackfoundry tracker check <file>` verifies it.

## Index

| Design | State | Open |
|---|---|---|
