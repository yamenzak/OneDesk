# OneProject

OneProject is where work bigger than a task is run: a villa's windows, a
website, an office move. A project holds its tasks, its time, what it costs
and what it's billed. It's built on ERPNext's Projects, so a project's
quotation, sales order, timesheets and invoices are the same records the rest
of One uses.

**OneTask and OneProject share the same tasks.** OneTask is what each person
has to do. OneProject is how a project is going, for the people who run it. A
project task assigned to you shows on your My Tasks and on the project's board.

## Finding your way

**OneProject** in the dock opens it. The panel on the left lists its four
places.

- **Projects**: every project you can see. Employee onboarding and exit
  checklists belong to OneHR and aren't listed.
- **Workload**: how many hours of open work each person has in a week.
- **Time**: the time people have logged, across projects, newest first. Each
  timesheet shows who, the project, the days it covers, its hours and how
  many of them are billable. Filter it by project, status, start date or
  person.
- **Templates**: the tasks a kind of job usually has, to start a project
  from (Starting from a template).

On a phone, tap the place's name at the top, **Projects**, to go to another.
A project's page and a template's page have no panel. There, **Projects** or
**Templates** at the top goes to another of the four places. **Rates**, what an hour of each
activity costs and is billed at, is in the ··· menu on **Projects**.

On a project's page, its name at the top opens your other open projects and
**All Projects**. Its sub-projects are in the step after its name.

Tasks are in OneTask, and a project's own tasks are on its page. Project
types are in One's **Masters**.

### Seeing projects another way

The view switch at the top of **Projects** lays them out as:

- **List View**: the list, with its filters.
- **Report View**: a table you can sort, group and add columns to, and save
  as a report of your own.
- **Dashboard View**: open projects, those at risk or off track, and those
  past due, then charts of open projects by health, kind, manager and
  customer, and how many started each month. Click a number to see its
  projects.
- **Kanban View**: **Projects by Health**, open projects in On Track, At Risk
  and Off Track. Drag a card to change its health; the project's people are
  told as when it's changed on its page.
- **Tree View**: each project under its parent. Click one to open it;
  **Show Completed** adds finished projects.
- **Gantt View**: each project as a bar from its start to its end, filled as
  far as it's done, with its milestones to come marked under it. Drag a bar
  to change its dates. A project with no dates isn't shown.
- **Calendar View**: the same bars on a month, week or day.
- **Image View**: each project's cover, as a grid.

Every view leaves out employee onboarding and exit checklists until you
clear that filter.

**Projects Settings**, in the same menu, is for whoever may change it.

### Rates

Each activity, such as Design or Execution, has a default rate an hour costs
and a rate it's billed at. Under **Rates for a Person**, give somebody their
own rates for that activity. A timesheet uses the person's rate when there's
one, and the activity's when there isn't.

## Projects

The list shows each project with its customer, manager, kind, due date and
how much is done, the ones worked on most recently first. A project under
another shows that project's name before its own: **Villa Al Barsha ›
Handrails**.

The pill says where a project stands. An open project shows its health,
**On Track**, **At Risk** or **Off Track**; otherwise it shows **On hold**,
**Completed** or **Cancelled**. Click a pill to see the projects that share
it.

Filter by name, kind, status, health or manager at the top, or by customer
and anything else under **Filters**. **Add Project** starts one.

## Starting a project

**Add Project** takes three steps: **Kind**, **Details** and **Plan**. Click a
kind to move on; **Previous** goes back without losing what you typed. The kind
decides what **Details** asks for and what the project's page shows.

- **Fixed Price**: an agreed price, billed as the work gets done. Give the
  **Contract Value**, the item to **Bill As** (**Contract Work** is there to
  start with), and any **Retention** with the date it's due and the share
  **Released at Handover** (when the workspace holds retention). The customer's
  sales order for the contract is made with the project, so **Bill Progress**
  works from the first day.
- **Time and Materials**: billed by the hour at agreed rates, plus what's
  bought for it. Give a **Budget** if there is one, and the **Markup on
  Costs** added to what's bought when it's billed.
- **Retainer**: a monthly fee for a set number of hours. Give the **Monthly
  Fee** and the **Hours a Month**.
- **Internal**: no customer. Give a **Budget** if there is one.

Every kind asks for a name, and a **Template** or a preset **From the
Library** to start its tasks from. A project for a customer also asks for its
**Payment Terms** and **Terms and Conditions** (see below). **Plan** asks when
it starts and ends, its manager (you, unless you pick someone), and how its
**Time** is counted. A retainer runs month to month, so it has a start and
no end.

**Time** is separate from the kind, which is how the customer pays:

- **Timesheets**: people log their hours on the project, by hand or with a
  task's timer. For people who work on several jobs in a day.
- **Attendance on Site**: pick the project's **Site** (a check-in location in
  OneHR). Each day someone's attendance has them at the site counts as a day
  on the project. For crews who spend the whole day on one site.
- **Not Tracked**: hours aren't counted, and the page has no Time view.

It starts as **Count Time By** under **Projects Settings**, and can be changed
later in **About**. A site belongs to one open project at a time.

Whether hours are billed follows the kind. Time and Materials and Retainer
hours are billable; a Fixed Price or Internal project's hours are its labour
cost, not invoiced. A project made some
other way gets the kind its records say: Fixed Price with a sales order, Time
and Materials with billable time or a customer, Internal otherwise.

## Photos and videos of a project

Every project's folder in OneCloud (**Records › Project ›** the project) has a
**Featured Media** folder. Put the project's best photos and videos in it:

- They're shown on the project's page and on the customer's portal, the cover
  first and then each in turn: a photo for a few seconds, a video muted to its
  end. A single video plays on a loop. Holding the pointer over them pauses
  them.
- The newest photo is the project's **cover**, shown wherever the project has a
  picture.
- A project can have as many photos and videos as it needs.
- Anyone with the link to one can open it, so they can go on a website too.
  Put nothing there that isn't meant to be seen.

Only photos and videos go in. Drag a file from the project's folder into
Featured Media to show it, or back out to stop showing it. A file taken out
needs a sign-in to open again. Whoever may change the project may change its
Featured Media; whoever may see the project sees it.

## A project's page

Opening a project opens its page. At the top are its Featured Media, across
the page, with its kind, name, status, health and the kind's facts over them
and the team in the corner. A project with no
photos shows the same on a plain panel, with **Add Cover** in its corner. The
facts depend on the kind:

- **Fixed Price**: the customer, the contract, the dates and the manager.
- **Time and Materials**: the customer, the dates and the manager.
- **Retainer**: the customer, when it started, the hours a month and the
  manager.
- **Internal**: the dates, how many days are left (or how late it is) and the
  manager.

The customer shows with their logo, here and on the Overview's orders and
retention, and the manager with their picture.

How far along it is shows in the Overview's figures.

Click the name to rename it; click the status or health to change it. With
no photos yet, **Add Cover** puts one in Featured Media. Click a photo to see
every photo and video, add more, or open the folder in OneCloud.

### Status

A project is **Open**, **On hold**, **Completed** or **Cancelled**.

- A project completes itself when its last task is done, and opens again
  when a new task is added. **On hold** and **Cancelled** stay as you set
  them.
- Marking a project **Completed** or **Cancelled** while tasks or
  sub-projects are still open asks first, and closes them with it. Say no
  and it stays as it was.
- A project whose tasks are all done can't be opened again until it has a
  new task.
- Once completed, **Needs You** shows what's still owed: the contract not
  invoiced yet, invoices not paid yet and retention still held. Its manager
  is told.

**Health** is separate: how an open project is going, set by its people.

Its views are a row of tabs under its head, as a form's are, and the page
remembers which one is open. When they don't all fit, slide the row sideways. Who
it's assigned to, its attachments, tags, sharing and likes are on the right,
as on any form:

- **Overview**: the project's figures and what its kind is run by, with
  updates and Needs You.
- **Tasks**: every task, as a table grouped by project, status, owner or due
  date, as a board in columns by status, or as a timeline across the weeks.
- **Time**: every hour logged on the project, with **Log Time**.
- **Money**: the forecast, the customer's side, the cost side and the budget
  by cost type. Shown to whoever may see the documents behind it.
- **Invoices**: the customer's invoices for the project, with what's paid and
  what's still owed.
- **Suppliers**: each subcontract as a card, with **Bill Progress**.
- **Team**: who's on the project, what's on them and the hours they've put
  in.
- **Files**: OneCloud on the project's folder, as every record's Files tab is:
  its own files, **Featured Media**, **Tasks** (each of its tasks with files,
  as a folder) and a folder for each sub-project, which holds the same again.
  Folders open in place, with back and up to return. On **Main** the
  sub-project folders are left out. The same folder is the project's under
  **Records** in OneCloud.
- **Activity**: what happened on the project and its sub-projects, its
  comments and emails, and where you write them.

On a phone the row of views scrolls sideways, and the lists keep their main
columns:
the day, who and the hours on **Time**, the person and their open tasks on
**Team**, the invoice, its status and total on **Invoices**.

### Overview

The Overview is laid out for the kind, and each thing on it shows once.
Its figures are cards at the top, two to a row when there are four, beside
**Needs You**. Under them, **Tasks** is a ring of the
project's tasks by status, a late one counted as **Overdue**, and **Hours by
Week** is the hours logged in the last twelve weeks. Clicking the ring opens
**Tasks**.

- **Fixed Price**: **Contract**, **Billed** (how much of the contract is
  invoiced), **Cost** against the budget, and **Forecast Margin**. **Work and
  Billing** shows **Work Done**, then what that work is worth but isn't
  invoiced yet (**Not Invoiced Yet**, with **Bill Progress**) or what's been
  invoiced ahead of it, what the customer **Owes** and how much of that is
  overdue or retention, and anything **Paid in Advance**. Work Done is the
  project's **% Complete**, measured the way it says under **% Complete
  Method**: tasks completed or cancelled, each task's progress, or progress
  by each task's weight. A project with sub-projects measures them all
  together, and that's the figure the Projects list and the reports show
  too. Before
  the customer orders, **Contract** shows what they've been **Quoted** and
  **Billed** gives way to **Valid Till**, the quote's last day. **Cost** is
  what's been spent: supplier bills, time, stock used and expense claims.
  Under it, the budget, or by how much the forecast passes it when it does
  (which is when Cost turns red), and what suppliers still have to bill on
  their orders. **Forecast Margin** is the contract less the forecast cost:
  the budget, or what's spent and still on order when that's more. Billed
  opens **Invoices**, and Cost and Forecast Margin open **Money**. Once the
  project is **Completed** or **Cancelled**, Forecast Margin gives way to
  **Margin**, what was billed less what was spent, and no milestones,
  sub-projects or health are added to it. A sub-project whose work is on the
  order of the project above it says so in **Contract**, and has no Billed
  of its own. Under
  them, **Work and Billing** puts the work done beside what's billed and
  paid, and when the customer was last billed. **Budget** charts each cost
  type, what's spent, on order and left of it, and **Other** for the rest,
  so its bars add up to the figures. A cost type over its budget is listed
  under the chart, with how far over. Then **Milestones** (see below). On the
  right, **Subcontracts** and **Retention**.
- **Time and Materials**: **Not Invoiced Yet**, **Hours This Month**,
  **Invoiced** and **Budget Used** (or **Done** with no budget). Every figure
  is in the company's currency, the customer's only on the invoice itself.
  **Paid** is under Invoiced. Under them,
  **Not Invoiced Yet** by person with **Invoice
  Time**. On the right, **By Activity**.
- **Retainer**: **This Month** against the hours a month, **Monthly Fee**
  and when it renews, **Months Not Invoiced**, and **Invoiced**. Under them,
  **Months**: each month says whether it is invoiced and how that invoice
  stands to anybody who reads the project, and opens the invoice for those
  who may read invoices. On the right, **By Person** and **By
  Activity**.
- **Internal**: **Done**, **Due**, **Overdue Tasks**, and **Budget Used**
  when it has a budget. Under them, **Milestones** and **Due Soon** (the next two weeks). On the right, **Who's On It**.

A figure turns red when something's wrong: cost heading over budget, a
margin below zero, more hours than the retainer covers, a late end date.
**Budget Used** shows the real share, past 100% when it's over.

**Needs You** lists what needs someone now, yours first and marked **You**:
cost types over budget over the project and its sub-projects (on a Fixed
Price project they're in **Budget** instead), bills drafted by Bill Progress
to check, supplier bills to pay and customer invoices to chase that are past
due (**Chase** the customer, with the invoice and how late), late tasks, and
tasks due today. What's past due is worked out from what's still owed,
earliest payment first, so retention not yet due never counts. A task on a sub-project says
which. The heading counts them all, and **Show All** lists the late tasks
when there are more than it shows.

**About** has what the head doesn't: **Progress** (how Work Done is
measured, ERPNext's % Complete Method: Manual, Task Completion, Task Progress
or Task Weight), when it's **Due** and how far off or late that is, the
**Team**, and its **Priority**, then its **Project Type**, **Department**,
**Task Prefix** and **Cost Center** when they're set. The pencil on the
heading opens **Edit About**, which holds every field of the project not
changed elsewhere on the page, in three groups. **Work** has the manager,
dates, progress, priority, time, task prefix, type, department and parent
project. **Customer** has the customer, the kind and what it needs, payment
terms, terms and conditions and retention. **Accounts** has the cost center.
A field your workspace adds to projects shows under **More**. The customer
and the kind are fixed once the project has orders or invoices, since those
already bill that customer that way, and an import or bulk edit is held to
the same. % Complete is typed when Progress is Manual. **Add Brief** writes
the project's brief, which then sits at the top with its own pencil. Both
save against the project as the page loaded it, so a change someone made
meanwhile is never overwritten. A sub-project's breadcrumb names the
projects it sits under.

**Sub-projects** starts with **Main**, the project's own work without what's
under it: what's ordered on it and how much is billed, and how far its own
tasks are. Click it to see the page for that alone. Then come the projects
directly under this one, each with its
kind, when it's due or how late, who runs it and how far it's done, and its
money for everything under it: what's ordered and how much is billed, or
what's spent against its budget. A red dot marks one that's late, Off Track
or over budget, and an amber one At Risk. Extra work has the **Extra Work**
badge, and one with projects of its own says how many. **Show All** lists
them all when there are more than it shows. **Add Sub-project** here
starts a new project under this one for the same customer.

