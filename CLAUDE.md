# OneDesk

One, built **on** the Frappe desk rather than beside it. One app, one module per
product, enabled per site.

## How to answer me

I am the only person reading this and I already know what we are building.

* **Lead with the answer.** One or two sentences that would satisfy me if I read
  nothing else.
* **Under 150 words.** 300 if it is genuinely long.
* **No headers, no bold-label lists, no tables** unless I asked for a comparison
  or there are three-plus parallel items.
* **Say the thing, not the shape of the thing.** "The bell writes a
  `Document Follow` row" — not "**The control.** A bell beside the heart…".
* **Plain words, the way you would say them out loud.** Write it like you are
  explaining it to me at my desk. No aphorisms. No "it is not X, it is Y". No
  sentence that is there because it sounds good. If I have to read a line twice
  to get it, it failed — and a whole answer of clever lines is unreadable even
  when every fact in it is right.
* **The concrete thing first, the principle after** — and only if I need it.
  Name the file, the field, the button. "The photo has no GPS in it" beats
  "the photo answers who, never where".
* **One caveat, not five.** The one that would change what I do.
* **Do not restate work I just watched you do.** A commit hash and one line is a
  complete report.
* **Never re-explain a decision I already agreed to.**

Long form goes in commit messages and `docs/`. `/bro` means it
did not land — re-explain it simply.

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

## Several companies

**One now supports a workspace with several companies.** Until 3 November 2026
a workspace was one company, and `one/company.py` still hides every `Company`
field and fills it from the global default. That is undone module by module:
each module's next pass makes its screens work for several companies (the
passthrough skill, Several companies) and says so in its version.

The rule that stays: **a workspace with one company looks exactly as it does
today.** The company is shown, offered as a filter or asked for only once
there is a second one. Where it is shown it is defaulted (the reader's default,
the employee's, the party's), figures are one company's at a time in its own
currency, and nothing is added up across companies.

## Every figure keeps to what is set

Any figure that adds things up (a Home, a card, a chart, a total) is the
reader's default company's, in its currency, from amounts already in that
currency (`base_`, `stock_value`, `total_asset_cost`). A quantity is added up
only within one item, with its unit; across items it is worth. Money, numbers,
months and the first day of the week print the way the workspace and reader
set them, through the kit's `money`, `count`, `hours`, `quantity` and
`weekdays`. Nobody should have to ask for this.
`docs/PASSOVER.md`, What ERPNext already does, has the whole of it, and
`tests/guards/test_formats.py` catches a chart left on the browser's format.

## A screen of our own follows an app people know

Before drawing a screen of our own, find the app that does the same job best
(Shopify or Katana for stock, Linear for issues, Harvest for time) and draw it
the way they do, with frappe-ui's parts. A table is not a wall of text: a
picture or avatar, the name with its code quiet under it, one status as a
coloured Badge, figures right-aligned with their unit smaller and grey, a dash
for nothing, and filters as a picker and a row of TabButtons above it. Its row
in `docs/ISLANDS.md` "What each screen follows" says which app, and
`tests/guards/test_islands.py` fails a screen without one. Badge colours are frappe-ui's
(`gray`, `blue`, `green`, `amber`, `red`, `violet`); there is no orange.

## The passover

`docs/PASSOVER.md` is the seventeen points and how a screen is walked, short
enough to read before every screen. What each walk found and fixed goes in
its commit message, as the seventeen-point table. Where each area stands and
what is up next go in `docs/PASSOVER-LOG.md`, which is kept short; the log of
every walk up to 18 October 2026 is `git show b22b68f:docs/PASSOVER-LOG.md`. The
guards and the atlas check what a machine can; the walk is for what it
cannot (placement, the look, the words, the flow, a phone). How any pass is
run, whatever its focus, is the `passthrough` skill; a screen it finishes
is stamped Passed on dev (`one_interface/stamps.py`).

## Nothing ERPNext has is lost

