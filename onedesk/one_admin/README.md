# OneAdmin

Written by hand. Everything above **Under the hood** is for the operators who
use OneAdmin, and OneAI reads it to answer "how do I…" questions. Under the
hood is for the people who build it.

OneAdmin is the console One is run from. It holds the workspaces customers pay
for, the jobs that build and close them, their domains, the price list,
signups, credits and OneAI's models.

It's only on the admin site, and only for **One Operator**. No one on a
customer's workspace can open it, whatever roles they hold there.

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

It was created once, and the admin site linked to it, by `house.ensure`.

## Home

**OneAdmin** in the dock opens **Home**.

The number cards at the top each open the list they count:

- **Live**: workspaces serving their customers.
- **Building**: workspaces still being built.
- **Owing**: workspaces overdue or suspended for non-payment.
- **Failed**: jobs that stopped on a step.
- **Paid, Not Built**: paid signups with no workspace.

**Needs You** lists what needs an operator, most pressing first. Each row says
what it is, why, and since when, with one action:

- **Failed job**: what it was doing, the step it stopped at and the error.
  **Resume** runs it again from that step. Every step is safe to run twice,
  so this never builds a second site.
- **Paid signup with no workspace**: whose it is and why it stopped.
  **Build Workspace** creates the workspace, as paying would have.
- **Workspace owing**: overdue or suspended, and since when. Open it to act.
- **Domain**: waiting over a day for DNS, or not working. **Check Again**
  asks Cloudflare for its status.
- **Slow build**: a new workspace still waiting on Frappe Cloud after three
  hours. Waiting never fails a job, so this is where a stuck build shows up.
  Check the site in Frappe Cloud.
- **Stalled job**: due but not run for fifteen minutes, with **Run Now**.
- **Over database**: a workspace holds more than it bought. Frappe Cloud sets
  no limit on dedicated servers, so OneAdmin watches it.
- **Server filling up**: at four-fifths of its **Most Workspaces**, full, or
  no open server left for new or EU workspaces. Buy the next one before a
  signup fails.
- **Update available**: for the bench group new workspaces use, with the apps
  that have one. Deploy it in Frappe Cloud. It updates every workspace on
  that bench group at once.
- **Wrong price**: a problem Price Check found.
- **No model**: an AI action no offered model can run.

Click a row to open the record. Home updates live, without reloading.

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

A workspace is built, then **Live**. When a payment fails:

1. **Payment overdue** for 7 days. It keeps working.
2. **Suspended** for 14 days. No one can sign in, and nothing is changed.
3. **Archived** for 30 days. The site is deleted after a backup. Files stay.
4. Then its files are deleted.

It moves one step a night. The periods are set in **Settings**. Paying before
the files are deleted brings it back: at once from overdue, and from
suspended by a job that serves the site again.

### Buttons

Each button moves the workspace one step and asks first.

- **Mark Overdue**, **Suspend**, **Archive** and **Delete Files** move it to
  the next status now. Archiving and deleting files can't be undone.
- **Restore** brings back an overdue or suspended workspace.
- **Refresh** › **Measure Storage** or **Refresh Domains**.
- **Billing** › **Invoices**, **Give Credits** (with a note and an optional
  expiry), **Credit Ledger** and **AI Usage** by model.

Below the fields are its **Jobs**, **Log** and **Domains**, its **Customer**
in the books and the **Signup** that paid for it.

The owner is emailed when the workspace is suspended, archived (with the
deletion date) and restored. Overdue notices show on their own workspace,
which still works then.

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
time. There are five types:

- **Provision** builds a new workspace. It chooses a server, checks the name
  is free, creates the site in Frappe Cloud, waits for it, sets up the
  address, configures the site, invites the owner and marks it live.
- **Suspend** and **Restore** stop and restart the site.
- **Archive** deletes the site after a backup, cancels the Stripe
  subscription so it isn't invoiced again, and removes its mail route.
- **Drop** deletes the files.

The server is the emptiest open one in Settings › Servers (an EU one for an
EU workspace), and is shown on the workspace as **Server**. A bench group
missing erpnext, hrms or onedesk fails the first step, naming what to add.

**Jobs** lists the ones not done, with the workspace, type, status, current
step and last update. Jobs run every two minutes.

- **Waiting to run**: its next step is due.
- **Waiting on Frappe Cloud**: a step waits on Frappe Cloud, such as a site
  being built. This is checked every minute and never fails the job. A slow
  build shows on Home after three hours.
- **Failed**: a step that errors is retried, less often each time. After
  twelve tries the job fails and operators are notified.

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
**Storage (GB)**, **Database (GB)** and **Credits a Month** they need. It
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
  **Update card** per workspace, since each workspace is billed separately.
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
taken since, or a Frappe Cloud refusal, will stop it again.

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
OneAI answers **Where did the credits go?**.

## Models

**Models** lists every OneAI model from the two providers, Cloudflare Workers
AI and Google AI Studio. The list syncs nightly from each provider, with
prices from each provider's published pricing page.

The sync does two things on its own:

