# Approvals

An approval sets the states a record moves through before it's done, and who
moves it. A purchase order stays Waiting for Approval until a manager approves
it, or a customer stays Pending until the accounts team checks it. Only
administrators see this, and only for record types they can open. The
system's own record types, such as users and roles, and One's own can't have
approvals.

OneAI offers **Approve bills by amount** and **Who approves what?** It
suggests a new or changed approval as a card you approve. The approval then
opens in the builder, laid out, to edit like any other.

A bill OneAI drafted waits in **Ready to Submit**. **Submit** takes the
approval's step when the step is waiting on your role. Otherwise it says who
it's waiting for. OneAI never takes a step itself.

## Adding an Approval

Open Setup › **Approvals**, or a record type's **Settings › Approvals**.

1. Click **New Approval**, and choose the record type and a name.
2. In the approval builder, drag a state onto the page for each step.
3. Connect two states with an action, such as Approve or Reject, and choose
   the role that can take it.
4. If you like, have a state set a field of the record, such as Status to
   Approved.
5. Click **Save**, then turn the approval **On**. Only one approval can be on
   for each record type.

## Who Is Told

People with the role see the action on the record. Each step waiting on their
role counts in **Approvals Waiting** on their Home. They're also told in One,
and by email if they chose (**Approval Waiting** in NotificationCenter's
**Words and Rules**), when a record reaches their step. Whoever made the
record, and whoever sent it to the step, hear where it went next (**Approval
Answered**).

## Conditions on a Step

An action can have a **Condition** that compares the record's fields with
plain values, so the same action can go to different people depending on the
amount. **Approve** by an accounts user when:

    doc.grand_total <= 5000

and by an accounts manager when:

    doc.grand_total > 5000

- Write a field as doc. followed by its name.
- Compare with ==, !=, <, >, <=, >= or in.
- Combine with and, or and not.

Conditions that do more, calculated values and tasks an action runs aren't
available here, since they'd run as whoever takes the action. A state can only
set fields that anyone who can edit the record could set.
