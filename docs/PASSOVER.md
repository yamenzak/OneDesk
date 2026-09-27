# The passover

Every screen of One, one at a time, checked against nine points. You decide when
a screen is done and when the next one starts. This file is where each screen's
findings and fixes are written down.

## The nine points

1. **Notifications and email templates**: what the screen's events send, to
   whom, and whether the message reads well.
2. **OneAI**: what OneAI does here, or should. Whatever is AI on the screen
   is drawn one way: something OneAI does or did is `onedesk.oneai.tag`
   ("Read by OneAI"), and something that asks it is `onedesk.oneai.button`,
   which opens the panel on the same question the page's suggestion asks.
   Both are frappe's own badge and button with OneAI's mark and spectrum
   (`oneai.css`). A violet badge or a plain button standing in for one is a
   finding.
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
9. **Built from frappe, in this order**: every part of the screen is taken
   from the first of these that has it, and only written by us when none does:
   1. a **frappe-ui component** (`node_modules/frappe-ui/src/components/`);
   2. the **desk's own parts**: its controls, `FieldGroup`, `FilterGroup`,
      list and form views, dialogs, and espresso's `frappe.ui.button`,
      `badge` and `alert`, looking the way frappe-ui draws them;
   3. frappe's **primitives and utilities**: `frappe.call`/`xcall`,
      `frappe.realtime`, `frappe.utils`, `frappe.format`, `__()`, the model
      and the router.

## Everything follows frappe

This applies to every screen, on top of the nine points. How a screen looks can
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

## A record answers first

On top of the nine points, every record screen is checked against the record
shell (`docs/SHELL.md`), which is how One looks now and what the pass enforces:

- **Its head answers what somebody opened it for**, above the fields and on
  every tab: where it stands (the pill), one sentence when there is news, a
  band of metric cards (a value, a meter for a part of a whole, a change
  against the period before), a chart only where the trend is the question,
  and its verbs, each asking in frappe's own dialog, with at most one
  primary. A record with nothing worth saying there gets no head; one that
  has something gets a Record Head in its module's `heads.py`.
- **No form script draws a head.** A pill, a headline, a band or a progress
  bar set from a script is refused by `tests/test_head.py`, headed doctype or
  not. A script keeps only what is not a head: a dialog that answers inside
  itself, a sidebar action, a field's options.
- **A sentence that reads a field the form changes redraws as it changes**
  (`redraw_on`), so a new record says what it will do before it is saved.
- **Another record's fields are edited in place**, as a Linked Section,
  rather than by opening the other record.
- **Mail, Files and Activity are the record's own tabs** (`one_record_tabs`),
  not links out.
- **A workspace administrator shapes it from the form's menu** (Customize),
  and OneAI proposes a change through the same door. Nothing a workspace
  does is code.
- **Lists stay frappe's list.** No stat strip above one; numbers belong on a
  record's head or a dashboard.

## How one screen goes

1. Screenshot it and read the code behind it.
2. Write the findings under the nine points, then "A record answers first"
   for a record screen, then anything else about using it (UX).
3. Fix them, look again in the browser, and run the gates.
4. Commit, push, and show you a screenshot.
5. Wait for your word before the next screen.

## Where we are

| Area | Screen | State |
|---|---|---|
| Settings, You | Profile | done (second pass too) |
| Settings, You | Notifications | done, second pass |
| Settings, You | Mail | done |
| Settings, You | Calendar | done |
| Settings, You | Sign-in | done |
| Settings, You | What OneAI Remembers | done |
| Settings, You | Agreements | done |
| Settings, Workspace | General | done |
| Settings, Workspace | People | |
| Settings, Workspace | Notifications | done (stages 2 and 5 of NOTIFICATIONS.md) |
| Settings, Workspace | Plan and Credits | |
| Settings, Workspace | Domains | |
| Settings, Workspace | OneAI | |
| Settings, Workspace | OneIntake | |
| Settings, Workspace | Holidays | |
| Products | One home, OneMail, OneCloud, OneCalendar, OneTask, OneProject, OneCRM, OneBook, OneInventory, OneHR, OneAI, OneIntake, OneAdmin | each screen listed here once we reach it |