**Updates** shows the latest update. Write the next one on the line under
it and **Post** (see Asking the team how it's going).

### A retainer's months

A Retainer's **Overview** lists its months, newest first, from the one it
starts in: the hours used of the month's allowance, any over, and the
month's invoice. A month that has ended without one has **Invoice Month**.

**Invoice Month** (also the page's main button) asks for the month and the
item to invoice it as. It shows the hours used of the allowance, and any on
timesheets not submitted yet, which the invoice won't include. When the
month went over, a tick to bill the hours over adds a line for them at what the
month's hours were billed at on average; untick it to leave them. It opens a
draft invoice with the month's fee, any hours over, and the month's time on
it. Submitting it marks that time invoiced, so it's never billed again, and
the month shows its invoice. A month is invoiced once.

A retainer's hours are billed with its months, so **Invoice Time** isn't
offered on one. Its **Time** shows this month's hours against the allowance
instead of amounts, and its **Invoices** has **Invoice Month** instead of
**New Invoice**.

### Tasks

A project's tasks and those of every project under it are shown together,
grouped by project at first, each titled by where it sits (Handrails ›
Glass for handrails). The switch beside **Search** lays them out as a
**Table**, a **Board** or a **Timeline**. **Group by** changes the grouping,
**Search** finds a task, and **Done** shows finished and cancelled tasks
too. On the board, drag a card to change its status; the timeline marks
today and counts the tasks without dates.

In the table, change a task's owner, status, due date, priority or hours
right in its row. Giving a task to a **group** (under **Settings ›
Access**) gives it to each person in the group. **Planned** is
the hours planned for it (ERPNext's Expected Time), and each group's heading
adds them up. **Progress** is ERPNext's own progress on the task. A
project with no tasks of its own shows only **Add Task**. A task that depends on others not yet done says what it's
**waiting on**. A sub-task sits under its parent, and a parent says how many
of its own are done. **Add Task** at the foot of a group adds one there;
**New Task** adds one to the project. Click a task's name to open it beside the page.
It's the same task OneTask opens: change its owner, priority, dates, hours
and whether it's a milestone in place; see what it's part of and what it
**Waits On**; tick and add its **Checklist**; add **Sub-tasks**; and read
and write its comments. ▷ times it onto your timesheet. **⋯** has **Edit
Details** (its type, hours, parent task, what it waits on, Bill on
Completion and description), **Repeat** and **Open Full Form**.

Late due dates are red. Whatever someone else changes shows up without
reloading.

### Time

Every hour on the project and its sub-projects, newest first: the day, who,
the activity, the task (with the sub-project under it), the hours, and where
they stand. **Draft** is on a timesheet not yet submitted, **To Invoice** is
billable and not invoiced, **Invoiced** is on an invoice, and **Not Billable**
is cost only. **Group By** puts them under each person, activity, task or
sub-project, with their total over all its entries. They come grouped by
person, a few each, with **Show More** under each group. The newest 200 are
listed, and **Open Older Entries** opens the rest in the Timesheet list. Where nothing is billed, as on a Fixed Price
job, only drafts say where they stand. Click an entry to open its timesheet.

The figures:

- **Logged**: all the hours, against what the tasks plan (their Expected
  Time), or else the project's **Planned Hours**, with what's not submitted
  yet.
- **This Month**: this month's hours.
- **To Invoice** and **Invoiced**: on a project that bills hours, or one with
  a sub-project that does (it says which). **Invoice Time** is the button on
  **To Invoice**. On a project with sub-projects it invoices all their billable
  hours for the same customer on one invoice.

  On a Time and Materials job, **Invoice Time** also offers **Bill Costs**:
  what was bought for it and not billed yet (supplier bills' lines, stock
  issued to it and approved expense claims), one line each at cost plus the
  project's **Markup on Costs**, made out as the item you pick in **Bill
  Costs As**. A cost billed once isn't offered again, unless its invoice is
  cancelled. A Fixed Price job's costs are covered by its price and are never
  billed this way.
- **Time Cost**: what the hours cost at each person's cost rate, against the
  project's **Time Budget** if it has one, red once it's over. On a Fixed
  Price job this is how you see whether the team is burning more time than
  the price allowed.

A retainer shows this month's hours against its allowance instead.

Money shows only to those who may see time rates (Accounts Users, as ERPNext
sets it). Everyone else sees the hours. Amounts are in the company's
currency.

**Log Time** asks for the day, the hours, the activity, and the task if there
was one. On a project with sub-projects it asks which one, and picking a task
picks its sub-project. The entry goes into your timesheet for the week, the
same one the timer on a task writes into, ready to submit with the rest.
Logging time on a task doesn't complete it; complete it when it's done.
Hours from before this week still in draft show in **Needs You** as **Submit
your timesheet**. On a project counted by attendance, the days come from
attendance and there's no Log Time.

Whoever may read timesheets sees Time, and sees the entries they may read. A
project whose time isn't tracked has no Time view, unless someone logged time
on it anyway.

#### Days on site

On a project counted by **Attendance on Site**, each day someone's attendance
is submitted and they were at the site, the day becomes a timesheet on the
project, made and submitted for them:

- **At the site** means one of their check-ins that day was inside the site's
  circle (or a clock place drawn on it). When check-ins have no position, their
  shift that day names the site.
- **The hours** are the attendance's working hours, or the standard working
  day from HR Settings (half of it for a Half Day).
- **The activity** is **Activity for Days on Site** in Projects Settings
  (**Site Work** to start with). Set its costing rate, or each person's
  Activity Cost, so the days carry their labour cost.
- **Billable** follows the kind: daywork on a Time and Materials project is
  billed, a Fixed Price project's days are cost.
- **Cancelling the attendance** cancels its timesheet, unless it's been
  invoiced.

HR keeps attendance for payroll as it is. A day that can't be written, such
as one whose hours overlap a timesheet the person already has, doesn't stop
the attendance. It's in the Error Log.

### Invoices

The customer's invoices for the project and those under it, newest first.
Each says what it's for (**Work done 40%**, **9 h of time and costs**, a
retainer's month, **Credit note**, or its first item) and which sub-project
it's on, its date, when the part owed now is due (in red once it's past), its
status, total, what's **Outstanding** now, and the **Retention** still held
with the date it's due. Outstanding and Retention together are what the
invoice still owes. The customer and their logo show when there's more than
one customer. Amounts in one currency are said once, above the figures.

The figures above are what's been **Invoiced**, **Paid** (with anything paid
in advance on the order), **Outstanding** now, **Overdue**, and
**Retention Held** when there is some. They count with tax, as the customer
pays, and only the project's part of an invoice that's partly another's.
Overdue says how many invoices are late.

**Release Retention** above the figures records the customer paying the
retention: it opens ERPNext's payment, not saved yet, for the parts due by
today (or all of it when none is due yet), each matched to its invoice's
retention, so those parts show as paid. Check the amount, the account and
the bank reference, and submit it. **···** on an invoice offers Release
Retention for that invoice alone.

**···** on an invoice offers **Record Payment** (how much, when, into which
account) and **Send**, which opens the invoice with its email ready and the
invoice attached. **New Invoice** starts one for the customer on the
project; **Invoice Time** and **Bill Progress** are in the page's buttons.
Shown on a project with a customer, to whoever may read invoices; Record
Payment to whoever may make payments.

### Team

Everyone on the project: its **Members**, its manager, whoever a task is
assigned to and whoever logged time on it. Each shows their job (from their
employee record, and **No sign-in** for somebody whose time is logged but
who can't sign in), their open tasks with how many are late, and their hours
this month and in all.

**Add Member** adds somebody to the project's members. **···** on a row makes
that person a member, or removes a member. Their tasks
and time stay, so somebody removed is still listed while the work names
them. Only somebody who signs in can be a member. An employee who only has
their time logged can't be. Whoever may change the project may change its
members.

The avatars in the project's head are the same people, the manager first,
and open **Team**. **About** on the Overview counts them too.

Members are who can open the project. Three things let somebody in, so
nobody is given work on a project they can't see:

- **A task given to somebody** who can't open its project makes them a
  member, as frappe shares a record with whoever is assigned it. New Task
  says so under **Owner** before it's made.
- **Mentioning somebody** in a comment who can't open the project asks
  whether to add them first (**Add to Project** or **Just Comment**).
  Without it they'd be told of the mention and find the project closed.
- **Members** in the sidebar is the project's sharing: it shows the members
  and its **+** is Add Member. Sharing a project any other way makes the
  person a member too.

**Contacts** lists the people outside the company on the project: the
subcontractors and suppliers, consultants, the architect, the engineer, the
client's representative and the authorities. Each has a **Role**, the
**Supplier** or, for anyone who isn't one, the **Company**, the **Contact**
(their email and phone come from it) and a **Note**. **Add Contact** adds
one, and clicking one changes it or removes it. The contact then lists the
project among its links. Whoever can open the project sees its contacts,
and whoever can change it can change them.

### Activity

What happened on the project and its sub-projects, the newest first:

- **Documents**: each quotation, order, delivery, invoice, payment, request,
  receipt, expense claim, stock entry and journal entry made for it, when it
  was made, submitted and cancelled, with the party and the amount. Clicking
  one opens it.
- **Changes to the project**: its name, status, health, manager, customer,
  dates, budget, priority, kind and members, from frappe's record of its
  changes.
- **Work**: tasks added and completed, the team's updates, the hours each
  person logged in a week (one line a week, saying over how many days), files added or removed, and sub-projects started.
- **Comments and emails** on the project.

At the top, you write a comment, and typing @ mentions someone. **New
Email** opens the email window on the project, with its mail templates and
its files to attach. **Reply** and **Reply All** on an email answer it. The
newest is first, and **Show earlier activity** at the foot loads older rows.
A task's panel has the same Activity.

**All**, **Money**, **Work** and **Comments** narrow it. A document only
shows to whoever may read its type.

### Beside the views

Under the views is what a project's form keeps beside its fields: who it is
**Assigned To**, its **Tags**, who it is **Shared With**, its likes, who else
has it open, and who made it and changed it last. **+** assigns or shares it
in frappe's own dialogs; a tag is picked from the workspace's or typed new.
Whoever can change the project can assign and tag it; whoever may share it
can share it.

### Buttons

The main button is the kind's: **Bill Progress** on a Fixed Price contract,
**Invoice Time** for Time and Materials, and **Post Update** otherwise.
**···** has **Ask for Updates** and **Group Under New Project**. The other steps are where they belong. **Quote Extra Work** is
under **Quotations** and **Draw Up Contract** under **Contracts** on the
Overview, **Add Sub-project** under **Sub-projects**, **Issue Stock** and
**New Expense Claim** on **Money**, and **Templates** on **Tasks**. On a
Fixed Price project with no contract yet, **New Quotation** takes the place
of **Quote Extra Work**, and while one quotation is open **Make Order** is
the main button.

Below them are the ones every record has, as on its form: **Print**,
**Email**, **Show Links**, **Duplicate**, **Rename**, **Reload**, **Delete**,
**Remind Me**, **Follow**, **Copy to Clipboard**, **New Project** and
**Customize**, each for whoever may do it.

The page is where a project is changed: its name, status and health in the
head, **Edit About** for the rest, members and contacts on **Team**, the
budget on **Money**, and **Ask for Updates** in **···**. ERPNext's form is
still at the project's address with `?edit=1`, with every field.

Whoever can open a project sees its page. Whoever can change it can rename
it and change its status and health. Whoever can change tasks can change
them here. Each button shows only to whoever may do what it does.

## Who runs a project

**Project Manager** is the one person who runs a project. It starts as
whoever created it. The manager always sees the project, whether or not
they're a member. Filter **Projects** by it, or by **Health**.

## Who sees a project

**A project's members** are the people listed under **Members** on its page.
They see the project and every task in it. People who work in projects but
aren't members don't see it. Projects Managers see every project, and whoever
created a project sees it.

**A project with no members is open** to everyone who works in projects, so a
small team never has to add anyone.

**A task's own people always see it.** Whoever is assigned a task sees it on
My Tasks, member or not, but nothing else of the project.

Someone who only picks a project on a quotation, order or invoice sees every
project in that list. Picking one doesn't open it.

## Sub-projects

A part of a job that's billed separately is a **sub-project**: handrails on a
villa whose windows you're already fitting, or a booking module a website
customer asks for halfway through. Set its **Parent Project**, or click **+**
next to **Sub-projects** on the parent's page. It's a project of its own,
with its own quotation, sales order, time, costs and invoices, and it also
counts towards the parent. Sub-projects can have sub-projects.

- A sub-project gets its parent's **customer** unless you set another.
- A parent's page shows the **whole tree added up** (estimated cost, cost,
  billed and margin), and its **% Complete** measures every task under it.
  **Sub-projects** lists the ones directly under it. The **Contract** card
  says how much of it was ordered as extra work.
- **Main**, first in **Sub-projects**, shows the page for the parent's own
  work alone: its own orders, tasks, time, invoices, bills, team and
  activity, and its figures without what's under it. A project with
  sub-projects has one more step in its breadcrumb, **All Work** or
  **Main**, which switches between the two and opens each sub-project. The
  address keeps it, so the link opens the same view.
- A parent's **Calendar** includes its sub-projects' tasks, each titled with
  its sub-project.
- **Members** of a project see everything under it.
- A project can't be put under one of its own sub-projects.

**Group Under New Project** (in **Actions**) puts a new project above this
one. If the villa's windows came first and the handrails were added under
them, grouping the windows under a new **Villa** project, with the handrails
ticked, leaves Windows and Handrails side by side under Villa, each with
everything it had.

## A project's board

**Board** shows a project's tasks in four columns: **Open**, **Working**,
**Pending Review** and **Completed**. Each card shows its priority, due date
and who is on it. Drag a card to move the task along. **Add Task** at the top
of a column adds one there. The board is created the first time anyone opens
it, and everyone shares it.

**Overdue isn't a column.** An overdue task stays where it is and its date
turns red, on the board and in every list.

## A project's calendar

**Calendar** is the project's own calendar: every open task in it, whoever is
on it, and every event about the project. Drag a task to move it. **Add
Event** creates an event about the project, which shows on the calendar of
everyone who can open the project.

## Task names

A task is named like **TASK-2026-00042** unless its project has a **Task
Prefix**. With the prefix **WEB**, its new tasks are named **WEB-1**,
**WEB-2** and so on. Existing tasks keep their names. A prefix is 2 to 10
letters and digits, starting with a letter, and no two projects share one.

## A project's schedule

**Schedule** shows a project's tasks on a timeline: this project's and every
sub-project's, except cancelled ones. Each task is a bar from its start to its
due date. A task with only a due date is one day, a **milestone** is marked
as one, and an arrow runs from a task to each task that depends on it. It
opens on today. **Today** goes back to it, and **Day**, **Week**, **Month**
and the rest at the bottom change the scale.

**Drag a bar to move a task**, or drag its end to make it longer.
Double-click a bar to open the task.

## Milestones

A milestone is a task marked **Milestone**, on the project or on any
sub-project. **Add Milestone** under **Milestones** on the Overview asks for
its name, which project it's on, and its due date. To make an existing task
a milestone, open it and turn on **Milestone**.

**Milestones** on the Overview shows the last two done and the ones to come.
Each says when it's due and how far off it is, and turns red once it's late.
One on a sub-project says which.

On a project with sub-projects, **Milestones** is a row per part of the job
on one dated line: **Main** first, then each sub-project with what's under
it, and a line for today across them all. Done ones are filled, a late one is
red, and each row's next one is named with its date. Point at the others to
see theirs. Each row counts how many are done. Click **Main** to see the
project's own work, or a sub-project's name to open it. On a phone each part
is a line with its next milestone.

**Bill on Completion** is optional. Give a milestone a share of the contract
and the project is billed by its milestones: **Work and Billing** shows
**Billable on Milestones**, the shares of the milestones done, and **Not
Invoiced Yet** is measured against that instead of the work done. When such
a milestone is done, the project's manager is told, and **Bill Progress**
starts from that share. A project whose milestones have no share is billed
by the work done, as before.

Anyone who can add tasks can add a milestone. Its share is on the task, so
whoever can change the task can change it.

## Documents on a project

Every document about a project names it:

- **Customer**: quotations, sales orders, delivery notes and sales invoices.
- **Suppliers**: material requests, requests for quotation, supplier
  quotations, purchase orders, purchase receipts and purchase invoices.
- **Work**: tasks, timesheets, updates, expense claims and stock used.
- **Payments**: payments in and out.

Set the project once. A document made from another takes its project, so an
order made from a quotation names the quotation's project. A line with no
project takes the document's, and a document with no project takes its
lines' if they all name the same one.

A payment made on its own, or for several invoices at once, takes the
project its invoices and orders all name. A new sales order, delivery note
or sales invoice for a customer with one open project names that project.
With more than one, pick it.

**Connections** on the project's page lists them in those four groups, and
**+** next to one starts it on the project.

## What a project costs, and billing it

**Money** on the project's page shows the money for the project and its
sub-projects together. Click a row to see the documents behind it.

- **Forecast**, by the project's kind:
  - **Fixed Price**: the **Contract** (what the customer ordered), the
    **Budget**, the **Forecast Cost**, the **Forecast Margin** and the
    **Margin So Far** (invoiced less spent).
  - **Time and Materials**, under **So Far**: what's **Earned** (invoiced, and
    time and costs not invoiced yet), the **Cost**, the **Margin So Far**
    (earned less cost), and the **Budget** if it has one. With an order,
    what was **Ordered** and the **Forecast Margin** against it.
  - **Retainer**, under **So Far**: the **Monthly Fee**, what's **Invoiced**,
    the **Cost** and the **Margin So Far**.
  - **Internal**: the **Budget**, what's **Spent**, the **Forecast Cost** and
    what's **Left**.
