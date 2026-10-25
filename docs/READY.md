# Ready for live

A module is ready for live when it passes the fourteen points below, and the
registry (`onedesk/one/ready.py`, checked by `tests/guards/test_ready.py`)
says so. OneMail is the first. From then on every change to a ready module
goes through the same points, so it stays ready.

`docs/PASSOVER.md` walks each screen against its seventeen points. This
file says what a module needs on top of that before people outside the
company use it, and, under **What finished looks like**, what each of the
seventeen points looks like in a finished module. It took in what was
`docs/STANDARD.md`, written when OneProject was closed.

Most points are a mechanism first and a check second. The mechanisms are
built once, for every module, and each section says what exists today and
what is missing. The checklist at the end is what a module is checked
against once they exist.

## The order

The mechanisms are built in this order, because each one leans on the one
before it:

1. **Copy.** Every other mechanism writes words on a screen.
2. **One home per module.** Everything else is a file in that home.
3. **Versions and What's New.**
4. **Docs and Help.**
5. **The module's foot: Settings, Help, version.** One settings dialog per
   module, role-aware.
6. **Legal in the module.** What the module adds to the agreements, shown in
   its settings dialog.
7. **Roles that ship.**
8. **Notifications.**
9. **Setup steps.**
10. **Tours.**
11. **OneAI reach.**
12. **The registry and its guard.**

Then OneMail is taken through the fourteen points, and marked ready.

## A module's folder

Every module has the same folder, and nothing else in it is written by hand
in Markdown:

```
onedesk/<module>/
  AGENTS.md            the one file for agents: OneAI and us
  SCRATCHPAD.md        known issues and plans, kept short
  docs/
    <page>.md          the wiki, one page per thing people do
    changelog/
      <version>.md     one per version, the newest is the version
  legal.py             what it adds to the agreements
  notifications.py     what it tells people, and on which channels
  abilities.py         what its roles may do
  setup.py             what the setup wizard may ask
  tour.py              its first-visit tour
  ai.py                its OneAI tools, and NOT_FOR_AI
  demo.py, checks.py   its part of the demo company, and its checks
  tests/               its tests
  doctype/, page/, permission_type/, custom/, patches/
```

- **`AGENTS.md`** is what the module is, its records and rules, where each
  file is, what OneAI may do in it and why, and the decisions that cost
  something. It replaces the README, which goes.
- **`SCRATCHPAD.md`** is what is known to be wrong and what is planned. What
  `docs/BACKLOG.md` says about a module moves here, and something done
  leaves it.
- **`docs/`** is for the people who use the module. Its pages are the Help
  dialog, and its `changelog/` is What's New.
- **No other `.md` file in a module.** A notification type, today a
  Markdown file in `notifications/<module>/`, becomes a declaration in the
  module's `notifications.py`, as a clause is in `legal.py`.
  `tests/guards/test_ready.py` fails on any other.

What frappe makes live elsewhere goes to a folder of the module's own name
there:

- **Desk scripts and styles** in `public/js/<module>/` and
  `public/css/<module>/`, because frappe serves only `public/`.
