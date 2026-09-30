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
| In One | a sidebar entry, a settings section or a record part reaches it | 36 |
| **Add, P1** | a workspace will need it in its first month | 17 |
| **Add, P2** | a growing workspace asks for it | 22 |
| **Add, P3** | small, or for some customers | 16 |
| Underneath | logs, queues, caches and settings the product runs on | 57 |
| Not a customer's | the platform's or a developer's: schema, scripts, the desk's own furniture | 31 |
| Website, out | frappe's website builder; One is not one | 15 |

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
   do that frappe's System Managers may is move a number down. The Naming tab
   is re-registered over it (series only; Document Naming Rule is not offered
   yet), `layer.py` lets exactly the `naming_series` options and default
   through from there, and Workspace › Numbering lists every kind of record
   numbered by a series, with the real next name (frappe's preview counts
   from one). The General tab is held back: frappe's saves a field on opening
   (a strict `===` after `set_value`), which wrote Accounts Settings twice and
   met itself as a conflict.
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

Then P2, each its own screen: Access (where the Permissions tab would have
been), Reports and Dashboards, Recycle Bin, Audit Log, Privacy Requests and
Integrations. Each stage runs the nine points like any screen in the pass.

## What was missing, grouped into what a person would call it

P1: Import and Export (later, a different feature), Numbering, Printing, Mail
Templates, Approvals, Automations. P2: Access, Reports and Dashboards,
Recycle Bin, Audit Log, Privacy Requests, Integrations. P3: Translation, SMS,
UTM Campaign and Medium, announcements (Note), following a record, prefilled
new records (Document Template), a Lists page for Salutation, Gender and
Address Template, Slack notifications, session defaults, LDAP, and the action
after saving.

## Every doctype