- **Customer**: what they've been **Quoted**, what they've **Ordered**, what's
  been **Delivered** and **Invoiced**, what's **Not Invoiced Yet** on Time and
  Materials, and what they've **Paid**, each with a bar against what they
  ordered.
- **Cost**: what's been **Ordered** from suppliers, **Received** and
  **Billed**, what they've been **Paid**, and the team's own **Time**,
  **Stock Used**, **Expense Claims** and **Journal Entries** (such as payroll
  or depreciation charged to the project).

A row still at nothing isn't shown. Amounts are before tax, except payments,
and in the company's currency. Everyone who reads the project sees its
totals, as ERPNext's project form shows what's billed. A row opens its
documents only for someone who may read them.
**Paid** is what's been paid on the project's invoices or bills, however it
was paid, with advances on its orders not yet set against a bill. The page
updates as documents are submitted.

The forecast cost is, for each cost type, what's been spent and what
suppliers still have to bill on their orders, or its budget while that's
more; then the same for the rest of the budget. So an order that takes a
cost type past its budget shows the day it's placed, even while another cost
type is under. With no budget there's no forecast.

Set the **Budget** to what you expect the whole project to cost: the pencil
on **Budget** under **Money**. The same dialog takes the
**Time Budget**, what the team's own hours may cost, and the **Planned
Hours** when the tasks don't plan any; the **+** on **Logged** and **Time
Cost** under **Time** opens it too. A cost type can't hold the time, as
ERPNext books timesheets to no account, so the time has its own budget.
Each can be changed whenever the plan changes.

**Time is priced for you.** Every hour on a timesheet (the timer on a task
writes one) is costed and billed at the rate set for that person and activity
under **Setup › Activity Cost**, or at the activity's own rate under
**Activity Type** if the person has none. Once the timesheet is submitted,
the hours count in the project's **Cost**, and billable ones in what there is
to bill. Time on a project with a customer is billable unless someone unticks
it.

**Bills from suppliers count too.** When OneIntake reads a supplier's bill
that names an open project, the bill it drafts is for that project, and so is
each line, so the project's **Cost** includes it once it's submitted. A bill
naming two projects, or none, is left for you to set.

**Invoice Time** (in **Actions**, on a project with a customer) creates an
invoice for every billable hour on the project not yet invoiced, with one line
per activity, so the customer reads *Execution, 7 hours* and *Planning, 2
hours*. It asks which item to bill the time as, remembering the last one, and
opens the invoice unsaved for you to check. Submitting it marks the hours as
invoiced, and the project's **Billed** goes up. A sub-project's time is
invoiced from the sub-project.

## Budget by cost type

Split the budget by **cost type** under **Cost Types** on **Money**: one
for each kind of cost you track, such as labour, materials, subcontracts or
equipment (each is an expense account in OneBook). Each shows its
**Budget**, what's **Committed** on supplier orders not yet billed, what's
been **Spent**, and what's **Left**, over the project and its sub-projects.
**Time** is the team's own hours against the **Time Budget**: ERPNext books
timesheets to no account, so the time has a line of its own, and the
project's **Budget** is the cost types and the Time Budget added up.
**Other** is the rest of the budget and cost, *not in a cost type*: a
sub-project's budget without cost types, and cost booked to accounts none
of them use.

**How a cost lands in a cost type**: by the account it's booked to, with
the project on it. A supplier's bill (**Record Bill** on **Suppliers**, or
an order's bill) books to each item's expense account; an expense claim to
its claim type's account; **Issue Stock** to the item's expense account, or
else the company's cost of goods, never to Stock Adjustment. Click a cost
type to see what was booked to it, each opening its document, and
**Change Budget** there; click **Time** to open **Time**.

**Add Cost Type** asks for the cost type, its budget, and what happens
**Over Budget**: **Warn** shows a warning on an order or expense that takes
it over, and **Stop** refuses it. Click a cost type to change its budget or
remove it. One only a sub-project budgets for adds this project's own. Once
a project has cost types, its **Budget** is their total.

On a Fixed Price project's **Overview**, **Budget** adds up each cost type
over the project and its sub-projects. A cost type counts only what's spent
and ordered on the projects that budget for it, as the warning does.
**Other** is everything else: budget not split into cost types, and cost
outside them, such as the team's time. The arrow on the heading opens
**Money**.

Cost types are set by whoever looks after the books (Accounts Manager).
Everyone who can see the project sees them.

## Subcontracts

A subcontract is a **purchase order** on the project, one for each supplier
and package of work: the glazing, the joinery, the electrics. Order a package
as 1 **Lump Sum**, so it can be billed a part at a time. An order with a Lump
Sum line, or for anything not kept in stock, is a subcontract. An order for
stock items is goods, and is listed under **Buying**.

**Suppliers** on the project's page shows each subcontract as a card: the
supplier, what it was ordered for and which sub-project, how much of it is
billed, what's left to bill, what's been paid, what's **To Pay** now (in red,
with how late, once it's past due), the retention held and the advance not
yet set off. **Open Order** opens it, **···** offers **Pay Advance**, and
**New Purchase Order** starts one on the project. **Record Bill** records a
supplier's bill with no order before it, a shop receipt, on the project.
**Add Supplier** adds a
supplier to the project's contacts before anything is ordered from them,
and they're listed under **No Order Yet** until there's an order. The line above adds up
what's ordered, billed, left to bill, to pay, overdue and held. A Fixed
Price project always shows **Suppliers**; others once they have an order.

**Bill Progress** (on the supplier's card, or under **Create** on a submitted
order) asks how far the
work has got. Say 40% and it drafts the supplier's bill for 40% of the order,
less what's been billed already, at the order's prices. The bill shows the
share as **Work Done**. Check it and submit it as any other bill.

**Retention**: a share of each bill held back and paid later, as contractors
are paid. It's off until **Hold Retention** is ticked in **Projects
Settings**, since most businesses never hold it. Then set **Retention** (the
share held back, often 5 or 10%) and **Retention Due** on the order's
**Terms** tab. Each bill holds that share of the work back, due on that date.
A subcontract keeps its own retention, whatever the project's.
To release part of it at handover, as is usual on building work, set
**Released at Handover** to that part of the retention (often 50%): it falls
due on the order's delivery date, or the day the project is marked
**Completed** if that's sooner, and the rest at Retention Due. Change Retention
Due and every bill from the order moves with it.

**Advances**: **Pay Advance** on the card opens ERPNext's payment against
the order, to check and submit. Each bill sets it off.

Above the cards, the figures say what's **Ordered** (and what's left to
bill), **Billed**, **Paid**, **To Pay** (and what's overdue) and any
**Retention Held**, in the currency said once at the top. Each subcontract's
card shows its own **Retention** and what's held from it so far.

**Bills** lists the suppliers' bills for the project and its sub-projects,
newest first: what each is for (**Work done 70%**, or its first item), its
date, when the part owed now is due (in red once it's past), its status,
total, what's **Outstanding** now and the **Retention** still held with its
date. The supplier and their logo show when there's more than one supplier. A draft from Bill Progress is there to check. **···** on a bill
offers **Record Payment**, and **Pay Retention** once retention is held from
it: ERPNext's payment to the supplier for that retention, to check and submit.

Extra work from a supplier gets an order of its own, so the original stays
readable.

**Buying**, under the cards, lists what's being bought for the project and
its sub-projects: material requests, requests for quotation, the suppliers'
quotations, orders for goods (with how much is received and billed, in amber
when it's billed ahead of what's come) and the goods received, newest first. **New Material Request**
asks for material for the project, and **Request Prices** asks suppliers to
quote.

**Subcontracts** on a Fixed Price project's Overview lists the subcontracts: what
each is for, which sub-project it's on, how much is billed, and what's to pay
once retention is set aside. An amber dot marks an order billed further than
the work on its project has got, with how far that is. A supplier's bill with
a payment past its due date is in **Needs You** as **Pay** the supplier. The
arrow on the heading opens **Suppliers**.

## What's agreed with the customer

A project for a customer holds two things agreed with them, both ERPNext's
own:

- **Payment Terms**: when an invoice is due, such as **Net 30**.
- **Terms and Conditions**: the wording printed at the foot of its
  quotations, orders and invoices.

**Add Project** fills both in. The payment terms are the customer's own when
they have some, else the template's, else the company's. The terms and
conditions are the template's, else the company's. Change either in the
dialog, or later in **About**. An internal project has neither. A sub-project
with none of its own is billed on the nearest project above it that has some,
and **About** says which.

Every quotation, order and invoice made for the project starts with them:
**New Quotation**, the contract, **Bill Progress**, **Invoice Time** and
**Invoice Month**. An order made from a quotation keeps the quotation's, and
an invoice made from an order keeps the order's. Pick others on a document and
that document keeps yours. **Bill Progress** dates the invoice by the order's
payment terms, and any retention falls due after. A supplier's bill is due as
its purchase order says, not as the customer agreed.

**Add Contract** asks for the payment terms and the terms and conditions too.
Ones changed there become the project's.

### Contracts

The contract value is the customer's sales order. What gets signed is an
ERPNext **Contract**, and a project can have as many as it needs: the main
contract, an addendum for extra work, a renewal, or a supplier's subcontract
agreement.

**Draw Up Contract** (under **Contracts** on the Overview)
asks who it is with: the project's customer, or one of its suppliers (those
ordered from for the project, and those on its contacts). It names the
project and runs over its dates. Its wording comes from a **Contract
Template**, or for the customer from the project's terms and conditions. A
supplier's contract needs a template. It opens in the Contract form, where you
record who signed it and when, then submit it.

**Contracts** on the Overview lists each one with who it is with, whether it
is signed and when it ends. A supplier's contract also shows on its card on
the **Suppliers** tab. **About** shows the customer's: **Signed** with when it
ends, or **Not signed yet**. While the project is open, Needs You says **Get
the contract signed** for each one not signed, and **Renew the contract** from
a month before a signed one ends, unless a later one with the same party runs
on past it.

**Draw Up Contract** shows to whoever may create contracts, a Sales Manager in
ERPNext. Everyone who reads the project sees the list. A contract's wording
opens only for those who may read contracts, since an employee's contract is
a Contract too.

## Billing the customer as the work gets done

The customer's contract is their **sales order** on the project, and a
project can have more than one: a variation ordered later is a second order
on the same project, and extra work is ordered on its own sub-project.
**Contract** adds up the orders on the project and those under it. With more
than one, the project's head says how many, **Orders** on the Overview (under
**Work and Billing**, with **Quotations** after it) lists each with where it is, what it's for, what's left to bill and how much of it
is billed (or its status when it's on hold or closed), and **Bill Progress**
asks which order to bill, each with where it is and what's left on it. The
heading's arrow opens the orders. **Bill Progress** (also under **Create** on a
submitted order) works as it does for a supplier: say how far the work has got and it drafts the invoice for that
share, less what's been invoiced already. On an order of several lines, such
as a bill of quantities, tick **By Line** to give each line its own share
done: 50% of the lights and 30% of the cabling bills 20 of 40 lights and 180
of 600 m. Each line shows what's ordered and what's billed so far, and the
invoice's **Work Done** is the share of the whole by value.

