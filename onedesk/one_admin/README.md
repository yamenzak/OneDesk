# OneAdmin

Written by hand. Everything above **Under the hood** is for the operators who
use OneAdmin, and OneAI reads it to answer "how do I…" questions. Under the
hood is for the people who build it.

OneAdmin is the console One is run from. It holds the workspaces customers pay
for, the jobs that build and close them, their domains, the price list,
signups, credits and OneAI's models.

It's only on the admin site, and only for **One Operator**. No one on a
customer's workspace can open it, whatever roles they hold there.

One has no desk to give that role from. When the admin site is set up or
migrated and there are no operators yet, its workspace administrators
become operators. **Operators** in OneAdmin Settings adds anyone
else from the workspace's people, and removes them, keeping the last one.

## Our own workspace

The admin site is **Four Degree Labs**' own workspace of One (`4dl`). It uses
One as a customer does, OneAI included, and is marked **Internal** on the
Workspaces list.

It differs from a customer's workspace in three ways:

- It isn't billed. It has no plan and no Stripe subscription, so it never
  becomes overdue.
- Its OneAI is never refused for lack of credits.
- Its AI cost is an internal cost, not a sale. AI Usage shows it as
  **Internal Use** and charges nothing for it, and Home doesn't count it as a
  live customer.

It is created, and the admin site linked to it, by `house.link` after every
migrate, whenever the admin site isn't linked yet. A new admin site is only
flagged as one after its first migrate, so a patch that ran once at install
would have found nothing to do.

## Home

**OneAdmin** in the dock opens **Home**.

The number cards at the top each open the list they count:

- **Live**: workspaces serving their customers.
- **Building**: workspaces still being built.
- **Owing**: workspaces overdue or suspended for non-payment.
- **Failed**: jobs that stopped on a step.
- **Paid, Not Built**: paid signups with no workspace.

Below them is **Needs You**. Click a row to open the record. Home updates
live, without reloading.

### Needs You on Home

**Needs You**, on OneAdmin's Home, lists what needs an operator, most pressing
first. Each row says what it is, why, and since when, with one action:

- **Failed job**: what it was doing, the step it stopped at and the error.
  **Resume** runs it again from that step. Every step is safe to run twice,
  so this never builds a second site.
- **Paid signup with no workspace**: whose it is and why it stopped.
  **Build Workspace** creates the workspace, as paying would have.
- **Workspace owing**: overdue or suspended, and since when. Open it to act.
- **Domain**: waiting over a day for DNS, or not working. **Check Again**
  asks Cloudflare for its status.
- **Slow build**: a new workspace still waiting on the hosting provider after
  three hours. Waiting never fails a job, so this is where a stuck build shows
  up. Check the site in the hosting provider's dashboard.
- **Stalled job**: due but not run for fifteen minutes, with **Run Now**.
- **Over database**: a workspace holds more than it bought. The hosting
  provider sets no limit on dedicated servers, so OneAdmin watches it.
- **Server filling up**: at four-fifths of its **Most Workspaces**, full, or
  no open server left for new or EU workspaces. Buy the next one before a
  signup fails.
- **Update available**: for the bench group new workspaces use, with the apps
  that have one. Deploy it in the hosting provider's dashboard. It updates
  every workspace on that bench group at once.
- **Wrong price**: a problem Price Check found.
- **No model**: an AI action no offered model can run.

## Workspaces

**Workspaces** lists every customer workspace with its name and slug, status,
plan, owner and storage against its plan's limit (red when over). Filter by
status, plan, jurisdiction or account. **Account** is the One account that
holds it (see Your One account).

A workspace is read-only. It's the record of what happened to it. The top
shows its address and, if it owes, when it moves to the next status. Below
that are its **Plan**, **Storage**, **Credits** left and OneAI **Used This
Month**. Placement and Site are collapsed. Open them when something breaks.

### Statuses

A workspace is built, then **Live**. When a payment fails, or its
subscription is cancelled in Stripe:

1. **Payment overdue** for 7 days. It keeps working.
2. **Suspended** for 14 days. No one can sign in, and nothing is changed.
3. **Archived** for 30 days. The site is deleted after a backup. Files stay.
4. Then its files are deleted.

It moves one step a night. The periods are set in **Settings**. Paying before
the site is deleted brings it back once nothing is left unpaid: at once from
overdue, and from suspended by a job that serves the site again. A payment
after that is sent to the operators (Paid While Archived).

A workspace whose build **Failed** stays as it is until an operator resumes
its job or archives it.

### Buttons

Each button moves the workspace one step and asks first.

- **Mark Overdue**, **Suspend**, **Archive** and **Delete Files** move it to
  the next status now. Archiving and deleting files can't be undone.
  **Archive** also closes a workspace whose build failed, and cancels its
  subscription; its owner isn't emailed.
- **Restore** brings back an overdue or suspended workspace.
- **Refresh** › **Measure Storage** or **Refresh Domains**.
- **Billing** › **Invoices**, **Give Credits** (with a note and an optional
  expiry), **Credit Ledger** and **AI Usage** by model.

Below the fields are its **Jobs**, **Log** and **Domains**, its **Customer**
in the books and the **Signup** that paid for it.

The owner is emailed when the workspace is suspended, archived (with the
deletion date) and restored, and when a payment fails (Payment Failed).
Overdue notices also show on their own workspace, which still works then.

### Closing on request

The workspace's billing contact can close it from its Plan and Credits page
(`closing.py`).

- **Closing On** is set 14 days out, and the subscription ends with its
  period.
- Operators get **Workspace Asked to Close**, and the Log records it.
- On that day the nightly run archives it with the usual Archive job, and the
  owner gets **Workspace Closed** instead of Workspace Archived. It's then
  deleted on the Archived schedule.
- Until that day, they can keep it open, which clears the date. After it,
  bringing it back means restoring from the backup.

Their One account shows it as Closing, then Closed, with the deletion date.

## Jobs

A **job** builds a workspace or moves it to another status, one step at a
time. There are six types:

- **Provision** builds a new workspace. It chooses a server, checks the name
  is free, creates the site at the hosting provider, waits for it, sets up
  the address, configures the site, invites the owner and marks it live.
- **Suspend** and **Restore** stop and restart the site.
- **Archive** deletes the site after a backup, cancels the Stripe
  subscription so it isn't invoiced again, and removes its mail route.
- **Drop** deletes the files.
- **Install App** installs a private app a workspace claimed with its code.
  It checks the app is on the bench group, asks the hosting provider to
  install it, and waits until it is. A failed install leaves the workspace
  Live.

The server is the emptiest open one in Settings › Servers (an EU one for an
EU workspace), and is shown on the workspace as **Server**. A bench group
missing one of the apps a workspace needs fails the first step, naming what
to add.

### Following a job and resuming one

**Jobs** lists the ones not done, with the workspace, type, status, current
step and last update. Jobs run every two minutes.

- **Waiting to run**: its next step is due.
- **Waiting on** the hosting provider (the status names it): a step waits on
  the hosting provider, such as a site being built. This is checked every
  minute and never fails the job. A slow build shows on Home after three
  hours.
- **Failed**: a step that errors is retried, less often each time. After
  twelve tries the job fails and operators are notified.
- **Done** with a note: a Suspend, Archive or Delete Files job checks again
  before the step that can't be undone, and stops there if the workspace was
  paid for, restored or kept open since it was queued.

Open a job to see every step, with done steps ticked, the current one marked
and a failed step's error under it. **Resume** runs a failed job again from
the step it stopped on. Every step is safe to run twice.

A job that was due and hasn't run for fifteen minutes shows on Home with
**Run Now**, which runs its next step at once. Usually the scheduler has
stopped, or a worker died while holding it.

**The new owner** is invited at the **Inviting the owner** step. The site
makes whoever paid its first administrator and emails them a link to choose
a password, valid for a week. When the job finishes they get **Workspace
Ready** with the address.

## Private Apps

A **private app** is an app made for one customer. Add one under **Private
Apps** with the app's name as in its `hooks.py`, its title and one sentence.
**New Code** makes a code for one workspace and shows it once; send it to
them. A new code for the same workspace replaces the old one.

The workspace types the code into Apps. That queues an **Install App** job,
and the workspace's row under **Workspaces** on the app says Installing,
then Installed. A workspace that has claimed an app keeps it: its row can't
be removed and the app can't be uninstalled. Turn **Enabled** off to stop
new codes working. Writing one, and putting it on the bench group, is
`docs/PRIVATE-APPS.md`.

## Price List

**Price List** is everything One sells. It's the one OneAdmin screen
operators edit. The signup page, a customer's Plan and Credits page, Plan
Calculator and Price Check all read it, and each offering is an Item in the
books. The list shows plans, then add-ons, then credit packs, each by price.

There are three types:

- **Plan**: what a workspace is on. It has a monthly (or one-time) price, an
  optional free trial, and quotas for storage, database, seats and monthly
  credits. Zero means unlimited.
- **Add-on**: adds one thing, in one size, to a plan, paid monthly with it.
  For example 50 GB of storage or 5 seats.
- **Credit Pack**: bought once, for OneAI credits that don't expire at the
  end of the month.

**Changing an offering**:

- Prices never change for existing customers. Stripe keeps each subscriber
  on the price they signed up at, and the next sale creates a new Stripe
  price.
- Quotas apply the next time the customer changes their plan or add-ons.
- The top of each offering shows how many workspaces have it.

**Disabling an offering** removes it from the signup page and customers'
choices. Workspaces already on it keep it. An offering a workspace has can't
be deleted. **View Signup Page** in the list's menu opens the page as a
customer sees it.

## Price Check

**Price Check** shows whether the price list makes sense. For every enabled
offering it shows what it **Includes**, its **Price**, its monthly **Cost**,
its **Margin** (price as a multiple of cost) and, for a plan, how much it
**Saves** over the plan below plus add-ons. Problems come first: **Wrong** in
red, **Close Calls** in orange.

It checks that:

- every price covers its cost with the **Target Margin** (2× unless Settings
  says otherwise)
- each higher plan gives at least as much of everything, for more
- moving up a plan is cheaper than buying the difference as add-ons
- the smallest add-on is cheaper than moving up a plan
- a bigger size of an add-on costs no more per unit

Costs (per workspace, seat, GB of storage and database, backups and credit)
and the target margin are set in **Settings**. **Edit Costs** in the
report's menu opens them. **Include Disabled** checks withdrawn offerings
too.

Saving an offering or the costs shows any new problems right away, and
anything Wrong stays on Home until it's fixed. OneAI answers **What should
we change?** on the report.

## Plan Calculator

**Plan Calculator** shows what a customer should buy. Enter the **Seats**,
**Storage (GB)**, **Database (GB)** and **Monthly Credits** they need. It
lists every plan with the add-ons that reach those needs, cheapest first,
showing what the plan **Includes**, the **Add-ons**, the **Monthly** price,
the **Cost**, the **Margin** and the **Difference** from the cheapest. Credit
packs aren't included because they're bought once.

It's the same calculation a workspace's Plan and Credits page uses when an
administrator adds to their plan, so the result matches what they'll be
offered.

For an existing customer, pick the **Workspace**. The needs fill in from what
it has now: paid seats, used storage and database, and the higher of its
monthly credits or this month's spend. The summary shows what it **Pays
Now**, and its plan's row says **Current plan**. Change any need to compare,
for example ten more seats.

Only operators see it, and it changes nothing. OneAI answers **What should
they buy?** for needs in words or a workspace by name.

## The signup page

**/start** on this site is where a customer asks for a workspace, before
they have an account. They:

1. Enter the workspace name and see its address as they type
   (`acme.t.4dl.app`, from Tenant Domain in Settings).
2. Enter the email for the first account and the receipt.
3. Pick where files are kept.
4. Pick a plan.
5. Click **Continue** to pay in Stripe.

Above Continue, the page says that continuing accepts the Terms of Service
and Privacy Policy, both linked to **/legal**, where every agreement can be
read without signing in.

- **Where files are kept** shows only when the EU bucket is set in Settings.
  The European Union keeps the workspace's files in the EU. The workspace
  itself runs on the main cluster. This can't be changed later.
- **Plans** are the enabled plans in Price List, cheapest first, each with its
  trial, description, storage, database, people and monthly credits.
- **Signed in to a One account**, the page doesn't ask for an email. It shows
  who's signed in, and the workspace joins that account. Otherwise it offers
  **Sign in**, and the email entered becomes the account (or joins an
  existing one).

### The welcome page after paying

Stripe returns them to **/welcome**, which shows the workspace's status:

- While it's being built, the page checks every ten seconds. After fifteen
  minutes it says it's taking longer than usual.
- When ready, it shows the workspace name, the trial end date and **Open it**,
  which goes to the workspace's sign-in on its own domain if it has one.
- A failed build shows a reference to quote.
- Once paid, it says the workspace is in their One account, with **Sign in**.
- Closing Stripe's page frees the name at once. **Start again** returns to
  the form with the name and plan filled in.

The welcome page opens only with the key in the link from Stripe and One's
emails. A request name alone shows nothing.

Someone who filled in the page but never paid gets **Finish Signing Up**
once, a day later, with a link back to payment. Neither page needs a sign-in,
and neither changes anything but the signup.

## Your One account

Whoever pays for a workspace gets a **One account** on this site under the
email they paid with. It's created when the payment lands and holds the
workspace. Paying for a second workspace with the same email adds it to the
same account.

Accounts sign in at **/login** with **Login with Email Link**. One emails a
link that works once, for a few minutes (**Sign-in Link**). There's no
password. Only customer accounts can sign in this way. An operator asking for
a link gets nothing, the same as an unknown address, and signs in with their
password.

The account has three tabs:

