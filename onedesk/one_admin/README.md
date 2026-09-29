# OneAdmin

Written by hand. What OneAdmin does and how to use it. Everything above
**Under the hood** is written for the operators who use it, and OneAI reads it
to answer "how do I…" questions. Under the hood is for the people who build it.

OneAdmin is the console One is run from: the workspaces customers pay for,
the jobs that build and wind them down, their domains, the price list, the
signups and the credits, and OneAI's models. It is only on the admin site,
and only for **One Operator**. Nobody on a customer's workspace can open it,
whatever roles they hold there.

## Our own workspace

The admin site is **Four Degree Labs**' own workspace of One (`4dl`): it
uses One as a customer does, OneAI included. It is a workspace on the list,
marked **Ours**, and three things are true of it that are true of no
customer: nobody bills it (no plan, no Stripe, so it never falls overdue);
its OneAI is never refused for credits, however many it has; and what its AI
costs is our cost, not a sale, so AI Usage charges nothing for it (its cost
is **Own Use**) and Home does not count it as a live customer. It was made
once, and the admin site linked to it, by `house.ensure`.

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

## Workspaces

**Workspaces** lists every customer's workspace: its name with its slug
after it (two companies can share a name), its status, plan, owner and
storage against what its plan allows, in red when over. Filter by status,
plan or jurisdiction.

A workspace is read-only. Nothing on it is typed; it is the record of what
happened to it. At the top it says its address, and how soon it falls if it
owes, then its **Plan**, **Storage**, **Credits** left and what it has
**Used This Month** on OneAI. Placement and Site are folded away: open them
when something breaks.

**Where it stands.** A workspace is built, then **Live**. When a payment
fails it is **Payment overdue** and carries on as before for 7 days, then
**Suspended** for 14 (nobody can sign in, nothing is touched), then
**Archived** for 30 (the site is taken down after a backup; the files stay),
then its files are deleted. It falls one rung a night, and the periods are
set in **Settings**. Paying before the files go brings it back: from
overdue at once, from suspended by a job that serves the site again.

**The buttons** move it by hand, one rung at a time, and each asks first:

- **Mark Overdue**, **Suspend**, **Archive** and **Delete Files** send it
  down the next rung now rather than when the clock says. Archiving and
  deleting files cannot be undone.
- **Restore** brings an overdue or suspended workspace back.
- **Refresh** measures its storage again, or asks Cloudflare about its
  domains.
- **Billing**: its **Invoices** in our books, **Give Credits** (goodwill,
  a correction, a trial extended, with a note and an expiry), its **Credit
  Ledger**, and its **AI Usage** by model.

Below the fields are its **Jobs** and **Log**, its **Domains**, and on the
billing side the **Customer** it is in our books and the **Signup** that
paid for it.

The owner is emailed when their workspace is suspended, when it is archived
(with the day it will be deleted) and when it is restored. Being overdue is
told on their own workspace, which still works then.

## Jobs

A **job** is the work that builds a workspace or moves it on the ladder, one
step at a time. There are five kinds:

- **Provision** builds a new workspace: checks the name is free, asks Frappe
  Cloud for the site, waits for it to be built, puts it on our own name,
  tells the site who it is, invites the owner, and marks it live.
- **Suspend**, **Restore**, **Archive** and **Drop** move a workspace down
  or back up the ladder (see Workspaces).

Jobs run by themselves every two minutes. **Jobs** lists the ones not done:
the workspace, the kind, where it is, the step it is on, and when it last
moved. A failed job has its error under its step.

A job is **Waiting to run** when its next step is due, and **Waiting on
Frappe Cloud** while a step waits for somebody else, such as a site being
built. A step that keeps not answering is tried again, less often each time,
and after twelve tries the job **Fails** and the operators are told.

Open a job to see its walk: every step in words, the ones done ticked, the
one it is on marked, and a failed step's error under it. **Resume** runs a
failed job again from the step it stopped on. Every step is safe to run
twice, so this never builds a second site or suspends a workspace twice.

A job that was due and has not run for fifteen minutes is on Home, under
Needs You, with **Run Now**: the scheduler has stopped, or a worker died
holding it. Run Now runs its next step at once.

**The owner of a new workspace** is invited by the job, at its **Inviting the
owner** step: the new site makes whoever paid its first administrator and
emails them a link to choose their password, good for a week. When the job
finishes they are emailed **Workspace Ready**, with its address.

## Price List

