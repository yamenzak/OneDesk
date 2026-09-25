# The passover

Every screen of One, one at a time, checked against eight points. You decide when
a screen is done and when the next one starts. This file is where each screen's
findings and fixes are written down.

## The eight points

1. **Notifications and email templates**: what the screen's events send, to
   whom, and whether the message reads well.
2. **OneAI**: what OneAI does here, or should.
3. **Intake**: whether what Intake reads lands here, or should.
4. **Permissions and roles**: who sees the screen, who may change what, and
   whether the server holds that line.
5. **Cross-module**: where this screen meets the other modules, for example
   OneCRM and OneBook's accounts.
6. **Bespoke UI**: the product has its own look, as OneMail and OneCloud do,
   rather than a standard desk. It still uses frappe-ui and espresso parts.
   Nothing looks boxed in: sections sit on the page, and Save goes in the page
   head.
7. **Documented, and OneAI knows it**:
   - The screen has its section in its module's `README.md`, above
     `## Under the hood`, written for the people using it: what it is for, how
     to fill it in, and who sees and changes what.
   - OneAI answers "how do I…" from that section (`how_to`).
   - The panel knows which screen the reader is on, and what records that
     means.
   - It offers the screen's own suggestions, if the screen has any worth
     offering.
8. **Legal**:
   - Whatever the screen does that the agreements must say is declared in its
     module's `legal.py`, beside the code:
     - a `clause()` for the Privacy Policy, the Terms, the Data Processing
       Addendum or the AI Addendum;
     - a `subprocessor()` for any company it sends data to.
   - OneLegal assembles them into the documents people agree to
     (`one_legal/README.md`).
   - A changed clause fails `tests/test_legal.py` until it is either a new
     revision (material, so everybody agrees again) or a recorded hash (a
     typo).

## Everything follows frappe

This applies to every screen, on top of the eight points. How a screen looks can
be ours; how it behaves is frappe's.

- **Fields** are frappe's own controls (`frappe.ui.FieldGroup`, or the desk
  form itself), never inputs drawn by hand. They carry frappe's Link search,
  date picker, validation and translation.
- **A record being edited** acts like a desk form:
  - It knows it is dirty by comparing against what was loaded, and it is clean
    again when a change is undone.
  - It warns before the page is left with unsaved changes.
  - It saves against the `modified` it loaded, so a change made elsewhere in
    the meantime is refused, not silently overwritten.
  - It listens on the record's realtime room (`doc_subscribe`, `doc_update`)
    and says when somebody else has changed it.
- **What a screen shows** changes live through `frappe.realtime` when the data
  under it changes, the way the desk's lists do.
- Where frappe already ships the behaviour, the screen uses it rather than a
  copy of it.
- **What a part looks like comes from frappe-ui.** The desk's espresso parts
  (`frappe.ui.button`, `alert`, `badge` and so on) are frappe-ui's design,
  ported to plain HTML, and the port is sometimes behind or simpler. Before
  using one, open the same component in frappe-ui
  (`node_modules/frappe-ui/src/components/<Name>/`: the `.vue`, its `.md` and
  its stories). Where the two differ, in layout, variant, size or colour,
  follow frappe-ui. For example, frappe-ui draws an alert with one action as
  one row, and espresso put the button on a line of its own. The desk part
  stays; only its look is brought in line. Behaviour is still frappe's.

## How one screen goes

1. Screenshot it and read the code behind it.
2. Write the findings under the eight points below.
3. Fix them, look again in the browser, and run the gates.
4. Commit, push, and show you a screenshot.
5. Wait for your word before the next screen.

## Where we are

| Area | Screen | State |
|---|---|---|
| Settings, You | Profile | done |
| Settings, You | Notifications | done (stage 3 of NOTIFICATIONS.md; push is stage 4) |
| Settings, You | Mail | |
| Settings, You | Calendar | |
| Settings, You | Sign-in | |
| Settings, You | What OneAI Remembers | |
| Settings, You | Agreements | done |
| Settings, Workspace | General | |
| Settings, Workspace | People | |
| Settings, Workspace | Notifications | done (stages 2 and 5 of NOTIFICATIONS.md) |
| Settings, Workspace | Plan and Credits | |
| Settings, Workspace | Domains | |
| Settings, Workspace | OneAI | |
| Settings, Workspace | Intake | |
| Settings, Workspace | Holidays | |
| Products | One home, OneMail, OneCloud, OneCalendar, OneTask, OneProject, OneCRM, OneBook, OneInventory, OneHR, OneAI, Intake, OneAdmin | each screen listed here once we reach it |

