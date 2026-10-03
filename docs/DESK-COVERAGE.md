# Frappe's doctypes, against One

The question: once the Framework app is gone from a customer's switcher, what
does frappe do that a workspace can no longer reach? Nobody on a workspace
holds System Manager (`one/roles.py`), so the stock desk's own screens were
never theirs anyway: every one of these is either behind a door in One, or not
reachable by a customer at all.

Frappe `develop` ships 301 doctypes, 107 of them child tables. This is the
other 194, each with one answer. Generated from frappe's source and One's
sidebars, settings pages and code, then read one by one.

| Answer | What it means | Count |
|---|---|--:|
| In One | a sidebar entry, a settings section or a record part reaches it | 63 |
| **Add, P3** | small, or for some customers; in docs/BACKLOG.md | 16 |
| Later | decided against for now; in docs/BACKLOG.md | 7 |
| Underneath | logs, queues, caches and settings the product runs on | 60 |
| Not a customer's | the platform's or a developer's: schema, scripts, the desk's own furniture | 33 |
| Website, out | frappe's website builder; One is not one | 15 |

P1 and P2 are done, bar Import and Export, which is its own feature. What is
left is in `docs/BACKLOG.md`. Reaching a kind is half of it: the people a
rail is for must be allowed to open it, and erpnext and hrms keep some of
what the rails link to for their System Manager. `one/reach.py` reads every
space's rail against the roles People hands out for it, and each space's
`access.py` gives what is missing; on 2026-10-01 it found 30 such links, and
finds none now.

## The plan: Frappe's Settings dialog is the door

Frappe `develop` has a **Settings** dialog per doctype
(`frappe/public/js/frappe/form/doctype_settings/`), opened from a form's or
a list's menu. Its tabs are Naming, Workflow, Permissions, Print Format,
Notifications, Email Templates, Global Search, and a General tab that shows
the doctype's settings where a Settings Map names them. Each tab lists that
doctype's rules and opens frappe's own form or builder to change one. It is
most of the P1 list, per document, where a person already is.

Two things keep it from a workspace administrator today, and neither is
fixed by System Manager:

- **The menu item** is shown only to whoever may create a Custom Field and a
  Property Setter. The Customize page writes those under its own guard, so
  the workspace administrator is given neither, and the item never shows.
- **Each tab** is shown only when its doctype can be read (`condition` in
  `registry.js`), and the Workspace Administrator reads none of them but
  Notification. The builders behind two tabs, `print-format-builder` and
  `workflow-builder`, are pages whose only role is System Manager, and the
  permission manager is `only_for("System Manager")` on the server.

So the work is doors and grants, not screens: One's own **Settings** menu
item beside **Customize** that calls `frappe.doctype_settings.open`, refused
on the same modules Customize refuses; grants per stage; and a **Custom
Role** row per builder page, which is frappe's own way to add a role to a
standard page. Every route a tab sends to is listed in One's sidebar, so the
rail stays One's and never flips to frappe's Printing or Workflow sidebar.
Across doctypes, the same records get one entry each under Workspace in
One's sidebar, as lists.

**Import and Export is out of this plan**; it is a different feature, later.

### Stages

1. **The door.** The Settings item on forms and lists for workspace
   administrators, and the sidebar entries. Permissions and Global Search are
   hidden from anybody who is not a System Manager: access is our app levels
   and, later, its own screen; the search index is ours. Useful from the first
   day, because Notifications is already granted.
   **Done.** `public/js/doctype_settings.js`: **Settings** beside Customize on
   forms, and on lists by wrapping `ListView.get_menu_items`, offered when
   frappe's own item is not (the same `can_create` test frappe makes) and on
   modules Customize does not refuse. The dialog's tabs are narrowed to what
   has been opened to workspaces (`TABS`: General and Notifications), since
   frappe shows a tab to whoever can read its doctype and reading an Email
   Template is everybody's. The Notifications tab is re-registered under its
   own id on frappe's list panel: it lists the workspace's rules on the
   doctype and opens them, or a new one already set to it, in Workspace ›
   Notifications, selecting One's sidebar first (frappe keeps the sidebar on
   screen for a page of the same app, and every One sidebar is one app).
