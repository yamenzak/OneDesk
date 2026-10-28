# OnePortal

The one file for agents, OneAI and us: what OnePortal is made of, its rules,
where each file is, and the decisions that cost something. What people read
is in `docs/`, one page per thing they do, shown in Help and searched by
OneAI's `how_to`; its versions are `docs/changelog/`. What is known to be
wrong and what is planned is `SCRATCHPAD.md` (docs/READY.md, A module's
folder).

OnePortal is what a workspace's customers and suppliers see of it: the
portal they sign in to, a link to one record that needs no account, and the
Portal dialog the workspace manages both from.

## Connections

- **From One**: the Contact, Customer and Supplier records the dialog opens on, and the addresses a customer keeps on the portal.
- **From OneAccount**: the invitation mail and the week-long link to choose a password (one_account/invite.py).
- **From OneCRM**: quotations and sales orders, which a customer accepts or declines on the portal.
- **From OneInventory**: shipments, quote requests, quotes and purchase orders, which a supplier prices on the portal.
- **From OneBook**: sales and purchase invoices, with what is left to pay.
- **From OneProject**: a customer's projects and timesheets (one_project/portal.py draws a project's page).
- **From OneLegal**: the portal's clause in the Data Processing Addendum (legal.py), and Your Data on the portal.
- **To OneMail**: OneAI's replies read what the portal shows the sender (one_mail/theirs.py).

## Under the hood

**OnePortal's rail is two of frappe's lists** (`sidebar/oneportal`):
People, Contact filtered on its Portal column (`Contact.one_portal`, kept by
`gate.py` from where the login stands: on the contact's `validate`, on sign
in, on revoke and restore), and Links, the Portal Link list
(`doctype/portal_link/portal_link_list.js`). Its foot and settings are drawn
the way One's are, by the window (`public/js/one_portal/portal.js`). The
Portal dialog still opens from a submitted record, a customer, a supplier or
a contact, and the portal itself (`frontend/portal`) is outside the workspace.

**Turned off in Apps, the portal is closed** (`gate.py`): `on_login` refuses
a portal login, `before_request` signs out a portal session still open, the
invitation link, `share._live`, `make_link`, `rotate_link`, `mail_link` and
every invite action refuse, and `onedesk.portal.on()` hides every Portal
button. Nothing is deleted, so turning it back on restores everything.
The dialog starts its own tour the first time it opens (`tour.py`).

**One dialog for every place.** `share.access` answers the dialog wherever
it opens: on a record, each contact of its customer or supplier, whether they
sign in and see it, who a link may go to, and its links; on a customer or
supplier, each of its contacts; on a contact, them alone. Each person's
Invite, Invite Again, Revoke Access and Restore call `invite.py` where they
are listed, and the dialog redraws from `access`.

**Who may invite.** A workspace administrator, whoever holds **Invite to the
Portal** (`abilities.py`, a Permission Type on Portal Link, a OnePortal
Manager's), and the manager of the contact's customer (Sales Manager) or
supplier (Purchase Manager) for that party's contacts (`invite.MANAGERS`),
which is how it was before the ability.

**Each module says what it shows.** What a kind of record looks like on the
portal is the module it belongs to's, in its own `portal.py`, as `KINDS`,
which the engine (`portal.py` here, `kinds`) reads through the `one_portal`
hook: One's addresses, OneCRM's quotations and sales orders, OneInventory's
shipments, quote requests, quotes and purchase orders, OneBook's invoices,
OneProject's projects and timesheets. The engine keeps no table of anybody's
records; `test_each_module_says_what_it_shows_on_the_portal` holds it to
that, and to each kind being declared once. `KINDS` is keyed by the kind
of record (its doctype), and what each declares is optional:

| Key | What it says |
| --- | --- |
| `icon` | Its tab's icon, a lucide name (the app's tailwind keeps it). |
| `transaction` | A customer's or supplier's own document: drawn as a row with its number, state and total, listed on Home, and one that can be hidden from some contacts. |
| `party` | The field naming its customer or supplier, which linked records must share. |
| `own_page` | Its record page is its module's own, not the engine's (a quote request). |
| `called` | What the portal calls it, where its doctype's name won't do. |
| `columns` | Its list's three column heads. |
| `said` | Its states in the reader's words: `{state: (tone, word)}`. |
| `badge` | `(doc) -> (tone, word)` or None: a word for its state the record decides (Accepted, Quoted). |
| `figure` | `(doc) -> str`: the figure at a row's end, where its total won't do. |
| `ahead` | `(field, words)`: the date it looks ahead to, and how that is said. |
| `ended` | The states after which nothing is ahead, and its page says the state. |
| `settled` | `(doc) -> bool`: nothing is ahead either (a quotation already accepted). |
| `owed` | A bill: what is left to pay and when, in place of `ahead`. |
| `waiting` | `(states, (n) -> str)`: what Home's tile says of how many wait. |
| `asks` | `((doc) -> bool, label)`: whether it asks something of the reader, under Needs You. |
| `steps` | `(doc) -> [(label, done)]`: where it is on its way. |
| `chain` | `(before, after)`: the records before and after it, shown under it. |
| `ships` | Its page shows the address it ships to. |
| `terms_label` | What its terms are headed, where Terms won't do. |
| `summary` | `(doc) -> dict`: words added to the figure its page leads with. |
| `answer` | `(doc) -> bool`: the reader may answer it on its page. |
| `actions` | `(doc, context) -> [action]`: buttons of its own on its page. |
| `row` | `(doc) -> row`: a row drawn by its module, for a kind that isn't a `transaction`. |
| `add` | `(path, label)`: an Add button on its list. |

