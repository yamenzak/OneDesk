# UI notes from the walk

The rules below are gathered, as they are applied, in
`.claude/skills/ui/SKILL.md`.

Yamen's points from walking every screen, written as rules for the next
screen. When the walk ends, each one either moves into the UI contract
(`onedesk/one_interface/AGENTS.md`, `docs/WORDING.md`) or becomes a guard, and this
file goes.

## Prefer the desk

- **A screen that only lists records is frappe's list, not an island.**
  The Recycle Bin was a Vue island over Deleted Document; frappe's own list,
  with Restore in its Actions, does the job. Build a bespoke screen only
  where it shows something a list can't.
- **A view of one kind of record split two ways is a field frappe filters
  by, not tabs, a page or a control we draw.** Announcements is frappe's
  Note list with a Status (Showing, Ended) marked as a standard filter, so
  frappe draws it in the filter row itself, colours it in the list, and the
  list opens on Showing by `listview_settings.filters`. Tabs, a redirect
  page, a window mechanism and a hand-drawn picker were all tried first;
  each was customisation nobody needed, and the drawn picker sat oddly in
  frappe's row.
- **As natural as possible.** Before drawing anything on a desk view, look
  for the frappe property that makes frappe draw it: `in_standard_filter`,
  `in_list_view`, `listview_settings.filters`, `get_indicator`.
- **Keep what frappe ships unless it is wrong.** The Note form's Edit mode
  stays. What we change is what doesn't fit One: the sign-in pop-up's two
  switches are gone, since announcements run along the top bar.
- **New records open in the window's create dialog**, not frappe's quick
  entry; it is ours, built on frappe's dialog.
- **A row that stands for a record opens that record.** Not an Edit button
  beside it: the row, its title, the whole card.

## Sections

- **Groups on a page need no separator lines.** Dashboards' groups are
  spaced, not ruled (`Section bare`).
- **An app's name heading what belongs to it wears the app's mark.**
  Dashboards' OneCRM, OneBook... headings draw the mark as a sentence does
  (`Section marked`, `Branded marked`).

## The window

- **A frappe node the window moves keeps frappe's look.** frappe scopes some
  styles to where it put the node (the filter count's pill lives under
  `.page-form`); moved into the window's controls, "Filters 2" read
  "Filters2". Every move the window makes is checked against the scss that
  styled the node in its old parent, and the rule follows it in
  `css/one_interface/frame.css`. A guard can list each node `window.view` moves
  and the frappe selectors that scope it.
- **Read-only JSON is a tree** (`js/one_interface/json_view.js`): any Code or JSON
  field that can't be edited and holds JSON folds by level, inks values by
  kind, counts what a level holds, finds a key or a value at any depth,
  copies a row, shows the path under the pointer, unfolds JSON inside a
  text, and shows the stored text on Show Raw. An editable one keeps
  frappe's code editor. What only shows data is never branded
  (`brand.LEAVE`).