- **Vue screens** in `frontend/src/<screens>/` (OneMail's are `mail/`),
  because the islands build resolves frappe-ui and the kit from `frontend/`.
- **Fixtures and translations**, which are per app.

`onedesk/one/ready.py` names each module's places, so the guards read all of
them. The root `docs/`
keeps what has no single module: this file, the passover, OneInterface, the
wording and the generated reference.

## The mechanisms

### 1. Copy

**Today.** `docs/WORDING.md` has the rules for labels, descriptions,
notifications and screens. `tests/guards/test_wording.py` checks
descriptions (130 characters, two sentences, no first person, no em dash)
and screen text (140 characters, no joined clauses).

**Missing.** A OneInterface section with hard limits and a tone, and a guard
that reads the strings a screen actually shows, not only doctype JSON.

**To build.**

- **Headings** are five words or fewer: tab titles, panel titles, dialog
  titles, section headings and tour steps.
- **A description is one sentence.** It says what the thing is or what it
  does, never how to use the screen.
- **A list of words we never show:** simply, just, easily, please, utilize,
  leverage, seamless, powerful, robust, note that, in order to, functionality,
  "Are you sure", "Something went wrong", and any word for our framework.
- **Three before and after pairs** for the tone, taken from screens we
  already fixed:
  - "Only a Mail Manager or an administrator can change this." becomes
    "Your role doesn't allow changing this."
  - "Allow Private Mailboxes" as a row of its own becomes the switch beside
    the title.
  - "Gmail and Outlook require an app password." is kept: it says the fact
    and nothing else.
- **A guard** that reads `title:`, `label:`, `description:` and heading
  strings passed to `__()` in a module's JS and Vue, and holds them to the
  limits and the banned list.

### 2. One home per module

**Done for OneMail.** Everything of OneMail is in its places
(`onedesk/one/ready.py`):

- **The folder,** `onedesk/one_mail/`. It holds the Python, the doctypes, the
  notification types (`notifications.py`), the OneAI tools (`ai.py`, now
  including the mailbox and template tools), mail templates
  (`mail_templates.py`), its demo step (`demo.py`, still called "mail" by the
  build), its checks (`checks.py`, which the suite imports through
  `ready.MODULES`) and its tests (`tests/`, which plain pytest collects).
- **Its static folders,** `public/js/one_mail/` and `public/css/one_mail/`:
  the settings dialog, the composer, the rule builder, the record's Mail tab
  and the mail template editor.
- **Its screens,** `frontend/src/mail/`, with the island's entry
  (`island.js`).

**Kept out on purpose** (`ready.SHARED`): `brand/onemail.svg`, because every
product's mark is drawn into one sprite; and
`templates/emails/one_mail.html`, which frames every mail One sends.

**Guards.** `tests/guards/test_ready.py` fails on anything left in `OUTSIDE`
and on any tracked file named for the module outside its places. The guards
that read the suite read every module's `checks.py` (`tree.suite()`), and the
ones that read only the top of `public/js` or `public/css` also read `one_*/`.

### 3. Versions and What's New

**Built, and OneMail is at 1.0.0.** As below, with these details:

- `onedesk/one/ready.py` reads a module's versions (`versions`, `current`)
  and takes its fingerprint over what it ships (`shipped`): its code, its
  screens and its help pages, but not AGENTS.md, SCRATCHPAD.md, its
  versions, its tests, its checks or its part of the demo.
- `scripts/version.py one_mail minor "Title"` writes the next file.
- `tests/guards/test_ready.py` holds the newest fingerprint to the module's,
  versions to follow one another from 1.0.0 by their kind, and every entry
  to a title of five words or fewer and words with no file, function or
  commit in them. A picture an entry names must sit beside it.
- `one/versions.py` sends What's New: the entries, newest first, rendered,
  with a picture sent inside its entry, each marked New past the version
  the reader last saw, which opening them moves on (a user default per
  module). `frappe.boot.one_versions` carries each module's version and
  whether it is unseen.
- The version sits at the end of the module's foot row (`win.foot_action`
  with `version`), with a dot until seen, beside a Help button.
- What's New (`public/js/module_docs.js`, `onedesk.whats_new.open`) is a
  OneInterface settings dialog whose sidebar is the module's own: its mark,
  a search, and a tree with each fix under the minor it fixes and each
  minor under its major, a dot on the unseen ones. The chosen version fills
  the panel with its pictures and a Read More row of buttons for the Help
  pages its `docs:` front matter names. `test_ready.py` fails on a `docs:`
  page that is not a Help page.

**Before.** Nothing per module. Frappe's own What's New dialog
(`frappe/utils/change_log.py`) is per app and reads
`<app>/change_log/v1/v1_2_3.md`.

**To build.**

- **Where entries live.** Each module keeps `docs/changelog/` with one
  Markdown file per version, such as `one_mail/docs/changelog/1.4.0.md`. The
  newest file is the version.
- **What a file says.** Its front matter has the date, the kind (major,
  minor or fix) and a title. The body is written for the people who use the
  module, in English only: what they can do now, and what changed for them.
  It never says which file, function or commit. A major version may have
  screenshots beside it.
- **Forced.** The front matter also carries a fingerprint of the module's
  files. `tests/guards/test_ready.py` fails when the files and the newest
  fingerprint disagree, so no change to a ready module goes in without a new
  version. `scripts/version.py <module> minor` writes the next file with the
  new fingerprint, and leaves its words for us to write.
- **Seen in the app.** The version shows at the foot of the module's rail.
  Clicking it opens a What's New dialog with the entries the reader hasn't
  seen, marked with a dot until they have. Each reader's last-seen version
  is kept per module.
- **Docs follow.** When a version changes what a Help page says, the page
  changes in the same commit.

### 4. Docs and Help

**Done for OneMail.** Its README is gone:
`AGENTS.md` holds Connections and what was under the hood, `docs/` holds nine
pages for its users (What OneMail Is, Your addresses, Settings, Connecting a
mailbox, Reading and writing, Rules and out of office, Mail on records,
Attachments and pictures, Asking OneAI), and `SCRATCHPAD.md` holds what is
not built, the known issues and the order it was built in. OneAI's
`how_to` reads a module's `docs/` pages when it has an `AGENTS.md`
(`one_ai/guide.py manuals`), as OneMail › Rules and out of office. The guards
that read READMEs read these too, and `test_ready.py` fails on any other
Markdown in the module.

