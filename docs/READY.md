# Ready for live

A module is ready for live when it passes the points of `docs/STANDARD.md`
held before live, and the registry (`onedesk/one/ready.py`, checked by
`tests/guards/test_ready.py`) says so. OneMail is the first. From then on
every change to a ready module goes through the same points, so it stays
ready.

The points are in `docs/STANDARD.md`, and `docs/PASSOVER.md` is how a screen
is walked against them. This file is what is not a point: the order the
mechanisms were built in and how each works, a module's folder, how a module
is finished and what finished looks like, the gates, and what closing a
module taught.

## The order

The mechanisms are built in this order, because each one leans on the one
before it:

1. **Copy.** Every other mechanism writes words on a screen.
2. **One home per module.** Everything else is a file in that home.
3. **Versions and What's New.**
4. **Docs and Help.**
5. **The module's foot: Settings, the tour, Help, TrustCenter, version.** One settings dialog per
   module, role-aware.
6. **Legal in the module.** What the module adds to the agreements, shown in
   its settings dialog.
7. **Roles that ship.**
8. **Notifications.**
9. **Setup steps.**
10. **Tours.**
11. **OneAI reach.**
12. **The registry and its guard.**
13. **TrustCenter.** The agreements in one place per app, the laws they
    answer, how a change to them reaches people, and the services a
    workspace turns on.
14. **AccessCenter.** Who may do what, in one place per app, read from what
    each module declares.
15. **NotificationCenter.** What each module sends, which channels the
    workspace allows, and what each person chooses, in one place per app.
16. **AICenter.** OneAI rebuilt on models we choose, in code, through
    Cloudflare's gateway, and set up in one place per app: the tier,
    Knowledge, credits, and what OneAI does in each module. Planned in
    `docs/AICENTER.md`.

Then OneMail is taken through the points held before live, and marked ready.

## A module's folder

Every module has the same folder, and nothing else in it is written by hand
in Markdown:

