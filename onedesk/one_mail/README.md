# OneMail

Written by hand. All nine stages are built: addresses on the mail domain,
sending, connected mailboxes, holders, the page, mail in OneCloud, faces and
logos, mail on records, and rules, out-of-office and bounces. What waits is
the AI lane and real inbound mail from outside, which needs the Cloudflare
key's Zone Settings: Edit. The part above
**Under the hood** is the manual; below it are the decisions and the stages
still to come.

OneMail is where a company's email lives. Every workspace has an address of
its own, and every person in it has one too. The company's existing mailboxes
— its Gmail, its Outlook, its hosting provider's mail — can be connected as
well, with their folders, and worked on here instead. Attachments are in
OneCloud and senders show with their faces and logos. A message can belong to
a customer, a supplier or an employee as well as to a mailbox.

## Your addresses

Every workspace gets `acme@m.4dl.app`. It is where the workspace's mail comes
in and goes out from, until a workspace administrator connects the company's
own mailbox to use instead. Every person gets `name.acme@m.4dl.app` when
they are added, with the name whoever adds them chooses, or their first name.
It only receives: it is where a supplier, a site or a newsletter can reach
them without their private address.

## Connecting a mailbox

Any mailbox that speaks IMAP can be connected: Gmail and Outlook with an app
password, and any hosting provider's. Its folders come with it, including
Sent, Junk, Drafts and those made elsewhere. What you do here happens there:
reading, starring, moving, deleting and making folders. A phone on the same
account agrees with OneMail.

A workspace administrator can connect the company's mailbox and make it the
workspace's own, for receiving, sending or both. They can also connect shared
addresses such as `sales@theircompany.com` and choose who holds each. Anyone
can connect their own, and nobody else sees into it, administrators included.

## Reading and writing

**Mail** in the rail opens every mailbox you hold: the workspace's first,
then the shared ones, then your own, each with its folders. A folder lists
its conversations, newest first. Opening one shows all of its messages,
your replies from Sent included, with older ones folded to a line. Pictures
from elsewhere are not shown until you ask, because loading one tells the
sender you opened the message.

Select several with their boxes, or with Shift and Ctrl, to mark them read,
star, move, archive or delete them together. Deleting from Trash is for good.
The keys are the usual ones: `j` and `k` to move, `e` to archive, `#` to
delete, `r`, `a` and `f` to reply, reply to all and forward, `s` to star,
`u` to mark unread, `c` to write and `/` to search.

Writing uses the desk's own email window, so a message can be scheduled,
undone for a few seconds after sending, and filed on a record.

## Rules and being away

**Rules** above a mailbox's list sort new mail as it arrives in the Inbox:
move it to a folder, mark it read or star it, by who it is from or to, its
subject, or whether it has attachments. On a connected mailbox the server
does it too, so your phone agrees. Rules never touch mail that was already
there when the mailbox was connected.

**Out of office** answers each sender once in four days while you are away,
until the date you set. Mailing lists, newsletters, other auto-replies and
no-reply senders get nothing.

When mail to an address bounces for good, the address is not written to
again, and the message that bounced says so.

## Mail on records

A message is filed on the records it is about as it arrives: the customer or
supplier of the contact who wrote, an employee or lead with the address, the
records its conversation is already on, and any invoice, order or other
document it names by its number. The reading pane shows those records, each
with a cross to take the message off, and the link button files it on
another. A customer, supplier, lead, employee or document has a **Mail** tab
beside Files with its conversations and a Write button.

Filing a message on a record never shows it to anybody new. The Mail tab and
the record's activity list only the messages you could already open.

## Attachments and faces

Every attachment is in OneCloud, under **Mail**, in a folder per mailbox,
seen only by the people who hold it. The paperclip above a mailbox's
conversations opens that folder. An attachment's folder button saves a copy
to My Files, and a file from OneCloud can be attached when writing. A file
too large to send from the workspace's address goes as a link that works
for thirty days.
People who write to you show with their contact picture, or their photo from
Gravatar, or their organisation's logo. A contact, customer, supplier or bank
without a picture gets one the same way. Every picture is fetched once by
the workspace, never by your browser, and kept in Company › Logos, so
opening a message tells nobody anything.

## Under the hood

For the people who build OneMail. OneAI does not read past this heading.

### What it is made of

Stage 1, mail arriving at the mail domain, is built. Nothing yet shows it but
the desk's own Communication list.

- **One Admin's Set Up Cloudflare** (one_admin/setup.py) deploys the mail
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
- **inbound.py**:
  - `notice` believes a notice only with this workspace's HMAC and a
    timestamp within five minutes, then enqueues the sweep.
  - `sweep`, every minute and after a notice, asks admin for what is new and
    takes each message. A message that fails is logged and passed over, and
    its original is still in R2.
  - `take` parses with Frappe's `InboundMail`, files it in INBOX on its
    account's Communication with its thread, references and original key,
    and saves attachments as Files on it. Taking one twice is taking it once.