The customer's **Retention** is set three ways. The project holds the usual
one (**Retention**, **Retention Due** and **Released at Handover**, from its
template or the New Project dialog, changed under **Edit About**). Each new
customer order on the project starts with it, and the order may change it,
say to 0 on extra work. Each invoice starts with its order's, and may change
it or set it to 0 before it's submitted. **Customer** under **Money** shows the **Retention Held** still to be
paid. **Retention** on the Overview sets what the customer holds (**From the
Customer**) beside what's held from suppliers (**To Suppliers**), across the
project and those under it, each with the rate when the orders agree and when
the first of it is due. A month before the customer's retention is due,
Needs You says to ask for it, and a supplier's past due says to pay it. The
project's manager is told on the day any of it falls due (**Retention Due**).
The invoice is for the whole amount and the retention is a later part of its
payment schedule, so the accounts are ERPNext's own: it stays in Debtors and
Creditors until paid, and Accounts Receivable by payment terms shows it not
yet due. **Release Retention** (and **Pay Retention** for a supplier) is
ERPNext's Payment Entry with each line naming its retention term, so ERPNext
marks those terms paid and Debtors or Creditors goes down by what was held.

### Before the customer orders

A Fixed Price project can start before anything is agreed. **New Quotation**
(in **···**) starts a quotation for the project's customer, as often as you
need until one is ordered. While the customer's quotation is open,
**Contract** on the Overview reads **Quoted** with the quotation's value,
**Forecast Margin** is worked out against it, and **Make Order** at the top
of the page turns the quotation into the sales order. A quotation with
alternative items opens instead, so you can pick which ones were ordered.
**Quotations** on the Overview lists the project's quotations not ordered
yet, drafts too, with where each stands. An ordered one is its order. **Work and Billing** shows once something is
ordered.

A project can have more than one quotation, a revised price or a choice of
two. With several open, **Quoted** shows the newest and says how many there
are, and clicking it lists them so you can order the right one. Mark a
quotation **Lost** once it's replaced, or cancel and amend it for a new
revision. A lost, expired or cancelled quotation no longer counts.

A quotation made outside the project, from a deal in OneCRM or the
Quotation list, offers the customer's open projects to pick from. If the
customer has one open Fixed Price project with nothing ordered yet, it's
picked for you.

With no quotation and no order, **Add Contract** under **Contract** makes the
sales order from a **Contract Value**, the item to **Bill As** and any
**Retention**, as **Add Project** does. To change a contract once it's made,
change its sales order.

### Customers billed in another currency

A customer whose account is in another currency, such as USD, is billed in
it. The contract value and a retainer's monthly fee are agreed in that
currency, and the contract, **Invoice Time** and **Invoice Month** make their
orders and invoices in it. Hours are turned into it at the day's exchange
rate. The project's own figures are all in your company's currency.

**Make Order** and **Add Contract** show to whoever may create sales orders;
**Add Contract** also needs the right to change the project.

## Extra work becomes a sub-project

When a customer asks for more in the middle of a job, such as handrails on a
villa whose windows you're fitting, quote it as its own piece of work.
**Quote Extra Work** (under **Quotations** on the Overview) starts a quotation for the project's
customer, on the project, with **Extra Work** ticked. You can also tick
**Extra Work** on any quotation for the project. When the customer orders it
and the **Sales Order** is submitted, a new project is created for the order
under this one, with the order's total as its estimate. It takes the
quotation's title when you gave it one, and otherwise is named after what was
ordered. The order then belongs to the sub-project. It has its own time,
costs and invoices, and they add up into the parent's.

To add an order to the project as it is, leave **Extra Work** unticked.

## Asking the team how it's going

**Updates** on a project's Overview shows the team's latest update, with the
health the project was in when it was written. **Show Earlier** opens the
rest. Write yours in the line under it and press **Post**. **Post Update** in
the page's menu brings you to the same line. Health is set in the page's head,
and each update keeps the health it was posted in.

**Ask for Updates** in the page's menu asks the team for an update: **How
Often** (**Daily**, **Twice Daily** or **Weekly**) and when. The Updates
heading then says how often, such as **Asked every Monday**. Each member gets
a notification that opens the project, and an email if the workspace sends
mail. **Subject** and **Message** are what the request says. Leave them empty
and One asks in its own words.

- On a day you're asked, Updates says **Your update is due today** until you
  post it.
- Posting again the same day replaces your earlier update.
- Replying to the email works too, whenever the reply comes.
- An update posted by someone else shows without reloading the page.
- Every update is in the project's **Activity**, under who wrote it.
- No one is asked on a day off in the project's **Holiday List**, and a
  project with no members asks no one.
- **Draft my update** in OneAI writes a first draft from your week on the
  project: what you finished, the hours you logged and what's next or late.
  Approving it puts it in the line, to change and post.

Anyone who can see a project can post an update on it. Asking the team is for
whoever can change the project.

If the workspace sends mail, everyone on the project also gets the day's
updates by email the next morning.

## Being told

- **Added to Project**: someone adds you to a project's members. Shows the
  project, its customer and its end date.
- **Made Project Manager**: someone makes you a project's manager.
- **Project Health**: someone marks a project you manage or are a member of
  **At Risk** or **Off Track**.
- **Project Completed**: a project you manage is completed, by someone or by
  its last task. Says what's still owed on it.
- **Milestone Done**: a milestone billed on completion is done, on a project
  you manage or one under it. Says what share of the contract to bill.
- **Project Update Asked**: the project asks for your update.
- **Project Summary**: each morning, what the project's people said the day
  before.
- **Over Budget**: what's ordered and spent on one of a project's cost types
  passes its budget. To the project's manager and whoever set the budget,
  once for each budget.
- **Progress Bill Drafted**: someone saves a bill or invoice made with **Bill
  Progress** on a project you manage, for you to check.
- **Retainer Month to Invoice**: on the first of the month, a retainer you
  manage whose last month isn't invoiced, with its hours against the
  allowance. To whoever made it when it has no manager.
- **Retainer Hours Used**: a submitted timesheet takes a retainer you manage
  past its hours for this month.
- **Hours Over Plan**: the hours logged on a task pass its planned hours
  (Expected Time). To whoever has the task and the project's manager, once,
  as they pass.

A task's own notifications (**Task Given**, **Task Done**, **Task Ready**,
**Pending Review** and **Due Date Changed**) are OneTask's, and listed with
it.

Each is on the bell, and by email or push if you chose. Change them under
**Settings › Notifications**.

## Asking OneAI

On a project's page, OneAI offers what fits the view you're on:

- **Overview**: **How is this project going?**, **What is late?**, **Write
  the customer an update** and **Plan the tasks**. On a retainer, first
  **How much of this month's hours are used?**
- **Tasks**: **What is late?**, **Plan the tasks** and **Who has too much
  on?**
- **Time**: **Where did the time go?**, **What's still to invoice?** and
  **Who has too much on?**
- **Money**: **Where is the money going?**, **What's still to invoice?** and
  **What's left to pay the subcontractors?**
- **Invoices**: **What's still to invoice?**
- **Suppliers**: **What's left to pay the subcontractors?**
- **Team**: **Who has too much on?** and **What is late?**

An internal project has no customer, so it isn't offered the customer
update or what's still to invoice. On the Projects list, OneAI offers
**Which projects need attention?**

OneAI reads a project as you see it on its page: its figures, its money with
the customer and suppliers, its cost types, its tasks, its time, its people
and their load, a retainer's months, and the team's updates, including the
sub-projects you can see, and the project's own work apart from them, so it
can say what the job is worth without its extra work. Tasks it suggests come as cards, and nothing is
added until you approve one.

On **Templates** and on a template's page, OneAI offers **Draft a template**.
Say what kind of job it is for. It offers a template you already have, or
one from the library, first. A new one comes as a card listing its phases,
how many tasks it has and how many days it runs. Approving it makes the
template and opens it to change.

## Who has room this week

**Workload** in the rail shows everyone on an open project's team, and
anyone else with open tasks, in a week. Someone with nothing planned shows
with all their hours free. It shows this week unless you pick a day in
another, and every project unless you pick one. The week it covers is named
above the table, and the cards above it give the team's **Capacity**,
**Planned** and **Free** hours and how many people are **Over Capacity**.
Each person shows:

- **Capacity (Hours)**: their working days that week, minus holidays and
  approved leave, times the working day set in HR Settings (**Standard
  Working Hours**, or 8 if it isn't set).
- **Planned (Hours)**: the hours still to do on their tasks that fall in the
  week. That's a task's **Expected Time** minus the time already logged on
  it, spread over the days from its start to its due date. Overdue work counts
  in full this week. A task assigned to two people counts half for each.
- **Free (Hours)** and **Load (%)**: red once they're over.
- **Tasks** and **Late**, how many are past their due date. Click either for
  the list.
- **Not Estimated**: how many of their tasks that week have no Expected Time.
  Click it for those tasks, to fill them in.
  The hours are only as good as the estimates, so a light week with five
  unestimated tasks isn't really light.

The busiest come first, then whoever has the most late tasks. Give tasks an
**Expected Time** and a date and the figures follow. You only
see the tasks you can see.

## What the customer sees

A customer can follow their projects on the website. On the customer's
**Contact**, **Invite as User** gives that person a login. They sign in at the
workspace's address and see their own pages: **Projects**, and their
quotations, orders and invoices.

**Projects** lists the customer's open projects. Opening one shows:

- its Featured Media beside its name, turning on its own as on the project's
  page, with arrows and the small photos to turn it by hand;
- how far along it is (the whole project, sub-projects included) and how many
  tasks are done;
- the **Expected End**, and how many days are left or how late it is;
- its **milestones**, its **sub-projects**, and the tasks with their dates and
  whether each is to do, in progress, in review or done;
- the order it's for and its invoices, paid or not.

They don't see who in the team does what, the hours, the costs or the team's
updates, and they can't change anything. A customer only sees their own
projects. To hide a project from them, leave its **Customer** empty.

## Starting from a template

A job you do again and again, like a website, a fit-out or an office move,
starts from a **template**: its usual tasks, when each starts and how long it
takes, which depends on which, the milestones and the checklists.

**Templates** at the top of OneProject lists them, each with how many tasks
it has, how many days it runs and how many projects were started from it. A
template opens on a page
of its own, its tasks in the same table a project's are in, each with when it
starts and how long it lasts, as "Day 12 · 5 days" counted from the day the
project starts. Everything changes in place:

- Type in **Add Task** under the table to add one, or **Add Task Under** in a
  task's ··· menu to add one inside it.
- Click a task's name to rename it.
- Click **Day 12 · 5 days** to change the day it begins on and how many days
  it lasts.
- The flag beside a task makes it a milestone, or takes that away.
- **Waits On** lists the tasks it can't start before. **+** adds one and **×**
  takes one away.
- **Put Under** in the ··· menu moves a task inside another, with the tasks
  under it. **Move to the Top** takes it out again. **Delete** removes it and
  the tasks under it.

The line above the table says how many tasks it has, how many days it runs
and how many projects were started from it (click that for the list). The
line under it says what a project made from it starts with: its type,
payment terms, terms and conditions and retention. The pencil beside them
changes those and whether the template can still be used, and any field
your workspace adds to templates. **New Project** at the top starts one.

### From the library

OneProject comes with templates ready to use. **From the Library** in
**New Project**, in **Add from Template** and on the **Templates** list offers
them as a list to pick from or search, each with its tasks, its days and what
it is for, or **In your templates** once you have a copy. The first time one
is used it is copied into the workspace as a
template of your own, in your workspace's language, to change as you like.
Using it again uses your copy. Every task in it has its hours, the work it
usually takes, so a project started from it shows its load on **Workload**
from the first day.

- **Aluminium & Glazing**: five phases, from contract review and approvals,
  through ordering, fabrication and installation, to testing, handover and
  the final account. Twenty-five tasks, and each phase ends in a milestone.
- **Interior Fit-Out**, **Small Building Works** and **Architectural Design
  Stages**.
- **Website**, **Mobile App**, **Marketing Campaign** and **ERP Rollout**.
- **Office Move**, **Event**, **New Client Onboarding** and **Year-End
  Audit**.

Each preset also brings its payment terms and terms and conditions, such as
**Net 30** and **Construction Works** for Aluminium & Glazing. The building
presets hold 5% retention, half released at handover. Any it names that the
workspace lacks are made the first time it is used, to change as you like.

### Other ways to make one

- **Save as Template** (in **Templates** on a project's **Tasks**) creates one from a
  project that went well. Each task keeps when it started and ended, as days
  after the project started, so a task that started on day 5 and took three
  days does the same next time. Cancelled tasks are left out.
- **New Project** on a template's page, or choosing it as **Template** on a
  new project, starts a project from it. Its tasks are created when it's
  saved, dated from the project's **Expected Start Date** (today if it has
  none), each with its sub-tasks, dependencies, checklist and whether it's a
  milestone, and named with the project's **Task Prefix** if it has one.
- **Add from Template** (in **Templates** on a project's **Tasks**) adds a template's
  tasks to a project that's already running, beside the tasks it has, dated
  from the day you choose.

A template's tasks aren't anyone's work. They aren't on anyone's My Tasks,
calendar or board, and everyone who works in projects can see them. Projects
Managers create and change templates. Anyone who works in projects can use
one.

## When a task is late, what depends on it moves

A task can depend on others (**Dependencies** on its page), in its own
project or in another under the same parent. When a task's due date moves
later, the tasks that depend on it and are still **Open** move later by the
same amount. The handrails wait for the frames, even though each is its own
sub-project.

## Connections

- **From OneCRM**: A quotation made from a deal or the Quotation list can be put on the customer's open project. Once the customer orders it, its Sales Order is the project's contract.
- **From OneTask**: A project's tasks are the same tasks people see on My Tasks. The timer on a task logs its time on the project.
- **From OneHR**: A day of attendance at the project's site becomes a timesheet on the project. Expense claims on the project count in its Cost, and Workload leaves out holidays and approved leave.
- **From OneInventory**: Purchase orders, goods received and stock issued for the project count in its Cost. A purchase order for a package of work is a subcontract on the Suppliers view.
- **From OneIntake**: A supplier's bill that names an open project is drafted for that project.
- **From OneCloud**: Photos and videos in the project's Featured Media folder show on its page and on the customer's portal.
- **To OneInventory**: New Material Request, Request Prices, New Purchase Order and Issue Stock on a project's page start those records on the project.
- **To OneBook**: Invoice Time, Invoice Month and Bill Progress make the customer's invoices for the project, due by its payment terms. Bill Progress on a subcontract drafts the supplier's bill. A new Retention Due on an order moves the date in the receivables report too.
- **To OneCRM**: Draw Up Contract makes a Contract for the project with its customer or one of its suppliers.

## Under the hood

For the people who build OneProject. OneAI does not read past this heading.

### What it is made of

ERPNext's **Project** is the project and its money: the customer, the one
Sales Order it answers to, `estimated_costing`, and the totals ERPNext keeps
from timesheets, purchases and invoices (`total_costing_amount`,
`total_billed_amount`, `gross_margin`). ERPNext's **Task** is the work, and is
OneTask's as much as ours. ERPNext has no project inside a project; stage 3 adds
one field for it.

- `board.py` — ERPNext's own per-project Kanban, shaped as it is made, and
  their nightly Overdue job stopped: a late task is a date, not a column. Their
  Project Summary report counted Overdue tasks, and now counts none.

  ERPNext already makes the board. **View › Kanban Board** on a project
  creates a board named after it, filtered to its tasks, with a column per
  Task status. board.py shapes that board as it is made (`shape`, on the
  Kanban Board's before_insert): Template and Cancelled are archived, the
  columns get colours, and a card shows the priority and the due date beside
  the people on it.

  **Overdue is not a status here.** ERPNext's daily job sets every open task
  past its due date to Overdue, whatever it was — a task somebody was Working
  on moves columns overnight, and moving it back lasts until the next night.
  How late a task is follows from its date, and every list in One already
  shows it from there (My Tasks has an Overdue group; the calendar draws it on
  its day). So the job is stopped, and Overdue is taken off the status list
  (custom/task.json).

  **The Projects list has a board too**: Projects by Health, open projects in
  On Track, At Risk and Off Track, made once by `settle` so the Kanban view
  opens on it rather than on a dialog asking which field to group by.
- `calendar.py` — a project's **Tasks** on its own calendar, read through
  OneTask's `calendar.due`.
- Currency: every order and invoice made here goes through one_book/currency.py
  `bill_in`, so a customer billed in USD is billed in USD. Timesheet amounts
  are turned into the invoice's currency by `billing.in_currency`, as
  ERPNext's own Fetch Timesheet does. A retainer's fee is in the customer's
  currency (`retainer.fee_currency`); the page shows it so (a card's own
  `currency`). Money's **Quoted** counts quotations still standing
  (`money.QUOTED`), and `view.to_quote` names a new quotation's project.
- `media.py` — a project's **Featured Media**: its files marked `one_featured`
  (File), shown in OneCloud as a folder inside the project's own
  (`@featured/<project>`, one_storage/namespace.py), so nothing is stored for
  the folder. Putting a file in attaches it to the project, marks it and makes
  it public; taking it back to the project's folder clears both. The newest
  photo is `one_cover`, Project's `image_field`, set as the folder changes
  (File after_insert, on_update, on_trash), and `CloudFile.on_trash` hands the
  cover to the next photo before frappe's check that no field still names the
  file. `featured` lists them for the page; `portal.view` for the portal.

  Every project's own folder in OneCloud, under Records, has a **Featured
  Media** folder. What is in it is shown on the project's page, on the
  customer's portal, and wherever else the project is shown off; the newest
  photo in it is the project's **Cover** (`one_cover`, Project's image field,
  so frappe shows it wherever it shows a record's picture).

  **Nothing is stored for the folder.** A record's folder in OneCloud is
  worked out from the files attached to the record each time it is opened
  (one_storage/namespace.py), and Featured Media is worked out the same way:
  the project's files with `one_featured` set. Putting a file in it attaches
  it to the project with the mark; taking it out to the project's own folder
  clears the mark. A folder called Featured Media anywhere else is just a
  folder.

  **Featured media is public.** It is there to be shown, on a portal and on a
  website, so a file put in it opens for anybody with its link (`is_private =
  0`), which is what frappe's File means by public and what OneCloud's
  `store.fetch` already honours. Only photos and videos go in.
- `naming.py` — a project's Task Prefix, as a frappe Document Naming Rule for
  Task with the condition "project is this one". ERPNext's Task class is not
  overridden, and frappe's series for a prefix never reuses a name.

  **Task Prefix** on a project is a short key. Setting it writes a frappe
  Document Naming Rule for Task with the condition "project is this one",
  which is the framework's own way to name a doctype differently by a field —
  nothing of ERPNext's Task is overridden, and a task in a project with no
  prefix keeps ERPNext's series.

  The number comes from frappe's series for the prefix, which is global to the
  site: a prefix changed and changed back carries on counting rather than
  reusing a name. Tasks already made keep the names they have. A new project's
  rule is written as it is saved, so the tasks a Project Template makes for it
  carry the prefix too.
- `members.py` — who sees a project: Projects Managers all, anybody else
  holding Projects User the ones they made, are listed on, or that list
  nobody (`visible`, kept for the request). A project's tasks follow it
  through one_task/access.py. Being listed is also ERPNext's own share.
  ERPNext's invitation mail is never sent (`invite`); tell.py says it in ours.
  Somebody who can't open a project joins it (`join`) when given one of its
  tasks (`assigned`, ToDo after_insert; New Task asks `joins` first), when
  it's shared with them (`shared`, DocShare after_insert, the sidebar's
  Members on the page and the form, `public/js/project_actions.js`), and
  when a comment mentions them and the writer agrees (`unseen`, `let_in`,
  through the composer's `vet`).

  ERPNext lets every Projects User read every project. A workspace running a
  villa for one customer and a website for another does not want the window
  fitter reading the website's budget, so a project's **Users** decide:

  - a **Projects Manager** sees every project, and so do the books (an
    **Accounts User** or **Accounts Manager**), who invoice every project's
    time and progress;
  - anybody else who works in projects sees a project they made, one they run
    (**Project Manager**), one they are listed on, and one with **nobody
    listed** — a project nobody has closed is open to everybody who works in
    projects, which is also what every project was before this;
  - members of a project see what is under it (sub-projects; `under`).

  The same rule decides a project's tasks (one_task/access.py): a task in a
  project is seen by whoever may see the project, and by its own people
  always.

  **Being listed is ERPNext's own share.** Their Project already shares itself
  with each person on Users and takes the share back when they are removed, so
  a member opens the project through frappe's share as well as through this
  rule.

  **A member can be taken off.** ERPNext takes back a removed member's share
  in a way only a System Manager may, so the save failed for everybody in a
  workspace; `unlist` takes it back first.

  **A member is told in ours.** ERPNext mails an invitation to each new member
  while the project saves: English mail outside the hub, which also failed the
  save where the workspace has no outgoing mail. `invite` marks it sent, and
  tell.py tells the member as Added to Project instead.

  Only somebody holding Projects User is narrowed here. Twenty other roles
  have Select on Project so a sales order or an invoice can name one; they
  pick from a list and never open the project, and narrowing their list would
  break their forms, not protect the project.
- `tell.py` — Added to Project, Made Project Manager, Project Health and
  Project Completed, through the hub.

  **Added to a project.** ERPNext mails each new member its own "Project
  Collaboration Invitation", in English, outside the hub. `members.invite`
  marks that mail sent, and `added` tells them in ours: on the bell, and by
  email or push as they chose, in their language.

  **Made its manager.** Nobody was told. `added` tells the new manager too.

  **Completed.** A project is completed by somebody or, in ERPNext, by its
  last task. `completed` tells its manager, with what's still owed on it, so a
  job done isn't taken for a job paid.

  **At risk.** Health is somebody's judgement that a project is in trouble
  before any figure says so. `health` tells its manager and members when it is
  marked At Risk or Off Track; whoever marked it already knows.

  **A retainer's month.** On the first of the month, `retainer_months` tells
  whoever runs each open retainer that last month isn't invoiced, with its
  hours against the allowance. And when a submitted timesheet takes this
  month's hours past the allowance, `hours_used` tells them then, while there
  is still time to say so to the customer.
- `updates.py` also keeps each answer's health (`one_health` on Project
  User), says how often the team is asked (`asking`), and tells the page an
  update was posted (`one_project_update`). OneAI's `draft_update` is a card
  whose approval puts the draft in the line (`one_project_draft`); nothing is
  posted from it.
- `milestones.py` — the Overview's milestones over the tree: the last two
  done and the ones to come (`pick`), where each is (`where`), and billing on
  them when one has a **Bill on Completion** share (`one_bill_share` on Task,
  `billable`). `reached` tells the manager of the project with the order.

  - The Overview shows the last two done and the ones to come, soonest first,
    with those without a date last (`pick`). One on a sub-project says which
    (`where`), and each says how far off or how late it is.
  - On a whole job, they are a row per part of it on one dated line: Main,
    then each sub-project directly under the page with what is under it
    (`lanes`).
  - **Bill on Completion** (`one_bill_share`) is a milestone's share of the
    contract, and it's optional. A project bills by milestones only when one
    of its milestones has a share: Work and Billing then counts the shares of
    the milestones done instead of the work done, and Bill Progress starts
    from that share (`billable`). When such a milestone is done, the manager
    of the project with the order is told to bill it (`reached`).
- `status.py` — the status, ERPNext's four. ERPNext sets it again on every
  save from the tasks (`update_percent_complete`), so `change` closes the
  open tasks and sub-projects first when asked (`ask`), keeps a task's own
  status when it's already closed, and puts progress back on the tasks when
  a project completed without any is opened again. `due` is what's still
  owed on a completed project.

  ERPNext works the status out again on every save
  (`update_percent_complete`): a project whose tasks are all done is
  Completed, and one with any task open is Open, unless it's On hold or
  Cancelled. So marking a project Completed while a task is open doesn't hold;
  the save sets it back to Open. `change` closes the open work first, on the
  page's say-so: the project's open tasks, and its open sub-projects with
  theirs, as ERPNext's own `set_project_status` closes a project's tasks.
  Unlike it, a task already done or cancelled keeps its status.

  Completing a project with no tasks of its own makes ERPNext keep its
  progress by hand at 100%, for good. Opening it again puts the progress back
  on its tasks.

  `due` is what's still owed on a completed project: the contract not yet
  invoiced, invoices not yet paid, and retention still held. Needs You shows
  it, and `tell.completed` tells the manager.

  `held` (Project before_validate, ahead of ERPNext's own status from
  progress) makes the status hold however it is set (the page, a bulk edit, an
  import):

  - A project closes with its work. Closed from its page, with its open tasks
    and sub-projects closed too, it closes them there. Set to closed any other
    way while work is open, it is refused.
  - Reopened after being completed with no tasks, its progress goes back to
    its tasks: ERPNext turned it to by hand only because there were none.
- `ai.py` — OneAI's `project_facts` (a project as its page reads it, with its
  late tasks, what waits on them, milestones and updates) and
  `projects_needing_attention`, and the page's suggestions.

  `project_facts` hands over the page's own answers (`overview.overview`): how
  far it has got, its dates, cost against the budget, what is billed, what is
  late and the next milestone, for the project and everything under it, and
  the Money view: both sides of the money, the subcontracts, the cost types
  and the forecast (`_money`). Beside them, what the page has further down:
  the late tasks with who is on each and what waits on them, the milestones to
  come, its people, and the team's last updates. `projects_needing_attention`
  reads the Projects list as the reader sees it and keeps the open ones in
  trouble.

  Both read as the person asking: a project they may not open is not read, and
  neither are its tasks. Tasks are only suggested (one_task/ai.py
  `plan_task`), as cards the reader approves.
- `chain.py` — every money document and its lines name the same project.
  Quotation, Request for Quotation and Material Request get a `project` field
  (custom/), named as on every other document so ERPNext's mapping carries
  it. Extra work is `one_extra_work` on Quotation and Sales Order
  (billing.py); `patches/extra_work.py` turned the old Sub-project Of into it.

  ERPNext lets most money documents name a project, on the document and on
  each line, and carries it when one is made from another: an order's delivery
  and invoice, a purchase order's receipt and bill, an invoice's payment.
  Three couldn't name one at all (Quotation, Request for Quotation and
  Material Request, which now can: custom/), and nothing kept a document's
  lines and the document itself in agreement, so a project's figures missed
  whatever somebody forgot to type.

  `agree` does that as each is validated: a line with no project takes the
  document's, and a document with no project takes its lines' when they all
  name the same one. Since the field is called `project` on every one of them,
  ERPNext's own mapping then carries it from document to document: a quotation
  to its order, a material request to its purchase order, a request for
  quotation to the supplier's quotation and on.

  A payment made from an invoice or an order takes its project from it, as
  ERPNext does. One made on its own and matched to invoices later, or paying
  several at once, takes the project they all name (`paid_for`). A new order,
  delivery or invoice for a customer with one open project names it
  (`customer_project`, public/js/customer_project.js).
