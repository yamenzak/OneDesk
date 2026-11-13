# OneMail

The one file for agents, OneAI and us: what OneMail is made of, its rules,
where each file is, and the decisions that cost something. What people read
is in `docs/`, one page per thing they do, shown in Help and searched by
OneAI's `how_to`; its versions are `docs/changelog/`. What is known to be
wrong and what is planned is `SCRATCHPAD.md` (docs/READY.md, A module's
folder).

## Connections

- **From One**: Each person added to the workspace gets their own address. The mail window offers the templates set in **Settings › Mail Templates**.
- **From OneAI**: Search also finds words inside attachments that have been read. About rules use what a message is found to be about.
- **To OneAdmin**: Mail from the workspace's addresses is sent through OneAdmin. By default the workspace can send 200 messages an hour and 2,000 a day.
- **To OneCRM**: Mail from a customer, a lead or one of their contacts is linked to their record. Customers, leads, contacts, deals and quotations have a Mail tab. Contacts, leads and customers without a picture get one from Gravatar or their website.
- **To OneHR**: Mail from an employee's address is linked to their record. Employees and job applicants have a Mail tab. An employee without a photo gets the one on their user, or their Gravatar photo.
- **To OneBook**: A message that names an invoice or payment by its number is linked to it. Sales and purchase invoices have a Mail tab.
- **To OneCloud**: Every attachment is saved in OneCloud under Mail, in a folder for each mailbox. A file too large to send from the workspace's address goes as a link that works for 30 days.
- **To OneAI**: In a mailbox OneAI reads, each new message and its attachments go to OneAI.

## Under the hood

### What it is made of

Stage 1, mail arriving at the mail domain, is built. Nothing yet shows it but
the desk's own Communication list.

- **OneAdmin's Set Up Cloudflare** (one_admin/setup.py) deploys the mail
  Worker, points the zone's catch-all at it, and onboards the mail domain
  for sending. Email Routing on the subdomain waits on the key's
  Zone Settings: Edit.
- **The Worker** (deploy/mail/worker.js) refuses what is not the mail domain,
  a workspace or one of its names. It stores the raw message at
  `tenants/<slug>/mail/in/<time>-<id>~<name>.eml` and then posts a signed
  notice. The `~<name>` is the address it came to, which the headers do not
  always say (a Bcc).
- **Admin** keeps each workspace's Worker record in KV under `mail:<slug>`:
  site, secret, bucket, prefix and names. `push_config` makes it with the
  site's `one_mail_secret` and `one_mail_domain`. `proxy.mail_names`
  replaces the names, and only with the workspace's own. `proxy.mail_waiting`
  lists the keys after the last one read.
- **addresses.py** makes the workspace's `Email Account` on first use
  (`one_hosted`, no server, no SMTP login) and a person's on
  `give(user, name)`, which a workspace administrator calls. The part after
  the last dot is the workspace, which `is_workspace_name` checks.
  The workspace's address is `<slug>@m.4dl.app` and a person's
  `<name>.<slug>@m.4dl.app`. Neither has a server, because there is none.
  The mail Worker stores what arrives, `inbound.py` files it, and sending
  goes through admin to Cloudflare (stage 2). The workspace's address sends
  and receives, and a person's only receives. A slug has no dot, so
  `is_workspace_name` is the whole rule, and the Worker and admin apply the
  same one.
- **inbound.py**:
  - `notice` believes a notice only with this workspace's HMAC and a
    timestamp within five minutes, then enqueues the sweep.
  - `sweep`, every minute and after a notice, asks admin for what is new and
    takes each message. A message that fails is logged and passed over, and
    its original is still in R2.
    A missed notice costs a minute, not a message.
  - `take` parses with Frappe's `InboundMail`, files it in INBOX on its
    account's Communication with its thread, references and original key,
    and saves attachments as Files on it. Taking one twice is taking it once.
    `InboundMail` handles charsets, inline images, attachments and the
    reply chain. The message goes on the hosted account its name belongs
    to, its attachments are in R2 like every file, and `one_raw_key` says
    where the original is, so "show original" and a re-parse are always
    possible.
- **threads.py**: the thread is the earliest referenced message we hold,
  otherwise the message's own ID.
Stage 2, sending, is built. Large attachments sent as OneCloud links, and
undo send, come with the composer (stage 5).