Noticed along the way, for the screen it belongs to:

- **Sign-in**: says "288 sessions" for the administrator. That counts every
  session ever left open, not the devices a person uses.

## Settings

Every settings screen, from the first commit of the pass:

- The sections are entries in One's own sidebar, so there is no second sidebar
  inside the page.
- No bordered card. Parts of a section are divided by a rule.
- Save is the page's primary action in the head, so Ctrl+S works. "Not Saved"
  shows once something changes.
- The breadcrumb names the section.
- A section is a column in the middle of the page, the form's width, so a wide
  screen leaves room on both sides rather than all of it on the right. A
  section that is a table (People) gets the width a table needs.

### Profile

1. **Notifications**: nothing is sent when a person changes their own details.
   The employee record keeps the change in its history, where HR sees it.
   Whether HR should also be told about a new address or emergency contact is
   open.
2. **OneAI**:
   - Before, the panel knew nothing on any Settings page. `oneai.where()` only
     recognised records, lists and reports, so it offered nothing and told the
     model nothing.
   - Now a desk page tells the panel the page and the open section, and the
     panel follows the reader between sections.
   - On Profile the model is told that it is the reader's own User record and,
     when they have one, their own Employee record. It is told what they may
     change and that job and bank are HR's.
   - Two suggestions:
     - **What is missing from my profile?** reads both records.
     - **How do I fill this in?** answers from the README.
   - Letting OneAI make a change itself ("I moved, update my address") is not
     offered. `edit_record` would need write permission on Employee, which the
     Employee role does not have.
3. **Intake**: nothing yet. Later, a proof of address that Intake reads could
   offer to update the address here.
4. **Permissions**:
   - "About You" said only HR sees marital status and blood group. The person
     sees them too, so it now says "Only you and HR see these".
   - A person changes their own login, and only the Profile fields.
   - On their employee record they may change how to reach them, the emergency
     contact, marital status and blood group. That record is only ever the one
     whose `user_id` is theirs.
   - Their job and their bank account are shown but never written, and the
     account shows only its last four characters.
   - `tests/test_settings.py` holds this.
5. **Cross-module**: gender, birth date, mobile and photo are on both the login
   and the employee. erpnext copies the employee's values onto the login every
   time the employee is saved. So those four are written to the employee as
   well, or HR's next save would undo the person's change. A department shows
   by its name, without the company's abbreviation.
6. **UI**: a Page of our own (`one/page/settings`), drawn by
   `public/js/settings.js`. It is not frappe's User form with CSS laid over
   it. The fields are frappe's controls in a `FieldGroup`, so they behave as on
   any form.
   - It follows "Everything follows frappe" the way a desk form does, from
     `form.js` and `model.js`:
     - Dirty is a difference from what was loaded, so undoing a change makes it
       clean again.
     - Leaving with changes gets frappe's own warning. Like frappe, it is off
       in developer mode.
     - Switching sections keeps unsaved changes, as frappe keeps an unsaved
       document in `locals`.
     - Save sends each record's `modified`, and frappe's `check_if_latest`
       refuses a stale save with its own message. The page then offers
       Refresh.
     - That warning is frappe-ui's row alert, from `Alert.vue`: the title
       and one action on one line, the action a ghost button in the alert's
       amber. Neither button library has an amber button (espresso: gray and
       red; frappe-ui: gray, blue, green and red). The colour belongs to the
       alert.
     - Both records' realtime rooms are subscribed. Untouched, the page reloads
       when somebody else saves. With changes in it, it says "This form has
       been modified after you have loaded it" and keeps them.
     - Ctrl+S saves. On a page that is `save_action`, not the button, which is
       why it did nothing before.
     - Every field is sent. `FieldGroup.get_values` leaves an empty field out,
       so a field somebody cleared was never cleared.
   - The photo is the avatar, at 80px. Espresso's largest size is 3xl, which
     is 46px, so the page sets the avatar's own size variable instead of
     drawing its own.
   - Clicking the photo opens frappe's upload dialog: My Device, Link, Camera
     and OneCloud.
   - Fields sit side by side, as on a record.
   - A person who is an employee also sees:
     - At Work (read-only)
     - Where You Live
     - In an Emergency
     - About You
     - Where Your Pay Goes (read-only)
