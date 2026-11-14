# One

One is the workspace itself: the frame every app sits in (the rail, the two
bars, the dock), Home, the Address Book, Announcements and the Recycle
Bin, and the centres that hold the workspace's settings
(ControlCenter: Company, Branding, Region and Formats, Sign-in, Sharing), who may do what (AccessCenter, with the Audit
Log) and how people are told (NotificationCenter). docs/ONE.md is how it was
cut down to that, and docs/STANDARD.md what it is held to.

Its Help pages, help/ beside this file, are what people read and what OneAI
answers "how do I…" from. This file is for the people who build One. Files
in this folder that are not One's own (the engines every module uses, and
privacy on its way to its own module) are named, with why, in
ready.SHARED. The portal is OnePortal's (one_portal/AGENTS.md).

## Connections

- **To OneMail**: One's frame and rail; ControlCenter, which OneMail's settings
  are drawn in; AccessCenter and NotificationCenter, which find and draw what
  OneMail declares of its roles and notifications.
- **From AccountCenter**: the dialog opened from the avatar and One's
  Centers, holds each person's profile and sign-in and the workspace's
  people, devices, plan and domains.
- **From TrustCenter**: TrustCenter holds the agreements and Your Data, whose
  Requests an administrator answers.
- **From OneAI**: the panel on every page; AICenter is a row of One's
  Centers.
- **From OneHR**: Home lists the leave and expense claims waiting for the
  reader's approval.
- **To OneStudio**: printing, numbering, approvals and automations, which
  were One's Setup and Automation, are OneStudio's, and so is making
  dashboards, which were One's Dashboards and are now on each app's rail.

## Under the hood

**The setup job** (`setup_job.py`, `setup_answers.py`; P4.5 of
docs/run/RUN.md). One entry point, `setup_job.run(answers)`, takes a plain
dict, the shape the wizard in OneAdmin sends and the Account Request keeps:

    {
        "owner": {"email", "first_name", "last_name", "password", "invite"},
        "language": "en", "time_zone": "Asia/Dubai", "field": "contracting", "theme": "Light",
        "companies": [{"name", "country", "currency", "abbr", "chart", "year_starts", "parent"}],
        "working_day": {"starts": "08:00", "ends": "17:00", "days_off": ["Sunday"]},
        "apps": {"one_crm": False},
        "steps": {"one_mail": {"domains": {"domain": "example.com"}}},
        "people": [{"email", "first_name", "last_name", "levels": {"one_book": "Manager"}, "admin"}],
    }

Only the owner, the language, the time zone and one company with its name
and country are needed; an unknown key at any level is refused, and every
problem is named in one `Invalid`. Apps, steps and levels are named by
folder. The first company is the one frappe's wizard makes and the System
Settings' country; a currency not said is its country's; `chart` is
"Standard" (left empty, as erpnext fills it) or "Standard with Numbers",
never a country's own (docs/ACCOUNTS.md). `year_starts` is MM-DD, the first
of January when not said. `parent` names another company in the answers:
once every company is made, `companies.join` puts each in its parent's group
and makes the parent a group company, written to erpnext's company tree
rather than saved through the form, so each keeps its own chart.

