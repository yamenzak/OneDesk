# OneDesk

One, built **on** the Frappe desk rather than beside it. One app, one module per
product, enabled per site.

## The rule everything else follows

**If the framework ships it, use it. Do not write our own.**

Before writing any UI, data access, or utility, look for it in this order:
`frappe` (the desk, the doctype, the workspace) → `@framework/ui` → `frappe-ui`.
Only then write something, and say in one line why nothing above fit.

**`docs/FRAMEWORK.md` is the list**, generated from the checkout we actually
have: every `frappe.*` namespace, what is callable directly, `frappe.utils`,
the `frappe.ui` classes, every `@framework/ui` export, the four ways a page
gets onto the desk, and the espresso design tokens. Read it before writing UI.

Which to reach for, when:

| you want | use |
|---|---|
| a message, a confirm, a prompt | `frappe.msgprint`, `frappe.show_alert`, `frappe.confirm`, `frappe.prompt` |
| a modal with fields | `frappe.ui.Dialog` |
| to call the server | `frappe.call`, `frappe.db.get_value`, `frappe.client` |
| a date or a number on screen | `frappe.datetime`, `frappe.format`, `frappe.utils` |
| live updates | `frappe.realtime` |
| to know if someone may | `frappe.perm`, `frappe.has_permission`, and doctype permissions |
| a list, a form, a filter, a child grid | the desk's own, or `@framework/ui` |
| a Vue screen inside the desk | an island — `frappe.ui.mount_island` |
| a colour, a radius, a shadow | an espresso token, never a literal |
| somewhere to keep a per-user preference | `frappe.model.user_settings` |

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
- `test_generated.py` — `docs/` and `docs/FRAMEWORK.md` are current, and
  upstream was read this fortnight.

`python scripts/reference.py` regenerates `docs/FRAMEWORK.md` from the frappe
checkout. It is pinned to the sha in `upstream.json`, so it describes the
framework we have rather than the one somebody remembered.

`python scripts/upstream.py` says what landed in frappe, erpnext and hrms since
we last looked; `--record` marks today. Run it before starting anything — twice
now we have rebuilt something that had already shipped.