```
onedesk/<module>/
  AGENTS.md            the one file for agents: OneAI and us
  SCRATCHPAD.md        known issues and plans, kept short
  help/
    <page>.md          the wiki, one page per thing people do (HelpCenter)
  updates/
    <version>.md       one per version, the newest is the version (UpdateCenter)
  trust.py             what it adds to the agreements (TrustCenter)
  notifications.py     what it tells people, and on which channels
  access.py            what its roles may do and the grants it gives (AccessCenter)
  setup.py             what the setup wizard may ask
  tour.py              its first-visit tour
  agent.py             its OneAI tools, and NOT_FOR_AI (AICenter)
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
- **`help/`** and **`updates/`** are for the people who use the module: the
  Help dialog's pages, and What's New. Pictures and clips sit beside the page
  or version that shows them.
- **No other `.md` file in a module.** A notification type, today a
  Markdown file in `notifications/<module>/`, becomes a declaration in the
  module's `notifications.py`, as a clause is in `trust.py`.
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
keeps what has no single module: this file, the passover, the wording and
the generated reference. OneInterface is a module like the others, in
`onedesk/one_interface/`.

## The mechanisms

### 1. Copy

**Built.** `docs/WORDING.md` has the rules for labels, descriptions,
notifications and screens, and the `wording` skill is how they are used.
`tests/guards/test_wording.py` checks descriptions (130 characters, two
sentences, no first person, no em dash) and screen text (140 characters, no
joined clauses). A module on its way to ready is held to harder limits by
`tests/guards/test_wording.py`, which reads the `title:`, `label:`,
`description:` and heading strings passed to `__()` in its JS and Vue:

- **Headings** are five words or fewer: tab titles, panel titles, dialog
  titles, section headings and tour steps.
- **A description is one sentence.** It says what the thing is or what it
  does, never how to use the screen.
- **A list of words we never show:** simply, just, easily, please, utilize,
  leverage, seamless, powerful, robust, note that, in order to,
  functionality, "Are you sure", "Something went wrong", and any word for
  our framework.
- **The tone**, from screens we fixed: "Only a Mail Manager or an
  administrator can change this." became "Your role doesn't allow changing
  this."; "Allow Private Mailboxes" as a row of its own became the switch
  beside the title; "Gmail and Outlook require an app password." is kept: it
  says the fact and nothing else.

### 2. One home per module

**Done for OneMail.** Everything of OneMail is in its places
(`onedesk/one/ready.py`):

- **The folder,** `onedesk/one_mail/`. It holds the Python, the doctypes, the
  notification types (`notifications.py`), the OneAI tools (`agent.py`, now
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
ones that read `public/js` or `public/css` read every folder in it: the top of
each holds only the desk's own scripts and styles, each in `ready.SHARED`.

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
  each picture and clip drawn from R2 (Pictures and clips, under 4), each marked New past the version
  the reader last saw, which opening them moves on (a user default per
  module). `frappe.boot.one_versions` carries each module's version and
  whether it is unseen.
- The version sits at the end of the module's foot row (`win.foot_action`
  with `version`), with a dot until seen, beside a Help button.
- What's New (`public/js/module_docs.js`, `onedesk.whats_new.open`) is a
  OneInterface settings dialog whose sidebar is the module's own: its mark,
  a search, and a tree with each fix under the minor it fixes and each
  minor under its major. A row is the version number alone, with its
  title on hover, its kind's icon before it (rocket for a major, sparkles
  for a minor, wrench for a fix) and a dot after it while unseen. The chosen version fills
  the panel with its pictures and a Read More row of buttons for the Help
  pages its `docs:` front matter names. `test_ready.py` fails on a `docs:`
  page that is not a Help page.

**Released at 1.0.0.** A module's first version is the day it is first
marked ready, and everything before that is in git, not in What's New. Its
Help already says everything it does, so 1.0.0 says what the module is and
points at HelpCenter. OneMail was released this way on 2026-10-25, under
this first version of the standard.

**Before production.** One is declared ready for production in the
registry (`ready.PRODUCTION`) once every module in it is ready, and
`test_ready.py` refuses the flag before then. Until that day nobody runs
One for real, so the agreements change freely. A change takes effect the
day it is made: no new revision, no published change (`documents.CHANGES`
stays empty), no thirty days, no switchover, and no old way kept in the
code. Record the documents' new versions in `test_legal.py` and move on.

Versions don't wait for production: a module released at 1.0.0 moves by
the rules below from its next change on.

On the day `PRODUCTION` turns on, `documents.BASELINE` is set to every
document's revision, and from then the rules below apply in full.

**Which number moves.** A version is x.y.z, and the biggest change in it
picks which:

- **Major (x)**: something people already use works differently or is
  gone. They have to learn it again, redo a setting, or lose something: a
  screen, a setting or an ability removed, a flow that now goes another
  way, mail or records moved or reshaped, a role given less than it had.
- **Minor (y)**: something new people can do, and nothing they already do
  changes: a new screen, setting, notification, role or Help page, an
  optional service, or any change to what the module adds to the
  agreements, even if nothing else moved.
- **Fix (z)**: it now does what Help already says it does. Bugs, words,
  layout, speed and translations. Nothing new to learn and no new setting.

When torn between two, take the bigger one. `test_ready.py` holds the one
rule a machine can check: a fix never changes what the module adds to the
agreements.

A day's work in a module is one version. `scripts/version.py` refuses a
second one the same day (a bigger kind renumbers today's instead), and
`scripts/close.py` keeps today's version on the module's fingerprint after
it is committed, so a later change that day is added to its words. On 6
November 2026 one pass wrote seven OneInventory versions in a day; they
were folded into 2.1.0.

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
screen it talks about beside it in `docs/<page>/`.
`test_ready.py` fails on a page not listed, a page that names code (what a
claim rests on goes in `AGENTS.md`, under Where Help's claims are kept), a
heading over five words, a picture that isn't there, and a link to a page
Help doesn't list.

**Pictures and clips.** A page or a version names a picture (`.png`,
`.jpg`, `.webp`) or a clip (`.gif`, nine seconds at most, made with
`scripts/clip.mjs`) that sits beside it in the repository; the docs and
changelog skills say when one earns its place. The page draws it from R2
(`one/media.py`): the public `one-docs` bucket, which holds nothing else and
which every environment shares, at `media.4dl.app/docs/<hash of the
file>.<kind>`, so a picture has one address on dev and in production and a
changed one a new address. Until R2 has it, the page falls back to the
workspace, which serves it from the repository. An admin site sends what R2
does not have whenever it migrates (`one_admin/media.py`), so on dev
`git pull` and `bench --site all migrate` publish a new picture; Set Up
Cloudflare makes the bucket, lets the storage token write it and puts it on
`media.<zone>` (`docs_media`). `tests/guards/test_docs_media.py` fails on a
picture that isn't there, one nothing shows, one over 1 MB, a clip over 4 MB
or nine seconds, and a kind a browser might not show.

**Read on.** A version names the pages it changed (`docs:`), and What's
New offers them under it as Read More; each of those pages ends with
Changed In, the versions that named it, each opening What's New on that
version. So writing `docs:` is what links both ways.

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
`win.module_foot({ module, settings })`, `interfaceModuleFoot` in an island:
a row of icons: Settings (the cog), the tour of the area on screen and Help,
then the version at the row's end (mechanism 18 for where every other
centre opens). A centre's Help, Enlarge and Close, and Back a page deep,
are OneInterface's dialog kit's (`one_interface/AGENTS.md`, Dialogs); a
centre asks for Help with `dialog.one_help` and draws no control of its
own. `test_ready.py` fails on a
module that draws its own settings dialog or its own foot. OneMail is on
both.

**A module with no window.** A module whose only screen is a center other
modules open, such as TrustCenter, has no rail, so no foot and
no settings dialog of its own. It says so in one sentence, as `windowless`
in its registry entry, and the guard skips this point for it; every other
point still holds. Its tour starts from the center the first time it
opens, and a tour of a dialog keeps the dialog above driver's overlay and
outlines each step where it is (`onedesk.tour.run`). Its Help is listed in
HelpCenter beside every other module's.

**An engine module.** A module that is the frame the others are drawn in,
rather than an app somebody is given, keeps no records of its own and has
no roles to ship. OneInterface is the one there is. It says so in one
sentence, as `engine` in its registry entry, writes no `access.py`, and
the roles guard skips it; it still declares what it sends (nothing), what
setting it up takes (nothing), what OneAI may do (nothing of its own) and a
tour, of the window itself, which waits for Help to offer it
(`docs/BACKLOG.md`).

### 6. Legal in the module

**Today.** Each module declares what it adds to the agreements in its own
`trust.py`: `clause()` for a paragraph of a document, `subprocessor()` for a
company it sends data to (OneMail names Cloudflare, Gravatar and Google).
`trust_center/assemble.py` puts them into the eight documents, and those are
what the Agreements page shows, what is printed, and what people are asked
to agree to. An agreement's version is `revision.hash`. Any change to a
clause moves the hash, and `tests/guards/test_legal.py` fails until we
either bump the revision (people agree again) or record the new hash (a
typo). A host the code calls that no `subprocessor()` declares also fails
it.

**Built.** Every module's ControlCenter ends with **Legal**
(`onedesk.module_settings.legal`, added by `module_settings.open`, so a
module can't leave it out). It reads `trust_center.reading.of_module(module)`,
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

### 7. Roles that ship

**Built.** A module's roles come from its folder alone. `<module>/access.py`,
named by the `one_abilities` hook, declares its abilities, the role everyone
holds (EVERYONE), or for a space over ERPNext the role every user of it holds
(USER, given on People), and DEFAULTS: every role it ships and what each
starts with.
`rights.settle`, on migrate, makes a role named there if it isn't there
and writes its defaults once, so a workspace's own changes survive an update;
the Role fixture is gone. The module's Help shows the same defaults: `{roles}`
on a page becomes `rights.defaults_table`, in English as Help is, so the
page can't say other than what ships. Overrides are one idea: `rights.grant`
gives one person more on one record than their role says, as a share frappe
answers, and nothing else in a module writes a share. `test_ready.py` fails on
a ready module without access.py or its hook, with defaults naming an
ability it doesn't declare, without `{roles}` in its Help, with a Role fixture,
or writing a share itself.

### 8. Notifications

**Built.** A ready module's types live in its own `notifications.py`, and
each names its `channels` (bell, email, push: `True`, or a sentence saying
why not) and its `sender` (`system`, One's mark; `workspace`, the
workspace's name and colour), in place of the `email`, `push` and `from_one`
flags, which `notifications/layout.py` `settle` derives for the rest of One.
How each channel shows one is in `layout.py` once: the bell's line
(`BELL_LINE`), the framed mail, and a push's title and body
(`PUSH_TITLE`, `PUSH_BODY`, cut on a whole word by `layout.cut`, which
`one/push.py` now uses). Help doesn't list what a module sends: people
see that in NotificationCenter, where they choose it. `test_ready.py`
fails on a ready module without `notifications.py`, a type missing a
channel or its sender, a channel off without a reason, a leftover flag, or
a subject past the bell's line. The README in
`onedesk/notifications/` has the table. OneMail's two about storage and
credits are from One; the rest from the workspace.

### 9. Setup steps

**Built.** A module declares its steps in its own `setup.py` as STEPS: a
key, a title, what it is for, the ability it needs, the module's settings
tab that does it, and, for a step the wizard asks, its fields, whether it
can be left for later and what saves it; `done` says how to tell it's done
where something can (OneMail's domains: an Email Domain exists), else it is
done once saved or marked done (a workspace default). `one/setup_steps.py`
is the one engine: `for_wizard`, built with the boot while setup is
unfinished, gives the wizard a slide per step with fields, named for the
module and step, after ours (`public/js/setup_wizard.js`); `apply`, a
wizard task, saves each step that was given and leaves an empty one for
later; `for_boot` gives each reader the steps their role can do. Every
step is reached in **SetupCenter** (`one/setup_center.py`), an app per tab
with its steps done and waiting: a step with fields is the wizard's own
form (`fields`, one declaration for both), saved through the step's `save`;
one without has Set Up (its tab) and Mark as Done (`finish`). A
ControlCenter starts with a Getting Started row that opens SetupCenter on
the module while a step waits, and turning an app on in Apps lands there. OneMail's are the company's
domain, private mailboxes, and mail templates (no fields: a to-do only).
`test_ready.py` fails on a ready module without `setup.py`, a step without
its key, title, what it's for, ability or tab, a tab its settings don't
have, or fields nothing saves.

### 10. Tours

**Built.** A module declares its tours in its own `tour.py` as `TOURS`, one
for each area of its screen, because a module like OneProject has several:
a key, the mark `at` that says the area is on screen, and steps, each the
`data-tour` mark it points at, the side its popover opens on, a heading of
five words or fewer and one sentence. Marks are attributes, never classes;
the window's own (`window-nav`, `window-search`, `window-foot`,
`window-tour`) serve every module. `one/tours.py` gives the tours in the
reader's language (`tour`), the areas a reader hasn't toured, as
`Module:key`, in the boot (`unseen`), and remembers an area's tour taken or
closed as a user default (`seen`). The runner in `module_docs.js` puts them
on `frappe.Driver`, taking the first tour whose `at` is on screen, from the
play button in the module's foot, which says so when the screen has no
tour. A tour never starts by itself.
An island's parts sit in shadow roots, so the runner looks for a mark in
each, lends driver's highlight rules to the root it is in, and lifts the
layers outside it that driver's own walk stops short of. `test_ready.py`
fails on a ready module without `TOURS`, a tour or step whose mark is
nowhere in its screens or the window's, two tours with one key, a heading
over five words, or text over one sentence. OneMail has one area, the
mailbox, and six steps: mailboxes, New Email, the list, the reading pane,
search, and the foot's tour button.

**Why not Form Tour.** It is kept per form or page route in the database
and `user.onboarding_status`, and its steps are found with
`document.querySelector`, which can't see into an island. Steps as code
beside the module are translated, guarded and versioned like the rest of it.

### 11. OneAI reach

**Built.** A call of a module's that changes something is one whitelisted for
POST alone; every such call is in the module's `agent.py`, either in `REACH`,
naming the OneAI tool whose card does it, or in `NOT_FOR_AI` with the reason
in one sentence. A card is a Setup proposal; approving it runs the module's
`approved`, which makes the page's own call as whoever pressed Approve, so a
card is refused exactly where the page would refuse. `test_ready.py` fails on
a changing call in neither, in both, or named but gone; a tool its `agent.py`
doesn't have or OneAI isn't given; an approval that never makes the call; or
a reason longer than a sentence.

OneMail's 36: 26 reached by eleven tools (`sort_conversations`,
`change_folder`, `file_conversation`, `suggest_away`, `suggest_mail_rule`,
`change_mail_rule`, `sign_mailbox`, `share_mailbox`, `suggest_mail_policy`,
`company_domain`, `default_mail_template`) and two reads (`mail_rules`,
`workspace_mail`); ten not, among them the three that take a password, the
OneAI tab's own settings, and the Worker's call. The rule card now saves
through `rules.save_rule`, so a rule asked for on an issued address waits
for a Mail Manager as the page's does; it had been inserted straight.

### 12. The registry

**Built.** The points are one list, `onedesk/one/standard.py`, written up in
`docs/STANDARD.md`. Each point says whether a module is held to it before it
is marked ready, and, where no rule can settle it, what a person looks at.
`onedesk/one/ready.py` reads it: `POINTS` are the points held before live,
`HAND` the five with a look (copy, the demo, notifications, the look of each
screen, legal). The rules holding each point are `tests/guards/registry.py`'s
`GUARDS`, each naming its point, listed in `docs/STANDARD-RULES.md`.

A module's `checked`, in its manifest, records each look: the day, the
commit it was taken at, and who looked (`scripts/close.py --looked`).
`docs/REGISTRY.md` is generated from it (`scripts/docs.py`): per module, its
version, whether it is ready, and per point, how many rules hold it and its
last look.

`tests/guards/test_registry.py` fails when `docs/STANDARD.md` and the list
disagree, a point has neither a rule nor a look, or a rule isn't a test.
`tests/guards/test_ready.py` fails, for a module marked `ready`, on a hand
point nobody has looked at, a look without who or with a commit git doesn't
have, or a major or minor version added after the commit a look was taken
at, which makes it stale. A fix leaves a look standing.

### 13. TrustCenter

**Built.** All six parts.

- **The center.** `public/js/trust_center/trust_center.js`, on the docs dialog
  (`onedesk.CENTERS.trust`), reads `trust_center.reading.trust`, in two
  sizes. **A module's part**, from the shield in its foot: **{Module} and
  Your Data** (its optional services and who it sends data to), its own
  paragraphs of each agreement it writes into with where the reader and the
  workspace stand on it, and the changes to those. **The whole**, from the
  shield in the bottom bar, from Read in Full, and from `/desk/legal`: every **Agreement** in full,
  **Optional Services**, **Companies** (struck through where unused),
  **Your Data** and **Changes**. The Agreements island and the Legal tab
  are gone.
- **The laws.** `trust_center/laws.py`; One's own clauses name their duties in
  `trust.py`'s `MEETS`; three clauses were added where no clause met one
  (privacy by default, the record of processing, switching provider), and
  Saudi Arabia's law named in rights, complaints and transfers.
- **Changes.** `documents.CHANGES` and `BASELINE`; `gate.effective`; only a
  first agreement stops anybody; **Agreements Changed** to administrators
  by mail and **Policies Changed** to everybody, each with the day. The
  first round of published changes was withdrawn the same day: before
  production the agreements change freely, so it took effect at once.
- **Optional services.** `service()`, `trust_center/services.py` (`call`,
  `switch`, the wizard's slide), Gravatar and logos off by default, the
  demo's owner turning both on.
- **Legal copy.** docs/WORDING.md, The agreements; `test_legal.py` holds
  every clause to no legalese, and a ready module's to 30 words a sentence.
  OneMail's are rewritten to it.
- **The registry.** `ready.HAND["legal"]`.

One correction to the rule below: a new subprocessor One can't work without
is still a core change, by notice with the right to object, as the Data
Processing Addendum allows. What needs an administrator's yes is a new
company for something One can work without.

**Before production none of this applies** (mechanism 3, Before
production): a change to the agreements takes effect the day it is made,
and the two paragraphs below start on the day One is declared ready for
production.

**Core changes wait for their day.** A notice is only worth something if
nothing changes before the day it gives. So a change One can't work
without is a **switchover** (`registry.switchover` in the module's
`trust.py`): it names the published change in `documents.CHANGES`, whose
day is at least thirty days after it was published, and the code runs the
old way until that day and the new way from it (`switchovers.when(key,
new, old)`). A new company's uses say `starts=` the switchover, and
TrustCenter shows them **From** that day. `test_legal.py` fails on a
company One can't work without that the agreements in effect don't name
(`documents.IN_EFFECT`) unless it comes in that way, and on a file that
reaches a switchover's hosts other than through `switchovers.when`.

**Cleaning up.** Every switchover is listed under **Switchovers** on the
Registry page, with its day and the day it is due to be cleaned up, thirty
days later (`switchovers.CLEAN_DAYS`). From then the guard fails until the
old way and the switchover are removed and its companies are added to
`documents.IN_EFFECT`. Nothing waits on anybody's yes: people are told,
may object, and keep using One or leave.

**As designed, in six parts.**

**1. One center.** TrustCenter is a center like HelpCenter and ControlCenter
(`onedesk.CENTERS`, `trust: "Trust"`), drawn by `onedesk.module_docs`'s
dialog. It replaces both the Legal tab and the Agreements page, which
becomes TrustCenter opened on the workspace. Opened from a module's foot
(a shield beside the question mark), it opens on that module, and its
sidebar is:

- **This app**: what the module adds to each agreement, the companies it
  sends data to, and its optional services with their switches;
- **Agreements**: each one, its version, when it takes effect, who agreed
  and when, every earlier version, and print;
- **Companies**: every company, what it gets, where, under which
  safeguard, and which app sends it. One a workspace doesn't use is struck
  through, marked **Not used by this workspace**;
- **Your data**: what is kept and for how long, the full export, and how to
  leave (the Data Act, below);
- **Changes**: what is coming, from when, and what changed before.

Everybody reads it. Switches and agreeing are for workspace administrators
(`trust_center/access.py`).

**2. The laws.** `trust_center/laws.py` lists each law One answers and the
duties it puts on us, and every `clause()` and `subprocessor()` names the
duties it meets (`meets=("gdpr.28", …)`). `test_legal.py` fails on a duty no
clause meets. To start with:

- **GDPR and UK GDPR**: the processor terms (Art. 28), what people are told
  (Art. 13 and 14), privacy by default (Art. 25), security (Art. 32), breach
  notice within 72 hours (Art. 33), the record of processing (Art. 30),
  transfers out of Europe under the Standard Contractual Clauses and the UK
  addendum (Chapter V);
- **ePrivacy**: nothing kept on a device but what One needs to run, without
  consent;
- **The EU AI Act**: people are told when they talk to OneAI, and what it
  makes is marked as made by it (Art. 50; the OneAI badge already does);
- **The EU Data Act**: a customer may switch to another provider and take
  everything with them, in a format another system reads, at no charge (from
  12 January 2027), on notice no longer than two months;
- **The CCPA and CPRA**: the service provider terms;
- **The UAE's PDPL and Saudi Arabia's PDPL**, for workspaces in the Gulf.

**3. How a change reaches people.** What large SaaS products do (Google
Workspace, Microsoft 365, Slack), and what we do from now on. There are three
kinds of change, and one rule decides between the last two: **anything that
sends data somewhere it didn't go, or uses it for something it wasn't used
for, needs an administrator's yes. Everything else is notice.**

- **A clarification** moves the hash, not the revision, and asks nobody (as
  today).
- **A core change** bumps the revision and carries `effective:`, at least 30
  days out. Administrators are told in the bell and by mail the day it ships;
  TrustCenter shows it under Changes; the old version holds until the day. A
  new subprocessor the product can't run without is a core change: the
  administrator may object, which is the Data Processing Addendum's right,
  and leaving with a full export is the remedy. Nothing stops working and
  nobody is stopped at sign-in: the sign-in gate stays for a workspace's
  first agreement, and for a person's first sign-in.
- **An optional service** is off until an administrator agrees to it (below).
  A change that gives an accepted service somewhere new to send data turns it
  off until they agree again; any other change to it is notice.

People who use a workspace are told, never asked: the workspace decides
what happens to its people's data, and a yes from an employee to their
employer isn't free consent under the GDPR. A change to the Privacy Policy
or the Acceptable Use Policy is notice in the bell, with the day it takes
effect.

A new workspace agrees to the latest core agreements when it signs up, and
is asked about each optional service in the setup wizard.

From the day a module is ready, a change to it that sends data somewhere new
ships as an optional service. The version that adds it says so, and
`scripts/version.py` writes `terms: notice` or `terms: service <key>` into
its front matter, so the guard can hold the words to it.

**4. Optional services.** A module declares one in its `trust.py` with
`service()`: a key, a title, what it is for, what it sends and to whom (its
`subprocessor()`s), the clauses that hold only while it is on, and
`default=False`. The code that calls out goes through
`trust_center.services.call(key, …)`, which refuses while it is off, and
`test_legal.py`'s host guard accepts that host only there. Turning one on is
an acceptance of its own terms, recorded like any other (`Legal
Acceptance`); turning it off stops the calls and strikes its subprocessors
through. They are off by default everywhere, which is what privacy by
default asks. OneMail's first two:

- **Pictures from Gravatar**: a hash of an address, to Automattic. Off: a
  person's initials.
- **Logos from Google**: an organisation's domain, to Google. Off: no logo.

The setup wizard asks about each one with its own slide (mechanism 9), and
an administrator agrees there or later in TrustCenter.

**5. Legal copy.** Agreements are written precise and plain, which is what
the GDPR asks of them (Art. 12): `we` is Four Degree Labs, `you` is the
organisation, a defined term is capitalised and defined once, one duty to a
sentence, a number where there is one (72 hours, 30 days), and nothing
promised that isn't built. The rules go in `docs/WORDING.md` beside the copy
rules, and `test_wording.py` reads `trust.py` too. Every module's `trust.py`
is rewritten to them as it goes through the points held before live.

**6. The registry.** Legal (point 19 of `docs/STANDARD.md`) is held by the
guards above, and, since no guard can read whether a clause is true, by a
look (`ready.HAND["legal"]`): what the module does with data, read against
what its clauses say.

**Still ours to confirm.** This is our own drafting. A lawyer reads the
assembled agreements before an EU customer signs, and the laws list is
theirs to complete.

### 14. AccessCenter

**Built.** `public/js/one/access_center.js` and `one/access_center.py`, on the
settings dialog (`onedesk.CENTERS.access`), for workspace administrators.
A module's part has three tabs: **Roles**, the matrix (`role_matrix.js`,
with Show Roles and New Role); **People**, everybody's role in the module,
changed in place as People changes it (`put`, which takes somebody off a
profile that says otherwise); and **On One Record**, everybody given more
than their role on one record (`records`, read from the module's shares),
with Edit and Remove through `rights.grant` (`give`). A record is named
by the field its `access.py` names (`TITLE`, OneMail's `email_id`).
A module everybody uses (`EVERYONE`: One, OneAI, AccountCenter, TrustCenter) is
not one of People's apps, so its People tab offers User and Manager only,
its User role being everybody's (`people.with_roles`), and it has no On One
Record unless it gives something there (`SHARED`, `access_center.shared`).

It is found, not drawn: the boot names the modules with abilities
(`one_centers.access`), and ControlCenter ends every such module's sidebar
with **Roles and Access**, which opens AccessCenter on it
(`onedesk.module_settings.centers`). The whole, every module with
abilities, opens from One's rail (mechanism 18); a role of such a module in Workspace Settings
› Access opens it too (`Settings.access`). OneMail's Roles tab and
`Settings.ROLES_IN` are gone. Profiles, groups, the record-type levels of
apps not yet ready, and frappe's per-doctype permissions stay where they
were. `test_ready.py` fails on a ready module whose screens draw the role
matrix, and the demo checks `access_center_finds_and_sets_roles`.

### 15. NotificationCenter

**Built.** `public/js/one/notification_center.js` and
`one/notification_center.py`, on the settings dialog
(`onedesk.CENTERS.notifications`), for everybody. A module's part has
**Yours**, each type the reader can get from it with an Email and a Push
switch, saved as it changes (`choose`, which carries a type's followers
with it), and a switch that can't move saying why; and, for
administrators, **Workspace**: each type it sends with Send, then whether
email and push are allowed (`set_type`), and a pencil to its words in
Workspace Settings. Whether a new person starts with a channel on is the
module's to say (`email_default`, `push_default` in its declaration), so
nobody sets it here; a workspace rule starts everybody on what it allows.

It is found, not drawn: the boot names the modules whose types the reader
gets, or every module with types for an administrator
(`one_centers.notifications`), and ControlCenter ends their sidebars with
**Notifications**. The whole opens from the bell's gear and One's rail (mechanism 18):
**Everything** (notifications and their email on or off, and push in this
browser), then one row per module under **Apps**, with **Yours** and, for
an administrator, **Workspace** in its head, **Other** for the workspace's
rules, and **Words and Rules**.
Workspace Settings › Notification Types keeps the words and the rules.
`test_ready.py` fails on a ready module whose screens draw notification
choices, and the demo checks
`notification_center_sets_yours_and_the_workspace`.

### 16. AICenter

**Built.** `public/js/one_ai/ai_center.js` and `one_ai/center.py`, on the settings
dialog (`onedesk.CENTERS.ai`). For everybody, **Yours**: what OneAI
remembers about the reader. For administrators, **OneAI** (on or off, the
tier with what an answer costs at each, credits left), **Knowledge**, each
module's part, **Summaries** and **Usage**. A module's part is found from
`JOBS` in its `agent.py`, each a field on one of its singles, drawn with the
field's own label and description; a module whose OneAI settings are per
record (OneMail's mailboxes) is listed and opens that record's tab.

The boot names the modules with a part for administrators while OneAI is
on (`one_centers.ai`), and ControlCenter ends their sidebars with **OneAI**.
The whole opens from One's rail (mechanism 18), and from the end of
OneAI's own rail.
`test_ready.py` fails on a screen that draws OneAI's settings and on code
outside OneAI that reaches the gateway. The plan and what is still to come
are in `docs/AICENTER.md`.

### 17. AccountCenter

**Built.** AccountCenter (`account_center/`), on the settings dialog
(`onedesk.CENTERS.account`): for everybody, **Yours** (Profile, Sign-in);
for administrators, **Workspace** (People, Devices, Plan and Credits with
closing the workspace at its foot, Domains). It opens from the avatar, the
rail and `/desk/one?center=account&at=...`. Each section is a
`CenterSection` (`public/js/center_section.js`), which every centre with a
form to save now draws on. It is the first step of cutting One down to
the shell, Home and a few screens of its own; the rest is in `docs/ONE.md`.

### 18. The centres, and where each opens

**Built.** There are nine: **AccountCenter**, **ControlCenter**,
**NotificationCenter**, **AccessCenter**, **TrustCenter**, **AICenter**,
**ShortcutCenter**, **HelpCenter** and **UpdateCenter** (`onedesk.CENTERS`). Every one of them is
One's, and every module but AccountCenter adds its part to them from its own
files rather than drawing one: its settings and Lists (ControlCenter), its
`access.py` (AccessCenter), `notifications.py` (NotificationCenter),
`trust.py` (TrustCenter), `agent.py` (AICenter), `shortcuts.py`
(ShortcutCenter), `docs/` (HelpCenter) and
`updates/` (UpdateCenter). AccountCenter is One's alone.

**Two ways in, and no third.**

- **The whole, from One's rail.** One's rail ends with **Centers**, a row
  for each, opening it over One for every module
  (`/desk/one?center=...`, `onedesk.centers.open`). A full view groups by
  module, and One's own part is a group called One like any other. A row a
  reader can't open is not on their rail: AccessCenter is an
  administrator's, AICenter goes when OneAI is off (`apps.trim`).
- **A module's part, from the module.** Its foot has Settings, the tour,
  Help (HelpCenter on the module) and the version (UpdateCenter on it).
  ControlCenter, its Settings, ends with a row per centre it has a part in,
  each opening that centre on the module: Roles and Access, Notifications,
  OneAI, Keyboard Shortcuts, and Your Data, which every module has
  (`onedesk.module_settings.centers`).

Nothing else opens a centre: the frame's bars carry what is used every day
(search, the bell, OneAI, Check In, timers) and no centre, and AccountCenter
holds its own tabs only.

**One owner, one dialog deep.** A thing lives in one centre, the one of the
module it belongs to, and anywhere else shows that centre's own control or
a row that opens it, never a copy: Pictures shows Gravatar's switch, and
the agreement it makes is TrustCenter's (`onedesk.trust.switch`). A centre
opened from a centre takes its place (`opens`), so no dialog is ever over
another. Each centre's head has Help (mechanism 5).

`test_ready.py` fails when One's rail lacks a centre, and when a module's
Settings leaves one out.

### 19. ShortcutCenter

**Built.** Every module declares its keys in its own `shortcuts.py`
(`SHORTCUTS`: a key, a label, where it works, the keys it ships with, and
`frappe` when it takes over a key frappe had). One collects them
(`one/shortcut_center.py`) into boot, and the engine
(`public/js/one/shortcuts.js`) runs each in the view it belongs to:
`anywhere`, `lists`, `record`, `calendar`, or a module's own page by name.
A shortcut made for the view in front of the reader wins over one that works
anywhere. The code that does a shortcut says so by its id
(`onedesk.shortcuts.does("one_mail.next", fn)`, or `shortcut()` from the kit
on an island), so a screen registers what it does while it is open.

A key is its place on the keyboard (`event.code`), with the modifiers in the
order mod, alt, shift: `mod+KeyK`, `shift+Slash`, `KeyJ`, so it stays on the
same key in any layout. A mouse's side buttons are keys too. frappe's own
keys are folded in: the ones a declaration names stop being frappe's, and
frappe's list of shortcuts opens ShortcutCenter. Letters alone and Alt+Shift
are ours; Alt and a letter stays frappe's, which clicks the button whose
letter is underlined.

ShortcutCenter draws a keyboard and a mouse, lights the keys a row uses, and
listens when a row's Change is clicked: press the keys, or click them on the
picture. A key another shortcut uses where this one works asks first. What a
reader moves is theirs alone, kept as their default `one_shortcuts`; keys
the browser keeps are refused (`RESERVED`).

## How a module is finished

OneProject was the first module finished against every point of the
standard, closed on 2026-10-09, and your word was "OneProject will be the
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
   with a table of all twenty points of `docs/STANDARD.md`, saying what was
   looked at, even where nothing was found. A point left out of the table is
   a point not checked.
4. **Fix, then look again.** Fix every finding, see it in the browser, run the
   gates, commit and push, and show a screenshot.
5. **Revisit.** OneProject's first three screens were walked before the rule
   that every point is written down. They were walked again against the
   points they had skipped, and that found as much as the first walk. A
   module is not finished until every screen has every point in its table.
6. **Close it.** Mark the module closed in `docs/PASSOVER-LOG.md`, and write
   what stays open in the module's `SCRATCHPAD.md`.

## What finished looks like

What each point of `docs/STANDARD.md` looked like in OneProject, the first
module finished against every point. The numbers are the standard's.

### Works

**1 Demo and tests.** OneProject has a fixed price villa with sub-projects
and a subcontract, a curtain wall tower counted by attendance on site, a time
and materials showroom billed in euros, two retainers, an internal project, a
completed one and a cancelled one. Its checks run as the people who would do
the work, with `bench … one_demo.check.run --kwargs "{'only': 'oneproject_'}"`,
and each screen's walk added one, such as
`oneproject_its_tasks_time_and_money_keep_their_rules`. The demo lied more
than once: retention paid in full, the workshop's time on the handover tasks,
a Berlin customer in Business Bay. The product was right each time.

**2 Rules on the server.** OneProject keeps these on its hooks:

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

**3 Hand-offs.** The document a project hands on says the project at the
top, by name, opening its page (`one_project/heads.py`). The last screen of
the walk is from the other side of each hand-off, as the person who works
there.

**4 What ERPNext already does.** On OneProject this found euros read as
dirhams, a draft timesheet counted as cost, cancelled tasks counted as
planned hours, a retention date read as a due date, and a subcontract booked
to the wrong cost type.

### Stays desk

**6 Tier declared.** OneProject had two pages of their own (Project and
Project Template), heads on the documents it hands on, Project's List,
Report, Kanban, Calendar, Gantt, Tree, Image and Dashboard declared, and
Task's List, Gantt and Kanban. In November 2026 Item, Project and Project
Template went back to their forms, with a head and parts in their tabs.

**8 Nothing lost, and extensible.** OneProject had a place for the page and
one for each tab (Overview, Tasks, Time, Money, Invoices, Suppliers, Team,
Files, Activity), and one each for the Projects list, a template and
Workload.

**10 Overrides recorded.** OneProject has 45 rows.

### Speaks

**11 Notifications.** OneProject has sixteen, from Added to Project to Bill
Due, each listed with who gets it.

**12 Printed.** For OneProject: One Project Status, One Timesheet, OneCRM's
One Contract, and the hours a time and materials invoice bills on One Sales
Invoice.

**13 Plain words.** Every label is frappe's word where frappe has one
(Assigned To, Parent Task, Depends On), and every string is in Arabic and
German before it is committed.

### Knows

**16 OneAI knows and does.** OneAI reads a project as its reader sees it on
the page, and does what the page does as a card: a project, its status, a
milestone, time, a budget, a member, a contact, a reminder, a template
(`one_project/agent.py`, the `projects` group in `one_ai/groups.py`). Approving
a card runs the page's own code (`one_studio/ai_setup.py`).

**17 Intake.** OneProject's sample is a scaffolding bill that names the
villa.

### Rules

**18 Permissions and roles.** On OneProject a project is its members', the
books read every project, totals show to every reader and documents open
only for those who may read them (`members.py`, `money._figure`).

**19 Legal.** OneProject has six clauses, and each changes the AI Addendum
or the Privacy Policy by a new revision when it says something new.
Everybody on the demo agrees again.

**20 One home, clean code.** `ruff check onedesk/one_project
onedesk/one_demo` is clean, and a helper is said once (`money.currency` for
the company's currency).

## The gates

Each must pass before a push.

```
python3 scripts/quick.py --all              # every test and guard, in parallel
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

## Learned registering OneDisplay

OneDisplay was the first module whose main screen is not the desk but a TV,
a guest page any browser opens. It added these to watch for:

- **A guest page is still a screen.** The player's colours and dates fell
  under the same guards as the desk's. A TV's browser is too old to format a
  date, so the server sends it in words, and the page's colours live in its
  own stylesheet as variables.
- **An address the workspace types is not a subprocessor.** A news feed is
  read from whatever address a manager gives, so it is no optional service
  and names no company; what it may reach is the public internet only, which
  the code checks rather than the agreements.
- **Notifications are written in the background.** A check reads what
  `tell.py` hands `notify`, not the bell, or it races the worker.

## After ready

A ready module stays ready. Any change to it:

- bumps its version with a What's New entry;
- moves the agreements with it when it changes what is done with data;
- updates the Help pages it changes;
- keeps the copy, roles, OneAI and notification guards green.

The guard makes the first one impossible to skip, and the rest are already
guards.
