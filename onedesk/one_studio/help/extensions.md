# Extensions

An extension makes a form do something it did not: refuse to save a customer
without a mobile number, fill in a field from another, warn when a discount is
over a limit, hide a field until another is ticked.

## Asking for One

Click **Add Extension** and tell {one_ai} what you need, or say it in {one_ai}
anywhere: "Stop an invoice being saved without a purchase order number."
{one_ai} writes it, a second check reads what it wrote against what it says it
does, and you get a card saying what it does. **Approve** turns it on.
Nothing runs before that.

## Where It Runs

| Where | What it can do |
| --- | --- |
| **On a form**, in the browser of whoever opens it, with their own permissions | Show, hide, fill in or require a field, add a button, and tell the person something. |
| **On a list**, the same way | Label records (a red **Overdue**), change how a column reads, and add a button. |
| **On the server**, whenever the record is saved, submitted, cancelled or deleted | Anything a rule needs, whoever does it and however: the form, an import, {one_ai}, another app. Use the server for a rule that must always hold. |

On a form or a list it can also look up another record, as the person
would, but never change one.

## On {one}'s Own Pages

An extension can also run on {one}'s own pages, each with its own few things it
may do:

- **{one_mail}**, when a conversation is opened: show a note under it ("A key
  customer"), or add a button next to Reply. And whenever a message is
  written, anywhere in {one}: show a note above it, or fill in its subject, cc
  or bcc.
- **A record's head**, each time the record is opened or saved: add a button
  next to the head's own, a figure in its band ("Sales Invoices: 12"), or a
  note under it. Only on the kind of record you name. One written for a
  Project runs on its page too.
- **A project's page**, when it is opened and each time the project changes:
  a note or a button under its header.
- **{one_calendar}**, when an event's card is opened: a note or a button on it.
- **{one_task}**, each time a view of your tasks is shown: a note or a button
  under its name ("4 of your tasks are overdue").
- **{one_cloud}**, when a file is chosen: a note or a button under its preview.
- **Reading**, when a document is opened in the inbox: a note or a button
  under its head.
- **The pipeline board**, each time what a stage is worth changes: a note
  above the board.
- **Every space's home** (One, {one_crm}, {one_hr}, {one_book} and the rest): a note or
  a button above its blocks.

Ask for one the same way: "When I open a conversation from anyone at
acmeco.example, show a note that they are a key customer." It is reviewed,
off until you approve it, and its errors are written down, the same as any
other. It never sees more of the page than what it is given, and it starts
running for each person the next time they load {one}.

## On a Schedule

An extension on the server can also run on its own, every hour, day, week or
month, or on a schedule you give ("each weekday at eight"), at most once an
hour: "every morning, add a comment to each open task whose end date has
passed." It works on the records it finds, not on one being saved, and only
on kinds of record you may open yourself.

## Checked Before You See It

Before an extension is kept, {one_ai}'s work is checked for what would make it
fail: every field it names must be one the record has, every form event it
uses must be one that forms really have, the code for the screen must read
as it should, and it must be one change, not a hundred lines of them. One
for the server is also run once on one of your records and undone straight
away, so an error shows now rather than on someone's next save, and {one_ai} is
told what it did ("it stopped the save, saying…"). Whatever is wrong goes back
to {one_ai}, which mends it before anything reaches you.

## What Each Extension Shows

Each extension opens on whether it is **On** or **Off** (or **Refused by
Review**, or **Cannot Run Here**) and what it does, then when it runs, what
was asked and by whom, and its review.

You do not see its code, and nobody in your workspace writes or changes it by
hand, so there is nothing to type and no **Save**. To change one, press
**Change this one…** on it and say what ("make it apply only to new
customers"). {one_ai} reads what it has now and changes only what you asked,
keeping the rest as it was, and it is reviewed again.

> A new version of one that is on waits on its page under **New Version**,
> while the one that is on keeps running. Approve {one_ai}'s suggestion, or
> press **Use New Version**, to run it in its place, or **Discard New
> Version** to keep what runs. A new version of one that is off stays off
> until you approve it.

Changing where or when it runs makes it a new extension to turn on.

## Turning One On and Off

**Turn On** and **Turn Off** are at the top of the extension. One the review
refused cannot be turned on: ask {one_ai} to change it. Deleting an extension
(**…** at the top) takes it away for good. The other administrators are told
when one is turned on, turned off or deleted, and by whom: from that moment it
runs on everybody's work, or no longer does.

**Server extensions** run only on workspaces where they are turned on. If an
extension says **Cannot Run Here**, ask us.

## When One Goes Wrong

An extension that runs into an error does not stop anybody's work: on the
server the record still saves, on the screen the form goes on working. The
error is written down, **Errors in the Last 7 Days** counts it, and every
morning the administrators hear of the extensions that ran into one.

1. Open the extension. Its **Errors** tab lists each error since {one_ai} last
   wrote it: when, on which record, and what went wrong in one line.
2. Press **Fix With {one_ai}** at the top. {one_ai} reads the extension and its
   errors.
3. A few minutes later you are told what went wrong and that a fixed version,
   reviewed, is ready. For one that is on, it waits under **New Version**
   while the one that is on keeps running. For one that is off, it stays off
   until you turn it on.

You can also ask **Has this one run into errors?** in {one_ai}, or turn it off.

An extension can also go wrong without an error: one that never does its work
writes nothing down. Tell {one_ai} what it does wrong, such as "Create Call Task
never makes the task", and it fixes it the same way. A message an extension
means to stop a save with, such as "A customer needs a mobile number", is not
an error: it stops the save, as it says.

## What It May Not Do

- Read or change what you could not.
- Reach outside your workspace: no mail, no calls to other services.
- Change the system's own records or {one}'s.
- Run more often than once an hour.

{one_ai} says so when what you ask needs one of these, and offers what it can do.
For something that tells people, an [automation](automations) is the way.