- **outbound.py** is Frappe's `override_email_send`. Email Queue builds each
  message and calls it once per recipient. The hook replaces the transport
  for every account, so it picks by the account the queue sends from:
  - an address on the mail domain goes to admin as the finished MIME
    message;
  - on the admin site, its own Sender Email goes to Cloudflare directly
    (one_admin/mailing.py, `send_ours`);
  - any other account goes over its own SMTP, as Frappe would have sent it.
  Queue statuses, retries and the IMAP Sent copy stay Frappe's. A reply
  gains a `References` header on the way: its parent's references, then the
  parent.
  Frappe does not set it, and with it the other side's mail client threads
  a reply as ours does (threads.py).
- **one_admin/mailing.py** is admin's half. It checks that the From is on
  the mail domain and is the workspace's own, that the message fits 5 MiB,
  and that the workspace has sends left this hour and this day (200 and
  2,000 unless site config says otherwise). The counts are atomic cache
  increments; over the limit is `faults.Again`, so the queue retries later.
  It then posts to Cloudflare's `send_raw`, which DKIM-signs for the mail
  domain.
- A hosted account names the mail domain as its SMTP host. It is never
  dialled, but Frappe's queue refuses an outgoing account with no host.
  Sending goes through `override_email_send` (outbound.py). Frappe's queue
  still builds an SMTPServer for the account, so the mail domain stands in
  for its host, and the session it would open is never asked for.
- A Communication sent from here is filed in Sent, in the thread of what it
  answers. A new conversation's thread is its own Message-ID, set once
  Frappe gives it one.
- frappe's `default_outgoing` is One's own sender (one_admin/setup.py), the
  address notifications go out from. Nothing in OneMail moves it. Where a
  workspace has no such sender, as in development, its address is the default
  until one is made.

- Fixed on the way: KV writes were sent as a form, so Cloudflare stored
  `value=…&metadata=…` as the value. The web router's routes had the same
  fault. They are multipart now, as the API takes them.

Stage 3, connected mailboxes, is built and tested against Dovecot. Only the
page to use them is missing (stage 5).

