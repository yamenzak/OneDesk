# OneDesk

One, built **on** the Frappe desk rather than beside it. One app, one module per
product, enabled per site.

## The rule everything else follows

**If the framework ships it, use it. Do not write our own.**

Before writing any UI, data access, or utility, look for it in this order:
`frappe` (the desk, the doctype, the workspace) → `@framework/ui` → `frappe-ui`.
Only then write something, and say in one line why nothing above fit.

This covers: dialogs, toasts and confirms (`frappe.msgprint`, `frappe.show_alert`,
`frappe.confirm`, `frappe.prompt`, `frappe.ui.Dialog`), fetching (`frappe.call`,
`frappe.db`, `frappe.client`), formatting and dates (`frappe.format`,
`frappe.datetime`), realtime (`frappe.realtime`), permissions (`frappe.perm`),
list and form UI, filters, child tables, notifications, follows, likes,
workflows, reports, dashboards and web forms.

## Declare, don't code

Doctypes, Workspaces, Docks, Desktop Icons, Sidebars, Roles, Print Formats,
Notifications and Workflows are **fixture JSON in this app**, synced by
`bench migrate`. A Python file that builds one of those at runtime is a bug.

## Writing code here

- Short files, one job each. Standard Frappe layout: `onedesk/<module>/doctype/…`.
- **Comments earn their place.** Explain *why* when it is not obvious, once, in
  a line or two. No essays, no restating the code, no decision logs in source —
  those go in the commit message.
- No dead code, no unused exports, no "kept in case". Delete it; git has it.
- No re-export barrels that defeat tree-shaking; import from the declaring module.
- Docs in `docs/` are **generated** by `scripts/docs.py`. Never edit them. If a
  fact has to be typed by hand in two places, one of them is wrong.

## The site

`onedesk.localhost` carries frappe, erpnext, hrms and onedesk, and nothing of
OneApp. OneApp is a separate repo on `space.localhost` and is not this app's
concern.

## The guards

`python -m pytest` — fast, no site needed, and every guard has a test proving
it still catches its own example.

- `test_borrowing.py` — a named list of what the framework does for us, and the
  pattern that must not appear. Add a rule when you find another.
- `test_declarative.py` — desk furniture is fixture JSON, and `modules.txt`
  agrees with the folders.
- `test_source_style.py` — no comment essays, no file that is mostly comment,
  nothing imported and unused.
- `test_generated.py` — `docs/` is current and upstream was read this fortnight.

`python scripts/upstream.py` says what landed in frappe, erpnext and hrms since
we last looked; `--record` marks today. Run it before starting anything — twice
now we have rebuilt something that had already shipped.