- **/account** lists its workspaces and their status: **Being built**,
  **Live**, **On trial** (with the end date), **Payment overdue**,
  **Suspended** or **Archived**. One that owes comes first, says how many
  days are left before the next status, and has **Pay**, which opens Stripe's
  page for its invoice and card. One that's running has **Open**, to its own
  sign-in. **Start another workspace** is at the bottom. Workspace Ready
  links here too.
- **Invoices** lists every invoice across its workspaces, newest first, with
  the date, workspace, number, amount and status (**Paid**, **Due**,
  **Unpaid** or **Cancelled**). Each has **View** and **PDF**, and a due one
  has **Pay**, all Stripe's own pages. **Card and billing details** has
  **Update card** per workspace, since each workspace is billed separately;
  it draws Stripe's form in the page rather than leaving it.
- **Profile** has the account holder's name and email. A new email gets a
  link valid for an hour. The account switches only once it's followed, and
  the old address is notified (**Confirm Your New Email**, **Account Email
  Changed**).

The account doesn't sign in to any workspace, and it has no desk.

### Changing who pays

A workspace administrator can make someone else the billing contact from the
workspace's Plan and Credits page (**Who Pays**).

- The workspace moves to that email's One account, created if needed.
- The new holder gets **Workspace Moved to You**, and the previous one
  **Workspace Moved Away**. The log records **Account Moved**.
- From then on, suspension, archive and restore emails go to the new holder.

## Signups

**Signups** are the people who asked for a workspace on the signup page,
before and after paying. The page creates them, and Stripe's payment
confirmation builds the workspace. Each has a status:

- **Not paid**: filled in the page but never paid.
- **At checkout**: at Stripe now, or was.
- **Paid, not built**: paid, but the workspace wasn't created.
- **Paid, build failed**: building stopped. The note at the top says why.
- **Being built**: the workspace's job is running.
- **Built**: the workspace is live.
- **Abandoned**: not paid within seven days, or closed at Stripe. The name is
  free again. If they pay later, the workspace is still built unless the
  name was taken in the meantime.

A paid signup with no workspace is the most urgent case, so it shows on Home.
**Build Workspace** on it tries again. Check why it stopped first. A name
taken since, or a refusal from the hosting provider, will stop it again.

Once there's a workspace, it's linked with **Open Workspace**. **Open in
Stripe** in the menu finds the payment, and the lead and deal for it are
under Outcome.

Only operators see signups, and no one edits them. On a paid signup with no
workspace, OneAI answers **Why wasn't this built?**.

## Credits

**Credits** is every change to every workspace's OneAI credits, one row each,
never edited. A workspace's balance is the sum of its rows.

- **Grant** adds credits: a plan's monthly credits (expire at month end), a
  credit pack (never expire), or credits an operator gave with **Give
  Credits** (with a note and an optional expiry).
- **Spend** is one OneAI call, taken from the grant that expires soonest. It
  shows the **Model** used. A spend beyond the balance is owed and has no
  grant.
- **Refund** returns an overcharge.

The list shows grants, refunds and revoked credits by default. Individual
calls, hundreds a day, are one filter away, and **AI Usage** totals them by
workspace and model. A grant shows what's left and until when. A spend shows
which grant it came from.

**Revoke Credits** on credits an operator gave removes what's left, with a
reason. It adds a spend for the rest rather than deleting the grant, so
what was spent stays spent. Credits from a plan or pack can't be revoked
because they were paid for.

When an operator gives credits, the workspace's administrators get **Credits
Added** with the note and expiry. Only operators see the ledger. On an entry,
OneAI answers **Where did the credits go?**. An entry prints as **One Credit
Entry** (the workspace, the kind, how many, from where and until when).

## Models

There is no list of models here any more. Which model does each kind of
OneAI work, at each tier, is code: `one_ai/models.py`, with Google's prices
beside it, checked against what Cloudflare and Google offer by
`scripts/models.py` (docs/AICENTER.md, Models). A workspace picks a tier,
never a model, so there is nothing for an operator to offer, price or
default. **Test Gateway** in Settings asks the Talk model for one sentence,
to prove the gateway is set up.

## AI Usage

**AI Usage** shows who spent what on OneAI, on what, and the margin. Pick the
dates (this month by default) and group **By** Workspace, Model, Action
(the OneAI feature that made the calls, such as Chat, Summarise, Read Scans
or Intake), or a workspace by model or action.

Each row shows:

- **Calls**
- **Credits** charged
- **Charged**: those credits in dollars, at the smallest credit pack's price
  per credit
- **Cost**: what the provider charged
- **Margin** between them

The summary shows the same for the whole period, green when OneAI made money.

Charged is the list price of the credits. A plan's monthly credits and
discounted packs earn less. Calls from before actions and costs were recorded
show "Not recorded", with a cost estimated from their markup. Only operators
see it. OneAI answers **Who is spending the most?**.

## Domains

**Domains** lists every custom domain on customer workspaces, such as
`crm.acme.com`, with the workspace, status (**Working**, **Waiting** or **Not
working**), Cloudflare's reason when it isn't working, and which is the
**Main** address. Every workspace also has its One address
(`acme.t.4dl.app`), which always works and isn't listed here.

Customers manage domains on their own workspace, under **Workspace ›
Domains**. They add a domain, create a CNAME record in their DNS pointing
to their One address, and choose the main address used in links and emails.
The page also shows a TXT record, `_one.<domain>` with the same value: it
proves the domain is theirs where the CNAME can't be read, as behind a
proxy. Operators can't add, remove or set the main domain for them, because
it's the customer's DNS.

A domain stays **Waiting** until its DNS record is right. Until One reads the
CNAME or the TXT record the domain isn't routed at all, so nobody can claim
a domain whose DNS they don't run. Then Cloudflare keeps checking and issues
the certificate. One checks each waiting
domain nightly, and **Check Again** checks now. A domain's page shows the
CNAME record it needs, Cloudflare's error and how long it has waited. A
domain **Not at Cloudflare** has been lost there, and the customer can remove
and re-add it.

A domain waiting over a day, or not working, shows on Home and in the
morning's **Domains Waiting**. The customer's administrators are notified on
their own site when a domain starts or stops working.

## Log

**Log** is what happened to each workspace, newest first, recorded
automatically. No one edits it. Each row shows the workspace, what happened,
who did it and when.

- **Overdue**, **Suspended**, **Archived**, **Dropped** and **Restored**: the
  new status and why (a failed payment, the grace period ending, a payment,
  an operator, or the hosting provider).
- **Plan Changed** and **Add-on Changed**: the customer changed their plan
  on their workspace.
- **Over Storage**: it holds more than its plan allows, with both sizes.
  Recorded when it goes over, then again only after it grows by a gigabyte or
  a month passes. It also shows on Home until it's back under.

**By** is **Customer** (from their workspace), an operator by name (for a
button or a job they started), or **One** (the schedule, a payment or a
nightly measurement). A row from a job links to it.

Click a row to open its workspace. A workspace's **Activity** shows its log
next to its changes, and a job lists the rows it wrote.

## Settings

**Settings** is what OneAdmin runs on, in four tabs.

**Connections**

- The hosting provider, in the first section: the account the sites are
  built on. The servers are rented from it, and customers never see it.
  Includes the **Bench Group** every workspace runs on, the **Site Plan** for
  each site (one of the provider's free Unlimited plans, which only sets daily
  CPU time), and **Servers** (below).
- **Cloudflare**: one **Master Token**, made in Cloudflare from the **Create
  Additional Tokens** template. **Set Up Cloudflare** uses it only to make
  One's own three tokens, each allowed only its own work: **OneAdmin** for
  OneAdmin's calls, **OneAdmin Storage** for the two R2 buckets, and **OneAI** to
  run the AI Gateway. It then finds or creates everything else and shows each
  step under **Last Setup** as it ends. It runs in the background, so leaving
  the page stops nothing.
- Pressing it again checks everything and mends what is missing. A run cut
  off anywhere loses nothing: each thing is saved the moment it is found or
  made, everything is looked for by name before anything is made, and a token
  whose secret was never saved is rolled for a new one.
- The certificate for every workspace's address needs **Advanced Certificate
  Manager**, a paid add-on, turned on for the zone in Cloudflare. Setup
  checks for it and says so; until it is on, workspaces don't open.
- The master token can make any token on the account. You can delete it in
  Cloudflare once setup is done; setup then asks for it again only when a
  token needs mending.
- The R2 buckets, Stripe's keys and the AI Gateway.
- **Sender Email** (noreply@4dl.app): where One's own emails come from, such
  as sign-in links, signups and customer notices. Set Up Cloudflare turns on
  sending for its domain and makes it this site's outgoing account, so those
  emails go straight through Cloudflare. Workspaces still send from their own
  addresses on the mail domain.

Keys show as dots and are never read back.

**Money**

- **Credits per Dollar**: what a dollar of provider cost becomes in credits.
  This isn't the sale price of a credit, which is set by the credit packs.
- **Default markup**. With Credits per Dollar, it prices every AI call.
- What each thing costs and the target margin, used by Price Check and Plan
  Calculator.

**Grace Periods**

- The days a workspace spends overdue, suspended and archived before the next
  step.

### Servers

**Servers** lists the servers new workspaces are built on. To add one:

1. Buy it from the hosting provider, add it to the bench group and deploy.
2. Add a row here with its name. Its **Region** fills in from the hosting
   provider on save.
3. Tick **EU** for a server in the EU. Workspaces that asked to keep data in
   the EU only go on those.

Untick **Open** to stop a server taking new workspaces. **Most Workspaces**
sets when it's full (0 is no limit). A new workspace goes on the emptiest
open server that allows it, has room and has the bench group. If none does,
its job fails saying what to buy or add, and **Resume** places it once
there is one. Home warns when a server is four-fifths full.

The note at the top lists what's missing and what that stops (for example,
without the Stripe webhook secret every payment is refused). **Test Gateway**
makes one real call. Saving notifies the other operators what changed and
who changed it (**Settings Changed**). Keys show only as changed. OneAI
answers **Is everything set up?**. Only operators see this page.

## Notifications

OneAdmin tells operators what needs them, and emails customers about their
account and workspace. Both lists are below.

### What operators are notified of

Operators are notified of:

- **Job Failed**: a job stopped, with the step and error.
- **Signup Not Built**: someone paid and their workspace couldn't be built,
  with the reason.
- **New Signup**: someone paid for a new workspace.
- **Workspace Owing**: a workspace became overdue or was suspended.
- **Workspace Asked to Close**: a billing contact asked to close a workspace.
- **Settings Changed**: another operator saved Settings, with what changed.
- **Domains Waiting**: each morning, domains waiting over a day or not
  working.
- **Paid While Archived**: a payment arrived for a workspace that's already
  archived or dropped. The payment is kept. Rebuild it from its backup or
  refund it in Stripe.
- **Build Slow**: a build has waited on the hosting provider for hours.
  Waiting never fails a job, so this is the only notice; its payer is mailed
  Workspace Delayed at the same time.
- **Server Filling Up**: a server new workspaces go on is near its limit, or
  full, once for each.

### What customers are emailed

Customers are emailed:

- **Sign-in Link**: when an account holder asks to sign in. Can't be turned
  off.
- **Confirm Your New Email** and **Account Email Changed** (to the old
  address): when an account holder changes their email.
- **Workspace Moved to You** and **Workspace Moved Away**: when billing moves
  to another account.
- **Workspace Delayed**: once, if a paid workspace couldn't be built or its
  build is taking hours, so a payment is never followed by silence.
- **Payment Failed**: when their card is declined, with the date the
  workspace is suspended.
- **Trial Ending**: three days before a free trial ends and the card is
  first charged.
- **Finish Signing Up**: once, a day later, if they never paid.
- **Workspace Ready**: when it's built (see Jobs).
- **Workspace Suspended**, **Workspace Archived**, **Workspace Closed** and
  **Workspace Restored** (see Workspaces).

Each can be reworded on the admin site under Automation › **Workspace
Notifications**, where they're listed under OneAdmin, and turned off except
the Sign-in Link, which nobody could sign in without. Each operator chooses
how they get theirs under You › Notifications.

## Asking OneAI

OneAI offers these questions. It reads what the screen shows and changes
nothing.

| Where | Question |
| --- | --- |
| Home | **What needs me today?** |
| A workspace | **How is this workspace doing?** (standing, plan, storage, credits, domains, recent jobs and log) |
| A failed job | **Why did this job fail?** |
| A waiting job | **Why is this job waiting?** |
| A domain not working | **Why isn't this domain working?** (what the customer has to change) |
| Price List | **How do our plans compare?** |
| A plan or add-on | **Who has this?** |
| Price Check | **What should we change?** |
| Plan Calculator | **What should they buy?** |
| A paid signup with no workspace | **Why wasn't this built?** |
| A credit entry | **Where did the credits go?** |
| AI Usage | **Who is spending the most?** |
| Settings | **Is everything set up?** |
| A model | **Is this model worth offering?** |
| Models | **Which actions have no model?** |

Resuming, building and checking again are Home's buttons, not OneAI's.

## Connections

- **From One**: A workspace's **Plan and Credits** page asks OneAdmin to change its plan or add-ons, buy credits, change who pays or close it. Its **Domains** page adds and removes its own addresses.
- **From OneAI**: Every OneAI call from a workspace is a row in **Credits**, with its model and action. **AI Usage** adds them up.
- **To One**: Each workspace's **Plan and Credits** page shows its plan, seats, storage, credits and invoices from OneAdmin. Whoever paid becomes the new workspace's first administrator.
- **To OneAI**: A workspace's credits and the models on offer decide what OneAI can run. A call with too few credits is refused, except on our own workspace.
- **To OneCloud**: A workspace's files are kept in the EU or globally, as chosen at signup. OneAdmin measures them each night against the plan.
- **To OneMail**: Mail to and from a workspace's addresses on the mail domain passes through OneAdmin. Sending is limited per hour and per day.
- **To OneCRM**: In our own workspace, each signup is a lead and a deal in OneCRM. Paying wins the deal and makes a customer, and a checkout left unpaid loses it.
- **To OneBook**: Each paid Stripe invoice is a sales invoice and a payment in our own OneBook, with Stripe's fee and any refund. Each offering on the Price List is an item there.
- **To OneLegal**: The agreements name the hosting provider, Cloudflare and Stripe as the companies that run workspaces and take payments. The Terms state how long a workspace stays overdue, suspended and archived.

