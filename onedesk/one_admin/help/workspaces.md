# Workspaces

**Workspaces** lists every customer workspace with its status, plan, owner and
storage against its plan's limit. A workspace's record is read-only: it says
what happened to it.

## Statuses

A workspace is built, then **Live**. When a payment fails, or its subscription
is cancelled in Stripe, it moves one step a night:

1. **Payment overdue** for 7 days. It keeps working.
2. **Suspended** for 14 days. Nobody can sign in, and nothing is changed.
3. **Archived** for 30 days. The site is deleted after a backup. Files stay.
4. Then its files are deleted.

The periods are set in [Settings](settings). Paying before the site is deleted
brings it back once nothing is left unpaid.

A workspace whose build **Failed** stays as it is until an operator resumes
its job or archives it.

## Its Buttons

Each button moves the workspace one step, and asks first.

| Button | What it does |
| --- | --- |
| **Mark Overdue**, **Suspend**, **Archive**, **Delete Files** | Move it to the next status now. Archiving and deleting files can't be undone. |
| **Restore** | Brings back an overdue or suspended workspace. |
| **Refresh** | Measures its storage, or checks its domains again. |
| **Billing** | Its invoices, giving credits, its credit ledger and its AI usage. |

## What the Owner Hears

The owner is emailed when the workspace is suspended, archived (with the
deletion date) and restored, and when a payment fails.

## Closing on Request

The workspace's billing contact can close it from its Plan and Credits page.
It closes 14 days later, and the subscription ends with its period. Until that
day they can keep it open. Operators are told when it is asked for.
