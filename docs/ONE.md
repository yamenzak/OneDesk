# One, cut down, and AccountCenter

One stops being where everything without a home ends up. What it holds today
goes to the centre or the module it belongs to, AccountCenter becomes a
module of its own, and what One keeps is the shell, Home and a few screens,
each drawn for what it is on OneInterface rather than a frappe list in a
rail. Then One goes through `docs/READY.md` like every other module.

This is the plan, with each stage marked as it is built (Stages, below).
AccountCenter is mechanism 17 in `docs/READY.md`.

## What was decided

Decided on 2026-10-26, before this was written:

1. **AccountCenter is its own module.** It was the heading on OneMail's
   dialog for one mailbox; it becomes where a person keeps their own
   account and where an administrator keeps the workspace's: who is in it,
   their devices, the plan and the domains.
2. **AccountCenter has Yours and Workspace,** as NotificationCenter and
   AICenter do. Finding your own passkey and adding somebody to the team
   are both account questions, and nobody should have to guess which
   centre to open.
3. **Masters go to the modules that use them.** The Masters page goes.
4. **One is bespoke.** Every screen it keeps is designed for what it is and
   drawn on OneInterface (`docs/ONEINTERFACE.md`, The screen contract), not
   a doctype's list dropped in a rail. A log nobody reads row by row (sign-ins,
   webhook calls, exports) is a view inside the centre that owns it, not a
   rail row of its own.
5. **Everything in `docs/READY.md` applies** to One and to AccountCenter's
   module.
6. **Before production, nothing old is kept** (`docs/READY.md`, Before
   production). A page that moves leaves no redirect and no second way in.

## What One holds today

Measured on 2026-10-26.

- **The rail:** 45 rows in eight groups: Home, Dashboards, Announcements,
  Recycle Bin; Address Book; You (7); Workspace (7); Setup (5); Automation
  (5); Privacy (2); Audit Log (3); OneAI (9).
- **Two pages for settings:** Settings (You) and Workspace Settings, both
  drawn by `one/settings.py` (2,028 lines, 19 sections) and
  `public/js/settings.js` (2,783 lines).
- **Masters:** `one/masters.py`, 29 short lists in a tree: 8 OneCRM, 8
  OneHR, 6 OneInventory, 2 OneBook, 1 OneProject, and 4 shared
  (Salutation, Gender, Print Heading, Address Template).
- **`onedesk/one/`:** 77 Python files, 26,543 lines, and 14 doctypes. Some
  are the shell, some are engines every module uses, and the rest are
  screens that belong to somebody else.
- **AccessCenter and NotificationCenter** are One's, in
  `public/js/one/access_center.js` and `public/js/one/notification_center.js`,
  outside any module's places.
- **AccountCenter** is only a heading: `dialog.center = { center: "account" }`
  in `one_mail/onemail_settings.js`.

## AccountCenter

The module is OneAccount (`one_account`). Its
centre is drawn on the settings dialog like the others
(`onedesk.CENTERS.account`), opens from your avatar at the foot of the rail
and from the arrows, and has two groups.

**Yours**, for everybody:

- **Profile**: what Settings › Profile holds today (`settings.py` profile).
- **Sign-in**: passkeys and where you are signed in (`signin.py`).
- **Your devices**: the browsers you have signed in on (`devices.py`, yours).

**Workspace**, for administrators:

- **People**: who is in the workspace, inviting somebody, and taking them out
  (`settings.py` people, `invite.py`, `owner.py`, `roles.py`). What each
  person may do stays in AccessCenter, which People links to.
- **Devices**: company devices, assigned or shared, and the rules for
  passkeys (`devices.py`).
- **Plan and Credits**: the plan, credits, and One's invoices to the
  workspace (`settings.py` plan, `account.py`, `bills.py`, `heads.py`). It
  is where the marketplace arrives when it is built.
- **Domains** (`settings.py` domains).
- **Apps**: the apps the workspace has on, and its private apps (`apps.py`,
  `private.py`).
- **Closing the workspace** (`closing.py`), at the end, as it is today.

What it tells people (`tell.py`) moves with it. OneMail's mailbox dialog
stops calling itself AccountCenter: it is OneMail's ControlCenter with the
mailbox's address under it, which is what it already is.