## Under the hood

For the people who build OneAdmin. OneAI does not read past this heading.

- **The account** (`accounts.py`) is a frappe Website User named by its
  email, and `Tenant.account` links a workspace to it.
  `send_login_link` overrides frappe's on the admin site only, and
  `home_page` (hooks `get_website_user_home_page`) sends it to `/account`.
  An account has no desk and no roles; it signs in at `/login` and sees only
  the portal pages we give it. No doctype of ours stands in for a person.
  `owner_email` stays as what the workspace was bought with; `account` is
  who holds it now.

  On the admin site, `send_login_link`'s link is made by frappe
  (`_generate_temporary_login_link`, spent by `login_via_key`), and only for
  a Website User: an operator keeps their password and passkey, and a mailed
  link is not a door into the console. Every other address gets the same
  silent answer an unknown one does, so the page tells nobody who has what.
  The mail is ours (Sign-in Link, `tell.sign_in_link`), in the same words as
  every other.

  The account holds what spans workspaces: the list of them, starting
  another, every invoice and the card, and the holder's name and email. What
  belongs to one workspace (its plan, add-ons, credits, domains and people)
  stays in that workspace's own screens. The account links to them rather
  than copying them, so there is one screen per plan.

  How an account comes to exist:

  * **At payment.** `accounts.hold` runs from `signup.accept`, after the
    money. The signup's email becomes a Website User if it is not one, and
    the Tenant's `account` is set to it. Nothing is made for a signup that
    never paid.
  * **For workspaces from before.** The `accounts` patch makes one per
    distinct `owner_email` and sets `account` on each Tenant. Our own
    workspace (`is_house`) gets none.
  * **Signed in on `/start`.** No email box: `signup.start` takes the
    account's email over anything posted, so the workspace joins the account
    the person is looking at. A guest is offered Sign in; `/welcome` links
    back to the account.

  **The Stripe customer is not shared.** Every invoice event is matched to
  its workspace by customer: `stripe._ladder`, `books`, `billing.invoices`
  and `billing.invoice` all read `Tenant.stripe_customer`. Two workspaces on
  one customer would let one workspace's failed payment suspend the other.
  Sharing it means matching by subscription in those four places, proven
  against real Stripe events. Until then each workspace keeps its own
  customer, which is why `accounts.invoices` asks Stripe once per workspace
  and merges the answers newest first (one Stripe cannot answer for is named
  rather than failing the page), and why Update card and **Pay** are asked
  per workspace: Update card draws a setup checkout for that workspace's
  customer in the page, and Pay opens that workspace's billing portal. Pay goes to the portal rather than
  the workspace's Plan screen because a suspended workspace cannot be opened
  to reach it. Where Link is on in our Stripe account, Stripe offers the
  saved card to the same email at checkout anyway.

  **A new email** is proven by a mailed link (`ask_email_change`,
  `confirm_email`) before frappe's own rename moves the User and every link
  to it, `Tenant.account` included.

  **Who pays** is on the workspace's Plan and Credits for its
  administrators. `proxy.billed_to` calls `accounts.move`, which moves
  `Tenant.account` to that email's account (making it if needed), logs
  **Account Moved** and mails both holders. The ladder's suspension, archive
  and restore mails go to the account holder, and `hello` carries
  `billed_to` so the workspace shows who pays.
- **The portal pages** are `www/start`, `www/welcome`, `www/account`,
  `www/account_invoices` and `www/account_profile` (routed from
  `/account/invoices` and `/account/profile`) and `www/legal`, drawn
  in `public/css/one_portal/portal.css` to frappe-ui's look (a guest page loads no desk
  controls). `signup.available`, `start`, `pay` and `state` are the guest
  calls, each rate-limited; `start` takes the signed-in account's email over
  whatever the form sent. `Account Request.access_key` opens `/welcome`
  (`signup.owned`); `signup.remind` is the daily Finish Signing Up.

- **Two gates** (`site.py`): the site config key `one_admin` makes a site the
  admin site, and every OneAdmin doctype grants only One Operator. On any
  other site the role is taken off everybody, and the permission hooks refuse
  every record and every list.

  On the admin site, `site.first_operators` runs on migrate and when the
  setup wizard finishes: while nobody but Administrator holds the role, every
  enabled workspace administrator (`roles.administrators`) is given it. `site.make_operator` adds and removes
  the rest from OneAdmin Settings and refuses to take the last one.

  The same app ships to every site. It is a site config key rather than a
  role, a setting or a fixture, and that is the whole point: all three of
  those are editable from a desk by somebody holding System Manager. Nobody
  on a workspace is given it (`one/roles.py`), but a rule that holds only
  while nobody is ever given a role is a rule one mistake away from not
  holding. `site_config.json` is a file on the bench that no request can
  write. So the question "may this site provision workspaces and hold the
  ledger that bills people" has an answer the people being billed cannot
  change.

  **Hiding is Frappe's own permission machinery, not a layer over it.** Every
  doctype in the OneAdmin module grants exactly one role, `One Operator`, and
  grants it to nobody else — not System Manager, not Administrator by
  DocPerm. So a tenant site carries the tables and refuses every route a
  person has to them. Measured on the dev site as a System Manager who is not
  Administrator: `frappe.client.get` and `get_value` raise
  `PermissionError`, the desk's own form load raises it, `get_list` never
  gets as far as a query, and the doctype is absent from `can_read`, which is
  what the awesomebar and the report builder offer from.

  The exact claim is "no route a request has", not "no route".
  `frappe.get_doc` called from bench Python reads it, because `get_doc`
  checks permission on write and not on read — the check lives at the API
  layer. That is not a hole here: running Python on the bench means holding
  the bench, and a tenant holds a workspace. It is worth being exact about,
  though, because the day somebody writes a whitelisted helper that calls
  `get_doc` on one of these and returns it, the permission is not there to
  save them. Anything reading an operator doctype for a caller starts with
  `require_admin()`.

  `apply()` keeps that true in both directions on every migrate. On the admin
  site the role exists. On a tenant site it is removed from everyone who
  somehow has it, which is the case that matters: a site restored from an
  admin backup, or a workspace that was the admin site during development.

  **The role is not on its own, though, and it should not be.** A role is a
  row, and anybody who ever held System Manager on a workspace could grant
  themselves `One Operator` between one migrate and the next, and the
  permission machinery would let them in. Two hooks close that, and it takes
  two because Frappe asks the question in two different places:

  * `refuse_on_a_tenant` is the `has_permission` hook. Frappe calls it only
    when there is a document to judge, so it is what refuses opening a
    record. Frappe calls it after the role check has already passed and a
    False there refuses anyway, so a role somebody granted themselves on
    their own workspace buys nothing.
  * `nothing_on_a_tenant` is the `permission_query_conditions` hook. It is
    what every list, report and link search goes through, and on a workspace
    site it returns a condition nothing satisfies.

  Measured, because the first on its own looked like enough and was not:
  with the role granted by hand and the flag off, `has_permission("Tenant")`
  with no document still answered True and `get_list` returned rows. The hook
  had only ever fired for `One Admin Settings`, which is a Single and
  therefore always has a document. A gate that covers the form and not the
  list is not a gate.

  Both read `frappe.conf`, which is a file on the bench that no request can
  write. So there are two kinds of gate and they fail differently: the role
  decides what is *offered* — a rail, an awesomebar, a report builder — and
  the site config decides what is *answered*.

  What the flag changes: the OneAdmin rail and its doctypes are offered
  (`site.offer`), the proxy answers instead of refusing (`caller` calls
  `require_admin`), and the provisioning runner does any work (`runner.py`
  returns at once elsewhere). On a workspace site the same doctypes exist as
  empty tables with no rail entry and no search hits, which is the cost of
  one app.
- **Who owns what.** Frappe Cloud owns the servers, benches, sites, their
  backups and their upgrades. We are a press customer, never its operator,
  and press's whitelisted HTTP API is the whole boundary (`press.py`). We own
  the commercial facts: who the customer is, what they bought and spent,
  where we put them and what the workspace is called. That is `Tenant` and
  what hangs off it. Nothing of press's is mirrored. What `Tenant` stores
  about the site is what we *asked* press for, which has to survive press
  being unreachable.
- **The admin site is in the control path, never the data path.** It
  checks, signs and records; R2 and Cloudflare carry the bytes. Calls go
  tenant to admin only (`proxy.py`), so there is no key anywhere that opens
  every workspace. Bench common config holds nothing secret: each site's own
  config gets the admin URL, its tenant name and its token from
  `push_config`, and admin keeps only the token's hash. The old design put
  R2 keys, the Cloudflare token and AI keys in common config, where every
  workspace on the bench could read them.

  AI is the one call that carries a payload through admin: it is kilobytes,
  admin owns the ledger, and the gateway token never exists on a workspace,
  so `ai_run` holds, calls and settles in one round trip. Anything that
  charges is safe to repeat, because a timeout leaves us unable to tell
  whether it landed: a Stripe event id is unique (`Stripe Webhook Event`),
  and `ledger.grant` takes a key that meets a unique index. A signed storage
  URL needs no key, since storage is billed on what is held, measured
  nightly.

  When admin is down, new uploads, new AI calls, plan changes and checkout
  stop. Everything else in a workspace keeps working, and `Workspace Account`
  keeps the plan and quota screens drawn.