7. **Documented**:
   - One had no README, so OneAI could not answer any question about Settings.
   - `one/README.md` now has Finding your way, Settings (how saving works, and
     what happens when somebody else changes the same thing), Settings ›
     Profile, and Asking OneAI.
   - Each Settings screen adds its own section as the pass reaches it.
   - Checked on the site: "how do I change my bank account", "how do I change
     my photo" and "who sees my blood group" each find One › Settings ›
     Profile first.
8. **Legal**: added when OneLegal was founded, after Profile was otherwise
   done.
   - Privacy Policy, `profile-employee`: what the profile holds, what the
     employee record adds, and who sees which.
   - Data Processing Addendum, `profile-special`: a blood group is a special
     category of personal data, and an emergency contact is personal data
     about somebody who is not a user. The organisation decides whether to
     collect them and needs a lawful basis to.

### Agreements

Built during the pass, right after OneLegal, so a person can see what they
agreed to. The Terms already promise that.

1. **Notifications**: nothing is sent. A new revision is asked for at the next
   sign-in. Whether administrators should also be told by mail when their
   organisation's agreements change is open.
2. **OneAI**:
   - A new read tool, `agreement`, returns a document's actual text, so OneAI
     answers from what was agreed, not from what such documents usually say.
     It sits in `one_legal/ai.py` and is registered in `one_ai_reads`.
   - The panel is told the reader is on Agreements.
   - It offers **What have I agreed to?** and **Who else sees my data?**, both
     expecting the tool.
3. **Intake**: nothing here.
4. **Permissions**:
   - Everybody sees their own acceptances, and the organisation's with who
     agreed and when, since they are bound by them.
   - Only administrators get **Everybody's Agreements**, the Legal Acceptance
     list, whose doctype only they may read.
5. **Cross-module**:
   - The section reads the rows OneLegal's gate writes, not a copy.
   - **Agree Now** opens the same dialog as sign-in. Agreeing there redraws
     the section (`legal-agreed`).
6. **UI**:
   - Three parts: Yours, Your Organisation's, Published.
   - Each document has a badge (Agreed, Not agreed yet, Updated since) and
     when, or by whom and when.
   - A changed document links to the exact text that was agreed.
   - It is read-only, so there is no form and no Save.
7. **Documented**: One's README has Settings › Agreements, and a test holds
   that a section OneAI offers anything on has its README section.
8. **Legal**: no new lines. The Terms' "every version anybody agreed to is kept
   and can be read in One" is now true of a screen.

### Notifications

Stage 3 of `docs/NOTIFICATIONS.md`. What was here were frappe's older
per-kind checkboxes (Mentions, Assignments, Document Share), which v17 hides
because they no longer decide anything: frappe mails a person the types in
their `email_notification_types`, and nothing on this screen wrote that.

1. **Notifications**: this screen is each person's half of the hub. Every kind
   reaches the bell; a tick per kind says whether it is also mailed, and it
   writes frappe's own `email_notification_types`, so frappe's mailing honours
   it with nothing of ours in between. Saving sends nothing.
2. **OneAI**:
   - A read tool, `my_notifications`, returns the kinds the reader can receive
     and which they get by email. It reads their own settings only.
   - The panel is told the reader is on their own Notifications.
   - It offers **What will I be told about?** and **Too many emails?**. Both
     advise; the person ticks and saves.
3. **Intake**: six kinds are Intake's (waiting, the weekly digest, a new IBAN,
   phishing and two more), chosen here like any other.
4. **Permissions**:
   - A person's own Notification Settings, and only theirs.
   - A kind declared for some roles (`roles` in a module's
     `notifications.py`) is shown only to people holding one: HR's kinds are
     for HR. A kind not shown is left as it was on save.
   - A kind the workspace does not mail is shown and cannot be ticked, with the
     reason. The project update, whose mail is always sent so people can
     reply, is shown ticked and fixed.