Noticed along the way, for the screen it belongs to:

- **Sign-in**: says "288 sessions" for the administrator. That counts every
  session ever left open, not the devices a person uses.

## Settings

Every settings screen, from the first commit of the pass:

- The sections are entries in One's own sidebar, so there is no second sidebar
  inside the page.
- No bordered card. Parts of a section are divided by a rule.
- Save is the page's primary action in the head, so Ctrl+S works. "Not Saved"
  shows once something changes. A section with nothing to save puts its one
  action there instead (Mail's Connect a Mailbox), never as a button in the
  page.
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

#### Profile, second pass

Against what the pass learned since: the OneAI tag and button, one action in
the page head, product names, and UX. All of it done, on your word.

1. **Notifications**: the question left open is worth a yes. HR relies on an
   emergency contact and an address being right, and learns of a change only
   by opening the record. Recommended: one notice to HR when a person
   changes their addresses or emergency contact, saying what changed.
2. **OneAI**: the panel offers its two suggestions, but nothing on the page
   says OneAI can help. Recommended: a OneAI button under the name, **Check
   My Profile**, asking the existing "What is missing?" question; and one
   under Bio, **Write It With OneAI**, as records have on a prose field.
3. **Intake**: still nothing; a proof of address offering to update the
   address stays a later idea.
4. **Permissions**: hold as the first pass left them.
5. **Cross-module**: nothing new.
6. **UI and UX**:
   - An emergency contact can be half filled: this one has a relation
     (Sister) and no name or phone, and saves without a word. Recommended:
     once any of the three is filled, a name and a phone are asked for.
   - The photo's placeholder shows "S" where the rail shows "SA".
     Recommended: both initials, as frappe's own avatar gives them.
   - "Mobile No" is frappe's label. Recommended: "Mobile".
   - Save is in the head, the page's one action. Nothing to change.
7. **Documented**: the Profile section of `one/README.md` gains whatever of
   the above is done.
8. **Legal**: nothing new.
9. **Built from frappe**: nothing new.

Done:

- **Employee Details Changed** (`one_hr/notifications.py`): HR Managers are
  told, once per save, when a person changes their current or permanent
  address or their emergency contact, with what changed ("current address
  and emergency contact"). Not the person themselves, and not the bench's
  own account.
- **An emergency contact is whole or empty**: once a name, relation or phone
  is filled, a name and a phone are required, on the server.
- **Check My Profile** under the name and **Write It With OneAI** under Bio,
  both OneAI buttons; the second is a new suggestion, Write My Bio, which
  comes back as an edit card to approve.
- **Both initials** in the photo's placeholder, as the rail says them.
- **Mobile**, not "Mobile No".
- `one/README.md`'s Profile section says all of it.

### Mail

Lists the reader's mailboxes (`holders.mailboxes`): the workspace's, their
own address on the mail domain, and any they connected. Each opens in
OneMail; one that sends has a Signature button (frappe's Text Editor in a
Dialog, `holders.set_signature`). Connect a Mailbox goes to OneMail.

Findings, and what was done about each (all of them, on your word; the
list stays a list, since three rows with actions read better than cards).

1. **Notifications**: a mailbox that stops being reachable says nothing to
   anybody. `sync.py` writes `one_error` and stops; the only sign is a red
   badge here and in OneMail. Recommended: one notice to its holders when it
   breaks, through the hub, with a way to reconnect, and none on every
   failed sync after that.
2. **OneAI**: the panel knows the section (`page:settings/mail`) and has no
   suggestion for it. Recommended: "Write my signature", from the profile
   (name, designation, phone, company), into the same dialog to check
   before saving.
3. **Intake**: nothing to add. The badge says which mailbox Intake reads;
   choosing one is Workspace › Intake.
4. **Permissions**: anybody who holds the workspace's mailbox can change the
   signature everybody sends under. By design (`set_signature`), but worth a
   decision: keep it, or keep a shared mailbox's signature to Workspace
   Administrators.
5. **Cross-module**: OneMail owns the mailboxes; this reads them and opens
   them there. Nothing to add.
6. **Bespoke UI and UX**:
   - What you sign with is behind a button. Recommended: the signature's
     first line on the row, or "No signature".
   - A personal address on the mail domain receives only, so it has no
     Signature button and nothing says why. Recommended: "Receives only".
   - A mailbox that is not reachable shows a red badge whose reason is in a
     hover title. Recommended: the reason on the row, and Reconnect.
   - The list does not change when a mailbox breaks or recovers until the
     page is opened again. Recommended: redraw on the sync's realtime event.
7. **Documented**: `one/README.md` has no Mail section, so OneAI cannot
   answer "how do I change my signature". Recommended: write it.
8. **Legal**: `one_mail/legal.py` already declares connected mailboxes
   (`onemail-mailboxes`) and the mail carrier. Nothing to add.
9. **Built from frappe**: the dialog is frappe's, the rows and buttons are
   the settings shell's (espresso buttons and badges). Nothing to change.

Done:

- **Mailbox Not Reachable** (`one_mail/notifications.py`): when a sync first
  fails, everybody who holds the mailbox is told, on the bell and by email,
  with the reason and a link here. Only the first failure sends, so a
  mailbox that stays broken is one notice.
- **Reconnect** on a mailbox that is not connecting: its password again
  (`connect.reconnect`), tried on the servers it already has before it is
  kept, then read at once. A holder may; a workspace mailbox, an
  administrator.
- **Each row says what it signs with** ("Signs with …" or "No signature"),
  **Receives Only** on a personal address on the mail domain, and a mailbox
  that is not connecting says why on the row, in red, beside Reconnect.
- **The page redraws** when a mailbox breaks or comes back (`one_mailbox`,
  published by `sync.py` to its holders).
- **A workspace mailbox is signed by its administrators** (`holders.may_sign`),
  held on the server in `set_signature` and in OneMail's own menu.
- **Connect a Mailbox is the page's primary action**, in the head.
- **OneAI**: Write My Signature (`my_mailboxes` reads the mailboxes and what
  a signature is made of, `sign_mailbox` suggests one as a card, a new
  proposal kind `Signature` that Approve saves), Why Is a Mailbox Not
  Working, and How Does Mail Work Here, which reads the new Settings › Mail
  section of `one/README.md`.

### Calendar

The page is one section: the calendar link as a raw `webcal://` address in a
code box, Copy, Make a New Link and Turn the Link Off. Nothing is changed yet.

1. **Notifications**: nothing is sent, and nothing needs to be. The link is
   the person's own, made by them.
2. **OneAI**: the page has no suggestions and no page sentence, and the panel
   cannot answer "how do I get this on my phone?". Recommended: a OneAI button,
   **How Do I Add It?**, answering from the README for Google, Apple and
   Outlook.
3. **Intake**: nothing here.
4. **Permissions**: hold. The secret is stored encrypted and found by its
   hash, the feed is rate-limited per link, a disabled person's link stops,
   and it carries only what that person can see. Administrators switch
   anybody's link off under OneCalendar › Calendar Links.
5. **Cross-module**: OneCalendar's own **Subscribe** dialog already does this
   better: a button per app with its mark (Google Calendar, Apple Calendar,
   Outlook) that opens the app ready to add it, and Copy Link. The two
   disagree: different words ("New Link" and "Switch Off" there, "Make a New
   Link" and "Turn the Link Off" here), and Copy copies the `https://` link
   there and the `webcal://` one here. Recommended: one drawing of the link,
   used by both.
6. **UI and UX**:
   - A raw address nobody reads fills the page. Recommended: the three app
     buttons, as in Subscribe, with Copy Link for anything else.
   - Nothing says whether the link works. The feed records when an app last
     read it (`last_read`). Recommended: "Read by a calendar app 2 hours ago",
     or "No app has read it yet".
   - Nothing says what the link carries. Recommended: the layers it carries,
     named ("Your events, your tasks, holidays…").
   - No action in the page head, and with no link, **Make My Link** is a dark
     button in the page. Recommended: **Make My Link** in the head when there
     is none, **Copy Link** when there is; New Link and Switch Off stay quiet
     in the page.
   - For both ways with Google, frappe's own Google Calendar sync exists
     once an administrator has set Google up. Recommended: a row saying so,
     shown only when Google Settings is on, opening the person's own Google
     Calendar record.
7. **Documented**: Settings has no Calendar section in `one/README.md`.
   Recommended: one, pointing at OneCalendar's README for the rest.
8. **Legal**: the privacy notice does not say a person can publish their
   own calendar to another app through a private link, readable by whoever
   holds it. Recommended: a clause in OneCalendar's `legal.py` (which does
   not exist yet); a new processing purpose, so a new revision.
9. **Built from frappe**: the code box is ours. The app buttons are
   espresso's, as Subscribe draws them; frappe's `copy_to_clipboard` and
   `confirm` are used as they are.

Your word: all of them but the Google sync row (5), which leans on frappe's
own Google integration.

Done:

- **One drawing of the link** (`public/js/calendar_link.js`), used by
  Settings and by OneCalendar's Subscribe: the three app buttons with their
  marks, what it carries as badges, whether an app has read it, and New Link
  and Switch Off as quiet buttons, both asking first. Copy Link copies the
  `https://` address everywhere.
- **The page head's action** is Make My Link with no link, Copy Link with
  one; Settings leaves the in-page Copy Link out.
- `feed.mine` and `feed.renew` also return `carries` and `last_read`;
  `feed.current` reads the link without making one.
- **OneAI**: How Do I Add It? on the page and as its suggestion, and the
  panel is told what the page is.
- `one/README.md` gains Settings › Calendar.
- **Legal**: `one_calendar/legal.py` says a person may publish their
  calendar through a private link; the privacy notice is revision 3.

Then, on your word: **Calendar Links** under Workspace › General (a switch
on System Settings). Off, every link is deleted at once (`feed.switched`),
the feed refuses any link, Settings says the workspace does not allow them,
OneCalendar has no Subscribe, and OneAI says so. On again, nobody's old link
comes back. Found on the way and fixed:

- Opening your own calendar link while signed in signed you out: the feed's
  `frappe.set_user` rewrote the request's session, sid and all. It now reads
  as the link's owner and gives the request its own session back (`feed._as`).
- General could not be saved: System Settings' Time Zone arrived with no
  options, so it showed blank and saved blank (`settings._zones`).

### Sign-in

Three sections: Change Password (a dialog), the passkey for checking in with
a dark Register This Device, and "475 sessions, this one included" with Sign
Out Everywhere Else. Nothing is changed yet.

1. **Notifications**: changing the password here tells nobody. Frappe mails
   "Security Alert: Your password has been changed" only when a password is
   set on the User form, and straight through `frappe.sendmail`, outside the
   hub. Registering a passkey tells nobody either. Recommended: two kinds
   through the hub, **Password Changed** and **Passkey Added**, mailed to the
   person always (a security notice cannot be switched off), each saying
   when, from which device, and what to do if it was not them.
2. **OneAI**: no suggestions, no page sentence. Recommended: **Is My Account
   Safe?**, reading this page's facts (password age, passkey, how many places
   you are signed in, two-factor) and saying what to do.
3. **Intake**: nothing here.
4. **Permissions**: hold. Each action is the reader's own; Sign Out
   Everywhere Else keeps this session.
5. **Cross-module**: the passkey is OneHR's, for checking in, but when the
   workspace allows Login with Passkey (System Settings) the same passkey
   signs you in, and the page does not say so. Two-factor sign-in, where the
   workspace requires it, is not mentioned either. Recommended: the passkey
   section says what it is used for here (checking in, and signing in when
   allowed), and a line says whether two-factor is on for you.
6. **UI and UX**:
   - "475 sessions" is a number nobody can act on, and most are old. Frappe
     keeps each session's device (user agent), network address and last
     activity. Recommended: a list of where you are signed in, as "Chrome on
     Mac · 2 hours ago", this one marked, each with Sign Out, and Sign Out
     Everywhere Else kept for all of them.
   - Change Password does not offer to sign out elsewhere, which is what a
     person changing a leaked password wants. Recommended: a switch in the
     dialog, on by default.
   - Register This Device is a dark button in the page. Recommended: quiet;
     this page has nothing to save, so its head has no action.
7. **Documented**: no Sign-in section in `one/README.md`. Recommended: one.
8. **Legal**: holds. The privacy notice already covers sign-in records with
   time and network address, and passkeys.
9. **Built from frappe**: the password dialog is frappe's, with its Password
   controls and strength check. Signing out one session is frappe's
   `delete_session`.

Your word: all of them, reading what frappe already keeps rather than
keeping anything new.

Done (`one/signin.py`):

- **Where You Are Signed In** reads `tabSessions`: each session's user agent
  as "Chrome on Mac", its network address and when it was last used, this
  one marked, each with Sign Out (frappe's `delete_session`, so the Activity
  Log records it). The page names a session by a hash, never its id.
- **Recent Sign-ins** are the Activity Log's last six, failed ones in red.
- **Password** says when it last changed (User's
  `last_password_reset_date`); **Two-Factor Sign-in** says whether frappe asks
  this person for a code, and that the workspace decides it.
- **Passkey** says it also signs you in where Login with Passkey is on.
- **Change Password** has Sign Out Everywhere Else, on by default.
- **Password Changed** and **Passkey Added** go through the hub, always
  mailed. Frappe's `update_password` is overridden to tell the person after
  it, so the reset link tells them too.
- **OneAI**: Is My Account Safe? on the page and as its suggestion, read by
  `my_sign_in`.
- `one/README.md` gains Settings › Sign-in.

### What OneAI Remembers

One section: the facts OneAI keeps for this person (`AI Memory`, private to
them), each with Forget, or a large centred "Nothing yet." Nothing is
changed yet.

1. **Notifications**: nothing is sent, and nothing needs to be.
2. **OneAI**: the panel links here ("What OneAI remembers"), but the page
   has no OneAI part, and OneAI keeps a memory quietly: nothing in the
   conversation says it did. Recommended: when OneAI keeps something, one
   quiet line in the conversation, "Remembered", with Undo; and a OneAI
   button here, **What Do You Know About Me?**, that says what it keeps and
   what the workspace told it.
3. **Intake**: nothing here.
4. **Permissions**: hold. A memory is its owner's only (`if_owner`), and
   Forget checks delete permission.
5. **Cross-module**: a memory about a record names the record as plain text.
   Recommended: a link that opens it. And OneAI also uses what the
   workspace's administrators wrote for everybody (`AI Knowledge`), which a
   person cannot see anywhere. Recommended: a second section, read-only,
   **What Your Workspace Told OneAI**, listing those by title.
6. **UI and UX**:
   - A person can only add a memory by asking OneAI. Recommended: **Add a
     Memory** in the page head, a dialog with the fact and an optional
     record, frappe's own controls.
   - A memory cannot be corrected, only forgotten. Recommended: Edit beside
     Forget, the same dialog.
   - Nothing says when each was kept. Recommended: "kept 3 days ago" under
     each.
   - With many, there is no way to clear them. Recommended: **Forget
     Everything**, quiet, asking first.
   - The empty state is large and centred, unlike every other section.
     Recommended: one quiet line, as the other sections say it.
7. **Documented**: no section in `one/README.md`. Recommended: one.
8. **Legal**: holds. The AI Addendum already says what OneAI remembers is
   listed in the person's settings and can be deleted.
9. **Built from frappe**: the list is ours; the dialog would be frappe's
   (Small Text, Link, Dynamic Link).

Your word: all of them.

Done:

- When OneAI keeps or updates a memory, the conversation shows one quiet line,
  "Remembered: …", with Undo (`one_ai/chat.py` `_remembered`, `Panel.vue`).
  Undo forgets it and the line says "Forgotten".
- **What Do You Know About Me?** on the page and as its suggestion, read by
  `my_memories`: what it keeps and what the workspace told it.
- A memory about a record links to it. **From Your Workspace** lists the
  enabled `AI Knowledge` by title, read-only.
- **Add a Memory** in the page head, and Edit beside Forget: one frappe dialog
  (Small Text, Link DocType, Dynamic Link). A record the person cannot read is
  refused. "kept 3 days ago" under each; **Forget Everything** when there is
  more than one, asking first. The empty state is one quiet line.
- The page redraws through `frappe.realtime` (`one_memory`, sent by the
  `AI Memory` controller) when a memory changes in the panel or another tab.
- Your word after seeing it with many: too cluttered. Both lists are now
  frappe's `EmbeddedList` (the table DocType Settings uses): one line each
  with Memory, About and Kept, a row opens the Edit dialog, the bin shows on
  the row under the pointer, and Search appears past five.
- `one/README.md` gains Settings › What OneAI Remembers.

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

#### Notifications, second pass

Against what the pass learned since. Nothing is changed yet.

1. **Notifications**: two kinds come in pairs that are one event said two
   ways: Intake Waiting and Intake Waiting, One Thing; Arrived Through a
   Link and its One File. Each has its own ticks, so a person who ticks one
   and not the other gets mail for some of the same event and not the rest.
   Recommended: one row per pair, and its ticks set both.
2. **OneAI**: the panel offers its two suggestions, and nothing on the page
   says so. Recommended: a OneAI button at the top, **Too Many Emails?**,
   asking the existing question; and the kinds OneAI itself sends (Intake's)
   carry the OneAI tag, since what OneAI does is drawn one way.
3. **Intake**: covered by 1 and 2.
4. **Permissions**: hold.
5. **Cross-module**: nothing new.
6. **UI and UX**:
   - The two switches say what happens when they are off, beside a ticked
     box: "Notifications ✓ — Off, nothing reaches your bell". Recommended:
     say what the tick does ("Everything One tells you reaches your bell"),
     and what unticking stops.
   - Turn On Push is a dark button in the page, a second primary beside
     Save in the head. Recommended: a quiet one; Save stays the page's one
     primary action.
7. **Documented**: Settings › Notifications in `one/README.md` gains what
   is done.
8. **Legal**: nothing new.
9. **Built from frappe**: nothing new.

Your word: all of them, and two more. The ticks made the page cluttered: use
a toggle. And the kinds' sentences had no one way of speaking ("The same,
when only one thing needs you.").

Done:

- **Switches, in columns.** Every tick is frappe's own `Switch` control. Each
  app's heading names the two columns, Email and Push, and each kind is one
  line: its name and sentence on the left, its two switches on the right. A
  switch the workspace decides is dimmed and shows how it stands (frappe
  draws a read-only switch with no input, so an always-mailed kind looked
  off).
- **One way of saying a kind** (`docs/WORDING.md`): every sentence starts
  with when it is sent, from the reader's side, and who it goes to is a
  separate `to`, shown on the workspace's page under the sentence and never
  on a person's own. All fifty-seven declared kinds and frappe's three were
  rewritten; `tests/test_notify.py` holds the rule.
- **Twins are one row.** A kind that `follows` another is not listed, and
  saving sets it with the kind it follows (Intake Waiting, One Thing; Arrived
  Through a Link, One File).
- **OneAI**: **Too Many Emails?** is a OneAI button beside the page's
  sentence; the kinds OneAI sends (Intake's, and the two grievance reads)
  carry the OneAI tag (`oneai` on the declaration).
- The switch sentences say what the switch does, then what off means.
- **Turn On Push** is quiet; Save is the page's one primary action.
- `one/README.md` says all of it; the workspace page and OneAI's
  `notification_type` tool now say who each kind goes to.

Then, on your word:

- **OneIntake** is a product: its name everywhere on screen (the rail, its
  page, Workspace settings, the notification heading, its legal clauses), and
  its own mark, `brand/oneintake.svg` (a page read by a line of light, in
  OneAI's sky-to-violet), registered as a Custom Icon. The ids
  (`one_intake`, the `intake` page and section) stay.
- Each app's heading carries its mark (`settings._mark`); Across One carries
  One's, and Rules none.
- OneIntake's kinds no longer carry the OneAI tag; every one of them is
  OneAI's, so the tag said nothing.
- **New IBAN is not a notification any more.** Its draft bill was already
  held red and its pay panel shows no QR code; now the bill is also marked
  wrong with why (`planning._hold_iban`), so it waits in OneIntake like
  anything else OneAI could not settle, and Intake Waiting tells the person.
  A patch removes the type.

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

### Workspace › General

What the workspace was made with (name, company, country, currency, read
only), then one stack of fields: Company Logo, Language, Time Zone, Date,
Time and Number Format, First Day of the Week, and the Calendar Links switch.
Saved to Company and System Settings.

1. **Notifications**: nothing is sent, and nothing needs to be.
2. **OneAI**: the panel does not know the screen: no page sentence, no
   suggestion. Recommended: the sentence, and with 6c below, **Is signing in
   here safe enough?**, read from the sign-in rules and how many people have
   a second step.
3. **Intake**: nothing here.
4. **Permissions**: hold. Only Workspace Administrator opens the page, and
   `load` and `save` call `roles.require()` first.
5. **Cross-module**:
   - The Company Logo only reaches printed invoices, quotes and orders
     (erpnext's letter head). One itself keeps its own mark. Nothing on the
     page says so. Recommended: say it under the field.
   - Language and Time Zone are only the starting point for people who have
     not set their own in Profile. Nothing says that either. Recommended: one
     line under each.
6. **UI and UX**:
   - a. One long stack, the formats half-width and the switch full-width.
     Recommended: three parts divided by a rule: **Company** (the facts and
     the logo), **Region and Formats** (in two columns), **Calendar Links**.
   - b. Nothing shows what a format looks like until it is saved.
     Recommended: one quiet line under the formats that reads as the choices
     do, "Today reads 27-09-2026 14:05, and a number 1,234.56", redrawn as
     they change.
   - c. The rules for signing in are nowhere an administrator can reach.
     Sign-in tells a person "your workspace decides" two-factor, and the
     passkey sign-in switch (`one_login_with_passkey`) is only in System
     Settings' desk form. Recommended: a **Signing In** part here, from
     System Settings' own fields: two-factor and its method, Login with
     Passkey, how long a session lasts, and the password strength rule.
   - d. It does not save against `modified` or hear `doc_update`: two
     administrators overwrite each other without a word. Recommended: the
     section returns `opened` for System Settings and Company, and saves
     through `_as_opened`, as Profile does.
7. **Documented**: no section in `one/README.md`. Recommended: **General,
   for the Workspace**.
8. **Legal**: holds. Nothing here reaches another company.
9. **Built from frappe**: holds. The fields are System Settings' and
   Company's own, drawn by frappe's FieldGroup.

Your word: all of them.

Done:

- Four parts under headings: **Company**, **Region and Formats** (two
  columns), **Signing In** and **Sharing**. A form that opens on a heading
  has no rule above it (`shell.css`).
- Under the formats, "Now it reads 27-09-2026 18:26:14, and a number
  1,234,567.89.", in the chosen time zone, redrawn as they change.
- **Signing In** writes System Settings' own fields. **Two-Factor Sign-in**
  is Off, Administrators or Everybody: frappe's switch plus its per-role
  flag, where frappe's own "everybody" is the All role, set after the save
  because frappe flags All whenever two-factor is switched on. The code
  comes from an authenticator app or email (SMS needs a gateway nobody has).
  **Signed Out After** is `session_expiry` as 8 hours to 30 days, keeping a
  value set elsewhere. **Passwords** is the policy switch and score as one
  choice. **Passkey Sign-in** is `one_login_with_passkey`.
- The section returns `opened` for System Settings and Company and saves
  through `_as_opened`: a stale save is refused, and another administrator's
  save reloads the page or says so.
- Help lines under Company Logo, Language, Time Zone and each sign-in rule.
- OneAI: the page sentence, **Is signing in here safe enough?**, and a read,
  `workspace_sign_in` (administrators only): the rules, people and
  administrators, passwords over a year old, the last week's failed
  sign-ins.
- `one/README.md` gains General, for the Workspace. `test_settings.py` now
  holds a workspace section OneAI offers anything on to its README section
  too.

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