- A model the provider stops listing becomes **Withdrawn**.
- A model whose price can't be read is taken off sale.

When either affects an offered model, operators get **Model Withdrawn**.

What operators set:

- **Offered**: workspaces may pick it. **Offer** and **Stop Offering** are on
  each row.
- **Default For**: what an action runs on when the workspace picked nothing.
- **Markup**: empty uses the default in Settings.
- **Priced by Hand**: for a model whose price page can't be read. **Needs
  review** shows what couldn't be read. Price it by hand or leave it off sale.

### Defaults

- Gemma 4 (`gemma-4-26b-a4b-it`, the one on sale) is the default for text, at
  a fraction of Gemini's price.
- Gemini 2.5 Flash stays on the actions that need it: Print Design, Workspace
  Setup, and the second review of an extension's code (Review an Extension).
- An action can name its own model (**Runs On** on the AI Action).
  **Print Design** runs on gemini-2.5-flash because a page layout is one long,
  exact answer the small model gets wrong. The chat hands a conversation to
  Print Design when it calls `print_layout` or `design_print_format`, and
  those rounds are charged to Print Design. **Workspace Setup** uses the same
  model for `suggest_approval`, because an approval's states, steps, roles
  and conditions must fit together and the small model repeated its mistakes.
- With no default for what an action needs (reading a scan, transcribing a
  recording), it uses the default for something else that can do it, then
  the cheapest offered model from the **Preferred Provider** in Settings
  (Google).
- A workspace whose own pick is withdrawn falls back the same way instead of
  failing. An action nothing can run shows on Home.

The list sorts offered first, then priced, then needing review, then
withdrawn. A model's page shows its markup, which actions use it by default
and how many workspaces called it this month. **Test Call** makes one real
call against a workspace's credits and shows the cost. It's charged.

OneAI answers **Is this model worth offering?** on a model and **Which
actions have no model?** on the list.

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
Domains**. They add a domain, create one CNAME record in their DNS pointing
to their One address, and choose the main address used in links and emails.
Operators can't add, remove or set the main domain for them, because it's
the customer's DNS.

A domain stays **Waiting** until its DNS record is right. Cloudflare keeps
checking and issues the certificate once it is. One checks each waiting
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
  an operator, or Frappe Cloud).
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

- **Frappe Cloud**: the account the sites are built on. The servers are
  rented from Frappe Cloud, and customers never see it. Includes the **Bench
  Group** every workspace runs on, the **Site Plan** for each site (one of
  Frappe Cloud's free Unlimited plans, which only sets daily CPU time), and
  **Servers** (below).
- **Cloudflare**: one token. **Set Up Cloudflare** finds or creates the rest
  and shows the result under **Last Setup**.
- The R2 buckets and keys, Stripe's keys and the AI Gateway.
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

**OneAI**

- **Preferred Provider** (Google), whose cheapest model runs an action with
  no default.
- The persona sent to the model before every action.

**Grace Periods**

- The days a workspace spends overdue, suspended and archived before the next
  step.

### Servers

**Servers** lists the servers new workspaces are built on. To add one:

1. Buy it in Frappe Cloud, add it to the bench group and deploy.
2. Add a row here with its name. Its **Region** fills in from Frappe Cloud on
   save.
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

Operators are notified of:

- **Job Failed**: a job stopped, with the step and error.
- **Signup Not Built**: someone paid and their workspace couldn't be built,
  with the reason.
- **New Signup**: someone paid for a new workspace.
- **Workspace Owing**: a workspace became overdue or was suspended.
- **Workspace Asked to Close**: a billing contact asked to close a workspace.
- **Settings Changed**: another operator saved Settings, with what changed.
- **Model Withdrawn**: the nightly sync took an offered model off sale, with
  what runs instead.
- **Domains Waiting**: each morning, domains waiting over a day or not
  working.
- **Paid While Archived**: a payment arrived for a workspace that's already
  archived or dropped. The payment is kept. Rebuild it from its backup or
  refund it in Stripe.

Customers are emailed:

- **Sign-in Link**: when an account holder asks to sign in. Can't be turned
  off.
- **Confirm Your New Email** and **Account Email Changed** (to the old
  address): when an account holder changes their email.
- **Workspace Moved to You** and **Workspace Moved Away**: when billing moves
  to another account.
- **Workspace Delayed**: once, if a paid workspace couldn't be built, so a
  payment is never followed by silence.
- **Finish Signing Up**: once, a day later, if they never paid.
- **Workspace Ready**: when it's built (see Jobs).
- **Workspace Suspended**, **Workspace Archived**, **Workspace Closed** and
  **Workspace Restored** (see Workspaces).

Each can be turned off or reworded under **Settings › Notifications**. Only
operators are offered them.

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

## Under the hood

For the people who build OneAdmin. OneAI does not read past this heading.

- **The account** (`accounts.py`, docs/ONE-ACCOUNT.md) is a frappe Website
  User named by its email, and `Tenant.account` links a workspace to it;
  `accounts.hold` runs from `signup.accept` and from the `accounts` patch.
  `send_login_link` overrides frappe's on the admin site only, and
  `home_page` (hooks `get_website_user_home_page`) sends it to `/account`.
- **The portal pages** are `www/start`, `www/welcome`, `www/account`,
  `www/account_invoices` and `www/account_profile` (routed from
  `/account/invoices` and `/account/profile`) and `www/legal`, drawn
  in `public/css/portal.css` to frappe-ui's look (a guest page loads no desk
  controls). `signup.available`, `start`, `pay` and `state` are the guest
  calls, each rate-limited; `start` takes the signed-in account's email over
  whatever the form sent. `Account Request.access_key` opens `/welcome`
  (`signup.owned`); `signup.remind` is the daily Finish Signing Up.

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
- `ai.py`: `console_today` is `home.needs` for OneAI, and `workspace_facts`
  one workspace's head and connections; both are refused to anybody who is
  not an operator on the admin site.