5. **Cross-module**: every module's kinds in one list, grouped by app, with
   frappe's own (mentions, assignments, shares) as Across One. Energy points
   left frappe with gamification, and frappe's Alert never mails, so neither is
   listed. Workspace › Notifications shows the always-mailed kind as Always
   Mailed.
6. **UI**:
   - Notifications and Also by Email first, then a part per app with a tick per
     kind and a sentence on when it is sent, then Other Mail (event reminders,
     mails on a record assigned to you).
   - Turning either switch off hides the ticks it makes meaningless.
   - Found doing it: frappe marks a section empty while a FieldGroup draws it,
     before its values are in, and never looks again, so a section whose
     fields have `depends_on` stayed hidden. `form()` now re-checks sections
     once the values are in and on every change, for every Settings section.
   - `form()` gains `{ stack }`, fields one under another in one part, so a
     list of ticks is not a section each.
7. **Documented**: One's README has Settings › Notifications.
8. **Legal**: the Privacy Policy gains `notifications`: the bell keeps a record
   of every notification, mail per kind is the person's choice within what the
   workspace allows, and the workspace's administrators decide what each says.
   Recorded as a clarification (new hash): the records existed and the policy
   already covered what the workspace holds. Frappe keeps notification records
   until a workspace clears them, so no period is promised.

### Push (Notifications, stage 4)

Stage 4 of `docs/NOTIFICATIONS.md`, on both Notifications screens.

1. **Notifications**: a Notification Log is pushed, after it is committed and
   in the background, to every browser its person turned push on in, when they
   ticked push for its type and the workspace allows push for it. A browser the
   push service says is gone is forgotten; so is one that fails five times in a
   row.
2. **OneAI**: `my_notifications` now says, per kind, whether it is pushed, and
   in how many browsers push is on. **Too many emails?** may suggest push
   instead of mail.
3. **Intake**: phishing, a new IBAN and what waits start pushed for a new
   person; the weekly digest does not.
4. **Permissions**:
   - A person registers, lists and removes only their own browsers; Push Device
     has no desk permissions at all.
   - A push goes only to Google's, Mozilla's, Apple's or Microsoft's push
     service, over https (`push.SERVICES`): the address comes from a browser,
     and a server that posts wherever a browser says is one anybody can aim.
   - The VAPID private key is in the site's config, never the database.
   - The worker is served for the whole site, and handles push and clicks
     only; a test holds that it has no fetch handler.
5. **Cross-module**: every module's types can be pushed as they can be
   mailed; frappe's mentions, assignments and shares too.
6. **UI**:
   - You › Notifications: a Push part at the top (on, off, blocked, or
     unsupported in this browser; Turn On Push, Send a Test, Turn Off; the
     other browsers with Remove), and each kind a row with Email and Push.
   - Workspace › Notifications: Push Allowed and Push for New People, and a
     Push badge in the list.
   - Found: headless Chromium is incognito and has no push, so turning it on
     cannot be seen here. The whole path was checked instead against a local
     push service: the push arrived VAPID-signed and aes128gcm-encrypted, and
     decrypted with the browser's key to the notification's text.
7. **Documented**: One's README, both Notifications sections.
8. **Legal**: the Privacy Policy gains `push` (what is kept about a browser,
   and that the push services carry messages they cannot read) and goes to
   revision 2, so everybody is asked again: push is a new thing kept about a
   person, not a clarification. The push services are named, not listed as
   subprocessors, since they are the browser's own and never see content.

### Workspace › Notifications

Built as stage 2 of `docs/NOTIFICATIONS.md`, and gone over against the eight
points as it was built.

1. **Notifications**: this is where every one of them is decided. Saving sends
   nothing. Turning email off takes the type out of everybody's email choices,
   because frappe would otherwise keep mailing whoever had chosen it; turning
   it back on gives it to everybody if it is on for new people. A new person
   now starts on email only for the types marked for new people (frappe
   started them on every type).