- **threads.py**: the thread is the earliest referenced message we hold,
  otherwise the message's own ID.
Stage 2, sending, is built. Large attachments sent as OneCloud links, and
undo send, come with the composer (stage 5).

- **outbound.py** is Frappe's `override_email_send`. Email Queue builds each
  message and calls it once per recipient. The hook replaces the transport
  for every account, so it picks by the account the queue sends from:
  - an address on the mail domain goes to admin as the finished MIME
    message;
  - any other account goes over its own SMTP, as Frappe would have sent it.
  Queue statuses, retries and the IMAP Sent copy stay Frappe's. A reply
  gains a `References` header on the way: its parent's references, then the
  parent.
- **one_admin/mailing.py** is admin's half. It checks that the From is on
  the mail domain and is the workspace's own, that the message fits 5 MiB,
  and that the workspace has sends left this hour and this day (200 and
  2,000 unless site config says otherwise). The counts are atomic cache
  increments; over the limit is `faults.Again`, so the queue retries later.
  It then posts to Cloudflare's `send_raw`, which DKIM-signs for the mail
  domain.
- A hosted account names the mail domain as its SMTP host. It is never
  dialled, but Frappe's queue refuses an outgoing account with no host.
- A Communication sent from here is filed in Sent, in the thread of what it
  answers. A new conversation's thread is its own Message-ID, set once
  Frappe gives it one.
- The workspace's address is the default outgoing account unless another
  already is.

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
- **imap.py** is the protocol: `LIST` lines, a folder's kind from its RFC
  6154 flag or its name in English, German or Arabic, modified UTF-7 folder
  names, `FETCH` responses and `COPYUID`. `Session` is one connection that
  reports MOVE, UIDPLUS and CONDSTORE and does without them where a server
  lacks them.
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
- **actions.py** is what a person does: read, star, move, delete, and make,
  rename or delete a folder. A connected mailbox changes on the server first
  and here once the server has taken it. A hosted one has only our rows, and
  gets the six usual folders when it is made. Only a holder or a workspace
  administrator may change a mailbox. Delete moves to Trash. Deleting from
  Trash is for good, but a message linked to a record stays on its timeline.
  Frappe's own links to contacts do not count.
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
- `holders.replace` makes a connected mailbox of the workspace's its
  mailbox, and, if it sends, its default outgoing account. The address on the
  mail domain keeps receiving, so nothing sent to it is lost. `restore` puts
  it back.
- `holders.mailboxes` is what the page will list: the reader's mailboxes,
  the workspace's first, each with its folders in the usual order and its
  unread count.

Stage 5, the page, is built. Large attachments sent as links, and saving an
attachment to OneCloud, come with stage 6.

- **page/onemail** loads **public/js/onemail.js** and **onemail.css** the
  first time it opens, as OneCloud's page does. The rail entry is the
  OneMail sidebar.
- **api.py** is what it reads. `conversations` groups a folder's messages
  by thread, newest first, fifty at a time. A search covers the whole
  mailbox. `conversation` returns every message of a thread in the mailbox,
  whatever its folder, with its attachments. `names` turns conversations
  into the messages an action changes: the whole conversation for read and
  starred, and only its messages in the open folder for move and delete.
- A Sent folder also answers to `Sent`. Mail sent from here is filed there
  until its copy on the server is read and matched.
- **live.py** sends `onemail_change` with the mailbox's name to its holders
  only, once per mailbox after the commit. Sync, the sweep, actions and
  every new message announce it.
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
  now opens for its holders, and for whoever may read the record it is
  filed on. Holders get Inbox User with their first mailbox, and a patch
  gives it to those who already held one.
- **cloud.py** is OneCloud's `@mail`: a folder per mailbox the reader
  holds, derived like a record's folder from the Files on the mailbox's
  Communications, newest first. Communication is left out of Records so a
  message's files are listed once. A file there answers to its message
  through `namespace.may`, which asks access.py.
- Saving to My Files is OneCloud's own `copy`, a new row on the same
  object. Choosing a OneCloud file in the email window with no record behind
  it hands over the existing File, since sending copies it onto the message.
- `outbound.shrink`: a message from the mail domain over 4 MiB has its
  largest attachments taken out, largest first, until it fits. Each becomes
  a Cloud Link anyone can download for thirty days, named in the plain and
  HTML text. The links are made once per message however many recipients
  it has. A file that cannot be found stays attached.

Stage 7, faces and logos, is built.

- **faces.py** asks Gravatar for a person, by the SHA-256 of their address
  with `d=404`, and Google's faviconV2 for an organisation, by its domain
  with the fallback options that make "no logo" a 404. Both are fetched by
  the server in a background job, once. The answer is a `Face` row, keyed by
  address or domain, and the picture a public File in Company › Logos.