## Where the rest goes

| Today | Goes to |
| --- | --- |
| You › Notifications | NotificationCenter, Yours (it already opens it) |
| You › Mail | OneMail's ControlCenter, Your Mailboxes |
| You › Calendar | OneCalendar's ControlCenter |
| You › What OneAI Remembers, What OneAI Reads | AICenter, Yours |
| You › Agreements | TrustCenter |
| Workspace › General | One's own ControlCenter: Company (with Start Again), Branding, Region and Formats, Sign-in, Sharing |
| Workspace › Access | AccessCenter (it already opens it) |
| Workspace › Holidays | OneHR (`holidays.py`) |
| Setup › Numbering, Printing, Approvals | OneStudio |
| Setup › Mail Templates | OneMail (its ability is already there) |
| Automation › Workspace Notifications | NotificationCenter, Workspace (the words and the rules, `rules.py`) |
| Automation › Automations, Reports by Mail, Webhooks, Webhook Calls | OneStudio |
| Privacy › Data Copies, Account Deletions | TrustCenter, Your Data (`privacy*.py`) |
| Audit Log › Changes, Sign-ins, Exports and Prints | AccessCenter, one Audit Log view (`audit.py`) |
| OneAI › every row | OneAI's own rail (its screens are already its own) |
| Masters | each module's ControlCenter, under **Lists** |

**OneStudio becomes "adapting One".** Its README already says it is where
administrators adapt One to their business. With numbering, printing
(`printing.py`, `print_*.py`, `letter_heads.py`), approvals, automations
(`automations.py`, `automation_steps.py`), webhooks, saved reports and
dashboards (`reports.py`), the Customize page (`customize.py`) and OneAI's
setup tools for them (`ai_setup.py`), it holds everything a workspace
changes about how One works. The engines stay importable from one place,
so a module that prints calls OneStudio's printing.

**Masters as Lists.** `masters.KINDS` splits into a `LISTS` declaration in
each module (same shape: the doctype, its plural, its singular), and each
module's ControlCenter ends with **Lists**, drawn as the tree is today. The
shared four go where they are used: Salutation, Gender and Address
Template to the Address Book, Print Heading to OneStudio's printing.
Managers keep seeing their module's lists, as they do now.

## What One keeps

**Screens**, each drawn for what it is:

- **Home**: what is waiting for the reader today, and for administrators,
  how the workspace is doing (`home.py`).
- **Address Book**: contacts and addresses as one screen, a list beside the
  person or place, not two frappe lists.
- **Announcements**: what the office has said, and writing a new one.
- **Recycle Bin**: what was deleted, and putting it back.

**Centres:** AccessCenter (with the Audit Log), NotificationCenter, and One's
ControlCenter (General). HelpCenter and UpdateCenter stay the shell's.

**The shell:** the top bar, the bottom bar, the dock, OneInterface, the boot,
the brand, and what keeps frappe's own desk out (`boot.py`, `brand.py`,
`declutter.py`, `outside.py`, `titles.py`, `quiet.py`, `stamp.py`,
`companions.py`, `company.py`, `countries.py`, `tiers.py`, `reach.py`,
`atlas.py`).

**The engines every module uses,** listed in `ready.SHARED` with why:
abilities, notify and push, the record head (`head.py`, `stages.py`,
`figures.py`, `linked.py`, `tabs.py`, `homes.py`), the workspace layer
(`layer.py`, `babel.py`), boards, and the READY mechanisms themselves
(`ready.py`, `versions.py`, `tours.py`, `setup_steps.py`, `setup_wizard.py`).

**Decided since:** the portal is OnePortal (`one_portal/`), a module of its
own: the engine, invitations, links and the Portal dialog there, and what
each kind of record looks like on the portal in the `portal.py` of the
module it belongs to (one_portal/AGENTS.md).

## Stages

Each stage ends the same way: the gates, the demo checks, a look in the
browser on a desktop and a phone, in English and Arabic, a commit, a push
and a screenshot. A module that is already ready and takes something in
moves its version.

