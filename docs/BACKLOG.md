# The backlog

What One has decided to build later, or not yet, in one place. Each line says
what it is and why it waits. When one is built, its line goes and the
module's README says what it does.

## Due now

- **Rebuild the demo on a fresh site.** Five checks read dates relative to
  today and fail on a demo built days ago:
  `onecalendar_shows_each_person_their_week`,
  `oneinventory_quotes_ask_compare_and_order_on_one_page`,
  `oneinventory_sent_out_says_what_went_and_what_came_back`,
  `onebook_home_tells_how_the_money_is_doing` and
  `oneinventory_equipment_bought_given_serviced_and_mended`. The twelve steps
  are in `onedesk/one_demo/README.md`. A fresh site needs the database's root
  password.
- **The upstream checkpoint.** The last is `docs/upstream/2026-10-07.md`;
  `tests/guards/test_generated.py` fails after 2026-10-21. Run
  `python3 scripts/upstream.py --fetch --draft`, close each item, then
  `--checkpoint`. On this box `--fetch` was killed for memory on 18 October,
  taking the session with it; fetch the three apps one at a time, or from a
  bigger machine.
- **The asks upstream.** `docs/OVERRIDES.md` lists 62 changes to ask frappe,
  erpnext and hrms for (31, 23 and 7). Each one sent and merged retires an
  override row. Which to send, and in what order, is yours.

- **What the desk pass left.** Of `DESK-PASS.md`'s stages, the dialog kit,
  corners, surfaces and the Canvas walk are done. Left: one bundle for our
  desk code and one stylesheet, with centres and module dialogs loaded when
  opened (`frappe.require`), measured against a baseline of requests, KB and
  time to a usable list, form, home and centre; motion in three durations
  (120, 180, 240ms) with `prefers-reduced-motion` honoured; skeletons in
  place of spinners; a dialog over a dialog dimming the one beneath. The
  plan is `git show cade87a7:docs/DESK-PASS.md`.

## Frappe that One does not reach yet (P3)

Small, or for some customers. Every other doctype frappe ships is reached in
One, runs underneath, or is the platform's; `onedesk/one/atlas.py` says which.