Help (`onedesk.help.open`, the same dialog as What's New) opens from the
question mark at the module's foot. Its tree is the pages in the order
`ready.MODULES[...]["help"]` gives, each with its icon, and the open page's
sections (its `##` headings) under it, the one at the top marked as you
scroll. The search above it reads every section's heading and words and
lists the matches with the words marked; picking one opens the page at that
section with them marked there too. A link to another page
(`[Settings](settings)`) opens it in place.

A page is written to be scanned: a line or two, then sections, with tables
for anything parallel, numbered steps for anything done in order, a
blockquote for the one thing worth knowing, and a cropped picture of the
screen it talks about beside it in `docs/<page>/`, sent inside the page.
`test_ready.py` fails on a page not listed, a page that names code (what a
claim rests on goes in `AGENTS.md`, under Where Help's claims are kept), a
heading over five words, a picture that isn't there, and a link to a page
Help doesn't list.

**Before.** Every module has a `README.md`. Above `## Under the hood` it is
written for users, and OneAI's `how_to` (`one_ai/guide.py`) searches that
part. No module has a `docs/` folder.

**To build.** Each module has two kinds of writing:

- **`docs/`, the module's wiki.** One page per thing people do, written for
  them: Connect a Mailbox, Out of Office, Automation, Mail Templates. It
  follows the copy rules. The Help dialog shows it, opened from the module's
  foot, from a `?` in its settings dialog, and from a tour's last step.
  OneAI's `how_to` searches it.
- **`AGENTS.md`, one file for agents.** That means OneAI and us: what the
  module is, its records, its rules, where each file is, what OneAI may do
  in it and why, and the decisions that cost something. It replaces
  README's "Under the hood". The users' half of the README moves to
  `docs/`, and the README itself goes (decided 2026-10-25).

### 5. The module's foot, and one settings dialog

**Built.** `onedesk.module_settings.open({ module, may, tabs })`
(`public/js/module_settings.js`) is every module's settings dialog: frappe's
settings dialog with ControlCenter and the module under it, and a Help
button, at the top of its sidebar. `onedesk.module_head` draws that for
every dialog a module has: One's mark and a name in the products' manner,
the first word light (HelpCenter, UpdateCenter for What's New,
ControlCenter, AccountCenter for one mailbox), and, small under it, whose:
the module's mark and name, or one thing in it, such as a mailbox's
address (`dialog.center`). The names are names, so they are not
translated (`onedesk.CENTERS`). Each tab names the `needs` it asks of the reader's role (an ability's
key, a list of keys any one of which will do, or a function), the dialog
leaves out what the role doesn't allow and drops a group left empty.
`onedesk.module_settings.kit` is what tabs are drawn with: list rows, a
heading with a control at its end, a switch after a tab's title, Back
before a view's title, a Save that shows once something changed; its
classes are `one-set-*` in `public/css/module_settings.css`, and a module's
own stylesheet keeps only what is its own. The foot is
`win.module_foot({ module, settings })`, `windowModuleFoot` in an island:
Settings, then Help and the version. `test_ready.py` fails on a module that
draws its own settings dialog or its own foot. OneMail is on both.

**Before.** OneMail had a SettingsDialog (`onemail_settings.js`) with its
helpers inside it, opened from Settings at the foot of its rail and from
Workspace Settings › Access. Tabs showed by ability
(`frappe.boot.one_mail_may`). No other module had one.

**To build.**

- **One way to make it.** `onedesk.module_settings(module, tabs)` builds the
  dialog for any module. It holds the helpers OneMail's file defines today
  (rows, views, a header switch, read-only values). Each tab declares the
  ability it needs, and the dialog leaves out what the reader may not use.
- **The foot of every module's rail** has the same three: **Settings**,
  **Help** and the **version**.

### 6. Legal in the module

**Today.** Each module declares what it adds to the agreements in its own
`legal.py`: `clause()` for a paragraph of a document, `subprocessor()` for a
company it sends data to (OneMail names Cloudflare, Gravatar and Google).
`one_legal/assemble.py` puts them into the eight documents, and those are
what the Agreements page shows, what is printed, and what people are asked
to agree to. An agreement's version is `revision.hash`. Any change to a
clause moves the hash, and `tests/guards/test_legal.py` fails until we
either bump the revision (people agree again) or record the new hash (a
typo). A host the code calls that no `subprocessor()` declares also fails
it.

**Built.** Every module's ControlCenter ends with **Legal**
(`onedesk.module_settings.legal`, added by `module_settings.open`, so a
module can't leave it out). It reads `one_legal.reading.of_module(module)`,
which is `assemble.of_module`: from the same registry the documents are
assembled from, each agreement the module writes into, with its current
version and the module's own paragraphs under their sections, and the
companies it sends data to, with what for, what they get and where. **Read
in Full** opens the agreement in Agreements. A version of the module
records `legal:`, a hash of the module's own part of each agreement
(`assemble.stamp`, which another module's clauses don't move), written by
`scripts/version.py`; `test_ready.py` fails when the newest version's stamp
isn't the module's, and when a version moves it without its words naming
the agreement.

**Before.** Nothing in a module showed what it adds to the agreements.

**As planned.**

- **A Legal tab in every module's settings dialog.** It lists the module's
  clauses under the agreement each sits in, and the companies it sends data
  to, with what they get and where. Each agreement shows its current
  version and opens in full. Everybody can read it, because the agreements
  are everybody's.
- **One call that answers it:** `one_legal.reading.of_module(module)`, read
  from the same registry the documents are assembled from, so the tab and
  the agreements can't disagree.
- **A legal change is a module change.** `legal.py` is inside the module, so
  changing it changes the fingerprint and needs a new module version. When
  the change bumps a revision, the What's New entry says what people are
  asked to agree to again.

### 7. Roles that ship

**Built.** A module's roles come from its folder alone. `<module>/abilities.py`,
named by the `one_abilities` hook, declares its abilities, the role everyone
holds (EVERYONE) and DEFAULTS: every role it ships and what each starts with.
`abilities.settle`, on migrate, makes a role named there if it isn't there
and writes its defaults once, so a workspace's own changes survive an update;
the Role fixture is gone. The module's Help shows the same defaults: `{roles}`
on a page becomes `abilities.defaults_table`, in English as Help is, so the
page can't say other than what ships. Overrides are one idea: `abilities.grant`
gives one person more on one record than their role says, as a share frappe
answers, and nothing else in a module writes a share. `test_ready.py` fails on
a ready module without abilities.py or its hook, with defaults naming an
ability it doesn't declare, without `{roles}` in its Help, with a Role fixture,
or writing a share itself.

**Before.** The abilities engine (`one/abilities.py`, the `one_abilities`
hook, `docs/ROLES.md`). OneMail ships OneMail User, given to everyone, and
Mail Manager. Roles are columns in the Roles matrix. The only override is a
grant on one mailbox (Users › Edit Access).

**To build.**

- **Each ready module ships its roles** as fixtures, with the default
  matrix in `docs/ROLES.md` checked against the fixtures.
- **Overrides become one idea**: a grant to one person on one record, over
  what their role says. OneMail's per-mailbox grant is the first, and every
  module's overrides use the same `abilities.grant`.

### 8. Notifications

**Today.** `one/notify.py` is the one door. Each type is a file in
`notifications/<module>/`, with who gets it, the button, and whether it
mails and pushes. The channels are:

- the bell (frappe's Notification Log);
- email, through frappe's `email_notification_types`;
- push (`one/push.py`, Web Push).

`from_one` makes a mail wear One's mark. Anything else wears the workspace's.
OneMail sends ten types.

**To build.** This is the groundwork for the larger rework you have
planned:

- **Every type says its channels:** bell, email, push, and Telegram when it
  comes. A channel left out says why, such as "no email: it is about mail".
- **Every type says its sender:** `system` (Four Degree Labs, One's mark)
  or `workspace` (the workspace's name and colour). This replaces
  `from_one`.
- **A look per channel**, written down once: the email layout we have, a
  push's title and body limits, and the bell's line.
- **Per module**, the types live in the module's home (mechanism 2).

Once that exists, the point to check is short: the module tells people what
they need to know, on the channels that make sense, only to the roles that
should hear it.

### 9. Setup steps

**Today.** The setup wizard has two slides of ours (look and working day).
Nothing per module.

**To build.** Each module declares its steps in `setup.py`. A step has a
title, its fields, whether it can be left for later, and how to tell it's
done. A step left for later shows as a to-do in the module's settings
dialog. OneMail's steps would be:

- the company's domains and Default Incoming and Outgoing;
- whether private mailboxes are allowed;
- the mail templates to start from.

Which steps the wizard shows is decided when the wizard is built.

### 10. Tours

**Today.** Frappe ships Form Tour (`ui_tour`, `page_route`), started from
`frappe.boot.onboarding_tours` and remembered in `user.onboarding_status`.
`frappe.Driver` is loaded on every page. We use none of it.

**To build.**

- **Each module ships one tour**, as a Form Tour fixture on its page. A step
  points at a stable `data-tour` attribute, never a class.
- **When it runs:** on the first visit. Help › Take the Tour runs it again.
- **What a step says** follows the copy rules: a heading of five words or
  fewer, and one sentence.

### 11. OneAI reach

**Today.** OneMail's tools are open a conversation, what waits for an
answer, draft a reply, suggest a rule, sign a mailbox, and templates
(`hooks.py` `one_ai_reads` and `one_ai_suggests`, the `mail` group).

**Missing:** out of office, folders, sharing, connection and the mailbox
policy.

**To build.** Every whitelisted method that changes something in a ready
module either has an OneAI tool that does the same through the page's own
code, or is named in the module's `NOT_FOR_AI` with the reason (a password
is one). The guard reads both.

### 12. The registry

`onedesk/one/ready.py` lists each module with its version and, per point,
either what checks it automatically or the date and commit it was last
checked by hand. `tests/guards/test_ready.py` holds a module marked ready to
every automatic check:

- the fingerprint is current;
- `docs/` and `AGENTS.md` are there;
- its roles are fixtures;
- its `legal.py` declares what it adds, and the Legal tab reads it;
- every notification type says its channels and sender;
- its setup steps and tour are declared;
- every action is OneAI's or named as not.

## The fourteen points

A module is checked against these once the mechanisms exist. Each point
names its mechanism.

1. **One home.** All of the module is in its folder, apart from what frappe
   forces elsewhere (mechanism 2).
2. **Versioned.** A version and a What's New entry for every change, written
   for its users (mechanism 3).
3. **What's New in the app.** The version at its foot opens the entries
   (mechanism 3).
4. **Documented.** `AGENTS.md` for agents and a `docs/` wiki for people,
   shown in Help (mechanism 4).
5. **Copy.** Every heading and description it shows passes the copy rules
   (mechanism 1).
6. **Roles.** Its roles ship, its overrides use grants, and the matrix is
   written down (mechanism 7).
7. **OneAI.** Everything a person can do here, OneAI can do as a card, or
   there is a stated reason not (mechanism 11).
8. **Demo and tests.** The demo company uses every part of it, and a check
   or test covers every behaviour (point 1 under **What finished looks
   like**).
9. **Notifications.** It tells people what they need, on the right channels,
   only to the right roles (mechanism 8).
10. **OneInterface pass.** On OneInterface, tokens only, frappe-ui and frappe
    controls, realtime where data changes under it, values formatted by
    frappe, and the reader's date, number and time zone preferences. This is
    checked in the browser, as each role, desktop and phone.
11. **Setup steps.** What the setup wizard can ask is declared, with what can
    wait (mechanism 9).
12. **Tour.** A first-visit tour that can be run again (mechanism 10).
13. **Settings.** One role-aware settings dialog where everything about the
    module is managed (mechanism 5).
14. **Legal.** Every fact about what it does with data that the agreements
    must say is a clause or a subprocessor in its `legal.py`, and its
    settings show them (mechanism 6).

## How a module is finished

OneProject was the first module finished against every point of the
passover, closed on 2026-10-09, and your word was "OneProject will be the
standard". What follows is what finished means, taken from it.

1. **The baseline.** Run the gates before touching anything, and write down
   the counts. They are what "nothing broke" is measured against.
2. **Screen by screen.** Split the module into its screens the way its people
   use it. For OneProject that was six:
   - the list and every view of it, and New Project;
   - a project's head and Overview;
   - Tasks, Time and Money;
   - Invoices, Suppliers, Team, Files and Activity;
   - Workload, Timesheet and Templates;
   - across modules, from the other side of each hand-off.
3. **Every point, every screen.** Look at the screen in the browser as the
   people who use it (OneProject used Samir, who runs projects, and Huda, who
   keeps the books), on a desktop and a phone, and read the code behind it.
   Write the findings in the screen's commit message. Each screen ends
   with a table of all seventeen points, plus Everything follows frappe and
   What ERPNext already does, saying what was looked at, even where nothing
   was found. A point left out of the table is a point not checked.
4. **Fix, then look again.** Fix every finding, see it in the browser, run the
   gates, commit and push, and show a screenshot.
5. **Revisit.** OneProject's first three screens were walked before the rule
   that every point is written down. They were walked again against the
   points they had skipped, and that found as much as the first walk. A
   module is not finished until every screen has every point in its table.
6. **Close it.** Mark the module closed in `docs/PASSOVER-LOG.md`, and write
   what stays open in the module's `SCRATCHPAD.md`.

## What finished looks like

### Works

**1 Demo coverage.** The demo company holds a real case of every kind the
module has. OneProject has a fixed price villa with sub-projects and a
subcontract, a curtain wall tower counted by attendance on site, a time and
materials showroom billed in euros, two retainers, an internal project, a
completed one and a cancelled one. Each record is made by the person whose
work it is, on the day it happened (`one_demo/history.py` moves it back).

- Every whitelisted method and every OneAI tool is reached by a demo check
  (`tests/guards/test_coverage.py`). OneProject's checks run as the people
  who would do the work, with `bench … one_demo.check.run --kwargs "{'only':
  'oneproject_'}"`.
- Each screen's walk adds a check that says what the walk found, such as
  `oneproject_its_tasks_time_and_money_keep_their_rules`.
- **Watch for** demo data that lies. On OneProject every open task was
  overdue, every invoice was due the day the demo was built, retention was
  paid in full, the workshop's time sat on the handover tasks, and a Berlin
  customer lived in Business Bay. The product was right each time and the
  demo made it look wrong. Fix the builder, then repair the site the same
  way, so a rebuilt demo and this one agree.

**2 Rules on the server.** Every rule is on the record's own hooks in
`hooks.py`, so the page, a bulk edit, a report cell and Data Import all meet
it. OneProject keeps these there:

- a project isn't closed with open work, and an internal one bills nobody
  (`status.py`, `kinds.py`);
- a budget is its cost types, and a cost centre's budget is the books' own
  (`budget.py`);
- milestones bill between 0 and 100% of the contract, and together at most
  all of it (`milestones.py`);
- a cancelled project takes no new work, and somebody who can't sign in
  joins no project (`members.py`);
- time on a project billed by the hour is billable, a timesheet row's task is
  on its project, and a retainer's hours are billed only with their month
  (`hours.py`, `retainer.py`);
- a new quotation, order or invoice takes the customer's one open project
  (`chain.py`);
- hours, budgets and bill shares are never below 0 (`non_negative` on the
  fields).

Checked by `tests/guards/test_rules.py` and by the demo, each rule changed
every way. **Watch for** a rule that lives in an endpoint behind a button.
The button offers and orchestrates. The record decides.

**3 Hand-offs.** The README's **Connections** says where the module's data
comes from and where it goes, one line per module. Each hand-off runs end to
end on the demo (`one_demo/check.py` HANDOFFS, `tests/guards/test_handoffs.py`).
The document a project hands on says the project at the top, by name,
opening its page (`one_project/heads.py`). The last screen of the walk is from the
other side of each hand-off, as the person who works there.

### Stays desk

**4 Tier declared.** `onedesk/one/tiers.py` says how each record is shown and
why, and every collection view frappe has, as frappe's own or ours.
OneProject has two pages of their own (Project and Project Template), heads
on the documents it hands on, Project's List, Report, Kanban, Calendar,
Gantt, Tree, Image and Dashboard declared, and Task's List, Gantt and Kanban.
No view frappe offers is taken away.

**5 Our look.** The project page has its own look, built from frappe-ui. It
is checked at 1440 wide and on a phone. **Watch for** text cut off in a
column, a figure only a bar says, a large empty state where every other one
is a line, and a list that only fits on a desktop.

**One figure.** Set by the user on 2026-10-20: a record's head, a module's
Home, a record page of ours and ERPNext's own overviews drew numbers three
ways. A figure is one card everywhere: a small grey label, the number at
20px, one line under it (a caption, or a change against last month), framed
with 8px corners, with a bar or a sparkline below where there is one. On the
desk it is frappe's `frappe.ui.stat_card`, so a head and ERPNext's Customer
Overview are the same card; on an island it is frappe-ui's NumberCard in the
same frame, through the kit's `Figures`. A number that warns is red-7,
frappe's negative. `tests/guards/test_figures.py` holds it.

**Money and tax.** Set by the user on 2026-10-20: One is sold to any country,
in any currency, under any tax. An amount always carries its own currency;
there is no heading that names the currency so the figures under it need not.
A generic label says **Tax**, **Tax ID** and **Tax Return**, never VAT or TRN.
What really is one country's (the UAE VAT 201, the UAE tax-invoice block, the
documents a UAE employer files) stays, shown only where the workspace's
country is that one. A figure that has a tax on it, or one shown before tax,
is underlined dashed and says the other side on hover: `other` on the kit's
`Figures`, and `head.taxed` on a desk record's head.
`tests/guards/test_any_country.py` holds it, with the regional files listed
and each one's reason.

**A module's Home tells its story.** Set by the user on 2026-10-13, first on
OneInventory. A Home opens on figures with sparklines (frappe-ui's
NumberCard, each against last month), a button for each kind of thing that
needs somebody, then the module's story in parts, top to bottom, each a row of
frappe-ui's charts. Use the whole range (Number Card, Area, Bar stacked,
grouped and horizontal, Donut and half Donut, Sankey, Heatmap, Funnel,
Scatter) where each fits what it shows, and colour by what a chart shows: a
kind keeps its hue, statuses keep theirs, magnitude runs light to dark. Never
two value axes on one chart. Every figure keeps to what the workspace and
the reader set (`docs/PASSOVER.md`, What ERPNext already does, Figures that
add things up): the reader's company in its currency, worth across items
rather than mixed units, and frappe's own formats. Every figure is read as the reader may see it,
and a slice or a bar opens what it stands for. What needs somebody (Today)
and the directory (Everything) stay beside it as tabs.

**A screen of our own follows an app people know.** Set by the user on
2026-10-13, first on Stock on Hand. Before a screen is drawn, the app that
does the same job best is looked at (Shopify's Inventory and Katana's Stock
for what the stores hold) and the screen follows its layout, built from
frappe-ui. A list of records is not a wall of text: a picture or avatar, the
name with its code quiet under it, one status as a coloured Badge, figures
right-aligned with the unit smaller and grey and a dash for nothing, and
filters as a picker and TabButtons above it rather than a long row of tabs.
Its row in `docs/ISLANDS.md` names its model, which
`tests/guards/test_islands.py` holds.

**6 Nothing lost.** A page of its own keeps everything frappe's form gives.
Its sidebar is frappe's own, its menu is frappe's under the page's, it saves
against the `modified` it loaded, and it hears changes made elsewhere
(`tests/guards/test_frame.py`). Every field on the form can be changed on
the page, in place or in Edit Details (`test_a_page_edits_every_field_of_its_record`).

**Nothing upstream is lost either.** Set by the user on 2026-10-13. Every
record type, report and page frappe, erpnext and hrms ship has a way in or a
written answer (`docs/ATLAS.md`, drawn by `scripts/atlas.py`). A way in is
seen (a rail, a Home, one of our screens) or found (a form's link, its
Connections tab, a list's Related Reports); a record on a page of our own has
no Connections tab, so what only its form led to has to be placed again.
Anything else is answered in `onedesk/one/atlas.py` as engine, inside,
replaced or left out, or waits. `tests/guards/test_atlas.py` holds what waits
in each module to a count that only falls, and an upstream update that adds a
record type fails until it is placed. **A module's walk is not done while its
modules have anything waiting.**
The same map says who may open each thing (from the demo site, kept the
site's by a demo check): nothing reached may be open to nobody beyond each
module's count. And no sentence frappe, erpnext or hrms say names them:
`onedesk/translations/<lang>.csv`, generated from the snapshot, says One in
English, Arabic and German, but for the outside names kept on purpose.
And each of our own screens is read for what its server lists: every one it
does not hear change, every number it prints bare, and every company's
record it lists without the reader's company, each held to a count that only
falls. Five of the points are read for every record type a person reaches as
well: point 1, the demo has one; point 11, a document sent to a customer or
supplier prints from a format of ours; point 5, its list says more than a
number; point 12, its labels read in Arabic and German; and point 10, what is
sent about it is listed. The first four are held to counts that only fall.

**Changing a field where it is shown.** A field on a page is changed where it
is shown, not in a dialog, and it is the record's own form field (set by the
user on 2026-10-12, first on the item page).
- The page holds the record's real desk form, out of sight
  (`onedesk.record.form`, the kit's `useForm`), as frappe's own Data Import
  dialog holds one. Its client scripts, queries, `depends_on` and
  `set_df_property` all run.
- Each field shows its value as the form formats it, with a pencil (a
  chevron for a Link or Select). The pencil floats that form's own control
  over the place (`onedesk.record.lend`, the kit's `FieldEdit`). It floats
  rather than moves because a page's island has its own styles, which
  desk's don't reach.
- A change saves the form as desk saves it, against the `modified` it
  loaded. Enter or leaving the field saves, Escape reloads it unchanged.
  Long text gets Save and Cancel. A Check is frappe-ui's Switch, which sets
  the form's value and saves.
- A field the form hides is not shown, and one it locks has no pencil. A
  script that locks or hides a field after the refresh is heard too.
- A field of a table row is changed the same way, as the form's grid makes
  its control (`onedesk.record.lend_row`, `FieldEdit` with `table` and
  `row`). A new row is added as the grid adds one, and its fields go in
  together with Save and Cancel (an item's reorder levels).
- Each label sits on the left and its value on the right (`Facts`).
- Something on or off is a Switch, never a checkbox, on a page as in a
  filter (set by the user on 2026-10-12). A checkbox is only a step ticked
  off a checklist or a task done (`test_a_setting_is_a_switch`).

OneProject and OneTask follow this when they are next passed.

**The head and the breadcrumb.** Set by the user on 2026-10-13, for every
page.
- Every crumb with somewhere to go is a switcher with a search box, as a
  link field searches (`public/js/crumb_switch.js`). The place's crumb lists
  the app's places. A record's crumb lists records of its kind, its own
  suggestions first (a project's open projects), and finds any by typing.
  **All …** stays at the foot. A page never draws a menu of its own on a
  crumb; it gives the trail a `menu` and the switcher draws it.
- On a phone the head is two bars, each its own height with a line under it
  (`public/js/phone_head.js`). The trail splits over them. The first bar has
  the panel's button, the place, the page's buttons and search. The second
  is the record's: its name, its status and a scope such as a project's All
  Work. A list's second bar has its view switch.
- A page that gathers several kinds of record keeps frappe's view switch,
  leading to their List and Report views (`public/js/page_views.js`).

**7 Extensible.** Every view of a page is a place where OneStudio's
extensions go, told what the view shows (`one_studio/places.py`, mapped to
its source in `tests/guards/test_frame.py`). OneProject has one for the page
and one for each tab (Overview, Tasks, Time, Money, Invoices, Suppliers,
Team, Files, Activity), and one each for the Projects list, a template and
Workload. A place's notes and buttons are drawn as frappe-ui's Alert and
Button (`PlaceSpot`).

**8 Built from frappe.** Every part comes from frappe-ui first, then the
desk's own parts, then frappe's primitives. Every value goes through
`frappe.format`. **Watch for** a number rounded by hand, a date written by
hand, or an amount without its currency.

**9 Overrides recorded.** Whatever of frappe's, ERPNext's or HRMS's the module
changes is a row in `scripts/overrides.py`, and `python3 scripts/overrides.py
--check` passes. OneProject has 45 rows.

### Speaks

**10 Notifications.** Every event someone should hear about is one file in
`onedesk/notifications/<module>/`, rendered by the hub, in the reader's
language. OneProject has sixteen, from Added to Project to Bill Due, each
listed under **Being told** in the README with who gets it. **Watch for**
amounts in the site's currency instead of the company's, a notice sent to
whoever did it, and a notice told during an install, a migrate or an import.

**11 Printed.** Every record that leaves the company has a print format we
ship, laid out in frappe's print format builder and checked by
`tests/guards/test_print.py`. A format is drawn from the builder's own pieces
(One Sales Invoice is the first), or, until it is redrawn, from the print
blocks (`one/print_blocks.py`, `templates/one_print/`). What a native format
cannot reach becomes a field on the record, never a block. For OneProject
that is One Project Status, One Timesheet, OneCRM's One Contract, and the
hours a time and materials invoice bills on One Sales Invoice. A print
format's `modified` moves with every change to it, or a migrate leaves the
site's copy as it was.

**12 Plain words.** Every label is frappe's word where frappe has one
(Assigned To, Parent Task, Depends On), and the rest follows
`docs/WORDING.md` (`tests/guards/test_wording.py`). Every string is in Arabic
and German before it is committed (`tests/guards/test_translations.py`).

### Knows

**13 Documented, and OneAI knows and does.** The README is the manual. Each
screen has its section above `## Under the hood`, written for the people who
use it, and the file map under the hood says what each file does. OneAI
reads a project as its reader sees it on the page, and does what the page
does as a card the reader approves: a project, its status, a milestone,
time, a budget, a member, a contact, a reminder, a template
(`one_project/ai.py`, the `projects` group in `one_ai/groups.py`). Approving
a card runs the page's own code (`one/ai_setup.py`). Nothing is changed
until it is approved.

**14 Intake.** Every mail or file that should make or change the module's
records has a sample in `tests/samples/intake/<module>/`, and the demo has
Intake read it. OneProject's is a scaffolding bill that names the villa.

### Rules

**15 Permissions.** Each screen is walked as each person who uses it, and
the server holds the line, not the screen. On OneProject a project is its
members', the books read every project, totals show to every reader and
documents open only for those who may read them (`members.py`,
`money._figure`).

**16 Legal.** Whatever the module does that the agreements must say is a
clause in its `legal.py`. OneProject has six, and each changes the AI
Addendum or the Privacy Policy by a new revision when it says something new
(`tests/guards/test_legal.py`). Everybody on the demo agrees again.

**17 Clean code.** One layout per module, a file per concern, and lint clean
(`ruff check onedesk/one_project onedesk/one_demo`). A helper said once
(`money.currency` for the company's currency). A comment only where the code
can't say why.

### On top of the points

**Everything follows frappe.** Fields are frappe's controls, a record being
edited acts as a desk form, and every screen updates through
`frappe.realtime` when what's under it changes. OneProject's tabs each
follow the records they show.

**What ERPNext already does.** Every screen checks currency (the party's on
documents, `base_` amounts in figures), the company, drafts and cancelled
and amended documents, ERPNext's own statuses, its mappers, payment terms,
precision, dates, record access and units. On OneProject this found euros
read as dirhams, a draft timesheet counted as cost, cancelled tasks counted
as planned hours, a retention date read as a due date, and a subcontract
booked to the wrong cost type. **Watch for** ERPNext's own checks on save
that a fix written straight to the database skips, such as a task's dates
inside its parent's.

## The gates

Each must pass before a push.

```
python3 -m pytest -q tests                  # fast tests and every guard
bench --site <site> execute onedesk.one_demo.check.run   # every demo check
python3 scripts/overrides.py --check
python3 scripts/atlas.py --check            # the snapshot is the bench's
python3 scripts/docs.py --check
ruff check onedesk/<module> onedesk/one_demo
```

## Learned closing OneTask

OneTask was the second module closed against the standard. It added these
to watch for:

- **A rule on the hooks that the guard doesn't know.** A task's progress was
  its checklist on `before_validate`, but nothing changed it every way until
  it was registered in `tests/guards/test_rules.py`.
- **OneAI that reads but doesn't do.** The page completes a task and moves
  its due date. OneAI does the same as a card (`edit_record` on the Task).
- **A kind the demo only makes in a check.** A repeating task was made and
  taken away in a check, so no screen showed one. The demo keeps one.
- **frappe's own bugs in the record frame.** A record's page carries
  frappe's sidebar, bugs included, such as "Repeats Weekly" without its
  words. Fix them for the form too, and record the override.

## After ready

A ready module stays ready. Any change to it:

- bumps its version with a What's New entry;
- moves the agreements with it when it changes what is done with data;
- updates the Help pages it changes;
- keeps the copy, roles, OneAI and notification guards green.

The guard makes the first one impossible to skip, and the rest are already
guards.
