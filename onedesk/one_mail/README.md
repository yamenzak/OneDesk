# OneMail

OneMail is where your company's email lives. Every workspace and every person
in it has an address. You can also connect existing mailboxes, such as Gmail,
Outlook or your hosting provider's, and work on them here with their folders.
Attachments are saved in OneCloud, and messages can be linked to customers,
suppliers, employees and other records.

Not built yet: mail from outside arriving at the workspace's own address. It
needs a Cloudflare key with Zone Settings: Edit.

## Your addresses

- **The workspace's address** is `acme@m.4dl.app`, made when the workspace
  is, before anyone runs the setup wizard. Workspace Administrators start
  with access to it; they choose who else reads it and who may send from it.
  It stays the workspace's mailbox until an administrator makes a connected
  company mailbox the workspace's instead.
- **Your own address** is `name.acme@m.4dl.app`, made when you're added to
  the workspace. The name is chosen by whoever adds you, or is your first
  name. You can send from it as well as receive, unless an administrator
  turns that off for everyone. Once given, it can't be changed.

## Settings

**Settings** at the foot of OneMail's rail opens OneMail's settings:

- **Mailboxes**: every mailbox you read. Opening one turns the sidebar into
  its own tabs, with **All Mailboxes** above them to go back: **Signature**,
  **Out of Office**, **Auto Reply** (shared mailboxes), **OneAI**, **Users**
  (shared mailboxes, administrators), **Connection** (connected mailboxes)
  and **Mail Rules**. Each tab has its own **Save**.

**OneAI** in a mailbox's settings:

- The switch beside the title decides whether OneAI may read the mailbox at
  all. Off, nothing reads it: not new mail, not search by meaning, and not
  the OneAI panel, which can't open its conversations or draft replies.
- **Read New Mail** reads each new message as it arrives, with the
  permissions of whoever turned it on. **Reads To** sets how far it goes:
  **Sort Only** moves junk and runs About rules; **Read and File** also
  reads each message and links it to its records; **Read, File and Act**
  also makes the tasks, events and records it asks for.
- **Read Attachments** off leaves attachments to the reading that costs
  nothing: scans, photos and recordings are not sent to OneAI.
- **Monthly Credit Limit** caps what reading this mailbox may spend in a
  month. When it is reached, new mail is read without OneAI until the month
  turns, and whoever OneAI reads it for hears once.
- **Shared Mailboxes** (administrators): the workspace mailbox and every
  shared one. Opening one shows the same tabs; **Users** adds or removes
  people, turns **Send** on or off per user, and sets it as the workspace
  mailbox.
- **Personal Addresses** (administrators): **Send From Workspace
  Addresses**, and **External Mailboxes** for mailboxes users connect
  themselves. When on, **Allowed Domains** limits them to the domains listed;
  leave it empty to allow any. Shared mailboxes are not affected.
- **Mail Templates** (administrators): reusable email text.

## Connecting a mailbox

You can connect any mailbox that supports IMAP. Gmail and Outlook need an app
password, made in the account's security settings.

1. Click **+** beside OneMail's heading, or **Connect Mailbox** in
   **Settings › Mailboxes**.
2. Enter the **Email Address** and **Password**.
3. Leave **Enable Outgoing** on to send from it too.
4. Open **Server** only if the server isn't found on its own, or the login
   differs from the email address.

All of its folders appear, including Sent, Junk, Drafts and your own. Changes
you make here, such as reading, starring, moving, deleting and new folders,
happen on the mail server too, so your phone stays in sync.

A mailbox's **…** in the sidebar (or right-click) has **New Folder**,
**Signature**, **Out of Office**, **Rules**, **Attachments in OneCloud** and
**Mailbox Settings**. A folder you made has **New Folder**, **Rename** and
**Delete**; deleting it moves its messages to Trash.

A shared mailbox's signature, out-of-office reply, auto reply, OneAI and
connection are changed only by a Workspace Administrator, whoever connected
it.

**Mail Rules** in a mailbox's settings lists its rules in the order they
run, each with a switch to turn it off. **New Rule**, or a rule clicked,
opens it in the same tab.

**Replying by a rule.** A mail rule can **Reply** as one of its actions:
with a fixed **Reply Text**, where `{{ sender_name }}` and `{{ subject }}`
fill in, or with **OneAI**, from an **Instruction** such as "send our price
list and say we answer within a day". A rule replies once per conversation
and never to automated mail. OneAI's reply waits as a card for whoever made
the rule when **Review Before Sending** is on, and always when it left a
blank for a person to fill in; it needs OneAI on for the mailbox and counts
against its monthly limit. A message a rule replied to gets no Auto Reply.
With an **About** condition, the rule answers by what a message is about,
such as "a customer asking for a price".

**Auto Reply** on a shared mailbox answers the first message of each new
conversation, such as "We received your message and will reply soon." It
is not sent to replies in a thread, to mailing lists or automated mail, or
more than once a day to the same sender, and an out-of-office reply takes
its place when both are on. `{{ sender_name }}` and `{{ subject }}` fill in
from the message.

Connecting signs in to both servers before anything is saved: the incoming
one, and with **Enable Outgoing** on, the outgoing one too. A guessed
outgoing server is also tried on its other usual port.

**Who can connect what:**

- Anyone can connect their own mailbox, unless an administrator has
  turned off **External Mailboxes**. No one else can see into it, not
  even administrators.
- A Workspace Administrator connects a workspace address such as
  `sales@yourcompany.com` from **Settings › Shared Mailboxes › Connect
  Shared Mailbox**, then adds its users and who may send from it.

## Reading and writing

**OneMail** in the dock opens every mailbox you have access to, the
workspace's first, then shared ones, then your own. Folders list
conversations newest first. A conversation shows all its messages, including
your replies, with older ones collapsed.

