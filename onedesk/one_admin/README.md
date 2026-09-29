# OneAdmin

Written by hand. What OneAdmin does and how to use it. Everything above
**Under the hood** is written for the operators who use it, and OneAI reads it
to answer "how do I…" questions. Under the hood is for the people who build it.

OneAdmin is the console One is run from: the workspaces customers pay for,
the jobs that build and wind them down, their domains, the price list, the
signups and the credits, and OneAI's models. It is only on the admin site,
and only for **One Operator**. Nobody on a customer's workspace can open it,
whatever roles they hold there.

## Home

**OneAdmin** in the dock opens it on **Home**.

Along the top are five numbers, frappe's number cards. Each opens the list
it counts:

- **Live**: workspaces serving their customers.
- **Building**: workspaces whose job is still being built.
- **Owing**: workspaces overdue or suspended for not paying.
- **Failed**: jobs that stopped on a step.
- **Paid, Not Built**: signups somebody paid for that have no workspace.

Under them, **Needs You** lists what needs an operator, the most pressing
first. Each row says what it is, why, and since when, and has its one
action:

- **A job that failed** says what it was doing, the step it stopped at and
  the error. **Resume** runs it again from that step. Every step is safe to
  run twice, so this never builds a second site.
- **A signup paid for and not built** says whose it is and why it stopped.
  **Build It** makes the workspace, as paying would have.
- **A workspace owing** says whether its payment is overdue or it is
  suspended, and since when. Open it to see its standing and act on it.
- **A domain** that has waited a day for its DNS, or has stopped working.
  **Check Again** asks Cloudflare where it has got to.

Clicking a row opens the record. Home keeps itself up to date: a job that
fails, a signup that arrives or a domain that comes up changes it without
reloading. When nothing needs you, it says so.

## Being told

Operators are told without opening Home:

- **Job Failed**: a job stopped on a step, with the step and the error.
- **Signup Not Built**: somebody paid and their workspace could not be made.
- **New Signup**: somebody paid for a new workspace.
- **Workspace Owing**: a workspace fell overdue, or was suspended.
- **Domains Waiting**: each morning, the domains that have waited a day or
  stopped working.

Each can be turned off or changed under **Settings › Notifications**, and
none of them is offered to anybody who is not an operator.

## Asking OneAI

On Home, OneAI offers **What needs me today?**. It reads the same list Home
shows, with each item's reason, and changes nothing: resuming, building and
checking again are Home's buttons. On a job, **Why did this job fail?**
explains where it stopped and what the error means.

## Under the hood

For the people who build OneAdmin. OneAI does not read past this heading.

- **Two gates** (`site.py`): the site config key `one_admin` makes a site the
  admin site, and every OneAdmin doctype grants only One Operator. On any
  other site the role is taken off everybody, and the permission hooks refuse
  every record and every list. `docs/INFRASTRUCTURE.md` and
  `docs/ACCOUNTS.md` are the long form.
- **Home is frappe's `One Admin` workspace**, as One's Home is: five
  number cards, and Needs You as a Custom HTML Block (`OneAdmin Needs You`,
  a fixture, for One Operator only) drawn with frappe's own quick list
  markup. frappe offers every workspace to Workspace Manager, whatever its
  roles, so `site.offer` (`extend_bootinfo`) takes OneAdmin's rail and
  Home out of the boot for anybody who is not an operator on the admin site.
  With its rail gone, the dock drops its entry, and the address answers
  "not found". `patches/home_is_a_workspace.py` removes the page Home was
  for a while, and the Stuck card, which is Failed now.
- `home.counts` and `home.needs` are the operator's only (`operator._may`).
  The actions are `operator.py`'s own verbs: `resume`, `retry_signup` and
  `refresh_domain`.
- `tell.py` and `notifications.py`: the machinery writes with `db_set`, so
  there is no document hook to hang a notice on. Each is called where the
  thing happens: `runner._stop`, `signup.accept`, `steps._arrive` and
  `domains.nightly`. A notice that fails is logged and never stops the job.
- `ai.py`: `console_today` is `home.needs` for OneAI, refused to anybody
  who is not an operator on the admin site.
