# Private apps

A private app is a Frappe app made for one customer. No workspace has it until
it is given a code. Somebody there types the code into **Apps**, and the app
is installed on their site, migrations and all. From then on it is one of
One's apps, and it can never be turned off or uninstalled.

The code is `one_admin/private.py` (control plane) and `account_center/private.py`
(workspace). This file is how to write one, and how it gets to a customer.

## Writing one

It is an ordinary Frappe app, made with `bench new-app`. It lives in this
repository under `private/<app>`, beside One, so a change to One and the
app it breaks land in one commit; `private/rua` is the first. Every
release's bench carries every one of them as an app of the bench, installed
on no site until a workspace claims it (On the bench, below). On the dev
bench, `apps/<app>` is a link to that folder.

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

- **`pyproject.toml`** names the project as its folder, and says which
  frappe and which One it runs on, because Pilot refuses an app that
  doesn't:

  ```toml
  [tool.bench.frappe-dependencies]
  frappe = ">=17.0.0-dev,<18.0.0"
  onedesk = ">=0.0.1"
  ```

- **Its names are its own.** Its Python package and every module in its
  `modules.txt` must be a name no other app on the bench uses: frappe,
  erpnext, hrms, One, or another private app. Frappe keys its module map
  by the module name across the whole bench, so a second `Accounts` breaks
  erpnext on every site, including the ones without the private app.

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

1. Push `main`. The release build reads every `private/<app>/<app>/hooks.py`
   for its `one_private_app` (`deploy/release/upload.py`, `declared`: parsed,
   never imported, so the build runs none of the app's code and One still
   names none of them) and lists them in the release's
   `releases/<sha>.json` as `private_apps`.
2. OneAdmin's release check (`releases.check`, hourly and when the release
   workflow says one is up) makes the **Private App** records from that
   list (`private.register`): one per app, its title, sentence and icon
   kept to what `hooks.py` says. Nobody adds one by hand, and the form
   doesn't offer New. A record no release declares any more is deleted
   only while no workspace holds a code for it; **Enabled** is the
   operator's and a release never changes it.
3. On it, **New Code**, and pick the workspace. The code is shown once. A new
   code for the same workspace replaces the old one.
4. Send the code to the customer. Somebody who administers their workspace
   opens **Apps**, types it under *Have a code for a private app?*, and
   presses **Add**.
5. OneAdmin queues an **Install App** job: it asks Pilot on the workspace's
   server whether the app is on its bench (`GET /apps`), asks it to install
   the app on the site (`POST /sites/<site>/apps`), and waits for Pilot's
   task and until the site lists the app. The card says *Installing…*
   meanwhile. When it is done the app is on the rail.

A failed job tells the operators and leaves the workspace as it was. Fix
what it says and **Resume** the job. A workspace whose bench is from a
release before the app fails at *Checking the app is on the server*; it
moves to the newest release in its window, and Resume then installs it.

## On the bench

`deploy/release/private.py` puts every folder under `private/` on the
release's bench, after One and before the archives are made. Each is copied
to the bench's `private-apps/<app>` and given a repository of its own (one
commit, branch `main`), then linked into `apps/<app>` and listed in
`bench.toml` the way Pilot links a local checkout: Pilot lists it in
`GET /apps` and never updates or fetches it. Pilot checks it as it checks
any app it is given, it is installed into the bench's Python, added to
`apps.txt`, and its `public/` built when it has one. The bench archive
carries `private-apps/` and the link, so every box has them; the box's
agent lists them in `bench.toml` again when it unpacks the bench, and
does the same when it builds a release from its commits, as `first-boot.sh`
does for a new box's first bench.

No site gets it there. The template site is made with frappe, erpnext,
hrms and One only, and `spares.as_template` stops the build if a private
app is installed on it, so a spare never holds one. A workspace moved to
another bench of its box needs every app it has on that bench; the agent
refuses the move before touching anything when one is missing.

The build stops, naming the app and why, when a private app:

- isn't a Frappe app (no `<app>/hooks.py`), or its folder isn't a lower
  case Python name;
- has no `one_private_app` with a title;
- has a `pyproject.toml` naming another project;
- takes a Python package or a Frappe module another app on the bench
  already has (including another private app);
- is refused by Pilot's checks or does not install into the bench's Python.

`tests/test_private.py` runs the same checks against the private apps in
the repository, and against frappe, erpnext and hrms where they sit beside
it, so a clash fails the gates before it fails a release.

## What holds it in place

- A code is kept hashed, opens its app for its own workspace only, and is
  checked at twenty tries an hour per workspace.
- Apps refuses to turn a private app off, and its card has no switch.
- `bench uninstall-app` refuses one. Only `one_allow_private_uninstall` in
  the site's own `site_config.json` lifts that, for that site.
- A grant once claimed can't be taken off the Private App record.

## What is not built

- A server of its own for a customer whose code must not sit on the same
  servers as anybody else's, with `private/` left out of every other bench.
- Taking a private app away again. By design there is no way, short of an
  operator with the server.