- `budget.py` — cost types: ERPNext's own Budget against the project, one per
  expense account, checked on orders and expenses alone and together
  (`applicable_on_cumulative_expense`). Changing one revises it as ERPNext's
  Revise Budget does (cancel, copy, submit). Committed is the open order
  lines on that account (`money.unbilled`); spent is the ledger. `sync` makes
  the project's Budget their total. Budget permissions are ERPNext's.

  A **cost type** is an expense account (labour, materials, subcontract,
  equipment, or whatever accounts the workspace uses), and its budget is one
  ERPNext **Budget** against the project for that account, submitted. ERPNext
  then checks every purchase order and every expense booked on the project
  against it, and warns or stops as the budget says (`Over Budget`).

  - ERPNext checks orders and spending each on their own, and together when
    `applicable_on_cumulative_expense` is set, which a cost type always is: an
    order is over budget when it, the open orders and what's spent come to
    more than the budget.
  - **Cost Types** on the page's Money view lists each one over the project
    and those under it, as the Overview does: its budget, what's committed on
    supplier orders not yet billed, what's been spent (the general ledger),
    and what's left, with Other for what they leave out (`lines`). A row the
    project budgets for itself is changed there; any other adds the project's
    own.
  - **Add Cost Type** and changing one (`set_budget`) are ERPNext's own: a new
    Budget, or the old one revised as ERPNext's Revise Budget does it,
    cancelled and copied with the new amount. Removing one cancels it.
  - The project's **Budget** is then the cost types added up (`sync`), so the
    forecast and the head read the same number.
  - **Over Budget** tells the project's manager and whoever set the budget,
    once for each budget, when its orders and spending pass it (`over`).
  - Making a budget is for whoever ERPNext lets make one (Accounts Manager);
    everybody who sees the project sees the cost types.
- `kinds.py` — a project's kind (`one_kind`, and `one_monthly_fee` and
  `one_monthly_hours` for a Retainer). `make` is New Project: the project,
  and for Fixed Price its customer's Sales Order, submitted, as its
  `sales_order`. `fill` gives a project made elsewhere the kind its records
  say (`guess`, pure); `patches/kinds.py` did it for the projects before.
  `settle` makes the **Contract Work** item, in Lump Sum.
  `public/js/project_new.js` is frappe's quick entry for Project
  (`ProjectQuickEntryForm`): the kinds as cards, then the kind's fields. Its
  fieldnames are its own, since a quick entry takes a field's label and
  whether it's hidden from the doctype when the names match.

  - **Fixed Price**: an agreed price, billed as the work gets done. Its
    contract is the customer's Sales Order, made with the project (`make`), so
    Bill Progress works from the first day (progress.py).
  - **Time and Materials**: billed by the hour at agreed rates, plus what's
    bought for it (billing.py's Invoice Time).
  - **Retainer**: a monthly fee for a set number of hours (`one_monthly_fee`,
    `one_monthly_hours`).
  - **Internal**: no customer; a budget and the work.

  A project made without a kind, by ERPNext, HR or an import, is given the
  kind its records say (`guess`, `fill`), as `patches/kinds.py` did for the
  projects made before kinds existed.
- `progress.py` — Bill Progress on a purchase or sales order: ERPNext's own
  "Create > Invoice" mapper with each line's quantity cut to the share done
  less what's billed (`to_bill`), since ERPNext keeps an invoice at the
  order's rate. `settle` makes the **Lump Sum** unit (can be split) and the
  **Retention** and **Retention at Handover** payment terms. Retention is the
  order's `one_retention`, `one_retention_due` and `one_retention_handover`
  (custom/purchase_order.json and sales_order.json, all editable after
  submit). Each invoice holds its own `one_retention`, which ERPNext's mapper
  copies from the order and which may be changed before submit; an invoice
  made before had its order's (patches/retention_by_invoice.py). The
  payment schedule holds it under those terms after the invoice's own
  (`_hold`, dated from the order or else the project, `source`), set again
  after ERPNext's own split so it's the share of the work billed, not of
  what's left after advances (`retained`, `split`, `spread`). Set to 0, the
  terms go. A new Retention Due moves it on the order's invoices (`release`).
  `public/js/progress.js` is the dialog; `money._suppliers` is the Suppliers
  table.

  A **subcontract** is a Purchase Order on the project, one per supplier per
  package of work. The customer's contract is their Sales Order. Both are
  billed the same way, a share at a time:

  - **Bill Progress** (`bill_progress`) asks how far the work has got, as a
    share of the order, or line by line (`lines`) where work is measured
    against a bill of quantities, and drafts the invoice for what that comes
    to less what's been billed already. The invoice's Work Done is then the
    share of the whole by amount (`overall`). It's ERPNext's own "Create >
    Invoice" from the order with each line's quantity cut to that share, so
    the order's billed amount, its status and the project's figures are
    ERPNext's. ERPNext keeps an invoice at the order's rate, so a share is a
    part of the quantity: a package of work is ordered as 1 **Lump Sum**
    (`settle`), a unit that can be split. A line in a unit that can't is
    refused in plain words.
  - **Retention** is a share of each invoice held back (often 5 to 10%), set
    on the order with the date it's due (`one_retention`,
    `one_retention_due`). The invoice's payment schedule splits in two: the
    rest, due as usual, and **Retention**, a Payment Term of that name due on
    that date, the share of the work billed before tax, whatever advance is
    set off (`retained`). Part of it may be released at handover first
    (retention.py). Changing the date on the order moves it on every invoice
    made from it (`release`).
  - **Advances** paid against the order are set off by ERPNext on each invoice
    (`allocate_advances_automatically`).
  - The invoice says the share it's for (**Work Done**, `one_progress`), and
    saving it tells the project's manager to check it (`drafted`).
- `retention.py` — the **Hold Retention** switch (`on`, Projects Settings'
  `one_retention`, in the boot for the desk), what's still held on an
  invoice part by part (`still_held`, `held_on`), the Overview's two sides
  (`sides`), Needs You's asks (`asks`), handover falling due when a project
  is completed (`handed_over`), and the daily Retention Due (`due`). A
  customer order on a project starts with the project's retention
  (`ordered`, Sales Order before_insert, and `public/js/progress.js` on the
  form); the project's own is `one_retention`, `one_retention_due` and
  `one_retention_handover` (custom/project.json). Release Retention and Pay
  Retention are `release`: ERPNext's `get_payment_entry` for the party, its
  lines replaced by one per retention term still held (`picked`), so
  ERPNext's own `update_payment_schedule` marks the terms paid. What's held
  is each term's own outstanding, so a released term no longer counts, and
  no more than the invoice owes (`held_on`, `_base`).

  - **Hold Retention** in Projects Settings turns it on (`on`). Off, the
    retention fields leave the orders, the project dialogs and the Overview. A
    workspace already holding retention had it turned on by the update
    (patches/retention_switch.py).
  - An order may release part of its retention at **Handover** (`HANDOVER`,
    `one_retention_handover`), due when the order's delivery date comes, or as
    soon as its project is marked Completed (`handed_over`), and the rest at
    **Retention Due** (`RETENTION`).
  - What's still held on an invoice is read part by part (`still_held`):
    retention is paid last, its handover part before the rest.
  - The Overview sets what the customer holds beside what's held from
    suppliers (`sides`). A customer's retention due within a month, or past
    due, is in Needs You (`asks`), and a project's manager is told on the day
    any of it falls due, either side (`due`).
- `intake.py` — which open project a document names, for the bills OneIntake
  drafts (one_intake/money.py).

  A supplier's bill for the villa's glass says "Villa Al Barsha" somewhere: in
  its reference, a line, the delivery address. Booked with no project, it was
  missing from the project's **Cost** until somebody set it by hand. Intake
  now asks `named` which open project the document names, and the bill it
  drafts, and each of its lines, carry it.

  A name only counts whole, ignoring case, and only one project may be named:
  a bill naming two is left for a person, as one naming none is. A name inside
  a longer one that is also named ("Villa" and "Villa Windows") is the longer.
- `tree.py` — sub-projects: Parent Project (`one_parent`), the only field
  added, since ERPNext keeps money per project and has no project inside one.
  A loop is refused, a sub-project takes its parent's customer, a tree's
  figures are ERPNext's own added up each time (`totals`), and
  `group_under` puts a new project above one. `path` is where a task is, for My
  Tasks and a parent's calendar. Sub-projects are a connection on the page
  (`dashboard`). The Projects list's Tree view is frappe's treeview over
  `nodes` (`public/js/project_tree.js`, `under` is pure), and its Gantt view
  is frappe's over the project's dates, with `milestones` added as rows of
  their own that can't be dragged (`public/js/project_calendar.js`).

  ERPNext keeps a project's money per project — its one Sales Order, its
  timesheets, its costs, what it has billed and its margin — and has no
  project inside a project. So a separately billable piece of a job is a
  project of its own, and the one field tree.py adds is **Parent Project**
  (`one_parent`). The handrails on a villa are a project under the villa:
  their own quotation and order, their own time and invoices, and ERPNext's
  totals for them as for any project. Nothing of ERPNext's is copied or
  changed.

  - **A project cannot sit under itself**, however far down (`validate`).
  - **A sub-project takes its parent's customer** when it has none.
  - **A parent adds up its tree** (`totals`): its own figures and the whole
    tree's, worked out each time rather than stored, so moving a project in
    the tree is right straight away.
  - **Group Under New Project** (`group_under`) puts a new project above one —
    the villa above the windows — and moves it and whichever of its
    sub-projects are ticked underneath, so they become siblings.
  - **Members of a project see what is under it** (members.under).
  - **A page can read a parent on its own** (`narrow`, `scope`): its Main, the
    work on the project itself without what is under it.
  - **Where a task is** reads as a path, Villa › Handrails (`path`), on My
    Tasks and on a project's calendar.
- `rates.py` — Rates: Activity Type is the rail's row, and an Activity Cost,
  a person's own rates for one, is its connection and leads back to it.

  ERPNext keeps rates in two places: an **Activity Type** has a default
  costing and billing rate, and an **Activity Cost** overrides them for one
  employee. They answer one question, so the rail has one row, Rates, the
  Activity Type list, and each activity lists its people's own rates under it,
  with + to add one for somebody (`dashboard`). A timesheet prices an hour
  from the person's rate if there is one, else the activity's (ERPNext's own
  rule).
- `plan.py` — a slip moves the dependants in the rest of the tree, which
  ERPNext's own pass never looks at (`reschedule`, `moved_after` is pure). The
  schedule is frappe's Gantt over Task, filtered to the tree
  (`public/js/project.js`); `public/js/task_list.js` draws a task with only a
  due date and lights the view mode the chart is in, and `public/css/desk.css`
  lets it scroll.

  **A slip crosses sub-projects** (`reschedule`). ERPNext moves only
  dependants in the same project as the task that slipped. "Install the
  handrails" in Handrails waits on "Fit the frames" in Windows, both under one
  villa, and should move when the frames do. So after ERPNext's own pass
  plan.py moves the dependants in the rest of the same tree, the way theirs
  moves the others: a task not yet done (Open, Working or Overdue) that would
  start before the new end starts the day after it, keeping its length, and a
  date past its project's end warns rather than refuses. It saves the
  dependant whether or not the person who moved the date may edit it: the date
  moved because of theirs, and a plan that holds only where the mover is a
  member is not a plan.

  **The plan is frappe's Gantt** over the tree's tasks (public/js/project.js,
  Schedule): bars, milestones, the dependency arrows, and dragging a bar moves
  the task. A task with a due date and no start is drawn as a day on its due
  date (public/js/task_list.js).
