# The One account

A customer has no account with us today. They have a user on their own
workspace, and nothing above it. This is the plan for the account that sits
above their workspaces, on the admin site, and for the portal pages that grow
out of it.

## What there is now

- **The admin site keeps a `Tenant` per workspace**: its owner's email
  (`owner_email`), its Stripe customer (`stripe_customer`), its plan, quotas,
  domains and credits. Two workspaces owned by the same person are two rows
  that happen to share an email; nothing says they are one person's.
- **The customer never signs in here.** `/start` and `/welcome` are guest
  pages. Everything after the signup is done from inside the workspace:
  Workspace › Plan, Credits, Invoices and Domains call the admin site with the
  workspace's own token (`one/account.py` → `one_admin/proxy.py`). It is the
  workspace talking to us, never a person.
- **So nobody can see their workspaces in one place**, see every invoice at
  once, or start a second workspace while signed in: a second one is a fresh
  guest signup, a second Stripe customer, a second card.

That was right for one customer with one workspace. It stops being right the
moment one person has two, or an accountant pays for three.

## What the account is

A **frappe `User` on the admin site, of type Website User**, whose name is the
person's email. Frappe already has everything this needs: a Website User has no
desk and no roles, signs in at `/login`, and sees only the portal pages we give
it. No doctype of ours stands in for a person.

A workspace belongs to an account through **`Tenant.account`**, a link to that
User. `owner_email` stays, as what the workspace was bought with; `account` is
who holds it now.

What lives on the account is what spans workspaces:

- the list of your workspaces;
- starting another one;
- every invoice across them, and the card they are paid with;
- your name and email.

What stays in the workspace is what belongs to one workspace: its plan, its
add-ons, its credits, its domains, its people. The account links to those
screens; it does not copy them. Two screens for one plan is two screens that
disagree.

## Signing in

**By a link mailed to the address**, which is frappe's own
`login_with_email_link` (System Settings) and `send_login_link` /
`login_via_key` in `frappe/www/login.py`. No password to set or forget, and an
account that only exists because somebody paid is proven by the mailbox it was
paid from.

One guard of ours: the link signs in **Website Users only**. An operator of One
keeps their password and passkey; a mailed link is not a door into the console.
That is a check in a `before_login`-style hook, not a copy of frappe's flow.

## How an account comes to exist

- **At payment**, in `signup.accept`: the signup's email becomes a Website
  User if it is not one already, and the new Tenant's `account` is set to it.
  Nothing is made for a signup that never paid.
- **For workspaces that exist now**, a patch makes a Website User per distinct
  `owner_email` and sets `account` on each Tenant. The house workspace (4dl) is
  ours and gets none.
- **Signed in on `/start`**, the email box is gone: the workspace joins the
  signed-in account, and Stripe checkout is opened for the account's Stripe
  customer, so the card on file is offered and the invoices land together.

## The pages

All on the admin site, all in the portal look (`one-portal`), all reading
through whitelisted calls that answer only for `frappe.session.user`'s own
workspaces:

- **`/account`**: your workspaces, each with its address, plan, standing (live,
  on trial, overdue, suspended) and an **Open** button to its sign-in; **Start
  another**; and a line per workspace that is owed money, with **Pay** going to
  its Plan screen.
- **`/account/invoices`**: every invoice across your workspaces, newest first,
  from `billing.invoices` per Tenant, each with its PDF, and **Update card**
  opening Stripe's billing portal (`stripe.portal`) for the account's customer.
- **`/account/profile`**: name and email. Changing the email re-proves it with
  a link to the new address before it moves.
- **`/start`**, signed in: as now, without the email box, with "Signed in as
  …" and a way out.
- **`/login`** is frappe's, dressed in the portal look.

The "Already have a workspace? Sign in" box on `/start` goes. Its place is a
plain **Sign in** at the top, to `/account`. Somebody who signs in with an
email that holds no workspace sees an empty account and **Start a workspace**.

## When the holder changes

A workspace's owner can leave. Then `account` has to move, or the invoices go
to somebody who no longer works there.

