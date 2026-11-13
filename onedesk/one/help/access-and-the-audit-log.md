# Access and the Audit Log

## Access

People gives each person a role in {one_crm}, {one_book}, {one_inventory}, {one_project},
{one_hr} and {one_mail}. **{access_center}**, on {one}'s rail, is where roles are made and
changed, with profiles, groups and user permissions, each below. Only
administrators see it.

A record type's **Settings › Access** shows what each app's roles can do with
that record type, and opens any of them to change it.

{one_ai} offers **Who can do what?** and **Who sees only part?**

You can also ask {one_ai} to set things up, for example:

- "a role in {one_crm} that can't delete quotations"
- "a profile for bookkeepers"
- "a group for the Gulf sales team"
- "limit Rania to the UAE territory"
- "remove Omar's access"

{one_ai} shows a card listing every permission it would add or remove, every
person it would add or remove, and who is notified. Nothing changes until an
administrator clicks **Approve**. If the role changed after the card was
made, the card says so and makes no change.

## Roles

Each app has a **User** and a **Manager** role, listed in
{access_center} with each one's people, and a workspace can add its own between them.
{one_mail} has roles too; everyone is at least its User.

**An app's roles are built in {access_center}**: open the app under **Apps**,
where **Roles**, **People** and **On One Record** are at the top right.
Roles is a table with what the app lets a role do down the side and its roles across the top,
each cell a dropdown or a switch that saves as it changes. Signatures and
sender names, out of office, mail rules and {one_ai} settings are each **No**,
**Their Own Address** or **Every Mailbox**; who uses a mailbox,
connections, connecting shared mailboxes, the address policy and mail
templates are switches. A role above User always has everything User has.
**New Role** adds a column; click a role's name to rename or delete it,
and **Show Roles** to choose which columns show.
Clicking a {one_mail} role here opens that table.

For the other apps, a role's page here has:

- **Record Types**: tick or untick permissions on any record type the app
  uses: Select, Read, Edit, Create, Delete, Submit, Cancel and Export. For
  example, remove Delete from Manager, or hide a record type from User.

To add your own role, such as Senior Sales or Brand Team:

1. Click **New Role**.
2. Name it, and choose its app and the role it's **Based On**.
3. Change what it may do on its page, or in {one_mail}'s table for a {one_mail}
   role.

The new role appears on each person's page, in that app's list between User
and Manager.

When you save a role:

- Permissions add the ones they depend on. Delete adds Read, and Cancel adds
  Submit and Edit.
- Select is added for the records a record type links to, such as an invoice's
  customer. People can then choose those records even if they can't open them.
- Everyone with that role is notified.

Permissions and abilities are saved the way Role Permissions Manager saves
them, so it shows both. Once you change a record type's permissions here, app
updates no longer change its standard permissions. Everyone at any role of
an app still counts as one of its users. They get the notifications its
users get, and can open its reports, which show only what their role can
read.

## Access Profiles

A profile is a job's role in every app at once, such as Accountant with
{one_book} as Manager and {one_inventory} as User. Make one in {access_center}, then
choose it under **Profile** on a person's page to set every app at once.

- Changing the profile later updates everyone on it.
- Their administrator setting and any other roles they have, such as HR roles,
  stay as they are.
- Changing one of their apps by hand removes them from the profile.

## Groups

A group is a named team, such as Sales Gulf, and its members. Make one under
{access_center}. Assign a record to everyone in it from **Assign To**, or
@mention the group in a comment to notify them all. A group doesn't grant any
permissions.

## Limiting Someone's Records

On a person's page, **Add User Permission** limits them to a territory,
customer group, customer, supplier, department, branch, project or warehouse.
They then see only records for it, plus records that don't name one. The
limit can apply everywhere or to one record type (**Applicable For**).

- **Remove** removes the limit.
- Limits HR sets, such as to their own employee record, aren't shown and can't
  be removed here.
- The person is notified either way.

## The Audit Log

Who did what in the workspace, under {one} › **Audit Log**. Only administrators
see it. Each entry is recorded as it happens, and no one can change or
delete one.

- **Changes**: every change to a record, such as "Wren changed {one}". Each
  entry shows every field that changed, from what to what. **Open** on its row
  goes to the record. Filter by record type or by user.
- **Sign-ins**: every sign-in and sign-out, including failed ones, with the IP
  address. Filter by person or by whether it failed.
- **Exports and Prints**: every list or report exported to a spreadsheet,
  every record printed to PDF and every private file downloaded, with who did
  it.

Administrators see changes and exports for record types they can read, plus
user accounts and permissions. A change shows only the fields they can read.
System activity, such as scheduled jobs, updates and platform support, isn't
listed. Sign-ins are kept for 90 days. Changes and exports are kept for good.
A record's own changes are also on its timeline, for everyone who can read it.

{one_ai} offers **What changed today?**, **Any odd sign-ins?** and **What left as
a file?**, using only what you can see in the log.