- `billing.py` — money on ERPNext's own records. Pricing is theirs
  (Activity Cost, then Activity Type, in `TimesheetDetail.update_cost`).
  **Invoice Time** (`invoice_time`, opened through
  `frappe.model.open_mapped_doc`) is their Sales Invoice with its Time Sheets
  filled from their own list of billable unbilled hours
  (`get_projectwise_timesheet_data`), lines by activity (`lines`, pure);
  submitting it is theirs too. **Extra Work** (`one_extra_work`, the same
  field on Quotation and Sales Order so their mapping carries it) makes the
  submitted order a sub-project of its project through their own
  `make_project` (`ordered`, named by `title`, pure), and moves the order and
  its lines onto it. **Quote Extra Work** (`public/js/project.js`) starts
  such a quotation, and `public/js/quotation.js` gives it the project's
  customer.

  **Time is priced by ERPNext.** A timesheet row takes its costing and billing
  rate from the person's **Activity Cost** for its activity, or the **Activity
  Type**'s own rates when they have none (`TimesheetDetail.update_cost`), and
  a submitted timesheet adds its cost and billable amount to the project. The
  timer (one_task/timer.py) writes those rows; nothing in billing.py prices
  anything.

  **Invoice Time** (`invoice_time`) is ERPNext's Sales Invoice with its Time
  Sheets table filled: every billable hour on the project not yet invoiced, as
  lines by activity — Design 12 h, Site visits 4 h — at what the hours come
  to. It opens as a draft for somebody to read before it is submitted, and
  submitting it is what marks the hours billed and adds to the project's
  Billed, which is ERPNext's (TimesheetBillingService). On a project with
  sub-projects it takes the whole tree's billable time for the same customer,
  each line of the invoice's Time Sheets naming its project, so the villa's
  page invoices the windows' hours too (`_rows`). A retainer's hours are
  billed with its month, never here.

  **What was bought for it** (`costs`). A Time and Materials job bills the
  materials and outside work bought for it as well as its hours: supplier
  bills' lines on the project, stock issued to it, and approved expense claims
  for it, each at what it cost the company plus the project's **Markup on
  Costs** (`one_markup`). Invoice Time adds them as lines under the time, one
  per cost, and each line names the cost it bills (`one_rebills`), so a cost
  is never billed twice and is billable again if its invoice is cancelled.
  Only a Time and Materials project's costs are billed this way; a fixed price
  covers its own.

  **A quotation for extra work becomes a sub-project** (`ordered`). A
  quotation names its project like any other (chain.py), and **Extra Work**
  says it is more than the job was ordered for. Both are carried to its Sales
  Order (the same fields on both, so ERPNext's mapping carries them), and when
  the order is submitted a project is made for it under that one, ERPNext's
  own "Create > Project" from an order with the order's total as its estimate.
  The order and its lines then name the sub-project, so the handrails a
  customer asked for halfway through the windows have their own order, time,
  costs and invoices, and add up into the villa's.
- `updates.py` — ERPNext's Project Update, asked and answered. Their asking
  mailed only (and raised where no mail goes), asked hourly all day and twice
  daily in two hours running, and read email replies back every hour, adding
  them again each time, and only on the day asked. Their three askers and the
  collector are stopped (`settle`); `ask` (hourly, `due` pure) makes the
  Project Update, notifies members in One and mails where mail goes; `post` is
  Post Update; `answered` takes an email reply once as it arrives; `timeline`
  (additional_timeline_content) shows the answers in the project's activity.
  Their morning summary still runs, where mail goes (`sum_up`). Hourly is off
  the Frequency choices.

  ERPNext has the parts: **Collect Progress** on a project, how often and
  when, the subject and message of the ask; a **Project Update** for each ask;
  the answers as rows on it; and a summary of yesterday's answers mailed to
  the team (`send_project_status_email_to_users`). The asking and the
  collecting did not work, and updates.py replaces those two:

  - **It only asked by email, and only where there was mail.** With no
    outgoing account the ask raised, rolled back its Project Update, and
    nothing was asked. `ask` makes the Project Update, tells each member in
    One (a notification that opens the project), and mails them as well where
    mail can go.
  - **It asked too often.** Hourly asked every hour of the day, its window
    tested with `or`; Twice Daily asked in two hours running. `due` asks once
    a day, twice at the two times, or once on the day of the week. Hourly is
    taken off the choices: a status note every hour is not a status note.
  - **An answer could only be an email reply**, and was read back every hour
    and added again each time, and only on the day it was asked. `post` is
    **Post Update** on the project's page, which answers today's ask or, with
    none, makes one; `answered` takes an email reply once, when it arrives,
    whatever the day.
  - **The answers were kept out of sight** on the Project Update. `timeline`
    puts each one in the project's activity, under who wrote it.
  - **The summary of yesterday's answers was only mailed**, and only where
    mail could go. `sum_up` tells the project's people in One instead, and
    each chooses whether it is mailed too.
  - **An answer kept no health.** `_answer` keeps the project's health on the
    answer (`one_health` on its row), so the page shows how it was going when
    each was written, and tells the page's readers it was posted
    (`one_project_update`).
  - **Nothing on the page said whether the team is asked.** `asking` says how
    often, for the Updates heading.
- `custom/project.json` also carries **Health** (`one_health`) and **Project
  Manager** (`one_manager`, who always sees the project — members.visible),
  both from the old OneProject: ERPNext's Project has neither a judgement of
  how it is going nor one person who runs it.
- Boarding projects — HRMS builds an onboarding or an exit out of a Project —
  are typed **Employee Boarding** by one_hr/lifecycle.py, and the Projects
  rail entry, the Tree view and the Timeline leave that type out.
- `report/workload` — Workload: planned hours from ERPNext's Expected Time
  and Actual Time on the reader's visible tasks (`in_week`, `load` pure),
  capacity from the holiday list (the employee's, else the company's), HR
  Settings' Standard Working Hours and approved Leave Applications. Figures,
  not a chart.

  **Planned** is the hours still to do on each person's open tasks in the
  week: a task's Expected Time less the time already logged on it (ERPNext's
  Actual Time), spread evenly over the days from its start to its due date and
  counted for the days that fall in the week, and shared equally when a task
  is given to more than one person. Work already late counts in full this
  week, since that is when it has to be done now. A task with only a due date
  is a day on it.

  **Capacity** is the person's working days in the week — not a holiday on
  their holiday list, not a day of approved leave — times HR Settings'
  **Standard Working Hours**, 8 when it is not set. Somebody with no employee
  record works the company's working days, or Monday to Friday where there is
  no holiday list.

  Hours are only as good as the Expected Time on tasks, so **Not Estimated**
  says how many of a person's tasks in the week have none: a light load with
  five unestimated tasks is not a light load.

  Only tasks the reader may see are counted. A project filter counts the tasks
  of that project and everything under it.
- `portal.py` and `www/projects.py` — ERPNext's portal, reachable. Its list
  (/project) reads the Customer's Portal Users, which Invite as User never
  filled (`invited`, Contact on_update, fills it); a customer signing in was
  sent to One's desk (`onedesk.check_app_permission` now refuses website
  users on the apps screen); and its project page (/projects) checked role
  permissions a customer never has, so refused everybody — and showed the
  team's assignees and a New Task button. `www/projects.py` replaces that page
  (frappe renders the last app's page for a route): `view` checks ERPNext's own
  website permission (`may_see`) and shows progress over the tree, the end,
  milestones, sub-projects, tasks, the order and the invoices; `when` is pure.

  ERPNext's portal lists a customer's projects at /project and shows one at
  /projects?project=…, to anybody listed under **Portal Users** on the
  Customer. Two things stopped any customer getting there:

  - **Invite as User** on a customer's Contact makes the login and never lists
    it under the Customer's Portal Users, which is the only thing their portal
    reads (`get_customers_suppliers`), so the customer was refused their own
    projects. `invited` lists it (Contact on_update).
  - A website user signing in was sent to One's desk, which they cannot open,
    because One's entry on the apps screen did not refuse them
    (onedesk.check_app_permission).

  And one thing that stopped a customer seeing a project once there: ERPNext's
  project page (templates/pages/projects.py) checks the reader's role
  permissions, which a customer has none of, so it refused every customer. It
  also showed who in the team each task is assigned to, and a New Task button
  that let a customer add tasks to the team's project. One's own page takes
  its place at the same address (www/projects.py, since frappe renders the
  last app's page for a route): what a customer asks of a project — how far
  along it is, when it ends, the milestones, the sub-projects, the work and
  its state, and their order and invoices (`view`). Nothing of the team's: no
  names, no hours, no updates.
- `templates.py` — ERPNext's Project Template, which already makes a
  project's tasks from template tasks as the project is saved. Added: **Save
  as Template** (`save_as`, with `start_of` and `days` pure), what their copy
  leaves out — milestone, expected time, checklist (`task_made`). A Projects
  Manager may keep templates (access.py `_templates`; ERPNext allowed only a
  System Manager). A template task is not assigned to its maker
  (one_task/capture.py), everybody in projects sees it (one_task/access.py),
  the Tasks rail entries leave templates out, and a new project's prefix rule
  is written before ERPNext makes its tasks (naming.py).

  ERPNext's **Project Template** is a list of template tasks — Tasks ticked
  **Is Template**, each with **Begin On (Days)** after the project starts and
  a **Duration (Days)** — and a project given one gets a task for each, dated
  from its own start, with the template's sub-tasks and dependencies between
  them (`Project.copy_from_template`). That part is theirs and stays theirs.
  What templates.py adds is what stopped anybody using it:

  - **Save as Template** (`save_as`). Building a template meant making each
    template task by hand on the Task form and then listing it on the
    template. Now a project that went well is the template: its tasks, their
    dates as days after the project's start, their lengths, sub-tasks,
    dependencies, milestones, checklists and expected time. Cancelled tasks
    are left out, and so are dependencies on tasks in other projects, since a
    template is one project.
  - **Add from Template** (`add`). ERPNext copies a template only into a new
    project with no tasks yet. A running project may take one too: its tasks
    are made by ERPNext's own copy (`create_task_from_template`,
    `dependency_mapping`), dated from the day chosen, beside the tasks it has.
  - **What ERPNext's copy leaves behind** (`task_made`). Their copy carries
    the subject, dates, priority, type and a few more, and not whether a task
    is a milestone, its expected time or its checklist; the new task takes
    them from the template task it was made from.
  - **Who may keep templates** (access.py `_templates`). ERPNext lets only a
    System Manager open one. A Projects Manager may keep them, and a Projects
    User read them.
  - **Days kept whole** (`days_kept`, Task before_validate). A template task
    never begins before the project or lasts fewer than no days, however it
    is saved.
  - **A template task is nobody's work.** It is not assigned to its maker
    (one_task/capture.py) and everybody who works in projects sees it
    (one_task/access.py), since a template is for the whole team.

  A new project's Task Prefix names the tasks a template makes, because the
  naming rule is written when the project is, not after (naming.py).
- `template_view.py` — a template's page (page/project_template_view, the
  onedesk.template island in frontend/src/template). `read` gives its tasks
  in the template's order with their depth and what each waits on, leaving
  out the tasks ERPNext lists on a group as what it waits on, which are only
  its own tasks. `change`, `add`, `nest`, `wait` and `remove` each save the
  task as its form would and then the template, so ERPNext's own check on it
  (every task a task waits on is in the template) runs, and the save tells
  whoever has the page open. A task put under another makes that one a group
  (ERPNext asks it of a parent), and a group left with no tasks stops being
  one. A task added under another goes after the last of its tasks, so the
  template's order reads as its tree.
- `library.py` — the presets in library/, one JSON file each: a title, what
  it is for, its place in the list (`order`) and its tasks, each with the day
  it begins on, the days it lasts and its own tasks. A phase is a milestone
  when it says so. `rows` turns a preset into the template tasks it makes
  (pure): a group begins with its first task and ends with its last, and a
  task waits on the one before it in its group when that one has ended by
  then, unless it says what it comes after. `copy` makes the workspace's own
  template the first time a preset is used, in the workspace's language
  (one/babel.py `project_template` puts every title and task in the
  translations), and returns that one after. New Project (kinds.py `make`)
  and Add from Template (templates.py `add`) take a preset as `library`.
  `drafted` makes a template OneAI drafted, once a person approves its card
  (ai.py `draft_template`, a Setup card applied by one/ai_setup.py), the same
  way as a preset and as whoever approved it.
- `overview.py` — what the band answers, over the tree the reader may see:
  tasks done of all, days to the expected end (`days_left`), the money
  (money.py), overdue tasks, the next milestone, and the hours logged a week
  for twelve weeks.

  All of it is ERPNext's own: `expected_end_date`, the project's tasks, and
  the money on its documents as money.py adds it up. A project with
  sub-projects answers for the whole tree (tree.py), since the villa's
  question is about the villa, handrails included.

  How far it has got (`share`): a completed project is done, whatever its
  tasks say, since one completed with no tasks of its own has none to count.
  Otherwise it is ERPNext's own % Complete, the tree's for a project with
  sub-projects (roll_up), so the page and the lists say the same; its own
  tasks' when the page shows its Main.
- `money.py` — the page's Money view, two sides and a forecast, over the whole tree:
  each figure is the submitted lines naming a project in it, before tax, as
  ERPNext adds up a project's Billed and Purchases, with the list behind it
  (`WHERE` finds the project on the lines). Time, stock used and expense
  claims are ERPNext's totals on the project; Margin So Far counts expense
  claims, which ERPNext's own gross margin leaves out. `forecast` and
  `unbilled` are pure. `moved` (every submit and cancel) tells the open
  pages of the project and those above it to redraw. `_suppliers` is the
  Suppliers view, one card per order. ERPNext's stored totals are hidden from
  the form, not removed; the form's Costing tab keeps the Budget and the
  fields ERPNext needs (patches/costing_on_the_page.py took the rest).

  **Customer**: what they've been quoted, what they've ordered, what's been
  delivered and invoiced, and what they've paid. **Cost**: what's been ordered
  from suppliers, received and billed, what they've been paid, and the team's
  time, stock used and expense claims. Each figure opens the documents behind
  it, and the project's sub-projects are included, as the head's are.

  Every figure is ERPNext's own record added up, before tax, as ERPNext adds
  up a project's Billed and Purchases: a document's lines that name the
  project, on submitted documents. Payments are what was paid, tax included.
  Time, stock used and expense claims are the totals ERPNext keeps on the
  project.

  **The forecast** answers before the money's gone. The contract is what the
  customer ordered, or the billable time when nothing was ordered. The
  forecast cost is, for each cost type, what's been spent and what suppliers
  still have to bill on their orders, or its budget while that's more; then
  the same for the rest of the budget. A cost type over its budget shows, even
  while another is under. With no budget there's no forecast (`forecast`).
- `hours.py` — the Time view: `entries` reads the tree's Timesheet Detail
  as the reader reads timesheets, with where each stands (`state`, pure);
  `log` writes into the reader's draft timesheet for the week through
  one_task/timer.py, after the day's last entry (`after`, pure); `whose`
  finds who a timesheet is for when it has no user of its own.

  **How time is counted** (`one_time`) is asked when a project is made, beside
  its kind, which says how the customer pays. The two are separate questions:
  a fixed-price villa counts its crews' days on site, and a fixed-price
  software build counts timesheets.

  - **Timesheets**: people log hours on the project, by hand or with a task's
    timer.
  - **Attendance on Site**: the project names its site (an HRMS Shift
    Location), and each day somebody's attendance has them there is a day on
    the project (site_time.py).
  - **Not Tracked**: hours aren't counted. The page has no Time view unless
    somebody logged some anyway.

  A project made without one (by ERPNext, HR or an import) is given the
  workspace's default, **Count Time By** in Projects Settings (`fill`).
  Whether an hour is billable follows the kind (`bills_hours`): Time and
  Materials and Retainer hours are, and a Fixed Price or Internal project's
  are cost only.

  Every hour is ERPNext's Timesheet Detail on the project or a project under
  it, read as the reader reads timesheets, so somebody who may see only their
  own sees only their own. Each entry says where it stands: a draft not yet
  submitted, not billable, still to invoice, or invoiced on a Sales Invoice.

  **Log Time** (`log`) writes an entry into the reader's draft timesheet for
  the week, the one the task timer (one_task/timer.py) writes into, so time
  logged by hand and timed by the clock end up in the same place and are
  submitted together.
