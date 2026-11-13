---
name: ux
description: Whether a person gets their job done in One — the steps, where the job starts, what they are told, what happens when it goes wrong, and who else it reaches. Load it before building or changing any flow (making, approving, importing or paying for something, a create dialog, a setting that changes behaviour, a notification that asks for action, an error, a first-run or empty screen) and before calling a feature done.
---

# UX

The `ui` skill is where things sit and how they look; this one is whether
the person finishes their job. A screen can pass every rule and still fail
here. News did: every rule passed, and adding a source had never been done
by someone allowed to. No rule can hold this skill; it is walked.

## Start from the job, not the feature

Before building, write four lines in the commit message:

- **Who:** the role and the demo user (huda keeps the books, samir runs
  projects, karim the stock, omar sales, mariam HR, tariq and nadia
  employees, wsadmin the administrator), and how often.
- **The job,** as they would say it: "pay last month's supplier invoices",
  not "Payment Entry batch support".
- **Where they are when it starts:** on the record, in a mail, on Home's
  Needs You, on a phone at a site.
- **What done looks like:** submitted, the money out, the next person told.

Then count every click and field from start to done. A daily job is a few
clicks; a yearly one may take more if each step is clear.

## Fewer steps

- **Start where the person already is:** on the record, the mail, the
  notification, not "go to the list, New, pick the customer again".
- **Carry over what is known** (opened from a customer, the customer is
  filled) and **default to what is right most of the time:** today, the
  person's company, the warehouse they used last.
- **Ask only what changes the outcome,** in the shape the answer takes: a
  search first when the thing exists out there, the kind first as cards
  when kinds mean different things.
- **Do several at once** when people do several: approve ten leave
  requests from one list.
- **Never make them leave to finish:** a missing customer is made from the
  field and fills it.

## Tell them what happened

- **Every action answers,** a toast in the button's verb; what takes time
  says it is running, lets them carry on and tells them when done.
- **Show what they will get first:** three headlines from the feed.
- **A state is where the person looks:** overdue on the row, not only
  inside the record.
- **The same number everywhere.** Project Progress said 0 beside seventeen
  late tasks, counting a different way from the list.

## Prevent, then forgive

- **Prevent the mistake:** Save stays off while something required is
  empty, and the foot says what.
- **Offer only what makes sense now:** a leave application finished by
  Approve does not also offer Submit.
- **Undo beats "are you sure".** Confirm only what can't be undone, with
  `onedesk.interface.ask` and a verb that names the act.
- **An error keeps what was typed** and says what to change.
- **No dead ends:** No access, not a spinner.

## The people around the job

- **A job that needs somebody else reaches them** with the record and the
  one action, and tells the first person when it is done.
- **What a person can never do is hidden;** what a role could do says
  "Your role doesn't allow changing this."
- **The same action has the same name in the same place in every app.**

## The first time, and real conditions

- **An empty screen leads to the first action.**
- **Setup asks once,** the module's steps from its `setup.py`, mandatory
  first (`setup-declared`, point 5).
- **A tour never starts by itself;** it points at what this role has here.
  OneHR's described HR's figures to an employee who sees their own leave.
- **Away from a desk is a phone.** Check in, approve, look up stock, read a
  mail: phone first.
- **Arabic and German are longer,** and a date beside Arabic words comes
  out backwards unless isolated.

## Claude's UX habits

Each happened in this app.

- **Building the feature, not the job.** News fetched sources well; nobody
  had added one the way a person would.
- **Checking with records that already exist.** A shot of a saved record
  says nothing about making one.
- **Asking for what the system could find:** the RSS link, not the site.
- **Every field up front** on a record nobody has saved yet.
- **Two ways to do one thing:** Add and From Library side by side.
- **A number true by one rule and wrong to the reader:** an invoice paid in
  parts showed "26 days overdue" beside the last part's due date.
- **Both verbs:** our Approve and frappe's Submit together.
- **The wrong device:** a desktop told to act "on this phone".
- **A Yes button:** the verb (Delete Customer) answers the question.

## Before calling it done

For a change to how a job is done (a look with the same steps is `ui`'s):
walk it as the person who does it, from where it starts to done, making the
record rather than opening one, with one mistake on purpose (a required
field empty, a role without the right, a wrong address). Then write in the
commit: who, the job, where it starts, the steps counted, and what the
person saw for the mistake.
