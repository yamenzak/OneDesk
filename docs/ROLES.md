# Roles

How a workspace decides who may do what, module by module, and the plan for
it. The guide for the people using it is `onedesk/one/README.md` (Access,
for the Workspace); this is the design under it.

## What there was

Workspace › Access already had most of a role system, under another name:

- **Levels.** Each of the five business apps (OneCRM, OneBook, OneInventory,
  OneProject, OneHR) had None, User and Manager, and a workspace could add
  its own between them ("Senior Sales"). A level's page was a matrix: a row
  per record type, a switch per right (Select, Read, Edit, Create, Delete,
  Submit, Cancel, Export), saved as frappe's Custom DocPerm.
- **Profiles.** A job's level in every app at once (frappe's Role Profile),
  picked on a person's page.
- **People.** A select per app on each person's page, listing the app's
  levels, the workspace's own among them.

Two things it couldn't say:

1. **What a module does that isn't a record right.** "Changes signatures",
   "turns on an out-of-office", "edits OneAI settings" aren't Create or Edit
   on any record type. They were hard-coded checks (OneMail's
   `holders.may_manage`, the Mail Manager role).
2. **The modules everyone has.** OneMail, OneCloud, OneTask, OneCalendar and
   OneAI had no levels at all, so nothing in them could be given to some
   people and not others.

## The design

### Roles, not levels

A level is renamed a **role** wherever a person reads it. Nothing else about
it changes: it is a frappe Role with `one_app` set, between the app's User and
Manager. Code keeps the word level (`access.py`), since renaming a working
engine buys nothing.

### Abilities are frappe's Permission Types

Frappe ships the piece this needs: **Permission Type** (`frappe/core/doctype/
permission_type`). An app declares a permission of its own on a doctype, such
as `one_sign` on Email Account; frappe adds it as a column to DocPerm, Custom
DocPerm and DocShare, shows it in the Role Permissions Manager, and answers it
in `frappe.has_permission(doctype, ptype, doc)`, through roles and through
shares alike. An app's permission types are files in its modules
(`<module>/permission_type/<name>/<name>.json`), synced on migrate like
doctypes.

So an **ability** is one or two permission types, and the role builder writes
them where frappe reads them:

- **For a role**, on Custom DocPerm, the same rows the record matrix already
  writes. Frappe wants at least Select on a row, so an ability row carries
  Select: the record can be picked in a link, nothing more.
- **For one record**, on DocShare. This is the second layer OneMail needs:
  a role says what someone may do on every mailbox, a share says what they
  may do on this one. Frappe always adds Read to a share; for a mailbox that
  is its settings, which whoever manages it may see.

A module declares its abilities once, in `<module>/abilities.py`, named by the
`one_abilities` hook: the doctype, the label, what it means, and its **kind**:

- **Switch**: on or off, one permission type.
- **Choice**: a dropdown of scopes, two permission types. For OneMail, "No",
  "Their own address" and "Every mailbox": `one_sign_own` and `one_sign`.

`one/abilities.py` is the one engine: what a role holds (`of`), saving a role's
abilities (`save`), whether somebody may do one (`may`), and a mailbox's
shares (`grants`, `grant`). A module asks `abilities.may("one_sign", doc)` and
never looks at roles itself.

Defaults are written on migrate (`abilities.settle`) only for a role that has
no row on the doctype yet, so a workspace's own changes are never undone by
an update, the same rule the record matrix keeps. An ability an update
brings (its Permission Type is newer than the role's row) is given its
default once, and remembered as given (`abilities._arrived`), so turning it
off afterwards sticks: OneAI Manager got Knowledge that way.

### The role builder

A module's roles are built in AccessCenter (docs/READY.md, mechanism 14),
which every module's ControlCenter opens from **Roles and Access**, because
that is where somebody thinking "who can change signatures" goes. It is a
Workspace Administrator's.

It is one matrix rather than a page per role: the module's abilities down
the side, in its groups, and its roles across the top (User, the
workspace's own, Manager). A scope is a dropdown, a switch is a switch, and
each cell saves as it changes (`access.set_ability`). A cell above User
starts at User's value, since every role holds User's roles. **New Role**
adds a column based on another; a custom role's name renames or deletes it.
The abilities' column stays put while the roles scroll sideways under it,
and **Show Roles** picks which columns show, kept for each person.
`public/js/role_matrix.js` draws it for any module that declares abilities,
from `access.matrix_of`.

Workspace › Access keeps what crosses modules: every app's roles in one
list, profiles, groups and people. Clicking a role of a module with
abilities opens AccessCenter on it (`Settings.access`); the business apps' roles
still open a page here with the record-type matrix, until their stage.

### Modules everyone has

OneMail joins the apps with roles. Everyone holds its User role
(`OneMail User`, made from OneMail's abilities.py and given to everybody by
a patch and to each new person). There is no None: a person's page offers User, the workspace's own
roles, and Manager. Mail Manager, made in the last change, becomes OneMail's
Manager, and the separate Mail Manager switch on a person's page goes.
Profiles take OneMail like any other app.

### A module's own roles

A module ships its roles from its own folder: `<module>/abilities.py`
declares its abilities and, in DEFAULTS, the roles it ships and what each
starts with. Migrate makes those roles if they aren't there and writes their
defaults once (`abilities.settle`); there is no fixture. The module's Help
shows the same defaults (`{roles}` on a page, `abilities.defaults_table`), so
what the page says is what ships. OneMail's are on its Who Can Do What page.

One person given more on one record than their role says is a share,
written by `abilities.grant` and nothing else; OneMail's per-mailbox Edit
Access is the first. `tests/guards/test_ready.py` holds both.

## Stages

1. **Engine and OneMail.** Permission types, `one/abilities.py`, roles in
   place of levels, OneMail as an app with roles, the role builder as a
   matrix in OneMail's settings, the Users tab's per-mailbox abilities,
   OneMail's checks moved onto `abilities.may`. Guide, tests, demo checks.
2. **OneCloud.** Sharing outside the workspace, deleting others' files,
   storage settings; per-folder grants on Drive's own model.
3. **OneTask and OneCalendar.** Assigning to others, others' calendars.
4. **OneAI.** Who may run it, act without approval, change its settings and
   spend credits; this is where the per-module AI settings land.
5. **The five business apps.** Their abilities beside their record matrix:
   approving, discounts past a limit, seeing cost and margin.

Each stage is the same four steps: a module's `abilities.py`, its permission
types, its own checks moved onto `abilities.may`, and a Roles tab in its
settings drawing `role_matrix.js`.
