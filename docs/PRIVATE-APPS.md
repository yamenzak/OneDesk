# Private apps

A private app is a Frappe app made for one customer. No workspace has it until
it is given a code. Somebody there types the code into **Apps**, and the app
is installed on their site, migrations and all. From then on it is one of
One's apps, and it can never be turned off or uninstalled.

The code is `one_admin/private.py` (control plane) and `one/private.py`
(workspace). This file is how to write one, and how it gets to a customer.

## Writing one

It is an ordinary Frappe app, made with `bench new-app`. It lives in this
repository under `private/<app>`, beside One, so a change to One and the
app it breaks land in one commit; `private/rua` is the first. On a bench,
`apps/<app>` is a link to that folder.

The line between them runs one way. The app reaches into One through the
hooks One declares (`one_verbs`, `one_record_notices`, its own fields and
records); One never names the app: no import, no hook path, no example in
its docs. The app's tests live in `private/<app>/tests` (a plain `pytest`
from the root runs them), its words in its own `locale`, and One's
catalogue skips `private/` (`private/**,ignore`, first in
`babel_extractors.csv`), so One ships none of a customer's strings.
`tests/test_private.py` holds the line.

- **`hooks.py`** says it needs One, and that it is a private app:

  ```python
  required_apps = ["onedesk"]

  one_private_app = {
      "title": "Acme Fleet",
      "said": "Acme's vans, drivers and routes, and who drives what today.",
      "icon": "truck",
  }
  ```

  `title` and `said` are its card in Apps. `icon` is a name in the icon
  sprite, or one of its own `Custom Icon` fixtures.

- **Its own record types** live in its own module, as doctypes in the app.
  They are created when it is installed and changed by its patches, exactly
  as One's are.

- **Fields on somebody else's record types** (a Customer, a Sales Order) go
  in `<module>/custom/<doctype>.json`, the way One's own do. They are synced
  on install and on every migrate.

- **The rail.** Ship a `Dock` for the app with one Sidebar row, and that
  `Sidebar`, its `app` set to the app's name. One mounts the Dock on its own
  rail when the app is installed and on every migrate, so the app sits among
  One's apps, opens on its own sidebar, and its records open there.

- **Words.** Its own `locale/ar.po` and `de.po`, the same rules as One's:
  every word a person sees, in both.

- **Forward only.** It can't be uninstalled, so there is no undo. A patch
  that changes data has to be right the first time, and a field once used
  stays.

- **Licence.** One is AGPL-3.0, and an app built on it that is served to a
  customer is too.

## Getting it to a customer

1. Frappe Cloud takes an app from the root of a repository, so the folder
   is pushed to one of its own: `git subtree split --prefix private/<app>`
   and push that to the app's repository. Add it to the bench group.
   Deploy. Every site on the bench group then carries its code, and only the
   ones that claim it install it.
2. In OneAdmin, add a **Private App**: the app's name as in its `hooks.py`,
   its title and its sentence.
3. On it, **New Code**, and pick the workspace. The code is shown once. A new
   code for the same workspace replaces the old one.
4. Send the code to the customer. Somebody who administers their workspace
   opens **Apps**, types it under *Have a code for a private app?*, and
   presses **Add**.
5. OneAdmin queues an **Install App** job: it checks the app is on the bench
   group, asks Frappe Cloud to install it, and waits until it is. The card
   says *Installing…* meanwhile. When it is done the app is on the rail.

A failed job tells the operators and leaves the workspace as it was. Fix
what it says (usually: deploy the bench group with the app on it) and
**Resume** the job.

## What holds it in place

- A code is kept hashed, opens its app for its own workspace only, and is
  checked at twenty tries an hour per workspace.
- Apps refuses to turn a private app off, and its card has no switch.
- `bench uninstall-app` refuses one. Only `one_allow_private_uninstall` in
  the site's own `site_config.json` lifts that, for that site.
- A grant once claimed can't be taken off the Private App record.

## What is not built

- A bench group of its own for a customer whose code must not sit on the
  same servers as anybody else's.
- Taking a private app away again. By design there is no way, short of an
  operator with the server.