- **Where a workspace lives** is one question at signup (`www/start.py`,
  `_jurisdictions`), and it sets both the R2 bucket (`jurisdiction`,
  `storage._bucket`) and the server `place_it` picks (a server marked EU in
  Settings' list, for the EU).
  Asking twice would let somebody pick EU files on a US server. It is
  permanent, and the page says so: R2 pins a bucket to its jurisdiction when
  it is made, so moving means copying every object. EU is offered only once
  Settings has `bucket_eu`, and with one choice the page draws no picker.
- **Provisioning** is `steps.ORDER`, walked by `runner.py`: choose a server,
  check the name is free, create the site, wait for it, write the edge key
  (`route_it`), push the config (admin URL, tenant, token, `host_name`,
  `max_file_size`), invite the owner, mark it live. The money comes first,
  before any job exists (`signup.accept`). The R2 prefix needs no step: it is
  `keys.prefix` of the slug.

  Workspaces run OneStudio's server extensions, which are frappe Server
  Scripts and run only where `server_script_enabled` is set in the bench's
  `common_site_config.json` (on Frappe Cloud, the bench group's config). It
  is set once per bench group, never per site. A workspace on a bench
  without it shows Cannot Run Here on its server extensions and nothing else
  changes. Who may write one is OneStudio's rule (`one_studio/README.md`).
- **What lives where.** OneAdmin's doctypes are on every site and answer only
  on the admin site: `One Admin Settings`, `Tenant` (with `Tenant Add-on`),
  `Tenant Event`, `Tenant Domain`, `Account Request`, `Provisioning Job`,
  `Workspace Server`, `Offering`, `Stripe Webhook Event`, `Credit Ledger
  Entry`, `Credit Reservation`. A plan, a
  pack and an add-on are all one `Offering`. The workspace side keeps
  `Workspace Account` (`one/`), a single holding what it last heard from
  `hello`, so its screens draw without a round trip. Storage is a
  measurement written onto `Tenant`, not a second ledger.
- **What is never here:** a credential that opens more than one workspace; a
  copy of press's state (a fact that can be asked for is asked for); bytes
  passing through admin; a second runtime. The bench's own queue,
  scheduler and socketio, plus Cloudflare's Workers, are all there is to
  deploy.
- **Home is frappe's `One Admin` workspace**, as One's Home is: five
  number cards, and Needs You as a Custom HTML Block (`OneAdmin Needs You`,
  a fixture, for One Operator only) drawn with frappe's own quick list
  markup. frappe offers every workspace to Workspace Manager, whatever its
  roles, so `site.offer` (`extend_bootinfo`) takes OneAdmin's rail and
  Home out of the boot for anybody who is not an operator on the admin site.
  Before it, a person holding Workspace Manager and nothing of OneAdmin's was
  offered its rail and its Home, and landed on a permission error. The
  records were never theirs to read; `offer` takes the way to them out of
  what the desk is told.
  With its rail gone, the dock drops its entry, and the address answers
  "not found". `patches/home_is_a_workspace.py` removes the page Home was
  for a while, and the Stuck card, which is Failed now.
- `home.counts` and `home.needs` are the operator's only (`operator._may`).
  The actions are `operator.py`'s own verbs: `resume`, `retry_signup` and
  `refresh_domain`. `counts` is live workspaces, workspaces being built,
  workspaces owing, jobs that failed, and signups paid for but never built;
  each says the list it opens, with its filters, so a number and the list it
  stands for cannot disagree. `needs` is one list of what needs a person,
  each with why and the one thing to do about it: a failed job is resumed
  where it stopped, a job that is due and has not moved is run now, a
  workspace over its storage is opened, a paid signup with no workspace is
  built again, a domain is asked about again, and a workspace owing is
  opened. OneAI's `console_today` reads `needs` (`ai.py`), and so does
  nothing else: the page and the model are told the same thing.
- `tell.py`, with the types in `notifications/one_admin/`: the machinery writes with `db_set`, so
  there is no document hook to hang a notice on. Each is called where the
  thing happens: a job stops in `runner._stop`, a signup is paid for and
  built in `signup.accept`, a workspace arrives on a rung in `steps._arrive`,
  and the domains are asked about in `domains.nightly`. The owner is mailed
  from `steps._arrive` when their workspace is suspended, archived or
  restored, and from `steps.live` when a new one is ready. Nothing here may
  stop the thing it tells of, so each is wrapped (`_quietly`): a notice that
  fails is logged, and the job carries on. The account's own mails (Sign-in
  Link, the two Workspace Moved, Confirm Your New Email, Account Email
  Changed) and Finish Signing Up are here too, unwrapped, called from
  `accounts.py` and `signup.remind`.
- `ai.py`: `console_today` is `home.needs` for OneAI, and `workspace_facts`
  one workspace's head and connections; both are refused to anybody who is
  not an operator on the admin site. Every reader there is the operator's
  own, on the admin site only and for One Operator only, as every console
  read is (`operator._may`). `console_today` is Home's own list
  (`home.needs`), so the panel and the page say the same thing;
  `workspace_facts` is what a workspace's own form shows, its head and its
  connections, with why each of its domains does or does not work (given a
  domain, it answers for that domain's workspace), `job_facts` a job's walk
  in words, and `price_list` the price list. Price Check and AI Usage are
  read by the generic `run_report`, the reports' roles keeping them the
  operator's.
  Nothing is changed from there: resuming a job, building a signup, checking
  a domain or giving credits is a button the operator presses.
- **A new workspace's owner** (`one_account/owner.py`, on the tenant): the admin site
  cannot sign in to a site it built and holds only a hash of its token, so
  `proxy.hello` names the owner and a workspace with no administrator yet
  makes them one and invites them. `steps.invite_owner` posts to the new
  site's `account.wake`, which only makes it ask, and waits until it says it
  has an administrator. `hello` answers a Provisioning workspace for this
  (`proxy.INTRODUCED`); no other endpoint does. `tell.ready` mails Workspace
  Ready from `steps.live`.
- **Jobs**: `runner.py` drives a Provisioning Job forward on a cron rather
  than in a request. A site takes minutes to build. Doing that inline would
  hold a worker open for the whole of it and lose the lot to a restart, so
  the request creates a job and returns, and the runner walks it. **A job
  resumes; it never repeats.** The step it is on is a field, so a worker that
  died between two steps comes back to the second one. Every step is written
  to be safe run twice anyway — see `steps.py` — because the field is written
  after the step returns and a crash in that gap is real. **Waiting is not
  failing.** A step that answers WAIT is asked again in a minute and never
  counts toward giving up; only an attempt that failed does. **Backoff is per
  step and grows.** A site press has not finished building is worth asking
  about again in a few seconds; a call that failed for a reason we cannot see
  is worth leaving longer each time. The cap stops a stuck job from being
  asked about once a day and finishing a week late. `tick` commits after each
  job, so one that throws loses only its own step, and a throw that is not a
  `faults.Refused` is rolled back, logged and counted like a failed attempt
  (`_counted`), so it gives up rather than running every two minutes for
  ever. A step that raises `steps.CalledOff` ends its job Done, with the
  reason as its error (`_called_off`). A Provision job on a tenant that is no
  longer being built is called off; a resumed one on a Failed tenant puts it
  back to Provisioning, so its `hello` answers.
  `runner.py` publishes every write (`notify=True`); the form's
  walk is `operator.walk`, drawn by `provisioning_job.js`; `home._stalled_jobs`
  and `operator.run_now` are the job that has not moved. `ai.job_facts` is the
  walk for OneAI, and a suggestion's `when` (`one_ai/suggest.py`) offers the
  failed question only on a failed job.
- **The price list** (`doctype/offering`): `CARRIES` says what each kind
  carries, and the form shows only that; `gives` and `sort_key` are
  written on save (`patches/offering_gives.py` for the rows before).
  `operator.sold` counts a plan's workspaces and an add-on's (from `Tenant
  Add-on`); `ai.price_list` reads it all for OneAI.
- **Price Check** (`report/price_check`): the rules are `plans.check`,
  frappe-free, whose findings carry a `rule` and `slots`; `offerings.RULES`
  says them in the reader's language, and `offerings.warn` says them on
  saving an offering or the costs. `home._mispriced` is the Wrong ones.
  OneAI's suggestions reach a report as `report:<name>` (`one_ai/suggest.py`),
  and OneAI reads it with `run_report`.
- **Our own workspace** (`house.py`): `Tenant.is_house`; `ensure` makes it
  and writes `one_tenant` and `one_token` into the admin site's config;
  `ledger.reserve` never refuses it; AI Usage's `_ours` takes its share out
  of Charged and the margin. The admin site uses One as any company does,
  OneAI included, and OneAI's calls go through the same gateway and credit
  ledger as a customer's. So the admin site is a Tenant of its own, ours, and
  three things are true of it that are true of no customer: nobody bills it
  (it has no plan and no Stripe subscription, so the ladder never moves it);
  its OneAI is never refused for credits (`ledger.reserve`), its balance can
  go below nothing, and what it spends is what the provider charged us; and
  its AI use is our cost, not a sale, so AI Usage does not count it as
  charged, and Home does not count it as a live customer. `ensure` makes it
  once and links the admin site to it, the way `push_config` links a
  customer's site to its Tenant.
- **Settings** (`doctype/one_admin_settings`): `heads.NEEDED` is what each
  connection needs and what stops without it, for the head and for
  `ai.settings_check`; `_tell` is Settings Changed. `offerings.credit_price`
  is what a credit sells for, from the smallest pack.
- **AI Usage** (`report/ai_usage`): `ledger.usage` sums the calls (one
  settled Credit Reservation each, with `usd`, what the provider charged, kept
  by `ledger.commit` since `patches/call_costs.py`); `usage` in the report is
  the cut and the margin, and OneAI reads it with `run_report`. The numbers
  are `ledger.usage`'s — one row per model call, what it was charged once the
  provider said what it used, and what the provider charged us for it —
  because only the ledger reads its own tables; the report is the cut and the
  columns. Charged is the credits at the smallest credit pack's price a
  credit (`offerings.credit_price`), so Margin is what OneAI makes on the
  calls at list price.
- **Models** are `one_ai/models.py`'s. `actions.kind` says which kind of
  work an action is; `gateway.call` asks that kind's first model at the
  workspace's tier, then its fallback, and the ledger records the one that
  answered (`patches/no_model_catalogue.py` removed the old catalogue).
- **Credits** (`ledger.py`, over `credits.py`, which has no frappe in it):
  a balance is a sum; `left_of` is one grant's rest; `take_back` writes a
  spend of it (source Operator); `last_gift` travels in `proxy.hello` so the
  workspace says Credits Added with the note (`one/account.py`).
  `patches/credit_model.py` linked old spends to their model.
  `ai.credit_facts` is a workspace's credits for OneAI.

  **The balance is a sum, never a stored number.** There is no
  `credits_left` field anywhere, on purpose: a stored balance can disagree
  with its own history, and when it does there is no way to tell which of the
  two is lying. Summing the rows costs one query and cannot drift.

  **Reserve, then commit.** Reading a balance and then spending against it is
  a race — two calls arriving together both see five credits and both spend
  four. So a hold is taken under a lock on the workspace's own row before
  anybody talks to a provider, and settled for what the call actually cost
  afterwards. The hold is a *ceiling* priced from an action's declared
  limits, not a forecast; the point is only that two calls cannot both spend
  the last credit.

  **A spend names the grant it came out of.** Which is what makes the ledger
  append-only: drawing down a bucket without rewriting it means writing a row
  that points at it. `credits.py` decides which bucket and in what order, and
  has no frappe in it.

  `ledger.py` is the only thing in the app that knows a balance is made of
  rows. Everything above it asks for a number.

  `STALE_MINUTES`: a worker that died mid-flight would otherwise eat a
  customer's credits for good, so holds whose call never came back are let go
  nightly — generously, because releasing one that is still running would let
  a second call spend the same credits.

  `_lock`: the workspace's own row is the mutex: it is the one row every
  credit operation touches and nothing else contends for it. **The lock alone
  is not enough, and this was measured rather than reasoned.** Two processes
  reserving seven credits against a balance of ten both succeeded: the second
  waited for the first exactly as intended, and then read a balance from the
  snapshot its transaction had taken *before* the first one committed.
  InnoDB's repeatable read fixes that snapshot at a transaction's first read,
  and a plain SELECT afterwards never sees past it. So every read this
  decision rests on is a locking read — `FOR UPDATE`, which reads the latest
  committed row rather than the snapshot — and the mutex is what stops the
  two of them interleaving between the read and the insert.
- **Signups** (`signup.py`): `accept` is what a payment calls; it sets
  Paid, then Provisioning, and never unwinds. `built` sets Done from
  `steps.live`; `abandon` is nightly; `tell.signup_not_built` mails the
  operators and, once, the customer. `patches/signup_states.py` mended the
  rows from before. `ai.signup_facts` is a signup for OneAI.

  Two rules, and the second is the one that matters. **Nothing is
  provisioned until money has moved.** A request sits as `New` until the
  payment says otherwise, and `accept` is what the payment calls. **Nothing
  unwinds.** `accept` runs after a charge, so the policy is never to leave a
  customer with a receipt and nothing to show for it. Each part records where
  it got to, a failure marks the request failed with a reason an operator can
  read, and the resume is the same call again — which is why every part of it
  is safe to run twice. Unwinding is how you end up having taken money and
  then deleted the thing it bought.

  `start` writes the request before the customer is sent to Stripe, so a
  payment that completes always has something to attach itself to. The
  reverse — a session created first — leaves a paid customer whose request
  never existed. Somebody signed in to their One account signs up as that
  account: the email is theirs, whatever the form sent, so the workspace
  joins the account they are looking at (`accounts.hold`, at payment).

  Storage and database limits are decimal gigabytes, not binary. The plan
  says 25 GB, R2 bills in decimal, and every tool a customer checks with
  reports decimal — so 1024³ quietly gave them 26.8 GB and made the screen
  say 27 for a plan called 25. Found by putting a progress bar next to it.
- **Plan Calculator** (`report/plan_calculator`): `quote` is `plans.quote`
  over the add-ons, as `billing.quote` is for the customer, with what each
  way costs us; `needs_of` is a workspace's needs now. `ai.plan_quote` reads
  both for OneAI.
- **Domains** (`domains.py`): the customer's own names are custom
  hostnames on our Cloudflare zone; Frappe Cloud is never told of them.
  `Tenant Domain.is_main` is the console's copy of the workspace's
  `primary_domain`, kept by `make_primary`; `_keep` publishes each answer.
  `ai.workspace_facts` says a workspace's domains for OneAI.

  Two names reach a workspace. `<slug>.t.4dl.app` is given at provisioning
  and lives entirely at the edge: a proxied wildcard, a Worker that rewrites
  `Host` to the Frappe Cloud site name, and the Advanced Certificate Manager
  pack Set up Cloudflare orders (`setup.certificate`). Frappe Cloud is never
  told that name exists.

  **A customer's own name goes the same way.** It is a *custom hostname* on
  our zone (Cloudflare for SaaS). The customer makes one CNAME record, from
  their name to their `<slug>.t.4dl.app`; Cloudflare sees the name arrive,
  validates it over HTTP and issues its certificate; a Worker route for the
  name sends it to the same router, which finds the site under `host:<name>`
  in KV. So the customer only ever sees our name, Frappe Cloud never sees
  theirs, and nothing issues a certificate but Cloudflare.

  This replaced adding the name to Frappe Cloud, which had three costs: the
  CNAME pointed at `*.frappe.cloud`, Frappe Cloud's Let's Encrypt check
  failed for anybody who kept Cloudflare's proxy on, and a workspace that
  made its name primary could not go back. Both at once would clash: Frappe
  Cloud's check would reach Cloudflare and fail. So press is only asked one
  thing here, to write `host_name` into the site's config (`_call_itself`).

  **What we keep and what we ask.** A `Tenant Domain` row per name, with
  Cloudflare's id for it, so the workspace's screen draws without a round
  trip. Status is Cloudflare's to decide (`hosts.standing` puts it in our
  words), and `refresh` is what asks: when the screen's Check Again is
  pressed and nightly for names not yet working.

  **Proof before routing** (`_route`, `hosts.proven`). A name is only given a
  custom hostname, a route and a KV key once public DNS, asked over HTTPS at
  Cloudflare's resolver (`cloudflare.answers`), shows the CNAME or a TXT at
  `_one.<name>` naming this workspace's own address. Before this, any
  workspace could claim any name, and a name whose DNS still pointed at us
  after its owner left was anybody's to take. The value is the workspace's
  address rather than a token of ours because only the domain's DNS can say
  it, and the screen already shows it. Until then the row is Pending with no
  Cloudflare id, and `refresh` looks again; a resolver that does not answer
  proves nothing.

  **A refusal here is thrown rather than raised.** It is something a customer
  has to act on, the name is taken or is ours, and `frappe.throw` is the
  route by which the sentence reaches the workspace that asked.

  **Bare domains.** A CNAME at the apex (`acme.com`) only works where the
  customer's DNS flattens it (Cloudflare, Route 53's ALIAS and many others).
  Pointing an apex at fixed addresses is an Enterprise feature of Cloudflare
  for SaaS, so the screen says to use a subdomain otherwise.