2. **OneAI**:
   - Two tools in `one/ai.py`: `notification_type` reads a type's text, slots
     and channels, and `rewrite_notification` suggests new text as a card,
     refused if it names anything but the type's slots. Applying the card is an
     ordinary save, by the administrator.
   - The panel is told the page and which type is open (`record` in
     `oneai.where()`).
   - It offers **Rewrite this notification**, **Which should be emailed?** and
     **How do notifications work?**. The editor's **Rewrite with OneAI** asks
     the first about the type that is open.
3. **Intake**: six of the types are Intake's, listed and edited here like any
   other.
4. **Permissions**:
   - Only workspace administrators see the section; `load`, `save` and
     `preview_notification` all ask `roles.require()`.
   - The Workspace Administrator gets read and write on Notification Type
     (Custom DocPerm), so OneAI's card applies as them.
   - An edited text is rendered in a Jinja sandbox with nothing but its slots.
     Frappe's own `render_template` would have handed it `frappe.db`, and so
     any record in the workspace. Saving a text that names anything else is
     refused, from the page, from a card, or from the desk.
   - The shared link's code cannot be turned off.
5. **Cross-module**: every module's types in one list, grouped by the app that
   sends them, with frappe's own (mentions, assignments, shares) at the
   bottom, read-only, since their text is frappe's.
6. **UI**:
   - The list is rows on the page, grouped by app, each a link with a
     frappe-ui list-row hover: its name, what it is about, and badges for Off,
     Edited, and Email (blue when on for new people) or Mailed Outside.
   - A type opens as a form: Send This, What It Says (subject as one line,
     message as a small code field), the names it may use, a live preview with
     each name as a chip where its value goes and the refusal in red, then
     Channels. Save is in the page head; it is dirty against what loaded, warns
     before leaving, saves against `modified`, and reloads on `doc_update`.
   - Subjects no longer carry `<b>`: every name in a subject is bolded when it
     is sent, so neither our text nor an administrator's has to say so.
   - Push is declared on every type but not shown until it can be sent
     (stage 4).
7. **Documented**: One's README has Notifications, for the Workspace, which is
   what `how_to` answers from.
8. **Legal**: the Acceptable Use Policy gains `notification-text`: what an
   administrator writes into a notification is the workspace's content, sent
   in its name, including to outside addresses. Recorded as a clarification
   (new hash, same revision): the policy already covered what a workspace
   sends.
   - Found doing it: the gate asked everybody again on a new hash, although
     OneLegal's README says only a new revision does. It now compares
     revisions (`gate.agreed`), and the Agreements page shows a clarified
     document as still Agreed, with a link to the text that was agreed.

### Rules (Notifications, stage 5)

Stage 5 of `docs/NOTIFICATIONS.md`: the workspace's own notifications, on
Workspace › Notifications.

1. **Notifications**: a rule is frappe's Notification, sent to the bell under
   a type of its own, so it is mailed or pushed as each person chose. It tells
   only the people who may read the record.
2. **OneAI**: `draft_notification` drafts a rule as a card, refused when its
   text names anything but the record's fields or its event is not one of the
   seven. The page offers **Make a rule**, and the Rules part has **Ask OneAI
   for One**.
3. **Intake**: nothing of its own. A rule may watch Intake's records like any
   other the administrator can read.
4. **Permissions**:
   - The Workspace Administrator gets Notification (Custom DocPerm), and a rule
     they save is held in the controller (`rules._hold`), so the desk is no way
     round the screen.
   - Frappe renders a Notification's text with its full globals and runs its
     conditions as Python, because only its own administrators may write one.
     A workspace rule has filters for a condition and text that names only
     `{{ doc.field }}`; a rule made on the desk by a workspace administrator
     with Python in it is refused.
   - Recipients: by role, by a person field of the record, or its assignees;
     no copies, no addresses, no conditions. At send time the list is cut to
     people who can read that record.
   - A rule may watch only a kind of record its author can read.
5. **Cross-module**: a rule can watch any module's records, so this is where a
   workspace says "tell the managers about a new expense claim" without a line
   of code. Its person fields come from the record (Allocated To, Assigned By).