- **No hand-made controls.** Buttons are `frappe.ui.button` (outline on a
  gray strip, ghost for a row's icon), inputs are frappe's `form-control`.
  A segmented switch, a drawn search box or a bare `<button>` is a custom
  primitive.

### Sections are space, not lines

A section ends with space, never a rule. Our two Section components draw
none (`.one-shell-section`, `kit/Section.vue`), and inside our dialogs
frappe's line above a settings heading is taken off (`module_settings.css`).
A list's rows keep their dividers, within the list only.

An empty list is not drawn: a bordered list with no rows is a line across
the page (AICenter's One, before its jobs list was taken out when it had
none).

### A choice you can see is a card

When each choice has a picture (a record type's avatar, a style, a mark),
it is a card in a grid, and clicking it opens its picker, saved as it is
picked. A list row is for text and a switch.

### A rail row opens a screen

A rail row is a place: a list, a page, a board. What opens a dialog is not a
rail row, with one exception: One's rail ends with Centers, a row per centre.
Where each centre opens, and how a module adds to it, is READY's
(`docs/READY.md`, mechanism 18), not this file's.

A group whose rows each need their own icon is a heading section (`indent`
0); frappe draws no icons under an indented one. A centre's name on a rail
row goes without One's mark, since the row's icon stands beside it
(`brand.CENTER_ICONED`).

### One switch per thing agreed to

Optional services stay separate switches when the code keeps them separate:
their own key, company and agreement (`one_legal/services.py`). Gravatar and
Google's logos are two; under one heading, Profile Discovery. Wherever a
service is switched, it is TrustCenter's own switch (`onedesk.trust.switch`).

### A home holds what only its app sees

An app's home shows what that app alone can gather. One's Home is the
approvals from every app, the announcements, what is new in each app and,
for an administrator, the workspace at a glance; tasks, meetings and
documents stay on their own apps' homes.

### Dashboards are where their app is

Each app's dashboards are Overview rows on its own rail (OneHR's shape: one
at the top, the rest first in their group). Making and changing them is
OneStudio's (Dashboards, Charts, Number Cards); no page lists them all.

### OneAI is a button that does one thing

An OneAI button does one thing in place (`onedesk.oneai.action`): violet,
OneAI's mark, opening a small popover beside it that asks what it needs and
shows what it wrote, to Use or Try Again. It never opens the panel. Each
app declares its actions in its `ai.py` (`ACTIONS`, named in hooks.py's
`one_ai_actions`), and AICenter lists them under the app with a switch.
A button that only asks the panel a question goes, as we walk each screen.

### A page keeps its app's rail

A page of an app (OneCalendar's calendar) keeps the app's rail rather than
drawing a left column of its own, and what it lets a person pick from (the
calendar's layers) is a section of that rail, under the rows (`window.tree`,
with `section` rows and `check` rows inked in their own colour). Its own
button goes first in the command row, then how to move through it, then its
views at the right. Nothing the rail already has is repeated on the page.

### Ways in are tiles, not rows

A handful of parallel things a person checks and acts on (Sign-in's
password, two-factor and passkey) sit side by side as tiles, each with its
state as a badge and its one action. A list row is for many of a kind
(sessions, sign-ins).

AccountCenter › Sign-in shows the standard liked: calm borders, no
separators, one action per thing, badges for state, words a person says,
and what is weak said plainly on an alert (`onedesk.alert`). Tiles are
`.os-ways` / `.os-way` in account_center.css. It is a standard of quality,
not a layout to copy: a page takes tiles only where it has a few parallel
things.

## Where the walk stands

Paused on One to move the portal into OnePortal, which is done (one_portal/,
not ready, 1.0.0). Nothing of the walk is committed yet; it all goes in
with the gates at the end.

- **AccountCenter, Profile**: Check My Profile gone; Write My Bio is the
  first OneAI action (one_ai/actions.py, one_account/ai.py, job `bio`).
  Sign-in's Is My Account Safe? is gone:
  the page says what is weak itself (signin.warnings), above a tile per way
  in (Password, Two-Factor, Passkey), then the sessions; This Device and
  Sign Out read frappe's hashed session ids; New Phone resets the
  authenticator (signin.reset_two_factor); turning two-factor on names the
  authenticator entry after the workspace (control.py).
- **AccountCenter, People**: apps in one line (AccountSection.apps_said),
  a Sign-in column (signin.way_in), no second People heading; a person's
  side says how they sign in, and Actions has Reset Two-Factor
  (signin.forget_two_factor, notification Two-Factor Reset: frappe's
  reset_otp_secret enqueues its mail with `retry=3`, which rq refuses).
  The demo's builder is faisal@one.test, not admin@example.com.
- **AccountCenter, Devices**: company devices (sorted ones) as the main
  list, Other Browsers under it, a device opened by its row with Lost and
  Retire at the dialog's foot (no buttons on rows), Passkeys blank at none,
  unnamed browsers forgotten after 30 days (devices.FORGET_DAYS).
- **ControlCenter**: General split into Company, Branding, Region and
  Formats, Sign-in and Sharing (one/control.py HOLDS), each loading and
  saving only its own fields; "general" stays as all of them for the demo.
  Company's Address in Mails starts as the address and follows it until
  someone writes their own. Branding is its three plain fields.
  Region and Formats says Global Defaults' two Disable switches the right way
  round (Rounded Totals, Totals in Words); turning one off had been refused
  by layer.py's property-setter guard, which now lets Global Defaults' own
  print_hide/hidden through (`flags.one_amounts`). Sign-in is six tiles on
  the form's own sections (`{ row: { stack }, css: "os-tile" }` after a
  heading with a mark), two to a row, drawn to AccountCenter's Sign-in
  standard: grey icon, medium-weight name, a state badge at the end (Off,
  On, Any password, 170 hours, After 10), controls a size down, and no
  field label that only repeats the tile's name. A tile is a border and the
  content's own weight; anything heavier reads as a shadow. Switches are
  tiles too, not a list of rows (Region and Formats' Amounts: three tiles and
  a sample of a sale's total that follows them); `OneSection.tiled` draws
  both. A switch on a page always means "on shows it" (Currency Symbol, not
  Hide Currency Symbol). Liking tiles on one page is not a reason to
  put them on the next: Branding tried tiles with previews and was worse than
  its three plain fields. Each page on its own merits.
  Lists: each list has its icon and its own count word (lists.py ICONS,
  COUNTED); opened, its siblings are their own Lists section of the nav pane
  above Centers (the tree's `heading` and `alone`), the crumb is Lists, and
  Home is not lit for it. Address Template lost its Country column (the name
  is the country) and its ID filter.
- **HelpCenter and UpdateCenter**: One first, then the apps, then the
  centres that are modules (AccountCenter, TrustCenter, as the rail names
  them: `module_settings.AS_CENTER`, shared with NotificationCenter and
  AccessCenter); only the first branch open; a long page name wraps.
- **AICenter**: OneAI, Reading, Knowledge, Summaries and Usage at the top;
  Apps; Yours (Memory, What It Reads). No OneAI dot on every setting or
  job; Reading's month is frappe's figures in one row; empty Memory and an
  unconnected Usage are quiet lines; Workspace Knowledge shows in Memory only
  to whoever can't open Knowledge; Help in the corner.
- **TrustCenter**: Companies is a card per company (its safeguard under
  its name, each use with what it receives and where; an unused one greyed,
  not struck through); Requests is its own page, counted while some wait;
  agreements carry no icon and a long name wraps; a version reads as its
  revision, the hash on hover; an empty Changes is a quiet line; Help in
  the corner.
- **AccessCenter**: the same shape. Roles and Profiles and Audit Log at the
  top with no heading, then one row per app under Apps, Roles, People and
  (where the app gives access on one record) On One Record chosen in its
  head; New Role beside the Roles list's search; People rows a row's height
  with frappe's avatar; an empty On One Record is a quiet line; Help in the
  corner.
- **NotificationCenter**: one row per app under Apps (Other for the
  workspace's own rules), each with frappe's TabButtons in its head, Yours
  and Workspace, for an administrator; no bell on every row; a Workspace row
  opens its words, and who it goes to is said there; AccountCenter and
  TrustCenter are named and drawn as the rail draws them. Words and Rules
  lost its panel buttons (Ask OneAI, Rewrite with OneAI); "Blue means on by
  default" is the list's own note. Every centre's and Help's Help and
  arrows sit in the dialog's top right corner (`dialog.$corner`, `help` on
  module_settings.Dialog), so the sidebar's head keeps its width for the name.
- **AccountCenter, Plan and Credits**: not connected to its account, one
  yellow alert, what was last known (or nothing but the alert), no actions,
  invoices or ledger; the side names the workspace as the top bar does;
  seats, storage, database and credits are four tiles (the Sign-in tile,
  figure first, a bar against the limit, Nearly Full/Full badges), each with
  its own buy button for an administrator of a connected workspace (Add
  Seats/Storage/Database open Add to Plan narrowed to that kind); no Links
  group in the side; a "0" limit says no limit and draws no bar. The demo keeps an account
  snapshot (one_demo/plan.py, step `plan`).
  Then: Middle Name, Preferred Contact Email, Education and Past Work
  (editable), Your Documents (editable; kinds by country, papers.offered;
  OneAI's reading replaces a renewed one in place), Contract End and
  Notice in Employment; User and Employee kept in step both ways
  (one_account/sync.py). Profile then split into Profile, Personal Details,
  Work and Documents (center.PROFILE_PARTS), and Documents shows Your Files,
  the person's Employee room, where a row's scan moves on save
  (center._file_scans, namespace.may_add). A file request can fill any file
  field on a record or in its tables, by the row's Kind, asking the row's
  other plain columns with the file, OneAI filling them when reading is on
  (one_storage/targets.py); what is asked of you is on Home, Asked of You
  (file_requests.asked_of, send_mine, guess): one load, each part saving only
  the fields it shows. A field's action sits on its label row
  (`.one-field-head`), never floated against the field.
- **Done on One**: Dashboards left One for each app's rail and OneStudio;
  Home rebuilt (approvals, announcements, New in Your Apps, The Workspace);
  Centers rows each with their own icon; Announcements as
  frappe's Note list (Status filter, Stop Showing, Show Until, Seen By);
  Recycle Bin as frappe's Deleted Document list (Restore); the JSON field
  viewer (`js/one_interface/json_view.js`); the Address Book as frappe's Contact
  and Address lists (no ID or Status column on Contacts); one Portal
  dialog on a document, a customer, a supplier and a contact.
- **OneCalendar**: the calendar keeps OneCalendar's rail, with the layers
  as Mine and Workspace under it; New Event, Today, the arrows and the date
  in the command row and the views at the right; All Events, Deadlines,
  Subscribe and Setup left the page (the rail and ControlCenter have them).
  Event's list has no ID column or box, Starts On as a column and Open in
  blue; its Subject is a short box. A maintenance visit is titled with the
  visit and the customer. Deadlines lost About (the title says what it is,
  Rule why it falls then) and its filter reads Found In. Calendar Feed reads
  Calendar Link. How Do I Add It? and the second Calendar Link heading left
  the settings. The demo's weekly meetings are one repeating event each
  (and Layla has one). `events._rows` no longer narrows every later event to
  the first record one was shown through. frappe's Google Calendar and
  Google Contacts sync is gone: closed to everybody, its fields hidden on
  Event and Contact, off the rail, and out of the privacy notice.
  Then through READY, 1.0.0: its own Help, tour, foot and settings, its
  notification kinds in its folder, and one ability, Put Events on
  Everyone's Calendar, a OneCalendar Manager's (Mariam in the demo) in
  place of the list of roles in events.py. A phone opens on Day, not a
  seven-column week; the grid names days and hours in the reader's
  language (frappe's calendar passes `locale` too), and Mine is translated.
  The tour's step over the grid sits in its middle, not off the top.
- **OnePortal, walked** as Khalid (customer) and Rami (supplier), on a
  phone and in Arabic, and from the desk as Layla. An invoice paid in parts
  said "26 days overdue" beside "Due 10-02-2027", the last part's date: its
  details now list each part still to pay (portal.py `_record`). Addresses
  was empty for a customer with a billing address, since frappe's portal
  list is only what the reader made: a kind may now read its own records
  (`found`), and One's addresses add those kept for their customer or
  supplier, read-only. Timesheets came out in the order last touched; they
  are newest first, titled by their day. An ended record's total no longer
  repeats its state under it (the head says it). On a phone, a money tile
  takes the row and the grid packs the rest (`grid-flow-dense`), and a
  Needs You row is the link, its button only on wider screens. A path that
  isn't the reader's says No access instead of spinning. In Arabic a date
  beside words came out backwards; dates are isolated (U+2068/2069), and
  erpnext's "لا" for the unit Nos is corrected ("قطعة"). On the desk, People
  shows each contact's sign-in state as frappe's indicator, Links lost its
  Answered On column so the record fits, and both lists lost the ID filter.
  The Data Processing Addendum now says what a one-record link does.
  Seen and left: erpnext's own customer overview counts an invoice as
  overdue only by its last part's date ("Overdue AED 0" beside OneBook's
  AED 113,810 in the side panel).
- **OneTask and OneProject, walked** as Samir (who runs projects), Mariam
  (who reads their money) and Layla, on a phone and in Arabic and German.
  My Tasks drew a column of its own beside OneTask's rail, with the same
  rows; the column is gone, Add Task is the page's button, and My Tasks,
  the task page, the project page and a template's page all keep their app's rail;
  a template's task names, narrower for it, end in an ellipsis and read in
  full on hover. With the
  rail and the record panel both there, frappe's form column (held at
  `flex: 1 0 80%`) pushed the panel past the window's edge; the column now
  shrinks (frame.css). Needs You on a project cut its rows to "Get the
  contr…" to keep a column for "20 days late"; how late now rides under the
  name. A task's Expected Time cut its placeholder to "Set H" (and
  "Stunden festlege"); the box is as wide as its words until there's a
  number. On a phone, every list's Filter and Sort stacked frappe's mobile
  toggle over their buttons and took two rows; they sit in one. A comment
  button said "Just Comment"; it says Comment Only. Seen and left, both
  frappe's own Arabic on every record: "2 weeks ago" reads
  "قبل 2 أسبوع /أسابيع", and the record panel's "Last Edited By" isn't
  translated at all.
- **Record pages on OneInterface.** A project, a task, an item and a
  project template are islands, and they had kept the layout from before the
  window: their tabs inside the page under the head, an Activity and a Files
  tab of their own, the sidebar with a Files row and Last Edited By / Created
  By under it, no details switch, and a task's Start Timer at the far right.
  They are laid out as a form now (onedesk/one_interface/AGENTS.md, A record page): tabs
  in the view row, the status pill in the address row, buttons in the command
  row, Activity in the record panel beside Mail, files behind OneCloud's mark,
  who changed it in the status. The item page keeps OneInventory's rail, and
  its print, like and OneCloud sit beside its name.
- **OnePortal is on the rail** with its own mark (`brand/oneportal.svg`):
  People (Contact filtered on its Portal column) and Links (the Portal Link
  list), a foot and settings. Turned off in Apps it closes the portal
  (`one_portal/gate.py`) and every Portal button goes.
- **Pictures**: One's settings › Pictures picks a DiceBear style per record
  type (`one/avatars.py`), drawn locally; records with no picture are filled,
  drawn ones redrawn on a change, the rest never touched.
- **Contacts and Addresses, second pass**: Contact's mail-reply Status
  hidden on the form too (frappe's own field, property setter); the Emirate
  shown only on a UAE address (`one_book/custom/address.json`).
- **At the walk's end, legal**: Your Data's clause (one/legal.py) still
  says "under You › Profile › Your Data", a path gone since AccountCenter.
- **At the walk's end, legal**: OneAccount's clauses (one_account/legal.py)
  gain what the walk added: an administrator sees how somebody signs in and
  can reset their two-factor, and a browser nobody named is forgotten after
  30 days; a company device can be marked lost or retired. One clause edit
  moves the revision hash and everybody agrees again, so they go in together,
  once.
- **At the walk's end**: pytest, demo checks, `docs.py`, translations into
  ar and de for every new string, version bumps for One and OneAccount
  (both ready), and the tests and docs that still name the removed islands
  and pages (test_tiers, test_shell ISLAND_PAGES, screens.mjs,
  test_outside, test_announcements, ISLANDS.md, ATLAS, MODULES.md), the
  tokens in frame.css's filter pill, one/checks.py reading the rail from
  its JSON, test_tiers for contact_list and test_interface_frame for json_view; a fix
  version for OneMail (theirs.py's import moved), One's version for the
  portal clause leaving its legal.py, and ar/de for OnePortal's new
  strings and its name (its picker line, the Portal column and its three
  states, the link states, People, Links, the closed-portal sentences and
  the Help pages) and for Pictures (its tab, note, None, the record types,
  the Help section), and for Home's new words (The Workspace, People, Apps,
  Storage, OneAI Credits, New in Your Apps, All Announcements, New
  Announcement, its tour), Write My Bio (its button, ask, Write, Writing…,
Use, Try Again, the AICenter row under One and its about), Profile's new
words (Education, Past Work, Your Documents and its note, Expired: {0},
{0} on {1}, education, past work, documents, Personal Details, Work,
Documents, Private, Your Files and its note, Plan's words (the tiles: Add Seats, Add Storage, Add Database, Buy Credits, Nearly Full, Full, no limit, of {0}, left, the three tile sentences, {0} used in the last 30 days, {0} reserved, {0} expire on {1}, Credits Ledger and its note; the two not-connected sentences), paying in the page (Billing Details, Buy {0} Credits, Paid. The credits arrive in a moment., Card saved. The next invoice is paid with it., Couldn't load the payment form. Check the connection and try again., Opening payment…, Back, Publishable Key and its description, ControlCenter's tabs (Company, Branding, Region and Formats, Sign-in, Sharing, their abouts, Contact, Address, Amounts, The Frame, A Letter Head, Rounded Totals, Totals in Words and their descriptions, Two-Factor, Passkeys, Email Link, Passwords, Sessions, Lockout, On, Off, Any password, After {0}, Currency Symbol and its description, Shown, Hidden, Lists' 1 country and {0} countries, Pictures' From the Web and its new about (Where pictures of contacts, customers and others come from: the web, or drawn for those with none.), Start Again's sentence (Deletes every sale, purchase, stock move, project, payslip, lead and asset. Customers, items, people and settings stay.), A Sale's Total, Grand Total, Rounded Total, In Words: {0}, {0} One Thousand Two Hundred Thirty-Five Only), the plan card: Billed to {0}, {0} Plan, a month, {0} seats, {0} storage, {0} database, 1 add-on, {0} add-ons), Devices' words (Other Browsers and its note, Browser, Make a Company Device, the empty company list, the Retire confirm), People's words ({0} in every app, {0} in {1}, {0} in {1} +{2}, Standard apps, Passkey, Two-Factor Not Set Up, Password Only, Signs In With, Reset Two-Factor and its confirm, Two-factor reset, the Two-Factor Reset notification, Two-factor sign-in is off for the workspace.), Sign-in's tiles and warnings (Two-Factor, New Phone, Turn On for the Workspace, Asked for when you sign in without a passkey., the two failed-password sentences, Your password has never been changed and you have no passkey., the reset confirm and alert, On {0}.), Home's Asked of You and its tour, NotificationCenter's Apps, Other, Whose, AccessCenter's Show, AICenter's Memory, What It Reads, Handled, TrustCenter's Greyed where your workspace doesn't use it., What the workspace's own rules tell you., Whether you're told at all, by email, and on this device.
step, Due {0}, {0} asks for this in {1}., OneAI is reading it…, Send, Sent,
Choose a file to send., This request is closed., {0} takes only {1}., {0} is
needed., Fill in what's marked as needed, then send again., the request
dialog's Saved To and the item's Saved To and Kind fields and their
descriptions, {0} has no file field called {1}., {0} has no kinds to pick
from., {0} is not one of {1}., {0} has a kind but no place on the record., and the four parts' abouts), the Country field on ID
Document Types and its description, and the rails' Overview rows and OneStudio's
  Dashboards, Charts and Number Cards; then this file folds into the UI contract and its
  guards.

### The arrows in a centre's corner enlarge it

The arrows in a centre's top right corner (module_settings.js `module_head_expand`)
make the window larger for reading, and back; the choice is remembered in the
browser and every centre, Help and What's New included, opens at it. They
used to jump to the whole of the centre, which nobody expected; the whole of a
centre opens from One's rail. A centre with no module foot (AccountCenter,
NotificationCenter) keeps a Help button beside them.

### OneInventory and OneBook, walked

Both walked as their people (Karim, a Stock Manager; Huda, an Accounts
Manager; the workspace administrator), on a phone, and in Arabic and German.
Their screens already sat on the window; what the walk changed:

- **A tour's first step had nothing to point at.** `window-nav` was drawn
  only by a view's own tree in the nav pane, so on a rail module (OneProject,
  OneTask, and now these two) the first step was skipped without a word. The
  pane itself carries the mark now (frame.js `nav.setup`), and every tour
  starts where it says it does.
- **Plant Floor's main button opened another page.** Shop Floor was the
  primary command; it is in the ··· menu now and New Workstation, on this
  floor, is the button.
- **Settings' Help said what the dialog doesn't have.** Neither module has an
  OneAI row in its settings, and both have Lists; the pages say so.
- **The item's shortage row was a sentence as a heading.** It says "{0}
  short" now, and opens Selling as before.
- On a phone a record page's tabs sit in the page under its figures, as they
  should: the window's view row belongs to the record panel, which a phone
  doesn't have.

### OneCRM and OneHR, walked

Walked as Omar (a Sales Manager), Mariam (an HR Manager) and Tariq (an
employee), on a phone, and in Arabic and German. Their Homes and records
already sat on the window; what the walk changed:

- **A module's settings opened on nothing.** With no Lists of their own, the
  dialog's first row was Notifications, which opens another centre and has
  no body, so Tariq saw an empty panel. A dialog now opens on its first row
  that has a body, and when none does the cog opens that first centre
  itself (module_settings.js `open`). OneHR's settings had also turned
  anybody who wasn't an administrator away with an alert; everybody gets
  them now, and only Holidays stays the administrators'.
- **HR's tour described HR's figures to everybody.** An employee's Home
  shows the leave they have left, so the step says both.
- **German called two employee tabs by the wrong words.** "Joining" and
  "Exit" read "Kommen hinzu" and "Verlassen", borrowed from a group's
  members coming and going in OneStudio; they are Eintritt and Austritt as
  ERPNext says, and OneStudio's group card says Added and Removed.
- **A heading was a sentence.** The holiday list's warning says "Ends {0},
  in {1} days".

### The full walk of OneCRM, OneBook, OneInventory and OneHR

Every rail entry, its list, a record and the reports, as each module's roles
and on a phone. What it changed in the parts every app shares:

- **A name with a % in it opened on nothing.** The address row decoded a
  record's name a second time, and "UAE VAT 5% - SGA" threw before the form
  drew (crumb_switch.js).
- **The command row led with the wrong button.** A button an app marks
  `btn-primary` and a solid group now lead as a solid button does, and where
  nothing is solid frappe's Create group leads (window/views.css, form.js).
  A draft whose main verb is One's (Approve on a leave application) is
  finished by it, so frappe's Submit and its "Submit this … to confirm" line
  are not offered beside it (head.js).
- **A phone's head took four rows.** It takes three: where you are and
  search; the record's name and pill; then Refresh, the view's search and its
  commands in one row, a submitted record's Cancel at the end of it.
- **Figures stood one to a row on a phone**, and a record's figures ran off
  the right edge. Two to a row, the number a size smaller; a record's grid
  stacks over its figures below 900px.
- **A report's status row carried frappe's filter hint and the query time.**
  It says how many rows there are, the total row aside. A tree's Expand All
  and Collapse All sit in it as the bar's own small buttons rather than
  floating over the rail's foot. Money columns are wide enough for an amount
  in the millions, dates for a date, and the row number for the count of rows.
- **A page reached by its address came up under OneHR.** frappe sends what no
  rail lists to the sidebar with the most entries, which for anybody with an
  employee record is OneHR. It opens under One's own rail now, and a page or
  record of an erpnext or hrms module opens under the app One keeps that
  module in (`one_module_heirs`, now with hrms's modules and Regional).
- **The rail lit Home for pages that weren't Home.** A row whose page moves
  its address (Mark Attendance), and a list opened from Home's Setup, lit
  Home because every address in the rail begins with it. The row clicked
  stays lit, and a page opened from another keeps that page's row. A page
  that changes its address in place (Home's tabs) relights the rail.
- **Lists took you out of the app.** Its row opened One's Home to show the
  dialog; it opens over the page you are on, and isn't drawn for somebody
  with no lists in that app.
- **Check In on a desktop asked to register a passkey "on this phone".** On a
  desktop it says to check in from your phone; on a phone it is a titled
  dialog with Register Passkey.
- **A dashboard's table was Bootstrap's grid.** hrms's Allocated Leaves (and
  a job applicant's interviews, the opening invoice tool) drew a bordered
  table with a line round every cell and raw green; any `.table-bordered`
  in a form's dashboard is drawn as frappe-ui draws a table (desk.css).
- **A dashboard block that came late stayed in the body.** The panel took
  frappe's dashboard blocks when the form drew; hrms's Allocated Leaves, a
  batch's Stock Levels and an asset's Maintenance Log arrive after a call of
  their own and were left above the form. The panel now watches the
  dashboard and takes each block as it lands, and a table in it is set small
  and fitted to the panel's width.
- **A batch's Move and Split were cramped.** erpnext lays its stock levels
  out as three columns for a full-width form; in the panel each warehouse is
  one ruled line, its name taking the room, then the quantity and the two
  buttons.
- **Panel blocks said things twice.** A customer's and a supplier's stats
  carried frappe's "Stats" heading over rows that name themselves; an asset
  showed an empty "Graph" under the head's own value chart; a work order's
  progress bars repeated its track; an asset maintenance schedule's log
  printed each count under its name and repeated the head's Completed. In
  the panel the stats heading goes, frappe's graph stands down where the
  head draws a chart or where it drew nothing, its progress bars stand down
  under a track, the log's counts are rows like the head's, and the head no
  longer counts what the log does.
- **OneTask and OneProject on the window.** Walked again after their record
  pages moved onto OneInterface. My Tasks and Inbox now name themselves in
  the address row rather than saying OneTask, drop the heading that repeated
  it, and fill the window as a list does; on a phone the new task's date
  takes its own line. A record panel left with one tab (a task's Activity)
  loses the bar of one icon. Project Progress counted only tasks erpnext's
  nightly job had marked Overdue, and said 0 beside seventeen late ones; it
  counts by end date now. Timesheet Billing Summary showed a Projects
  Manager the billed money and 0 billing hours (erpnext hides the hours and
  leaves the money's copy readable); a Projects Manager reads timesheet
  billing now. Workload dropped a stale assignee that is no user.
- **My Tasks is frappe's board.** OneTask's own page (an island grouping
  the reader's tasks by when they were due) is gone; My Tasks and the Inbox
  are two Kanban Boards on Task by status (one_task/board.py), each narrowed
  to its reader, the Inbox to what has no project. One adds an add bar over
  them and a play button on every task card; filters, grouping, settings,
  the per-column + and dragging a card to Completed are the board's own.
- **A board lost the window's command row.** Its Add and menu sat on the
  right with frappe's own layout: the window waits for frappe's Kanban
  class with a setter on frappe.views, and the board scripts (OneTask's and
  OneProject's) each put a setter of their own on the same name, the last
  one replacing the window's. onedesk.interface.when now keeps every waiter
  and calls them all; the board scripts wait through it, and a guard
  refuses another setter of their own. OneTask's add field goes in the
  command row through the window's `commands`, beside Add Task, instead of
  a bar of its own.

## 2026-10-29 — A task opens on its form

The task page (TaskPage, TaskTime, TaskFiles, page task_view, task_actions.js)
is gone. A task opens on frappe's Task form: one_task/heads.py puts its due
date and lateness, checklist, what it waits on and hours against plan in the
panel's Overview, and Complete Task is the head's primary verb. Weight and
Color are hidden; Issue and Is Template show only when set. On a phone the
form's buttons are in ⋯, as on every form.

## 2026-10-29 — Switching screens holds, then fades

Opening an app's home for the first time showed the old screen vanish, then
about 0.4s of empty window and 0.5s of Loading before it drew; the rail never
moved and nothing reloaded. public/js/switching.js wraps frappe's router in a
view transition: the old screen stays until the new one has drawn (an
island's shadow root holds no `.one-loading`, at most 900ms), then fades in
140ms. The rail and the two bars are named so they stay put.

## 2026-10-31 — Adding a news source, as it shipped

News went out with its guards green and the job of adding a source never
done in a browser by someone allowed to do it. The screenshots were taken
as Karim, who can't add a source, so neither button below was on screen
until Yamen asked to see it. The copy was telegraphic as well (see
WORDING.md, What is out). That much was missed with every guard passing.
This is what a person adding a source sees, and none of it is acceptable.

**New News Source** (the window's create dialog over the News Source form):

- A rail on the left holding one tab, Details, and the title "New News
  Source" in small grey type above it. A third of the dialog explains
  nothing, and the heading says "Details" when it should say what is being
  made.
- The question that decides everything, what kind of source this is, is
  the second field, a dropdown defaulting to Feed. Picking Google News
  swaps half the form underneath. Four kinds that each work differently
  are four cards with a line each, asked first.
- Source is required before the address, although a feed names itself.
  Paste the address first and fill the name from the feed's title.
- Only a feed's exact RSS address works. People have the site's address
  (thenationalnews.com), not `/arc/outboundfeeds/rss/...`, and nothing
  finds the feed from the site.
- Nothing shows what the feed contains before saving. Read it once and
  show its newest three headlines under the address, or the error.
- Enabled, Website, Fetch and Items to Keep all show on a record nobody has
  saved yet. Enabled is always on, Website fills itself in, and the other two
  have sensible defaults. They belong on the saved record, not in the way of
  making one.
- The Feed section's note is indented away from its own heading, and the
  right column is empty under Website, so the form is a narrow strip
  down the left of a wide dialog.
- The library is a separate button on the list, so someone who opened
  New never learns it exists.

**From Library**:

- It runs off the bottom of the screen: 60 rows, no scrolling inside the
  dialog.
- It opens on the first 60 business feeds alphabetically, from a US
  list: Hacker News, a venture blog, and podcasts (EconTalk, HBR IdeaCast,
  How I Built This), which are not news. A workspace in Dubai sees nothing
  near it until it searches. Open on the workspace's country and language.
- Duplicates (Feld Thoughts twice, same site) and raw feed titles
  ("Fortune | FORTUNE", "Blog on Feld Thoughts"). The library needs
  cleaning, not just copying.
- Text rows with no logo, in a product whose News is built around logos.
- Category and Country are empty dropdowns with no "All" in them.
- No way to see a feed's headlines before adding it, and one Add at a time
  for something people pick five of.
- The ownership notice sits first, above Search, with a rule under it,
  before anyone has done anything.

**The Sources list**: a Status column reading Enabled on every row, an ID
column repeating the name, and the Google News name cut off. On an
administrator's list there is a primary Add and a From Library button side
by side, two ways to do one thing.

### The rules this leaves

- **Walk the job as the person who does it, before calling it done.** Sign
  in as someone with the role, click the button they would click, and finish
  the task. A screenshot of a record that already exists says nothing about
  making one.
- **A create dialog asks the deciding question first**, as cards when the
  answer changes what follows, and shows only what is needed to make the
  record. The rest is on the saved record.
- **A dialog with one section draws no section rail.** Its heading says
  what is being made.
- **Take what the person has.** A site's address, not the feed's; a name
  read from the source, not typed.
- **Show what you'll get before it's added**: a few headlines, a preview,
  the error.
- **A picker opens on what is near the person** (their country, their
  language), scrolls inside itself, shows each choice's face, and lets
  several be picked.
- **Shipped lists are curated, not imported.** No podcasts in a news
  library, no duplicates, names cleaned.

## 2026-10-31 — A weather place, and what a small form is owed

Three fields (Place, Units, Default Place) opened in the full-height settings
dialog with a rail, and the location button sat on the field as a bordered
button of its own. Both were the same mistake: drawing the thing before asking
what frappe already draws for it.

- **An action inside a field is frappe's `.link-btn`**, the icon a Link field
  shows for its open arrow, not a button laid over the input.
- **A create dialog sizes to its form** (window/form.js `SMALL`): no tabs and
  at most six fields to fill is a 36rem dialog, one column, as tall as its
  fields, with no line under the last section above the foot's own.
- **What is filled for the person is not shown to them while making it.**
  Region, country and coordinates are hidden on a new place and read-only on
  a saved one, where they say which of five Dubais it is.
- **An autocomplete's rows need distinct values.** frappe's Autocomplete finds
  a row by its value, so five towns called Dubai drew as one and filled in
  Uganda's.

## 2026-10-31 — Switching screens no longer holds

The hold above froze the window on every app switch: measured from a rail
click to a window that takes clicks again, 0.9 to 1.8s with it and 30 to 140ms
without, because its readiness check rarely matched and it ran to its 900ms
cap, and a view transition takes no input while it runs. The next screen now
draws in 40 to 170ms on its own, so switching.js and its view-transition
names are gone.