What a kind does on the portal stays with its module too: accepting and
declining a quotation is `one_crm/portal.py`, pricing and sending a quote
`one_inventory/portal.py`, a project's page `one_project/portal.py`.

**Patches that ran stay put.** The four portal patches in `one/patches/`
ran under those paths, and frappe's Patch Log keys a patch by its path, so
moving them would run them again (ready.SHARED).

### portal.py

The engine. The portal is a frappe-ui app (frontend/portal), built by frappe-ui's vite
plugin the way HRMS builds its own, and served at `/portal` by
www/portal.py with what it starts with (`boot`: the reader, their tabs, their
language). It draws; what is listed, and for whom, stays erpnext's and
frappe's. Portal Settings lists what each role sees (`get_portal_sidebar_items`),
`rows` lists a kind through frappe's `get_list_data_for_context`, which runs
the kind's own `get_list_context`, `record` (and OneInventory's `rfq`) read erpnext's own page
contexts (`templates/pages/order` and `rfq`), which check the reader may see
the record, and `form` reads a web form through frappe's `get_form_data`. Each
answers with every value as frappe formats it. A record's steps, the figure
it leads with and its linked records (`_steps`, `_summary`, `_related`)
read only the record and the items rows that name it (its kind's `chain`),
and a linked record shows only when it is the same customer's or supplier's
(its kind's `party`).

The Jinja portal this replaces (a page and a row template for each kind,
under the site's navbar) is gone; website_redirects in hooks.py send its
addresses, and erpnext's (/orders/<name>), into the app. ERPNext's project
page is www/projects.py, which does the same: frappe keeps a redirect by its
path alone, so a rule can't tell /projects?project=… from /projects.

A record unticked for some contacts keeps only them, as a list of Contact
names in its `one_portal_hidden` (a hidden custom field on each of the eight
kinds), so a contact added later sees it with nobody having to tick them.
`mine` holds a reader to it: the lists, Home and linked records filter by it,
and `has_website_permission` (hooks.py), beside erpnext's own, refuses the
rest on the record page, erpnext's own pages and a PDF. erpnext lets every
portal user of a customer read all of it, and has no narrower rule to build
on. A quote request has no erpnext rule to sit beside, and adding one would
open it to every website user, so `rfq` checks `mine` itself.

A link (share.py) is a Portal Link: the record, the party, the
contact or address it is for, its last day, and the sha256 of its token,
looked up by that hash; the token itself is a Password field, kept only so
**Copy** can give the link again. `_live` refuses a revoked, expired,
cancelled or unknown token with the same words, so a guess learns nothing.
The link's page is the portal's own (pages/Link.vue draws Record.vue or
Rfq.vue with the token), and its calls are `link_view`, `link_accept`,
`link_decline`, `link_preview`, `link_send` and `link_pdf`, allowed to a
guest, which run the signed-in reader's code (OneCRM's `accept` and
`decline`, OneInventory's `rfq_page`, `priced` and `send`) with the link's
party in place of a signed-in one. A link
is used up by its answer, not by being opened, because mail scanners open
links before people do. The answerer's name and address go on the record as
a comment and on the link as `used_by`.

`ACCOUNT` is the reader's own account, under Account in the sidebar: frappe's
Edit Profile web form, Password on frappe's update_password, One's Your Data
(One's privacy.py) and frappe's Third Party Apps, shown once an app has been
let in. frappe's own pages for these send a portal reader to the app (`reads`).

OneInventory's `quote_preview` builds the same quote `send_quote` saves (`priced`) and
reckons it with erpnext's own `calculate_taxes_and_totals` without saving it,
so the page and the saved quote cannot disagree. A row's discount is
erpnext's `discount_percentage`, off the supplier's rate as its list price,
and the quote ignores the workspace's pricing rules.

`send_quote`: erpnext's own mapper (`create_supplier_quotation`) cannot finish
for a portal user, since filling the quote's defaults reads each Item, which a
supplier may not. So its steps are taken in `send_quote`: the reader is
checked to be one of the supplier's portal users, the request to be one sent
to that supplier, and then, as frappe's web form does for a save it has
already authorized, the quote is made with the session's user switched, owned
by the supplier's user.

### invite.py

frappe's Invite as User makes the login only for somebody who may create
users, and nobody on a workspace may (One's roles.py), so the portal could not
be reached. Here a workspace administrator, or the manager of the contact's
customer (Sales Manager) or supplier (Purchase Manager), invites the contact
from their form: a Website User is made for the contact's address, linked to
the contact (`portal.invited` then makes it a portal user of each customer and
supplier the contact is for), and One's Portal Invitation is mailed with a
link that works for a week (one_account/invite.py). An address that is already
somebody's in the workspace is refused: they sign in to One, not the portal.

Revoke Access turns the login off and signs it out everywhere; Restore Access
turns it back on.

