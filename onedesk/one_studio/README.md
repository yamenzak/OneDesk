# OneStudio

Written by hand. What OneStudio does and how to use it. Everything above
**Under the hood** is written for the people who use it, and OneAI reads it to
answer "how do I…" questions. Under the hood is for the people who build it.

OneStudio is where workspace administrators adapt One to their business.
Describe what you want to OneAI, and approve the card it makes. Nothing
changes before that.

Only workspace administrators see OneStudio.

## Finding your way

**OneStudio** in the dock opens it. The rail has:

- **Extensions**: scripts that make a form or page behave the way you need.
- **Custom Fields**: every field your workspace added or changed.
- **Custom Collections**: what your workspace keeps that no app came with.
- **Setup**: Numbering, Printing and Approvals, which open OneStudio's
  ControlCenter on that tab.
- **Automation**: Automations, Reports by Mail, Webhooks and Webhook Calls.

## Extensions

An extension makes a form do something it did not: refuse to save a customer
without a mobile number, fill in a field from another, warn when a discount is
over a limit, hide a field until another is ticked.

**Asking for one.** Click **Add Extension** and tell OneAI what you need, or
just say it in OneAI anywhere: "Stop an invoice being saved
without a purchase order number." OneAI writes it, a second check reads what
it wrote against what it says it does, and you get a card saying what it
does. **Approve** turns it on. Nothing runs before that.

**Where it runs.** On the **screen**, it runs in the browser of whoever opens
the page, with their own permissions. On a **form** it can show, hide, fill in
or require a field, add a button, and tell the person something. On a
**list** it can label records (a red **Overdue**), change how a column reads,
and add a button. It can also look up another record to do it, as the person
would, but never change one from the screen. On the **server**, it runs whenever the record is saved, submitted,
cancelled or deleted, whoever does it and however: the form, an import,
OneAI, another app. Use the server for a rule that must always hold.

**On One's own pages.** An extension can also run on One's own pages, each
with its own few things it may do:

