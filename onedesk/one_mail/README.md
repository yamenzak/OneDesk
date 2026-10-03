# OneMail

OneMail is where your company's email lives. Every workspace and every person
in it has an address. You can also connect existing mailboxes, such as Gmail,
Outlook or your hosting provider's, and work on them here with their folders.
Attachments are saved in OneCloud, and messages can be linked to customers,
suppliers, employees and other records.

Not built yet: mail from outside arriving at the workspace's own address. It
needs a Cloudflare key with Zone Settings: Edit.

## Your addresses

- **The workspace's address** is `acme@m.4dl.app`. The workspace sends and
  receives from it until a Workspace Administrator connects the company's own
  mailbox instead.
- **Your own address** is `name.acme@m.4dl.app`, made when you're added to
  the workspace. The name is chosen by whoever adds you, or is your first
  name. It only receives mail, so you can give it to suppliers, sites and
  newsletters instead of your private address. Once given, it can't be
  changed.

## Connecting a mailbox

You can connect any mailbox that supports IMAP. Gmail and Outlook need an app
password, made in the account's security settings.

1. Click **Connect Mailbox**.
2. Enter the **Email Address** and **Password**.
3. Leave **Enable Outgoing** on to send from it too.
4. Open **Server** only if the server isn't found on its own, or the login
   differs from the email address.

All of its folders appear, including Sent, Junk, Drafts and your own. Changes
you make here, such as reading, starring, moving, deleting and new folders,
happen on the mail server too, so your phone stays in sync.

**Who can connect what:**

- Anyone can connect their own mailbox. No one else can see into it, not
  even administrators.
- A Workspace Administrator can tick **Shared Mailbox** to connect a
  workspace address such as `sales@yourcompany.com` and choose who has
  access to it. They can also make the company's mailbox the workspace's
  own, for receiving, sending or both.

## Reading and writing

**OneMail** in the dock opens every mailbox you have access to, the
workspace's first, then shared ones, then your own. Folders list
conversations newest first. A conversation shows all its messages, including
your replies, with older ones collapsed.

Remote pictures are hidden until you click **Show pictures**, because loading
them tells the sender you opened the message.

**Working with several conversations:** select them with their checkboxes,
or with Shift and Ctrl, then mark read, star, move, archive or delete them.
Moving, archiving and deleting can be undone with **Undo** for a few seconds.
Deleting from Trash is permanent.

**Keyboard shortcuts:**

| Key | Action |
| --- | --- |
| `j` / `k` | Next / previous conversation |
| `e` | Archive |
| `#` | Delete |
| `r` / `a` / `f` | Reply / Reply all / Forward |
| `s` | Star |
| `u` | Mark as unread |
| `c` | New email |
| `/` | Search |

**Search** supports `from:`, `to:`, `subject:`, `has:attachment`,
`is:unread`, `is:read` and `is:starred`. Other words are searched anywhere in
the message. For example, `from:ana subject:"price list" is:unread` finds
unread mail from Ana with "price list" in the subject.

**Writing** uses frappe's email window, so you can schedule a message, undo
it for a few seconds after sending, and link it to a record.

**Signatures** belong to the address, not the person. Set one under
**Signature** in the mailbox's **⋯** menu. It's added to every email sent
from that address, and you can edit it before sending. Only a Workspace
Administrator can change the signature of a workspace mailbox.

## Rules and out of office

**Rules**, in a mailbox's **⋯** menu, sort new mail as it arrives in the
Inbox. A rule can move mail to a folder, mark it as read or star it.

It can match mail by:

- who it's from or to
- the subject
- a word anywhere in it (**Subject or Text Contains**)
- whether it has attachments
- what it's about (**About**, in plain words such as "soft drinks")

On a connected mailbox, the rule is also set up on the mail server, so your
phone matches. Rules only apply to new mail, not to mail that was there when
the mailbox was connected.

**About rules** need **Read with OneAI…** turned on in the mailbox's menu.
OneAI reads each new message and moves it a moment later. Spam and phishing
always go to Junk.

You can also ask OneAI, for example "move any mail with the word cola into a
CocaCola folder" or "put mail about soft drinks in Beverages". It suggests
the rule on a card. When you approve it:

- the folder is created if it doesn't exist
- **Read with OneAI** is turned on, for an About rule
- the rule is created
- for a rule by words, matching mail already in the Inbox can be moved too

**Out of Office**, in the same menu, sends an automatic reply until the date
you set. Each sender gets one reply every four days. Mailing lists,
newsletters, other automatic replies and no-reply addresses get none.

**Bounces:** when mail to an address bounces permanently, OneMail stops
sending to it and marks the message that bounced.

## Mail on records

