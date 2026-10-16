# Mail

What every mail One sends looks like, whether everything that should tell
somebody does, and the words each one says by default. An audit of every
module's notifications against its code, then four stages. The machinery
(types, the hub, choices, push, rules) is docs/NOTIFICATIONS.md; this is what
it sends.

## What the audit found

Four reads of the code, one per group of modules, each listing every type,
every place that sends one, what should send and does not, every mail
frappe, erpnext and hrms send from a screen of ours, and how each default
reads. In short:

- **The mail itself was frappe's.** "New Notification" as the heading of
  every notification, "Open Document" as its only link (an empty one when
  the sender gave no record), an SVG logo no mail client shows, "One" where
  the workspace belongs. A mail to an outside address had no frame at all.
- **Some notices never arrived.** A person asking to be deleted was never
  sent the confirmation (frappe drops a notice a person sends themselves);
  a deleted person never heard so (they were switched off before the job
  ran); seven types marked "always mailed" were bell only, three of them
  privacy requests with a legal deadline; a file request answered from
  outside failed to save; Task Given never showed on the bell in our words.
- **Some were silenced or mistimed.** Four OneInventory notices were skipped
  for anybody who had ever been assigned or mentioned on the record; a
  CRM next step was missed for good if the scheduler stalled ten minutes;
  HRMS's interview reminders, copied as they were, fired at midnight or
  never.
- **One could be sent by anybody, about anything.** Credit Limit Crossed
  took its recipients and figures from the browser.
- **Events with nobody told.** About two dozen, listed under Stage 3.
- **Mails nobody listed.** erpnext's repost error mail (sent beside our own
  Reposting Failed), appointment confirmations, payment request links, the
  delivery trip mail, the supplier scorecard mail, the deferred accounting
  and Auto Repeat failures, frappe's sign-in link and authenticator setup.
- **Words.** "3.0 days", "1 years ago", "a experience letter", "Open it to
  Approve, Reject", a subject that names the step but not the lead, a
  Check-in Place "proposed" that was already in use.
- **Every employee was offered the administrators' notices** (credits,
  plan, privacy requests): no type in `one/` or `one_intake/` named roles.

## Stage 1: the frame

Done. One frame for every framed mail, modelled on Linear's and Stripe's:
the workspace above a white card, what happened as the heading, the message,
one button named for what it opens, and which notification it is. Ours is
found before frappe's, so frappe's own framed mails wear it too; a mail a
person writes is not framed. docs/NOTIFICATIONS.md, The mail.

## Stage 2: what was broken

- Always mailed means mailed: `notify.notify` mails those types itself, to
  each person, whatever they chose; the senders' own second mails are gone.
  That delivers Confirm Deletion, Account Deleted, Copy Asked, Deletion
  Asked, Deletion On Hold, Privacy Requests Waiting and Your Data Is Ready.
- A dedupe is per type, in `notify.notify`, for every sender.
- Task Given writes the bell's title too; a task completed tells its other
  assignees Task Done rather than frappe's "your assignment was removed".
- Next Step Due looks back a day.
- Credit Limit Crossed reads its controllers and figures on the server, and
  says who was stopped.
- Interview Soon compares the interview's start, not its date; Interview
  Feedback Due every interview that has ended; Birthday, Work Anniversary
  and the feedback reminder go in the morning.
- Holidays Coming Up opens the calendar.
- File Request Answered and Complete are sent from nobody, with the
  sender's address as `{who}`; a test refuses a slot named like one of
  `notify()`'s own words.
- Administrator Added no longer mails the administrator who made the change.

## Stage 3: what should tell somebody and did not

By module, each a type of its own:

- **One**: New Sign-in (always mailed); Credits Ran Out.
- **OneAI**: Extension Fixed, for Fix With OneAI, which says "you will be told".
- **OneIntake**: Couldn't Read, for a document parked failed or waiting for credits.
- **OneHR**: Attendance Request Asked and Answered; the approver's note on
  every Answered; Letter Issued; Grievance Raised, without OneAI; Document
  Expiring (passport, visa, permit); Passkey Reset Done; Interview Scheduled.
- **OneCRM**: Given to You (a lead or opportunity whose owner is set to
  somebody else); New Lead Waiting (nobody owns it); Quotation Running Out.
- **OneBook**: Invoice Overdue, to the team; Bills Due This Week; Paid Online;
  Repeat Failed.
- **OneInventory**: Material Request Asked, to buying; Delivery Late.
- **OneTask**: Comment on Your Task; Sent Back, for a review answered no.
- **OneCalendar**: a guest taken off an event is sent its cancellation; an
  event shared with somebody reminds them.

And every upstream mail found unlisted is listed, with who it really reaches.

## Stage 4: the words

Done. Every type's default subject and message rewritten against what the
audit found: the subject says what happened and to what, the message what
to do next.

- A type may say `button:`, the label of its one button, where "Open
  {record}" is wrong: "Open Plan and Credits", "Review It", "Confirm
  Request". `notify.button()` reads it, in the reader's language, for bell
  mails and for the mails a module sends itself; a link written into the
  message as an anchor is gone from every type.
- A task's facts and a project's are one line, "Due 20 Oct · Mansour Villa",
  rather than a sentence each.
- Every mail was rendered on a sheet per module (the type's sample values
  in the frame it is sent in) and read, in English and Arabic.
- Roles on every administrator's type.

## Stage 5: whose mail it is

Done. Looking at single mails found the company's Brand Colour unused and
One's mark on nothing, because the mark is an SVG. The button is now the
company's colour; One's own mails (the admin site's, and the fifteen types
marked `from_one`) wear One's mark as a PNG; and a mail to a reader of
Arabic reads right to left. docs/NOTIFICATIONS.md, The mail.