The goal is every feature frappe, erpnext and hrms have, reached in One more
simply. `docs/ATLAS.md` lists every record type, report and page they ship
with how a person gets to it, and `tests/guards/test_atlas.py` fails when one
has no way in and no answer in `onedesk/one/atlas.py` beyond each module's
waiting count, which only falls. When a walk reaches a module, bring its
waiting count to zero: place each thing (rail, Home, Setup, a record's page)
or answer it. After an upstream update, `python scripts/atlas.py --snapshot`
then `--brand`; after a change to who may read what, `--site`.

The atlas also says, for each record type, who may open it, how much One
changed it, and whether OneStudio, OneAI and OneIntake reach it. Nothing a
person reaches may be open to nobody beyond each module's count. No sentence
of frappe's, erpnext's or hrms's names them: `onedesk/translations/` says One
instead, generated, but for the outside names in `onedesk/one/atlas.py`
`OUTSIDE`. Each of our screens is listed too, with what its server lists that it
does not hear change, prints bare or lists without the reader's company; each
count only falls. And for every record type a person reaches: the demo has
one, a document sent to a customer or supplier prints from ours (or is in
`NOT_SENT`), its list says more than a number, its labels read in Arabic and
German (a label they never translated goes in `onedesk/translations/words/`),
and what it sends is listed. Each count only falls.

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
- **No comments in code.** The why goes in the commit message, the module's
  README or a docstring. What stays: licence and attribution lines (`Derived
  from frappe/…`, copyright), tool directives (`noqa`, `fmt:`, `eslint-`), and
  docstrings, which OneAI reads as each tool's description and which tests
  read. Nothing a test checks may live in a comment.
- No dead code, no unused exports, no "kept in case". Delete it; git has it.
- No re-export barrels that defeat tree-shaking; import from the declaring module.
- Reference in `docs/` is **generated** — `MODULES.md`, `UPSTREAM.md`,
  `FRAMEWORK.md`, `OVERRIDES.md`, `ATLAS.md` and `atlas-site.json`. Never edit
  those. If a fact has to be typed by
  hand in two places, one of them is wrong.
- A **module's README** is written by hand, lives beside the module and says so
  in its first line — `onedesk/one_studio/README.md` is one. Everything above its
  `## Under the hood` heading is written for the people who use the module,
  because OneAI's `how_to` tool reads it to answer them; the rest is for us.
  A module keeps one README rather than plans and audits in `docs/`: git keeps
  the history. This is moving to `docs/READY.md`'s **A module's folder**
  (`AGENTS.md`, `SCRATCHPAD.md`, and `docs/` for help pages and versions),
  module by module.
- **A module in `onedesk/one/ready.py` changes only with a new version.**
  `python3 scripts/version.py <folder> <major|minor|fix> "<title>"` writes the
  next `docs/changelog/<version>.md` with the module's fingerprint; say in it,
  in English and for the people using the module, what they can do now.
  `tests/guards/test_ready.py` fails until it matches and is written.
- **`docs/BACKLOG.md` is what waits**: what is due now, the P3 frappe
  doctypes, what was decided against for now, each module's unbuilt parts and
  what the passover noticed. Something built leaves it; something put off goes
  in it.
- The rest of `docs/` is written by hand and short: `PASSOVER.md` (the
  points), `READY.md` (what a module needs before it goes live, what a
  finished module looks like, and the registry), `SHELL.md` (the
  record and list frame), `ISLANDS.md` (frappe-ui screens inside desk),
  `WORDING.md`, `ACCOUNTS.md`, and `docs/upstream/<date>.md` for each
  checkpoint.
- **A space's rail opens for its own roles.** erpnext and hrms keep some of
  what a rail links to for their System Manager; the space's `access.py`
  gives it to the roles People hands out, and
  `bench execute onedesk.one.reach.check` lists any link that still refuses.
- **Code a workspace runs is code OneAI wrote** (OneStudio). Nothing an
  administrator writes runs; an extension is kept off until guard.py has read
  it and a second model has passed it, its code is at a level only System
  Manager reads, and a tool's code argument is `unshown`. Read
  `one_studio/README.md` before touching scripts, DocTypes or what OneAI may
  write.
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

## Names and the licence

* **The product is One.** OneApp, OneSpace and the old OneAdmin control app
  were earlier names and earlier code; none of them is product-facing.
* **An id is not a name.** A module's directory, its Frappe module name and a
  doctype's name are ids, and they do not change when a product is renamed.
* **This repo is AGPL-3.0, and so are `frappe/crm`, `frappe/drive`,
  `frappe/sheets` and `frappe/helpdesk`.** Code may be taken from them, and
  taking it means keeping Frappe's copyright notice, saying at the top of the
  file what it was derived from, and never moving that file to a permissive
  licence. Anything that is really a frappe-ui component still comes from
  frappe-ui (MIT).

## The site

`onedesk.localhost` carries frappe, erpnext, hrms and onedesk, and nothing else.
OneApp and its control app, the product before OneDesk, are retired: their
repository is emptied and their sites are gone. Some module READMEs and
docstrings still say a piece was first written there; that is history, not a
dependency.

On the dev server the bench is `~/one-bench`, and `~/one-bench/CLAUDE.md`
(written by `deploy/local/setup.sh` from `deploy/local/CLAUDE.bench.md`) says
how that machine runs: the service, the sites on the domain, what never to do
there.

## The guards

`python -m pytest` — no site needed, and every guard has a test proving
it still catches its own example. Run it as `python3 scripts/quick.py --all`
(pytest-xdist, every core: about 35s for the whole suite, against two and a
half minutes in one process), and while working `python3 scripts/quick.py`,
which runs only the guard files that name what changed, in seconds. The
bookkeeping the guards check (docs/, the overrides ledger, a version's
fingerprint, what is left to translate) is written by `scripts/close.py`, so
it never fails a run; `--looked` re-dates a ready module's hand looks after
the commit. Every guard is listed by the passover point
it serves in `tests/guards/registry.py` and lives in `tests/guards/`, except
the two below that sit in `tests/` and are not in the registry.

The editors' own tests (`frontend/src/**/*.test.*`, taken with OneWorkbook and
OneWriter) run with `cd frontend && npx -p vitest@5 -p jsdom@26 vitest run`;
`frontend/vitest.config.mjs` gives them the same seams the build does.