2. **Numbering.** Document Naming Rule and Document Naming Settings, read and
   write. The tab's "current value" calls `update_series_start`, which is
   `only_for("System Manager")`, so it gets a guarded door of ours or is left
   out. Workspace › Numbering lists every document's series.
   **Done, differently.** Document Naming Settings is not granted after all:
   its whitelisted methods run for anybody who can read it and change any
   doctype's series. `one/numbering.py` is the door instead, guarded to a
   doctype the workspace may change and its administrator may read, calling
   frappe's own `update_series` and `NamingSeries`; the one thing it does not
   do that frappe's System Managers may is move a number down. Document Naming
   Rule is granted, so the Naming tab shows on frappe's own condition, on every
   kind of record. It says how a new record is named, with Customize Form's
   choices written as Customize Form writes them (series, a field made unique,
   an expression, typed, random; the four apps' own switches for the kinds that
   name themselves), the series where the kind has them, and the rules, each
   with the name it would give next. A kind whose records are made by code
   (frappe's User Cannot Create, One's own, or declared by a module in
   `one_makes_records`) is never typed by hand. `layer.py` lets exactly these
   property setters through from there. Workspace › Numbering lists every kind
   with a series, a naming the workspace chose, or rules, read from what the tab
   reads. The General tab is held back: frappe's saves a field on opening (a
   strict `===` after `set_value`), which wrote Accounts Settings twice and met
   itself as a conflict.
3. **Printing.** Print Format, Letter Head and Print Settings, and the print
   format builder through a Custom Role. A standard format stays read-only
   (frappe refuses to change one outside developer mode); a workspace copies
   it and changes the copy. The letter head and its logo go under Workspace ›
   General, beside the logo it already has. Checked before granting: that a
   format's Jinja renders in frappe's sandbox for a non-System Manager, as a
   Notification's already does.
   **Done, with the print page held to what the builder makes.** A printed
   page is drawn on the workspace's own address (and a PDF by a browser on
   the server), so what an administrator writes into one runs as whoever
   opens it. `one/printing.py` grants Print Format, Letter Head, the
   builder's Library (Print Format Snippet) and read on Print Settings
   through Custom DocPerm, and the builder page through a Custom Role that
   keeps the page's own roles. A format the workspace writes is a builder
   format of frappe's escaped blocks: no HTML or Typst block (bar the empty
   ones and the heading frappe's own layout makes), no hand-written, raw or
   JS format, no block key frappe's renderer trusts (`renderer`, `_value`),
   formatted text only from a field that holds it, and styles without markup,
   imports or URLs off the site. The builder's previews of an unsaved format
   run the same checks first (`override_whitelisted_methods`), and its
   canvas previews frappe's own templates, which it keeps to System Managers.
   A letter head written here is an image; one that came with the workspace
   can be made the default or turned off. The star goes through
   `printing.set_default`, since frappe's writes a Property Setter as the
   caller, and the tab's two reads of the default are answered by
   `printing.default`. Letter heads live in Workspace › Printing, not
   General. Found on the way: a letter head picture kept in One's store never
   became its markup, because frappe's `is_image` drops the query where the
   store names the file; it now does, for everybody. The builder's rail is
   frappe's own, as the page is.
4. **Mail Templates.** Email Template, read and write. OneMail's composer
   already has frappe's template field; HR Settings' leave mails start working
   when somebody writes one.
   **Done, with a template held to a rule's text.** Frappe renders a
   template as Jinja with its globals, as whoever sends it, so its author
   could make it read anything the sender may. `one/mail_templates.py` grants
   Email Template and holds one written by the workspace to what
   `one/rules.py` holds a rule's text to: every tag it adds is a field,
   `{{ field }}` or `{{ doc.field }}`, of the record it is for; every tag it
   already had stays, so hrms's leave and interview mails can be reworded.
   A template is edited in One's dialog (`onedesk.mail_templates.edit`,
   frappe's controls, saved with `frappe.client.save` against `modified`),
   from the re-registered tab and from Workspace › Mail Templates, not
   frappe's form, whose rail is frappe's. The default goes through
   `layer.set_default`, which printing now shares, and `roles.grant` is the
   one grant loop for notify, printing and mail templates.