1. **AccountCenter.** Built. OneAccount (`one_account`) has its folder,
   registry entry, Help pages, roles, notifications, legal clauses, setup
   step and tour; `signin.py`, `devices.py`, `invite.py`, `owner.py`,
   `bills.py`, `heads.py`, `closing.py` and `private.py` and the four
   account doctypes moved in. The centre has Profile and Sign-in under
   Yours, and People, Devices, Plan and Credits and Domains under
   Workspace. One's rail rows for those six open it, and OneMail's mailbox
   dialog is its ControlCenter. Changed from the plan: there is no separate
   Your devices (Sign-in already lists where you are signed in), Apps stays
   in Workspace Settings until stage 2, and `account.py`, `apps.py` and
   `tell.py` stay in One, which every module calls through them.
2. **Settings empties.** Built. A centre's section is a `CenterSection`
   (`public/js/center_section.js`), lifted out of AccountCenter, so each
   moved section kept its drawing and its save. General is One's
   ControlCenter (`one/control.py`, `public/js/one/one_control.js`); Access's
   roles, profiles and groups are AccessCenter's Roles and Profiles, at the
   top of its list; Holidays is OneHR's ControlCenter (`one_hr/control.py`, and
   `holidays.py` moved into OneHR); the calendar link is OneCalendar's
   ControlCenter, Your Calendar Link; What OneAI Remembers and What OneAI
   Reads are AICenter's Yours (`one_ai/yours.py`); Notifications is
   NotificationCenter's Everything, which took the one switch it lacked
   (mail about what is assigned to you). The Settings page is deleted.
   `/desk/one?center=settings&module=OneHR&at=holidays` opens any module's
   ControlCenter (`onedesk.control_centers`), and every centre tells OneAI
   which tab is open. Workspace Settings keeps Workspace Notifications,
   Numbering, Printing and Approvals until stage 3.
3. **OneStudio takes Setup and Automation.** Built. Printing (with
   `print_*.py` and `letter_heads.py`), numbering, approvals, automations
   and their steps, saved reports and dashboards (`reports.py`), Customize
   and OneAI's setup tools moved into `one_studio/`. Numbering, Printing
   and Approvals are OneStudio's ControlCenter (`one_studio/control.py`,
   `public/js/one_studio/studio_control.js`), and its rail has Setup and
   Automation (Automations, Reports by Mail, Webhooks, Webhook Calls).
   Workspace Notifications is NotificationCenter's Words and Rules
   (`one/notification_words.py`), Mail Templates OneMail's ControlCenter.
   The Workspace Settings page and `settings.js` are deleted; the
   stylesheet the moved sections share is `center_section.css`.
4. **Privacy and the Audit Log.** Built. TrustCenter's Your Data ends,
   for administrators, with Requests: who asked to have their account
   deleted and who asked for a copy of their data, each opening its
   request (`privacy.requests`). AccessCenter's top of the list has the Audit
   Log: changes, sign-ins and exports and prints as one list, newest
   first, filtered by kind, each row opening frappe's record
   (`audit.log`). One's rail loses Privacy and Audit Log, and its
   Workspace group gains Audit Log.
5. **Masters go home.** Built. Each module declares its lists as `LISTS` in
   its `lists.py`, and `one/lists.py` is the engine (`HOMES`, `listed`,
   `kinds`, `homes`, `place`). Every ControlCenter ends with Lists
   (`public/js/lists.js`, found by `module_settings.open` as the centres
   are), one row per list with its count, each opening frappe's list in the
   module's own rail with the module's other lists beside it. Salutation,
   Gender and Address Template are One's (Address Book › Lists), Print
   Heading OneStudio's. OneCRM, OneBook, OneInventory and OneProject have
   no ControlCenter of their own yet, so theirs holds only what every
   ControlCenter finds, and each module's rail has a Lists row that opens
   it. A list's trail reads "OneHR Lists / Departments". The Masters page,
   `masters.py` and `masters.js` are deleted, and One's rail has no Setup.
