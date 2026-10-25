# Rules and out of office

**Automation and OneAI, who decides what.** Automation is what you decide:
rules you write, which do the same thing every time, and the only thing
besides Out of Office that answers or forwards mail on its own. OneAI is
what OneAI decides from reading the mail (the OneAI tab): sorting junk,
filing, and the records and tasks a message asks for. It never mails
anyone outside the workspace; an Ask OneAI step is a question a rule asks,
and the rule decides what follows. Where both would do the same thing, the
rule wins: a record a rule made from a message (linked to it as `rule`) is
one OneIntake makes no second of (`act._ruled`, `gate.made_by_rule`), and a
rule that moved the message out of the Inbox leaves nothing to sort.

Rules, under **Automation** in a mailbox's **⋯** menu, decide what happens to new mail as it
arrives in the Inbox. A rule reads as sentences on a line down the side,
such as "If the sender **is a Customer** and **it arrives after hours**,
then **star it** and tell **Layla** on the bell". Each bold part is a chip:
click it to choose something else, type in a blank, or open a reply in a
small window. A rule is a list of steps, read top to bottom:

- **If** checks the message. Its conditions sit in groups, each **All of
  These Are True** or **Any of These Is True**, and a group can hold
  another. It can check who it's from or to, the subject, any words in it,
  the sender's domain, whether it has an attachment, whether it starts a
  conversation, whether it's from outside the workspace, whether the
  sender is a customer, supplier, lead, contact or employee, and whether it
  arrives after hours or on a holiday (the workspace's shift and holiday
  list). An If has **Then** steps, and **Otherwise** steps if you add them.
  With no conditions, it's every message.
- **Ask OneAI**, on a mailbox OneAI reads, asks a yes-or-no question ("is
  it a complaint?") or picks one of your labels ("Quote Request",
  "Complaint"). Each answer has its own steps. A rule with Ask OneAI runs
  once OneAI has read the message, a moment after it arrives.
- **Actions:** move to a folder, mark as read, star, move to Junk, reply
  (your own words, or written by OneAI and sent as it is), forward,
  assign to someone who uses the mailbox, tell them on the bell, link the
  message to the sender's customer, supplier or lead, create a lead, issue
  or task from it, and **Stop Here**, which keeps the rules after this one
  off the message.

A reply goes **once per conversation**, or once a day, week or month to
each sender, never to automatic mail or mailing lists, and with the
mailbox's signature. A rule's reply stands in for an out-of-office reply
to the same message.

**To make a rule:** **New Rule**, then start from **Blank** or one of the
examples, change anything, and save. The examples come in five groups, and
between them they use every condition and every action:

- **Replies**: **Auto Reply** (every message, once per conversation),
  **Acknowledge New Mail**, **We're Closed** and **Confirm Documents
  Received**.
- **Sorting**: **Newsletters to a Folder**, **Invoices to a Folder**,
  **Customers to a Folder**, **Important Sender** and **Block a Sender**.
- **People and Records**: **Support Requests** (an issue, assigned),
  **New Leads**, **Tasks From Mail**, **Urgent After Hours**, **Assign New
  Conversations** and **Route by Subject** (quote requests to one person,
  invoices to another).
- **Forwarding**: **Auto Forward** (every new message), **Forward Supplier
  Bills**, **Forward After Hours** (customer mail to an on-call address) and
  **Forward Job Applications**.
- **With OneAI**, only where OneAI may read the mailbox: **Sort by
  Topic**, **Upset or Urgent**, **Answer From Their Records** and **Auto Reply in Their Language**.

Every example that asks OneAI something or has OneAI write a reply carries
the OneAI badge.

An example with a blank to fill (an address, a domain) can't be saved until
it is filled: a condition with nothing to look for would match all mail.
Rules run in order; switch one off in the list to pause it. Moves happen on
the mail server too, so your phone matches. Rules only apply to new mail.

**Auto Reply** is a rule now, the first example. A mailbox that answers by
a rule says **Auto Reply On** in the rail.

You can also ask OneAI, for example "move any mail with the word cola into a
CocaCola folder" or "put mail about soft drinks in Beverages". It suggests
the rule on a card. When you approve it:

- the folder is created if it doesn't exist
- OneAI starts reading the mailbox, for a rule about what mail says
- the rule is created
- for a rule by words, matching mail already in the Inbox can be moved too

**Out of Office** is on every mailbox of your own: the address the
workspace issued you and any you connected. Shared mailboxes don't have it;
they answer by a mail rule. Everyone can set their own, unless their
OneMail role says otherwise.

- **From** and **Until** set it up ahead of time; leave From empty to start
  now and Until empty to keep it on.
- **Sent To**: everyone, only people in the workspace, or them and the
  workspace's contacts.
- **Message** starts as the standard reply; change it, and **What They Get**
  shows it as the sender will, signed and under the mailbox's sender name.

Each sender gets one reply every four days, and one again when a new time
away begins. Mailing lists, newsletters, other automatic replies and
no-reply addresses get none. While it's on, the mailbox says **Out of
Office until …** in OneMail's rail and in Settings › Mailboxes, and anyone
writing to you sees that you're away above their message, and who covers.

**On leave.** Every mailbox of your own answers on its own on each day of
your approved leave in OneHR, so nobody turns it on or off. On the leave
request:

- **Away Message** is what the reply says. Left empty, it's the mailbox's
  own message, or else that you're on leave and back on the first working
  day after it, past weekends and holidays.
- **Out of Office Replies** off means no replies for this leave.
- **Covering Person** is named in the reply for anything urgent, and with
  **Covering Person Reads My Mail** they can read your workspace address
  in OneMail until the leave ends (never send from it). They're told when
  it starts.

The half day of a half-day leave gets no replies, since you're working
too. A leave that's cancelled stops the replies, and the covering, at once
(`rules.on_leave` as each message arrives, `rules.covered` as a leave is
decided, `rules.cover` each day).

**Bounces:** when mail to an address bounces permanently, OneMail stops
sending to it and marks the message that bounced.
