# Settings

**Settings** at the foot of OneMail's rail opens OneMail's settings:

- **Mailboxes**: every mailbox you read. Opening one turns the sidebar into
  its own tabs, with **All Mailboxes** above them to go back: **Signature**,
  **Out of Office** (your own mailboxes), **OneAI**, **Users**
  (shared mailboxes, administrators), **Connection** (connected mailboxes)
  and **Automation**. Each tab has its own **Save**. Where your role can't
  change a tab, such as the signature and OneAI on the address the workspace
  gave you, it still shows what is set. Whether it can be changed is the role's
  ability in **Roles**, such as **Signature and Sender Name** set to **Their
  Own Address**.

**OneAI** in a mailbox's settings is OneIntake for that mailbox, the virtual
employee that reads its mail:

- The switch beside the title decides whether OneAI may read the mailbox at
  all. Off, nothing reads it: not new mail, not search by meaning, and not
  the OneAI panel, which can't open its conversations or draft replies.
- **New Mail** says how far each new message is read on its own, with the
  permissions of whoever set it: **Not Read**, **Sorted** (a quick look,
  which also answers the Automation's Ask OneAI steps), **Read and Filed**
  (read in full and filed where it belongs) or **Read, Filed and Acted On**
  (it also does what the message asks for). Each level does everything the
  one before it does.
- Under it, everything OneAI does at each level is listed, each with its own
  switch, all on until switched off (`gate.JOBS`):
  - Sorting: **Move Junk and Phishing**, **Move Newsletters and Ads**.
  - Filing: **Link Messages to Records**, **Attach Files to Records**,
    **Rename and Tag Files**.
  - Actions: **Create Customers and Suppliers**, **Create and Update
    Contacts**, **Update Tax ID, Website and Phone** (empty fields filled, a different value proposed), **Create Tasks**, **Create
    Events**, **Draft Invoices, Orders and Payments** (drafts in Ready to
    Submit; a bill asking to be paid to an IBAN not on file is held), **File Employee Documents**, **Post Site Logs** and **Other
    Actions** (what the agent decides on for itself).

  A job past the level New Mail is set to stays in view, greyed, and its
  group says which level brings it. Every OneIntake write goes through
  `act.apply`, which asks `gate.does` for the job its key names
  (`gate.job_of`), so a switched-off job is never done or proposed; the
  e-invoice submit asks the same for Bills.
- **Read Attachments** off leaves attachments to the reading that costs
  nothing: scans, photos and recordings are not sent to OneAI.
- **Credits** shows what reading this mailbox spent this month, against the
  **Monthly Credit Limit** when there is one. When it is reached, OneAI stops
  reading new mail until the month turns, and whoever it reads for hears once.
- Ask OneAI steps only run while new mail is read, since they ride on that
  quick look. A rule with one can't be switched on otherwise, the step says
  so in the builder, and setting New Mail to Not Read names those rules
  first; they then show **Not Running** in Automation.
- **Setup** (administrators): **Company Domains**, each with its incoming
  and outgoing servers, found from the domain when its mail is on Google
  Workspace, Microsoft 365 or Zoho, then **Default Incoming** and **Default
  Outgoing**, and which address notifications are sent from.
- **Shared Mailboxes** (administrators): the workspace mailbox and every
  shared one. Opening one shows the same tabs; **Users** adds or removes
  people and turns **Send** on or off per user.
- **System Mailboxes** (administrators, and roles that reach other
  people's mail): **Send From New Addresses**, whether the address a new
  person is given sends, then each person's address with its own **Send**
  switch (`holders.set_sends`). The default never changes an address
  already given.
- **Organization Mailboxes** (the same): every mailbox people hold at the
  company's domains, and **Connect Organization Mailbox** to connect one for
  somebody.
- **Private Mailboxes** (administrators): the switch beside the title allows
  mailboxes people connect anywhere else, such as Gmail. When on, **Allowed
  Domains** limits them to the domains listed; leave it empty to allow any.
- **Mail Templates** (administrators): emails people start from. One opens
  in place, with Save and Delete at the top. A template a setting still
  sends, such as the leave approval HR Settings sends, says **Used by** and
  can't be deleted until the setting names another. A template with code in
  it, as the apps' own are written, opens as code so its tags stay whole.
  Once **For** is set, typing **/** in the subject or the message opens
  the record's fields at the cursor; typing narrows them and Enter puts one
  in. A table asks which columns, the item's name, quantity, rate and
  amount ticked, and is written as one line that is mailed as a table.
  **Preview** fills the template in from the latest record of its kind, or
  another picked, as it would be sent. Values come out as the record shows
  them, 1,250.00 AED rather than 1250.0, in a table too.

A mailbox opened from System or Organization Mailboxes shows its signature,
out-of-office reply, OneAI and Automation tabs.

Every mailbox is one of five kinds, by whose it is. **Workspace** is the
Default Incoming. **Shared** is a team's, such as `sales@yourcompany.com`.
**System** is the address the workspace gives each person, such as
`ahmad.yourcompany@m.4dl.app`. **Organization** is a person's at one of the
company's domains, such as `ahmad@yourcompany.com`. **Private** is a
person's anywhere else, such as Gmail. The company's domains are the
workspace's mail domain, every shared mailbox's, and every domain added in
Setup (`addresses.company_domains`), so nobody types them twice.
