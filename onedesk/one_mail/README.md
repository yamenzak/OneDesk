# OneMail

Written by hand. **Not built yet.** This is the plan: what OneMail will be,
what was studied, what was decided and why, and the stages. As each stage
lands, the part above **Under the hood** becomes the manual, as OneCloud's
did.

OneMail is where a company's email lives. Every workspace has an address of
its own, and every person in it has one too. The company's existing mailboxes
— its Gmail, its Outlook, its hosting provider's mail — can be connected as
well, with their folders, and worked on here instead. Attachments are in
OneCloud and senders show with their faces and logos. A message can belong to
a customer, a supplier or an employee as well as to a mailbox.

## Your addresses

Every workspace gets `acme@m.4dl.app`. It is where the workspace's mail comes
in and goes out from, until a workspace administrator connects the company's
own mailbox to use instead. Every person gets `name.acme@m.4dl.app`, which
only receives: it is where a supplier, a site or a newsletter can reach them
without their private address.

## Connecting a mailbox

Any mailbox that speaks IMAP can be connected: Gmail and Outlook with an app
password, and any hosting provider's. Its folders come with it, including
Sent, Junk, Drafts and those made elsewhere. What you do here happens there:
reading, starring, moving, deleting and making folders. A phone on the same
account agrees with OneMail.

A workspace administrator can connect one mailbox as the workspace's own,
and add shared addresses such as `sales@theircompany.com` for several people
to hold. Anyone can connect their own.

## Attachments and faces

Every attachment is in OneCloud, under **Mail**, in a folder per mailbox.
People who write to you show with their photo from Gravatar. Companies show
with their logo, which is kept in Company › Logos and used by every record
in One, not only by mail.

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