| Module | Doctype | Answer | Why, or where |
|---|---|---|---|
| Automation | Assignment Rule | In One | OneCRM › Assignment Rules |
| Automation | Auto Repeat | In One | OneBook › Repeating |
| Automation | Automation Event Subscription | Underneath | runs under the product; no screen wanted |
| Automation | Automation Flow | **Add, P1** | Automations: when a record changes, on a date or on a schedule, do set a field, create a record, notify, assign or call a webhook. Frappe's new builder; nothing in One reaches it. |
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
| Core | Access Log | **Add, P2** | Audit log: who exported or printed what |
| Core | Activity Log | **Add, P2** | Audit log: sign-ins and actions |
| Core | Audit Trail | **Add, P2** | Audit log: a record compared across dates |
| Core | Background Task | Underneath | runs under the product; no screen wanted |
| Core | Comment | In One | every record's timeline |
| Core | Communication | In One | OneMail and every timeline |
| Core | Custom DocPerm | **Add, P2** | what each role may read, write, submit per doctype (the Role Permissions Manager) |
| Core | Custom Icon | In One | the dock |
| Core | Custom Role | Underneath | roles for a page or report; One's app levels decide |
| Core | Data Export | **Add, P1** | with Data Import: a list out to a spreadsheet |
| Core | Data Import | **Add, P1** | Bringing customers, items, employees and balances in from a spreadsheet. The first thing a new workspace needs. |
| Core | Data Import Log | Underneath | runs under the product; no screen wanted |
| Core | Deleted Document | **Add, P2** | A recycle bin with Restore. Frappe keeps every deleted record; nobody can get one back. |
| Core | DocShare | Underneath | runs under the product; no screen wanted |
| Core | DocType | Not a customer's | the platform's or a developer's; only an operator |
| Core | DocType Layout | Not a customer's | the platform's or a developer's; only an operator |
| Core | DocType Settings Map | Not a customer's | the platform's or a developer's; only an operator |
| Core | Document Naming Rule | **Add, P1** | with Document Naming Settings; today only OneProject writes one, for tasks |
| Core | Document Naming Settings | **Add, P1** | Number series: INV-2026-0001 and so on. Accountants ask on day one. |
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
| Core | Module Profile | **Add, P2** | with Role Profile |
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
| Core | Role Profile | **Add, P2** | Access finer than an app level: a bundle of roles to hand out by job |
| Core | SMS Log | **Add, P3** | with SMS Settings |
| Core | SMS Settings | **Add, P3** | Notifications by SMS, which some markets expect |
| Core | Scheduled Job Log | Underneath | runs under the product; no screen wanted |
| Core | Scheduled Job Type | Underneath | runs under the product; no screen wanted |
| Core | Scheduler Event | Underneath | runs under the product; no screen wanted |
| Core | Security Settings | Underneath | One's Sign-in section writes the parts that matter |
| Core | Server Script | Not a customer's | the platform's or a developer's; only an operator |
| Core | Session Default Settings | **Add, P3** | Defaults a person works under, such as their company |
| Core | Submission Queue | Underneath | runs under the product; no screen wanted |
| Core | Success Action | **Add, P3** | What a person sees after saving a record |
| Core | System Settings | In One | Workspace › General and Sign-in |
| Core | Translation | **Add, P3** | A workspace's own words for ours (call a Lead a Prospect) |
| Core | User | In One | Workspace › People, You › Profile |
| Core | User Group | **Add, P2** | a named group to assign to, share with and notify |
| Core | User Invitation | Underneath | One sends its own invite |
| Core | User Permission | **Add, P2** | Access by record: a salesperson sees only their territory, a manager only their department |
| Core | User Type | Not a customer's | the platform's or a developer's; only an operator |
| Core | Version | **Add, P2** | Audit log: who changed what, across the workspace, for administrators |
| Core | View Log | Underneath | runs under the product; no screen wanted |
| Custom | Client Script | Not a customer's | the platform's or a developer's; only an operator |
| Custom | Custom Field | In One | Customize page |
| Custom | Customize Form | In One | replaced by the Customize page |
| Custom | Property Setter | In One | Customize page |
| Desk | Bulk Update | Not a customer's | the platform's or a developer's; only an operator |
| Desk | Calendar View | Underneath | runs under the product; no screen wanted |
| Desk | Console Log | Underneath | runs under the product; no screen wanted |
| Desk | Custom HTML Block | Not a customer's | the platform's or a developer's; only an operator |
| Desk | Custom Sidebar | Not a customer's | the platform's or a developer's; only an operator |
| Desk | Custom Workspace | Not a customer's | the platform's or a developer's; only an operator |
| Desk | Dashboard | **Add, P2** | A workspace's own dashboards of charts and number cards |
| Desk | Dashboard Chart | In One | record heads |
| Desk | Dashboard Chart Source | **Add, P2** | with Dashboard |
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
| Desk | Note | **Add, P3** | Announcements shown to everybody on sign-in |
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
| Email | Auto Email Report | **Add, P2** | Mail a report every Monday to whoever needs it |
| Email | Document Follow | **Add, P3** | Follow a record and get a digest of its changes |
| Email | Email Account | In One | You › Mail, OneMail |
| Email | Email Domain | Underneath | OneMail |
| Email | Email Flag Queue | Underneath | runs under the product; no screen wanted |
| Email | Email Group | In One | OneCRM |
| Email | Email Group Member | In One | OneCRM, with Email Group |
| Email | Email Queue | Underneath | runs under the product; no screen wanted |
| Email | Email Rule | Underneath | OneMail |
| Email | Email Template | **Add, P1** | Saved mails for OneMail replies and for notifications. HR Settings already points at them and nobody can write one. |
| Email | Email Unsubscribe | Underneath | runs under the product; no screen wanted |
| Email | Notification | In One | Workspace › Notifications |
| Email | Unhandled Email | Underneath | OneMail |
| Geo | Country | In One | picked on records |
| Geo | Currency | In One | picked on records |
| Integrations | Connected App | **Add, P2** | Integrations: connect an outside API with OAuth |
| Integrations | Geolocation Settings | Underneath | runs under the product; no screen wanted |
| Integrations | Google Calendar | In One | OneCalendar |
| Integrations | Google Contacts | Underneath | not offered |
| Integrations | Google Settings | Underneath | runs under the product; no screen wanted |
| Integrations | Integration Request | Underneath | runs under the product; no screen wanted |
| Integrations | LDAP Settings | **Add, P3** | Enterprise sign-in; later |
| Integrations | OAuth Authorization Code | Underneath | runs under the product; no screen wanted |
| Integrations | OAuth Bearer Token | Underneath | runs under the product; no screen wanted |
| Integrations | OAuth Client | **Add, P2** | Integrations: let another app act for a person |
| Integrations | OAuth Provider Settings | **Add, P2** | with OAuth Client |
| Integrations | OAuth Settings | **Add, P2** | with OAuth Client |
| Integrations | Push Notification Settings | Underneath | One's own push |
| Integrations | Slack Webhook URL | **Add, P3** | Notifications into a Slack channel |
| Integrations | Social Login Key | **Add, P2** | Sign in with Google or Microsoft for the workspace's people |
| Integrations | Token Cache | Underneath | runs under the product; no screen wanted |
| Integrations | Webhook | **Add, P2** | Integrations: tell another system when a record changes (Zapier, Make, their own) |
| Integrations | Webhook Request Log | **Add, P2** | with Webhook |
| Printing | Letter Head | **Add, P1** | with Print Format: the logo and address at the top of every printed page |
| Printing | Network Printer Settings | Underneath | runs under the product; no screen wanted |
| Printing | Print Format | **Add, P1** | How an invoice, quote or letter prints. Only OneHR's employee letter is ours; a workspace cannot brand its own documents. |
| Printing | Print Format Field Template | **Add, P1** | with Print Format |
| Printing | Print Format Snippet | Not a customer's | the platform's or a developer's; only an operator |
| Printing | Print Heading | **Add, P1** | with Print Format |
| Printing | Print Settings | **Add, P1** | with Print Format: paper size, PDF, the default letter head |
| Printing | Print Style | **Add, P1** | with Print Format |
| Website | About Us Settings | Website, out | One is not a website builder |
| Website | Color | Underneath | runs under the product; no screen wanted |
| Website | Contact Us Settings | Website, out | One is not a website builder |
| Website | Discussion Reply | Website, out | One is not a website builder |
| Website | Discussion Topic | Website, out | One is not a website builder |
| Website | Help Article | Website, out | One is not a website builder |
| Website | Help Category | Website, out | One is not a website builder |
| Website | Personal Data Deletion Request | **Add, P2** | GDPR self-service: a person asks to be erased |
| Website | Personal Data Download Request | **Add, P2** | GDPR self-service: a person asks for their data |
| Website | Portal Settings | Website, out | One is not a website builder |
| Website | UTM Campaign | **Add, P3** | OneCRM has Sources but not Campaigns or Mediums |
| Website | UTM Medium | **Add, P3** | with UTM Campaign |
| Website | UTM Source | In One | OneCRM |
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
| Workflow | Workflow | **Add, P1** | Approvals: who approves what, in what order. One honours a workflow on a record but nobody can build one. |
| Workflow | Workflow Action | **Add, P1** | the Waiting on Me inbox of approvals, which nobody reads today |
| Workflow | Workflow Action Master | **Add, P1** | with Workflow |
| Workflow | Workflow State | **Add, P1** | with Workflow |
| Workflow | Workflow Transition Tasks | **Add, P1** | with Workflow |