A connected mailbox is checked for new mail every minute, and the list
updates on its own. **Refresh**, beside the search box, reloads it now.

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

**Writing:** **New Email** at the top starts a message, and **Reply**,
**Reply all** and **Forward** answer the one you're reading. The email window
opens in the bottom-right corner, and you can minimise it and keep reading. You can schedule a message with the
arrow beside **Send**, undo it for a few seconds after sending, ask for a read
receipt or a copy to yourself from **⋯**, and link it to a record.

**Signatures** belong to the address, not the person. Set one under
**Signature** in the mailbox's **⋯** menu. It's added to every email sent
from that address. Only a Workspace
Administrator can change the signature of a workspace mailbox.

A signature is one of six styles drawn from what One already knows: the
holder's name, job title and numbers, and the company's name, logo, colour,
website and address. The tab shows the chosen style large, with a small card
for each style under it; pointing at a card shows that style. **Show** picks
which details appear, Company Name among them. A shared mailbox signs as the
company. The two logo styles are offered only once the company has a logo.
**Custom** is written by hand, starting from Simple's lines, and is never
redrawn. A style is drawn when it's saved, so a later change to the company
or the person shows up the next time it's saved (`signatures.py`).

The signature isn't put in the compose window's editor, which would flatten
its layout into paragraphs. It shows under the editor as it will be sent,
with **Remove** to leave it off one email, and goes in above the quoted mail
as the email is sent (`mail_compose.js`). The company logo goes inside the
email as an inline image rather than as a link to the workspace, which mail
clients block until asked: the signature keeps only the logo's path, and
`signatures.inline_logo` marks it to be embedded in the copy that is queued.

## Rules and out of office

**Rules**, in a mailbox's **⋯** menu, sort new mail as it arrives in the
Inbox. A rule can move mail to a folder, mark it as read or star it.

It can match mail by:

- who it's from or to
- the subject
- a word anywhere in it (**Subject or Text Contains**)
- whether it has attachments
- what it's about (**About**, in plain words such as "soft drinks")

**To make a rule:**

1. Open the mailbox, then **Rules** in its **⋯** menu.
2. Click **Add Mail Rule**.
3. Under **When**, fill in what to match. **Matching Mail** says whether
   mail must match all of them or any one.
4. Under **Then**, pick a **Move To** folder, or tick **Mark as Read** or
   **Star**.
5. Save.

When several rules match, the lowest **Order** runs first. **Stop Here**
keeps later rules off mail this one matched. Untick **Enabled** to pause a
rule.

On a connected mailbox, the rule is also set up on the mail server, so your
phone matches. Rules only apply to new mail, not to mail that was there when
the mailbox was connected.

**About rules** need OneAI to read the mailbox, which is turned on in One,
under **OneIntake › What OneAI Reads**.
OneAI reads each new message and moves it a moment later. Spam and phishing
always go to Junk.

You can also ask OneAI, for example "move any mail with the word cola into a
CocaCola folder" or "put mail about soft drinks in Beverages". It suggests
the rule on a card. When you approve it:

- the folder is created if it doesn't exist
- OneAI starts reading the mailbox, for an About rule
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
templates for any record. See **Settings › Mail Templates**.

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

**Being told.** A mailbox that stops connecting is told to whoever holds it,
or to every administrator when nobody does (**Mailbox Not Reachable**). Mail
you sent that could not be delivered after every retry is told to you, on
the bell and by push (**Mail Not Sent**). Being given a shared mailbox is told
to you (**Mailbox Shared With You**).

**Sender pictures:** people who write to you show with their contact
picture, their Gravatar photo or their organization's logo. Contacts, leads,
customers, suppliers, manufacturers and banks without a picture get one the
same way. So do your own people: a user or employee without a photo gets
the one on their other record (a photo on the employee goes to the user,
and back), else their Gravatar photo. Your company without a logo gets its
website's, and the letter heads drawn from it show it. A picture you upload
always comes first.
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

## Connections

- **From One**: Each person added to the workspace gets their own address. The mail window offers the templates set in **Settings › Mail Templates**.
- **From OneIntake**: Search also finds words inside attachments that have been read. About rules use what a message is found to be about.
- **To OneAdmin**: Mail from the workspace's addresses is sent through OneAdmin. By default the workspace can send 200 messages an hour and 2,000 a day.
- **To OneCRM**: Mail from a customer, a lead or one of their contacts is linked to their record. Customers, leads, contacts, deals and quotations have a Mail tab. Contacts, leads and customers without a picture get one from Gravatar or their website.
- **To OneHR**: Mail from an employee's address is linked to their record. Employees and job applicants have a Mail tab. An employee without a photo gets the one on their user, or their Gravatar photo.
- **To OneBook**: A message that names an invoice or payment by its number is linked to it. Sales and purchase invoices have a Mail tab.
- **To OneCloud**: Every attachment is saved in OneCloud under Mail, in a folder for each mailbox. A file too large to send from the workspace's address goes as a link that works for 30 days.
- **To OneIntake**: In a mailbox OneAI reads, each new message and its attachments go to OneIntake.

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
  The `Email Domain` is one a workspace administrator set up, and the guess
  uses the standard ports. Somebody whose server is none of these types it
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
- `holders.replace` makes a connected mailbox of the workspace's its
  mailbox, and, if it sends, its default outgoing account. The address on the
  mail domain keeps receiving, so nothing sent to it is lost. `restore` puts
  it back.
  A connected mailbox can take the place for receiving, sending or both.
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
  A message's attachments answer to it (one_storage/namespace.py `may`), so
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

Stage 7, faces and logos, is built.

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

An attachment is stored in R2 like any file (one_storage/store.py), and a
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
