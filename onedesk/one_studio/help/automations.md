# Automations

An automation runs by itself when a record is created, changed, submitted or
deleted, when a field changes to a value, on a date before or after one of the
record's dates, or on a schedule. Only administrators see this, and only for
record types they can open. The system's own record types, such as users and
roles, and One's own can't have automations. Automation › **Automations**
lists them all.

## What One Can Do

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

> An automation runs as whoever last saved it. Each step can only do what
> that person could do by hand.

Advanced conditions, If steps, scripts and calculated values aren't
available, since they'd run as code. How often automations can run, and
turning them all off, is managed by the platform team.

On the list, OneAI offers **Thank customers who pay** and **What runs by
itself?** It suggests a new or changed automation as a card. Once you approve
it, it runs as you.

## Adding an Automation

1. Open Automation › **Automations** and click **Add Automation Flow**, or
   click **New** on a record type's **Settings › Automations**.
2. Give it a **Title** and choose the **Document Type**, the record type it
   runs on.
3. Under **Trigger**, choose the **Trigger Type**: when it runs. **Match
   Fields** limits it to the records it's for.
4. Under **Actions**, click **Add row** and open the row.
5. Choose the **Action Type**. Its own fields appear below, such as who to
   notify and what to say, which field to set and to what, or how long to
   wait. The record's creator and assignee are offered along with your team.
6. Turn the automation **On** once it has at least one step.

## Telling People

**Tell People** notifies the people it names (team members, the record's
creator or its assignee) in One, and by email if they chose (**Automation
Notice** in NotificationCenter's **Words and Rules**). Give it a subject and
message, or a **Mail Template**. The template is filled in from the record the
same way the email window does it, with amounts and dates as the record shows
them.

## Trying One First

**Test Run** runs the automation on one record and then undoes everything, so
you can see what it would do.
