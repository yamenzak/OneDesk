# Records, Reports and Dashboards

## Reports

Saved reports, dashboards and reports by mail each belong to an app. Only
administrators create dashboards and reports by mail. Script reports, Query
reports, copies of them, and charts or cards that run code can't be made
here. Those come with the apps.

OneAI offers **What do our dashboards show?** and **Which reports go out by
mail?**

You can also ask OneAI for a saved report ("unpaid invoices over a thousand,
largest first, in OneBook"), a dashboard or a report by mail. It shows a card
with the columns, filters, charts and recipients. When you click **Approve**,
it creates it as you, so it can't create anything you couldn't. Anyone can ask
for a saved report of records they can read. Dashboards, reports by mail and
reports shown to everyone are for administrators.

## Saving a Report

1. Open a list's **Report** view from the view switcher at the top right.
2. Set its columns, filters, grouping and totals.
3. Choose **Save As** from its menu.

The report appears under **Saved Reports** in the sidebar of the list's app,
such as OneBook for invoices or OneCRM for customers.

- If an administrator saves it, everyone who uses the app sees it. Otherwise
  only the person who saved it sees it.
- **Show In…** on the report's menu, also offered when you save, moves it to
  another app or takes it out of the sidebar. An administrator can also choose
  between only themselves and everyone who uses the app.
- Whoever saved it can change it and delete it, and nobody else can but an
  administrator. Deleting it from the report's menu removes it from the sidebar.
- A saved report shows each person only the records they can read.

## Dashboards

A dashboard is a page of charts and number cards, such as invoices by month
or how many are unpaid.

- Each app's dashboards are on its own rail, as **Overview** rows.
- Administrators make and change them in OneStudio › **Dashboards**, with
  its **Charts** and **Number Cards**.
- Each chart and card shows only to people who can read what it counts.
- A chart counts, sums or averages records, groups them, or shows a report.
- **Show In…** on a dashboard's menu also lists it under Dashboards in an
  app's sidebar, for the administrator only or for everyone who uses the app.

## Customizing a Form

Every field your workspace added or changed is listed in **OneStudio ›
Custom Fields**. **Custom Fields** on a form's menu opens the same list,
filtered to that form. Only administrators can open it. You don't edit
anything on the list. Ask OneAI instead, and approve the card it makes.
Changes apply to everyone who uses the form.

The list shows each field's form, type, status and the other forms it was
also added to. **Added** is a field the workspace made, **Changed** a standard
field it changed (renamed, hidden, made required, shown in list view).
Numbers, buttons, charts and linked sections above a form's fields, and
connections, are changed through OneAI too. Extensions are in OneStudio ›
Extensions.

## Adding a Field

Click **Add Field**, or ask OneAI from anywhere, for example "add a field to
Item". OneAI asks a few short questions and recommends an answer for each.

1. What the field is for.
2. The field type and properties: required, unique, default, list view,
   filters, depends on, fetch from, length and validation (email, phone, URL,
   non negative). A check that no property covers, such as comparing two
   fields, becomes an extension.
3. Whether related forms need the field too. For example, a field on Item
   usually belongs on Sales Invoice Item and Purchase Order Item, fetched from
   the item.

OneAI then makes one card with every change. **Approve** applies them all, and
the other administrators are notified. OneAI won't add a field the form
already has.

## Changing a Field

Click a field in the list, or tell OneAI what to change. You can rename, hide,
require, move or remove a custom field. Standard fields can be hidden but not
removed, and fields the form needs stay required.

## Export and Reset

Tick fields in the list, then choose **Export** or **Reset** from **Actions**.
Export downloads this workspace's changes to their forms. Reset removes them
all, including fields added to related forms. If someone changes the form
after OneAI made a card, the card can't be applied and says so.

## A Form's Settings

**Settings**, on a form's or a list's menu next to Customize, shows what the
workspace has set up for that record type. Only administrators see it. Each
part appears once the workspace can use it.

- **Numbering**: how a new record is named (a series, a field, an expression,
  set by user or random) and its naming rules. For a record type with series,
  it lists the series, with the default first, and the name the next record
  gets. **Add Series** adds one. Click a series to edit it or move its number
  up. A number only goes up, since going down would repeat a name already
  used. A series another record type uses is refused. OneStudio's
  **Numbering** lists every record type with a series that you can open, and
  opens each one here.
- **Print Formats**: every format this record type can print with, each shown
  as a page. Click a page to preview it, the star to make it the default, or
  the name to open it in the print format builder. **New** creates one from the
  record's fields and opens it in the builder. The workspace's standard formats
  can be printed with or starred, but not changed. To change one, open it in
  the builder and save it under a new name.
- **Notifications**: the workspace's notification rules for this record type.
  Opening one, or clicking **New Rule**, opens it in NotificationCenter's
  Words and Rules, set to this record type.
- **Mail Templates**: the email templates for this record type. **New**
  creates one, and clicking one opens it. **Set as Default** makes the email
  window start with it. See Mail Templates, for the Workspace.
- **Approvals**: the approvals for this record type. **New** opens the
  approval builder set to it. Click one to edit it or turn it on or off. See
  Approvals, for the Workspace.
- **Automations**: the automations for this record type. **New** opens a new
  automation set to it. Click one to edit it or turn it on or off. See
  Automations, for the Workspace. The system's own record types, and One's,
  have none, since they have no Customize.

## Printing a Record

Open the record and click the printer icon at the top, choose **Print** from
its menu, or press Ctrl+P (Cmd+P on a Mac). The print page shows the record
as it will print.

- **Print Format**, **Letter Head** and **Language**, at the top, choose how
  it looks. The workspace's defaults are chosen to begin with.
- **Print** sends it to your printer.
- **PDF** makes a PDF copy to download or send.
- **Full Page** opens the printed page on its own.
- The file icon, **Form**, goes back to the record.

Every PDF is listed in the Audit Log, under Exports and Prints. How formats
and letter heads look is set in OneStudio's **Printing**.

## Reminders

**Remind Me**, in a record's menu (Shift+R on a form), reminds you of that
record later.

1. Choose **Remind Me In**: 30 minutes, 1 hour, 4 hours, 1 Day, or
   **Custom** to pick a time under **Remind At**.
2. Add a **Description** if you like, such as what to do.
3. Click **Create**.

When it's due you get a **Reminder** notification that opens the record. It
comes by email and push too, as you chose in NotificationCenter.