- **The log** (`log.py`): every row is `log.write`, which says who from the
  session or the job's owner (the proxy passes Customer), links the job,
  and stores a fixed phrase from `SAID` (`_lt`) in English for the list to
  translate. Who is the customer (a plan they changed, through the proxy),
  an operator (a button they pressed, or a job they started), or One (the
  clock, a payment, a nightly measure); which job, when a job did it; and
  what, a phrase from `SAID` shown in the operator's own language, or plain
  data (a plan's name, two sizes) that needs none. Each says the three things
  the list used to leave out. `log.over_storage` keeps one row per stretch over.
  `log.timeline` is the workspace's `additional_timeline_content`, so the
  workspace's own Activity shows its rows too, and its story is on its form.
  `patches/log_in_words.py` reworded the rows written before.
- **Workspaces is Tenant.** `one/titles.py` hands the rail's labels for our
  own doctypes down in the boot, and `public/js/reports.js` writes them as the
  list's title, the crumb back to it and a record's connections. The owner's
  mails are `tell.owner`, from `steps._arrive`, which writes `status_since`
  with every status and publishes the change (`notify=True`), so an open
  form and list update. `patches/status_since.py` dated the workspaces
  written before it, which the ladder otherwise never moved.

### actions.py

**Nothing a workspace sends reaches the instruction.** A workspace names a
job and its tier. What the model is told is `one_ai/jobs.py`'s, the voice's
parts and then the job's own words, and it goes where the provider puts a
system instruction rather than being glued onto the front of the prompt
(docs/AICENTER.md).

**Nothing is ever asked "which model" at the call site.** A job names its
kind of work, and `one_ai/models.py` names the model for that kind at the
tier the workspace sends. A key that is not a job is refused.

### billing.py

Everything here is asked by the workspace through the proxy and answered by
the calculator (`plans.py`), so the customer and the operator see the same
arithmetic: what the workspace has now, what each plan with the cheapest
add-ons on top would cost for what it needs, and taking one of those.

**Taking an option sets the whole shape.** An option is a plan and the
add-ons that bring it up to a need, so taking it makes the subscription
exactly that: the plan swapped if it differs, each add-on set to its count,
and add-ons the option does not have taken off. Stripe prorates each change
and charges the difference now; a declined card refuses the change before
anything here is written (`stripe.PRORATED`).

**Nothing goes below what is used.** A smaller plan, or an add-on taken off,
that would leave the workspace over its seats, its storage or its database is
refused with what to clear first, because the alternative is a workspace that
cannot save anything the moment the change lands.

### books.py

The admin site is a One workspace and One is what it sells, so every sale is
booked the way any company using One books one:

* **An Item per Offering** (`item_for`), a service under One Subscriptions,
  kept in step with the price list (`synced`, on the Offering's save).
* **A Sales Invoice per paid Stripe invoice** (`invoiced`): the plan, each
  add-on at its quantity, and the prorated lines Stripe writes when a plan
  changes part way through a month. A proration credit (a negative line) is
  taken off as the invoice's discount, since an invoice line cannot be less
  than nothing. A credit pack is an invoice of one line (`pack_bought`).
* **A Payment Entry** into the Stripe account, for what Stripe collected,
  referenced by the charge.
* **Stripe's fee** as a Journal Entry from the Stripe account to Stripe Fees,
  read from the charge's balance transaction.
* **A refund** as a credit note against the invoice, paid back out of the
  Stripe account (`refunded`).

The customer is the tenant's (`sales.customer_for`). Stripe charges in the
price list's currency, US dollars, and the company keeps its books in its own,
so the invoice and the payment are in dollars at the day's exchange rate into a
receivable and a Stripe account in dollars, both made here once (`ensure`).
ERPNext does the conversion; nothing here multiplies by a rate.

**Booked once.** Each invoice carries the Stripe object it came from
(`one_stripe_invoice`), so a webhook Stripe redelivers finds it already there,
and `catch_up` books any paid invoice the webhook missed.

**Never in the way.** A failure here is logged and left for `catch_up`; the
webhook still moves the workspace, because the customer has paid either way.

### closing.py

The workspace asks (`one_account/closing.py`, through the proxy); this writes the day
and walks it there. Closing is the ladder's own Archive job, started by a date
rather than by a debt, so it takes the same backup, cancels the same
subscription and is undone the same way; and from Archived it falls to Dropped
on the ladder's own clock, which is the day it is deleted for good.

**Notice, not at once.** It closes `NOTICE_DAYS` after it is asked, and works
as before until then: long enough to take the full download, tell everybody and
move what they need. Until that day the same person may keep it open; after it,
the site is gone and restoring it from the backup is an operator's decision, as
for an archived workspace that pays.

**Billing.** Asking sets the subscription to end with its period, so no renewal
falls in the notice; the Archive job cancels it outright. What was paid for the
current period is not refunded, as the Terms say.

**Too late to keep.** `keep` refuses once the Archive job is past its first
step (`lifecycle.archiving`): the site may already be gone. Kept before that,
`archive_site` finds no closing day and the job is called off.

### cloudflare.py

A workspace is reached at `<slug>.t.4dl.app`. That name resolves to one proxied
wildcard record and one Worker route, both made once by **Set up Cloudflare**
(`setup.py`); no tenant ever gets a DNS record of its own. What the Worker needs
is the answer to one question — which press site is this slug? — and this
module writes that answer into a Workers KV namespace as the site is
provisioned.

**Why KV rather than the Worker asking us.** The admin site is the control path
and must never become the data path. A Worker that calls us on every request
means an admin outage is an outage for every workspace, which is exactly the
coupling the rest of this design avoids. KV is Cloudflare's own edge store:
once the key is written, serving a workspace needs nothing of ours at all.

**Certificates.** `*.t.4dl.app` is covered by an Advanced Certificate Manager
pack on the zone, which `setup.certificate` orders once, rather than a
per-tenant call: the zone's free certificate covers `*.4dl.app` and not a
name two labels down. A
customer's own domain is a **custom hostname** on the same zone (Cloudflare for
SaaS): the customer points a CNAME at their `<slug>.t.4dl.app`, Cloudflare
validates it over HTTP and issues its certificate, and a route for that name
sends it to the same router, which finds its site under `host:<name>` in KV.
Frappe Cloud is never told the name exists, exactly as it is never told ours —
see `domains.py`.

The token needs Workers KV Storage: Edit on the namespace for routing, and for
customers' own domains SSL and Certificates: Edit and Workers Routes: Edit on
the zone.

### credits.py

Same reason as `ladder.py` and `keys.py`: this decides what somebody is allowed
to spend, and a decision that costs money should be readable in milliseconds
against a table of cases rather than against a site.

Three rules, and the second is the one that is easy to get wrong.

**A grant is a bucket with a date on it.** What is left in one is what was
granted plus everything drawn from it, and a bucket whose day has passed stops
counting — which is the whole of expiry. There is no sweep, no expiry row and
nothing to run nightly: a balance simply stops including it.

**The soonest-expiring bucket is drawn first.** The other order loses somebody
credits they paid for while a free monthly grant sits unused beside them, and
it does it quietly, a month later.

**An overdraw belongs to no bucket.** A call the provider answered costs what
it cost, even if it came to more than was held for it, so the arithmetic has to
have somewhere to put that rather than refusing after the money is spent.

### doctype/credit_ledger_entry/credit_ledger_entry.py

Submittable because that is what an append-only record is in Frappe: a balance
is a sum over these rows, so a row somebody could edit is a balance that can be
changed without leaving a trace. Amending one leaves an `amended_from` trail
and cancelling leaves the cancelled row.

The sign is carried on the row rather than implied by the kind, so `balance` is
one SQL sum and not a mapping somebody has to keep in step — and `validate`
refuses a grant that takes credit away.

### doctype/tenant/tenant_dashboard.py

They are connections rather than tabs of fields because they are lists that
grow, and each is a screen somebody opens on its own.

Each is called what the rail calls it (`one/titles.py` renames our own doctypes
in the browser); the customer is erpnext's, and keeps its name. Its invoices
are one click from it, and from the form's Billing menu.

### private.py

Private apps. A code is twelve characters from an alphabet without 0, O, 1
and I, kept as its SHA-256 with its last four for the operator to tell codes
apart. `claim` looks the hash up among one workspace's grants only, so a
code can't open another workspace's app, and every miss says the same thing.
`proxy.app_claim` rate-limits it to twenty an hour a workspace. A claim
queues one Install App job (`runner.start` dedupes on its payload, the app
and the grant); typing it again answers the job's state. `state` is what
the workspace sees: Installed when the last step has run, Failed when the
job has, Installing otherwise. The steps are in `steps.py` after `APPS`:
`app_on_bench` reads `press.apps` for the bench group, `install_app` asks
`press.api.site.install_app` once (skipped when `press.api.site.installed_apps`
already lists it), and `app_is_installed` waits on that list.

### faults.py

Nothing of Frappe in here on purpose. Retrying a permanent failure forever is
how a provisioning queue quietly stops working while looking busy, and the
decision that prevents it is four lines of arithmetic over a status code — so
it is four lines that can be read back in milliseconds rather than against a
site.

Two exceptions, and `Again` is a subclass of `Refused` so that a caller who
does not care about the difference does not have to name both.

### gateway.py

Calls go through our **Cloudflare AI Gateway**, and the thing that makes it
worth a dependency is where the keys live: the provider keys are stored *in
the gateway*, so this site holds a Cloudflare token and an account id and
nothing that would open an account at Google or anywhere else.

**Nothing on a tenant site ever reaches this module.** A workspace asks admin
through `proxy.py` and admin makes the call, for the same reason a workspace
cannot sign its own storage URL: the credential is the product.

- **Two routes, each a provider's best-supported one.** Workers AI is reached
  on Cloudflare's REST endpoints (`API`): `/v1/chat/completions` in OpenAI's
  shape for talking, `/run/{model}` for a model with its own shape (Whisper,
  vectors, Clef, Clairic), with `Authorization` carrying our Cloudflare token
  and `cf-aig-gateway-id` naming the gateway. Measured on 2026-10-25: the
  gateway's own Workers AI route answers 401 for Clairic and Clef, the REST
  endpoint answers both. Gemini stays on the gateway's Google route in
  Google's own shape (`HEADER`, `cf-aig-authorization`), where it reads
  documents and sound, hands back thought signatures, and uses the key the
  gateway stores; Cloudflare's chat endpoint billed Gemini to Cloudflare's own
  credits instead.
- `UNSEEN`: every call tells the gateway to keep its counts and cost but not
  what was in it, so customers' mail and records are not stored at
  Cloudflare. `TAG` carries the workspace, the job and the tier.
- `call`, `run`, `embed`: the model is `one_ai/models.py`'s, by kind of work
  and tier, leaving out any that cannot read the files sent. The first is
  asked; one that cannot answer now, or no longer exists, hands over to the
  fallback (`_first_that_answers`), and a refusal of what was asked is not
  tried again elsewhere. The hold is priced on the dearest of the two; the
  charge on the one that answered, at its own price on that day.
- `_heard`: Whisper takes the sound and no instruction, so each stretch it
  heard is written on its own line after the time it starts.
- `THOUGHT`, for a call allowed to think (`THINKS` tokens or more), which
  writes code: measured on Gemma 4 writing a scheduled extension, past 60
  seconds three times out of three, and each was billed and thrown away. Under
  the 120 seconds a Frappe Cloud web worker is given (its bench
  `http_timeout`), as this runs inside the account's request.
- `THINKS`: measured, Gemma 4 given the chat's 800 tokens spends every one on
  `reasoning_content`, stops at "length" and answers nothing; told not to
  think, it answers in twenty. A model that does not think ignores the switch.
- `talk`: `turns` is the whole conversation in our shape rather than one
  prompt: a round where a model asked for a tool, was given the result and
  answers again is three turns, and a provider has no memory between calls.
  `system` goes where each provider puts a system instruction rather than being
  glued to the front of the first turn, which is the whole reason an action can
  be told things a workspace cannot take away from it. `tools` is the same:
  declared to the provider as tools, never written into the words, so a
  workspace cannot invent one by typing it.
- `call` **holds first.** Reading a balance and then calling is a race, and
  refusing after the provider has answered is a call we paid for and then told
  the customer they could not have. The hold is priced from the caps the caller
  declared — a ceiling, not a forecast — and the only thing that matters about
  it is that two calls cannot both spend the last credit. **Settle on what the
  provider reported**, never on an estimate. A response that carries no usage
  at all is charged its hold and flagged, because the provider billed us for it
  either way and charging zero would be a model that costs money and earns
  none.
- A blank answer right after a tool answered is not an answer: the model did
  what it was asked — a receipt became a card — and has nothing to add.
  Measured: gemini-2.5-flash-lite does exactly this, every time, on the round
  after `claim_expense`. It is billed like any round.
- A blank answer anywhere else is asked again with a turn only the model sees.
  Measured: gemini-2.5-flash answered an Arabic question with tools declared
  with an empty STOP every time, the same request again blank too; told to
  answer, it called the tool three times out of three. Past the gateway's
  cache, which would hand the same blank back; a second blank is said as "try
  again", which is what it is.
- A 200 with neither words nor a tool call in it is not an empty answer, it is
  a shape we do not understand — and treating it as an empty answer is how a
  provider changing its response silently starts returning blanks to
  customers.
- One conversation, two shapes: a turn of ours is `{role, text, calls}` or
  `{role: "tool", id, tool, result}`, which is neither provider's shape and is
  deliberately both of theirs written down once. The tenant holds the
  conversation and sends it with each round — admin keeps nothing, because
  admin has no session with a workspace and is not going to grow one.
- `OPENAI_ROLES`: OpenAI's dialect refuses anything but "assistant" (measured:
  Gemma 4 on Workers AI, on any conversation where the model had said
  something before it called a tool).
- OpenAI's dialect carries a picture as a data URL beside the words, and
  carries nothing else at all — a model that reads sound or video through that
  endpoint is not something either provider offers, and `files.readable` has
  already refused anything it could not send.
