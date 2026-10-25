# Connecting a mailbox

You can connect any mailbox that supports IMAP. Gmail and Outlook need an app
password, made in the account's security settings.

1. Click **+** beside OneMail's heading, or **Connect Mailbox** in
   **Settings › Mailboxes**.
2. Enter the **Email Address** and **Password**. The page says what you may
   connect: your organization address, and a private one such as Gmail
   only if **Private Mailboxes** allows it.
3. Leave **Enable Outgoing** on to send from it too.
4. Open **Server** only if the server isn't found on its own, or the login
   differs from the email address.

All of its folders appear, including Sent, Junk, Drafts and your own. Changes
you make here, such as reading, starring, moving, deleting and new folders,
happen on the mail server too, so your phone stays in sync.

A mailbox's **…** in the sidebar (or right-click) has **New Folder**,
**Signature**, **Out of Office**, **Automation**, **Attachments in OneCloud** and
**Mailbox Settings**. A folder you made has **New Folder**, **Rename** and
**Delete**; deleting it moves its messages to Trash.

**Who manages what** depends on each person's OneMail role, chosen on their
page in Workspace › People:

- **User**, which everyone has: their own connected mailboxes, such as their
  Gmail, are theirs to manage. On the address the workspace issued them,
  they set their own out of office, and ask for rules, which a Mail Manager
  approves.
- **Manager**: everything on every mailbox, as well as connecting shared
  mailboxes, the address policy and mail templates. Give it to the people in
  HR or PR who look after the company's mail.
- **Your own roles**, made by a Workspace Administrator in **Settings ›
  Roles**. It's one table: what OneMail lets a role do down the side, every
  role across the top. Signatures and sender names, out of office, mail rules
  and OneAI settings are each **No**, **Their Own Address** or **Every
  Mailbox**; who uses a mailbox, connections, connecting shared
  mailboxes, the address policy and mail templates are switches. Each cell
  saves as it changes. **New Role** adds a column, and a role's name renames
  or deletes it. **Show Roles** hides the columns you don't need. For example, a Brand role that keeps every signature and
  nothing else.

Workspace Administrators can do everything. Connecting a shared mailbox
doesn't make it the connector's.

**One mailbox only.** On a shared mailbox's **Users** tab, each person
shows their OneMail role, and **Edit Access** lets them change some parts of
that one mailbox, such as its signature or Automation, beyond what their
role allows. It offers only what the role doesn't already, and is disabled
for someone whose role allows everything. Taking them off the mailbox takes
that away too.

Whoever's role reaches other people's mailboxes finds them under
**Personal Addresses › People's Mailboxes**, and opens one to set its
signature or sender name.

**Sender Name**, at the top of **Signature**, is the name people see beside
the address. Left empty, mail from a person's own address goes out under
their name, and from a shared mailbox under whoever writes.

**Automation** in a mailbox's settings lists its rules in the order they
run, each with a switch to turn it off. **New Rule**, or a rule clicked,
opens it in the same tab.

On the address the workspace issued you, a rule is asked for: **Request
Rule**, then **Send Request**. It shows **Waiting for Approval** and
everybody who may change that mailbox's rules hears of it. When one approves it, it runs and you're told; if
one declines it, it's removed and you're told. Changing a rule that runs
asks again, and it pauses until it's approved. You can delete a request
while it waits.

**Replying by a rule.** A rule's **Reply** step answers in your own words,
where `{sender_name}` and `{subject}` fill in, or OneAI writes the reply
itself. What you type for OneAI is an instruction, never the reply: "answer
from their orders and say we follow up within a day". A rule's reply is an
automatic reply, so OneAI's goes out as it is, with no one checking it
first; a reply that needs a person belongs in the conversation, not in a
rule. OneAI is told the reply is sent as written, and one that still leaves
a blank for a person to fill is not sent at all. It needs OneAI on for the
mailbox and counts against its monthly limit.

**What OneAI may tell the sender.** Nothing about the workspace's records,
unless the reply is set to **reading their records**. Then OneAI is
handed, in short, everything the portal shows that person:
for each customer or supplier the address is a contact of, every record
still open (quotations not yet ordered, orders not yet delivered, invoices
not yet paid, the supplier's side of the same), the latest ten of the rest
of each kind, and any the message names, one line each (number, date,
status, total, what is left to pay, due or delivery date, items). For the
rest it can ask for two more things, only while it writes that reply: one
record in full as the portal page shows it (steps, facts, items with
prices, totals), and older records of a kind. Both
refuse anything that is not the sender's. A customer never writes
"SAL-ORD-2026-00003"; they write "where is my order", so OneAI works out
which records the message is about and is told to mention only those, not
an overdue invoice when they asked about a delivery. The
portal is the one place that decides what a customer may see, so there is
no second list to keep in step with it.

That needs the sender to be who they say. A From line is free to write, so
the server that received the message must have confirmed it: DMARC passed,
or DKIM or SPF passed for the sender's own domain, kept
on the message as **Sender Verified**. Only the check written by the last
server counts, since each server adds its own above what it received and a
forger can write any below it. Where the receiving server
writes none, nothing is verified and OneAI says nothing about records.

Connecting signs in to both servers before anything is saved: the incoming
one, and with **Enable Outgoing** on, the outgoing one too. A guessed
outgoing server is also tried on its other usual port.

**Who can connect what:**

- Anyone can connect their own mailbox at a company domain. It is an
  Organization mailbox: administrators can set its signature, away reply, OneAI and
  Automation, as for the address the workspace gave them. At a domain set
  up in **Setup** they type only the address and password; the server
  fields are hidden.
- A workspace administrator can connect somebody's organization mailbox
  for them from **Organization Mailboxes › Connect Organization Mailbox**,
  with its password. It appears in that person's mailboxes. Only a mailbox
  at a company domain can be connected this way, never a private one.
- Anyone can connect a private mailbox, such as Gmail, unless an
  administrator has turned off **Private Mailboxes**. No one else can see
  into it or change it, not even administrators.
- A Workspace Administrator connects a workspace address such as
  `sales@yourcompany.com` from **Settings › Shared Mailboxes › Connect
  Shared Mailbox**, then adds its users and who may send from it.