- **connect.py** takes an address and a password and finds the servers: an
  `Email Domain` for the address's domain, then the providers in `KNOWN`,
  then `imap.` and `mail.` of the domain. Each is logged into before it is
  kept. A server that answers and refuses the password stops the guessing,
  since it is the right server. The account is an `Email Account` with
  `one_connected` and `enable_incoming` off, held by whoever connected it
  through a `User Email` row.
  The `Email Domain` is one a workspace administrator set up in Setup
  (`connect.add_domain`, which frappe's own validate dials before saving),
  and the guess uses the standard ports. For a domain with neither,
  `connect.hosted_by` reads its MX record over DNS-over-HTTPS (there is no
  DNS library on the bench), so a Google Workspace or Microsoft 365 company
  is tried at Gmail's or Office 365's servers first. Such accounts still
  need an app password; signing in through Google or Microsoft is not
  built. Somebody whose server is none of these types it
  in, and that is tried the same way. `enable_incoming` stays off because
  Frappe's own pull reads one folder and marks what it reads, while sync.py
  reads every folder and changes nothing. The `User Email` row is how
  Frappe's own inbox holds a mailbox.
- **imap.py** is the protocol: `LIST` lines, a folder's kind from its RFC
  6154 flag or its name in English, German or Arabic, modified UTF-7 folder
  names, `FETCH` responses and `COPYUID`. `Session` is one connection that
  reports MOVE, UIDPLUS and CONDSTORE and does without them where a server
  lacks them.
  What `imaplib` leaves to the caller is here, pure and tested. A `Session`
  is opened for one piece of work and closed.
- **sync.py** runs every minute as one job per account, so two workers never
  read one mailbox. Per folder, a `Mail Folder` keeps UIDVALIDITY, UIDNEXT,
  HIGHESTMODSEQ and the oldest uid read:
  - new mail from UIDNEXT;
  - history newest first, 100 a minute, until the folder is read;
  - flags by CONDSTORE where the server has it, else the newest 500;
  - messages gone from a folder leave it but are kept.
  Everything is matched by Message-ID within the mailbox, so a move made on a
  phone or a renumbered folder ends in one Communication, not two. Folders
  that only repeat others, such as Gmail's All Mail, are listed and not read.
  Nothing is marked read by reading it (`BODY.PEEK`).
  The job's id keeps two from running at once. `LIST` is read every quarter
  of an hour and on first sync, and each folder becomes or stays a
  `Mail Folder`, its kind from its RFC 6154 flag or its name. Gmail's
  Starred and Important repeat others too. A changed UIDVALIDITY means the
  server renumbered the folder, so its uids are forgotten and messages are
  matched again by Message-ID as they are read. History is read `BATCH` at
  a time below the oldest uid read so far, so the last weeks arrive in the
  first minute and years of history over the following ones. Without
  CONDSTORE the newest `WATCHED` messages have their flags read back. When
  the server holds fewer messages than we think, the missing uids are
  found. A message moved on a phone appears in its new folder with the same
  Message-ID and is matched to the one we have, keeping its links to
  records.
- **actions.py** is what a person does: read, star, move, delete, and make,
  rename or delete a folder. A connected mailbox changes on the server first
  and here once the server has taken it. A hosted one has only our rows, and
  gets the six usual folders when it is made. Only a holder or a workspace
  administrator may change a mailbox. Delete moves to Trash. Deleting from
  Trash is for good, but a message linked to a record stays on its timeline.
  Frappe's own links to contacts do not count.
  For a connected mailbox the server is the truth, so a phone reading the
  same mailbox sees a change at once, and the next sync finds nothing to
  undo. A hosted mailbox, on the mail domain, has no server. Read and
  starred belong to the mailbox, not to the person, so two people holding
  sales@ see one inbox, as the server does. Deleting from Trash removes the
  message from the server for good. The Communication goes too, unless it
  is linked to a record. Then it stays on the record's timeline and only
  leaves the mailbox.
- A connected mailbox's sent mail is appended to its Sent folder once per
  message, after the last recipient. Gmail and Outlook are skipped, since
  their SMTP files it there itself.
- **threads.adopt** runs when a message is saved. Replies read before the
  message they answer then join its thread. Folders are read one after
  another, so an answer in the Inbox often arrives before its parent in Sent.
- `one_references` holds Message-IDs bare. Frappe strips anything in angle
  brackets from a stored field as if it were HTML, and did so to every
  reference until this stage.

Stage 4, holders, is built.

- To hold a mailbox is to have a `User Email` row for it, Frappe's own
  notion, which Frappe's Communication permission already reads. Only a
  holder may change anything in a mailbox. Being a workspace administrator
  is not enough, because somebody's own Gmail is theirs.
  Nothing adds a second list, so a message is visible to exactly the people
  who hold its mailbox, and an administrator does not see into somebody's
  own.
- A mailbox is somebody's own or the workspace's (`one_shared`). The
  workspace's are its address on the mail domain and anything an
  administrator connected with `shared`, such as sales@. **holders.py** lets
  an administrator choose who holds those, and only those.
- Everyone who works here gets an address when they are added. The
  administrator adding them may type its name in **Mail Name** on the User;
  otherwise it is made from their first name, or from their login when the
  first name is in another script, with a number when it is taken. The
  address is appended in the User's own `before_save`, so the form the
  administrator is looking at is never stale.
- A workspace administrator picks two defaults on the Defaults page, each
  one of the shared mailboxes (`holders.set_defaults`).
  **Default Incoming** (`workspace()`, the `one_mail_workspace` default) is
  listed first and called Workspace, and it is the Reply-To of every mail
  `notify.mail` sends for the workspace, so an answer to a notification
  lands there. **Default Outgoing** (`sends_from()`, `one_mail_sends_from`)
  is the From the composer starts with, in OneMail and on a record, for
  whoever may send from it. Neither is frappe's `default_outgoing`: until
  October 2026 choosing a connected mailbox made it frappe's default, so
  notifications went out from the customer's own address, and
  `patches/notifications_send_from_one.py` puts One's sender back. The
  address on the mail domain keeps receiving whichever mailbox is chosen.
- `holders.mailboxes` is what the page will list: the reader's mailboxes,
  the workspace's first, each with its folders in the usual order and its
  unread count.

Stage 5, the page, is built. Large attachments sent as links, and saving an
attachment to OneCloud, come with stage 6.

- **page/onemail** is the island `onedesk.onemail` (frontend/src/mail): the
  mailboxes and their folders in the window's nav pane, the conversations
  and the one open in the view, its commands in the command row and its
  search in the address row. A reply and a forward are written by
  public/js/mail_compose.js, which OneAI's reply card uses too. The rail
  entry is the OneMail sidebar.
- **api.py** is what it reads. `conversations` groups a folder's messages
  by thread, newest first, fifty at a time. A search covers the whole
  mailbox. `conversation` returns every message of a thread in the mailbox,
  whatever its folder, with its attachments. `names` turns conversations
  into the messages an action changes: the whole conversation for read and
  starred, and only its messages in the open folder for move and delete.
  A conversation is the messages of one thread (`one_thread`) in one
  mailbox. The list shows one row per conversation that has a message in
  the folder, dated by its newest message there. Opening it shows every
  message whatever its folder, so a reply in Sent is read beside the message
  it answers. Only somebody who holds a mailbox reads it
  (`actions.require`).
- A Sent folder also answers to `Sent`. Mail sent from here is filed there
  until its copy on the server is read and matched.
- **live.py** sends `onemail_change` with the mailbox's name to its holders
  only, once per mailbox after the commit. Sync, the sweep, actions and
  every new message announce it.
  Holders only, so the event says nothing to anyone who may not read that
  mailbox. After the commit, so nobody re-reads a folder before the change
  is in it. Changes are announced where they are made, not from
  Communication hooks, since most of them are `db.set_value`, which runs
  none.
- A message is drawn in a sandboxed frame with no scripts, links opening
  elsewhere and a CSP that loads nothing from outside until "Show pictures".
  Handlers and forms are stripped before it is drawn.
- Writing, replying and forwarding open Frappe's `CommunicationComposer`
  from the open mailbox if it sends, else the workspace's. A reply is
  `in_reply_to` its message and on its record, if it has one.

Stage 6, mail in OneCloud, is built.

- **access.py** is the has_permission hook on Communication. Frappe lets
  anybody with Inbox User open any message by name and only narrows lists,
  so a guessed name opened a message and its files. A message in a mailbox
  now opens for its holders only. Holders get Inbox User with their first
  mailbox, and a patch gives it to those who already held one.
  A message's attachments answer to it (one_cloud/namespace.py `may`), so
  a name guessed or passed on opened those too. Being filed on a record does
  not change who may open it. A link never grants read, or filing a message
  on a customer would publish somebody's mail to everyone who can read the
  customer (linking.py). Holders get Inbox User with their first mailbox in
  `addresses.hold`, and it is what lets them open a message at all.
- **cloud.py** is OneCloud's `@mail`: a folder per mailbox the reader
  holds, derived like a record's folder from the Files on the mailbox's
  Communications, newest first. Communication is left out of Records so a
  message's files are listed once. A file there answers to its message
  through `namespace.may`, which asks access.py.
  Nothing is stored for these folders, so a mailbox's folder is exactly its
  attachments and is seen by exactly its holders. A copy in My Files is the
  reader's own.
- Saving to My Files is OneCloud's own `copy`, a new row on the same
  object. Choosing a OneCloud file in the email window with no record behind
  it hands over the existing File, since sending copies it onto the message.
- `outbound.shrink`: a message from the mail domain over 4 MiB has its
  largest attachments taken out, largest first, until it fits. Each becomes
  a Cloud Link anyone can download for thirty days, named in the plain and
  HTML text. The links are made once per message however many recipients
  it has. A file that cannot be found stays attached.

Stage 7, faces and logos, is built. Both are optional services (`legal.py`
`service()`, one_legal/services.py), off until an administrator turns them
on in TrustCenter: `fetch` asks through `services.call`, and `lookup` queues
only what a service that is on would answer.

- **faces.py** asks Gravatar for a person, by the SHA-256 of their address
  with `d=404`, and Google's faviconV2 for an organisation, by its domain
  with the fallback options that make "no logo" a 404. Both are fetched by
  the server in a background job, once. The answer is a `Face` row, keyed by
  address or domain, and the picture a public File in Company › Logos.
  Fetching on the server, never in anybody's browser, means a sender learns
  nothing when their message is opened. Google and Gravatar are asked once
  per address or domain rather than every time a face is drawn, and a
  tenant's pictures are theirs, in their own storage. Nothing is fetched
  while somebody waits.
- A face not found is looked for again after thirty days (daily job). An
  unreachable source is not taken to mean "has none".
- Mail providers' domains (gmail.com and the like) and our own mail domain
  never give a sender a logo, since the provider is not who wrote.
- `dress_later` runs on Contact, Lead, User, Employee, Customer, Supplier,
  Manufacturer, Company and Bank. A record
  without a picture is dressed in the background from both services, in the
  order that fits it (`sources`), stopping at the first picture:
  - a contact or lead: their face, then their company's logo by the domain
    of their address, then by their website;
  - a customer or supplier: its website's logo, then its address's domain
    (its own, or its primary contact's), then a face registered to the
    address itself, since some register a logo against info@;
  - a user or employee: the photo on their other record first (a User's
    Employee, an Employee's User), then their face only, never a logo, since
    their address's domain is our own; Administrator and Guest are nobody.
    A photo put on either record goes to the other when it has none;
  - a manufacturer or the company: as a customer, by its website; a
    company dressed redraws the letter heads drawn from it;
  - a bank: its website's logo only.
  Bank gains `one_logo`, set as its image field, since ERPNext's Bank has no
  picture. Patches run `dress_all` once in the background for records that
  existed before (`dress_existing`, then `dress_people_and_company` for the
  four added later); a migrate does not wait on Gravatar or Google.
- `lookup` is what the page asks: the contact's picture, else the person's
  face, else the organisation's logo. Addresses never looked for are looked
  for in the background and appear on the next draw.

Stage 8, mail on records, is built, without AI. What a model could add (a
message that names nothing, a statement that names eleven invoices) waits
for OneAI's mail lane.

- **linking.py** writes Frappe's own `timeline_links`, with how each was
  made in `one_linked_by` on Communication Link: `contact` (Frappe's own,
  unmarked), `address` (Employee and Lead by address, which contacts do
  not reach), `thread` (a reply takes its conversation's records), `text`
  and `manual`. The first record that is not a contact also becomes the
  message's reference, which Frappe's reply matching reads.
  So a message shows on several records at once. Each row says how it was
  made, since a link nobody can explain is one nobody will trust. A
  `contact` link comes from a Contact with the address and whatever that
  contact is linked to. `manual` is somebody filing it, or sending it from
  the record.
- `text` reads the subject and the new part of the message, never the
  quoted history, for words that start with a naming-series prefix this
  site issues and end in a number. It keeps only those that exist, at most
  ten.
  The quoted history of a reply is not read, since its names were found
  when those messages arrived.
- It runs from `inbound.Arrival.process`, after Frappe has finished. Frappe
  saves a new message a second time after inserting it, which rewrote links
  made in an after_insert hook.
- **A link never grants read.** access.py opens a message to its mailbox's
  holders only. Frappe's form timeline lists every message linked to a
  record to whoever may read the record, so `getdoc`, `get_docinfo` and
  `get_communications` are wrapped with `override_whitelisted_methods` and
  narrowed to what the reader may open. Tested: a sales user who holds no
  mailbox sees none of the customer's mail; Frappe alone showed all three.
  A record's Mail tab and timeline list only the messages the reader may
  open (`visible`).
- **record_mail.js** draws the Mail tab beside Files on the records
  `linking.TABS` names; `record_tabs.js` adds it to the layout, not to any
  doctype, as it adds every record tab (one/tabs.py).

Stage 9, rules, out-of-office and bounces, is built.

- **rules.py** runs from `Arrival.process` for each message filed, on both
  kinds of mailbox. `Arrival.fresh` says whether a message is new. A first
  read and history read in the background are not, so connecting a mailbox
  does not re-sort or answer years of mail.
- A rule with an **About** is not run on arrival: `rules_of(by_meaning=True)`
  hands its topics to Intake's first look (`one_ai/reading/understand.py`), the
  one model call every new message already has where OneAI reads, which
  answers which topics the message is about; `by_meaning` runs those rules
  on it if it is still in the Inbox. A rule that moved it on arrival wins.
- `ai.suggest_mail_rule` is the card; `ai.make_rule`, run by `ai_setup.apply`
  as whoever approved it, makes the folder, switches Intake on and makes the
  rule, all behind `actions.require`.
- `Mail Rule` is a mailbox's, and is seen and changed by its holders only
  (a has_permission hook and a query condition). It matches all or any of
  from, to or cc, subject and attachments, then moves, marks read and stars
  through actions.py, on the server for a connected mailbox. `stop` ends
  the rules for that message. A rule acts for its mailbox while
  `frappe.flags.one_mail_rules` is set, which `actions.require` lets
  through; nothing else sets it.
  On a connected mailbox a rule acts on the server, so a phone sees the
  message where the rule put it.
- Away is three fields on Email Account (`one_away`, `one_away_until`,
  `one_away_message`) set from the page. Each sender is answered once in
  four days (a cache key), with `Auto-Submitted: auto-replied` and the
  message's Message-ID as In-Reply-To. Machines are recognised by
  Auto-Submitted, Precedence, List-Id or List-Unsubscribe, X-Autoreply, and
  no-reply, mailer-daemon and postmaster senders. The reply goes by
  `outbound.deliver`, the transport `send` now shares, so a person's
  address on the mail domain can answer too.
  The reply is from the mailbox itself, while its holder is away, and
  nothing that is itself automatic gets one: mailing lists, bulk mail,
  other auto-replies, bounces and no-reply senders.
- A delivery report (multipart/report, delivery-status) with a failed 5.x.x
  recipient puts that address on Frappe's Email Unsubscribe with
  `global_unsubscribe`, which Frappe's queue already leaves out, and says
  why in `one_bounce`. The message it bounced is marked Bounced. A 4.x.x
  delay is left alone. Mail sent from the mail domain bounces to
  Cloudflare, not to us, so those bounces are not seen yet.

Read against the old OneMail before it was deleted, three things came
across:
- **The address signs, not the writer.** Frappe signs a Communication on
  save with the sender's own User signature or the default outgoing
  account's, after the composer has closed, so a reply from sales@ went out
  signed by somebody else and nobody saw it. `file_sent` sets
  `skip_add_signature`, and mail_compose.js makes the composer show the
  sending address's own signature (`holders.signature_for`, since Email
  Account is not readable to its holders) under the editor, where it can be
  seen and left off, and put it in as the email is sent.
- **Search operators** (`api.operators`), each narrowing the search further.
  The body is still a LIKE: there is no full-text index behind it.
- **Undo.** `move` and `delete` answer where each message was, and
  `put_back` moves them there again. A connected server that did not say a
  moved message's new uid (no UIDPLUS) has it found by Message-ID.
Left behind on purpose: per-person read state on a shared address (one read
state per mailbox was decided); sending as a customer's own domain from the
mail domain (their own server does that, connected); complaints and
soft-bounce backoff (no feedback loop reaches us); formal letters
(Correspondence), which are OneWriter's rather than mail's; and the AI lane.

Stage 10, drafts and the team inbox, is built (November 2026).

- **drafts.py** and `Mail Draft`: frappe's composer keeps a draft only in the
  browser (localforage, and only for a form). mail_compose.js saves one to the
  server 1.5 s after a change, from any mailbox the writer holds
  (`_account` by the From address), and frappe's `clear_cache`, which it calls
  after sending and on Discard, throws it away. A draft is its writer's alone
  (`has_permission`). The Drafts folder lists the reader's drafts before the
  server's; a conversation returns its reply draft. A connected mailbox's
  draft is also kept in the server's Drafts (`to_server`, a job a moment
  after the last change): one Message-ID for its life, the copy before it
  expunged by that Message-ID and the new one appended with \Draft, and
  `off_server` takes it out once sent or discarded. Its copy synced back is
  left out of the Drafts list (`mirrored`). Send later is frappe's Schedule email
  (Email Queue `send_after`); `scheduled` reads the queue and `unschedule`
  empties it and makes the message a draft again.
- **team.py** and `Mail Conversation`: one row per conversation, made the
  first time somebody assigns, notes, finishes, snoozes or asks for a
  reminder. Assignment is frappe's Assign To on the row, so the person is told
  and it is among their ToDos; Done closes it; notes are frappe's comments on
  the row. `conversations` joins the row for the list's Open, Mine, Unassigned
  and Done and keeps snoozed ones out of the Inbox. `arrived` (Communication
  after_insert) opens a Done conversation again on a message from outside and
  ends its snooze and reminder; `due`, every five minutes, brings snoozed ones
  back unread and tells reminders through tell.no_reply. "Is writing a reply"
  is a realtime event to the mailbox's other holders, `onemail_replying`. The
  row's form sends its reader to OneMail (mail_conversation.js).
- **sender.py**: the party an address belongs to (a contact's links through
  frappe's `get_contact_name`, then the party's own address) and what of
  theirs is open, by `frappe.get_list`, so only what the reader may open.
- **Create** (MailConversation.vue) is One's create dialog with the mail carried
  over, then `linking.file` on the new record.
- **linking.py** reads a record type's own naming (`own_pattern`) as well as
  its naming series, so Task, Job Offer, Interview and quality's `format:`
  names are found by their numbers, and links customers, suppliers and
  applicants by their own address.

### Where Help's claims are kept

The pages in `docs/` name no code, so what each claim rests on is here. Their
pictures sit beside them, one folder per page (`docs/<page>/`), and are
cropped from the demo with Layla signed in.

- **Answering from their records** (rules-and-out-of-office): the portal's
  view is `theirs.py`; the two tools the run gets are `their_record` and
  `their_records`; the sender check is `theirs.verified`, which reads only
  the topmost `Authentication-Results`.
- **Who connects what** (connecting-a-mailbox, who-can-do-what):
  `connect.connect_for` for an administrator connecting someone's
  organization mailbox, `holders.may` for who sees into a mailbox.
- **Rules before OneAI** (rules-and-out-of-office): a record a rule made is
  linked to it as `rule`; `act._ruled` and `gate.made_by_rule` keep
  OneAI from making a second. Out of office covering is
  `rules.on_leave` per message, `rules.covered` as a leave is decided and
  `rules.cover` daily.
- **OneAI's jobs** (asking-oneai): the list is `gate.JOBS`; every OneAI write
  goes through `act.apply`, which asks `gate.does` for the job
  `gate.job_of` names, and the e-invoice submit asks the same for Bills.
  **Send** per address (settings) is `holders.set_sends`; the company's
  domains (your-addresses) are `addresses.company_domains`.
- **Signatures** (reading-and-writing): drawn by `signatures.py`, added below
  the editor by `mail_compose.js`, logo embedded by
  `signatures.inline_logo` in the queued copy.

### Research and decisions

**What was studied.** The old OneApp mail backend and its inbound Worker
(logic only, not its screens). Frappe's own email stack in this bench.
ERPNext's and HRMS's parties. Cloudflare's Email Service as of September 2026.
Google's favicon service and Gravatar.

**Frappe has most of the parts and none of the whole.**
- *What it has.* `Email Account` holds an IMAP/SMTP login, encrypted, with
  OAuth. `Communication` is the message, and every form's timeline already
  shows it. `User Email` says who may use an account, and Communication's
  permission query honours it. `frappe.email.receive.Email` parses MIME, with
  charsets, inline images and attachments. `override_email_send` is a hook
  that replaces the transport, and Email Queue already appends sent mail to
  an IMAP Sent folder.
- *What it lacks.* It pulls at most 100 messages a run. It tracks the highest
  UID across the whole account rather than per folder. It never writes read,
  flagged, moved or deleted back to the server: `Email Flag Queue` is
  written and nothing reads it, and `update_flag` has no callers. It fills
  no folder on a Communication. It sets no `References` header. Its threads
  are a chain of Communication names, not Message-IDs.
- *So:* keep its model — Email Account, Communication, User Email, File —
  and write the sync, the threading and the transport ourselves.

**The old OneMail is a list of features, not code to keep.**
- *Worth keeping as features:* addresses per workspace and per person, and
  shared addresses with holders. Picking the From address by context. Undo
  send. Rules and out-of-office. Suppression of addresses that bounce. Stars.
  Linking mail to records. Faces from Gravatar and the favicon service.
  Templates and signatures per address.
- *Why not the code:* its inbound path never worked end to end. A function
  was defined twice, the tenant stayed on the handler's key, and the
  Worker's signing serialiser emptied every attachment. Threads were keyed on
  the subject, so two unrelated "Invoice" threads merged, and the record link
  of one was copied onto the other. Access was a substring test, so
  `ap@x.com` could read `cheap@x.com`'s mail. Search took the site's newest
  2,000 matches before narrowing to the reader, so older mail vanished from
  their results. It sent through Cloudflare's SMTP, which refuses any domain
  that has not been onboarded, so its "send from your own domain" could not
  have worked.

**Cloudflare, as it stands.**
- *Email Routing* (inbound) is free, takes up to 25 MiB, works on a
  subdomain, and hands each message to a Worker's `email()` handler.
  Whether a catch-all on a *subdomain* is possible is unconfirmed: the API
  has one catch-all per zone. The way to be sure of it is the zone's
  catch-all pointed at the Worker, which answers only for `m.4dl.app` and
  refuses everything else.
- *Email Sending* (outbound) is a public beta. It needs Workers Paid:
  3,000 a month included, then $0.35 per thousand. Messages are 5 MiB at
  most, attachments included. There are 50 recipients per message, and it
  is for transactional mail only. It can be called over REST from any
  server: `accounts/{id}/email/sending/send_raw` takes a finished MIME
  message, which Frappe already builds. The From must be on a domain
  onboarded for sending, and onboarding adds `cf-bounce.` SPF, DKIM and
  DMARC records.
- *Cloudflare has no mailbox.* No IMAP and no store. For the addresses on
  `m.4dl.app`, the workspace is the mail server's mailbox.

**Decisions.**

1. *One domain, two shapes of address.*
   - The workspace is `<slug>@m.4dl.app`, its default for sending and
     receiving.
   - A person is `<name>.<slug>@m.4dl.app`, receive only.
   - One catch-all on `m.4dl.app` goes to one Worker. It reads the part
     after the last dot of the local part as the slug. Slugs cannot contain
     a dot, which makes this unambiguous, unlike the old `t-` prefix.
2. *Two kinds of mailbox behind one screen.*
   - A *hosted* mailbox is an `m.4dl.app` address. Its mail and folders live
     in the workspace, because there is nowhere else for them to be.
   - A *connected* mailbox is any IMAP account: the workspace's replacement
     default, a shared address like `sales@theircompany.com`, or a person's
     own. Its server is the truth. Folders, read, starred, moved and deleted
     are written back and read back, so a phone on the same account agrees
     with OneMail.
   - Both are an `Email Account`. `one_hosted` says which kind.
3. *State belongs to the mailbox, not the reader.* Read, starred and folder
   are one per message, as they are on an IMAP server and in any shared
   mailbox in Outlook or Gmail. The old code had these per document too, but
   by accident; this is the IMAP-consistent choice, made on purpose. What
   stays per person is what IMAP has no place for: drafts and personal
   settings.
4. *The Worker stores first, then tells.*
   - It writes the raw message to R2 under the tenant's own prefix, where
     it counts towards the tenant's storage.
   - It then posts a small signed notice to the site. The HMAC covers the
     notice's exact bytes, so there is no serialiser to get wrong.
   - The site fetches the raw message through admin's signed URL and parses
     it with Frappe's parser.
   - A site that is down, or mid-migrate, loses nothing: a sweep picks up
     notices that never arrived.
   - Each tenant's secret sits in the same KV record as its route. The
     site's copy is written by `push_config`.
5. *Sending picks its transport by From.*
   - An `m.4dl.app` From goes through admin to Cloudflare's `send_raw`.
     Admin holds the token, counts the sends and applies the limits. The
     tenant holds no Cloudflare credential, as for storage.
   - Any other From goes over that account's own SMTP.
   - Both go through `override_email_send`, so Email Queue, retries and the
     IMAP Sent copy stay Frappe's.
   - A message over Cloudflare's 5 MiB sends its large attachments as
     OneCloud links instead.
6. *Threads are Message-IDs.*
   - A thread is its root's Message-ID, found through `In-Reply-To` and
     `References`.
   - Mail with neither starts its own thread. Subject is never a key.
   - Everything sent carries `In-Reply-To` and `References`, so the other
     side's client threads it too.
7. *Attachments are Files on the Communication, as Frappe keeps them.*
   Holders of the mailbox may open them. OneCloud gains a **Mail** root, as
   it gained Requests: a folder per mailbox the reader holds, and a folder
   per month in each. It is a view, not a copy, so saving a file from an
   email into My Files is OneCloud's ordinary copy, with no bytes moved.
8. *Faces and logos are a service for every party, not a mail feature.*
   - Candidates: Contact, Customer, Supplier, Lead, Company, Employee and
     Bank. Bank has no image field, so it gets a custom one.
   - Order of lookup: Gravatar by SHA-256 with `d=404` for a person's
     address. The favicon service for the party's website, or for the
     domain of an email address that is not a free-mail provider's.
   - "No icon" is a 404 from both services, never the grey globe.
   - The image is fetched once, in the background, and stored as a File in
     Company › Logos. The record's image field points at it.

**What is not in the first version:**
- IMAP IDLE. Workers poll each connected mailbox every minute; IDLE needs a
  long-lived process a Frappe worker is not.
- OAuth sign-in for Gmail and Microsoft. App passwords work; OAuth needs
  our own Google and Microsoft app registrations, which is paperwork before
  it is code.
- Marketing and bulk mail. Cloudflare forbids it.
- POP3.

### ai.py

Everything is read as the reader, and only from a mailbox they hold
(`actions.require`), so the rule that decides who may open a message
decides what OneAI may read of it. A conversation's text goes to the model
only when the reader asks about it, and nothing of it is kept but the
answer.

A reply is never sent from here. `draft_reply` writes a card. Approving it
opens frappe's own email window with the reply written in, the recipients
and the quoted conversation filled as Reply fills them, and the person
reads it, changes it and sends it (mail_compose.js, `onedesk.mail.reply_to`).

### room.py

An attachment is stored in R2 like any file (one_cloud/store.py), and a
full workspace refuses it (`store.NoRoom`). Frappe's receiver does not
expect that, so before this the whole message failed, the sweep or the sync
moved past it, and it was never in OneMail. A message is text in the
database, which has its own limit. Only its attachments need the room.

So `Arrival` saves attachments one at a time (inbound.py), and one refused
for room is written down on its message (`one_unsaved`) instead of failing
it. The reading pane shows it as not saved. `again`, every hour, takes each
such message's original again, from R2 for an address on the mail domain
or from the server for a connected mailbox, and saves what now fits. The
administrators and the mailbox's holders are told once a day at most while
attachments are being refused (tell.py).