- `_workers_ai_said`: measured against the real API, the classic
  text-generation models answer with `result.response`, and the newer ones —
  gpt-oss, gemma-4, qwen3, glm — answer in OpenAI's shape,
  `result.choices[0].message.content`. Both are read, because which one a model
  uses is not something the models list says and not something we find out
  about before a customer does. The thinking is deliberately not read, under
  either of the two names it arrives with — `reasoning_content` on `/ai/run`
  and `reasoning` on the gateway's endpoint. It is the model thinking out loud,
  it is not an answer, and putting it on screen as one is how a person is shown
  working notes and told they are a reply.
- A choice that came back at all is an answer, even an empty one: a reasoning
  model given a small budget spends it all on `reasoning_content` and omits
  `content` entirely, and that is the model saying nothing rather than a shape
  nobody has seen. `None` is kept for the second case, which is what makes the
  guard in `_answered` worth having.
- A string or nothing. Measured: qwen2.5-coder puts a tool call in `content` as
  an object rather than using `tool_calls`, and a dict handed on as an answer
  is a crash three functions later. It is not read as a call either —
  inventing one from free-form content is how a model ends up having "asked"
  for something it never asked for.

### heads.py

Every one of these records is read-only, because every field on it is the
record of something that happened (a signup, a call to Frappe Cloud, a
measurement, a rung). So each opens on where it stands, in a word and a colour;
one sentence saying what that means for somebody; for a workspace and a job,
how far along they are; and the verbs that move them, which run the same code
the nightly ladder runs (`operator.py`).

### hosts.py

Nothing of Frappe in here. A mistake in this module is a workspace claiming a
name that routes somebody else's traffic to it, so it has to be readable in one
sitting and testable in milliseconds — the same reason `keys.py` is pure.

**Two kinds of name, and they are not the same thing.** `<slug>.t.4dl.app` is
ours: it is served by a Cloudflare Worker that rewrites `Host` to the site's
own press name, and press is never told it exists. A customer's own name is
theirs: press adds it, verifies the DNS itself and issues the certificate. This
module decides only the second kind, because the first is not asked for — it
is given.

**A tenant may not claim a name under a domain we operate.** Not our tenant
domain, not the admin's own host, not a bare public suffix. Nothing stops
somebody typing `admin.t.4dl.app` into the box, and the refusal belongs here
rather than in whatever press would eventually say about it.

The port is stripped from the domains we operate because the admin's own host
carries one in development and the name being compared never can — `tidy`
refuses a port outright. Without this, `onedesk.localhost` does not match
`onedesk.localhost:8002` and the admin console's own hostname is claimable.
Measured, not imagined.

### keys.py

Nothing of Frappe or boto3 in here, because this is the module where a mistake
means one customer reading another customer's files. It has to be readable in
one sitting and testable in milliseconds.

**A tenant never names an object; it names a suffix.** Everything it asks for
is put under `tenants/<slug>/` by this module, and a key that would escape that
is refused rather than trimmed. Trimming is how you end up with two tenants
sharing a prefix because one of them sent something clever.

**A `..` segment is refused outright**, even one that would land back inside
the prefix. `a/../b` is harmless and nobody legitimate sends it, so the rule
that is easy to verify beats the rule that is merely correct.

- `ROOT`: one prefix per tenant inside one of two buckets, never a bucket per
  tenant: a lifecycle rule written against one bucket gets written against the
  next one too, and a key scoped to a bucket still reaches every tenant in it.
- `room_for`: `held` is what was measured, `pending` is what has been signed
  for since — a signed URL is a promise somebody may keep, so it counts against
  the limit until the next measurement says whether it was kept. A limit of
  zero or less means unmetered rather than nothing: a plan with no storage line
  is a plan nobody thought about, and refusing every upload is a worse answer
  than not enforcing a limit that was never set.

### ladder.py

Nothing of Frappe in here. This is the module that decides when somebody's data
is deleted, so it has to be readable in one sitting and testable in
milliseconds — the same reason `keys.py` and `hosts.py` are pure.

**Five rungs and one direction.** Live, Overdue, Suspended, Archived, Dropped.
Money stops and a workspace walks down them, one at a time, never skipping; the
customer pays and it goes straight back to Live from anywhere above Dropped.
Each rung has a period, and the period is how long the workspace *stays* on
that rung before falling to the next.

**What each rung means, so the periods can be argued about honestly.** Overdue
is nothing at all: the workspace works exactly as it did, and somebody is told.
Suspended is press deactivating the site — it answers a page and nobody can log
in, and the data is untouched. Archived is press destroying the site, having
taken an offsite backup first; our own R2 prefix is not moved, copied or
touched, because it is already ours and already where it should be. Dropped is
the only rung that destroys anything of ours, and it is last on purpose.

**A workspace with no timestamp never falls.** `since` is when it arrived on
the rung it is on, and if we do not know, the answer is to do nothing and let
somebody look. A clock that deletes data on a missing field is a clock that
deletes data on a failed migration.

**A failed build is off the ladder,** and no clock moves it. `by_hand` gives
it one rung, Archived, for an operator closing it; `below` stays the ladder.
`climbing` answers None while a workspace is being built: an invoice paid then
has nothing to restore. `settled` is whether a paid invoice clears the debt:
one of the workspace's own subscription, with nothing else left open.

**A period of zero means never.** Not "immediately". An operator who clears the
grace period is asking for the ladder to stop, not for every overdue workspace
to be suspended tonight, and the reading that loses data is the wrong one.

`falls`: a workspace nobody looked at for two months has not earned a jump
straight to Dropped: each rung does real work — press deactivates, press
archives, the edge route goes — and skipping one leaves that work undone. So it
returns them in order and the caller walks them, one a night or all at once.
The period of each rung is counted from the same `since`, which is the
conservative reading: a workspace that went Overdue sixty days ago and was
never touched is Suspended after seven and Archived after fourteen, not after
twenty-one.

### lifecycle.py

`ladder.py` decides *whether* a workspace should be on a different rung;
`steps.py` does the press and R2 work of getting it there. This is the part in
between: the events that put a workspace on the ladder in the first place, the
nightly walk, and the one call that takes it off.

**Nothing here talks to press.** Every rung is a job, for the reason every
other press call is a job: press is another service and it will be slow, down,
or mid-deploy exactly when the cron fires. A fall that failed half way is a job
an operator can see and resume, rather than a workspace in a state nobody wrote
down.

**One rung a night.** `nightly` moves a workspace one step and no further, even
when the clock says it is three rungs late. Each rung does real work and the
next one should start from a finished previous one; and a workspace that is
being suspended tonight and archived tomorrow gives whoever is watching a day
to notice. A workspace nobody has looked at for a year still gets there, just
not in one go.

**Falling is never retroactive.** A workspace goes Overdue when a payment fails
and not a day earlier, so `status_since` is written when the rung is reached.
The one thing this costs: an operator who fixes a stuck job has reset the clock
on that rung, which is the forgiving direction.

- `paid`, on an archived workspace: the site is gone, so a payment cannot bring
  it back on its own; and throwing there made Stripe redeliver the event for
  days while nobody was told. The operators hear it (Paid While Archived) and
  decide: rebuild from the backup, or refund. The same once an Archive job is
  past `note_backup` (`archiving`), since `archive_site` may have run. Before
  that, the Restore job it queues makes the Archive job call itself off.
- `ended`: a subscription cancelled in Stripe starts a Live workspace's fall
  at Overdue, with the grace period, the way a failed payment does — unless a
  closing day was asked for or an Archive job is running, since those cancel
  it themselves. The owner is not mailed Payment Failed for it.
- `standing` carries `days`, how long this rung lasts, so a screen drawing a
  bar has a denominator without keeping its own copy of the periods. A second
  copy in JavaScript is a second copy to be wrong the day somebody lengthens
  the grace period because of an outage.

### mailing.py

A workspace holds no Cloudflare credential, as for storage. It builds the
message — Frappe's Email Queue does, headers and attachments and all — and asks
here. What is checked here, because a workspace could lie about it:

- the From is on the mail domain and is the workspace's own, `<slug>@` or
  `<name>.<slug>@`;
- the message fits Cloudflare's 5 MiB;
- the workspace has sends left this hour and this day.

The counts are atomic increments in the cache, one key per workspace per hour
and per day, so two workers sending at once cannot both slip under the limit. A
send refused for the limit raises `faults.Again`, and Email Queue retries it
later.

Cloudflare's `send_raw` takes the finished MIME message, so nothing is rebuilt:
what the workspace's Email Queue made is what goes out, signed by Cloudflare
with the mail domain's DKIM key.

### meter.py

Pure, and the shortest module in this arc, because the whole of it is: take the
numbers the provider reported and turn them into `pricing.Use`. Nothing is
inferred, nothing is estimated, and a response with no usage in it comes back
saying so rather than coming back as nothing.

**The two providers report differently, and that is the reason the rate schema
is unit-aware.** Gemini's `usageMetadata` carries token counts per modality for
the prompt, the cache and the output, so a multimodal call is exactly
meterable. Workers AI reports tokens for text and nothing at all for pictures
or speech, so those are metered from what we asked for — which we know,
because we sent it.

**A call that answered but could not be metered is not free.** `read` returns
what it found and the caller charges the hold, which is the only honest answer:
the provider billed us for it either way.

`TOKENS`: both providers bill text per million tokens and both report a count
of tokens, so the unit is the same word — which is a coincidence rather than a
rule, and is why it is written down rather than assumed at the call site.

### offerings.py

Four plans from 30 a month, the add-ons that go on them, and the credit packs.
Written once: `install` adds what is missing by key and never touches an
offering that exists, because the operator's prices are theirs to change and a
migrate must not put the old ones back. The Price Check report says whether the
list still makes sense after they do (`plans.py`).

Why these numbers, briefly (the Price Check shows the rest):

* Each plan is at least twice what it costs us (`COSTS`), and each step up
  saves more than half over buying the difference as add-ons, so somebody who
  has outgrown a plan is better off moving up.
* The smallest add-on of each thing costs less than any step up, so somebody
  who needs a little more is better off adding it.
* A bigger add-on is cheaper per unit than a smaller one.
* Database is dear and storage is cheap, because a GB of database moves the
  site up Frappe Cloud's plans and is backed up every day, where a GB of files
  is a GB in R2.

### operator.py

Every one of these exists because the alternative was editing a field. A Status
that an operator can set from a dropdown is a workspace dropped with no job, no
call to press and no R2 sweep behind it — a record saying the files are gone
while the files are still there. So the record is read-only and the verbs live
here.

**Each verb does exactly what the nightly ladder does.** `suspend` is not a
shortcut past `lifecycle`; it is `lifecycle.fall` with the rung named, which
queues the same job, runs the same steps and writes the same event. An operator
acting early and a clock acting on time are the same code, which is the only
way the second one stays tested.

**Two gates, as everywhere else in this module.** `require_admin` refuses on a
workspace site, and `only_for` refuses anybody without the operator role. The
first cannot be edited from a desk; the second is what keeps a curious
colleague out.

`sold` is shown before somebody edits an offering. The price never reaches the
workspaces that have it (Stripe keeps a subscriber on the price they signed up
at); the quotas do, the next time the customer changes their plan or add-ons
(`quota.apply` copies them from the offering again).

### plans.py

A workspace is sold four things it can run out of: **seats**, **storage** (its
files, in R2), **database** (its site's database on Frappe Cloud, and the
backups kept of it) and **OneAI credits**. A plan is a bundle of all four at a
monthly price. An add-on is one of them, in a fixed size, on top of a plan.

**Why a calculator.** A price list is only coherent if three things hold at
once, and they pull against each other:

1. every price covers what it costs us, with the margin we want (`margin`);
2. a plan is a better deal than buying its contents as add-ons, and more so the
   bigger it is, so somebody who needs a lot more moves up (`upgrade`);
3. an add-on is a better deal than moving up for somebody who needs a little
   more, or nobody would buy one (`addon`).

Change one price and the other two can quietly stop holding. `check` says
which, and `quote` answers the customer's version of the same question: given
what I need, which plan with which add-ons is cheapest.

Credits in a plan are monthly and do not roll over; credits bought in a pack
never expire (`topup.py`). A plan's monthly credits are valued at what the same
credits cost in packs, since that is what a customer would otherwise pay.

### press.py

We are a press *customer* and not its operator. Its whitelisted HTTP API is
the whole boundary: no server, no agent daemon, no SSH, nothing that assumes we
are inside their infrastructure.

**Nothing here is stored.** There is no `Press Server`, no `Press Bench Group`
and no `Press Site` table, because a table of somebody else's state is wrong
between syncs and the way you find out is a customer who cannot be placed on a
bench that exists. What the operator's screens need — which benches exist,
which clusters a bench can reach, what a site plan costs — is asked for and
held in redis for a minute, so the answer is press's and the cost is one call a
minute rather than one a page.

**Failures are classified, because the retry decision depends on it.** A 503
is worth another attempt in two minutes and a 400 will fail identically
forever. That decision lives in `faults.py`, which imports nothing of Frappe
and is therefore read back by a test rather than by a site.

### pricing.py

Pure, like `credits.py` beside it. This is the arithmetic between a model's
rate (`one_ai/models.py`) and a customer's balance, and
every one of its failures is a wrong number rather than an exception — so it is
read back against a table of cases rather than against a site.

**Nothing is estimated.** A `Use` is either a count the provider reported or a
parameter we sent, and it says which. Nothing is derived from the length of a
string, because a token count guessed from characters is a bill guessed from
characters.

**A use with no rate to price it is not free.** It comes back named, and the
caller charges the hold it had already taken rather than charging zero — a call
the provider answered and billed us for is a call somebody has to pay for, and
the alternative is a model that quietly costs money and earns none.