**Price List** is everything One sells, and the one OneAdmin screen an
operator writes in. The signup page, a customer's Plan and Credits screen,
the Plan Calculator and Price Check all read it, and each offering is an
Item in our books. Plans come first, then add-ons, then credit packs, each
by price, with what it costs and what it gives in one line.

There are three kinds:

- A **Plan** is what a workspace is on: its price a month (or once), a free
  trial if it has one, and its quotas: storage, database, seats and credits
  a month. Nought means unlimited.
- An **Add-on** adds one thing, in one size, to a plan, and is paid monthly
  with it: 50 GB of storage, 5 seats. Fill in the one thing it adds.
- A **Credit Pack** is bought once, for OneAI credits that do not expire at
  the month's end.

**Changing one** reaches customers in two different ways. The price never
does: Stripe keeps each subscriber on the price they signed up at, and the
next sale makes a new Stripe price. The quotas do, the next time the
customer changes their plan or add-ons, when they are copied from here
again. The top of each offering says how many workspaces have it.

**Disabling one** takes it off the signup page and the customer's choices;
the workspaces already on it keep it. An offering a workspace has cannot be
deleted. **See the Signup Page** in the list's menu opens it as a customer
sees it.

## Price Check

**Price Check** says whether the price list makes sense. For every enabled
offering it shows what it gives, its price, what it costs us a month, its
**Margin** (how many times its cost it sells for) and, for a plan, how much
it **Saves** over the plan below bought as add-ons. Anything that does not
hold comes first: **Wrong** in red, a **Close Call** in orange.

It checks five things:

- every price covers its cost with the **Margin Wanted** (2× unless
  Settings says otherwise);
- each plan up gives at least as much of everything, for more;
- moving up a plan is cheaper than buying the difference as add-ons, or
  nobody moves up;
- the smallest add-on is cheaper than moving up, or nobody buys it;
- a bigger size of the same add-on is no dearer per unit.

What each thing costs us (a workspace, a seat, a GB of storage and of
database, the backups kept, a credit) and the margin wanted are set in
**Settings**; **Costs in Settings** in the report's menu opens them.
**Include Disabled** checks withdrawn offerings too.

You are also told without opening it: saving an offering, or the costs,
shows at once what the price list now gets wrong, and anything Wrong is on
Home, under Needs You, until it is fixed. On the report, OneAI answers **What
should we change?**.

## Plan Calculator

**Plan Calculator** answers what a customer should buy. Say how many
**Seats**, how much **Storage** and **Database** in GB, and how many OneAI
**Credits a Month** they need, and it lists every plan with the add-ons that
bring it up to that, cheapest first: what the plan **Gives**, the add-ons,
what it comes to **A Month**, what it **Costs** us, its **Margin**, and how
much **Dearer** it is than the cheapest. The summary says the needs back and
the cheapest answer. It is the same sum a workspace's own Plan and Credits
screen does when its administrator adds to their plan, so what it says is
what they will be offered. Credit packs are not in it: they are bought once,
not monthly.

For a customer you already have, pick the **Workspace**: the needs fill in
from what it has now (the seats it pays for, the storage and database it
uses, and its credits a month or this month's spend, whichever is more), the
summary says what it **Pays Now**, and the row of its plan says **Their
plan**. Change any need from there to ask "and with ten more people?".

Only an operator of One sees it, and it changes nothing. On the report,
OneAI answers **What should they buy?**, for needs said in words or a
workspace by name.

## Signups

**Signups** are the people who asked for a workspace on the signup page,
before and after they paid. Nobody types one in: the page writes it, and
Stripe's word that the payment went through builds the workspace. Each says
where it stands:

- **Not paid**: they filled in the page and never paid. **At checkout**:
  they are, or were, at Stripe.
- **Paid, not built**: the money arrived and the workspace was not made.
  **Paid, build failed**: making it stopped, and the red line on the
  signup says why.
- **Being built**: its workspace's job is running (the workspace has the
  job). **Built**: the workspace went live.
- **Abandoned**: not paid within seven days, so the name they asked for is
  free for somebody else. If they pay after all, the workspace is still
  built, unless the name was taken in the meantime.

A paid signup with no workspace is the worst state there is, so it is on
Home under Needs You, and **Build Workspace** on it tries again. Look at why
it stopped first: a name taken since, or a Frappe Cloud refusal, will stop it
again. Its **Workspace** is linked once there is one, with **Open
Workspace**; **Open in Stripe** in the menu finds its payment; and our own
lead and deal for it are under Outcome.

Only an operator of One sees signups, and nobody edits them. On one that was
paid and not built, OneAI answers **Why wasn't this built?**.