- `team.py` — the Team view: members, manager, assignees and whoever logged
  time, with open and late tasks and hours; `add` and `remove` change the
  project's Members as the form does.

  The team is ERPNext's **Members** on the project (Project User), and with
  them everyone the work names: the manager, whoever a task on the project or
  a project under it is assigned to, and whoever logged time on it. Each says
  how much is on them (open tasks, and how many are late) and how much they
  have put in (hours this month and in all), read as the reader reads tasks
  and timesheets.

  Adding or removing a member is a change to the project, made by whoever may
  change it, and saved as the form saves it, so ERPNext's own rules on members
  (the welcome mail, who sees the project in the portal) run as they do there.
- `billing.py` `invoices` — the Invoices view: Sales Invoices naming the
  tree on the invoice or a line, read as the reader reads them.
- `retainer.py` — a Retainer's months: `months` (hours used of the
  allowance, over, the month's invoice), `waiting`, `asked` (what Invoice
  Month would bill) and `invoice_month`, a draft Sales Invoice with the fee,
  the hours over at the month's average rate (`over`, `rate`, pure) and the
  month's billable time on its Time Sheets table. The month is
  `one_retainer_month` on Sales Invoice. Invoice Time refuses a retainer.

  A month is a calendar month from the one the project starts in. Each says
  how many hours were used of the allowance (`one_monthly_hours`), how many
  over, and whether it's been invoiced: a Sales Invoice for the project with
  its **Retainer Month** (`one_retainer_month`) set to the month.

  **Invoice Month** (`invoice_month`) is a draft Sales Invoice, opened unsaved
  as Invoice Time's is: one line for the month's fee, and, when the month went
  over, one for the hours over at what the month's billable hours were billed
  at on average. The month's billable time is put on the invoice's Time Sheets
  table, so submitting it marks that time invoiced (ERPNext's
  TimesheetBillingService) and Invoice Time never bills it again.
- `heads.py` — the band and the hours chart as the project's Record Head
  (one/head.py), each a measure or a chart over `overview`.
- `view.py` — the project's page (`page/project_view`): `said` gives it, in
  one call read as the reader, the head, the kind's four cards (`cards`) and
  its Overview, from overview.py, money.py, budget.py, billing.py and
  tree.py. `needs` is Needs You; `contract` is the project's Sales Order or
  the first one against it; `quotation` is its open quotation (not extra
  work) while nothing is ordered, which the first Fixed Price card shows as
  **Quoted** (`_first`). kinds.py's `add_contract` makes the contract after
  the project, as `_contract` does for the New Project dialog, in the
  customer's party account currency. `work` gives the Tasks, Board and Timeline views
  the tasks of the project and its sub-projects, the people they're assigned
  to, and the statuses and priorities to pick from; `files` and `updates`
  give the Files view and the Overview's updates. The page's body is the
  `onedesk.project` island, `frontend/src/project/ProjectPage.vue` and the
  views beside it, built from the kit in `frontend/src/kit`
  (docs/ISLANDS.md). A task is changed as desk changes it
  (`frappe.client.set_value`, `insert`, `assign_to`), and the views follow
  the Task list through desk's `list_update`. Desk keeps its head through
  `onedesk.island_page`, and the island reports the name, the status and the
  actions. `public/js/project_new.js` hands `/desk/project/<name>` to the
  page; the form is the same address with `?edit=1`, and a new project's form
  stays. The page follows the record through the kit (`follow`, desk's
  `doc_subscribe` and `doc_update`) and its money through `one_project_money`.

  The page is `page/project_view` (public/js/project_page.js), opened at the
  project's own address. `said` gives it the head (the kind, status, health,
  the main action), the title line, the kind's four cards and its Overview.
  Everything is read from the modules that work it out already: overview.py
  (tasks, dates, hours), money.py (both sides), budget.py (cost types),
  billing.py (time not invoiced) and tree.py (sub-projects). It reads as the
  person asking and checks they may read the project.
- `public/js/project_actions.js` — Board, Schedule, Group Under New Project,
  Save as Template, Invoice Time and Post Update, for the page and the form
  alike. `public/js/project.js` is the form: those as its buttons, and
  Calendar; `public/js/project_template.js` is a template's New Project.

### What OneTask has to keep doing for projects

OneTask is everybody's; these are the promises it makes to OneProject, and each
stage below that touches tasks keeps them:

- a task's people see it wherever it is, and a task in no project is its own
  people's alone (`one_task/access.py`);
- a sub-task is in its parent's project (`one_task/task.py`);
- the timer writes time against whichever project a task is in;
- My Tasks names the project a task is in — and, once there are sub-projects,
  the path to it.

### The plan

1. **The split.** *Done.* The project half of OneTask — the board, a project's
   calendar, task prefixes, the plan and the project settings — moves here,
   and OneProject gets its own place in the dock.
2. **Members.** *Done.* A project's Users decide who sees it and its tasks,
   instead of every Projects User seeing every project; a project listing
   nobody stays open. A task's own people still see it. Members of a project
   will see what is under it once there is something under it (`under`).
3. **Sub-projects.** *Done.* A Parent Project on Project, to any depth, so a separately
   billable piece — the handrails on a villa, a change request on a website —
   is a project of its own with its own quotation, sales order, time and
   invoices. A project cannot sit under itself. A parent shows its own figures
   and the whole tree's, worked out rather than stored, and its sub-projects as
   an indented list. **Group Under New Project** makes a parent above a project
   and moves it and any of its sub-projects under it. A sub-project takes its
   parent's customer unless told otherwise. The calendar includes the
   sub-projects' tasks, titled by sub-project; the board stays one project's,
   since ERPNext's board is a filter fixed when it is made.
4. **The overview.** *Done.* A project's page answers first: done so far, due against
   expected, cost against budget, billed against billable (each of the three
   with a line showing how far), overdue tasks and the next milestone, and
   beside them the hours logged on its timesheets a bar a week for twelve
   weeks, this week's in blue.
5. **The plan.** *Done.* frappe's Gantt over a project's tasks and its
   sub-projects', milestones on it, and dependencies that move across projects
   in one tree, not only within one. Three things of frappe's needed fixing for
   it to show anything: a task with no start date, a chart that never scrolled,
   and the view mode pills.
6. **Templates.** *Done.* ERPNext's Project Template starts a project with its
   tasks, sub-tasks and dependencies; a project that went well is saved as
   one; milestones, expected time and checklists come across; the project's
   prefix names them; templates are the team's, not their maker's. A template
   of a whole tree of sub-projects is not built: ERPNext's template is one
   project.
7. **Cost and billing.** *Done.* Time priced by Activity Cost, which ERPNext
   already did; a project's billable hours invoiced in one step, by activity;
   a quotation for extra work ordered as a sub-project of the project it is
   for. A rate per customer or per project is not built: ERPNext prices time
   by person and activity only.
8. **Status updates.** *Done.* ERPNext's Project Update asks the team for a
   note on a schedule — in One, and by mail where there is mail — the note is
   written on the project's page or by replying, and the answers are in the
   project's activity. Asking the customer is stage 9's.
9. **The customer's view.** *Done.* ERPNext's portal shows a customer their
   own projects: a customer invited from their contact can sign in, reach the
   list and open a project, which shows its progress, end, milestones,
   sub-projects, tasks, order and invoices, and nothing of the team's. A
   customer adding tasks or commenting is not built.
10. **Workload.** *Done.* Who has how many hours of open work in a week, from
    the expected time left on the tasks assigned to them, against their working
    days less holidays and leave, with what is late and what is not estimated.
    Moving work between people is done on the tasks, not here.
11. **The old OneProject.** *Done.* Read from OneApp's `56216d9a`, where it
    left: a space manifest over the same ERPNext doctypes, with seven screens.
    Taken: **Health** and **Project Manager** on a project, a **Milestones**
    list across projects, and boarding checklists kept out of the portfolio.
    Already here: task prefixes (its Key), the checklist, the Gantt with
    dependencies and milestones, sub-tasks, the project's tasks, time and
    invoices as connections, templates, and the rate card under Setup. Not
    taken: its own board columns, labels, ranks, cycles and assignee mirror
    (OneTask's stage 6 says why); a colour per project; a board of projects by
    health, which anybody can make from Health with frappe's Kanban; its
    dashboards and charts beyond the page's one hours chart; a Gantt of projects, since
    a project's own schedule is the one people plan with; a read-only
    Invoices screen, which is the project's connections; and members seeing
    only their own timesheets, which would stop a project lead invoicing
    their team's time. Its one live leftover in OneApp, OneBook reading the
    OneProject catalogue row on import, is fixed there.

### access.py

ERPNext lets only a **System Manager** open **Projects Settings**, which the
rail links to: whether a timesheet may overlap another and whether a task's
dates are checked against its project's. A Projects Manager keeps them.

ERPNext keeps **Budget** to the books, so a project manager could not set a
project's budget by cost type. A Projects Manager now keeps the budgets of
projects, and only those (budget.py `kept_to_projects`): a budget against a
cost centre stays the books'.

The books read every **Project**, since they invoice its time and progress
(members.py sees to which ones).

A role that reads it already, by ERPNext's rules or the workspace's, keeps
what it has (one/roles.py `give`). Tasks and project templates are
one_task/access.py and `_templates` here.

### agreement.py

A project's contracts are ERPNext's **Contract**, with `document_type`
Project and `document_name` the project, so ERPNext's own form, statuses
(Unsigned, Active, Inactive) and daily status update all hold. `draw_up`
fills the party (the customer, or a supplier from `suppliers`: those with a
submitted purchase order on the project or those under it, and those on its
contacts), the dates and `contract_terms`: a Contract Template's wording
rendered as ERPNext's form renders it (`get_contract_template`), else, with
the customer, the project's Terms and Conditions. `contracts` lists those not
cancelled on the project and those under it with no permission check, since
whether they are signed is the project's business, and gives a route only to
whoever may read contracts. `main` is the customer's for About: the latest
signed, else the latest. `asks` adds the Needs You rows, and `_renewed` keeps
a contract quiet once a later signed one with the same party runs past it. No
grant is added. Contract stays with ERPNext's roles, because employment
contracts are Contracts too.

### activity.py

The Activity view puts the project's history beside frappe's own timeline of the project,
which keeps its comments, its emails and the changes to its fields (Project
tracks its changes, `custom/project.json`). Each row here is one of frappe's
ActivityTimeline rows (`type`, `key`, `timestamp`, `author`, `data`), with a
`kind`: `money` for documents, `work` for the rest.

A document shows when it was made, submitted and cancelled, read from the
Version frappe keeps of it, or from the document itself where its type keeps
none. Tasks added in one day are one row, as are a person's hours in a day and
the files somebody added in a day.

### buying.py

The orders for goods leave out subcontracts, which have their own card
(money.subcontract). An order for goods says how much is received and billed,
and when it's billed ahead of delivery. The Suppliers view lists them beside
the subcontracts, the project's and those under it, each opening its document
(`papers`).

Each is ERPNext's own document, naming the project on its lines (chain.py).

### contacts.py

Each person outside the company on a project is a row of its **Contacts** (Project Contact): a **Role**, the
**Supplier** or, for anyone who isn't one, the **Company**, a frappe
**Contact** with their email and phone, and a **Note**. The Team view lists
them under **Contacts**, and Suppliers lists the suppliers among them
(`contacts`). Adding one is changing the project (`save`, `remove`); the
Contact is linked to the project too, as frappe links a contact to any record,
so the project is among the contact's own links.

### terms.py

A project's `one_payment_terms` (Payment Terms Template) and `one_terms`
(Terms and Conditions), also on Project Template with `one_retention` and
`one_retention_handover`. `defaults` gives a new project the customer's own
payment terms (ERPNext's `get_payment_terms_template`: customer, then group,
then company) before the template's, then the company's. The wording is the
template's, else the company's `default_selling_terms`.

`of` is what a project is billed on: its own, else the nearest project
above it with some, with the one they come from. `carried`, Invoice Time,
Invoice Month and the New Project contract all read it.

`give` puts both on a document not saved yet: the template, which ERPNext
turns into the payment schedule, a due date from it (ERPNext's
`set_missing_values` dates an invoice by the party's terms, not the ones on
it), and the wording rendered as ERPNext's form renders it.

`carried` runs before_insert on Quotation, Sales Order, Sales Invoice and
Purchase Invoice. A document made from a single order or quotation starts
with that one's terms, as ERPNext's Fetch Payment Terms from Order does. A
selling document for a project otherwise starts with the project's. A
purchase invoice made outside an order keeps ERPNext's. Payment terms someone
picked, other than the party's own default, are kept, and so is wording other
than the company default.

Bill Progress gives the invoice the order's terms before ERPNext's
`set_missing_values` (ERPNext's mapper leaves `payment_terms_template` off),
then splits the schedule for retention (progress.py `_retain`). Moving an
order's Retention Due moves the date on its submitted invoices, their
payment schedules and their Payment Ledger Entry and GL Entry rows
(progress.py `_due`), which the receivables and payables reports age by.

library.py makes the payment terms and wording a preset names
(`library_terms.json`) the first time it is copied in.

### site_time.py

HRMS's attendance says who worked and for how long, for payroll; it has no
project. ERPNext's project costing reads only timesheets. So a day on site is
written as the timesheet ERPNext expects, made from the attendance, and HR
keeps attendance as it is:

- **Attendance submitted** (`attended`): when the day was at the site of an
  open project counted by attendance (`project_at`), a Timesheet for that
  person is made and submitted. It has one row on the project, the
  attendance's working hours (or HR Settings' standard day, half of it for a
  Half Day), at Projects Settings' **Activity for Days on Site**, billable
  when the project bills hours (`hours.bills_hours`). Its cost is the person's
  Activity Cost, as any timesheet's.
- **Where they were**: one of their check-ins that day inside the site (its
  own circle, or any clock place drawn on it). With no position on any
  check-in, a shift assignment that day naming the site.
- **Attendance cancelled** (`cancelled`): its timesheet is cancelled too,
  unless it's already invoiced, which ERPNext refuses.
- A timesheet made here names its attendance (`one_attendance`), so neither is
  made twice.

A day that can't be written (a timesheet already covering those hours, say)
doesn't stop the attendance. It's logged in the Error Log for HR to see.