**Nothing converts between units.** A rate and a use meet on `(kind, modality,
unit)` exactly or they do not meet at all: a picture's price per image and a
model's per million tokens are not the same thing at a different scale.

`ceiling`: the point of holding it is that two calls cannot both spend the last
credit, not that the number is right — the settle replaces it with what the
provider reported. A cap nothing could price is *not* a reason to refuse: an
action that caps its output tokens against a model priced per picture has
simply capped something that does not apply. The hold covers what could be
priced, and the settle is where an unmeterable call is caught.

### search.py

Search on Cloudflare's AI Search for a workspace (docs/AICENTER.md, Search):
`find` asks the workspace's instance by keyword or by meaning (hybrid and
reranked), bills it at Cloudflare's price per search, and returns each hit's
key, text and score. An instance is one per workspace, named by `name_for`,
with its R2 data source on the workspace's prefix and its path filter on
`search/**`; none is made here. Made by hand, it is recorded with `adopt`,
and a workspace without one is refused with `NoSearch` and searches as it
did (`proxy.ai_search_state`, `proxy.ai_search`).

### web.py

Web search for a workspace (docs/AICENTER.md, Web search): `find` asks
Cloudflare's web search through our gateway, with the question alone and
Exa as the provider, and returns each page's address, title and what it
says. Billed at Exa's list price for a search of up to ten results; a
failed search is released. Whether a workspace may ask is its own optional
service, which the workspace holds (`proxy.ai_web_search`).

### proxy.py

Everything a workspace is billed for comes through here: a signed URL to put a
file, a credit hold, a plan change, a domain. **Calls only ever go tenant to
admin.** Admin never calls a tenant site, which is what removes the dangerous
credential from this design — there is no admin key that opens every
workspace, because admin never needs to open one.

A tenant proves itself with the token `push_config` wrote into its own site
config at provision time. Only a hash of it is here. The comparison is
constant-time, and **every failure says the same thing**: an unknown
workspace, a wrong token and a suspended one are one sentence, because a caller
who has guessed one of the three should not be told which.

The endpoints are `allow_guest` and that is deliberate rather than an
oversight. The caller has no Frappe session here and should not have one — a
login on the admin site is a person, and this is a machine holding a bearer
token. So Frappe's own authentication is not in the path and ours is, which
means ours has to be the careful kind.

What is *not* here: anything that carries bytes. Admin checks, signs and
records; R2 and Cloudflare carry. A file never passes through this process.

- `INTRODUCED`: what `hello` alone answers, which is `SERVING` and
  Provisioning, because the build's `invite_owner` step is a `hello`: the new
  site asks it to learn its owner. Marking it Live first instead would mail
  Workspace Ready before anybody can sign in, and an invitation that then
  failed would turn a Live workspace Failed.
- `SERVING`: Live and Overdue, and nothing below. Overdue is here because
  Overdue is defined as nothing happening to the workspace — somebody is told
  and that is all. Leaving it out would mean a failed card silently broke every
  upload on the same afternoon, which is the grace period not existing.
  Suspended is out, and below that there is no site left to call. It costs
  nothing to say so anyway: press has already deactivated a suspended site, so
  a call from one is a call from a site that should not be running.
- `_offered_token`: a header rather than a parameter: a token in the body is a
  token in a traceback, in a slow-query log and in anything that echoes what it
  was sent. Not `Authorization`, though, and this was measured rather than
  reasoned: Frappe's own `validate_auth_via_api_keys` reads that header, sees
  the word token and splits the rest on a colon to get an API key and secret. A
  token of ours has no colon, so every call died with
  `InvalidAuthorizationToken` before reaching this module. A header of our own
  stays out of its way.
- `CALLS_A_MINUTE`: per tenant per minute, and not per IP: every tenant on one
  bench calls from one address, so an IP limit would be a limit on the busiest
  neighbour. High enough that a workspace doing real work never meets it, low
  enough that a leaked token cannot be used to run up a bill.
- `hello`: `database_bytes` is the workspace's own measure of its database,
  sent along because the workspace can read it and admin cannot. It is shown
  and warned about, never billed: the sites are on our own servers, where
  Frappe Cloud sets no limit, so the limit is ours (`quota.py`). The tenant
  caches the answer in its own `Workspace Account`, so a screen showing a plan
  or a quota draws without a round trip and keeps drawing through an admin
  outage. That is why it returns the whole picture rather than answering one
  question — the alternative is a workspace making four calls to render a
  header. It returns what exists. A zero is a fact and an absence is the truth,
  so anything not built yet is left out rather than reported as nothing —
  `credits` arrived with the ledger and is a real number now. `standing` is the
  ladder: whether money is owed, and how many days are left before the next
  thing happens. It is there rather than behind a call of its own because a
  workspace that has to ask a second question to find out it is about to be
  suspended is a workspace that will not ask.
- `hello`'s `credits`: a sum over the ledger rather than a number anybody
  stored, which is why it is safe to answer from here rather than keeping a
  copy on the workspace that could disagree with its own history. `gift` is
  the last credits an operator gave, with their note, so the customer hears why
  and not only that the number went up (`one/account.py`).
- `ai_run`: `turns` is the conversation so far and `tools` are the ones the
  workspace is willing to run. Both arrive whole each round, because this is
  stateless: a model that wants to look something up is answered with what it
  asked for, the workspace runs the tool as whoever is signed in there, and
  calls back. `model` and `extra` are the workspace's own settings, sent with
  the call because they live on the workspace's site and admin never calls a
  workspace. Both are checked here rather than trusted: the model against what
  is offered and what the action needs, and the extra against a length,
  because what a tenant sends is what a tenant's administrator typed. The
  instruction the action carries is **not** sent — it is read here, from the
  administrator's own copy of the fixture, which is the copy a workspace cannot
  write.