Incoming messages are linked automatically to the records they're about:

- the customer or supplier of the contact who sent it
- an employee or lead with the sender's address
- records the conversation is already linked to
- any invoice, order or other document named by its number

The reading pane shows the linked records. **Unlink** (the ×) removes one,
and **Link to Record** adds another.

Customers, suppliers, leads, employees and documents have a **Mail** tab next
to Files, with their conversations and a **New Email** button.

**Email Template** in the email window offers the templates for the record a
conversation is linked to, filled in from it. In a new message it offers
templates for any record. See Mail Templates in the Workspace settings.

Linking a message to a record never shows it to anyone new. The Mail tab and
the record's activity only list messages you could already open.

## Attachments and pictures

Every attachment is saved in OneCloud, under **Mail**, in a folder for each
mailbox. Only people with access to the mailbox can see it.

- **Attachments in OneCloud** in the mailbox's **⋯** menu opens the folder.
- The folder button on an attachment saves a copy to My Files.
- When writing, you can attach a file from OneCloud.
- A file too large to send from the workspace's address is sent as a link
  that works for 30 days.

**When storage is full**, mail still arrives but its attachments aren't
saved. Each shows **Not saved, storage is full**. Administrators and the
people with access to the mailbox get **Attachments Not Saved**, at most once
a day. OneMail tries again every hour and saves them once there's space. Free
up space or add storage in Plan and Credits.

**Sender pictures:** people who write to you show with their contact
picture, their Gravatar photo or their organization's logo. Contacts, leads,
customers, suppliers and banks without a picture get one the same way.
Pictures are fetched once by the workspace, never by your browser, and kept
in Company › Logos, so opening a message reveals nothing to the sender.

## Asking OneAI

In OneMail, the OneAI panel knows the mailbox, folder and conversation you
have open. It offers:

- **Summarise this conversation**: who wants what, what was agreed and what's
  still open.
- **Draft a reply**: finish the sentence with what the reply should say, such
  as "turn down their offer". OneAI writes the reply in the conversation's
  language and shows it on a card. **Approve** opens it in the email window,
  ready to edit and send. OneAI never sends it.
- **What needs an answer?**: conversations in the folder where the last
  message came to you, oldest first.

**In the email window**, the OneAI button next to **Message** helps with what
you're writing:

- **Improve it**, **Make it shorter**, **Make it longer**, **Make it more
  formal**, **Make it friendlier**, **Fix spelling and grammar**
- **Translate…**, followed by the language
- **Write a first draft** and **Reply saying…**, in an empty reply
- or anything in your own words

OneAI reads your text, the subject, the recipients and the message you're
replying to, but not your signature. **Approve** replaces your text with the
suggestion and keeps your signature and the quoted message.

OneAI only reads conversations in mailboxes you have access to, and only when
you ask. Each question uses OneAI credits.

## Under the hood

For the people who build OneMail. OneAI does not read past this heading.

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
- `dress_later` runs on Contact, Lead, Customer, Supplier and Bank. A record
  without a picture is dressed in the background from both services, in the
  order that fits it (`sources`), stopping at the first picture:
  - a contact or lead: their face, then their company's logo by the domain
    of their address, then by their website;
  - a customer or supplier: its website's logo, then its address's domain
    (its own, or its primary contact's), then a face registered to the
    address itself, since some register a logo against info@;
  - a bank: its website's logo only.
  Bank gains `one_logo`, set as its image field, since ERPNext's Bank has no
  picture. A patch runs `dress_all` once in the background for records that
  existed before; a migrate does not wait on Gravatar or Google.
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
- **record_mail.js** draws the Mail tab beside Files on the records
  `linking.TABS` names; `record_tabs.js` adds it to the layout, not to any
  doctype, as it adds every record tab (one/tabs.py).

Stage 9, rules, out-of-office and bounces, is built.

- **rules.py** runs from `Arrival.process` for each message filed, on both
  kinds of mailbox. `Arrival.fresh` says whether a message is new. A first
  read and history read in the background are not, so connecting a mailbox
  does not re-sort or answer years of mail.
- A rule with an **About** is not run on arrival: `rules_of(by_meaning=True)`
  hands its topics to Intake's first look (`one_intake/understand.py`), the
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

Read against the old OneMail before it was deleted, three things came
across:
- **The address signs, not the writer.** Frappe signs a Communication on
  save with the sender's own User signature or the default outgoing
  account's, after the composer has closed, so a reply from sales@ went out
  signed by somebody else and nobody saw it. `file_sent` sets
  `skip_add_signature`, and mail_compose.js makes the composer put in the
  sending address's own signature (`holders.signature_for`, since Email
  Account is not readable to its holders) before the writer's.
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
