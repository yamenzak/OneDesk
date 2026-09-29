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

## What to add, grouped into what a person would call it

P1, in the order a new workspace meets them:

1. **Import and Export** (Data Import, Data Export). Customers, items, employees
   and opening balances from a spreadsheet, and any list back out. The first
   thing a new workspace does, and today it cannot.
2. **Numbering** (Document Naming Settings, Document Naming Rule). INV-2026-0001
   and the like, per document. Accountants ask on the first day.
3. **Printing** (Print Format, Letter Head, Print Settings, Print Style, Print
   Heading, Print Format Field Template). How an invoice, a quote or a letter
   looks. Frappe has a drag-and-drop format builder; One only ships OneHR's
   employee letter, and a workspace cannot put its own logo on an invoice.
4. **Mail Templates** (Email Template). Saved replies in OneMail and the body
   of a notification. HR Settings already points at templates nobody can write.
5. **Approvals** (Workflow and its four parts). Who approves a purchase, a leave
   or a discount, in what order, with a **Waiting on Me** inbox (Workflow
   Action). One honours a workflow on a record; nobody can build one.
6. **Automations** (Automation Flow). New in frappe: when a record changes, on
   a date field or on a schedule, check conditions, then set a field, create
   a record, notify, assign, wait or call a webhook. A no-code builder, and
   the biggest single thing a customer would miss.

P2:

7. **Access** (Role Profile, User Permission, Custom DocPerm, User Group,
   Module Profile). Today People gives an app level per person. Missing: a
   salesperson who sees only their own territory, a manager only their
   department, and bundles of access handed out by job.
8. **Reports and Dashboards** (Dashboard, Dashboard Chart Source, Auto Email
   Report). A workspace's own dashboards, and a report mailed every Monday.
9. **Recycle Bin** (Deleted Document). Frappe keeps every deleted record;
   nobody can restore one.
10. **Audit Log** (Version, Activity Log, Access Log, Audit Trail). Who changed,
    exported or printed what, across the workspace, for its administrators.
11. **Privacy Requests** (Personal Data Download and Deletion Request). A
    person asks for their data or to be erased; GDPR expects the door.
12. **Integrations** (Webhook, OAuth Client, Connected App, OAuth settings,
    Social Login Key). Tell Zapier or another system when something changes,
    let another app act for a person, and **Sign in with Google or Microsoft**.

P3: Translation (a workspace's own words), SMS, UTM Campaign and Medium in
OneCRM, announcements (Note), following a record (Document Follow), prefilled
new records (Document Template), a Lists page for Salutation, Gender and
Address Template, Slack notifications, session defaults, LDAP, and the action
after saving.

## Where they would live

Most of this is **Workspace settings**, next to General and People: Numbering,
Printing, Mail Templates, Access, Integrations, Privacy Requests, Translation.
Two are **tools of their own** in One's sidebar, because people use them
rather than set them: **Import and Export**, and **Automations** with
**Approvals** beside it. The **Recycle Bin** and the **Audit Log** go under
Workspace for administrators. **Waiting on Me** goes on Home.

Everything above is frappe's own doctype and its own engine; each is a door
and a look, never a second implementation.

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