- A face not found is looked for again after thirty days (daily job). An
  unreachable source is not taken to mean "has none".
- Mail providers' domains (gmail.com and the like) and our own mail domain
  never give a sender a logo, since the provider is not who wrote.
- `dress_later` runs on Contact, Customer, Supplier and Bank. A record
  without a picture is dressed in the background: a contact by their
  address, an organisation by its website. Bank gains `one_logo`, set as its
  image field, since ERPNext's Bank has no picture.
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
- `text` reads the subject and the new part of the message, never the
  quoted history, for words that start with a naming-series prefix this
  site issues and end in a number. It keeps only those that exist, at most
  ten.
- It runs from `inbound.Arrival.process`, after Frappe has finished. Frappe
  saves a new message a second time after inserting it, which rewrote links
  made in an after_insert hook.
- **A link never grants read.** access.py opens a message to its mailbox's
  holders only. Frappe's form timeline lists every message linked to a
  record to whoever may read the record, so `getdoc`, `get_docinfo` and
  `get_communications` are wrapped with `override_whitelisted_methods` and
  narrowed to what the reader may open. Tested: a sales user who holds no
  mailbox sees none of the customer's mail; Frappe alone showed all three.
- **record_mail.js** adds the Mail tab beside Files on the records in its
  list, as record_files.js adds Files: to the layout, not to any doctype.

Stage 9, rules, out-of-office and bounces, is built.

- **rules.py** runs from `Arrival.process` for each message filed, on both
  kinds of mailbox. `Arrival.fresh` says whether a message is new. A first
  read and history read in the background are not, so connecting a mailbox
  does not re-sort or answer years of mail.
- `Mail Rule` is a mailbox's, and is seen and changed by its holders only
  (a has_permission hook and a query condition). It matches all or any of
  from, to or cc, subject and attachments, then moves, marks read and stars
  through actions.py, on the server for a connected mailbox. `stop` ends
  the rules for that message. A rule acts for its mailbox while
  `frappe.flags.one_mail_rules` is set, which `actions.require` lets
  through; nothing else sets it.
- Away is three fields on Email Account (`one_away`, `one_away_until`,
  `one_away_message`) set from the page. Each sender is answered once in
  four days (a cache key), with `Auto-Submitted: auto-replied` and the
  message's Message-ID as In-Reply-To. Machines are recognised by
  Auto-Submitted, Precedence, List-Id or List-Unsubscribe, X-Autoreply, and
  no-reply, mailer-daemon and postmaster senders. The reply goes by
  `outbound.deliver`, the transport `send` now shares, so a person's
  address on the mail domain can answer too.
- A delivery report (multipart/report, delivery-status) with a failed 5.x.x
  recipient puts that address on Frappe's Email Unsubscribe with
  `global_unsubscribe`, which Frappe's queue already leaves out, and says
  why in `one_bounce`. The message it bounced is marked Bounced. A 4.x.x
  delay is left alone. Mail sent from the mail domain bounces to
  Cloudflare, not to us, so those bounces are not seen yet.

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

### The plan

1. **Hosted addresses, inbound.** The Worker (in this repository), the
   KV record and secret, and admin's part in provisioning. Then the
   notice endpoint, raw storage, parsing into Communication, and the
   sweep.
2. **Sending.** The transport switch on `override_email_send`, admin's
   `mail_send` proxy to `send_raw` with its counts and limits, large
   attachments as links, undo send, and `References` on everything.
3. **Connected mailboxes.** Connect with known hosts and a guess for the
   rest. Folders from `LIST` with RFC 6154 special-use flags. Sync per
   folder by UIDVALIDITY and UIDNEXT, backfilling newest first, and flags
   by CONDSTORE where the server has it. Read, starred, move, delete and
   folder create or rename written back. A per-account lock so two workers
   never sync one mailbox.
4. **Threads and holders.** Message-ID threads, per-mailbox permission by
   exact address, shared addresses with holders, and the workspace's
   default replaced by a connected mailbox.
5. **The OneMail page.** Mailboxes and folders, the thread list, the
   reading pane, the composer, search, keyboard, drag to a folder, and
   live updates, as OneCloud's explorer does.
6. **Mail in OneCloud.** The Mail root, attachments from OneCloud when
   composing, and saving an attachment to My Files.
7. **Faces and logos.** For every party, stored in Company › Logos.
8. **Mail and records.** A message linked to its customer, supplier,
   employee or lead by address, and a Mail tab beside Files on those
   records.
9. **Rules, out-of-office and bounces.** Rules run on both kinds of
   mailbox and move on the server. Out-of-office replies on hosted
   addresses too. Addresses that bounce are suppressed at admin.
