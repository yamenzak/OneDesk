---
name: ux
description: Whether a person gets their job done in One — the steps, where the job starts, what they are told, what happens when it goes wrong, and who else it reaches. Load it before building or changing any flow (making, approving, importing or paying for something, a create dialog, a setting that changes behaviour, a notification that asks for action, an error, a first-run or empty screen) and before calling a feature done.
---

# UX

The `ui` skill is where things sit and how they look. This one is whether
the person finishes their job: how many steps it takes, where it starts,
what they are told, and what happens when it goes wrong. A screen can pass
every UI rule and still fail here. News did: every guard passed, and adding
a source had never been done by someone allowed to.

## Start from the job, not the feature

Before building, write these four lines in the commit message:

- **Who:** the role and the demo user (huda keeps the books, samir runs
  projects, karim the stock, omar sales, mariam HR, tariq an employee,
  wsadmin the administrator), and how often: every day, every month, once
  at setup.
- **The job**, as they would say it: "pay last month's supplier invoices",
  not "Payment Entry batch support".
- **Where they are when it starts:** on the record, in a mail, on Home's
  Needs You, on a phone at a site.
- **What done looks like:** the record submitted, the money out, the next
  person told.

Then count the steps from where they start to done: every click and every
field. A daily job is a few clicks. A once-a-year job can take more if each
step is clear.

## Fewer steps

- **Start the job where the person already is.** An action on the record,
  in the mail, on the notification, not "go to the list, New, pick the
  customer again".
- **Carry over what is known.** Opened from a customer, the customer is
  filled; from a project, the project; from a mail, the sender.
- **Default to what is right most of the time:** today, the person's
  company, the warehouse they used last.
- **Ask only what changes the outcome.** The rest goes on the saved record,
  or nowhere. On a saved record, empty fields nobody must fill wait behind
  one button rather than stretching the page.
- **Ask in the shape the answer takes.** When the thing exists out there
  (a place, a company), search first and let the choice fill the rest. When
  kinds mean different things, ask the kind first, as cards, then only that
  kind's questions.
- **Take what the person has, find the rest.** The site's address, not its
  RSS link; a place's name, not its coordinates.
- **Do several at once when people do several.** Pick five sources; approve
  ten leave requests from one list.
- **Never make them leave to finish.** A missing customer is made from the
  field, in the create dialog, and fills the field when saved.

## Tell them what happened

- **Every action answers.** A toast in the button's verb: "Invoice
  submitted." Silence reads as broken.
- **What takes time says it is running**, and lets the person carry on: a
  background job, and a notification when it is done.
- **Show what they will get before it is added:** three headlines from the
  feed, the preview of the print, the error from the bank file.
- **A state is where the person looks.** Overdue on the row, waiting on the
  pill, not only inside the record.
- **Progress is read, not clicked.** A record's steps say what is done and
  where it stands; something that looks like a set of buttons is taken for
  a choice.
- **Nothing a person looks for waits for hover.** Who has a row, when it
  last changed, its comments: always shown. Hover may add, never reveal.
- **A value is never cut on a record.** A name, a state or an amount that
  is squeezed or ends in "…" with no way to read it is information lost.
- **The same number everywhere.** Project Progress said 0 beside seventeen
  late tasks, because it counted a different way from the list.

## Prevent, then forgive

- **Prevent the mistake.** Save stays off while something required is
  empty, and the dialog's foot says what is missing.
- **Offer only what makes sense now.** A leave application finished by
  Approve does not also offer frappe's Submit.
- **Undo beats "are you sure".** Confirm only what cannot be undone, with
  `onedesk.interface.ask`: the question, what it does, and a verb that
  names the act, red when it cannot be undone. Never Yes and No.
- **An error keeps what was typed** and says what to change.
- **No dead ends.** A record the person cannot open says No access, not a
  spinner. A settings dialog opens on something, never an empty panel.
- **Try one mistake on purpose** before calling it done: leave a required
  field empty, use a role without the right, paste a wrong address.

## The people around the job

- **A job that needs somebody else reaches them with the record and the one
  action** (Approve, Send the File), and tells the first person when it is
  done.
- **What a person can never do is hidden.** What they could do with a role
  says who can: "Your role doesn't allow changing this."
- **The same action has the same name in the same place in every app.**
  Somebody who learned OneBook already knows OneHR.

## The first time

- **An empty screen leads to the first action:** a short empty state and the
  primary button, never a blank page.
- **Setup asks once,** in the setup wizard, with defaults for the country.
- **A tour points at what this role has on this screen.** OneHR's tour
  described HR's figures to an employee who sees their own leave instead.

## Real conditions

- **Away from a desk is a phone.** Check in, approve, look up stock and read
  a mail are done on a phone first. Check In on a desktop asked to register
  a passkey "on this phone".
- **Arabic and German are longer and Arabic runs right to left.** A label
  that fits in English is cut in German; a date beside Arabic words comes
  out backwards unless it is isolated.
- **Real amounts of data.** A list of thousands opens fast; a picker
  searches; nothing loads every row to count them.

## Claude's UX habits, and what to do instead

Each happened in this app.

- **Building the feature, not the job.** News stored sources and fetched
  them well; nobody had added one the way a person would.
- **Checking with records that already exist.** A screenshot of a saved
  record says nothing about making one.
- **Asking for what the system could find:** the exact RSS link, a name the
  feed already has.
- **Every field up front,** on a record nobody has saved yet.
- **Two ways to do one thing:** Add and From Library side by side.
- **A number that is true by one rule and wrong to the reader:** an invoice
  paid in parts showed "26 days overdue" beside the last part's due date.
- **Both verbs:** our Approve and frappe's Submit offered together.
- **The wrong device:** a desktop told to act "on this phone".
- **A Yes button.** frappe.confirm's Yes and No made the person reread the
  question; the verb (Delete Customer) answers it.

## Before calling it done

This is for a change to how a job is done: its steps, where it starts, what
the person is told, what happens when it goes wrong. A change to how a part
looks, with the steps the same, is the `ui` skill's alone.

Walk the job as the person who does it, from where it starts to done (the
`ui` skill's table, How a job is done). Then write in the commit message:
who, the job, where it starts, the steps counted, and what the person saw
when you tried a mistake.