## Credits

**Credits** is every movement of every workspace's OneAI credits, one row
each, written once and never edited. A workspace's balance is the sum of its
rows; nobody types a balance anywhere.

- A **Grant** adds credits: the plan's monthly credits (they expire at the
  month's end), a credit pack they bought (never expires), or credits an
  operator gave with **Give Credits** on the workspace (with a note, and an
  expiry if one was set).
- A **Spend** is one OneAI call, drawn from the grant that expires soonest.
  It names the **Model** it ran on. A spend beyond what the workspace had is
  owed, and belongs to no grant.
- A **Refund** gives back an over-charge.

The list opens on everything but calls: grants, refunds and credits taken
back. A call's spends, hundreds a day, are one filter away, and **AI Usage** sums them by workspace and model. A grant says what is
left of it and until when; a spend says which grant it came out of.

**Take Back** on credits an operator gave takes back what is left of them,
with a note saying why. It writes a spend of the rest rather than deleting the
grant, so what was already spent stays spent. Credits a plan or a pack gave
cannot be taken back: they were paid for.

When an operator gives credits, the workspace's administrators are told
**Credits Added** with the operator's note and when they expire. Only an
operator of One sees the ledger. On an entry, OneAI answers **Where did the
credits go?**.

## Models

**Models** is every OneAI model the two providers offer, Cloudflare Workers AI
and Google AI Studio. Nobody types one in: each night the list is read from
each provider, and each price from the page the provider publishes. The sync
decides two things on its own, and tells the operators when either touches a
model on sale (**Model Withdrawn**): a model the provider stops listing is
**Withdrawn**, and one whose price can no longer be read comes off sale.

What is yours to decide:

- **Offered**: workspaces may pick it. **Offer** and **Stop offering** are on
  each row.
- **Default For**: what an action needing that runs on when a workspace picked
  nothing. Gemini is the default: the owner's call is that it is better at
  everything OneAI does. When nothing is the default for what an action needs
  (reading a scan, transcribing a recording), it runs on the default for
  something else that can do it, else the cheapest offered model from the
  **Preferred Provider** in Settings (Google). A workspace whose own pick is
  withdrawn falls back the same way rather than failing. An action nothing can
  run is on Home, under Needs You.
- **Markup**: empty uses the default in Settings.
- **Priced by Hand**: for a model whose price page cannot be read. **Needs
  review** says what the page said that could not be read; price it by hand,
  or leave it off sale.

The list opens on what is offered, then priced, then needing review, then
withdrawn. A model's head says its markup, which actions run on it for
workspaces that picked nothing, and how many workspaces called it this month.
**Price a call** makes one real call against a workspace's credits and shows
what it cost: it is charged. OneAI answers **Is this model worth offering?**
on a model and **Which actions have no model?** on the list.

## AI Usage