- **A new workspace's owner** (`one/owner.py`, on the tenant): the admin site
  cannot sign in to a site it built and holds only a hash of its token, so
  `proxy.hello` names the owner and a workspace with no administrator yet
  makes them one and invites them. `steps.invite_owner` posts to the new
  site's `account.wake`, which only makes it ask, and waits until it says it
  has an administrator. `tell.ready` mails Workspace Ready from `steps.live`.
- **Jobs**: `runner.py` publishes every write (`notify=True`); the form's
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
  OneAI's suggestions reach a report as `report:<name>` (`one_ai/suggest.py`).
- **Our own workspace** (`house.py`): `Tenant.is_house`; `ensure` makes it
  and writes `one_tenant` and `one_token` into the admin site's config;
  `ledger.reserve` never refuses it; AI Usage's `_ours` takes its share out
  of Charged and the margin.
- **Settings** (`doctype/one_admin_settings`): `heads.NEEDED` is what each
  connection needs and what stops without it, for the head and for
  `ai.settings_check`; `_tell` is Settings Changed. `offerings.credit_price`
  is what a credit sells for, from the smallest pack.
- **AI Usage** (`report/ai_usage`): `ledger.usage` sums the calls (one
  settled Credit Reservation each, with `usd`, what the provider charged, kept
  by `ledger.commit` since `patches/call_costs.py`); `usage` in the report is
  the cut and the margin, and `ai.ai_usage` reads it for OneAI.
- **Models** (`catalogue.py`, `prices.py`, `capability.py`):
  `actions.default_model` is what an action runs on when nobody picked, and
  what a withdrawn pick falls back to; `tell.models_gone` is Model Withdrawn;
  `home._unmodelled` the Needs You row. `patches/gemini_default.py` made
  Gemini 2.5 Flash the default, and `patches/gemma_default.py` Gemma 4. `ai.model_facts` is the catalogue for OneAI.
- **Credits** (`ledger.py`, over `credits.py`, which has no frappe in it):
  a balance is a sum; `left_of` is one grant's rest; `take_back` writes a
  spend of it (source Operator); `last_gift` travels in `proxy.hello` so the
  workspace says Credits Added with the note (`one/account.py`).
  `patches/credit_model.py` linked old spends to their model.
  `ai.credit_facts` is a workspace's credits for OneAI.
- **Signups** (`signup.py`): `accept` is what a payment calls; it sets
  Paid, then Provisioning, and never unwinds. `built` sets Done from
  `steps.live`; `abandon` is nightly; `tell.signup_not_built` mails the
  operators and, once, the customer. `patches/signup_states.py` mended the
  rows from before. `ai.signup_facts` is a signup for OneAI.
- **Plan Calculator** (`report/plan_calculator`): `quote` is `plans.quote`
  over the add-ons, as `billing.quote` is for the customer, with what each
  way costs us; `needs_of` is a workspace's needs now. `ai.plan_quote` reads
  both for OneAI.
- **Domains** (`domains.py`): the customer's own names are custom
  hostnames on our Cloudflare zone; Frappe Cloud is never told of them.
  `Tenant Domain.is_main` is the console's copy of the workspace's
  `primary_domain`, kept by `make_primary`; `_keep` publishes each answer.
  `ai.domain_facts` is a domain for OneAI.
- **The log** (`log.py`): every row is `log.write`, which says who from the
  session or the job's owner (the proxy passes Customer), links the job,
  and stores a fixed phrase from `SAID` (`_lt`) in English for the list to
  translate. `log.over_storage` keeps one row per stretch over.
  `log.timeline` is the workspace's `additional_timeline_content`.
  `patches/log_in_words.py` reworded the rows written before.
- **Workspaces is Tenant.** `one/titles.py` hands the rail's labels for our
  own doctypes down in the boot, and `public/js/reports.js` writes them as the
  list's title, the crumb back to it and a record's connections. The owner's
  mails are `tell.owner`, from `steps._arrive`, which writes `status_since`
  with every status and publishes the change (`notify=True`), so an open
  form and list update. `patches/status_since.py` dated the workspaces
  written before it, which the ladder otherwise never moved.