6. **UI**:
   - The list gains a Rules part above the types: each rule a row saying when
     it fires, with New Rule and Ask OneAI for One.
   - A rule is a form: the kind of record (a Link that searches translated
     names; frappe's own query cut at two hundred names and found nothing),
     when, the date or field that goes with it, frappe's filter editor for
     "only when", who is told, the text with a preview, and channels. Save in
     the page head against `modified`; Delete asks first. A new rule moves to
     its own address once saved.
   - Found: frappe's default message for a new Notification ("Add your message
     here") was prefilled into the form; a new rule now starts empty.
   - Found: a rule could be saved telling nobody (frappe allows it, and the
     sample rule was one). It is now refused until it names a role, a person
     on the record, or its assignees.
7. **Documented**: One's README, Notifications for the Workspace, has Rules.
8. **Legal**: the Acceptable Use Policy's `notification-text` now names rules
   as the workspace's own content. A clarification (1.cc05bbc3), not a new
   revision: what a workspace sends was already its own.

### What erpnext and hrms send (Notifications, stage 6)

Stage 6 of `docs/NOTIFICATIONS.md`, done at once so both Notifications
screens are whole before the passover comes back to them.

1. **Notifications**: every mail erpnext and hrms send is now a type on
   Workspace › Notifications. Seventeen are told through the hub, four
   standard rules are carried to the bell in their own words, and nine are
   still mailed by the app and listed as such. The table in NOTIFICATIONS.md
   says which is which and why.
2. **OneAI**: `notification_type` says whose words a type is in; a type in
   erpnext's or hrms's words is refused by `rewrite_notification`.
3. **Intake**: nothing of its own here.
4. **Permissions**: nothing new to grant. An approval goes to the approver
   HRMS names, a reminder to the employees of the same company, and a
   carried rule only to the people it names who are in the workspace.
5. **Cross-module**: OneHR, OneBook, OneInventory, OneCRM and OneProject now
   each declare what they send. HR Settings loses its reminder, leave and
   interview mail switches and templates, and Stock Settings its reorder mail
   switch, because Send This decides now. OneHR's two leave Email Templates
   went with them.
6. **UI**:
   - A type in an app's words shows its channels and says whose words they
     are; it has no text to edit and no Rewrite button.
   - A type mailed by the app shows **Mailed by ERPNext** or **Mailed by
     HRMS** in the list, and opens to Send This and a line saying so. Where
     the app has no switch, Send This cannot be turned off.
   - Found: a "What It Says" heading with nothing under it was hidden by the
     form, taking its note with it. The note is a plain line now.
7. **Documented**: One's README, Notifications for the Workspace, names the
   three kinds.
8. **Legal**: nothing new. Nothing is sent to anybody new or through anybody
   new; only which door it goes through changed.

## OneLegal

Founded during the pass, so that each screen can add its lines as the pass
reaches it (point 8). `one_legal/README.md` is the reference.

- **Ported from OneApp's `onelegal`**:
  - the registry, the eight documents and `revision.hash` versions;
  - the two parties (the organisation, agreed by an administrator; the
    person, agreed by each person);
  - Legal Acceptance and Legal Document Version.
- **The desk's own parts**:
  - A dialog that cannot be closed asks when the desk starts. The documents
    open on the Agreements page (`/app/legal`), which is never behind the
    dialog.
  - Only a Workspace Administrator agrees for the organisation. A person
    whose workspace has not agreed yet is told so, rather than shown a button
    that would refuse them.
- **The text is OneDesk's, not OneApp's**:
  - Intake acts without being asked each time, and the AI Addendum says so.
  - The lifecycle's periods are read from `one_admin/ladder.py`.
  - Nothing is promised that is not built.
- **Every company One calls is declared**, and `tests/test_legal.py` fails on a
  new outside host that is not:
  - Cloudflare (R2, AI Gateway and Workers AI, sending mail);
  - Google (Gemini, and the favicon lookup);
  - Automattic (Gravatar, by a hash of the address);
  - Stripe;
  - Frappe (Frappe Cloud).
  - Gravatar and the favicon lookup were in no document before.
- **Not yet built**, for the screens they belong to:
  - an Agreements section in Settings showing what you and the workspace
    agreed to, and when;
  - asking at sign-up, before the workspace exists;
  - `gate.require()` on turning an application on.