6. **OneAI's rail leaves One's.** Built. OneAI is on the dock with a rail
   of its own (`one_ai/sidebar/oneai/oneai.json`): Documents first, then
   Conversations, Suggestions and Knowledge, Reports (Ready to Submit,
   Deadlines, Spending, Credits) and AICenter. One AI leaves
   `code_only_modules`, so its records open in its rail. Turned off in Apps,
   OneAI's rail leaves the dock as any app's does; `apps.py` keeps Reading
   as the one switch that is not an app, and when it or OneAI is off the
   rows it named (Documents, its reports, What OneAI Remembers and Reads)
   leave every rail (`apps.gone`). What OneAI Remembers and Reads stay under
   You in One's rail, since they are the reader's own.
7. **One's own places.** Built. One is in `ready.MODULES` (not ready
   yet), and every READY guard holds it. AccessCenter's, NotificationCenter's
   and One's ControlCenter's scripts are in `public/js/one/`. Every file
   left in `onedesk/one/` is One's or named in `ready.SHARED` with why: the
   engines every module uses, and the portal, privacy and webhooks on their
   way to their own modules (`OUTSIDE` must be empty, so `SHARED` says
   where they are going); a module's files leave `SHARED` out. The
   abilities engine is `one/rights.py`, so `one/abilities.py` is One's own:
   One User and One Manager, and **Everyone's Deletions**, which lets a role
   see and put back what anybody deleted. One's README became its AGENTS.md
   and twelve Help pages; what it said of OneStudio, OneHR and OneCalendar
   went to theirs. Its notifications are `one/notifications.py`, its
   changing calls are each in `NOT_FOR_AI` with why, its foot is drawn on
   any screen of its rail, and it has no setup steps or tours until stage 8.
   Registering One held OneLegal's own clauses, written under One's name, to
   one point to a sentence, so the agreements were reworded without
   changing what they say. Roles and abilities now settle on every migrate,
   not only on install.
8. **One's screens, bespoke.** Built. Each is a Vue island on a page of its
   own, declared in `tiers.SCREENS`, with a tour (`one/tour.py`). Home is
   the page `one`, so `/desk/one` and every `?center=` link still work; it
   counts what waits for the reader in each app they have, lists the first
   tasks due, today's calendar and the approvals waiting, and for an
   administrator what the workspace needs (`home.read`). The `One`
   workspace, its five number cards and its block are gone
   (`patches/home_is_a_page.py`). Dashboards lists frappe's dashboards
   under the app each is about, for whoever works in it
   (`one/dashboards.py`), and an administrator makes one with New
   Dashboard. Announcements shows each in full, Showing Now and Earlier, and
   for an administrator who has seen each and Stop Showing. The Recycle Bin
   lists deletions by day, searched and narrowed by kind, put back one at a
   time or many ticked, with Yours and Everyone's for whoever holds
   Everyone's Deletions. The rail's Contacts and Addresses, under Address
   Book, are frappe's own Contact and Address lists. Changed from the plan: Dashboards keeps New
   Dashboard, since OneStudio has no place to make one yet.
   Later it got one: the page is gone (`patches/no_dashboards_page.py`),
   each app's dashboards are Overview rows on its own rail, and OneStudio ›
   Dashboards, Charts and Number Cards is where they are made.
9. **READY for One and AccountCenter.** Built. Both are ready at 1.0.0,
   with their hand looks recorded in `ready.MODULES`. The walk found five
   things and fixed them. Tours were drawn shifted in Arabic, in every
   module: frappe's right-to-left sheet turns driver's `left: 0` into
   `right: 0`, and a step written for the left now mirrors.
   AccessCenter only knew People's six apps, so nobody could be made One's,
   OneAI's, OneAccount's or OneLegal's Manager from a screen. Now a module
   everybody uses gets a People tab with User and Manager
   (`people.with_roles`), and On One Record shows only where something is
   given on a record. A OneAccount Manager was shown Plan and Credits and
   then refused it, because the closing details are an administrator's.
   Somebody who administers nothing saw One's Workspace links and was
   refused by each (`reach.centre_shown`). Dashboards took 24 seconds,
   because frappe's sidebars were built once for every kind of chart; now
   they are read once a request. The demo keeps Mariam as One's Manager
   and Huda as OneAccount's.

## Open

- **Whether the Address Book stays One's.** Every module uses contacts, which
  is why it is here; it could also be a module of its own.
- **The portal's module** (above).