- The workspace says who its owner is: Workspace › Plan gains **Who pays for
  this workspace**, an email, changeable by the workspace's owner, which calls
  the admin site (a new proxy endpoint) to move `Tenant.account` to that
  email's account, making it if needed and mailing a sign-in link.
- The old holder is told, and the workspace drops off their `/account`.

## The nine points, ahead of time

1. **Notifications**: the sign-in link (frappe's, reworded as ours); **Workspace
   Moved to You** and **Workspace Moved Away** when the holder changes; the
   existing Workspace Ready mail gains "It is in your One account" with the
   link. Nothing new to operators.
2. **OneAI**: none on these pages. A guest or a Website User has no credits,
   and every call costs us. Operators see accounts through Workspaces.
3. **Intake**: nothing.
4. **Permissions**: Website Users only, their own Tenants only, every read a
   whitelisted call filtered by the session user; operators unchanged; the
   mailed link refused to anybody who is not a Website User.
5. **Cross-module**: Tenant gains `account`; the Workspaces list and form show
   it with a filter; our own CRM's lead and deal (`sales.py`) attach to the
   account's contact rather than one per signup; Stripe checkout for a second
   workspace reuses the account's customer.
6. **UI**: the portal look, as `/start` now draws it to frappe-ui.
7. **Documented**: OneAdmin's README gains **Your One account**; the Workspaces
   section says what `account` is.
8. **Legal**: the privacy clause says the account keeps your email, name and
   the workspaces you hold, and that signing in is by a mailed link; the Terms
   say the account holder is who we bill and whom we tell.
9. **Built from frappe**: the User, the Website User type, `/login`, the
   email link and the portal routing are frappe's; ours is `Tenant.account`,
   three pages, and the move.

## Stages

Each stage lands whole (code, translations, docs, legal, gates) and is shown to
you before the next.

1. **The account exists.** `Tenant.account`; a Website User made at payment;
   the patch for today's workspaces; sign-in by mailed link, Website Users only.
   Done. Two changes on the way: frappe's `/login` already draws One's mark in
   frappe-ui's look, so it stays frappe's; and signing in landed on frappe's
   `/portal`, which is ERPNext's customer menu, so a first `/account` (who is
   signed in, the workspaces held, Open, Start a workspace) came forward from
   stage 2.
2. **`/account`.** Your workspaces with their standing and Open; Start another;
   what is owed. Done: each says Being built, Live, On trial (free until when),
   Payment overdue, Suspended or Archived, and an owing one says how many days
   are left before the next fall and comes first. **Pay** opens Stripe's
   billing portal for that workspace rather than its Plan screen, since a
   suspended workspace cannot be opened to reach it. Workspace Ready links the
   account.
3. **Signed in on `/start`.** No email box, the workspace joins the account, the
   account's Stripe customer and card are reused. The lookup box goes.
   Done, but for one part. The page says who is signed in and asks no email;
   `signup.start` takes the account's email over anything posted; a guest is
   offered Sign in; the lookup box and `signup.where` are gone; `/welcome`
   links back to the account. **The Stripe customer is not shared.** Every
   invoice event is matched to its workspace by customer (`stripe._ladder`,
   `books`, `billing.invoices` and `billing.invoice` all read
   `Tenant.stripe_customer`), so two workspaces on one customer would have one
   workspace's failed payment suspend the other. Sharing it means matching by
   subscription in those four places, proven against real Stripe events. Until
   then each workspace keeps its own customer; where Link is switched on in our
   Stripe account, Stripe offers the saved card to the same email at checkout. Stage 4 lists invoices per
   workspace, so it does not need the shared customer either.
4. **Invoices and card.** `/account/invoices` across workspaces, and Update
   card through Stripe's portal.
5. **Profile and the move.** `/account/profile`; Who pays for this workspace in
   Workspace › Plan; the two mails.

## Not in this plan

- **One sign-in for the account and its workspaces.** Opening a workspace from
  `/account` still lands on that workspace's own sign-in. Carrying the session
  across would need a one-time token the workspace trusts; it can come after,
  and nothing here stands in its way.
- **More than one person on an account.** An accountant paying for a company
  is an account of their own, made the holder through the move in stage 5.
- **Teams, roles or seats on the account.** People belong to workspaces, and
  stay there.
