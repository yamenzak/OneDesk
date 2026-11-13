# Notifications

## The Bell

**Notifications** is the bell in the bar. Its number is how many you haven't
read. Click it to open the panel:

- **All** lists your notifications, newest first. Click one to open its
  record. That marks it read.
- **Events** lists your events for today.
- The double tick, **Mark all as read**, marks every one read.
- The gear, **Notification Settings**, opens NotificationCenter, where
  you choose what also comes by email or push.

## Your Notifications

Every notification One can send you, and how you get it. Every notification
appears in One. Here you choose which ones you also get by **email** and by
**push**. Push shows them on your computer or phone even when One isn't open.

## Push Notifications

In NotificationCenter:

- **Turn On Push** asks your browser for permission. After that, this browser
  gets the notifications you switch on for push.
- **Send Test** shows a test notification. **Turn Off** stops push in this
  browser.
- Push is turned on per browser. Your other browsers are listed with
  **Remove**.
- Private windows can't get push. If you blocked notifications in a browser,
  the page says so. Allow them in the browser's settings and come back.
- iPhone and iPad aren't supported yet. Apple only allows push for sites added
  to the Home Screen as an app, and One can't be added that way yet.

## Choosing What You Get

In NotificationCenter:

- **Notifications** is the main switch. When it's off, you get no
  notifications and no emails, except the few that are always mailed.
- **Also by Email** turns off all emails at once, whatever is switched on
  below, except the few that are always mailed.
- **Always mailed** are security notices (a new sign-in, a changed password,
  a new administrator), privacy requests, and what the workspace's money and
  storage need from its administrators. Each says so at its foot.
- Under **Apps**, each app has one row. Open it for every notification it
  can send you, each with a line on when it's sent. Switch on **Email** or
  **Push** for the ones you also want that way. **Other** has what the
  workspace's own rules tell you.
- You only see notifications that can reach you. For example, HR's
  notifications are only for HR. Notifications from OneAI have the OneAI tag.
- When an event comes in two versions, such as one document or several, they
  share one row and one set of switches.
- A dimmed switch says why you can't change it. Either the workspace doesn't
  send that notification that way, or the email is always sent because you
  answer it by replying, like a project's status check-in.
- **Other Emails** has the two emails that aren't notifications: reminders
  before your events, and emails about records assigned to you.

An email of a notification you chose ends with **Turn off these emails**. It
turns off email for that one notification, as its switch here does, without
signing in, and the page it opens has **Turn On Again**. Your email app may
offer the same as an Unsubscribe button. Emails that are always mailed have
neither.

Each switch is saved as you change it. Administrators choose what new people start
with, and the text of each notification, in NotificationCenter's
**Words and Rules**.

OneAI offers:

- **What will I be told about?** Every notification that can reach you, and
  which ones you get by email.
- **Too many emails?** Which emails you could switch to in-app or push only,
  and why. You make the change yourself. This is also the **Too Many Emails?**
  button at the top of the page.

## The Workspace's Notifications

Administrators see **Yours** and **Workspace** at the top of each app's page
in NotificationCenter. **Workspace** lists everything the app sends here, with
three switches each: **Send**, and whether people may have it by **Email** and
by **Push**. Click a notification to open its words.

**Words and Rules** lists every notification One sends, with the app that
sends it and who gets it. For example, a file shared with you, a letter
requested from HR, or a document OneAI flags as phishing. Each has these
badges:

- **Off**: it isn't sent.
- **Edited**: its text was changed.
- **Email** and **Push**: it can also be sent that way. Blue means new people
  start with it on, which the app sending it decides.
- **External Email**: it goes to an address outside the workspace, such as a
  file request email.

Mentions, assignments and shares are the system's built-in notifications,
listed at the bottom. Their text is built in, so it can't be changed here.

OneAI offers:

- **Rewrite this notification**: new text as a card, using only the names allowed. Approving saves it, and the
  open page shows the new text.
- **Which should be emailed?** Which notifications are worth an email and
  which are better left in One.
- **Make a rule**: asks what should happen and who should be notified, then
  suggests the rule.
- **How do notifications work?** An explanation of this page.

## What the Apps Send

Notifications the products send are listed under their product, in one of
three ways:

- **Sent through One**, like any other notification. For example, a leave or
  expense to approve, a birthday, an upcoming interview, a credit limit
  exceeded, or a material request from reordering. Their switches in HR
  Settings and Stock Settings are gone, because **Send This** here controls
  them.
- **Sent through One in the product's own words**: the product's built-in
  rules, such as Training Scheduled or New Fiscal Year. You can change their
  channels but not their text.
- **Sent by OneHR**, **Sent by OneBook** and so on: emails the product
  sends itself, such as payslips, campaign emails, customer statements and the
  reports nightly jobs send when something fails. They're listed so nothing the
  workspace sends is hidden. The payslip's **Send This** is the same setting
  as in Payroll Settings. The others are always sent.

## Changing the Words

In NotificationCenter's **Words and Rules**:

Click a notification to open it, and save from the top right.

- **Send This** turns it off for everyone. The code for opening a shared link
  can't be turned off, or no one could open shared links.
- **Message** is the subject and message. A name in `{{ }}`, such as
  `{{ who }}`, is filled in when it's sent, and shown in bold in the subject.
  The page lists the names each notification can use, and won't save text
  with any other name. The preview shows the text as it will read.
- The default text is sent in each person's language. Once you edit it, your
  text is sent to everyone as written. **Reset to Default** restores
  the default, which is translated again.
- **Channels**: notifications in One are always on. **Email Allowed** and
  **Push Allowed** let people also get it by email or push. Whether new
  people start with it on is the app's to say, and for a workspace rule,
  everybody starts with what is allowed. Turning a channel off stops it for
  everyone, including people who chose it. Turning it back on gives it to
  everyone again if new people start with it on. Each person changes their
  own in NotificationCenter.

## Your Own Rules

Rules are notifications the workspace makes itself. When something happens to
a record type, they notify someone. They're at the top of the page. Click
**New Rule** and fill in:

1. **Name**: how people recognise it when choosing how to get it.
2. **Trigger**: the record type, which must be one you can open, and when the
   rule runs. That's when a record is created, saved, submitted or cancelled,
   a number of days before or after one of its dates, or when one of its
   fields changes. **Conditions** limits it to records matching conditions,
   such as a status or an amount.
3. **Recipients**: people with a role, a person named on the record (its
   creator, or a field such as Allocated To) and whoever it's assigned to.
   Only people who can open the record are notified, whatever the rule says.
4. **Message**: a subject and a message. `{{ doc.field }}` inserts a
   field of the record, such as `{{ doc.customer_name }}`. Nothing else can be
   used.
5. **Channels**, as for any notification. The rule is then listed in
   NotificationCenter with the others, so each person can choose how they get it.

**Delete** removes a rule for good. With **Make a rule** in the OneAI
panel, you describe the rule in your own words ("tell the
account manager when an invoice is seven days overdue"). OneAI suggests it as
a card, and nothing is created until you approve it.
