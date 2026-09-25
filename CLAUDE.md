# OneDesk

One, built **on** the Frappe desk rather than beside it. One app, one module per
product, enabled per site.

## The rule everything else follows

**If the framework ships it, use it. Do not write our own.**

Before writing any UI, data access, or utility, look for it in this order:
`frappe` (the desk, the doctype, the workspace) → `@framework/ui` → `frappe-ui`.
Only then write something, and say in one line why nothing above fit.

**How a part looks follows frappe-ui**, which is the more finished design.
Espresso, the desk's own parts, is frappe-ui ported to plain HTML, and the
port is sometimes behind. Before using an espresso part, open the same
component in frappe-ui (`src/components/<Name>/`: the `.vue`, the `.md`, the
stories) and match its layout, variant, size and colour where they differ.
Behaviour stays frappe's.

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

## The setup wizard

A tenant configures their whole site here — frappe, erpnext, hr, and every One
module they turned on. Two different things arrive wearing the same clothes:

- **Real configuration** — company, chart of accounts, financial year, HR
  settings. It stays. Every module a site enables should contribute its own
  slide, and a site that does not enable a module should never see it.
- **Telemetry and vendor questions** — erpnext's `persona` slide asked four
  required questions that only `capture_user_persona` read, and offered
  Accounting/Manufacturing/Stock. Spliced out.

`frappe.setup.on("before_load")` gives both moves: `add_slide` to contribute,
`slides.splice` to replace. Both erpnext and hrms gate on a boot flag — hrms on
`frappe.boot.hr_only_setup` — so per-site slides are their pattern, not ours.

## One workspace is one company

**Multi-company is not a thing One does.** A group that runs four companies buys
four workspaces. There is no consolidation, no inter-company anything, and no
screen that has to ask whose record this is.

So **every `Company` field is hidden**, on all two hundred-odd doctypes erpnext
and hrms put one on. `one/company.py` does it after every migrate, the global
default fills the value, and a document that can do better than the default does
— an attendance request and a shift request take it from the employee. When you
add a field or meet a screen that asks which company, the answer is to take the
question off the screen, not to answer it.

## Declare, don't code

Doctypes, Workspaces, Docks, Sidebars, Roles, Print Formats, Notifications and
Workflows are **fixture JSON in this app**, synced by `bench migrate`. A Python
file that builds one of those at runtime is a bug.

## Navigation is the Apps screen and the dock

The desk has two navigations. The **Apps screen** — `add_to_apps_screen`, a
`Dock` of `Sidebar` rows — is the one frappe is building on. The **icon grid** —
`Desktop Icon`, `Desktop Layout`, `Desktop Settings.desktop_page` — is the one
`frappe/desk/RETIRING.md` lists for removal in a single batch, and the desk
itself offers to move people off it.

**We build on the first and ship nothing for the second.** One takes one tile;
every product is a row in its dock, and that row names a `Sidebar` — ours, or
another app's, since nothing requires them to match. `tests/test_declarative.py`
refuses a `Desktop Icon` fixture.

Frappe has not named a date, so this is where the framework is going rather than
where it has gone. If the grid is still there in a year that changes nothing:
the dock does the same job on the surface that is not in a removal list.

**A module name is bench-wide.** `frappe.local.module_app` is built by walking
every app on the bench, not on the site, so two apps that name a module the same
break each other's imports on sites that carry only one of them.

## Writing code here

- Short files, one job each. Standard Frappe layout: `onedesk/<module>/doctype/…`.
- **Comments earn their place.** Explain *why* when it is not obvious, once, in
  a line or two. No essays, no restating the code, no decision logs in source —
  those go in the commit message.
- No dead code, no unused exports, no "kept in case". Delete it; git has it.
- No re-export barrels that defeat tree-shaking; import from the declaring module.
- Reference in `docs/` is **generated** — `MODULES.md`, `UPSTREAM.md`,
  `FRAMEWORK.md`, `OVERRIDES.md`. Never edit those. If a fact has to be typed by
  hand in two places, one of them is wrong.
- A **module's README** is written by hand, lives beside the module and says so
  in its first line — `onedesk/one_hr/README.md` is one. Everything above its
  `## Under the hood` heading is written for the people who use the module,
  because OneAI's `how_to` tool reads it to answer them; the rest is for us.
  A module keeps one README rather than plans and audits in `docs/`: git keeps
  the history.
- **`docs/ACCOUNTS.md` is where a company's accounts come from**, and why
  onboarding must not default to the country's chart of accounts. Read it
  before touching company setup; the instinct it warns about is the obvious
  one.
- **A child doctype's custom fields go in their own `custom/<child>.json`.**
  `sync_customizations_for_doctype` inserts the Custom Field rows from a
  parent's file but runs `updatedb` only on the file's own `doctype`, so the
  column is never created and the first save fails with "Unknown column".
- **`docs/WORDING.md` is how a label and a description are written**, taken from
  frappe's own JSON rather than invented. Read it before adding a field, and
  remember its last rule: rewording is also a translation change, so the POT and
  `locale/ar.po` and `de.po` move in the same commit.

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
- `test_generated.py` — `docs/` and `docs/FRAMEWORK.md` are current, upstream
  was read this fortnight, and every line we override is still there.

`python scripts/reference.py` regenerates `docs/FRAMEWORK.md` from the frappe
checkout. It is pinned to the sha in `upstream.json`, so it describes the
framework we have rather than the one somebody remembered.

`python scripts/upstream.py` says what landed in frappe, erpnext and hrms since
we last looked; `--record` marks today. Run it before starting anything — twice
now we have rebuilt something that had already shipped.

**`docs/OVERRIDES.md` is every place we lean on somebody else's code** — a CSS
rule we outweigh, a class we subclass, a seam we hook, a field we write. Each
row names the upstream line it depends on, and the guard fails when that line is
gone, so an update that moves it breaks a test rather than a screen. Add a row in
`scripts/overrides.py` whenever you write one; ordinary use of a documented API
is not an override.