5. **Approvals.** Workflow, Workflow State and Workflow Action Master, and the
   workflow builder through a Custom Role. A workflow is refused on the
   framework's and One's own doctypes. **Waiting on Me** (Workflow Action,
   scoped by frappe's own permission query) goes on Home.
   **Done, with an approval that runs no code.** A workflow can run code:
   a transition's condition and a state's value expression go through
   `safe_eval`, a transition can run tasks, and the state field is written
   on every record of the kind. `one/approvals.py` grants Workflow,
   Workflow State and Workflow Action Master, opens the builder through
   `roles.open_page` (printing's Custom Role code, moved there), and holds
   a workflow the workspace writes to: a kind of record it can open, not
   frappe's or One's; no condition and no tasks on an action; a state sets
   a plain value, only on a first-level field that is not the record's own
   bookkeeping; and a state field that is a Link to Workflow State, made
   by `approvals.py` as the workspace since frappe's step makes it as the
   caller. The tab is re-registered only so New opens the builder's own
   create dialog rather than frappe's Workflow form. **Approvals** on
   Home now counts Open Workflow Actions beside leave and expenses, and
   Workspace › Approvals lists every approval. The builder's rail is
   frappe's, as the print builder's is.
6. **Automations.** Not a tab in frappe's dialog, but the dialog takes new
   ones (`frappe.doctype_settings.register`), so an **Automations** tab lists
   that doctype's Automation Flows and opens frappe's form for one. Run Script
   is refused, since it runs a Server Script; Call Webhook is https only.
   Automation Settings stays the operator's.
   **Done, with a flow that runs as its author.** A flow runs as
   Administrator unless told otherwise, its condition and an If step's are
   Python, every step's values are Jinja with frappe's globals, and a step
   can run a Server Script. `one/automations.py` grants Automation Flow and
   holds one the workspace writes to: it runs as whoever saved it
   (`run_as` Automation User, `automation_user` the author), so each step
   meets frappe's own permission checks as them; no condition and no If
   step; the steps are Set Field, Increment, Create Document (not of
   frappe's or One's doctypes), Send Notification, Assign, Call Webhook
   (https, and frappe already refuses internal addresses) and the two
   waits; and every value's tags are field tags on `doc`, `target`,
   `trigger` or `payload`. The tab is ours, added beside Approvals, and
   opens frappe's own form, which One's sidebar now lists (Workspace ›
   Automations), so the rail stays One's; the form hides the advanced
   condition and Run As from a workspace administrator.

Then P2, each its own screen: Access (where the Permissions tab would have
been), Reports and Dashboards, Recycle Bin, Audit Log, Privacy Requests and
Integrations. Each stage runs the nine points like any screen in the pass.
Integrations is webhooks only (Workspace › Webhooks); signing in with Google
or Microsoft, another app acting for a person (OAuth Client) and One
reaching into an outside service (Connected App) are later, marked so below.

## What was missing, grouped into what a person would call it

P1: Import and Export (later, a different feature), Numbering, Printing, Mail
Templates, Approvals, Automations. P2: Access, Reports and Dashboards,
Recycle Bin, Audit Log, Privacy Requests, Integrations. P3: Translation, SMS,
UTM Campaign and Medium, following a record, prefilled
new records (Document Template), a Lists page for Salutation, Gender and
Address Template, Slack notifications, session defaults, LDAP, and the action
after saving.

## The desk around the doctypes (audit of 2026-10-03)

Every doctype has its answer, but a customer also meets frappe's desk itself:
the rail, the sidebars, the menus, frappe's pages and workspaces. Read from
frappe `11fb93570c` and One's code, with the main points checked by hand.
What is already One's: the rail and its sidebars, the Settings page in the
user menu, a record's head and Activity tab, the Custom Fields and Settings
menu items, the composer, the print page's sidebar, the dashboard and
workflow builder rails, the setup wizard, the theme dialog and Getting
Started. What is left, the most visible first:

1. ~~**Frappe's own records leave One's rail.**~~ **Done** (`one/outside.py`):
   the boot carries One's sidebars only, One's first, for everyone but the
   platform's own people. Frappe's records open in the One sidebar they were
   reached from, or One's when opened cold. Address is in OneCRM beside
   Contact. Where One has its own screen, frappe's opens it instead
   (`outside.js`): Notification Settings opens You › Notifications, the User
   list Workspace › People (and a person's page, or one's own Profile), the
   File list OneCloud, the ToDo list My Tasks, and Print Settings, the Print
   Format list and the Letter Head list Workspace › Printing.
2. ~~**Frappe's, erpnext's and hrms's workspaces still open.**~~ **Done**: out
   of the boot, so search no longer offers them, and their addresses go to
   One's Home (`one_elsewhere`, desk.js). A private workspace can no longer
   be made.
3. ~~**Every sign-in lands on frappe's apps screen.**~~ **Done**: `/desk`
   goes to One's Home, so the apps screen and its avatar menu never show.
4. ~~**An erpnext or hrms record opened cold.**~~ **Done**: with their
   sidebars out of the boot, it opens in One's.
5. ~~**Menu items that end on a screen only a System Manager can open.**~~
   **Done** (`public/js/outside.js`): View Audit Trail and Setup Auto Email
   are offered on frappe's own read check of where they go, the print page's
   Print Settings (read only, even for an administrator) not at all,
   Help › System Health on a navbar condition (`declutter.SHOW_IF`), and
   Import not at all (`can_import` is empty in the boot).
6. ~~**Frappe's editors for its own furniture are open to everybody.**~~
   **Done**: Edit Sidebar and Manage Dock are not offered on One's desk, and a
   private Workspace cannot be made.
7. ~~**Help is erpnext's.**~~ **Done** (`outside.js`): Help is **Ask OneAI**,
   which answers from each product's README, and the site's own help rows.
   The theme is in the user menu. All apps, which only led Home, is gone.
8. ~~**The Communication list and the Inbox view.**~~ **Done**: both open
   OneMail. A single message keeps its form.
9. ~~**Search lists frappe's and erpnext's pages and reports.**~~ **Done**:
   search offers the pages and reports a One sidebar lists or One's own
   modules hold, and OneCalendar rather than frappe's event calendar. Records
   of every kind are still found.
10. ~~**Frappe's not-permitted, not-found and error pages.**~~ **Done**: one
    scene for the desk's and the web's (`templates/includes/one_lost.html`,
    `css/lost.css`, `outside.js`), the code drawn with One's ring as its 0:
    404, 403 (no access), 500, and a message page's own code. The desk's keeps
    the rail. A kind of record the reader may not read says No access, not Not
    Found. A web page that does not exist is 404, not 500 with its traceback.
    `/me` sends someone with a desk to Profile. Set Password is frappe's, in
    One's look.
11. ~~**Frappe reports not in One.**~~ **Done**: Addresses and Contacts is
    in OneCRM › Sales, from erpnext's working report. Permitted Documents For
    User, User Doctype Permissions and Document Share Report stay the
    platform's: frappe allows only its System Manager, and Access and People
    answer who sees what.
12. **The customer portal is erpnext's.** A customer's contact signed in to
    the website meets erpnext's Orders, Invoices, Quotations, Shipments,
    Issues, Addresses, Timesheets and Material Request, in erpnext's look.
    Only a project's page is One's (`www/projects.py`). Its own pass.
13. **Frappe's account pages.** Edit Profile (`/update-profile`), Request
    Account Deletion and Third Party Apps, reached from a contact's account,
    are frappe's web forms and pages in frappe's look. Its own pass.

Kept as frappe's on purpose: list views and their switcher, bulk actions,
filters, group-by, report view, a form's menu, its sidebar (assign, tags,
share), the print page's toolbar, keyboard shortcuts, the bell itself, Reload
and Log Out.

## Every doctype

| Module | Doctype | Answer | Why, or where |
|---|---|---|---|
| Automation | Assignment Rule | In One | OneCRM › Setup › Lead Assignment, the Sales Manager's, on leads and deals (one_crm/access.py) |
| Automation | Auto Repeat | In One | OneBook › Repeating |
| Automation | Automation Event Subscription | Underneath | runs under the product; no screen wanted |
| Automation | Automation Flow | In One | Workspace › Automations and the Settings dialog's tab (one/automations.py) |
| Automation | Automation Settings | Underneath | runs under the product; no screen wanted |
| Automation | Automation Trigger Queue | Underneath | runs under the product; no screen wanted |
| Automation | Milestone | Underneath | written by Milestone Tracker |
| Automation | Milestone Tracker | Underneath | runs under the product; no screen wanted |
| Automation | Reminder | In One | the record's Remind Me |
| Contacts | Address | In One | Workspace › General › Addresses |
| Contacts | Address Template | **Add, P3** | Small lists reached only through a field today; one Lists page |
| Contacts | Contact | In One | OneCRM › Contacts |
| Contacts | Gender | **Add, P3** | as Address Template |
| Contacts | Salutation | **Add, P3** | as Address Template |
| Core | API Request Log | Underneath | runs under the product; no screen wanted |
| Core | Access Log | In One | One › Audit Log › Exports and Prints (one/audit.py) |
| Core | Activity Log | In One | One › Audit Log › Sign-ins (one/audit.py) |
| Core | Audit Trail | Underneath | compares a submitted record's amendments; each record's timeline already shows every version |
| Core | Background Task | Underneath | runs under the product; no screen wanted |
| Core | Comment | In One | every record's timeline |
| Core | Communication | In One | OneMail and every timeline |
| Core | Custom DocPerm | In One | Workspace › Access › Levels: a level's rights, as Custom DocPerm rows (one/access.py) |
| Core | Custom Icon | In One | the dock |
| Core | Custom Role | Underneath | roles for a page or report; One's app levels decide |
| Core | Data Export | Later | with Data Import (docs/BACKLOG.md) |
| Core | Data Import | Later | Bringing customers, items, employees and balances in from a spreadsheet; its own feature (docs/BACKLOG.md) |
| Core | Data Import Log | Underneath | runs under the product; no screen wanted |
| Core | Deleted Document | In One | One › Recycle Bin (one/recycle.py) |
| Core | DocShare | Underneath | runs under the product; no screen wanted |
| Core | DocType | Not a customer's | the platform's or a developer's; a workspace's own custom ones are OneStudio › Custom Collections (one_studio/record_types.py) |
| Core | DocType Layout | Not a customer's | the platform's or a developer's; only an operator |
| Core | DocType Settings Map | Not a customer's | the platform's or a developer's; only an operator |
| Core | Document Naming Rule | In One | Workspace › Numbering and the Settings dialog's Naming tab (one/numbering.py) |
| Core | Document Naming Settings | Underneath | not granted: its methods change any kind's series; one/numbering.py is the door |
| Core | Document Share Key | Underneath | runs under the product; no screen wanted |
| Core | Domain | Underneath | runs under the product; no screen wanted |
| Core | Domain Settings | Underneath | runs under the product; no screen wanted |
| Core | DuckDB Sync | Underneath | runs under the product; no screen wanted |
| Core | Error Log | Underneath | runs under the product; no screen wanted |
| Core | File | In One | OneCloud |
| Core | Installed Applications | Underneath | runs under the product; no screen wanted |
| Core | Language | In One | Workspace › General, You › Profile |
| Core | Log Settings | Underneath | runs under the product; no screen wanted |
| Core | MapReduce Job | Underneath | runs under the product; no screen wanted |
| Core | MapReduce Task | Underneath | runs under the product; no screen wanted |
| Core | Module Def | Not a customer's | the platform's or a developer's; only an operator |
| Core | Module Profile | Underneath | which modules a person sees; One's app levels decide |
| Core | Navbar Settings | Not a customer's | the platform's or a developer's; only an operator |
| Core | Package | Not a customer's | the platform's or a developer's; only an operator |
| Core | Package Import | Not a customer's | the platform's or a developer's; only an operator |
| Core | Package Release | Not a customer's | the platform's or a developer's; only an operator |
| Core | Page | Not a customer's | the platform's or a developer's; only an operator |
| Core | Patch Log | Underneath | runs under the product; no screen wanted |
| Core | Permission Inspector | Not a customer's | the platform's or a developer's; only an operator |
| Core | Permission Log | Underneath | runs under the product; no screen wanted |
| Core | Permission Type | Underneath | runs under the product; no screen wanted |
| Core | Prepared Report | Underneath | runs under the product; no screen wanted |
| Core | RQ Job | Underneath | runs under the product; no screen wanted |
| Core | RQ Worker | Underneath | runs under the product; no screen wanted |
| Core | Recorder | Not a customer's | the platform's or a developer's; only an operator |
| Core | Report | In One | each app's reports in its sidebar |
| Core | Role | In One | Workspace › People, as app levels |
| Core | Role Permission for Page and Report | Not a customer's | the platform's or a developer's; only an operator |
| Core | Role Profile | In One | Workspace › Access › Profiles (one/access.py) |
| Core | SMS Log | **Add, P3** | with SMS Settings |
| Core | SMS Settings | **Add, P3** | Notifications by SMS, which some markets expect |
| Core | Scheduled Job Log | Underneath | runs under the product; no screen wanted |
| Core | Scheduled Job Type | Underneath | runs under the product; no screen wanted |
| Core | Scheduler Event | Underneath | runs under the product; no screen wanted |
| Core | Security Settings | Underneath | One's Sign-in section writes the parts that matter |
| Core | Server Script | In One | OneStudio › Extensions: written by OneAI only, reviewed, on a record event (one_studio/extensions.py) |
| Core | Session Default Settings | **Add, P3** | Defaults a person works under, such as their company |
| Core | Submission Queue | Underneath | runs under the product; no screen wanted |
| Core | Success Action | **Add, P3** | What a person sees after saving a record |
| Core | System Settings | In One | Workspace › General and Sign-in |
| Core | Translation | **Add, P3** | A workspace's own words for ours (call a Lead a Prospect) |
| Core | User | In One | Workspace › People, You › Profile |
| Core | User Group | In One | Workspace › Access › Groups (one/access.py) |
| Core | User Invitation | Underneath | One sends its own invite |
| Core | User Permission | In One | a person's page › Record access (one/access.py) |
| Core | User Type | Not a customer's | the platform's or a developer's; only an operator |
| Core | Version | In One | One › Audit Log › Changes (one/audit.py) |
| Core | View Log | Underneath | runs under the product; no screen wanted |
| Custom | Client Script | In One | OneStudio › Extensions: written by OneAI only, reviewed (one_studio/extensions.py) |
| Custom | Custom Field | In One | OneStudio › Custom Fields, changed through OneAI (one/customize.py) |
| Custom | Customize Form | In One | replaced by OneStudio › Custom Fields |
| Custom | Property Setter | In One | OneStudio › Custom Fields |
| Desk | Bulk Update | Not a customer's | the platform's or a developer's; only an operator |
| Desk | Calendar View | Underneath | runs under the product; no screen wanted |
| Desk | Console Log | Underneath | runs under the product; no screen wanted |
| Desk | Custom HTML Block | Not a customer's | the platform's or a developer's; only an operator |
| Desk | Custom Sidebar | Not a customer's | the platform's or a developer's; only an operator |
| Desk | Custom Workspace | Not a customer's | the platform's or a developer's; only an operator |
| Desk | Dashboard | In One | each app's Dashboards (one/reports.py) |
| Desk | Dashboard Chart | In One | record heads |
| Desk | Dashboard Chart Source | Not a customer's | a chart's source is code; a developer's |
| Desk | Dashboard Settings | Underneath | runs under the product; no screen wanted |
| Desk | Desktop Icon | Not a customer's | the platform's or a developer's; only an operator |
| Desk | Desktop Layout | Underneath | runs under the product; no screen wanted |
| Desk | Desktop Settings | Not a customer's | the platform's or a developer's; only an operator |
| Desk | Dock | Not a customer's | the platform's or a developer's; only an operator |
| Desk | Document Template | **Add, P3** | Prefilled new records: a standard quote, a standard job opening |
| Desk | Event | In One | OneCalendar |
| Desk | Form Tour | Not a customer's | the platform's or a developer's; only an operator |
| Desk | Global Search Settings | Underneath | runs under the product; no screen wanted |
| Desk | Kanban Board | In One | board views (OneCRM, OneTask) |
| Desk | List Filter | Underneath | runs under the product; no screen wanted |
| Desk | List View Settings | Underneath | runs under the product; no screen wanted |
| Desk | Module Onboarding | Not a customer's | the platform's or a developer's; only an operator |
| Desk | Note | In One | Announcements (one/announcements.py) |
| Desk | Notification Log | In One | the bell |
| Desk | Notification Settings | In One | You › Notifications |
| Desk | Notification Type | In One | Workspace › Notifications |
| Desk | Number Card | In One | Home and record heads |
| Desk | Onboarding Step | Not a customer's | the platform's or a developer's; only an operator |
| Desk | Route History | Underneath | runs under the product; no screen wanted |
| Desk | Sidebar | Not a customer's | the platform's or a developer's; only an operator |
| Desk | System Console | Not a customer's | the platform's or a developer's; only an operator |
| Desk | System Health Report | Not a customer's | the platform's or a developer's; only an operator |
| Desk | Tag | In One | list and record tags |
| Desk | Tag Link | In One | list and record tags |
| Desk | ToDo | In One | OneTask and My Tasks |
| Desk | Workspace | Not a customer's | the platform's or a developer's; only an operator |
| Desk | Workspace Sidebar | Not a customer's | the platform's or a developer's; only an operator |
| Email | Auto Email Report | In One | a saved report's Send by Mail (one/reports.py) |
| Email | Document Follow | **Add, P3** | Follow a record and get a digest of its changes |
| Email | Email Account | In One | You › Mail, OneMail |
| Email | Email Domain | Underneath | OneMail |
| Email | Email Flag Queue | Underneath | runs under the product; no screen wanted |
| Email | Email Group | In One | OneCRM › Campaigns, the Sales Manager's (one_crm/access.py) |
| Email | Email Group Member | In One | OneCRM, with Email Group |
| Email | Email Queue | Underneath | runs under the product; no screen wanted |
| Email | Email Rule | Underneath | OneMail |
| Email | Email Template | In One | Workspace › Mail Templates and OneMail's composer (one/mail_templates.py) |
| Email | Email Unsubscribe | Underneath | runs under the product; no screen wanted |
| Email | Notification | In One | Workspace › Notifications |
| Email | Unhandled Email | Underneath | OneMail |
| Geo | Country | In One | picked on records |
| Geo | Currency | In One | picked on records |
| Integrations | Connected App | Later | One reaching into an outside service with OAuth; not built (decided 2026-10) |
| Integrations | Geolocation Settings | Underneath | runs under the product; no screen wanted |
| Integrations | Google Calendar | In One | OneCalendar |
| Integrations | Google Contacts | Underneath | not offered |
| Integrations | Google Settings | Underneath | runs under the product; no screen wanted |
| Integrations | Integration Request | Underneath | runs under the product; no screen wanted |
| Integrations | LDAP Settings | **Add, P3** | Enterprise sign-in; later |
| Integrations | OAuth Authorization Code | Underneath | runs under the product; no screen wanted |
| Integrations | OAuth Bearer Token | Underneath | runs under the product; no screen wanted |
| Integrations | OAuth Client | Later | another app acting for a person, with their consent; not built (decided 2026-10) |
| Integrations | OAuth Provider Settings | Later | with OAuth Client |
| Integrations | OAuth Settings | Later | with OAuth Client |
| Integrations | Push Notification Settings | Underneath | One's own push |
| Integrations | Slack Webhook URL | **Add, P3** | Notifications into a Slack channel |
| Integrations | Social Login Key | Later | sign in with Google or Microsoft; not built (decided 2026-10) |
| Integrations | Token Cache | Underneath | runs under the product; no screen wanted |
| Integrations | Webhook | In One | Workspace › Webhooks (one/webhooks.py) |
| Integrations | Webhook Request Log | In One | Workspace › Webhook Calls |
| Printing | Letter Head | In One | Workspace › Printing (one/printing.py) |
| Printing | Network Printer Settings | Underneath | runs under the product; no screen wanted |
| Printing | Print Format | In One | Workspace › Printing and frappe's print format builder (one/printing.py) |
| Printing | Print Format Field Template | Not a customer's | a field's own Jinja; a workspace's format is the builder's escaped blocks (one/printing.py) |
| Printing | Print Format Snippet | Not a customer's | the platform's or a developer's; only an operator |
| Printing | Print Heading | **Add, P3** | the heading a printed invoice can carry (Tax Invoice, Proforma); a small list, with the Lists page |
| Printing | Print Settings | In One | read by the print builder; changing it stays frappe's (one/printing.py) |
| Printing | Print Style | Not a customer's | a stylesheet; a workspace's styles go through the builder, checked (one/printing.py) |
| Website | About Us Settings | Website, out | One is not a website builder |
| Website | Color | Underneath | runs under the product; no screen wanted |
| Website | Contact Us Settings | Website, out | One is not a website builder |
| Website | Discussion Reply | Website, out | One is not a website builder |
| Website | Discussion Topic | Website, out | One is not a website builder |
| Website | Help Article | Website, out | One is not a website builder |
| Website | Help Category | Website, out | One is not a website builder |
| Website | Personal Data Deletion Request | In One | Workspace › Account Deletions (one/privacy.py) |
| Website | Personal Data Download Request | In One | You › Profile › Your Data, Workspace › Data Copies (one/privacy_copy.py) |
| Website | Portal Settings | Website, out | One is not a website builder |
| Website | UTM Campaign | **Add, P3** | OneCRM has Sources but not Campaigns or Mediums |
| Website | UTM Medium | **Add, P3** | with UTM Campaign |
| Website | UTM Source | In One | OneCRM › Setup › Lead Source, the Sales Manager's (one_crm/access.py) |
| Website | Web Form | In One | OneCRM › Get in Touch |
| Website | Web Form Request | **Add, P3** | with Web Form, a form sent to one person |
| Website | Web Page | Website, out | One is not a website builder |
| Website | Web Page View | Underneath | runs under the product; no screen wanted |
| Website | Web Template | Website, out | One is not a website builder |
| Website | Website Route Meta | Website, out | One is not a website builder |
| Website | Website Script | Website, out | One is not a website builder |
| Website | Website Settings | Website, out | One is not a website builder |
| Website | Website Sidebar | Website, out | One is not a website builder |
| Website | Website Slideshow | Website, out | One is not a website builder |
| Website | Website Theme | Website, out | One is not a website builder |
| Workflow | Workflow | In One | Workspace › Approvals and frappe's workflow builder (one/approvals.py) |
| Workflow | Workflow Action | In One | Home › Approvals, Waiting on Me |
| Workflow | Workflow Action Master | In One | with Workflow |
| Workflow | Workflow State | In One | with Workflow |
| Workflow | Workflow Transition Tasks | Not a customer's | runs code on a step; refused on a workspace's approval (one/approvals.py) |