- **OneMail**, when a conversation is opened: show a note under it ("A key
  customer"), or add a button beside Reply. And whenever a message is
  written, anywhere in One: show a note above it, or fill in its subject, cc
  or bcc.
- **A record's head**, each time the record is opened or saved: add a button
  beside the head's own, a figure in its band ("Sales Invoices: 12"), or a
  note under it. Only on the kind of record you name. One written for a
  Project runs on its page too.
- **A project's page**, when it is opened and each time the project changes:
  a note or a button under its header.
- **OneCalendar**, when an event's card is opened: show a note on it, or add
  a button.
- **OneTask**, each time a view of your tasks is shown: a note or a button
  under its name ("4 of your tasks are overdue").
- **OneCloud**, when a file is chosen: a note or a button under its preview.
- **Reading**, when a document is opened in the inbox: a note or a button
  under its head.
- **The pipeline board**, each time what a stage is worth changes: a note
  above the board.
- **Every space's home** (One, OneCRM, OneHR, OneBook and the rest): a note or
  a button above its blocks.

Ask for one the same way: "When I open a conversation from anyone at
acmeco.example, show a note that they are a key customer." It is reviewed,
off until you approve it, and its errors are written down, the same as any
other. It never sees more of the page than what it is given, and it starts
running for each person the next time they load One.

**On a schedule.** An extension on the server can also run on its own,
every hour, day, week or month, or on a schedule you give ("each weekday at
eight"), at most once an hour: "every morning, add a comment to each open task
whose end date has passed." It works on the records it finds, not on one being
saved, and only on kinds of record you may open yourself.

**Checked before you see it.** Before an extension is kept, OneAI's code is
checked for what would make it fail: every field it names must be one the
record has, every form event it uses must be one that forms really have, the
screen code must read as JavaScript, and it must be one change, not a hundred
lines of them. Code for the server is also run once on one of your records and
undone straight away, so an error shows now rather than on someone's next
save, and OneAI is told what it did ("it stopped the save, saying…"). Whatever
is wrong goes back to OneAI, which mends it before anything reaches you.

**What you see, and what you do not.** Each extension opens on whether it is
**On** or **Off** (or **Refused by Review**, or **Cannot Run Here**) and what
it does, then when it runs, what was asked and by whom, and its review. You do
not see its code, and nobody in your workspace writes or changes it by hand,
so there is nothing to type and no Save: OneAI writes it, and to change one you
press **Change this one…** on it and say what ("make it apply only to new
customers"). OneAI reads the code it has now and changes only what you
asked, keeping the rest as it was; it is reviewed again, and it stays off
until you approve it. Changing where or when it runs counts as changing it.

**Turning one on and off.** **Turn On** and **Turn Off** at the top of the
extension. One the review refused cannot be turned on; ask OneAI to change
it. Deleting an extension (**…** at the top) takes it away for good. The other
administrators are told when one is turned on, turned off or deleted, and by
whom: from that moment it runs on everybody's work, or no longer does.

**When one goes wrong.** An extension that runs into an error does not stop
anybody's work: on the server the record still saves, on the screen the form
goes on working. The error is written down, **Errors in the Last 7 Days** counts
it, and every morning the administrators hear of the extensions that ran into
one. The extension's **Errors** tab lists them: when, on which record, and what
went wrong in one line, since OneAI last wrote it. Press **Fix With OneAI**
at the top of the extension: OneAI reads the code and its errors, and a few
minutes later tells you what went wrong and that it has written a fixed
version, reviewed and off until you turn it on. Or ask **Has this one run into errors?**
in OneAI, or turn it off. An extension can also go wrong without an error:
one that never does its work logs nothing. Tell OneAI what it does wrong,
such as "Create Call Task never makes the task", and it fixes it the same
way. A message an extension means to stop a save with,
such as "A customer needs a mobile number", is not an error: it stops the
save, as it says.

**What an extension may not do.** Read or change what you could not; reach
outside your workspace (no mail, no calls to other services); change the
system's own records or One's; run more often than once an hour. OneAI says
so when what you ask needs one of these, and offers what it can do. For
something that tells people, an **Automation** is the way.

**Server extensions** run only on workspaces where they are turned on. If an
extension says **Cannot Run Here**, ask us.

## Custom Fields

**Custom Fields** lists every field your workspace added to a form or changed
on it: the field, its form, its type, and the other forms it was also added
to. **Added** marks a field the workspace made, **Changed** a standard field
it changed. Filter by form, status or app, or search by name. **Custom
Fields** on a form's own menu opens the list filtered to that form.

- **Add a field**: click **Add Field** and tell OneAI what you need. It asks a
  few questions, recommends the field type and properties, suggests related
  forms that need the field too (for example Item fields on invoice and order
  items), and makes one card to approve.
- **Change a field**: click it. OneAI asks what to change.
- **Export or Reset**: tick fields, then choose from **Actions**. Reset
  removes everything the workspace changed on those forms.
- **Restore a field**: a removed field is in One › **Recycle Bin**. Restoring
  it brings back its values too.

See Customizing a Form in One's documentation.

**Who sees and changes it.** Workspace administrators only, on the forms they
can open, and never the framework's own forms or One's. A change applies to
everyone who opens the form. The other administrators are notified
(**Form Customized**).

**OneAI** on the list says which forms were changed and how, or changes the
one you name. On a form it adds a field step by step, suggests changes as one
card, says what was changed and which extensions run on it, or explains how
customizing works. A check no field setting can say, it offers as an
extension.

## Custom Collections

A custom collection is something your workspace keeps that no app came with:
memberships, vehicles, rooms, contracts, inspections.

**Adding one.** Click **Add Collection** and tell OneAI what you keep, for
example "the vans we keep: registration, make, mileage, the date we bought it
and whether it is in use." OneAI designs its fields and shows a card with its
name, app and fields. **Approve** creates it.

**Where it is.** In the rail of the app it belongs to, in the group you choose:
one the rail already has, such as **Sales** in OneCRM, or a new one. Without a
choice it goes under **Your Records**. People who use that app create and edit
its records, and its managers delete them. A collection in **One** is for
everyone.

**Moving one.** Tick it and click **Actions › Move**, then choose the app and
the group. Its records stay as they are, and the people who use them follow
the app.

**Opening one** opens its records.

**Field types.** Text, numbers, money, percentages, dates and times, checks,
selects, phone numbers, ratings, durations, files and images, and links to
records you can open or to another collection. The first text field is each
record's title.

**Numbering.** Each record gets a number from the collection's initials, such
as CV-00001 for a Company Van. Change it in Setup › **Numbering**.

**Changing one.** Tick it and click **Actions › Change**, or ask OneAI, for
example "Add a colour to Company Van." A removed field is hidden, not deleted, so no
data is lost.

**Deleting one.** Delete its records first. A collection that still has
records can't be deleted. A deleted collection is in One › **Recycle Bin**, and
restoring it brings back its records list.

## Numbering

How each record type is named when a record is created. For example, an
invoice `ACC-SINV-2026-00006`, a customer by its name, or a project by its
title. Only administrators see this, and only for record types they can open.

The list shows every record type you can open that uses a naming series, a
naming method the workspace chose, or naming rules:

- **Naming Rule**: how a new record is named.
- **Series**: the series or expression.
- **Next**: the exact name the next record gets, where it can be known.
- **Document Naming Rules**: how many naming rules it has.

Click a row to open that record type's **Settings › Numbering** (see A Form's
Settings), where you make changes. The list refreshes when you close it. **Set
Up Naming** lets you choose any other record type and opens it there. While
you type a series or expression, the window shows the next name it would give,
or what's wrong with it.

You can also ask OneAI, for example "number our invoices by year", "start
this year's quotations at 500", "name projects by their title", "give
government customers their own prefix" or "is any numbering behind?". OneAI
suggests the change as a card, and nothing changes until you approve it.

### Changing how invoices are numbered

The same steps work for quotations, orders or any record type with a series.

1. Open Setup › **Numbering** and click the **Sales Invoice** row.
2. Click the series to change, or **Add Series** for a new one.
3. Type the series, such as `INV-.YYYY.-.####`. The window shows the next
   name it would give, or what's wrong with it.
4. Tick **Default** so new invoices start with this series.
5. To start from a higher number, set **Current Value**. It can only go up.
6. Click **Update**, or **Add** for a new series.

Existing invoices keep their names. Only new ones use the change.

### Writing a series

A series is parts separated by dots, read left to right.

- Text stays as written (`INV-`, `SO/`).
- `YYYY` is the year (2026) and `YY` its last two digits (26). `MM` is the
  month, `DD` the day, `JJJ` the day of the year and `WW` the week of the year.
- `FY` is the fiscal year (2025-2026) and `TFY` its short form. `ABBR` is the
  company's abbreviation.
- `{department}`, or a field's name on its own, inserts that field of the
  record. `timestamp` inserts the time the record is created.
- The number is one `#` per digit, after a dot. `.#####` gives 00001. Only the
  first run of `#` counts.
- The number restarts whenever the text before it changes. `INV-.YYYY.-.####`
  restarts at 0001 each year, and `INV-.YYYY.-.MM.-.####` each month.
- Only letters, digits, spaces and `- / _ . # { }` are allowed.

**Series Format**, in the edit window, explains the same.

A series another record type already uses is refused, so two record types
never share numbers. You can move a series' number up, for example to start a
new year at 1000, but never down, and never below the highest number a record
already has. The edit window shows that number. Each change is kept in the
record's history.

### Choosing how a record type is named

**Name each new ... by**, at the top of Numbering, sets how a new record gets
its name, with these options:

- **Naming Series**: the next name in one of its series, for record types that
  have them.
- **Field**: the value of a field you choose, such as a project's title or a
  vehicle's plate. The field becomes required and unique. It's refused while
  two records share a value, and the message names that value.
- **Expression**: a pattern written like a series, such as `PRJ-.YYYY.-.####`,
  for record types with no series of their own. The window shows the next name
  as you type, and **Use This Expression** applies it.
- **Set by User**: the person creating the record types its name. Not offered
  for record types One creates in the background, such as expense claims
  OneHR files or timesheets from the timer, since no one is there to type a
  name. These can be named by a field only if that field is always filled in.
  Records OneAI creates from a document aren't limited this way, since OneAI
  reads the name or field from the document.
- **Random**: a random name, for records no one refers to by name.

**Customer**, **Supplier**, **Item**, **Employee** and **Campaign** have their
own naming options: Customer Name, Naming Series or Auto Name, an Item by its
Item Code, and an Employee by Full Name or Employee Number. The series list
and **Add Series** appear only while the record type is named by a series.

Changes never rename existing records. They apply only to records created
afterwards. Switching back to a series continues from the number it had
reached.

The naming method can only be changed on record types people create
themselves. Ledgers, logs, and the system's and One's own record types are
named by the system. Rules work on all of them.

### Naming rules: a prefix for some records

A rule gives a record its own prefix when its fields match, whatever its
naming method. For example, returns as `RET-.YYYY.-`, or government customers
as `CUST-GOV-.YYYY.-`.

1. Click **Add Rule**.
2. Enter the prefix, written like a series but without `#`. The window shows
   the next name it would give.
3. Set how many digits the number has.
4. Under **When**, add conditions, each a field, a comparison and a value. All
   of them must match. A rule with no conditions names every new record.

When two rules match, the one with the higher **Priority** wins. Rules only
check the record's standard fields.

## Printing

How the workspace's documents look on paper: letter heads and print formats,
each below. Only administrators see this, and only formats for record types
they can open. Print headings are in OneStudio's ControlCenter, under
**Lists**.

### Letter heads

A letter head is the header and footer of every printed page. Each letter head
shows as a card with a full page, as it prints. The star makes one the
default. Click a card to open it. The letter head window has **Header** and
**Footer** tabs on the left, each a list of presets with its options under
it, and the page on the right. Pointing at a preset shows it on the page;
clicking keeps it.

**Edit in Builder** opens the letter head in the print format builder
instead, where the header and footer are each an image or HTML. A header or
footer edited there stays as written. Choosing a preset again replaces it.

**Default** prints a letter head on every document unless another is chosen.
**Disabled** keeps it but stops offering it. The workspace's standard letter
heads can be made the default or disabled.

### Letter head headers

The header uses one of thirteen presets, filled in from One's ControlCenter (Company and Branding):

- **Classic**: the logo on the left, the company stacked on the right.
- **Columns**: the logo on the left; the address and contacts in columns
  under small grey labels.
- **Ledger**: the logo on the left; address, phone, email and tax number two
  by two under labels in the Brand Colour.
- **Strip**: the logo on its own, then every detail in a labelled row across
  the page.
- **Masthead**: the logo centred over three columns.
- **Centred**
- **Window**: everything top right, leaving the left free for the address a
  letter goes to.
- **Accent**: a short bar in the Brand Colour over the logo.
- **Wordmark**: with no logo, the name in large spaced capitals.
- **Minimal**: the name and contacts on one line.
- **Tinted**: the company on a faint tint of the Brand Colour.
- **Band**: a band in the Brand Colour, the name or the logo on it.
- **Logo Only**

A company with no logo shows its initials on the Brand Colour beside its
name. The name isn't repeated beside a logo unless **Name** is ticked, for a
logo that is only a symbol. A light Brand Colour is darkened wherever it is
text, so it still reads; lines and bands keep it as it is. A UAE company's
tax number is its **TRN**.

Under the presets:

- tick what it should **Show** (name, address, phone, email, website, tax ID)
- set the **Logo Height**
- turn on the **Brand Line**, a line in the Brand Colour under the header

When you change any of these details in General, including the Brand Colour,
every preset header and footer updates.

### Letter head footers

The footer uses one of nine presets:

- **Centred**: one line.
- **Two Sides**: the name and address on the left, the rest on the right.
- **Fact Strip**: each detail in a column under a small label.
- **Legal**: the name, address and tax number centred, contacts under them.
- **Accent**: a short bar in the Brand Colour over one line.
- **Corner**: the logo or the name on the left, the rest on the right.
- **Spread**: each detail in an equal share of the width.
- **Logo Above**: the logo centred above the line.
- **Tinted**: the line on a faint tint of the Brand Colour.
- **None**

A new footer shows the phone, website and tax number. Tick what else to
**Show**, including the **Logo**, add a **Note** of your own, such as "Thank
you for your business.", and turn on its **Brand Line** if you like. A new
letter head starts with the Centred footer.

The page number isn't part of the footer. It's part of the print format (Page
Number, in the builder), and it prints on every page.

### Print formats

This shows the same cards as a record's **Settings › Print Formats** (see A
Form's Settings). There's one group for each record type the workspace made a
format for, with the other formats it can print with. Click a page to preview
it, the star to make it the default, or the name to open it in the builder.

To add a format:

1. Click **New**.
2. Enter a name and choose what to **Start From**: a copy of one of the record
   type's formats, or all of its fields.
3. The format opens in the builder.

A format belongs to one record type. A printed record stays inside its app,
with that app's sidebar.

### Print formats One ships

Everything that leaves the company prints from a format of ours unless the
workspace chooses another: One Quotation, One Sales Order, One Sales Invoice,
One Payment Receipt, One Delivery Note, One Purchase Order, One Request for
Quotation, One Payslip, One Job Offer and One Appointment Letter. Each prints
under the default letter head, with its title and total in the company's
Brand Colour (One's ControlCenter › Branding). To change one, open it in the builder and
save a copy, which the star then makes the default.

Their blocks are in the builder's **Library**, for any format of the
workspace's own:

- **One Title**: what the paper is (an invoice, a credit note, a receipt) and
  its number. A Print Heading chosen on the record replaces it.
- **One Party**: who it's for, their address, contact and tax ID, and where
  the goods go when that's somewhere else.
- **One Details**: its dates and references, the ones that are set.
- **One Totals**: the subtotal, discount and each tax, the total, what's paid
  and still owed, the total in the company's currency when the record is in
  another, and the total in words.
- **One Payment Schedule** and **One Bank Details**: when it's due, and the
  company's bank account to pay into, its default one first.
- **One Payslip**: earnings, deductions and net pay.
- **One Payment**: the amount and the invoices it settles.
- **One Signatures**: a line for each side to sign, on a quotation, a
  delivery note, a job offer and an appointment letter.

### HTML blocks in a print format

In the builder, a format is made of the record's fields, tables, text, images,
barcodes, the standard field templates and **Custom HTML** blocks.

- An HTML block is a template of the record and nothing else. It can use the
  record's fields and rows (`{{ doc.customer_name }}`,
  `{% for row in doc.items %}`), `doc.get_formatted(...)`, conditions, loops,
  `_()` and plain filters.
- Every value is escaped. Scripts, forms, frames and images from other sites
  are removed. The same applies to a letter head's HTML, which can't contain
  template code at all.
- Images must be uploaded to the workspace.
- Typst blocks, formats written by hand, and styles that load anything from
  another site aren't available, since each would print exactly what's
  written, on the workspace's address.

### Designing a letter head or print format with OneAI

OneAI offers **Suggest a letter head**, **Tidy our footer**, **Design a letter
head from our details**, **Design a clean invoice format** and **Which format
do invoices print with?**

Each suggestion is a card an administrator approves. **See the Page** on the
card previews it first: a format on the record type's latest record, or a
letter head's header and footer.

- **Letter heads**: OneAI can change an existing header or footer as well as
  create one. Ask it to remove the footer's line or add a note, and only that
  changes. It can use any preset, or write HTML from the company's details,
  where `[icon:phone]` (any Lucide icon name) shows that icon in
  the Brand Colour.
- OneAI can also suggest the default letter head, and which format a record
  type prints with.
- **Model**: designing a format uses a stronger model than the chat, which
  One picks.
- **Checks**: a layout that would print badly, such as an empty section, a
  table wider than the page, or an invoice without its customer or total, is
  fixed before you see a card. If it still can't be fixed, OneAI says nothing
  was made.

### How OneAI lays out a print format

- **Print formats**: OneAI designs a format for any record type from the
  builder's own blocks, so it opens in the builder like any other. It uses an
  HTML block only for a part the blocks can't show, such as a stamp, a grid of
  terms or a figure calculated from the rows, or across the whole body for a
  page designed from end to end.
- **Layout**: it starts from a standard layout for the record type and changes
  only what you ask, so the same request gives the same result. For an
  invoice, quotation, order or bill, that's who it's for on the left, the
  dates on the right, the items in one table, the totals below next to the
  amount in words, and the terms last.
- **Style**: by default it uses a house style based on the standard print style,
  with small muted labels, space between sections, an items table under a
  soft header without a box, and the totals as label and figure on one line,
  with the grand total above a rule. A look you ask for, such as a colour, a
  band behind the title or a typeface, replaces the house style. A typeface is
  set with the format's Google Font setting.
- **Properties**: it can set any property the builder shows, by the
  builder's own name. That includes a section's background, padding, margin,
  radius, borders and when it prints, a field's size and colours, a table's
  style, which rows print and column widths, barcodes, images, repeaters, and
  the page's font size, margins and colours. You can keep editing all of it in
  the builder.
- **HTML blocks**: in the house style these use cards, large figures, status
  badges, stamps, tables and label and value rows, in One's own colours. They
  can only use the record's fields and rows, `get_formatted`, conditions, loops
  and plain filters.

## Approvals

An approval sets the states a record moves through before it's done, and who
moves it. For example, a purchase order stays Waiting for Approval until a
manager approves it, or a customer stays Pending until the accounts team
checks it. Only administrators see this, and only for record types they can
open. The system's own record types, such as users and roles, and One's own
can't have approvals.

OneAI offers **Approve bills by amount** and **Who approves what?** It
suggests a new or changed approval as a card you approve. The approval then
opens in the builder, laid out, to edit like any other.

A bill OneAI drafted waits in **Ready to Submit**. **Submit** takes
the approval's step when the step is waiting on your role. Otherwise it says
who it's waiting for. OneAI never takes a step itself.

### Adding an approval

Open Setup › **Approvals**, or a record type's **Settings › Approvals**.

1. Click **New Approval**, and choose the record type and a name.
2. In the approval builder, drag a state onto the page for each step.
3. Connect two states with an action, such as Approve or Reject, and choose
   the role that can take it.
4. Optionally, have a state set a field of the record, such as Status to
   Approved.
5. Click **Save**, then turn the approval **On**. Only one approval can be on
   for each record type.

People with the role see the action on the record. Each step waiting on their
role counts in **Approvals Waiting** on their Home. They're also notified in
One, and by email if they chose (**Approval Waiting** in NotificationCenter's Words and Rules), when a record reaches their step. Whoever made the
record, and whoever sent it to the step, hear where it went next (**Approval
Answered**).

### Conditions on an approval step

An action can have a **Condition** that compares the record's fields with
plain values. The same action can then go to different people depending on
the amount. For example, **Approve** by an accounts user when
`doc.grand_total <= 5000`, and by an accounts manager when
`doc.grand_total > 5000`.

- Write a field as `doc.` followed by its name.
- Compare with `==`, `!=`, `<`, `>`, `<=`, `>=` or `in`.
- Combine with `and`, `or` and `not`.

Conditions that do more, calculated values and tasks an action runs aren't
available here, since they'd run as whoever takes the action. A state can only
set fields that anyone who can edit the record could set.

## Automations

An automation runs by itself when a record is created, changed, submitted or
deleted, when a field changes to a value, on a date before or after one of the
record's dates, or on a schedule. Only administrators see this, and only for
record types they can open. The system's own record types, such as users and
roles, and One's own can't have automations. **Automations**, under
Automation, lists them all.

An automation applies to records that match its **Match Fields**, then runs
its steps in order. A step can:

- set a field
- add to a number
- create another record
- notify people
- assign the record to someone
- call a web address (https only)
- wait

A value can include a field of the record, such as `{{ doc.customer_name }}`.

An automation runs as whoever last saved it. Each step can only do what that
person could do by hand. Advanced conditions, If steps, scripts and calculated
values aren't available, since they'd run as code. How often automations can
run, and turning them all off, is managed by the platform team.

On the list, OneAI offers **Thank customers who pay** and **What runs by
itself?** It suggests a new or changed automation as a card. Once you approve
it, it runs as you.

### Adding an automation

1. Open Automation › **Automations** and click **Add Automation Flow**, or
   click **New** on a record type's **Settings › Automations**.
2. Give it a **Title** and choose the **Document Type**, the record type it
   runs on.
3. Under **Trigger**, choose the **Trigger Type**: when it runs.
   **Match Fields** limits it to the records it's for.
4. Under **Actions**, click **Add row** and open the row.
5. Choose the **Action Type**. Its own fields appear below, such as who to
   notify and what to say, which field to set and to what, or how long to
   wait. The record's creator and assignee are offered alongside your team.
6. Turn the automation **On** once it has at least one step.

**Tell People** notifies the people it names (team members, the record's
creator or its assignee) in One, and by email if they chose (**Automation
Notice** in NotificationCenter's Words and Rules). Give it a subject and
message, or a **Mail Template**. The template is filled in from the record the
same way the email window does it, with amounts and dates as the record shows
them.

**Test Run** runs the automation on one record and then undoes everything, so
you can see what it would do.

## Reports by Mail

Automation › **Reports by Mail**, or **Setup Auto Email** on a report's menu,
emails a report daily, weekly or monthly to the addresses you enter. The
report shows what the person who set it up can see. Only administrators
create them.

## Webhooks

A webhook notifies another system, such as Zapier, Make, n8n or your own
server, when a record is created or changed. Automation › **Webhooks** lists
them, and **Webhook Calls** lists every call each one made. Only
administrators see either.

**Adding a webhook**

1. Choose the record type and the event: created, changed, submitted,
   cancelled or deleted.
2. Enter the address the other system gave you.
3. Choose what to send. Either JSON with the record's fields, such as
   `{"customer": "{{ doc.customer_name }}", "id": "{{ doc.name }}"}`, or a
   list of fields, each under the name the other system expects.
4. Add a header if the other system needs a key. Turn on **Enable Security**
   to sign each call with a secret it can check.
5. Set **Max Retries** to retry a failed call, up to five times, waiting
   longer each time.

**Limits**

- A webhook must be on a record type you can open, and can only send fields
  you can read. For example, you can't send a salary above your level.
- It sends every record of its type on its event. To send only some, such as
  won deals, use an automation with a Call Webhook step.
- What it sends can only use the record's fields, as `{{ doc.field }}`.
- It uses https to an address on the public internet, never an internal one,
  even through a redirect.

**Webhook Calls** shows each call's record, what was sent, the response and
its status:

- **Delivered**
- **Failed**: it will be retried.
- **Exhausted**: no more retries.

Each morning, administrators are notified of any calls exhausted the day
before (**Webhooks Failing**).

OneAI offers **Are the webhooks working?**, and on the calls, **Why did these
fail?**

## Notifications

Every administrator is notified in One and by email, unless they turned it
off in their notifications:

- **Extensions Failing**: each morning, the extensions that hit an error the
  day before. Not sent when none did.
- **Extension Turned On**: when another administrator turns one on, with what
  it does and where it runs.
- **Extension Turned Off** and **Extension Deleted**: in One only, unless you
  turn on email.
- **Collection Added**: when another administrator adds a custom collection,
  with its fields and where its records are.
- **Collection Changed** and **Collection Deleted**: in One only, unless you
  turn on email.
- **Form Customized**: when another administrator changes a form or resets
  it, in One only unless you turn on email.
- **Extension Fixed**: when Fix With OneAI has mended an extension, to
  whoever asked.

No one is notified of their own change.

## Asking OneAI

On Extensions: **Write an extension…**, and **What do our extensions do?**,
which says what each does and whether any is failing. On an extension:
**Change this one…**; when it is on, **Has this one run into errors?**, which
reads what went wrong and on which record (never its code); when it is off,
**Why is this one off?** On Custom Collections: **Make a collection…** and
**Change a collection…**; on one collection, **Make a collection…** On
Custom Fields: **Add a field…**, **Which forms
have we changed?** and **How does customizing work?**

## Connections

- **From OneAI**: Extensions, custom fields and custom collections come from cards OneAI makes. Nothing changes until an administrator approves the card.
- **To One**: An extension can add a button or a note to a record's head and to every space's home. A custom collection is listed in its app's rail, and a deleted one goes to the Recycle Bin.
- **To OneMail**: An extension can add a note or a button to a conversation. It can also fill in a new message's subject, cc or bcc.
- **To OneCRM**: An extension can add a note above the pipeline board.
- **To OneProject**: An extension can add a note or a button under a project's header.
- **To OneCalendar**: An extension can add a note or a button to an event's card.
- **To OneTask**: An extension can add a note or a button under a view's name in My Tasks.
- **To OneCloud**: An extension can add a note or a button under a file's preview.
- **To OneAI**: An extension can add a note or a button under a document's head in the Intake inbox.

## Under the hood

### What it is made of

| File | What it is |
|---|---|
| `extensions.py` | The Extension record's rules, and frappe's Client Script or Server Script made from it as Administrator. |
| `guard.py` | Pure. Reads an extension's code before it is kept and refuses what reaches past the administrator. |
| `places.py` | One's own pages an extension can run on (OneMail, OneCalendar, OneTask, OneCloud, OneAI, the pipeline board, a project's page, every space's home, a record's head): each one's events, what it gives, and what it may do. `../public/js/places.js` runs them. |
| `checks.py` | Pure. Whether an extension's code would work: the field and handler names it uses against the record's own, and its length. |
| `trial.py` | Tries an extension before it is kept: node parses screen code; server code runs once on a real record, undone after. |
| `review.py` | The second reading, `studio_review`: a separate call shown the code and its explanation, nothing of the chat. |
| `record_types.py` | A record type's rules, and frappe's custom DocType made, changed and deleted from it. |
| `doctype/workspace_field` | Custom Fields: a virtual doctype read from the workspace's ledger, frappe's own list. |
| `forms.py` | Each form's app and counts, and the extensions on one form, for OneAI. What OneAI's card saves is `../one_studio/customize.py`. |
| `ai.py` | `write_extension`, `mend_extension`, `extensions_here`, `extension_code`, `extension_places`, `extension_mistakes`, `design_record_type`, `record_types_here`, on the `studio` action. |
| `mend.py` | An extension's errors, the Errors tab, and mending one from them (`studio_mend`). |
| `heads.py`, `legal.py` | The record heads, and what the Terms and the AI Addendum say. Extensions Failing and an extension turned on, off or deleted are in `notifications/one_studio/`. |
| `tell.py` | Every notification OneStudio sends: an extension turned on, off or deleted, the ones failing, and a collection added, changed or deleted. |

### How it is made

**Code a workspace never writes.** frappe trusts whoever writes a script,
because only its own managers may. Here an administrator never writes one:
OneAI does, `guard.py` refuses what no explanation excuses (imports, raw SQL,
`get_all`, `db_set`, `ignore_permissions`, frappe's flags, mail, requests,
jobs, a kind or a field the administrator may not read; on the screen, the
server, the network, markup and the browser's storage), and a second model
reads it against its explanation. That second reading sees none of the
conversation, so whatever the administrator said to the writer does not
reach it. An administrator can still steer the writer, which is why the
guard and the review are the line, not the writer's instruction.

**Code nobody on the workspace reads.** The code is on the Extension at
permission level 1, which only frappe's System Manager reaches, so frappe
leaves it out of the form, the list and the API. `write_extension.unshown`
keeps it out of the chat as it is streamed and kept (`tools.shown_args`).
Changing one is writing it again from what it does. A screen extension's code
is sent to the browser that runs it, so it is not secret from somebody who
opens their browser's tools; it is only nobody's to change.

**On only as reviewed.** An extension turns on only if its review passed and
its code, record, view and event are the ones that passed
(`review.fingerprint`, `extensions.reviewed_as`): the guard and the reviewer
read the code for one kind of record at one moment. `read_only` keeps a field
only in the form, so `extensions.validate` keeps what OneAI wrote (`WRITTEN`)
on the server too: through the API as anywhere else, an administrator turns
an extension on and off and nothing more. A server one turns on only where the
bench runs server scripts (`server_script_enabled` in
`common_site_config.json`, set on our benches when they are made).

**Wrapped, on the server and on the screen.** frappe's Server Script is the
code inside `try`: `frappe.ValidationError` (a `frappe.throw`) passes,
anything else is logged under `OneStudio: <name>`, and the save goes on.
frappe's Client Script is the code given its own `frappe`
(`guard.WRAPPED_ON_SCREEN`), whose `ui.form.on` runs each handler inside a
`try` and whose `throw` is marked as meant: a meant throw still stops the
save, anything else is sent to `extensions.tripped` (rate-limited, only for an
extension that is on and on the screen) and logged under the same name.
`failing`, the Errors tab and the count on the extension cover both.

**On One's pages.** frappe has no script for a page of One's, so a page
extension (`view` Page, `place` such as `onemail.conversation`) is no Client
Script: the extensions that are on, and still as reviewed, come with the boot
(`extensions.boot`, `one_page_extensions`), and `places.js` runs each once,
keeping what it listens for with `one.on`. A page says what happened
(`onedesk.places.emit`) with a copy of what it shows and its own functions
for what places.py lets that event do; the extension is lent only those, its
handlers and any function it hands back run inside a `try`, and what trips is
sent to `extensions.tripped` under its name. `guard.on_page` refuses code that
listens for an event its page does not have. Screen code may look a record up
as the person (`guard.LOOKUPS`: `frappe.db.get_value`, `get_list`, `count`,
`exists`), and frappe answers with that person's permissions; anything else on
`frappe.db` is refused. Text passed to `__()` is words on the screen, never
read as the kind of record of that name. A space's home is frappe's own
Workspace page: `places.js` wraps `Workspace.show_page` rather than editing it,
and lends a spot above its blocks (`onedesk.places.spot`).

**On a schedule.** A scheduled extension (`event` Every Hour, Every Day, Every
Week, Every Month, or Scheduled with `cron`, at most hourly by
`extensions.cron_refused`) is a Server Script of type Scheduler Event; frappe
makes its Scheduled Job Type, and stops it when the script goes. It runs as
Administrator with no `doc`, so `guard.on_server` refuses one that reads `doc`,
and its kinds are still held to what the administrator may open. Its wrapper
(`guard.WRAPPED_SCHEDULED`) logs an error under its name with no record.

**Checked before it is kept.** After the guard, `checks.py` (pure) reads the
code for what would not work: a field it names on `doc`, `frm.doc`,
`frm.set_value`, `toggle_*`, `set_df_property`, a lookup's fields and filters,
that the kind does not have (with the nearest that it does, by `difflib`); a
form handler frappe never calls; and code longer than `checks.LONGEST` lines.
`trial.py` then has node parse screen code (`node --check`, nothing run) and
runs server code once on the newest record of its kind the person may read,
inside a savepoint that is rolled back: an error refuses it, and what it did
(stopped the save with a message, changed these fields, nothing) is handed to
OneAI as `tried`. All of it comes before the review, so a refusal costs no
second reading, and goes back to the model as `mend`.

**Mending without reading.** `mend.py` is a separate call, its own action
(`studio_mend`), made on the server with the extension's code and its last
five errors (a server error's whole traceback, a screen error's message and
the browser's stack). It answers what went wrong in plain words and the code
mended; the code goes through `extensions.write` like anything OneAI writes,
and only the diagnosis comes back to the form or the chat. The button runs it
as a job (`mend.start`, two model calls are minutes, more than a request may
take) and tells whoever pressed it when it is done. Errors count from
`written_on`, when OneAI last wrote it: older ones are about other code. The Errors tab and
`extension_mistakes` show only the line of each error a person can read
(`mend.what_went_wrong`). A screen error carries the record it was open on.

**Record types are frappe's.** A custom DocType in module One Studio, made as
Administrator, with permissions written for the app's roles, and a place in
the app's rail through the sidebar layers `one_studio/reports.py` already uses for
saved reports. Fields are frappe's own kinds, nothing that runs.

### The plan

Done: Extensions, the review, Custom Fields, Custom Collections. Not built: a child table in
a record type, and extensions on API calls (`docs/BACKLOG.md`).

### ai.py

- `extensions_here` reads what the workspace has: each extension, where and
  when it runs, whether it is on, its review, and whether it ran into a
  error lately. No code.
- `write_extension` keeps what OneAI wrote, off, after the guard and the
  review (`extensions.write`), and makes a card whose Turn On does what the
  administrator would do in the list. A refused review comes back to the
  model to mend, under the same extension. The code it wrote is left out of
  the conversation as it is kept and shown (`unshown`), so it is in the
  extension alone.
- `extension_code` hands OneAI the code it is changing, so a change edits it
  rather than rewriting it from the explanation. Its answer's code is
  `unshown` too: the run reads it, the kept conversation does not.

Both run on OneStudio Extensions (`studio`), a stronger model than the
chat's, which is told what an extension may do.

### checks.py

`guard.py` says what an extension may do; this says whether what it does is
there. A model writing frappe code invents a field name, or names a handler
frappe never calls, and the code passes every review and then does nothing,
or runs into an error on every save. So the names the code uses are read
against the record's own fields, and what is wrong comes back to OneAI in
words it can mend from, with the fields that are there.

### extensions.py

An extension is one record of ours, **Extension**, and one of frappe's: a
Client Script for one that runs on the screen, a Server Script on a record
event for one that runs on the server. Ours holds what the administrator
reads (the title, what it does, what was asked and the review) and, at a
level only frappe's System Manager reads, the code; frappe's is made from it
here, as Administrator, since frappe keeps both to its own managers, and is
nobody else's to change.

- **Written only by OneAI** (`write`, called by its tool in `ai.py`), after
  `guard.py` has read the code and `review.py` has had a second model read it
  against what it says it does. Nothing it writes is on until somebody turns
  it on.
- **On only as reviewed.** An extension turns on only if its review passed
  and its code, record, view and event are the ones that passed
  (`reviewed_as`). Nothing OneAI wrote changes by hand (`WRITTEN`). One on the
  server turns on only where the bench runs server scripts at all.
- **Off and deleted by the administrator.** Off disables frappe's script;
  deleting the extension deletes it.
- **An error does not stop the work.** Every extension runs wrapped
  (`guard.wrapped` on the server, `guard.wrapped_on_screen` in the browser):
  what it means to stop a save with still stops it, and anything else it
  trips on is written to the error log under its name (in the browser through
  `tripped`) and the work goes on. `failing` tells the administrators each
  morning.

Who hears of an extension turned on, off or deleted, and of the ones failing,
is `tell.py`.

### guard.py

An extension is code OneAI writes, and nobody else. An administrator could
still ask OneAI for code that reaches past what they may do, so this reads
the code itself, as a second line after the review (`review.py`), and refuses
what no explanation would excuse.

**On the server** an extension is a Server Script on a record event, run in
frappe's sandbox as whoever saved the record. The sandbox already refuses
imports, files and the private parts of objects; this refuses the rest of
what it leaves open:

- writing past permissions: `db_set`, `db.set_value`, `ignore_permissions`,
  frappe's flags, deleting or renaming another record;
- reading past them: raw SQL, `get_all` (frappe's `get_list` checks), a
  password, and any field the administrator may not read;
- reaching outside: requests, mail, jobs, other scripts and whitelisted
  methods;
- naming a kind of record they cannot open, or frappe's or One's own, and
  naming one any way but as plain text, so every kind it touches is known.

**On the screen** an extension is a Client Script, which runs in the browser
of everybody who opens the form. It may change the form and speak to the
person; it may not call the server, store or send anything, or write markup.

`IN_THE_SANDBOX`, the names a server extension's code finds already there, is
frappe's safe_exec globals and RestrictedPython's builtins, as
`get_safe_globals()` answered on frappe develop (Oct 2026), and `print`, which
RestrictedPython turns into its own collector.

`WRAPPED_ON_SCREEN`: each handler a screen extension gives
`frappe.ui.form.on` runs inside a `try`, a `frappe.throw` it means still stops
the save, and anything else it trips on is written down
(`extensions.tripped`) and the form goes on. Its `frappe` is frappe's own,
with those two wrapped; everything else is frappe's.

### mend.py

An administrator never reads an extension's code, so they cannot read why it
fails either: the errors frappe keeps are about the code, line by line. So the
mending is a separate call, its own AI action (`studio_mend`), made here on
the server: shown where the extension runs, what it says it does, its code
and its last errors, and asked what went wrong, in words for somebody who
does not read code, and for the code mended. Nothing of the chat reaches it,
and nothing it is shown goes back to the chat: the conversation, and the
extension's form, hear the diagnosis and nothing else.

What it writes goes through `extensions.write` like anything OneAI writes:
the guard, the second reading, kept off. The mended version runs only once an
administrator turns it on.

### places.py

A frappe Client Script reaches a kind of record's form and its list, and
nothing else: OneMail, OneCalendar, OneTask, OneCloud, OneAI, the pipeline
board, a project's page, every space's home and the head of a record (on its
form, and on a project's page) are One's own, drawn by One's code. So each of
those says here, once, what happens on it that an extension may hear (its
events), what each event tells the extension (`gives`), and the few things
the extension may do there (`may`).

This is the whole contract. The browser runs only these events with only
these powers (`public/js/places.js`); `guard.py` refuses code that listens for
an event the page does not have; and OneAI reads it to know what each page
allows (`ai.py` `extension_places`), so what it writes and what runs are the
same list.

### record_types.py

A record type is frappe's own custom DocType (`custom`, module One Studio),
with a **Record Type** of ours beside it that the administrator reads: what
it is for, the app it belongs to, who asked. OneAI designs one from what was
asked (`ai.py`), and approving the card makes it here, as Administrator, since
frappe makes DocTypes for its own managers alone.

What a workspace's record type may be, whoever asks:

- plain fields of the kinds a form is made of (`FIELDTYPES`): text, numbers,
  money, dates, ticks, choices, files, and links to a kind of record the
  administrator may open, or to another record type. Nothing that runs:
  no code, no HTML block, no button, no condition on another field;
- a name that is not taken, by frappe, an app, or another record type;
- belonging to one app: its users make and change records of it, its
  managers delete them, and it is listed in that app's rail, in the group
  the administrator chose (one the rail has, or a new one), else under Your
  Records. One is everybody's.

Each record is numbered from the collection's initials, CV-00001 for a
Company Van, as the workspace's documents are, so the number a person sees
beside its title means something; Workspace > Numbering changes it.

Changing one adds fields, renames them and changes their choices; a field
already holding data is never dropped, only hidden. Deleting one deletes its
records, so it is refused while it has any.

Who hears of a collection added, changed or deleted is `tell.py`.

### review.py

OneAI writes an extension from what an administrator asked, so whoever asks
steers the writer. The reviewer is a separate call, its own AI action
(`studio_review`), shown the code, the explanation the administrator will
read, and where it runs, and nothing of the conversation, so nothing said
there reaches it. It answers Pass or Refuse with a reason. `guard.py` has
already refused what no explanation could excuse; this catches code that is
allowed but is not what it says: a check that also copies a field elsewhere,
a button that does more than its label.

An extension that has not passed, or whose code, record, view or event has
changed since it passed, cannot be turned on (`extensions.py`).

### trial.py

- **Screen code is parsed** by node (`node --check`), which reads it and
  runs nothing: a missing bracket comes back with its line, rather than as a
  form that silently has no extension. Where the bench has no node, nothing
  is said.
- **Server code is run once on a real record** of its kind, the newest the
  person may read, inside a savepoint that is rolled back: whatever it
  changed or made is undone. A scheduled one is run once as it will run,
  with no record, and undone the same way. What happened comes back to OneAI
  as it would on that record: it stopped the save with this message, it
  changed these fields, or it ran into this error, which refuses it.

Both come after `guard.py` and `checks.py`, so what is tried has already been
read for what it may do and for the names it uses.

### ai_setup.py

Each tool in ai_setup.py checks what it was asked against the same rules the
page does, and writes a card (an `AI Proposal` of kind Setup) that does
nothing until a person approves it. Approving runs the page's own code
(one_studio/reports.py, one/access.py) as whoever pressed Approve, so a card can do
no more than they could by hand. A card says in plain words what changes: a
level's card names every right it gives and takes away.

All of them run on Workspace Setup, the stronger model approvals and
automations run on.

### approvals.py

An approval is frappe's own Workflow: its states, the actions between them,
and the role each action is for, drawn in frappe's workflow builder. The
workspace administrator is given Workflow, Workflow State and Workflow
Action Master, and the builder page through frappe's Custom Role.

Frappe trusts whoever writes a Workflow, because only its System Managers
may, and a workflow can run code: a transition's condition is Python, a
state's value can be an expression, a transition can run tasks (a Server
Script's method among them), and the field the workflow keeps its state in is
written on every record of the kind. A workflow written by somebody frappe
does not let customize (layer.held) is held to this:

- it is on a kind of record they can open, never frappe's own or One's;
- its transitions run no tasks, and a condition only compares the record's
  own fields with plain values (`doc.grand_total > 5000`), so a bill over a
  sum can go to a manager without a line of code;
- a state sets a field only to a plain value, and only a field anybody who
  may edit the record may set (the first permission level, not the record's
  own bookkeeping);
- it keeps its state in a field of its own, which is made here the first
  time, as frappe makes it but as the workspace, since the administrator may
  not add a field by hand.

Every approval, the workspace's or not, is told through One's hub: frappe's
own mail to whoever a step waits on is off (`send_email_alert`), and
`waiting` tells them on the bell, and by mail as they chose, as Approval
Waiting. One made without the builder (by OneAI, or by code) is laid out for
it, since frappe's builder stacks every step it has no place for on one spot.

### automation_steps.py

Tell People tells people through the hub (one/notify.py), on the bell and by
mail as each chose, as Automation Notice, and fills a mail template in as the
composer does (one_mail/mail_templates.py). Frappe's Send Notification mails past
the hub, and renders a template with only `doc`, so a template that names the
record's fields bare, as the composer and the leave mails need, prints its
tags there.

### automations.py

An automation is frappe's own Automation Flow: a trigger, the records it
matches, and steps (set a field, make a record, notify, assign, call a
webhook, wait). The workspace administrator is given Automation Flow, and
it is listed in One's sidebar, so its list and form keep One's rail.

Frappe trusts whoever writes a flow, because only its System Managers may.
A flow runs as Administrator unless told otherwise, its condition and an If
step's are Python, every step's values are Jinja with frappe's globals, and
a step can run a Server Script. A flow written by somebody frappe does not
let customize (layer.held) is held to this:

- it runs as whoever wrote it, so each step can do only what they could do
  by hand, and frappe's own permission checks decide;
- it decides by its field rules, never by code: no condition, no If step;
- it runs no script;
- a value names a field of a record, `{{ doc.customer_name }}`, and nothing
  else (as one_mail/mail_templates.py holds a template);
- a webhook is sent over https (frappe already refuses internal addresses);
- it is on a kind of record they can open, never frappe's own or One's.

Automation Settings stays the operator's.

**Tell People** (`TellPeople`, one_studio/automation_steps.py) is One's own step,
added through frappe's `automation_actions` hook: it tells people through the
hub (one/notify.py), on the bell and by mail as each chose, as Automation
Notice, and fills a mail template in as the composer does
(one_mail/mail_templates.py), from the record's own fields. Frappe's Send
Notification mails past the hub and renders a template with only `doc`, so a
template named by its fields prints its tags; it is not offered to a
workspace's own flows.

### customize.py

What a workspace administrator changes on the Customize page is frappe's own
records, and one of ours:

- **Fields**: a field's label, whether it is hidden, required or in the list,
  and the order of them all, as **Property Setters**; a field of the
  workspace's own, as a **Custom Field**, which it may change again or take
  away. A field the record came with may be hidden, never removed.
- **Above the fields**: rows of the doctype's **Record Head** (one/head.py):
  numbers in the band, verbs a module registered, and linked sections
  (one/linked.py). A module's own rows are shown and kept; the workspace's are
  marked `custom`, so a migrate keeps them too.
- **Connections and buttons**: the DocType's own Links and Actions, marked
  `custom` as frappe's Customize Form marks them. A button there only goes
  somewhere; one that runs something is a verb.

Every row is written under `frappe.flags.one_workspace_layer`, so the holds in
one/layer.py read it as the workspace's, and it is saved against the state
the page loaded (`state`), so two administrators do not overwrite each other.
What frappe does not mark (a custom field, a property setter) the page writes
into a ledger, **Workspace Customization**, and **Reset** takes back what the
ledger names and nothing else: a module's customizations are never the
workspace's to remove.

### letter_heads.py

frappe keeps a letter head's top as HTML, and ERPNext's own reads the
company's logo, name, address and contacts from the document as it prints. A
workspace's letter head may hold no template (`print_html.letter_head_html`),
so its top is drawn in letter_heads.py instead: one of `PRESETS`, from what
Workspace > General keeps (the logo, the name, the company's own address, its
phone, email, website and tax ID, and its Brand Colour), showing what the
administrator ticked. The choice is kept on the letter head (`one_top`), and
the top is drawn again whenever the company or its address changes (`redraw`),
so a printed page always says what General says now.

The foot is drawn the same way, from `FEET` (`one_foot`, `draw_foot`). It
carries no page number: that is the print format's own (Print Format's Page
Number), which frappe draws on every page.

A top or foot written by hand, in frappe's builder, stays as it was written:
editing a drawn one there makes it hand-written (`apply`).

In `draw`, the logo's cell is as wide as the logo, so the company's lines have
the rest of the width and the address and the contacts each stay one line. It
is said in pixels: frappe's print style holds every letter head picture to its
cell, and a cell sized to its content would hold it to nothing.

### numbering.py

Frappe keeps this in Document Naming Settings, a Single whose whitelisted
methods change any doctype's series and run for anybody who can read it
(`run_doc_method` checks read, and `update_series` writes the property
setters itself). So the workspace administrator is not given that Single.
numbering.py's functions are the doors instead, each guarded to a doctype the
workspace may change and its administrator may read, and each calling
frappe's own logic: `update_series` validates a series and refuses one
another doctype uses, `NamingSeries` previews and counts.

The one thing frappe lets its System Managers do that numbering.py does not:
set a series' next number lower. Going down repeats a number already used, and
the save that meets it fails; going up only skips numbers, as a new year does.

`NAMED_BY` holds the kinds of record that name themselves in code, by one of
their app's own settings: the Single, the field, the method that shows or
hides the series and the name field to match (or None), and whether the code
reads the setting as a global default, which the Single's save would have
written.

`SERIES`, `FIELD` and `EXPRESSION` are how any other kind may be named, as
frappe's Customize Form offers it: the naming rule it records, and what it
writes as `autoname`. Frappe's Autoincrement cannot be changed to or from once
records exist, UUID changes how the name is stored, and By script is code, so
none is offered.

### print_blocks.py

Everything One submits prints from a format laid out in frappe's print format
builder (each module's `print_format/`, written by `scripts/print_formats.py`)
out of the builder's own pieces: fields, tables, linked fields, static text,
sections that show only when they say something. A workspace changes them in
the builder like any of its own.

A few papers are gathered from records the one printed doesn't hold, which the
builder can't reach. That part alone is one of One's blocks, frappe's own Print
Format Field Templates, standard in module One
(`one/print_format_field_template/`), so a workspace finds them in the
builder's Library; the rest of the paper is still the builder's:

- **One Statement**: a customer's or a supplier's account this fiscal year,
  from the general ledger: the opening balance, each document with the
  balance after it, how old what's open is, the open invoices, and where to
  pay. On **One Statement of Account** and **One Supplier Statement**.
- **One Salary Certificate** and **One Experience Letter**: the letter an
  employee asks for, dated today, with the monthly pay as their latest
  payslip made it up.
- **One Leave Balance**: each leave the employee has, on a leave
  application, as HRMS counts it.
- **One Total**: a payment order's total, which it doesn't keep.
- **One Progress**, with **One Title**, **One Party** and **One Details**:
  a project's status, the one paper still drawn wholly from blocks.

Each template (templates/one_print/) is drawn from `one_print_block`, which
says what to show; every amount is frappe's own formatting in the record's
currency.

Each record in `FORMATS` prints with One's format unless the workspace has
chosen another (`settle`), and ERPNext's own that One's replace (`REPLACES`)
are turned off.

### print_html.py

A printed page is drawn on this site's address, where a script runs as
whoever opens it, and a PDF is drawn by a browser on the server, which fetches
whatever the page points at. And an HTML block is a Jinja template, which
frappe renders with globals that read any table (`frappe.db.sql`,
`frappe.get_all`) and fetch any address (`make_get_request`). So what a
workspace administrator writes in HTML is held to three things:

- **The template reads the record and nothing else** (`check_template`): the
  record's fields and rows (`doc.grand_total`, `{% for row in doc.items %}`),
  `doc.get_formatted(...)` and `doc.get(...)`, conditions, loops, arithmetic,
  `_()` and plain filters. It is rendered in a sandbox of its own that holds
  only those (`render`), escaping every value, never in frappe's.
- **The markup is markup for paper** (`clean`): text, headings, tables, lists,
  images and links, with scripts, forms, frames, media and event handlers
  taken out.
- **Nothing is fetched from elsewhere**: an image is this site's file or an
  inline image, and a style may not import or point off this site.

A block the workspace saves is marked `one_sandboxed`, and onedesk's copy of
frappe's HTML block macro (templates/print_format/macros/HTML.html) renders a
marked block through `render`. A block frappe or its System Managers wrote is
unmarked and renders as frappe renders it. A letter head's HTML is rendered by
frappe as it is stored (printview.get_letter_head), so it holds no template at
all and is stored already cleaned.

### print_props.py

The properties are read from frappe's builder (public/js/print_format_builder:
field_properties.js, SectionPropertiesPanel.vue, TableFieldInspector.vue,
BarcodeRows.vue and the rest of the inspector) and checked against what its
renderer reads (templates/print_format/print_format.html, macros.html and
macros/*): a property the builder sets and the page never reads is left out,
and so is one the page reads that nothing sets. What each accepts is what the
builder's own control offers.

A value is checked in print_props.py for its shape; a style for what it may
load (`printing._style`), and a condition for its grammar. frappe runs a
condition in its own safe_eval with the record and the print settings, as the
builder's own do.

### print_recipes.py

OneAI designs a print format as the builder lays one out
(`ai.design_print_format`). Left to itself, two requests for the same invoice
came out as two different pages. So `print_layout` offers a starting layout
made from the kind's own fields, in the order a reader looks for them, and
OneAI changes only what was asked. The look is frappe's own print style with
`HOUSE_CSS` over it: the same page, spaced and toned the way frappe-ui draws
one, so it still reads like every other format the workspace prints. A format
made to a look somebody asked for carries their css instead, never this one as
well.

Two shapes cover what a workspace prints:

- a document of trade (an invoice, a quotation, an order, a delivery note, a
  bill): who it is for and where on the left, its dates and references on the
  right, the items as one table, the amount in words beside the totals, and the
  terms last;
- anything else: its main fields in two columns, each of its tables with the
  columns its list shows, and its long text last, each under its label.

Every layout is written as `ai.LAYOUT_HELP` describes: sections of columns of
blocks.

`HOUSE_CSS` is the house finish over frappe's print style, in frappe's own
classes and its grey scale: labels small and muted, room between sections,
tables lined rather than boxed under a soft header, the totals as label and
figure on one line and the grand total set off above them. Sizes are em, as
frappe's are.

### printing.py

The formats are frappe's own: Print Format made in frappe's print format
builder, and Letter Head. The workspace administrator is given both, and the
builder page, through frappe's own Custom DocPerm and Custom Role. What is
held in printing.py is what a printed page may carry when somebody frappe does
not let customize wrote it (layer.held), because the page is drawn on this
site's origin, where a script runs as whoever opens it, and a PDF is drawn by
a browser on the server:

- **A format is made in the builder.** No hand-written HTML format, no raw
  printing, no JS format, and in the builder no Typst block, which reads
  files. An HTML block is allowed as print_html.py holds it: a template that
  reads only the record, rendered in a sandbox of its own, its markup cleaned.
  Everything else the builder offers (fields, tables, text, images, barcodes,
  a standard field template) is escaped by frappe's own macros.
- **Styles are styles.** A format's CSS goes into a `<style>` element as it
  is, so it may not contain markup, `@import`, or a URL that is not this
  site's file or an inline image; a block's own style, likewise.
- **A letter head is a picture or plain HTML.** Its top and foot are each a
  picture, which frappe turns into its own markup, or HTML with no template in
  it, stored cleaned (`print_html.letter_head_html`). The header and footer
  scripts stay frappe's System Managers'.

A standard format stays frappe's (it refuses changes outside developer
mode); a workspace copies it in the builder and changes the copy.

`DESIGNER` is the workspace's own format frappe's builder opens to design a
letter head on: the builder draws a format's letter head above and below it,
top and foot, each a picture or HTML. It is kept off, so nothing prints with
it, and out of every list of formats.

### reports.py

Three things, each frappe's own:

- **Saved reports.** A list's Report view, saved under a name, is frappe's
  `Report` of type Report Builder. Anybody may save one (frappe offers Save As
  to everybody, and its `save_report` only ever writes that type), and it goes
  in the sidebar of the app whose list it was: for everybody when a workspace
  administrator saved it, in the person's own sidebar otherwise, through
  frappe's own sidebar layers (`Custom Sidebar`). Deleted, it leaves.
- **Dashboards.** frappe's `Dashboard`, of its `Dashboard Chart` and `Number
  Card`, which a workspace administrator makes. Everybody sees them under One >
  Dashboards, and frappe shows each chart only to who may read what it counts.
- **Reports by mail.** frappe's `Auto Email Report`, which a workspace
  administrator sets from a report's menu (Setup Auto Email).

What frappe trusts to whoever may customize it, and a workspace does not get:

- a report of any type but Report Builder. A Custom Report runs the report it
  is a copy of with no check of who may open that one, and frappe leaves
  Script and Query reports to its Script Manager already;
- a chart or a card of type Custom, which runs code an app wrote and is free
  to read past the reader's permissions;
- a report by mail that runs as somebody else.

erpnext's own dashboards are its modules' (Accounts, Stock, CRM), with a
company on every chart, each on its own app's rail. OneStudio › Dashboards
is where a workspace makes and changes them.