- **SMS** (SMS Settings, SMS Log, ERPNext's SMS Center): notifications and
  campaigns by text message, which some markets expect. Needs a provider and
  its own subprocessor line.
- **Translation**: a workspace's own words for ours, such as calling a Lead a
  Prospect. Needs to stay out of what OneAI and the READMEs say.
- **Prefilled new records** (Document Template): a standard quote, a standard
  job opening.
- **Following a record** (Document Follow): a digest of a record's changes.
  The bell already tells a record's people; this is for anybody else.
- **Session defaults** (Session Default Settings): the values a person works
  under. One has a single company, so little is left of it.
- **What happens after saving** (Success Action).
- **Slack** (Slack Webhook URL): notifications into a channel. Webhooks
  already reach Slack through Zapier or n8n.
- **UTM Campaign and Medium**: OneCRM has Lead Source, not the other two.
- **A form sent to one person** (Web Form Request), with OneForms.
- **LDAP**: enterprise sign-in.

## Decided against for now (Later)

- **Import and Export** (Data Import, Data Export): bringing customers, items,
  employees and balances in from a spreadsheet. The first thing a new
  workspace needs, and its own feature, not a door to frappe's. Renaming many
  records at once waits with it.
- **Signing in with Google or Microsoft** (Social Login Key).
- **Another app acting for a person** (OAuth Client, OAuth Provider Settings,
  OAuth Settings).
- **One reaching into an outside service** (Connected App).

Webhooks are the integration One offers today (Workspace › Webhooks).

## OneStudio

- **An extension behind an API call**, and **a table inside a custom
  collection**. AI-written endpoints and SQL are not going to be built.
- **Custom apps**: a workspace's own app in the dock, with its own icon, rail
  and Home, holding its custom collections (a Fleet app for vans, drivers and
  trips). Needs its own roles, a place in People and in the switcher. Today a
  collection sits in a group of one of One's apps.
- **Hiding a record tab** (Files, Mail, Activity) on one form, as a Record
  Head row. Tabs are declared by modules only (`one/tabs.py`).
- **Server scripts on every workspace**: `server_script_enabled` per Frappe
  Cloud bench group. Opening a code-execution surface is your call.

## The shell

- **The phone answer**: what the dock and the panel become on a phone
  (`frappe.ui.BottomSheet`).
- **A witness for the field grammar**: a test that runs every `depends_on` in
  our Property Setter and Custom Field fixtures through `one/layer.py`
  `plain`.
- **OneAI's badge on a field it wrote.**

## OneProject (P2)

Checked against ERPNext while passing OneProject's Time tab.

- **An Overview dashboard of OneProject's own** (decided 2026-10-27, for
  OneProject's READY walk). ERPNext's Project dashboard has one chart, read
  from Project Summary, which One disables (`one/declutter.py`), so it is
  empty and its rail row was taken off. Ours: a frappe `Dashboard`
  "OneProject" shipped as a fixture in `one_project/`, with number cards for
  open projects, projects past their expected end and hours logged this
  month, a chart of open projects by status, and a chart of completion per
  project from our Project Progress report; Employee Boarding projects left
  out everywhere. It goes on the rail as **Overview** under Project, the
  way the other apps' dashboards do (the `ui` skill, Rules from the walks).

- **Advance recovered by share**: an advance comes off each invoice in full
  until it is used up. Many building contracts take back a share of each
  bill, say 10%. Today the amount is changed by hand on each invoice.
- **Retainers other than monthly**: `retainer.py` bills by calendar month
  only, so a quarterly or yearly retainer is not possible.
- **Work Orders on the project page**: the material a Work Order uses already
  counts in Stock Used, but the page does not list its Work Orders.
- **A template of a whole tree of sub-projects** (ERPNext's Project Template
  is one project).
- **A time rate per customer or per project** (ERPNext prices time by person
  and activity only).
- **The customer on the portal** adding tasks or commenting on their project,
  and **a consultant** given the portal at all.
- **Price escalation** (rare): raising a contract's prices by an index.
  Workable today as a variation or an extra invoice line.
- **Revenue by progress** (rare): recognising revenue by percent complete
  (IFRS 15). ERPNext defers revenue by time only.
- **Deliverables** (postponed 2026-10-09, nothing built): a Deliverable on a
  task, handed to a customer, consultant or teammate who approves it or sends
  it back, with revisions (Rev A, B…) and their files, a
  sent/approved/returned status, Deliverable Templates as named packs, and a
  register across the project. The plan is `git show
  b22b68f:docs/DELIVERABLES.md`, with the five decisions it needs at its end.

## OneBook and OneCRM

- **Reverse charge on a bill from abroad**: ERPNext charges zero, not the
  reverse charge. Tax design for you and an accountant.
- **Customer on hold and the customer overview**, brought in from upstream
  when those pages are next passed.
- **Quotation revisions**: Revise on the project page and on an
  opportunity (upstream).
- **Approvals by condition and priority** (frappe's Workflow Condition), in
  Workspace › Approvals.

## OneInventory and OneHR

- **Sizes in inches, a minimum charge per piece, a perimeter, volume, and
  offcuts kept as stock.**
- **Tax & Benefits in countries without income tax**: whether those screens
  stay in the rail.
- **Gratuity's pay**: OneHR asking which pay counts towards gratuity, so UAE
  rules work without the desk. The demo names Basic Salary meanwhile.
- **Passkeys belong in One**: they are rows of OneHR's Clock Device, and
  sign-in lives in `one_hr/`. A doctype rename with a data patch across the
  clock, the ledger and the reviews.
- **A leave answered over a day marked present**: hrms refuses it. Overriding
  that is a policy call; otherwise upstream.

## OneAdmin and the account

- **The hostname**: `<slug>.t.4dl.app`'s certificate is ordered by Set up
  Cloudflare (`setup.certificate`), which needs Advanced Certificate Manager,
  a paid add-on, enabled on the zone by hand first. Until it is, that step
  says so and no workspace's address has a certificate. If the rewrite fails,
  provisioning could fall back to press's add-domain for the same name.
- **Warm sites**: a pool built ahead of demand and claimed at signup, so a
  paid signup does not wait minutes for `create_site`.
- **A card-less trial**: a workspace with no Stripe customer. Only
  `Offering.trial_days`, card up front, exists.
- **The setup wizard filled in**: company name from the Account Request and
  country from the region.
- **Press reconciled nightly**: press's site list read against our ledger,
  with a `Tenant Event` for each difference.
- **Backups of the workspace's own**: `backup.put_url`, a presigned PUT under
  `backups/<tenant>/<stamp>/`.
- **Promo codes and support sign-in**: neither doctype exists.
- **One sign-in for the account and its workspaces**: Open from `/account`
  still lands on the workspace's own sign-in. Needs a one-time token the
  workspace trusts.
- **More than one person on an account**, and teams or seats on it. An
  accountant paying for a company is an account of their own, made the
  holder through Who Pays.
- **One Stripe customer per account**: invoice events matched by
  subscription in `stripe._ladder`, `books`, `billing.invoices` and
  `billing.invoice`, proven against real Stripe events.
- **The cold copy** of press's offsite backup into our R2 is not possible
  (press's S3, not ours); `note_backup` records its name. Listed so nobody
  plans it again.
- **Plan descriptions**: the words on each plan are yours to write.

## Mail and notifications

- **Mail from outside at the workspace's own address**: needs a Cloudflare
  API key with Zone Settings: Edit.
- **Push on iPhone and iPad**: Apple allows it only for a site added to the
  Home Screen, which needs a web app manifest the desk does not have.
- **Workspace rules that mail outside addresses or attach a print**:
  `rules._hold` keeps them to the bell. Widening it is a decision.
- **Mails still sent from inside upstream jobs**: earned leave not allocated,
  depreciation not posted, reordering failed, and ERPNext's Reposting Error
  Mail beside One's Reposting Failed. Standing in means patching their code.
- **The demo site sends no mail**: it has no outgoing mailbox, so mailed
  notifications fail there. Link it to an admin site or mute mail.

## OneIntake

Checked against `onedesk/one_intake/` on 2026-10-18. The design is
`onedesk/one_ai/reading/README.md`, The design, at the § given.

- **DATEV export** for a business's tax year (§16.6).
- **Keeping periods elsewhere**: countries other than Germany and the
  Emirates, and mail deleted in OneMail (§16.10).
- **Credits used this month** in Reading Settings (§14).
- **An asset from an equipment invoice**, with its warranty in Deadlines
  (§3.1, §16.7).
- **An order confirmation** matched to our Purchase Order, with changed dates
  or prices proposed (§3.1). **A shipping notice** moving the order's
  expected date (§8).
- **A reminder fee** proposed as a line on the invoice's matter (§12.4).
- **A renewed identity document**: the old row marked replaced, the old scan
  kept as an earlier version (§3.3).
- **A supplier's address and IBAN** made into an Address and a Bank Account
  with the Supplier (§3.1).
- **HR officer routing**: an employee's documents go to their HR officer
  (§3.4). **A task for somebody who has left** goes to their manager (§3.4).
- **More steps that tick themselves**: sign, receive goods, check and submit
  a draft, decide a leave, cancel a contract (§3.4).
- **A drafted reply** when a reminder comes for an invoice already paid
  (§3.4).
- **Versions of the same file**: a corrected or signed copy stored as a new
  version (§5.4).
- **The mark on Kanban cards and in the report view** (§4.2).
- **An opportunity from a quote request** (§3.1, §13).
- **"OneAI already drafted this"** on a form (§5.2), and **"May be the same
  as …"** with Merge on a second task (§5.3).
- **One person's records shown on each other**: two applications, a Lead and
  a Contact sharing an identifier (§5.5). **Documents carried over on hire**
  from the Job Applicant to the Employee (§5.5).
- **A direct-debit watch** when the bank line has not come a week after the
  due date (§3.2).
- **Pausing a switch** when the person who turned it on loses the permission
  or leaves (§4.3).
- **A private matter sent to a work address** kept with that person (§4.5).
- **Search by meaning**: Reading Chunk with embeddings, through the gateway
  (§11).
- **Reading more**: GiroCode as data (§2.4), `.msg` files (§2.4), one photo
  of several receipts split (§2.2), rotated pages (§12.1), a PDF password kept
  per sender (§12.1), a link instead of an attachment (§12.1), a huge file
  read in part (§12.1).
- **Junk**: lookalike domains marked red (§8), moving mail in and out of Junk
  learned per sender (§8), bare Contacts made from junk offered for deletion
  (§7).
- **Confidence that learns** per workspace (§10). **The model and prompt
  version** on each reading, and reading again with a better one (§12.6).
- **A backfill estimate** before history is read, with new documents first
  (§12.6).
- **Where it runs**: the workspace's jurisdiction choosing the models, and
  medical and pay documents kept to one model or out (§14).
- **Measured per kind** each month (§15.5).
- **Tax**: a template proposed when reverse charge or small-business VAT is
  unclear (§12.4), proforma invoices told apart (§12.4), a tax payment
  proposed as a draft Journal Entry (§12.2).
- **HR**: a sick note for a child gets the right leave type (§12.5), and
  applicants' and former employees' documents are deleted after retention
  (§12.5).
- **Meeting minutes**: action items become the project's tasks (§13).
- **A time in a letter** converted from the sender's time zone (§6).

## Noticed along the way

- **Profile**: a OneAI button, Check My Profile, and Write It With OneAI
  under Bio. A proof of address Intake reads could offer to update it.
- **Agreements**: whether administrators are told by mail when their
  organisation's agreements change.
- **Audit Log**: telling the administrators of a sudden large export, once a
  workspace asks.
- **Legal still to confirm**: encryption at rest of backups, how long sign-in
  and error records are kept, and inbound mail through Cloudflare Email
  Routing. Facts about Frappe Cloud you confirm; a legal revision follows.
- **The Settings dialog's General and User Permissions tabs** for workspace
  administrators: what each setting does to a workspace, then whether to open
  it.
- **Numbering refuses manual names** for the dozen kinds `one_makes_records`
  declares. Taking them off changes Numbering for those kinds.
- **OneBook › Bank**: erpnext's reconciliation tool shows a banner for its
  newer Banking app, which One does not carry.
- **The monthly statements** that Process Statement Of Accounts mails print
  from ERPNext's own template. One Statement of Account on the Customer is
  ours, printed by hand; giving the mailed ones our look means replacing
  how ERPNext renders them, an override row of its own.
- **Platform records nobody may open**: DocType, Domain, Module Profile,
  Package, Page, User Type, Role Profile, User, Customize Form and One's own
  Record Head, Push Device and AI Touch are reached through a link or our
  screens but open to no role a workspace gives. Opening any is a security
  call, so the atlas counts them in NOBODY.
- **Demo records still missing**: about 45 record types a person reaches
  have none in the demo (`EMPTY` in `tests/guards/test_atlas.py`). Each
  goes in the step of the person whose work it is, with the next demo
  rebuild.

## Upstream's, not ours

Reported or to report; nothing here is patched in One.

- Every PDF logs "Attempted Unauthorized File Access in PDF Generator" for
  Chrome's own `/favicon.ico` request (frappe).
- The Gantt draws a long bar's name at its middle, off screen
  (frappe-gantt).
- A board card's date is not red when late (frappe's board).
- `customer_overview.js` throws `removeChild` on every customer page
  (erpnext).
- The Plant Floor form shows ERPNext's own cards on its Workstations tab;
  One's Plant Floor page replaces it in the rail.
- frappe's list layouts, chart parts and Frappe UI pages: One's own list
  layouts, Home figures and island pages move onto them as they land.