The steps, in `ORDER`: `settings` (language, time zone, country, currency,
and the country's date, time and number formats, set one by one, first,
because frappe's wizard takes them back from System Settings when its own
part counted as done on an earlier try), `wizard` (frappe's own
`setup_complete`, which runs erpnext's, hrms's and One's stages; never given
a user, so nobody gets System Manager), `owner` (account_center/owner.make:
Desk User and Workspace Administrator, named, invited unless a password is
given), `companies` (`setup_job.company`, which AccountCenter's Companies
calls too; then `companies.ready` gives the company its financial year,
holiday list, leave and payroll periods, salary component accounts and
letter head, so it pays payroll and invoices, the days off its country's
when the answers have no working day), `apps` (apps.switch, the Apps screen's own), `steps` (each
app's `setup.py` STEPS through setup_steps.save, a step done already left)
and `people` (AccountCenter's invite, as the owner; one refused, as for
seats, is logged and left for People). Which are done is the
`one_setup_job` default; a failure is written there with its reason, and
the next run starts at the step that failed.

A new site runs it from its build: OneAdmin's `set_up` step, between
`push_config` and `invite_owner`, posts `setup_job.wake` (guest, rate
limited, takes nothing but `start`), and the site enqueues `from_admin`,
which refreshes the account and asks `proxy.setup_answers` with its own
token. OneAdmin hands over the answers typed into its wizard
(one_admin/wizard.py), kept on the Account Request, with the workspace's
owner as the owner (one_admin/answers.py). A signup from before the wizard
is set up from the Tenant and Account Request: the workspace's name as the
company, the country said or the one its time zone is in alone, English. A
signup with no country to tell is left to frappe's wizard on the site.

**Pictures** (`avatars.py`, One's settings › Pictures). The tab also switches
Gravatar and Google's logos through `onedesk.trust.switch`, TrustCenter's own
agreement, so a service is agreed to in one way wherever it is turned on; a
style is picked from the record type's avatar (`avatars.gallery`, `pick`) and
saved as it is picked. DiceBear
(`@dicebear/core` and `@dicebear/collection`, MIT, pinned in
`frontend/package.json`) draws on the server through
`frontend/avatars/draw.mjs`, one run of node per batch; nothing leaves the
workspace, so it is no optional service and no clause. The style picked per
record type is the `one_avatar_styles` default. OneMail's `faces.dress`
tries the record's own and Gravatar's first and draws only when both have
nothing. A drawn picture is a File named `drawn-<style>-<hash>.svg` in
Home/Pictures, unattached so it is no attachment and says nothing in the
activity; the name is how a change of style finds what it may redraw and
None what it takes off, and nothing else is ever replaced. Fourteen of the
31 styles are CC BY 4.0: their credit is the creator in the style's name in
the settings and DiceBear's own `<metadata>` inside every SVG.

| File | What it does |
|---|---|
| `sidebar/one/one.json` | One's sidebar, with a link per section |
| `agent.py` | What OneAI offers on these pages, what it is told about where the reader is, and its suggestion tools: a notification rule, its text, and a form customized (`customize`) |
| `notify.py` | The one door every notification goes through, and the sandbox an edited text renders in; see `onedesk/notifications/README.md` |
| `push.py`, `doctype/push_device`, `../public/js/one/push.js` | Web Push: a person's browsers, the site's keys, sending, and the service worker |
| `rules.py` | The workspace's own notification rules: frappe's Notification, held to what a workspace rule may do |
| `custom/notification_type.json` | What a Notification Type carries here: its app, text and channels |
| `head.py`, `figures.py`, `doctype/record_head*`, `../public/js/head.js`, `../public/js/band.js` | What a record's form says above its fields, as rows, and the band that draws its numbers and charts: see below |
| `linked.py` | Fields of a linked record, edited on the form and saved in its save |
| `tabs.py`, `../public/js/record_tabs.js`, `../public/js/one_cloud/record_activity.js` | The tabs after a record's fields (Mail, Files, Activity), each declared by its module under `one_record_tabs` and added to the form in one place; Activity is One's own |
| `../public/js/crumb_switch.js`, `../public/js/panel_menu.js` | Every crumb with somewhere to go is a switcher: a frappe.ui.Popover with a search box over frappe's menu rows, as frappe-ui's Combobox draws one with `trigger="button"`. The place's crumb lists the panel's rows (`onedesk.panel.options`), a record's crumb (a form's last, or the one `shell.trail` marks `one_record`) searches its doctype with `frappe.desk.search.search_link`, with `onedesk.crumbs.suggest[doctype]` before anything is typed (a project's: the reader's open projects), and a crumb a page gave a `menu` filters that. **All …** stays pinned under the rows |
| `../public/js/phone_head.js` | Below 768 wide the page head is two bars, each its own height with a line under it (desk.css), and the trail splits over them: the place stays in the first with the panel's button and search, and phone_head.js moves the page's buttons there too, before search; crumb_switch.js draws the record's crumb and any after it (a project's All Work) as buttons in the second, beside the status and the view switch. The head is marked `one-head-actions` when it has any, its height is set as `--page-head-height` for frappe's sticky parts, and the status pill moves to the second row with its word, which frappe shrinks to a dot on a phone |
| `outside.py`, `boot.py`, `../public/js/desk.js`, `../public/js/outside.js` | One's sidebars and workspaces only, for everyone: frappe's, erpnext's and hrms's are left out of the boot, their addresses and frappe's apps screen go to One's Home. No menu item ends on a screen the reader cannot open (Import, View Audit Trail, Setup Auto Email, System Health), the print page has no Print Settings, frappe's Edit Sidebar is not offered, and its Manage Dock is Arrange Apps (one/rail.py). Frappe's own screens for notification settings, people, files, to-dos, mail and printing open One's. Help is Ask OneAI, the theme is in the user menu, and search, pickers of record types and reports, and global search offer only what One shows (`shown.json`); frappe's documentation links are dropped. A page not found or not permitted keeps the rail. Search, Check In, OneAI, Timers and Notifications are frappe's own buttons in the bar across the top of the shell (`desk.js` `bar`, Discord's and Slack's title bar), since a page with a sidebar of its own hides the panel's band they were in; frappe's full-height boxes are each the window less the bar (`desk.css`), beside the bar the band is hidden, the bar and the pinned rail are one frame with the rest inset in it, its first panel's corner rounded, and on a phone there is no bar and the band keeps them |
| `private.py` | Private apps on this workspace: the installed apps whose package has a manifest.py the registry holds (`names`, `about`, read by registry/private.py without running it), mounted on the rail by `companions.apply` and kept in the boot by `outside.kept`; always-on tiles in OneMarketplace, under the company's name; `claim` hands a typed code to the control plane (`proxy.app_claim`), `waiting` asks how far each claimed install has got; `after_app_install` relayers the rail at once, and `before_app_uninstall` refuses one |
| `marketplace.py`, `../../frontend/src/one/Marketplace.vue`, `MarketApp.vue`, `page/marketplace/` | OneMarketplace, which replaced Turn Apps On or Off: `pages` (pure) makes each app's page from its manifest's `line`, `pitch`, `brings`, `media` (3 to 6 files in its folder's `media/`, served as Help's pictures are, `media.picture`) and `credits` (kinds in `registry/credits.py`, the price list's `MARKUP` keys), the cheapest sold plan with every feature its `plan` names when the workspace's plan lacks one, its `needs`, who needs it (`switches.needed_by`, the private apps always on) and why it is kept now. `turn` sets one app on or off through `apps.switch`, bringing back what was off only because it was (as AICenter's `set_on`), and answers SetupCenter's address on the app when it has steps. Administrators only (`roles.require`); the launcher's foot opens it |
| `apps.py`, `companions.py`, `../public/js/apps.js` | Apps a workspace turns off (`one_hidden_apps`, a global default): the site's Dock layer hides their rows (`companions.layer`), `outside.kept` leaves their sidebars out of the boot so their records open in another app that lists them or on Home (`apps.rehome`), and the record types only they list (`apps.doctypes`) leave the awesomebar (`AwesomeBar.build_options`), DocType pickers (`apps.search_link` wraps frappe's) and empty Link fields on forms. Nothing touches permissions, so OneAI's `has_permission` check before it files still passes; frappe's own disabled-app switch would refuse. OneAI is turned on or off in OneMarketplace and AICenter, reading in AICenter, neither a rail row: `NEEDS` turns Reading off with OneAI, `apps.refuse_ai` in every call of `run.py` refuses every model call, `apps.intake_on` stops `pipeline.later`, `again`, the scheduled jobs and the switches, and `apps.trim` takes their sections out of One's sidebar and their links out of others |
| `../www/404.py`, `../www/message.py`, `../www/error.py`, `../www/me.py` | Frappe's web pages for not found, a message, an error and `/me`, in One's portal look. `/me` sends someone with a desk to Profile and an account holder to `/account` |

**A record's head is rows.** The pill beside a form's title, the sentence
under it, the band of numbers and the verbs a person presses are a **Record
Head** (one per doctype, with a table for each), not a script per doctype.
`head.onload` (every record's onload) works the rows out on the server as the
reader and sends them in `__onload.one_head`; `head.js` draws them on any
form. A band row is one of the record's fields, a field of a record it links
to, a count or a sum of another doctype taken with the reader's own list
permissions, or a **measure**: a Python function a module registers by name
(`one_measures`) that answers one number or phrase, and may say its own
label, tone and link. A verb row names a **verb** a module registers
(`one_verbs`): whom it is for, when it can be done, what it asks in frappe's
own dialog, and what it does; `head.run` checks again that it still can be
done. A chart row names a **chart** a module registers (`one_charts`): a
function of the record that answers a run of figures, drawn beside the band
by frappe's own `frappe.Chart` in one hue (`public/js/band.js`), with the
one figure the record is about in the hue and the rest in grey when it says
which. A measure may add how its number changed (`delta`, drawn with the
Number Card's own pill) and how far it is to a whole (`meter`, frappe-ui's
Progress). `figures.py` is the month and week arithmetic every chart
shares. A condition is frappe's filters, and a template names only
`{{ doc.field }}`, so no row can run anything. Each module declares its heads
(`one_record_heads`) and `head.install` writes them on every migrate. Nobody
edits a Record Head row by row; OneAI (Customizing a Form, below) places a
workspace's own numbers, charts, verbs and linked sections.

A Record Head is one per doctype and its module's to declare, so another app
can't add rows to it. What such an app has to say goes in a **notice**
(`one_record_notices`): a function of the record that answers a line, a few
sentences under it and a colour, or nothing, and the names of the verbs that
are its buttons. `head.js` draws it as a strip above the fields, and a
record's own page that draws no head shows it too (the project's Overview,
from `view.said`'s `notices`). `head.run` takes a notice's verbs as it takes
the head's. The first came from a private app (docs/PRIVATE-APPS.md): whether
a client still holds retention from invoices made before One, until it is
answered.

A verb whose dialog changes money can say what it would change before it is
done: `live`, a function of the record and the dialog's values, answers rows
of a figure now and after, and a few sentences. `head.foresee` runs it as
the fields are typed, saving nothing, and the dialog draws it as a Table
field of figures under the fields, or where the verb's fields put a field
named `one_live`, with the sentences as its description.
A private app's Retention Held is the first to use it.

A form of ours used to say all this in a script per doctype: an overview
method worked the numbers out, and the script drew them under the title and
added its buttons. docs/SHELL.md, decision 4, is the argument for rows. What
stays code is what is really a program, registered by name: a measure's
arithmetic stays Python and tested, and where it goes on the page is a row. A
chart is, for instance, what this customer was billed month by month, or what
the asset is worth over its life. Because a count or a sum is taken with the
reader's own list permissions, the band never shows a number the reader's list
would not. `head.install` writes the heads on every migrate, as notification
types are written.

**A linked section** puts fields of the record a form links to (the
holder's mobile on an asset) on the form itself, in frappe's own controls,
and saves them in the form's own save: `__one_linked` carries what changed
and the `modified` it was read at, and `linked.save` (on_update and
on_update_after_submit) saves the linked record in the same transaction,
refusing a stale one. The linked record's own permissions decide who sees
and who edits, down to the field's permission level. A child table is drawn
as frappe's grid and set whole on the linked record. The fields are laid out
as the linked record's own form lays them (`placing`).

"Put the employee's mobile on this form" means a field of a different record.
Frappe's `fetch_from` copies it, which gives two values that drift apart and
cannot be edited there. A Linked Section names a Link field of the record and
fields of the record it points at, and is saved like this (docs/SHELL.md,
decision 5):

- **One save, one transaction.** frappe keeps a key it does not know
  (`__one_linked`) on the document it saves, and `save` saves the linked
  record in the same request, so if either fails both roll back and there is
  never half a save.
- **A clash is frappe's.** A change somebody made meanwhile is refused with
  the record named, and nothing is overwritten. The form hears the linked
  record's `doc_update` too, and says so before Save is pressed.
- **Permissions are the linked record's**, down to the field. Its fields are
  read-only for a reader who may not write it, and the section is not drawn
  for one who may not read it. A field above permission level nought is
  hidden from a reader without read at that level and read-only without
  write, as it is on the record's own form. On a submitted record only
  fields it allows on submit are editable; on a cancelled one none are.
- **A child table** has its rows added, edited, moved and deleted in the
  grid, and the whole table is sent and set on the linked record, so frappe
  updates, inserts and deletes the rows as it would from that record's form.
  The rows on this form are copies under names of their own, so a form of the
  linked record open elsewhere keeps its own.
- **Not** computed or fetched fields, or a second link onward: those are a
  Connection, or a report.

Profile writes a person's own User record, and their own Employee record when
they have one (`own.employee_of`), and only the fields named in `PROFILE` and
`EMPLOYEE_OWN`. Gender, birth date, mobile and photo go to the employee as well
(`SHARED`), because erpnext copies the employee's values onto the login every
time the employee is saved.

### www/legal.py

`/start` asks a person to agree to the Terms of Service and the Privacy Policy
on its first page, and a person cannot agree to what they cannot read. Inside a
workspace the documents are read in TrustCenter's own page, which needs a sign-in;
`/legal` is the same text, rendered by the same `assemble.render`, for a guest.

On every site rather than the admin site alone: the text is the same
everywhere, and a workspace's sign-in page may link to it too. What is recorded
as agreed is still the acceptance in One (`trust_center/gate.py`); reading here
records nothing.

### www/start.py

A tenant workspace carries this file like every other, and answers 404 for it:
`one_admin.site.is_admin` decides, and a workspace offering its own customers a
signup form would be a confusing thing to stumble onto. On the admin site it
sends the reader to the setup wizard at `/portal/start` (`one_admin/wizard.py`),
keeping a plan or a name the address carried; what the wizard offers, the plans
among it, is read as it is (`one_admin/wizard_offer.py`), so a plan withdrawn in
OneAdmin stops being offered without anybody editing a page.

### www/welcome.py

`ON_TRIAL`: when the plan carried a trial, nothing was charged, so "Payment
received" is simply false — the card was taken and the first invoice is days
away. Done is not in it: "The workspace is ready" is already the whole answer
on the screen somebody opens to click Open it.

### www/your_data.py

On every workspace's own site. A guest (a customer's contact, a supplier, a
lead or an applicant with no account) gives their address and is mailed a
link. A portal reader signed in is sent to Your Data in the portal app,
under Account: the same state and calls as You > Profile > Your Data on the
desk. Someone with a desk is pointed to their profile.

### access.py

People gives each person None, User or Manager on each app that is somebody's
job (`settings.APPS`), and those are erpnext's own roles. Access adds four
things, each frappe's own:

- **Levels.** A Role the workspace makes for one app (`Role.one_app`), between
  its User and its Manager. A person at a level holds the app's User roles and
  the level, and the level carries only what it adds, as Custom DocPerm rows:
  on a kind of record the app's own roles work with, and never a right none of
  them has there, so a level cannot reach past the app's Manager, another app
  or frappe's own records.
- **Record access.** frappe's User Permission: a person sees only the records
  of a territory, a department or a customer group they are given.
- **Profiles.** frappe's Role Profile, a named set of app levels, applied
  through `settings._set_access` rather than by frappe's own sync, which would
  take away roles other parts of One give (HR's Employee). `User.one_profile`
  remembers whose profile it is, and a profile changed is applied again to
  everybody on it.
- **Groups.** frappe's User Group, which frappe's assign dialog already takes.

Writing Custom DocPerm copies a kind's standard permissions first, as frappe's
Role Permissions Manager does, after which an app update to that kind's
standard permissions no longer reaches it.

`save_profile` unlocks the profile it saved. Frappe queues its own sync of the
profile's members on every save and locks the profile until a worker runs it.
One's profiles have none of frappe's members (they are applied here), so the
lock only refuses the next save.

`settle` gives the workspace administrator what each Settings page needs, all
in one list (`ADMINISTRATOR`): Printing, Approvals, Automations, Numbering,
Mail Templates, Reports and Dashboards, every module's lists, Audit Log, Webhooks,
Announcements, Privacy Requests and the Recycle Bin. It also opens the two
builders (workflow and print format), the Note's two field levels, and the
two rights everybody at a desk has (making a report and reading what they
deleted). A right the administrator already has is left alone, and a master
given once is not given again after the workspace takes it away
(`onedesk_masters_given`).

### account.py

A tenant site knows four things, all written into its own config when it was
provisioned: where admin is, which workspace it is, the token that proves it,
and what hostname it answers on. It knows no provider key, no bucket
credential and no press token, and that is the whole security argument — a
workspace that is compromised gives up itself and nothing else.

**Nothing here decides anything.** Quota, price and permission are admin's
answers; account.py asks and records. A tenant site that could decide its own
quota is a tenant site that could raise it.

**An outage degrades rather than stops.** `refresh` failing leaves the last
answer in place with the error beside it, so a header keeps drawing what was
last true. What does not survive is anything that needs a fresh decision — a
new upload, an AI call — and that is the right thing to be fragile about.

`PATIENCE_FOR` is how long an AI run may take on admin: the account waits on
the provider for up to its own sixty seconds, or 110 for a call that thinks
(`gateway.THOUGHT`), so a caller giving up at ten gave up on answers that were
on their way — a drafted appraisal is longer than a lookup.

### agent.py

`suggest_approval`, `suggest_automation` and `draft_notification` are run by
Workspace Setup, on a stronger model, for the same reason the two tools that
lay a page out are run by Print Design: an approval's states, steps, roles and
conditions have to fit together, and a small model sent back to mend one
repeats it. A notification rule goes the same way, since a small model asked
to tell somebody and assign the record reached for the rule, which cannot
assign, rather than the automation.

### announcements.py

An announcement is frappe's own Note, made public and shown on sign-in:
frappe pops it up for each person the next time they sign in, once or on
every sign-in, until the day it expires, and writes down who has seen it.
One adds five things:

- **The administrator may announce.** frappe holds a Note's public and
  sign-in fields at a level only its System Manager writes, so anybody
  else's note stays private whatever they send. One gives that level, and
  the one that shows who has seen it, to the workspace administrator.
- **Everybody is told when one is posted,** on the bell and by mail as
  each chose (Announcement), not only at their next sign-in.
- **The administrators see who has read it,** frappe's own Seen By, and
  OneAI answers who has not.
- **It is frappe's Note list** (`public/js/one/note_list.js`), titled
  Announcements and opening on what is showing: Status (`one_status`,
  Showing or Ended) is a standard filter, administrators get Stop Showing
  in its actions, and `stop` ends one at once by setting its Show Until to
  now. Who has seen each is frappe's own Seen By on the form.
- **It runs along the top bar** (`current`, booted as `one_announcements`
  and drawn by `onedesk.interface.news`): public, not expired, newest five. A Note
  with no expiry runs for `FRESH_DAYS` from when it was posted, as frappe's
  pop-up does. Saving or deleting a public one sends `one_announcements`, and
  every open bar asks again. The text scrolls only when it is wider than the
  bar, pauses on hover and focus, runs the other way in Arabic, and stands
  still for anybody who has asked for less motion. Hiding (`hide`) keeps the
  names on the bar as the person's own default, so it follows them to another
  computer; it is not a record of who read it, which Seen By is.

**It pops up.** frappe works out each person's unseen notes in `on_login`,
which runs before the session is made, so it works them out for Guest and
nobody is ever shown one. `boot` works them out again when the desk loads,
whenever frappe has cleared the list (at sign-in, and when a note changes),
so a new announcement also reaches somebody already signed in, once.

### audit.py

Frappe already writes all three: a `Version` for every change to a record that
tracks its changes, an `Activity Log` for every sign-in and sign-out (failed
ones too), and an `Access Log` for every export, printed PDF and private file
downloaded. Reading them is its System Manager's, whom no workspace has, so
nobody here could answer "who changed this price?" across the workspace. Now
a workspace administrator reads them, as frappe's own lists, with three
limits:

- only changes to, and exports of, the kinds of record they may read, plus
  people's accounts and what they may do (the `PEOPLE` kinds), so the log
  shows no salary to somebody who cannot open a salary slip;
- never frappe's own machinery or the platform's records;
- never what the system did (`SYSTEM`): a scheduler, a patch or an operator
  signed in as Administrator, which is the platform's, not the workspace's.

Nobody writes to it: frappe writes every row, and nobody here may change or
delete one. Frappe clears sign-ins after 90 days; changes and exports are
kept. Audit Trail, frappe's comparison of a document's amendments, stays
out: every submitted record's own timeline already shows each version.

### babel.py

frappe's extractors read doctypes, workspaces, reports and the rest, but not a
card's label, a chart's name or the labels of a format laid out in the print
format builder. The dashboard shows the first two through `__()`, and the
builder's macros print each label through `_()`. An app may add its own
extractors in `babel_extractors.csv` beside it; babel.py's are listed there.

### boot.py

Frappe pins its own Framework tile last on every site. It is the desk's own
administration — Users, Build, Data, the System settings — and the people who
need it all hold System Manager, so anyone else gets a tile they cannot use.

The tile comes from frappe's own `add_to_apps_screen` hook, which we cannot
edit, so it is taken off the screen in boot.py instead. `extend_bootinfo` runs
after `app_data` is built, which is the only seam that sees it.

`boot_session` also sends what each provisioning step is doing, in words. The
list view needs it and so does the form; putting a copy in JavaScript would be
a second list to be wrong the day somebody adds a step. Only on the admin
site, where the screens that read it exist.

### brand.py

Two doctypes because two readers. `Website Settings.app_name` titles the desk,
the login page and every system email, and its `app_logo` is what
`get_app_logo` reads first — the navbar, the login page, the password reset,
the OAuth consent. The desktop screen asks `Navbar Settings.app_logo` instead
and falls back to frappe's own hook, so that one has to be written as well.

`footer_powered` is there for a third reason: a portal page left alone says
**Powered by ERPNext** at the foot, which is erpnext's default and which a
customer signing up to One should never be shown. Found on `/start`. An
empty one is not enough, because frappe's footer treats empty as unset and
draws erpnext's line anyway; a space draws nothing. The mails had the same
line, "Sent via ERPNext", which System Settings' `disable_standard_email_footer`
leaves out.

`footer_items` puts Your Data and the Privacy Policy at the foot of every
public page, the sign-in page included, so somebody who is not a user finds
where to ask for their data (one/privacy_public.py). frappe's own footer
links, so a workspace can change or add to them in Website Settings.

### companions.py

A `Dock` may name a host, and frappe calls an app that does so a companion: it
gets no tile on the apps screen and no rail of its own, and every workspace it
owns resolves its app context to the host. That is exactly what One needs from
the two it is built on — without it, opening an HRMS doctype by URL lands in
Frappe HR's rail under Frappe HR's mark, because `get_modules_linking` puts the
shell that owns the doctype first and only continuity from inside One overrode
it.

The claim is the companion's to make, so it is written onto their own `Dock`
rows — as a column and not through the document, because saving a standard doc
in developer mode writes its JSON back, and their app's file is not ours to
edit. The mount is this site's, which is why it survives nothing: their file
does not carry it, so a `bench update` shipping a newer dock clears the row,
and companions.py runs on every migrate rather than only at install.

Mounting appends the companion's rows to the host's rail. We want the host and
not those nine, so One's site layer carries each of them hidden — the refusal
frappe names for exactly this, since a host cannot veto a mount.

### company.py

Multi-company is not a thing One does. A group that runs four companies buys
four workspaces, which is the commercial decision and also the simpler product:
there is no consolidation, no inter-company anything, and no screen anywhere
that has to ask *whose* this is. What is left over from erpnext and hrms is a
mandatory `Company` Link on about two hundred and fifty doctypes, showing the
same value every time — a field that can only be got wrong and never right.

So every one of them is hidden, and the global default fills it. Where the
field is also mandatory, it is given the company as its default as well:
frappe holds that a hidden mandatory field has a default, and checks it every
time a form's fields change, so without it nobody could add a field to one of
these forms, from the Customize page or frappe's own Customize Form. Where a
document can do better than the default it does: an attendance request and a
shift request take the company from the employee, because that is the answer
even on a site somebody has left two Company records on.

**This is derived from the site rather than shipped as a fixture.** A generated
fixture would have to be pinned to one bench's set of apps, and a site that does
not carry erpnext would fail to import rows naming doctypes it has never heard
of. The list is a query over the schema the site actually has, which is a thing
only the site knows — so it runs after every migrate, beside `policy.seed`, and
by the same rule: write it once, and never overrule a tenant who changed it.

### declutter.py

Every installed app writes into the same navbar and the same onboarding list,
so a One site arrives carrying rows nobody here authored. All of it is site
data, which is why declutter.py is a list of names rather than a patch, and
why a tenant can put any of it back.

`sync_standard_items` matches a navbar row by its label and only appends the
missing ones, so hiding a row survives every migrate. Marking an onboarding
complete is what its own "Skip All" writes, and `import_file` never overwrites
that field.

`HIDE_REPORTS` are reports One has replaced with one of its own. They are
disabled rather than deleted: the row is theirs and a `bench update` would
write it back, and this runs on every migrate so it settles again after one
does. A tenant who wants the original back enables it.

### exports.py

A large export waits for a workspace administrator (second.py). Every way
frappe takes records out in a file is held to the workspace's **Export
Limit** (System Settings `one_export_limit`, 1,000 by default, 0 for none,
in ControlCenter › Sharing), each by `override_whitelisted_methods`:

| Path | frappe's method | Ours |
|---|---|---|
| A list's, the report view's and the report builder's Export | `frappe.desk.reportview.export_query` | `report_view` |
| A report's Export | `frappe.desk.query_report.export_query` | `query_report` |
| Data Export | `frappe.core.doctype.data_export.exporter.export_data` | `data_export` |
| Data Import's Export Data | `frappe.core.doctype.data_import.data_import.download_template` | `data_import_export` |
| The file list's Download (a zip) | `frappe.core.api.file.zip_files` | `zip_files` |
| OneCloud's Download of several files | (one request per file) | `may_export`, asked first by OneCloud.vue |

Each runs frappe's own method and then counts the rows of the file it made
(`rows`: a CSV's lines or a workbook's rows, less the heading), so what is
counted is what would have gone out, whatever filters or grouping made it.
Over the limit the file is dropped from the response and frappe's own
message page (`respond_as_web_page`, which frappe's export already uses for
"No data to export") says it waits, with Back to the screen it came from;
the Export approval is asked of the administrators the first time
(`asked`). An approved export of at least that many records of that kind,
decided in the last day and unused, lets the same person export once
(`used_on`). An export frappe makes in the background and mails is counted
in our job (`report_view_job`, `query_report_job`, enqueued as frappe
enqueues its own), and when it is held the person is told on their bell
(Export Held) rather than mailed a file. Not held here: frappe's bulk
print, which keeps its own limit (System Settings, Max Documents for Bulk
Print), and reading through the REST API a page at a time, which is not an
export.

### home.py

Home is the page `one` (so `/desk/one`, where every `?center=` link opens a
centre, is still Home), drawing the island `onedesk.one_home`
(`frontend/src/one/Home.vue`). `read` gives it what only One sees across
the apps, all at once: what waits for the reader's approval in every app,
the announcements running (`announcements._running`), the apps with a
version they have not opened (`news`, from `versions.for_boot`), and for an
administrator the workspace at a glance (`glance`: people against seats,
apps on, storage against its limit, credits, from `Workspace
Account`) and `attention`. A task, a meeting or a document waiting is its
own app's, on that app's home. Each approval is read through
`frappe.get_list`, so it is exactly what the reader may open. The island
hears the kinds it lists, and a version seen, and asks again.

It replaced frappe's `One` workspace, five Number Cards and a Custom HTML
Block (patches/home_is_a_page.py), then its own first shape, which counted
tasks, meetings and documents that their apps' homes already show.

Nothing here is kept: each number is asked when Home is drawn. `my_day`
reads the reader's whole day across the apps for OneAI, tasks and meetings
included.

### homes.py

frappe's form trail is the record's list, then the record. A kind of record
One keeps on a page of its own (a department, in OneHR's Lists) has a list nobody
reaches: no rail links it. So its trail named a list the reader never came
from, and left out the page they did.

A module says which of its kinds live on its pages (`one_homes` in hooks.py),
as {doctype: [{label, route}, ...]}, for the person reading; the browser puts
those crumbs where frappe's list crumb would be (public/js/shell.js). A kind
the rail links keeps frappe's own crumb.

### layer.py

A workspace customizes a form with frappe's own records (Custom Field and
Property Setter, the DocType's Links and Actions) and one of ours (Record
Head), on the Customize page (one_studio/customize.py). Frappe trusts whoever writes
those, because only the people it lets customize can. A workspace
administrator is not that, so every row written through the Customize page,
and any written by somebody frappe does not let customize, is **held** in
layer.py, as a workspace's notification rule is (one/rules.py).
docs/SHELL.md, decision 6.

- **Nothing that runs.** No virtual field (its options are Python), no HTML
  field (its options are markup the desk puts on the page), no button, and a
  `depends_on` that is a field's name or a comparison of fields and plain
  values, read by `plain` rather than run: the desk runs an `eval:` as
  JavaScript in every reader's browser, and a row anybody here may write that
  runs there turns "may customize a form" into "may act as whoever opens it".
  Client and Server Scripts are refused outright.
- **Nothing that weakens a guard.** No permission level, no ignoring user
  permissions, no field made optional that frappe made mandatory, no Link or
  table pointed somewhere else, and no field changed into another kind.

`property_setter` lets through how a kind of record is named when it comes
from Numbering (one_studio/numbering.py `set_naming_by`), which has checked the kind
and the choice, and writes what Customize Form would: the autoname and naming
rule, the series shown or hidden, and the field a record is named by made
required and unique.

### lists.py

Each list is frappe's or erpnext's own doctype, declared by the module whose
records pick from it, as `LISTS` in its `lists.py` (One's are here, the
Address Book's); `HOMES` names the modules that have any. A module may also
give a list its own icon (`ICONS`) and say what its entries are when they
are not values (`COUNTED`, "10 countries" for Address Templates). An administrator
keeps every module's; an app's managers keep their app's, and are given what
erpnext keeps for a role of its own (access.py `_lists`). Whether a value can
be added, renamed or removed is frappe's own permission check, as anywhere
else; the workspace administrator is given the kinds frappe keeps for its
System Manager (`settle`), so frappe's "Create a new" under a field works for
them too.

**There is no screen of lists.** Every module's ControlCenter ends with
Lists (public/js/one/lists.js, added by the centre frame as the centres
are), one row per list with its count, each opening frappe's list; the
module's other lists are a tree in the window's nav pane beside it (through
`onedesk.interface.trees`). A module with lists and no ControlCenter of its own
(OneCRM, OneBook, OneInventory, OneProject) gets one with only what every
ControlCenter finds. `listed()` is the lists this person keeps, by module, in
boot; `kinds(module)` adds the counts. A value's trail leads to its module's
Lists, then its list (`homes`).

An address template is Jinja, run wherever an address is shown or printed, so
one the workspace writes (layer.held) is held to what a mail template is held
to: every tag it adds names a field of the address, bare, or is an `if` on one
and its `endif`, or a plain label in the reader's language. Every tag it
already had stays, so frappe's own per-country templates can be reworded.

### news/

News Sources and their News Items (one/help/news.md is the Help).

- **Two record types and a third for colour.** `News Source` says where and
  how often; `News Item` is one headline, its own record because items are
  listed, filtered, read by screens and the bar, and deleted one by one as a
  source keeps only its newest `keep`. A child table would have made every
  fetch rewrite the source. `News Category` is a name and a colour, made the
  first time a source names it (`news.category`, called before frappe checks
  links, which is before any hook).
- **Four kinds.** Feed: `feeds.get` asks once over https, only public
  addresses, at most three redirects each checked again, 2 MB, with the
  etag and date it gave last time; `feeds.read` parses with lxml, entities
  off and nothing fetched. Google News: asked of the account
  (`proxy.google_news`, one_admin/google_news.py), never of Google: OneAdmin
  alone fetches Google, one edition at a time on its own timer, shared by
  every workspace that follows it, and pauses all of it on a refusal. The
  source asks hourly (`GOOGLE_EVERY`), or in ten minutes while its edition is
  `waiting`; its Fetch is not shown and `validate` holds it at Hourly. Behind
  the `google_news` service. OneAI: the account's
  `news_brief` (one_admin/news.py), one grounded Gemini call, billed per run,
  at the source's set times. Written: items are written by hand.
- **The schedule** is `next_fetch`, worked out by `fetching.next_at` and read by
  `fetching.due` every five minutes, which enqueues one job per source.
- **Reading** is `news.items`: the newest items of enabled sources, each with
  its category's colour and a logo, the publisher's (a `Face` by its site)
  or the source's (dressed by `faces` from its website, `DRESSED`).
- **The desk** (`news/desk.py`): who follows what is a user default; the top
  bar's news is `announcements.current()["news"]`, switched with
  `announcements.shows`. `one_news` is published when items arrive.
- **The library** is `news/library.json`, searched and added by
  `news/library.py`: plenaryapp/awesome-rss-feeds
  (CC0) plus a few Gulf, Arabic and German feeds of ours, built by a script
  outside the repo from its OPML. Its feeds are other people's; the clause
  `news-content` says so.

### notify.py

**The hub is frappe's own.** A notification to somebody in the workspace is a
Notification Log of a Notification Type. That rings their bell, and frappe
emails it to them if they chose email for that type. We add what frappe's type
lacks, as custom fields on Notification Type: the app it belongs to, what it is
about, its text, and which channels it may use.

**A type is one file in `onedesk/notifications/`**, under the module that
sends it, in one layout (notifications/layout.py). The folder is named in
`hooks.py` under `one_notification_types`, where another app may name its own
list. `install()` makes each one a Notification Type after every migrate. From
then on the workspace's administrator owns its text and its channels.

**Two texts, and whose words they are.** A type's default subject and message
are translatable strings with named slots, `_lt("{who} shared {file} with you")`.
They are sent in each reader's own language, because they are ours and are
translated. Once an administrator edits a text, it is theirs: Jinja in their
own words (`{{ who }} shared {{ file }} with you`), sent as they wrote it.
Resetting a text makes it the default again, and translated again.

**Two ways out:**
- `notify()`, for people in the workspace: the bell, and whatever else they
  chose. The bell is always on, because it is the record of what was sent.
- `mail()`, for addresses outside the workspace (a file request, a shared
  link, a sign-in code), or a mail somebody replies to. It is still the type's
  text, so an administrator can still change it.

Nothing else in OneDesk calls `frappe.sendmail` or writes a Notification Log;
`tests/test_notify.py` holds that.

**What erpnext and hrms send is declared here too** (stage 6), in the module
whose screens it belongs to, in one of three ways:
- told through the hub in our words, by our code in their place: their own
  switch for it is turned off (`replaces`), and hidden;
- told through the hub in their words (`words`): a standard rule of theirs
  carried to the bell (`rule`, one/rules.py), whose text is theirs to write;
- mailed by them (`mailed_by`), where nothing lets us stand in their place, or
  the mail itself is the point (a payslip). Listed, so the administrator sees
  everything the workspace sends; where the app has a switch for it
  (`switch`), or a frappe Notification of ours sends it (`notification`),
  that switch or the Notification's Enabled and Send This are one.

Every value put into a text is escaped first, because the text is HTML in the
bell and in the mail, and a file or person's name is not ours to trust.

**An administrator's Jinja sees its slots and nothing else.** Frappe's own
`render_template` hands a template `frappe.db` and the rest of its safe
globals, which would let whoever edits a text read any record into it. A
workspace administrator is not everybody's HR or accounts, so their text is
rendered in a sandbox with no globals at all, and saving a text that names
anything but its own slots is refused.

`choosable` lists every kind a person can receive. A kind declared for some
roles is theirs only; one that goes outside the workspace is nobody's to
choose. A kind that `follows` another is the same event said another way (one
thing waiting rather than several), so it is not listed: it rides on the kind
it follows, whose `twins` it is in, and takes that kind's choices.

### outside.py

One's rail and its sidebars are a workspace's whole desk. Frappe still boots
every sidebar and workspace a person may open, its own (Build, Users, Email,
Printing), erpnext's (Accounts, Selling, Stock, Home) and hrms's (Payroll,
Leaves), and its sidebar resolver picks among all of them: a record no One
sidebar lists, opened cold or reached from a frappe record, landed in
erpnext's or frappe's sidebar and rail, and their workspaces opened by address
and through search.

So the boot carries One's sidebars only, with One's first, and One's
workspaces only. A record no One sidebar lists stays in the sidebar it was
opened from, or One's when opened cold (frappe's own steps 5 and 6). The
workspaces taken out are named in `one_elsewhere`, and desk.js sends their
addresses, and frappe's apps screen, to One's Home.

A module of erpnext's or hrms's whose sidebar is left out can name where its
kinds go instead (`one_module_heirs` in hooks.py, `inherited`): a kind no
sidebar of One's lists then opens in that one, where frappe would put it in
the reader's first sidebar. erpnext's Projects goes to OneProject, so
Projects Settings, Rates and Project Types open beside OneProject's rail even
for somebody who also has OneHR.

Everybody gets this desk, a System Manager included. A tenant has no System
Manager, and the platform's own people work in OneAdmin, not in frappe's
desk, so an exception for them only hid what a tenant would see.

What One offers on its own is one list, `shown.json`, which the atlas writes
(scripts/atlas.py `shown`, through scripts/docs.py, so `--check` fails when it
is stale): what a rail, a workspace or a Home names, what our screens open,
and those record types' reports, less what one/atlas.py answers is somewhere
else. What is only reached through a Link field or a Connections tab is found
from a record and never offered by itself. Private apps add their own rails
and modules when the cache is filled (`brought`), and `forget` empties it on
every clear-cache, so a migrate or a newly installed app is read again.

Four things read that list. The search bar: every source frappe's draws from
is filtered by where its result goes (outside.js `SOURCES`, `offered`), and
test_outside.py fails when frappe adds a source neither in `SOURCES` nor in
`UNFILTERED`. A picker of record types or reports, which is also what a
Dynamic Link asks first (`standard_queries`, `doctype_query`, `report_query`;
the record types somebody links to by choice, `PICKED`, are added). Global
search (`search`, over frappe's). And the demo check
`one_offers_only_what_it_shows`, which also holds every rail's links to it.

What is not done: an address typed by hand still opens whatever the person's
roles let them read. That is permissions' job (one/access.py), and a list
here would only hide the door, not lock it.

Two more of frappe's that lead out. A record type's or report's
documentation link, on an empty list, in a list's or form's menu, on a report
and in a field's help, is dropped as the meta arrives (outside.js
`undocumented`, wrapping `frappe.model.sync`). And a dashboard or a tool's
record that a rail lists opens in that rail; desk.js `kept` sends one to One's
Workspace Settings only when no rail lists it, where it used to send every
dashboard there, so OneHR's Recruitment Overview left OneHR.

### privacy.py

Frappe has both: a `Personal Data Download Request` that gathers what a person
left across the workspace (the `user_data_fields` hooks) into one file, and a
`Personal Data Deletion Request` that redacts their name and address from
those records, disables the account and renames it to an anonymous one. Both
are driven by its System Manager and its own mails ("Dear User"), and nobody
on a workspace is either. In One:

- anybody asks from You > Profile: a copy of their data, which an
  administrator reviews first (one/privacy_copy.py); or their account
  deleted, confirmed with their password, or by a link One mails them when
  they sign in without one, because it cannot be undone;
- a workspace administrator decides on a deletion in TrustCenter's
  Requests: approve it, or hold it with a reason the person is told (an open
  payroll, a dispute: what the law makes the workspace keep);
- approving runs frappe's own erasure, as frappe runs it, after One deletes
  what is only the person's and no use to anybody else: their OneAI
  conversations and memories, notifications, devices and feeds;
- what the workspace keeps is kept with the name and address replaced:
  invoices they raised, tasks they did, the Recycle Bin and the Audit Log.
  An employee record is HR's, kept as the law requires, and deleted by HR.

Nobody deletes the last administrator, or the person the workspace is billed
to: both have to be handed to somebody else first.

### privacy_copy.py

Frappe's `get_user_data` hands over every row a person's address appears in,
whole: mail they were copied on, records they deleted, pages they printed,
other people's values in the changes they made. Much of that is the
workspace's, not theirs. GDPR article 15 gives a person a copy of their
personal data, and 15(4) lets it be limited where it would harm the rights
of others, the company's confidential information among them. So:

- what is plainly about the person always goes: their account and profile,
  sign-ins, contacts with their address, what OneAI remembers about them,
  what they agreed to;
- what they wrote or touched goes unless an administrator withholds it, kind
  by kind, with a reason the person is told: mail, comments, to-dos, their
  OneAI conversations, which records they changed (never the values), what
  they exported or printed (never the pages), their notifications;
- what is never theirs to take never goes: the contents of records they
  deleted, printed pages, values in other people's records, account secrets.

The request is a `Personal Data Download Request`, frappe's own, with three
custom fields for where it stands, what was withheld and who decided.

### privacy_public.py

They have the same rights as a user and no account to ask from, so each
workspace's own site has a page, `/your-data` (www/your_data.py): they give
their address and whether they want a copy of what the workspace holds about
them or that deleted. One mails a signed link to that address, so only
whoever reads its mail can ask, and nothing is written until it is opened;
the page says the same whatever the address, so it cannot be used to learn
who the workspace knows.

Opening the link files the request where a user's goes: Workspace > Data
Copies or Account Deletions, for an administrator to review and decide the
same way. A copy for them holds what is about them (contacts and records
with their address) and the mail, which may be withheld; it is mailed as a
link that works for a week. Deleting takes their name and address out of
everything the workspace keeps, by frappe's own redaction, without the step
that renames an account they do not have.

Somebody whose address is a user's gets the same link; opening it files the
request as if they had asked from their profile.

### push.py

Standard Web Push (onedesk/notifications/README.md). Nothing of Frappe's relay
and no Firebase account: each message is encrypted on our server for the one
browser it is for (RFC 8291, by `pywebpush`), and the browser's own push
service carries it without being able to read it: Google's for Chrome and
Edge's Chromium, Mozilla's for Firefox, Apple's for Safari, Microsoft's for
Windows. Those four are the only addresses a message is ever sent to
(`SERVICES`), because the address comes from a browser and a server that posts
wherever a browser says is a server anybody can aim.

**Who gets one.** A Notification Log is pushed when its person ticked push for
its type (Settings, Notifications writes `one_push_notification_types` on
their Notification Settings, beside frappe's own email list), the workspace
allows push for it, and they turned push on in at least one browser (a Push
Device). Pushing is queued after the log is committed, so a slow push service
never holds up whatever sent the notification.

**The keys.** One VAPID key pair per site, made the first time it is asked
for and kept in the site's config, never in the database: the private half
signs every push, and a copy of the database is not a copy of it.

**The worker** is served from a method rather than from /assets, with
`Service-Worker-Allowed: /`, so it can be registered for the whole site and a
click can bring an open tab forward instead of opening another. It handles
push and clicks, and nothing else: it never sees a request the page makes.

### quiet.py

HRMS counts first-time milestones by inserting a row and letting the unique
index refuse the second attempt:

    with savepoint(catch=Exception):
        frappe.get_doc({"doctype": MILESTONE_DOCTYPE, "event": event}).insert(...)

The savepoint rolls the row back, but the message the failure left behind does
not roll back with it — `frappe.local.message_log` is a list on the request,
not part of the transaction. So from the second leave application onwards,
every person who approves one is told **"HR Telemetry Milestone
first_leave_applied already exists"**, and the same on expense claims,
attendance requests, shift requests, job offers, appraisals, interviews,
payroll entries and salary slips.

It is the same shape as the "Duplicate Name" that used to land on top of every
clock-in, which `one_hr/clock.py` handles inside its own endpoint. quiet.py is
the general case: hooked on `"*"` for the two events HRMS attaches its
telemetry to, and matching only that doctype's own name, so nothing anybody
meant to say is touched.

### reach.py

A space's rail links to erpnext's, hrms's and frappe's kinds of record, and
each of those decides for itself who may open it. Many open only for frappe's
System Manager, which nobody on a workspace is given (roles.py), so a link
can be in the rail and refuse everybody who sees it. reach.py reads every
rail against the roles People hands out for its app (`settings.APPS`): a link
opens if the app's User or Manager roles, or a role everybody holds, may
read it. Each space's `access.py` gives what is missing.

At boot, `unopened` takes out of every rail what the reader would only be
refused: an address link to a kind they cannot read, a country's screen
where no company is, and a link to a centre that is an administrator's
(`centre_shown`: AccessCenter, One's own settings, AccountCenter's
workspace sections but Plan and Credits for whoever holds it). A section
heading left with no rows goes too. The demo checks
`ones_rail_leaves_out_what_the_reader_cannot_open`.

### recycle.py

Every record frappe deletes is kept whole as a `Deleted Document`, and frappe
puts one back with its own `restore`. Both are its System Manager's, whom no
workspace has, so nobody here could see or undo a deletion. Now:

- everybody sees what they deleted themselves, and puts it back;
- whoever holds Everyone's Deletions (an administrator always does) also sees
  what any person (or OneAI) deleted, of the kinds of record they may read,
  though not the system's own cleanups, and puts it back; only an
  administrator empties it for good;
- what is not a record somebody made is never shown: tables, frappe's own
  machinery (permission rows, property setters) and the platform's records.

It is frappe's Deleted Document list (`public/js/one/deleted_document_list.js`),
each row titled by what it was (`one_title`, set as it is deleted) and
narrowed to what the reader may see by `query` and `has_permission`;
`restore` and `bulk_restore` put back one or many ticked and stamp the time.

Putting one back is frappe's own restore (in recycle.py, from
frappe/core/doctype/deleted_document/deleted_document.py, MIT), with its
checks kept: whoever restores must be able to make and read that kind of
record. Frappe keeps a deleted record until somebody empties it; it is not
among the logs it clears on its own.

`RESTORERS` names what a workspace makes of frappe's machinery, which its
administrators see in the bin all the same, and what puts each back: a plain
insert would leave a field out of the Custom Fields list, or a collection
without its records. Each restorer checks who may and returns the name it
came back as.

### roles.py

Nobody on a workspace is ever given System Manager — not the person who signed
up, not whoever they hand the keys to. System Manager is the whole desk: every
doctype, every setting, the scheduler, the users. What somebody running their
own workspace needs is much narrower — which model an action runs on and what
it is told, the workspace's address, buying credits — and a role that grants
exactly that is one that can be handed out without handing out the site.

It is called Workspace Administrator because frappe already ships a role named
Workspace Manager, and that one is about editing the desk's sidebar pages.

Administrator the user holds every role, so nothing in roles.py locks the
bench's own account out of anything.

### rules.py

A rule is frappe's own Notification: what it watches, when it fires, who is
told, and what it says. It goes to the bell with a notification type of its
own, so everything else follows from the hub: it is mailed or pushed to each
person as they chose, and an administrator decides its channels as for any
other type.

**Frappe trusts whoever writes a Notification**, because only its own roles
may: the text is rendered with frappe's template globals, a condition or a
recipient's condition is Python, a rule can set a field on the record after it
sends, attach its print, and mail any address. A workspace administrator is
not frappe's administrator, so a rule saved by anybody without frappe's own
Notification roles is a **workspace rule** (`one_rule`), held to this:

- it watches a kind of record they may read themselves, on one of `EVENTS`;
- its condition is filters, never Python;
- its text names only fields of that record, `{{ doc.field }}`, and nothing
  else (`check_text`);
- it is told to people by role, by a person field of the record, or to its
  assignees, with no conditions, copies or addresses of its own;
- it goes to the bell only, sets nothing and attaches nothing;
- and when it fires, only the people who may read the record are told
  (`Rule.get_list_of_recipients`), so a rule never shows anybody what their
  own permissions would not.

**The rules erpnext and hrms ship mail whoever they name**, whatever those
people chose. A module that declares one as a type (`rule` in its
`notifications/`) has it carried: the people in the workspace are told
through the hub, in the rule's own words, and only an address that is nobody
here is still mailed (`Rule.send_an_email`). The rule itself is not changed,
so a new version of it arrives with the app.

### second.py

What waits for a second person (docs/run/RUN.md P9.3): a payment out of the
ordinary (one_book/unusual.py), a party's changed bank details
(one_book/details.py, one_hr/bank.py) and a large export (exports.py). Each
is a **Second Approval** (doctype in `one/doctype/second_approval`), read
only, made and brought up to date by `ask`, keyed so the same payment, the
same party or the same person's export of a kind is one waiting request.

- **Who may decide** (`may_decide`): an enabled System User holding the
  request's `approver_role` (Accounts Manager for a payment and a
  supplier's or customer's bank details, HR Manager for an employee's,
  Workspace Administrator for an export), or any workspace administrator,
  who is not the person who asked. `deciders` is who is told and who Home
  lists it for (`waiting_for`, Home's APPROVALS).
- **Never a machine** (`machine`): an agent, OneAI, Administrator, or
  anybody while OneAI writes for them (`frappe.flags.one_intake_writing`),
  can't decide one; `_decide` refuses it before anything else. An agent's
  request is asked for the person it works for (`asker`). The head's verbs
  are the only door, and no agent's REACH or TOOLS names them.
- **Alone** (`alone`): where nobody but the person who asked may decide
  (one administrator who keeps the books too), they approve it themselves,
  and only with remarks, which the record keeps with `alone` set. Refusing
  would leave a one-person workspace unable to pay anybody; letting it pass
  silently would hide it. As soon as a second person holds the role, it is
  theirs again.
- **What approving does** (`DONE`): a payment is submitted by whoever
  approved it, as themselves, so their own right to submit is checked
  (unusual.approved). Bank details and exports are only recorded.
- **Told**: each kind's waiting is its module's notification (Payment
  Waiting for Approval and Bank Details Waiting for Approval in OneBook's,
  Export Waiting for Approval in One's), with the kind's one action as its
  button; whoever asked hears the decision (Approval Decided).
- **Read**: the person who asked and whoever holds its role
  (`has_permission`, `query`); an administrator reads all. A bank number is
  kept masked to its last four (`masked`), so the request never holds the
  whole number; the record it is about has it, for those who may read it.

### setup_wizard.py

The wizard is frappe's and erpnext's, with One's two slides in place of
erpnext's persona slide (which only fed telemetry). Four things are changed
so that it works for a workspace owner anywhere:

- **The owner can run it.** Frappe's page is System Manager's only, and its
  stages save System Settings as whoever is signed in, and nobody on a
  workspace has System Manager. `setup-wizard` is opened to Workspace
  Administrator (access.py `PAGES`), and `setup_complete` runs frappe's own as
  Administrator: only while setup is unfinished, and only for somebody who
  administers the workspace. The theme still lands on the owner.
- **The Standard chart is the one picked.** erpnext lists the country's
  charts first and a Select takes the first; none of them carries both
  payroll accounts (docs/ACCOUNTS.md). The slide puts Standard first and says
  why; a country's chart is still one click away.
- **Days off are the country's, and can be two.** The `holidays` package
  knows each country's weekend (Friday and Saturday in Saudi Arabia, Friday in
  Iran); boot carries the map while setup is unfinished and the slide ticks
  them.
- **The leave and payroll years are the fiscal year** (one_hr/periods.py).

`settle` re-runs every `after_sync` hook once the company exists. Each runs
under a savepoint, so one that fails is logged and left to the next migrate
instead of rolling back the whole setup.

`_assign` tells hrms about the holiday list, which is not the same as telling
erpnext. `hrms.utils.holiday_list.get_holiday_list_for_employee` replaces
erpnext's lookup through the `employee_holiday_list` hook, and reads neither
`Employee.holiday_list` nor `Company.default_holiday_list`: only a submitted
`Holiday List Assignment`. Without one, every question about whether a date is
a holiday throws — leave, attendance requests, and the shift's own processing.
`Company.default_holiday_list` is set as well, because erpnext's own reports
still read it.

### shortcut_center.py

ShortcutCenter's server half (docs/READY.md, mechanism 19). `declared()`
reads each module's `shortcuts.py` and gives every shortcut the id
`<folder>.<key>`; `for_boot()` hands the engine their words, where each
works (`WHERE`, or a module's page), the keys each ships with and the keys
the reader moved. `save` keeps a reader's keys for one shortcut and drops
the entry when they equal the shipped ones; `reset` puts one or all back.

A key is written as the engine reads it: the modifiers held, in the order
mod (Ctrl, or Command on a Mac), alt, shift, then the key's place on the
keyboard (`event.code`: KeyK, Slash, ArrowLeft), or a mouse button
(mouse:back, mouse:forward, mouse:middle). The place, not the letter, so a
shortcut stays on the same key in any keyboard layout. `RESERVED` is what a
browser or the system keeps and no page can be given.

### stamp.py

Frappe Cloud serves `/assets` as immutable for a year, and only frappe's
bundles have a hash in their names. Our includes are plain files, so without
this a deploy reached nobody who had opened One before: the browser kept last
week's script for a year. hooks.py wraps every include in `stamped`, which
adds `?v=` and the first ten characters of the file's md5, and boot carries
the same hashes so theme.js can add them to what `frappe.require` loads later
(OneCloud, a record's mail). A file that did not change keeps its address and
stays cached.

### tabs.py

Each tab is declared by the module that draws it, under `one_record_tabs` in
hooks.py, as a measure or a verb is (one/head.py): a name, a label, where it
goes, and which records carry it. The desk draws it with what that module
registers under the same name in `public/js/record_tabs.js`, which is the one
place the form's layout is added to for them. Nothing is written to any
doctype, erpnext's and hrms's included. docs/SHELL.md, Record tabs.

A tab is on every record that has a room of its own, which is not a child
table or a settings page, unless it names the doctypes it is for; `leaves_out`
names the ones it is not.

### tiers.py

Frappe shows every doctype the same way: its form for a record, and for the
collection each view the doctype qualifies for. Most stay that way. Where we
do more it is declared in tiers.py, and `tests/guards/test_tiers.py` fails on
anything done and not declared.

- **A record** is shown in one of three tiers. **desk** is frappe's form as it
  is, and every doctype not named in tiers.py. **head** is frappe's form with a
  Record Head above its fields (`one/head.py`). **page** is a page of its own,
  for the few records people work inside all day, keeping all the form gives
  (point 6).
- **A collection** keeps every view frappe offers it. Ours may set a view up
  (a list's indicators and filters, a calendar's fields, a tree's parent),
  never take one away.
- **A screen** of ours that stands for a collection or a tool is a desk page,
  named in tiers.py with what it is.

### titles.py

Every report and dashboard the rail points at belongs to erpnext or hrms, and
its heading is its record's name — "Employee Hours Utilization Based On
Timesheet" against a rail row reading "Hours Utilization", "Employees working
on a holiday" against "Working on a Holiday". Five reports and five dashboards
disagreed with the row somebody had just clicked.

Renaming theirs is not available: the name is the record's identity, and a
standard Report is rewritten from its app's JSON on every migrate. Forking ten
of them to change a string is worse than the string.

So the rail's own labels are handed to the browser and the heading is set from
them. **Read from the Sidebar rows rather than typed into a list**: a second
copy of those labels is a copy that will disagree with the first the week
somebody renames a row.

`RENAMES` is what the rail can rename. A workspace's heading is the
workspace's own title. All three are read in `public/js/reports.js`, at their
own seams: a report's heading comes from `QueryReport.set_breadcrumbs`, a
dashboard's from the crumb the dashboard page adds, which honours a `label`
the page never passes, and a list's from its title and its crumb.

`for_boot` also gives each crumb: a crumb leads back to the list the rail
shows, so it says what the row says, for any app's doctype the rails call one
thing: "Items" over an item, "Recycle Bin" over a deleted document. One that
is two rows keeps its own name. Read in public/js/shell.js.

### webhooks.py

A webhook is frappe's own Webhook: a kind of record, an event, an address,
and what to send. The workspace administrator is given it and its Webhook
Request Log, and both are in One's sidebar, so the list and form keep One's
rail. Zapier, Make, n8n or the customer's own server take it from there.

Frappe trusts whoever writes one, because only its System Managers may. A
webhook written by somebody frappe does not let customize (layer.held) is
held to what an automation is held to (one_studio/automations.py):

- it is on a kind of record they can open, never frappe's own or One's;
- it sends only fields they may read: a salary above their level is not
  theirs to send somewhere else;
- what it sends names a field of the record, `{{ doc.customer_name }}`, and
  nothing else, and it decides by no code: a webhook that sends only some
  records is an automation with a Call Webhook step;
- it goes over https to a public address, fixed when saved: never a
  template, never the cloud's metadata service or a neighbour.

**The address is checked when it is sent, too.** frappe's plain sender
follows redirects and resolves the name only when it calls, so a public
address could hand the call to an internal one. `install`, run before
every request and job, sends through frappe's own guarded sender from its
automation engine instead, which checks each hop.

Every call is in the Webhook Request Log: what was sent, what came back,
and whether it was delivered, failed and will be tried again, or gave up.
The administrators hear each morning of any that gave up the day before.

### automation/ and automation_center.py (AutomationCenter)

An automation is a trigger, then steps, kept in `Automation` (one/doctype).
Two modules declare triggers today: OneMail's "When a message arrives",
by mailbox, and OneChat's "When a message is posted", by channel
(one_chat/AGENTS.md, Automations). Nothing in `automation/` knows mail or
chat: every block is declared by the module
that owns it, in its own `blocks.py` as `BLOCKS`, found through the
`one_automation_blocks` hook the registry builds (registry/hooks.py
CONVENTIONS). `kinds.py` has the four kinds:

- **Trigger**: what starts one (`one_mail.arrives`), the record type it
  belongs to (`scope`, a mailbox), what a run is about (`doctype`, the
  message), whether OneAI's reading answers its Ask steps (`reads`), its
  starters, and `keeps`: the module's functions that keep its automations,
  as its own screens did. `scopes` lists the places the reader keeps or asks
  for, `offers` what a place's steps may name (folders, people, who writes
  a reply), `listed` a place's automations in words, `save`, `enable`,
  `delete` and `decide` change them (outright, or asked for and waiting for
  whoever approves), `allowed` and `query` are Automation's permission hooks
  for its rows (`who.py` asks the trigger), and `validate` what a place
  needs beyond the steps. `runs` is said under a place's list.
- **Condition**: what an If may test of the trigger's facts, "text",
  "flag" or "kind".
- **Action**: one thing done, `run(automation, name, step, context)`, its
  module's own function, so an automation can do no more than its owner
  could with that module's screens; its params, its `check`, its `words`,
  `ai` (offered only where OneAI may read) and `offers` of its own.
- **Param**: what an action asks, and when (`shown`).

`hours.py` is what any trigger may test of the day: After Hours and On a
Holiday. `flow.py` is pure: If, Ask and Stop, groups of All or Any, walking the steps
against the facts. `engine.run` is what a trigger's code calls with the
record and its facts; each action is tried on its own and logged if it fails.
No OneAI is needed for any of it: only an Ask and an AI block use it.

Decided 14 November 2026 (P8.4): frappe's own Automation Flow was the first
place to look, and it does not fit a rule. It runs after commit in the
drainer, so a rule's reply could not stand in for the away reply; it has no
order or Stop between flows; its conditions and values are Python and Jinja
it trusts its System Manager to write, the opposite of a block that writes
only its own part; and a mail rule is kept by a mailbox's holders and Mail
Managers, who are not System Managers. The builder does take frappe's own
parts whole: `@framework/ui`'s AutomationCanvas and ConditionBuilder.

`automation_center.py` is the centre's calls; it decides nothing, asking the
trigger's `keeps`. The builder is the island `onedesk.automation`
(frontend/src/automation/), mounted in a place's section of
`public/js/one/automation_center.js`.

### hooks.py

- `after_sync` runs when the app is installed, after its custom fields are
  synced; `after_install` runs before them, and much of this reads them. The
  site wears One from its first boot and carries nobody else's navbar rows or
  checklists; after that all of it is the tenant's, in Website and Navbar
  Settings.
- `code_only_modules`: TrustCenter is not a place but a dialog
  every module's foot opens, so its doctypes have no rail and One inherits
  them. The mapping is frappe's and erpnext's own: a module to where its
  navigation went. OneAI was the same until it had a rail of its own
  (docs/ONE.md, stage 6).
- The operator console has a second gate. The role decides what is listed;
  `one_admin.site.refuse_on_a_tenant` decides what is answered, and it reads
  site_config.json rather than a table, so a tenant administrator granting
  themselves One Operator on their own workspace gets a rail entry and nothing
  behind it.
- `one_ai_*`: what OneAI can do in each module, owned by the module. Reads run
  as the person asking; suggests write a card; suggestions are what the panel
  offers when it opens on a page.
- `before_request` and `after_request`: OneCloud as a network drive. A drive
  password signs a person in on the drive's address before Frappe's API-key
  check would refuse it, and Frappe answers OPTIONS before any method runs, so
  the headers a WebDAV client looks for are added after (one_cloud/dav.py).
  frappe's webhook sender is guarded against internal addresses and redirects
  to them wherever a webhook may be sent from, a request or a job
  (one/webhooks.py).
- `user_data_fields`: frappe's erasure replaces the person's name and address
  wherever they are written, beyond its own list, because the Recycle Bin keeps
  deleted records whole, a to-do names who to call and a notification names who
  did it.
