# OneMail: scratchpad

Known issues and plans, kept short. Something done leaves it.

## Not built

- **Mail from outside at the workspace's own address.** It needs a Cloudflare
  API key with Zone Settings: Edit.
- **Signing in with Google or Microsoft** to connect an organization mailbox,
  instead of a password. Microsoft needs an Entra app registered first; Google
  needs domain-wide delegation. Put off on 2026-10-24.

## Known issues

- **OneAI is told only the title** of One › Mail and One › Mail Templates on
  the rail (`one_ai/here.py untold`, the demo check
  `oneai_is_told_what_every_place_shows`).
- **Organization mailboxes and company domains aren't in the demo.** Both
  need a real mail server, so the READY pass read them in code and checks
  only.

## How it was built

The order OneMail was built in, kept for the stages still open.

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
