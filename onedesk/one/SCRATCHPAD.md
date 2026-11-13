# One: scratchpad

Known issues, plans and open questions, kept short. Something done or
answered leaves it.

## Known

- **Privacy is One's in name only.** `privacy.py`, `privacy_copy.py` and
  `privacy_public.py` are TrustCenter's Your Data, and Your Data
  is in One's Help until they move into `trust_center` (ready.SHARED says so).
- **Webhooks is OneStudio's** and sits here until it moves.
- **The portal** (`portal*.py`) becomes its own module in a later plan;
  its Help page is One's until then.
- **Deleted Document's own list and form are still reachable** by their
  address, and a row of the bin opens the form to show what the record held
  (and an administrator's Delete). The page does not draw that yet.
- **A Recycle Bin row's title is cut off without an ellipsis** on a phone:
  `Branded` draws it in a span the row's `truncate` doesn't reach.
- **The Address Book is empty for most people.** frappe lets somebody
  without a sales, purchase or HR role read only the contacts they made, so
  Nadia's says No contacts yet. That is frappe's rule, not the screen's.

## Planned

- Nothing for One itself; the portal and Your Data move out (above).
- `atlas.py --site` is stale since the 3 November upstream (frappe's Flow
  record types), and rerunning it on one.4dl.dev says Access Log, Activity
  Log, DocType Layout, Module Profile, Package and Display Board Change have
  no demo record, which test_atlas refuses. Seed those, then rerun (6 Nov).