- A refusal in `ai_run` is thrown rather than allowed to propagate, because
  frappe answers an unhandled exception with a body carrying only `exc_type` —
  so the sentence that says *why* ("this has gone five rounds", "that model is
  not offered") never reaches the workspace, and the panel has nothing to show
  but the endpoint's name. `Again` is a subclass and keeps its own name, so the
  caller can still tell retryable from permanent.

### quota.py

The limits are a sum and copied onto `Tenant` when the workspace signs up
(`signup.py`) and whenever its plan or an add-on changes, and only then: an
offering is a price list the operator edits, and re-pricing a plan must not
change what a customer already bought. Everything that enforces a limit reads
the copy:

* **seats**, pushed to the workspace in `hello`, where People refuses a seat
  past it;
* **storage**, refused at upload by `storage.put_url`;
* **database**, measured by the workspace itself and sent in `hello`, where it
  is shown and warned about. The sites are on our own Frappe Cloud servers,
  where a site is unlimited and carries no Frappe Cloud plan, so there is
  nothing to move it to: the limit is ours to watch, and Home says when a
  workspace is past it;
* **credits a month**, granted by `topup.monthly`.

A zero on the plan is no limit, as Offering says; an add-on on an unlimited
plan changes nothing.

### sales.py

The admin site is a One workspace too, and it sells One. So a signup is kept the
way any company using One keeps a sale, in ERPNext's CRM, rather than only in
the operator's tables:

* **Lead**, when the signup is taken (`signup.start`): who, the workspace they
  asked for, and the plan, with the source Website.
* **Deal**, at the same moment, because a signup is sent straight to pay: an
  Opportunity from the lead at the Checkout stage, worth a year of the plan.
  Paying wins it; a checkout left unpaid for `ABANDONED_DAYS` is lost with the
  reason Checkout Abandoned, which leaves a list somebody can follow up.
* **Customer**, when the payment lands (`signup.accept`): made from the lead by
  ERPNext's own mapping, billed in the plan's currency, and written on the
  Tenant, where our invoices find it (`books.py`).

Nothing here stops a signup. Every step is wrapped so a CRM that cannot take a
record logs the failure and the workspace is still made: the money has been
taken, and a missing lead is a thing to fix, not a reason to refuse.

### setup.py

The operator gives One Admin Settings one master token, made from
Cloudflare's **Create Additional Tokens** template, and presses **Set up
Cloudflare**. Everything a workspace needs from Cloudflare is then found or
made here:

- One's own three tokens (`TOKENS`, `ensure_token`): **OneAdmin**, which
  every other step and OneAdmin's own calls run with; **OneAdmin Storage**, whose
  id and the SHA-256 of whose secret are R2's S3 keys, allowed only the two
  buckets; and **OneAI**, which may run the gateway and nothing else. The
  master token makes and mends them and is used for nothing else. Each is
  found by its name before one is made, and its permissions are set again
  whenever they differ from `TOKENS`. OneAdmin starts allowed any account
  and zone, since neither is known yet, and is narrowed to the two found in
  the same run. A permission is looked up by the names Cloudflare may give
  it (the API says Write where the dashboard says Edit); Email Sending and AI
  Search are named nowhere in Cloudflare's documentation, so whichever
  permission starts so is taken, and none is no complaint;
- the account and the zone;
- the KV namespace both Workers read;
- the two R2 buckets and the S3 keys to them;
- the web router and the mail Worker, with their routes and DNS;
- the certificate for `*.t.4dl.app` (`certificate`): an Advanced Certificate
  Manager pack, ordered only when no pack, issued or pending, names both
  `t.4dl.app` and `*.t.4dl.app`; the order names the zone's apex as well,
  which Cloudflare requires of every pack. ACM is a paid add-on and has to be enabled
  on the zone first, and the key needs SSL and Certificates: Edit; without
  either, the step says so and nothing is ordered;
- mail routing and sending for the mail domain;
- the AI gateway OneAI calls through (`one`, or the one named in settings),
  with its logs of counts and costs on and Guardrails flagging prompt
  injection and Llama Guard's thirteen hazards on every call. Flagged, not
  blocked: OneAI's own guard is what stops it acting on what arrived. What
  the gateway already holds (caching, rate and spend limits) is kept.

**It never takes what is somebody else's.** A resource that exists under our
name is ours and is kept. One that exists but belongs to something else — a
route another Worker answers, a DNS record that points elsewhere — is left as
it is and reported. Nothing is deleted.

The one deliberate exception is the zone's email catch-all. There is only one
per zone, and the mail domain cannot work without it, so it is pointed at our
Worker whatever it held. The operator decided that for `4dl.app`.

**A run cut off anywhere loses nothing.** It runs as one background job
(`set_up` enqueues `run`, deduplicated, and `run` holds a lock that expires on
its own), so a closed page or a dropped connection stops nothing. Each thing
is saved the moment it is found or made (`keep`, `own`, each with its own
commit), and each step's result as it ends (`note`). A token is the one thing
Cloudflare shows only once: one made but never saved, because the run died
between Cloudflare answering and the secret being stored, is found by name on
the next run, its held secret fails `/user/tokens/verify`, and it is rolled,
the same token with a new secret, saved before anything else. The demo check
`oneadmin_sets_up_cloudflare_from_a_master_token` cuts a run off exactly
there against a stand-in Cloudflare and checks that the next run makes
nothing twice.

**Running it twice is running it once.** Each step reads before it writes, so
the button is also the check: pressed on a set-up account it changes nothing
and says so. Our own Workers are the exception: their code is the
repository's, and a step redeploys one whose deployed code differs, which is
how a change to deploy/edge or deploy/mail reaches Cloudflare.

A setting already filled in on the form is never replaced. A step that finds it
empty writes what it found or made.

### signing.py

Nothing of Frappe in here, because an endpoint that takes money on the strength
of this check is an endpoint anybody on the internet can reach. It has to be
readable in one sitting and testable in milliseconds, and the two ways to get
it wrong are both silent:

* **comparing signatures with `==`** leaks how much of a guess was right, one
  byte at a time, to anybody willing to measure;
* **ignoring the timestamp** means a signature captured once is good forever,
  so an old "payment succeeded" can be replayed to provision another workspace.

Stripe's scheme, for the record: the header is `t=<unix>,v1=<hex>,v1=<hex>…`,
the signed payload is `<t>.<raw body>`, and the signature is HMAC-SHA256 of
that with the endpoint's own secret. More than one `v1` appears while a secret
is being rotated, so any of them matching is a match.

### steps.py

**Every step must be safe to run twice.** A network timeout leaves us genuinely
unable to tell whether the call landed, and the failure we refuse to accept is
creating two sites and billing a customer for both. So a step that creates
something looks first, and a step that sets something sets it to the same
value it would have set the first time.

A step returns `None` when it is done and the job may advance, or `WAIT` when
it has started something press has not finished — the runner comes back after
a backoff and runs the same step again. Raising `faults.Again` means the
attempt failed but the next one might not; raising `faults.Refused` stops the
job and records why.

**Nothing unwinds.** A half-provisioned site whose job failed is a site an
operator resumes, because unwinding is how you end up having taken money and
then deleted the thing it bought. The customer is told the truth, which is
that it is taking longer than it should.

- `ORDER` and `WALKS`: every walk but `Provision` is the ladder — see
  `ladder.py` for what each rung means and `lifecycle.py` for what starts one.
  They are here rather than in their own module because they are the same kind
  of thing: an idempotent step that talks to press, driven by the same runner
  and the same backoff.
- `SAID`: a job that stopped on `archive_site` tells somebody nothing; a job
  that stopped while asking Frappe Cloud to delete the site tells them where to
  look. Every step in `WALKS` is named there, and a test fails on one that is
  not — because the failure is silent: the screen falls back to the function
  name and nobody notices it was meant to say something.
- `place_it`: chosen here, by the job, and not on the signup page: a Frappe
  Cloud that is slow or down must not stop anybody signing up or paying. Every
  workspace runs on the one bench group Settings names (the first the team owns
  when none is named), and it has to carry every app a workspace gets: a site
  asked for on a bench missing one is refused by press half way, so it is
  refused here first, in words that say what to add. The server is the
  emptiest open one in Settings' list, an EU one for a workspace that asked for
  the EU, that has room and that the bench group has been added to. None
  fitting fails the job, saying what to buy or add, and Resume places it once
  there is one.
- Making the site on our own server: press puts a site there only when it is
  named with the bench group's version, and on one of its free Unlimited plans,
  which sets the CPU time a day and nothing we charge for. The limits a
  customer bought are ours (`quota.py`). Named so, press takes the group on
  that server carrying these apps; `place_it` has already checked it is ours.
- `route_it`: one key at the edge, the slug against the press site name, which
  is all the Worker needs to rewrite `Host` and hand the request to press.
  Nothing is asked of press, and that is the point: the name it serves is its
  own, so there is no DNS to verify and no certificate to issue. The browser
  is served by the wildcard on our zone.
- `push_config`: the token is generated there and never again: only its hash
  is kept, on the tenant. If the step runs twice the site gets a second token
  and the first stops working, which is correct — the first one may be the one
  that leaked. It sends a list of `{key, value, type}` rather than an object,
  because press has two `update_config`s and they disagree: the doc method
  takes a mapping and the whitelisted `press.api.site.update_config` — the
  only one a token reaches — iterates and reads `c.key`. Handed a mapping it
  iterates the keys as strings and dies on the first one. `max_file_size` is
  set there too, since it is the one Frappe limit the site cannot change for
  itself (see `one_storage/store.py` `unlimit`). `host_name` is set there and
  not through press's `set_host_name`, which needs a `Site Domain` record
  first. Our name is deliberately not one of those: the workspace is reached
  at it because a Worker rewrites `Host`, and press is never told it exists.
  So the config key is written directly, and press's own `Site.host_name`
  stays the press name. Nothing overwrites this unless a customer later makes
  one of their own domains primary, which is exactly when it should change.
- `create_site`: a retry whose first answer was lost asks press for
  `<slug>.<press domain>` first (`_ours_already`), and records it rather than
  asking for a second site, which press would refuse.
- `_still_going`: Suspend, Archive and Drop each ask again, before the step
  that cannot be undone (`deactivate_site`, `archive_site`, `empty_storage`),
  whether the workspace is still meant to go down — on the rung the job left
  from (`STILL`), or Live or Overdue with a closing day for an Archive, and
  with no Restore queued. If not, `CalledOff` ends the job. After
  `archive_site` the Archive job finishes whatever happens: the site is gone,
  and leaving it billed would be worse.
- `invite_owner`: we cannot sign in to the site we built, and we hold only a
  hash of its token, so the site does it: `account.wake` makes it ask
  `proxy.hello`, which names the owner, and a workspace nobody administers yet
  makes them its administrator and mails One's own invitation
  (`one_account/owner.py`). Safe to run twice: a workspace that has an administrator
  does nothing. A site that has not read its new config yet answers that
  nobody administers it, and the step waits and asks again, as `site_is_up`
  does.
- `note_backup`: recorded and not copied. Press takes an offsite backup as part
  of archiving and keeps it for as long as its own retention says; pulling
  four gigabytes through this site to put them in our R2 would move real bytes
  to no end, because restoring is press's `restore` from press's copy either
  way. What is worth keeping is the name, so somebody can ask for it. A
  workspace with no backup is not a reason to stop. It may be a site that
  never had one, and refusing to archive it would leave it running for free
  forever.
- `CALLED`: arriving at Live is what somebody reading the log wants to see as
  Restored, because that is the interesting half — nothing writes an event for
  a workspace that was always Live.

### storage.py

Admin is in the control path and never the data path. It checks the quota,
works out the key and signs a URL; the browser then talks to R2 directly and
not one byte passes through this process. Doing it the other way would put
every tenant's uploads through one Frappe site with four workers, and that is
the first thing that would fall over.

**Two buckets, Global and EU, and a prefix per tenant.** Jurisdiction is chosen
once at signup and is permanent — R2 pins a bucket to it at creation, so moving
afterwards means copying every object. Never a bucket per tenant: a lifecycle
rule written against one bucket gets written against the next one too, and a
key scoped to a bucket still reaches every tenant in it.

**Usage is measured, not reported.** The nightly pass lists each prefix and
adds it up. A workspace that reported its own number would be a workspace that
could under-report it, and the whole reason storage is billed from here is that
a tenant cannot be the authority on what it owes.

`empty` is the last rung of the ladder and the only step on it that destroys
anything of ours. It is written to be safe to run twice, because the runner
retries: emptying a prefix that is already empty deletes nothing and succeeds,
so a sweep that died half way finishes on the next attempt rather than starting
an argument about where it got to. The prefix comes from `keys.prefix`, which
refuses a slug with a slash in it. That is the whole of what stands between
this and deleting the wrong workspace's objects, and it is the reason that
function is pure and tested.

### stripe.py

No `stripe` package. Two calls are needed — make a checkout session, and read a
webhook — and one of them is a form-encoded POST. A dependency that exists to
save writing `requests.post` is a dependency to keep current forever.

**Nobody leaves One to pay, wherever Stripe allows it.** Every Checkout
session is made with `ui_mode: "embedded"` and handed back as its client
secret and the publishable key (`embedded`), and the page draws it with
Stripe.js (`public/js/one_pay.js`): the signup page in place of its form, the
welcome page's Pay again, credit packs and Payment Method in a dialog in Plan
and Credits, and Update card in the account's invoices page. It is still
Stripe's form in Stripe's frame, so the card never touches us and PCI stays
Stripe's. A signup's session carries a `return_url` to the welcome page,
since that page is where a signup goes next; the others are
`redirect_on_completion: "never"` and the page hears `onComplete`. A card is a
`mode: "setup"` session (`checkout_for_card`); nothing is charged, and the
webhook makes the card the customer's and the subscription's default
(`card_set`), so the next invoice is paid with it. Two things stay Stripe's
own pages, because Stripe has no embedded version of them: the billing
portal (billing address, tax ID, receipts: **Billing Details**) and paying an
open invoice (**Pay**). Stripe.js has to load from `js.stripe.com` — Stripe
allows no copy — so it loads the first time something is paid for and not
before. The publishable key is `stripe_publishable_key` in One Admin Settings
or site_config; it can only draw a session the secret key made.

The webhook is the dangerous half and it has three guards, in this order:

1. **the signature**, checked in `signing.py`, which has no Frappe in it;
2. **the event id**, which is unique on `Stripe Webhook Event`, so a redelivery
   meets a database index rather than a check somebody has to remember to
   write;
3. **the request's own state**, since `signup.accept` returns the tenant it
   already made rather than making a second one.

Any one of the three would stop a double provision. All three are here because
Stripe redelivers by design — on a timeout, on a non-2xx, hours later — and the
cost of being wrong is a second site somebody is billed for.

The clock is `time.time()` and not `frappe.utils.now_datetime()`. The latter is
the *site's* local time as a naive datetime, so calling `.timestamp()` on it
reinterprets it as the server's local time and lands an offset out — measured
here at four hours, which refused every real delivery. Stripe's `t` is a Unix
timestamp, so it has to be compared against one.

- `OWED`, `SETTLED` and `ENDED`: a subscription's invoice failing is what
  starts a fall; one being paid is what ends it; the subscription being
  cancelled starts one too (`lifecycle.ended`). Deliberately these three and
  no more. Stripe sends dozens of event types and an endpoint that grows a
  branch per type is an endpoint nobody can reason about. `ENDED` is needed
  because the ladder does *not* notice a cancelled subscription by itself: no
  invoice is sent, so none fails, and the workspace stayed Live for ever. It
  is matched by the subscription's id, not the customer's. The endpoint in
  Stripe has to send all five kinds acted on: `checkout.session.completed`,
  `invoice.paid`, `invoice.payment_failed`, `customer.subscription.deleted`
  and `charge.refunded`.
- `_settles`: an invoice paid while a workspace is Overdue or Suspended
  restores it only when it is the workspace's own subscription's and Stripe
  holds no other open invoice for the customer (`ladder.settled`). An add-on's
  proration paid while the renewal that failed is still open restores
  nothing. Since API version 2025-03-31 the subscription is under
  `parent.subscription_details`, so both places are read.
- `_portal`: the billing portal is opened with a configuration of ours, found
  by `metadata[one]` or made once, that turns off cancelling and changing
  plan: either would bypass `billing.take` and `closing.ask`, and the account's
  default configuration may allow both. So `customer.subscription.updated` is
  not handled: nothing but our own calls changes a plan.
- `_post`: a POST that makes something (`MADE_BY_POST`) carries an
  Idempotency-Key, the hash of what it asks and the ten minutes it is asked
  in, so a retry after a lost answer gets the first price, session or item
  rather than a second. Updates carry none: asking the same change twice is
  harmless, and a replayed answer to a change made, undone and made again
  would be wrong.
- A signup that cannot be built (`signup.NotBuilt`) is answered 200 and kept
  handled: raising rolled back the Failed status, the operators' notice and
  the error, and Stripe redelivered into the same failure. Retry Signup is
  the way on. A completed checkout naming no request we have is ignored.
- A trial changes nothing downstream. Stripe still takes the card, still
  completes the session, and still sends `checkout.session.completed` — the
  subscription simply starts in `trialing` with a zero invoice. So the
  workspace is built exactly as a paid one is, and when the trial ends the
  first real invoice arrives as `invoice.paid` or `invoice.payment_failed`,
  which is the ladder we already have.
- `_remember`: the unique index is the idempotency. Catching its refusal is not
  a fallback for a check we forgot — it *is* the check, and it is the only one
  that holds when two redeliveries arrive at once. The insert is wrapped in a
  savepoint rather than caught around a bare `rollback()`. A plain rollback
  undoes the whole request, and measured here it undid the *first* delivery's
  work when the second one arrived before it had committed — the second then
  looked for a row it had just destroyed. `None` means another delivery holds
  this event and has not committed yet. The caller answers 200 and does
  nothing, which is right: the delivery that holds it is about to finish, and a
  second worker racing it is how one payment becomes two workspaces.
- `PRORATED`: the difference for the rest of the period, invoiced now, and
  refused at once if the card declines rather than left as an unpaid invoice
  the ladder would notice days later. A step down is a credit on the next
  invoice, which Stripe does by itself.

### topup.py

Two ways credit arrives and both of them write one `Credit Ledger Entry`, which
is the point: there is no second path into a balance and no number anybody
stored. `ledger.grant` takes an idempotency key, so both of the things that
would otherwise double a customer's credit — Stripe redelivering a webhook, and
a nightly job running twice — meet a unique index rather than a check somebody
remembered to write.

**Packs rather than amounts.** A customer buys a row from a price list, not a
number they typed. That is a decision rather than a shortcut: a calculator on
this screen is a second place where credits per dollar is decided, and the
first one is in One Admin Settings where it belongs.

**A plan's monthly credit does not roll over.** It carries the end of its own
month as `expires_on`, which is the case the ledger's draw order was built for
— the soonest-expiring grant goes first, so nobody loses credit they paid for
while a free monthly allowance sits unused beside it.

`GRANTED_ON`: Overdue is there for the same reason `proxy.SERVING` carries it:
Overdue is defined as nothing happening to the workspace, and cutting off its
allowance would be the grace period not existing.

### Google News

`google_news.py` is the only place in One that reaches Google News. A
workspace's Google News source asks `proxy.google_news` for an edition (a
topic or a search, in a country and language) and gets what was last
fetched; it never asks Google itself, and how often Google is asked is not a
workspace's to set.

- **Editions are shared.** Every workspace following the same topic or search
  in the same country and language reads one copy, held in Redis.
- **One request at a time, on a timer.** `tick` runs every five minutes on
  the admin site and fetches at most one edition: one never fetched first,
  else the stalest older than `REFRESH` (two hours). That is twelve requests
  an hour at most, whatever the number of workspaces. Asking never fetches; a
  first ask answers `waiting`, and the workspace asks again in ten minutes.
- **A refusal stops everything.** Any answer from Google but a feed pauses
  every fetch for `FIRST_PAUSE`, doubling each time in a row up to
  `LONGEST_PAUSE`; the next good fetch clears it.
- **Nothing is kept for nobody.** An edition no workspace asked for in
  `FORGOTTEN` (three days) is dropped, and a workspace follows at most
  `MOST_A_WORKSPACE` editions, so one cannot make the rest wait.
- **Not charged.** It costs Google nothing we pay for, and the headlines are
  for previewing only (the `news-content` clause).

### Weather

`weather.py` gets the weather from OpenWeather's One Call API 4.0 for every
workspace that has the Weather service on (`one/weather.py`).

- **Places share a reading.** A place is a cell about ten kilometres across,
  its coordinates to one decimal, so two workspaces in one city share one
  reading, held in Redis.
- **It is fetched only when asked, and only when old.** A cell's next hours
  (`timeline/1h`) are fetched again after two hours and its next days
  (`timeline/1day`) after twelve: fourteen calls a day for a place shown all
  day. Nothing runs on a timer. "Now" is the hour that covers the present,
  read from the hours already held.
- **The first place a day is free.** Every other place a workspace shows that
  day costs `CREDITS_A_DAY`, charged the first time it is served that day,
  whether it was fetched for that workspace or already held for another.
  `calls_today` counts the calls against OpenWeather's free thousand a day.
- **Places are found by name** through OpenWeather's geocoding, which is not
  charged.
- **The key never leaves.** It is the OpenWeather Key in One Admin Settings.
  OpenWeather takes it in the address, so `_get` raises a failure again
  without the address, and the `prev` and `next` links OpenWeather answers
  with are never kept.
