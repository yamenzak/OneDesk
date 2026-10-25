# Ready for live

A module is ready for live when it passes the fourteen points below, and the
registry (`onedesk/one/ready.py`, checked by `tests/guards/test_ready.py`)
says so. OneMail is the first. From then on every change to a ready module
goes through the same points, so it stays ready.

This sits on top of `docs/PASSOVER.md` and `docs/STANDARD.md`, which stay as
they are: the passover walks each screen, the standard says what a finished
module looks like, and this file says what a module needs before people
outside the company use it.

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

## The mechanisms

### 1. Copy

**Today.** `docs/WORDING.md` has the rules for labels, descriptions,
notifications and screens. `tests/guards/test_wording.py` checks
descriptions (130 characters, two sentences, no first person, no em dash)
and screen text (140 characters, no joined clauses).

**Missing.** A Window UI section with hard limits and a tone, and a guard
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

**Today.** OneMail is about thirty files in `onedesk/one_mail/`, and the
rest are spread out:

- **Desk JS and CSS:** `public/js/onemail_settings.js`, `mail_compose.js`,
  `rule_builder.js`, `record_mail.js`, `public/css/onemail_settings.css` and
  `record_mail.css`.
- **The island:** `frontend/src/mail/` and `frontend/src/islands/onemail.js`.
- **Python elsewhere:** `one/mail_templates.py`, part of `one/ai.py`, and
  `one_demo/mail.py`.
- **Notifications:** `notifications/one_mail/*.md`.
- **Tests:** `tests/test_mail.py`, `tests/test_mail_templates.py`, and the
  `onemail_*` checks in `one_demo/check.py`.

**To build.** Everything moves under `onedesk/one_mail/`, with three
exceptions frappe forces on us:

- Static files are served only from `onedesk/public/`, so they go to
  `public/one_mail/` and nowhere else.
- Fixtures are per app.
- Translations are per app.

Vue source moves to `one_mail/frontend/` with an alias in the islands
build. Notification types are read per module (the `one_notification_types`
hook already takes a list). Demo steps and checks go to `one_mail/demo.py`
and `one_mail/checks.py`, which `one_demo` calls.

A guard fails on any file outside the module that names `one_mail`, other
than the wiring in `hooks.py`.

### 3. Versions and What's New

**Today.** Nothing per module. Frappe's own What's New dialog
(`frappe/utils/change_log.py`) is per app and reads
`<app>/change_log/v1/v1_2_3.md`.

**To build.**

- **Where entries live.** Each module keeps `changelog/` with one Markdown
  file per version, such as `one_mail/changelog/1.4.0.md`. The newest file
  is the version.
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

**Today.** Every module has a `README.md`. Above `## Under the hood` it is
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

**Today.** OneMail has a SettingsDialog (`onemail_settings.js`), opened from
Settings at the foot of its rail and from Workspace Settings › Access. Tabs
show by ability (`frappe.boot.one_mail_may`). No other module has one.

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

**Missing.** Nothing in a module shows what it adds to the agreements.

**To build.**

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

**Today.** The abilities engine (`one/abilities.py`, the `one_abilities`
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
   or test covers every behaviour (`docs/STANDARD.md` point 1).
9. **Notifications.** It tells people what they need, on the right channels,
   only to the right roles (mechanism 8).
10. **Window UI pass.** On the Window, tokens only, frappe-ui and frappe
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

## After ready

A ready module stays ready. Any change to it:

- bumps its version with a What's New entry;
- moves the agreements with it when it changes what is done with data;
- updates the Help pages it changes;
- keeps the copy, roles, OneAI and notification guards green.

The guard makes the first one impossible to skip, and the rest are already
guards.