**AI Usage** says who spent what on OneAI, on what, and whether we made money
on it. Pick the dates (this month unless you say) and cut it **By**
Workspace, Model, Action (which of OneAI's features made the calls: Chat,
Summarise, Read Scans, the intake readings), or a workspace by model or by
action. Each row has its **Calls**, the **Credits** charged, what those are
**Charged** in dollars (at the smallest credit pack's price a credit), what
the provider charged us (**Cost**) and the **Margin** between them; the
summary says the same for the whole period, green when OneAI made money.

Charged is the credits' list price: a plan's monthly credits and packs sold
at a discount earn less. Calls made before the action and the cost were kept
say "Not recorded" and carry a cost worked back from their markup. Only an
operator of One sees it. OneAI answers **Who is spending the most?**.

## Domains

**Domains** lists every name customers have put on their workspaces, such
as `crm.acme.com`: the workspace, whether it is **Working**, **Waiting** or
**Not working**, Cloudflare's reason when it does not work, and which is the
workspace's **Main** address. Every workspace also has the name One gave it
(`acme.t.4dl.app`), which always works and is not listed here.

The customer does all of it from their own workspace, under **Workspace ›
Domains**: they add a name, make one CNAME record in their DNS from it to
the name One gave them, and choose which is the main address, the one links
and mail use. An operator cannot add, remove or make a name main for them:
it is their DNS, and only they can change it.

A name **Waits** until its DNS record is right; Cloudflare keeps checking by
itself and issues its certificate once it is. One asks Cloudflare where each
waiting name has got to every night, and **Check Again** asks now. Open a
domain to see what it needs: the CNAME record it must have, what Cloudflare
says is wrong, and since when it has waited. A name **Not at Cloudflare**
has been lost there; the customer can remove it and add it again.

A name that has waited a day, or stopped working, is on Home under Needs
You, and in the morning's **Domains Waiting**. The customer's
administrators are told on their own site when a name starts or stops
working.

## Log

**Log** is what happened to each workspace, newest first, written by One as
it happens. Nobody types in it. Each row says the workspace, what happened,
in words, who did it, and when:

- **Overdue**, **Suspended**, **Archived**, **Dropped** and **Restored**:
  it reached a rung, and why: a payment failed, its time on the last rung
  ran out, it was paid, it was moved by hand, or what Frappe Cloud did.
- **Plan Changed** and **Add-on Changed**: the customer changed their plan
  from their own workspace, by name. **Plan Change Pending**: Frappe Cloud
  refused to move the site to the plan its database needs; it is asked
  again each night.
- **Over Storage**: it holds more than its plan allows, with both sizes.
  Written when it goes over, and again only when it moves by a gigabyte or
  a month has passed. It is also on Home until it is back under.

**By** is **the customer**, from their own workspace, **an operator** by
name, for a button they pressed or a job they started, or **One**, for the
clock, a payment or a nightly measure. A row written by a job links it.

A row opens its workspace. A workspace's **Activity** shows its own log
beside its changes, and a job lists what it wrote.

## Settings

**Settings** is what OneAdmin runs on, in four tabs:

- **Connections**: the Frappe Cloud account the sites are built on,
  Cloudflare (one token; **Set Up Cloudflare** finds or makes the rest and
  says what it did under Last Setup), the R2 buckets and keys, Stripe's keys,
  and the AI Gateway. Keys are shown as dots and never read back.
- **Money**: Credits per Dollar (what a dollar of provider cost becomes, not
  what a credit sells for, which is the credit packs' price) and the default
  markup, which together price every AI call; and what each thing costs us
  and the least margin, which Price Check and the Plan Calculator use.
- **OneAI**: the Preferred Provider (Google), whose cheapest model runs an
  action nothing is the default for, and the persona said to the model
  before every action.
- **Grace Periods**: the days a workspace spends overdue, suspended and
  archived before the next step.

The line at the top says what is not filled in and what that stops (no
Stripe webhook secret: every payment is refused). **Try the Gateway** makes
one real call. Saving tells the other operators what changed and who changed
it (**Settings Changed**); a key is only said to have changed. OneAI answers
**Is everything set up?**. Only an operator of One sees this page.

## Being told

Operators are told without opening Home:

- **Job Failed**: a job stopped on a step, with the step and the error.
- **Signup Not Built**: somebody paid and their workspace could not be made,
  with why it stopped.
- **New Signup**: somebody paid for a new workspace.
- **Workspace Owing**: a workspace fell overdue, or was suspended.
- **Settings Changed**: another operator saved Settings, and what changed.
- **Model Withdrawn**: the nightly sync took an offered model off sale, and
  what now runs instead.
- **Domains Waiting**: each morning, the domains that have waited a day or
  stopped working.

The person who signed up is mailed **Workspace Delayed** once if it could not
be made, so a payment is never followed by silence. The workspace's owner is
mailed **Workspace Ready** when it is built (see Jobs), and **Workspace Suspended**, **Workspace Archived** and **Workspace
Restored** (see Workspaces).

Each can be turned off or changed under **Settings › Notifications**, and
none of them is offered to anybody who is not an operator.

## Asking OneAI

On Home, OneAI offers **What needs me today?**. It reads the same list Home
shows, with each item's reason, and changes nothing: resuming, building and
checking again are Home's buttons. On a job, **Why did this job fail?**
explains where it stopped and what the error means, and on one waiting, **Why
is this job waiting?** says what it is waiting for. On a domain that does not
work, **Why isn't this domain working?** says what the customer has to change.
On the price list, **How do our plans compare?**, and on a plan or add-on,
**Who has this?**. On Price Check, **What should we change?**, and on Plan
Calculator, **What should they buy?**. On a signup paid and not built,
**Why wasn't this built?**. On a credit entry, **Where did the credits go?**. On AI Usage, **Who is spending
the most?**. On Settings, **Is everything set up?**. On a model, **Is this model worth offering?**, and on the list, **Which actions have no model?**. On a workspace, **How is
this workspace doing?** reads its standing, plan, storage, credits, domains,
last jobs and log, and says whether anything is wrong.

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
  Gemini 2.5 Flash the default. `ai.model_facts` is the catalogue for OneAI.
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