- `test_borrowing.py` — a named list of what the framework does for us, and the
  pattern that must not appear. Add a rule when you find another.
- `test_declarative.py` — desk furniture is fixture JSON, and `modules.txt`
  agrees with the folders.
- `guards/test_source_style.py` — no file that is mostly comment, nothing
  imported and unused.
- `guards/test_generated.py` — `docs/` and `docs/FRAMEWORK.md` are current, upstream
  was read this fortnight, and every line we override is still there.

`python scripts/reference.py` regenerates `docs/FRAMEWORK.md` from the frappe
checkout. It is pinned to the sha in `upstream.json`, so it describes the
framework we have rather than the one somebody remembered.

**Upstream checkpoints** (docs/UPSTREAM.md). `upstream.json` records the
frappe, erpnext and hrms commits One runs on, and each move to newer ones is a
checkpoint with a note in `docs/upstream/<date>.md`:

1. `python scripts/upstream.py --fetch --draft` writes the note: what One leans
   on that moved, and what upstream shipped, every item open.
2. `--update` moves the bench to the note's commits (`ONE_BENCH_ENV` names a
   file sourced before each step, for Node, certificates and a proxy), then
   restart the bench.
3. Run `scripts/overrides.py --check`, the gates, the browser screens and the
   demo checks, and fix what broke.
4. Close every item: **Kept**, **Corrected**, **Adopted**, **Not for us**, or
   **Later** with a task.
5. `--checkpoint` records it. The guard fails while the bench is off the
   ledger, an item is open, or the last checkpoint is over 14 days old.

Run `python scripts/upstream.py` before starting anything. It says what landed
since the checkpoint. Twice now we have rebuilt something that had already
shipped.

**`docs/OVERRIDES.md` is every place we lean on somebody else's code** — a CSS
rule we outweigh, a class we subclass, a seam we hook, a field we write. Each
row names the upstream line it depends on, and the guard fails when that line is
gone, so an update that moves it breaks a test rather than a screen. Add a row in
`scripts/overrides.py` whenever you write one; ordinary use of a documented API
is not an override.
