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
| Settings, Workspace | People | done |
| Settings, Workspace | Notifications | done (stages 2 and 5 of NOTIFICATIONS.md) |
| Settings, Workspace | Plan and Credits | done |
| Settings, Workspace | Domains | done |
| Settings, Workspace | OneAI (now OneAI › Actions) | done |
| Settings, Workspace | OneIntake (now OneIntake › Settings) | done |
| Settings, Workspace | Holidays | done |
| Products | One › Home | done |
| Products | OneMail | done |
| Products | OneCloud | done |
| Products | OneCalendar, OneTask, OneProject, OneCRM, OneBook, OneInventory, OneHR, OneAI, OneIntake, OneAdmin | each screen listed here once we reach it |

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
- Your question, "anything else to bring from frappe settings?", and your
  word, all of them: **Address in Mails** (`email_footer_address`) under
  Company; **Email Link Sign-in**, **One Device at a Time**, the lockout
  (**Wrong Passwords Before a Lockout**, **Locked Out For**) and **Passwords
  Expire After** under Signing In; **Record Sharing** (frappe's
  `disable_document_sharing`, the other way round) under Sharing. Left out:
  what is the operator's (backups, scheduler, telemetry, API logging, app
  name), what is OneBook's (precision, rounding) or OneCloud's (upload size
  and types), and "disable password login", which can lock everybody out.

### Workspace › People

Everybody on the workspace in one grid: a row per person with five
dropdowns (OneCRM, OneBook, OneInventory, OneProject, OneHR: None, User,
Manager), an Administrator tick and Turn Off. Seats above, Invite beside
them. Each change saves at once through `set_access`, `set_admin`,
`set_enabled`; Invite makes a User and sends frappe's welcome mail.

1. **Notifications**: only the welcome mail. A person is not told when
   they are given an app or made an administrator, and nobody is told when
   somebody becomes an administrator, which is how a taken account widens
   itself. Recommended: **Access Changed** to the person, on the bell
   ("You can now use OneCRM as a manager"); **Administrator Added** to every
   administrator, always mailed, like Password Changed.
2. **OneAI**: the panel does not know the screen. Recommended: the page
   sentence, and **Who has access to what?** and **Who has not signed in
   lately?**, read by a new `workspace_people` (administrators only):
   access, administrators, last active, turned off.
3. **Intake**: nothing here.
4. **Permissions**: hold. Every call asks `roles.require()`; nobody turns
   themselves off or removes the last administrator; a seat is checked
   before turning somebody on or inviting.
5. **Cross-module**:
   - Whether a person is an employee in OneHR is not shown. Recommended:
     their Employee, linked, when they have one.
   - An administrator cannot see where somebody is signed in or sign them
     out: offboarding means Turn Off and hoping. Recommended: in the
     person's dialog (6b), their devices and last sign-ins from
     `signin.py`, **Sign Out Everywhere**, and **Send a Password Reset**
     (frappe's own reset mail).
6. **UI and UX**:
   - a. A wall of thirty "None" dropdowns, a bare checkbox and a Turn Off
     on every row; the app icons sit apart from their names. Recommended:
     frappe's `EmbeddedList`, as What OneAI Remembers now is: Person (photo,
     name, address), Apps (a badge per app they have, "OneCRM · Manager"),
     Administrator, Last Active, and an Off badge; search built in.
   - b. Recommended: a row opens the person in a frappe Dialog: a Select
     per app, an Administrator switch, and Turn Off / Turn On, Sign Out
     Everywhere and Send a Password Reset in its footer. Saved together,
     against the User's `modified`.
   - c. Invite is a button inside the page. Recommended: **Invite
     Somebody** is the page head's primary action, and its dialog also
     asks which apps they get, so nobody needs a second step.
   - d. Turning somebody off asks nothing. Recommended: ask first, and say
     their records stay.
   - e. The seats badge floats alone. Recommended: one quiet line under
     the intro, "6 of 10 seats used".
7. **Documented**: no section in `one/README.md`. Recommended: **People,
   for the Workspace**.
8. **Legal**: with 5b, administrators see where people sign in from. The
   privacy notice must say so. Recommended: a `clause()` in `one/legal.py`,
   "Your workspace's administrators can see where you are signed in and
   your last sign-ins, and can sign you out."
9. **Built from frappe**: the dropdowns are a raw `<select>` and the tick a
   raw checkbox, not frappe's controls. 6a and 6b replace both.

Your word: all of them.

Done:

- The list is frappe's `EmbeddedList`: Person (photo, name, address, an Off
  badge), Apps (a badge per app, or "Every app · Manager"), Administrator,
  Last Active; search past five. The seats are in the line under the intro.
- A row opens the person in a frappe Dialog: a Select per app in two
  columns, the Administrator switch, their employee record, where they are
  signed in (five, then "And N more") and their last sign-ins. Its footer
  has Turn Off (asks first, signs them out now, frees the seat), Turn On,
  Sign Out Everywhere (frappe's `clear_sessions`) and Send a Password Reset
  (frappe's own reset mail). One `save_person` sets the roles in one save
  against the User's `modified`; a stale save is refused. The values are
  set after the dialog is made, because frappe reads a field default of
  "User" as the person signed in.
- A save always keeps Desk User: found when taking the administrator role
  from somebody who held nothing else made frappe turn them into a website
  user, and they dropped out of the workspace.
- **Invite Somebody** is the page head's primary action; its dialog asks
  which apps they get.
- Notifications: **Access Changed** to the person ("Samir Aoun changed what
  you can use: OneCRM as a user."), **Administrator Added** to every other
  administrator, always mailed.
- OneAI: the page sentence, **Who has access to what?** and **Who has not
  signed in lately?**, read by `workspace_people` (administrators only).
- Your word after seeing it: the dialog was too crammed. A person is now a
  page, `?section=people&person=`, as a desk form like Profile: Save in the
  page head, against the User's `modified`, heard through realtime. Each app
  is a Select with its mark and what it holds; Sign Out Everywhere, Send a
  Password Reset and Turn Off sit under their name. The invite dialog shows
  the marks too, and an invited person is not also sent Access Changed:
  their welcome mail says it.
- The invitation is One's own (`one/invite.py`): frappe's welcome mail was a
  reset link that lived twenty minutes (`reset_password_link_expiry_duration`)
  and said nothing of who asked. Ours is the hub's Invitation type, "Samir
  Aoun invited you to Nine X", with the apps they get and a link that works
  for seven days: opening it asks frappe for a fresh reset link and goes
  there, so the password is still set on frappe's page. Choosing it spends
  the link, and a first password is not told as Password Changed. Invite
  Again for somebody who has not joined.
- No mail says "Sent via ERPNext" any more: System Settings'
  `disable_standard_email_footer`, by patch and in `brand.py`.
- Your word on the sub-pages: a person, a notification type and a rule are
  now drawn as docviews (`Editor.as_record`, docs/SHELL.md): "People /
  Rania Sabbagh" in the breadcrumb with the status pill, Actions and Save in
  the page head, full-width parts, frappe's form sidebar. No back buttons.
- `one/README.md` gains People, for the Workspace. The privacy notice gains
  "people-sign-in" and goes to revision 4, since administrators now see
  where a person is signed in: everybody agrees again at their next
  sign-in.

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

### Workspace › Plan and Credits

Two sections drawn from the `Workspace Account` copy (`account.refresh`,
nightly): Plan (plan, status, seats, a storage bar) and OneAI Credits
(balance, what expires when, OneIntake's line for the month), then Buy
Credits (a dialog of packs, then Stripe in a new tab) and See What Used Them
(the AI Credits report). The same record also has its own desk form,
`/desk/workspace-account`, with a Record Head and its own Buy credits.

1. **Notifications**: nothing about the account is ever sent. Nobody is
   told credits are running out, that 5,000 expire in three days, that a
   pack they paid for has arrived, that storage is at 84%, or that payment
   is overdue and the workspace is suspended in N days. Recommended, in
   `one/notifications.py`, to administrators, sent from `refresh` by
   comparing what it held with what it heard:
   - **Credits Running Low**, on the bell and mailed, when the balance
     falls under a tenth of the last thirty days' use.
   - **Credits Expiring**, on the bell, seven days before.
   - **Credits Added**, on the bell, when the balance rises by a pack.
   - **Storage Nearly Full**, on the bell and mailed, at 90%.
   - **Payment Overdue**, always mailed, with the days left.
2. **OneAI**: the panel does not know the screen. Recommended: the page
   sentence; **How long will our credits last?** and **What used the most
   credits this month?**, read by a new `workspace_plan` (administrators
   only): plan, seats, storage, balance, held, expiring, and the last
   thirty days' use by model and person (the same `ai_usage` ask the report
   makes; no AI call).
3. **Intake**: "OneAI handled 26 of 39 documents this month" is OneIntake's
   and is already on the OneIntake page. Here it answers nothing about
   credits. Recommended: take it off.
4. **Permissions**:
   - The page and Buy ask `roles.require()`, and hold.
   - `Workspace Account` gives read to **All**, so every desk user can
     open `/desk/workspace-account` and read the balance, what is owed and
     the last error; `account.mine` hands the same to anyone and nothing
     calls it. Recommended: read for administrators only; delete `mine`.
5. **Cross-module**:
   - The OneAI rail's **Credits** and See What Used Them are the same
     report. Fine, but the report is where the numbers are.
   - Seats do not link to People, and the storage bar does not lead to
     OneCloud. Recommended: "6 of 10 used" opens People; storage opens
     OneCloud's Home, sorted by size.
   - Two screens for one record. Recommended: `/desk/workspace-account`
     sends administrators here, as the Customize form's own page does.
6. **UI and UX**:
   - a. Buy Credits is a button in the body. Recommended: the page head's
     primary action; See What Used Them its secondary.
   - b. A workspace days from suspension sees nothing: `account_said`
     (the overdue sentence, or "could not reach your account") is only on
     the desk form. Recommended: drawn as a record (`Editor.as_record`):
     the standing badge (heads.py's "Active", "Payment overdue") and the
     sentence at the top, the plan in the side.
   - c. Status says "Live", the admin's word. Recommended: heads.py's
     word.
   - d. Days Left is a bare number. Recommended: only in the overdue
     sentence.
   - e. Held credits are not shown, so a balance that looks fine while
     calls are refused says nothing. Recommended: "Held" under Credits,
     when there is some.
   - f. The page never says how old its numbers are, and a pack paid for
     shows up tomorrow. Recommended: "As of 10:42", **Check Again** (a
     `refresh`), and a refresh when the page is opened and older than an
     hour.
   - g. The storage bar is black at 84%. Recommended: frappe-ui's
     Progress, amber from 90%, red over.
   - h. The pack Select says only the pack's label. Recommended: "5,000
     credits · $50" per pack.
   - i. "OneAI  Credits" has a double space where the brand splits the
     word.
7. **Documented**: no section in `one/README.md`. Recommended: **Plan and
   Credits, for the Workspace**: what each number is, where credits go
   first, how to buy, what expires.
8. **Legal**: the terms say credits are bought ahead and not refunded, but
   not that they expire, that the plan's monthly credits do not roll over,
   or that the soonest-expiring are used first (`topup.py`). Recommended:
   say so in the terms' `credits` clause, and bump the terms' revision
   (material). Stripe is already a subprocessor in `one_admin/legal.py`.
9. **Built from frappe**: the dialog is frappe's; the bar is espresso's
   `frappe.ui.progress` (6g); the facts are a hand-drawn list, which 6b
   replaces with the record view's own parts.

Your word: all of them.

Done:

- Five notices in `one/notifications.py`, sent from `account.refresh` to
  every administrator when a line is crossed: Credits Running Low (under a
  tenth of the last thirty days' use, which `hello` now sends as
  `credits.month`), Storage Nearly Full (nine tenths) and Payment Overdue
  (the suspension date, once per date), all three also mailed; Credits
  Expiring (a week ahead, once per date) and Credits Added on the bell.
  `roles.administrators()` is who hears, shared with Administrator Added.
- The page is the account drawn as a record: the standing in the pill, the
  overdue or out-of-touch sentence above everything (`heads.account_said`),
  Plan (plan, seats leading to People, storage leading to OneCloud, orange
  from nine tenths, red over) and OneAI Credits (left, held, used in the last
  thirty days, expiring). The side has the name, the plan, links and "As of".
  Buy Credits is the page head's primary action; See What Used Them and
  Check Again sit beside it. Opening the page asks the account again when
  its copy is over an hour old, and so does coming back from payment.
- Packs read "1,000 credits · $ 9".
- OneIntake's month line is gone from here.
- `Workspace Account` is read by administrators only, `account.mine` is
  deleted, and `/desk/workspace-account` sends its reader here.
- OneAI: the page sentence, the two suggestions and `workspace_plan`.
- `one/README.md` has Plan and Credits, for the Workspace.
- The terms' credits clause says the plan's monthly credits expire at the
  month's end and are used first, and bought ones never expire; terms
  revision 2, so administrators agree again.
- A section title is one flex item, so "OneAI Credits" no longer splits.

Afterwards, on your word: a **Ledger** section, the account's last ninety
days newest first. Each grant and refund is a line of its own (bought, the
plan's monthly credits, given by One, refunded); spend is summed per day,
because the account keeps a spend row per call and per bucket. A day opens
the AI Credits report for that day, by person. The admin's `ai_usage` now
sends `arrived` (`ledger.arrived`), and `workspace_plan` reads the ledger.

Afterwards, on your word: plans and add-ons are sold here. Change Plan
shows the plans side by side and what a move costs a month; Add, Storage,
Database or Seats is an add-on and how many, and says when the plan above
gives the same for less; the Plan section shows the database beside
storage, what it costs a month, and the add-ons with Remove. How the price
list is built and kept coherent is `docs/INFRASTRUCTURE.md`, Plans, add-ons
and what they cost. Terms revision 3.

Not done: storage leads to OneCloud's Home, not to a list of the biggest
files, because OneCloud has no workspace-wide list by size to open.

### Workspace › Domains

One section, Addresses: each name the workspace answers at, with a status
badge, Primary and Ours, and Make Primary and Remove per row. Add a Domain
and Check Again are buttons in the body. The rows come from the
`Workspace Account` copy (`settings._domains`); every button asks the admin
site, which asks Frappe Cloud (`one_admin/domains.py`) and writes the answer
back into the copy (`account._keep`). The admin site asks Frappe Cloud
nightly about names not yet Active, and `hello` carries the list back
hourly.

1. **Notifications**: nothing is sent. A name goes Active minutes or hours
   after it is added and nobody is told, so the administrator has to come
   back and press Check Again. Nobody is told when a name stops working
   (Frappe Cloud drops it, status Gone), and the other administrators are
   not told when somebody adds a name, removes one or changes the main
   address, which moves the sign-in page and every link in every mail.
   Recommended, in `one/notifications.py`, to administrators, sent from
   `account.refresh` comparing before and after as the credit notices are:
   - **Domain Working**, on the bell and mailed, when a name goes Active.
   - **Domain Stopped Working**, on the bell and mailed, when one that was
     Active is not.
   - **Main Address Changed**, on the bell and mailed, to every other
     administrator, from `domain_primary`.
2. **OneAI**: the panel does not know the screen. Recommended: the page
   sentence, and **Why is our domain not working?**, read by a new
   `workspace_domains` (administrators only): each name, its status, what
   Frappe Cloud last said about it, and what its DNS should say. No AI call
   is needed to read it; the model only explains.
3. **Intake**: nothing here, and nothing should be.
4. **Permissions**:
   - The page is in the Workspace group (administrators), and every call
     asks `_may_rename` (Workspace Administrator). Holds.
   - The guard's names are wrong: `MAY_RENAME` and "Only an administrator
     of this workspace can change its address" also guard buying credits.
     Recommended: `roles.require()`, as Plan and Credits uses, and the
     constant gone.
5. **Cross-module**:
   - The main address is what the site calls itself (`host_name`), so it is
     every link in One's mail, the invite link, the calendar feed and a
     OneCloud share link. The screen does not say so. Recommended: one line
     under Primary saying it.
   - OneMail's mail domain is a separate thing (Settings › Mail) and the
     two are easy to confuse. Recommended: the note says this page is where
     the workspace opens, and names where mail addresses are set.
6. **UI and UX**:
   - a. **A dead end.** Once your own name is primary, Make Primary on
     ours fails ("a name we hand out, so it cannot be added as your own"),
     because `_held` runs every name through `hosts.claimable`. And Frappe
     Cloud refuses to remove the primary name. So a workspace that makes
     its own name primary can never go back or remove it. Recommended: the
     given name is always allowed back as primary (`set_host_name` to the
     site's own name, `primary_domain` cleared).
   - b. **The DNS is never explained.** Add a Domain is one field, "For
     example office.example.com", and nothing says what to point it at.
     `domain_check` exists and nothing calls it. Recommended: the dialog
     says the record to make (a CNAME to the site's Frappe Cloud name, with
     Copy) and that Cloudflare's proxy must be off; Add checks the DNS first
     and shows Frappe Cloud's own sentence when it is wrong; a Pending row
     shows the same record, so the instructions are there when somebody
     comes back to it.
   - c. **Raw JSON.** After Check Again or any action, a custom name's row
     prints what Frappe Cloud said as a JSON string (`Tenant Domain.said`
     via `domains.mine`); after a reload it is gone, because `_keep` drops
     it. Recommended: keep the one sentence worth keeping (Frappe Cloud's
     message) on the copy, and draw it as the row's sub-line.
   - d. Add a Domain is a solid button in the body. Recommended: the page
     head's primary action; Check Again beside it, as on Plan and Credits.
   - e. Hand-drawn rows. Recommended: `shell.table` (Domain, Status, a
     Primary badge, actions), as Invoices is on Plan and Credits.
   - f. Status words are Frappe Cloud's raw ones and all amber: Pending,
     Broken and Gone look the same. Recommended: Active green, Pending
     orange, anything else red; translated.
   - g. The note says "The one we provide", which is first person.
     Recommended: "The t.4dl.app address always works".
   - h. `hosts.Unclaimable` sentences are not translated.
7. **Documented**: `one/README.md` has no Domains section, so OneAI's
   `how_to` cannot answer "how do I use our own domain". Recommended: a
   section on what the page is for, the DNS record, why Cloudflare's proxy
   has to be off, what Primary changes, and who may do it.
8. **Legal**: the terms say nothing about a customer's own name.
   Recommended, a clause in `one/legal.py`: the customer must own or
   control the name, the certificate is issued for it by Let's Encrypt
   through Frappe Cloud, and the name stops answering when the workspace
   is closed. Let's Encrypt only sees the name, which is not personal
   data, so it is not a subprocessor.
9. **Built from frappe**: the dialog is `frappe.ui.Dialog` with a Data
   control and the confirm is `frappe.confirm`. The rows are hand-drawn
   (see 6e), and the page does not update when a name goes Active; with the
   notice in 1 it would, through `frappe.realtime` from `account.refresh`.

Your word: all of them.

Done:

- **The dead end is gone.** Make Main Address on the address One gave the
  workspace puts press's own record back on the press name and writes our
  name into the site's `host_name` again, as provisioning does
  (`domains._back_to_given`). Ours is the main address whenever none of
  the customer's is, so a stale `primary_domain` can no longer hide it,
  and removing a domain that was primary clears it.
- **The DNS is explained.** `hello` sends the CNAME target (the site's
  Frappe Cloud name) and the account keeps it (`dns_target`). The Add
  dialog shows the record to make as the domain is typed, with Copy and the
  Cloudflare note; Add checks the DNS first and says what to do when it
  does not point here yet. Your Own Domain shows the same record on the
  page.
- **No raw JSON.** `mine` no longer sends what press said; a row says in
  our words what Waiting and Not Working mean. A refusal from the admin
  site now reads as the sentence it was (`faults.detail` reads
  `_server_messages`), and `hosts` refusals are sentences, translated.
- **The page.** Add a Domain is the page head's action and Check Again
  beside it; the list is `shell.table`; Working is green, Waiting orange,
  anything else Not Working in red; Main Address and Given by One are
  badges. A line under the list says what the main address changes, and
  the note says email addresses do not change. The page asks the account
  again when its copy is over an hour old, and redraws on `one_domains`.
- **Notices**: Domain Working and Domain Stopped Working, to every
  administrator, on the bell and by mail, told when the account's answer
  changes (`account._tell_domains`, from `refresh` and from every domain
  call); Main Address Changed to every other administrator.
- **Guards**: every call asks `roles.require()`; `MAY_RENAME` and
  `_may_rename` are gone.
- **OneAI**: the page sentence, **Why is our domain not working?**, and
  `workspace_domains`.
- `one/README.md` has Domains, for the Workspace.
- The terms say what having your own domain means (`one/legal.py`,
  own-domain); terms revision 4.

Afterwards, on your word: a customer's own domain is a Cloudflare custom
hostname on our zone, not a Frappe Cloud domain. The customer CNAMEs it to
their `<slug>.t.4dl.app`; Cloudflare issues the certificate; a Worker route
and a `host:` key in KV send it to the site, as ours already are. Frappe
Cloud never sees the name, so `*.frappe.cloud` is never shown and a customer
behind Cloudflare's proxy needs to change nothing. Add no longer waits on the
DNS: the domain waits, and says Cloudflare's own sentence about what is
stopping it. The record is drawn as a DNS provider lists one, with Copy on
each value, and a note on bare domains. Cloudflare is now listed as the
network every workspace is reached through (subprocessors revision 2).
Tested live on `one-test.4dl.dev`: Working in 100 seconds with a valid
certificate, served through the router, then removed with its hostname,
route and key.

### Workspace › OneAI

Two sections. **What Runs on Which Model** lists every enabled AI Action
(seventeen: Chat, Look It Up, Draft a Reply, the five OneIntake reads, the
OneHR ones, Summarise, Transcribe…), each with its model as a badge
("Default", or the model's raw id) and **Change**, which opens the desk
form `AI Action Setting` for it: the model (a Select filled from the
account's catalogue) and Added Instructions, with **Try it**. **Knowledge**
is a count ("1 notes OneAI reads before it answers") and Open, to the desk
list of AI Knowledge.

1. **Notifications**: nothing is sent. Changing an action's model or its
   added instructions changes what OneAI does, and what it costs, for
   everybody, and the other administrators are not told. Recommended: **OneAI
   Changed**, on the bell, to every other administrator, naming the action
   and what changed (model, instructions, back to default).
2. **OneAI**: the panel does not know the page. Recommended: the page
   sentence, and **Which of these costs us the most?** and **Is there a
   cheaper model that would do?**, read by a new `workspace_oneai`
   (administrators only): each action, its model or the default, its added
   instructions, the models the account offers for it with their price, and
   what each action used in the last thirty days. No AI call to read it.
3. **Intake**: five of the rows are OneIntake's (First look, Read a
   document, Place a document, Read scans, Transcribe recordings), mixed
   in alphabetically with Chat and the OneHR ones, and Workspace ›
   OneIntake does not link here. Recommended: the rows grouped by the
   product they belong to (OneAI, OneIntake, OneHR, OneMail), and OneIntake's
   page linking to its group.
4. **Permissions**:
   - The page is administrators'; `AI Action Setting` is written by
     Workspace Administrator (and System Manager). Holds.
   - `AI Knowledge` is read by All. That is needed, because OneAI reads it
     as the person asking (`memory.py`), so everybody can open the list; it
     is what OneAI would tell them anyway. Holds, and the docs should say so.
   - **Try it** charges the workspace's credits, and says so after, not
     before. Recommended: the cost is said on the button's dialog before
     running.
5. **Cross-module**:
   - What each action costs is nowhere: the AI Credits report groups by
     model, person or day, not by action. Recommended: a last-thirty-days
     column here, and **Action** in the report's By (the ledger's
     reference carries it).
   - Knowledge is a count and a link out. Recommended: the notes listed
     here (title, what they apply to), opened and added from the page.
6. **UI and UX**:
   - a. **Raw model ids.** Chosen models show as
     `google-ai-studio:gemini-2.5-flash-lite` in a violet badge, and the
     form says "Empty uses gemma-4-26b-a4b-it". Recommended: the model's
     name from the catalogue ("Gemini 2.5 Flash Lite"), "Default (Gemma 4)"
     in gray, and the price per million tokens in the picker.
   - b. **Change leaves the page** for a desk form that shows the action's
     key ("chat") in a Link field, a Templates button and a blue banner.
     Recommended: a dialog on this page: Model, Added Instructions, Try It
     and Use the Default, saved against `modified`.
   - c. Labels are in two cases ("Look It Up", "Draft a Reply" beside
     "Explain a document", "Read scans"), and "Audit what OneAI did" puts
     gaps round OneAI. Recommended: Title Case throughout, brand span fixed.
   - d. Hand-drawn rows. Recommended: `shell.table`, grouped as in 3.
   - e. "1 notes": the plural is not handled.
7. **Documented**: `one/README.md` has no section for Workspace › OneAI,
   so `how_to` cannot answer "how do I make OneAI answer in Arabic" or
   "what is knowledge". And `one_ai/` has no README at all. Recommended: a
   section, OneAI, for the Workspace (what each part does, what added
   instructions can and cannot change, what knowledge is and who reads it,
   what Try it costs), and the module README when the pass reaches OneAI
   itself.
8. **Legal**: choosing a model chooses who receives the data. The catalogue
   offers two providers, `google-ai-studio` and `workers-ai`, and both are
   listed (Google, Cloudflare). Holds today, but nothing stops an operator
   enabling a provider the subprocessors do not name. Recommended: a guard
   that every provider offered is a listed subprocessor, and the picker
   saying which company runs the model.
9. **Built from frappe**: the setting is a frappe form with frappe
   controls, which is right for behaviour, but it is reached by leaving the
   page (6b). The rows are hand-drawn (6d). No realtime: a change made by
   another administrator does not redraw an open page; it would with
   `doc_update` on AI Action Setting.

Your word: all of them, with model makers' logos (Google's favicon service,
v2), a proper list for the actions, and the page under OneAI in the rail.

Done:

- **Where it lives.** The rail's OneAI group now has **Actions** (this page,
  titled OneAI Actions) and **Knowledge** (the AI Knowledge list) beside
  Credits, Conversations and Suggestions. It left the Workspace group.
- **The list.** `shell.table`: Action (with what it does), Product, Model
  and Last 30 Days. A model is its maker's logo and its name, read from the
  catalogue and made readable (`makers.pretty`: "Gemma 4 26B A4B IT", not
  `gemma-4-26b-a4b-it`), with a gray Default when One picked it. The logo
  is the maker's, not the host's: Meta for Llama even though Cloudflare
  runs it (`one_admin/makers.py`).
- **Change is a dialog on the page**: Model (every model on offer that can
  do it, named with its maker), what the picked one is (made by, run by,
  and about how many credits per thousand words read and written), Added
  Instructions, **Try It** (runs what the dialog holds, saved or not, and
  says it uses credits before it runs), **Use the Default** and **Save**,
  which refuses when another administrator changed it since it was opened.
  The old desk form sends its reader here.
- **What each action costs.** Every reservation now records its action
  (`Credit Reservation.action`, from `actions.run` through the gateway),
  `ai_usage` answers by action, the list shows the last thirty days, and
  the AI Credits report has **Action** in By. Calls from before this show
  as Other.
- **Grouped by product**: `AI Action.product` (OneAI, OneIntake, OneHR,
  OneMail), labels in Title Case. OneIntake's page has **Models**, which
  opens this list showing its actions only.
- **Notice**: OneAI Changed, on the bell, to every other administrator,
  saying what changed ("the model to Gemini 3 Flash Preview", "the added
  instructions"). The page redraws on `one_oneai`.
- **OneAI**: the page sentence, **Which actions cost the most?** and **Is
  there a cheaper model that would do?**, read by `workspace_oneai`.
- **Legal**: `makers.PROVIDERS` is every provider a workspace's data may go
  to; `actions.offered` never offers another, and
  `test_every_model_provider_offered_is_a_declared_subprocessor` holds it
  to the Subprocessors list.
- `one/README.md` has OneAI Actions, for the Workspace, with Knowledge.

Not done: `one_ai/` still has no README of its own; that is the OneAI
product's screen, when the pass reaches it.

### OneIntake › Settings (was Workspace › OneIntake)

Moved on your word before the findings: the One sidebar has a **OneIntake**
group (Inbox, Ready to Submit, Deadlines, Spending, Settings) under OneAI,
and this page is its Settings, titled OneIntake Settings.

The page is `Intake Settings` as one flat form of eight fields, under a
violet line "OneAI handled 26 of 39 documents this month; 13 needed a
person", with **Models** and **Save** in the page head.

1. **Notifications**: nothing is sent when these change, and three of them
   change what OneAI does with money for everybody. **Submit Matching
   E-Invoices** lets OneAI post invoices to the books; **Household** stops
   every draft; **Audit What OneAI Does** off removes the second check.
   Recommended: **OneIntake Changed**, on the bell, to every other
   administrator, naming what was switched and by whom.
2. **OneAI**: the panel does not know the page. Recommended: the page
   sentence, and **Is OneIntake set up well for us?**, read by a new
   `workspace_intake`: the settings, this month's numbers (handled, needed a
   person, undone), what waits now, and how often the floor sent things to a
   person. No AI call to read it.
3. **Intake**: this is Intake's own page. The month line answers nothing on
   its own: 13 needed a person, but which, and are they still waiting?
   Recommended: a **This Month** section (handled, needed a person, undone,
   waiting now), each number opening the Inbox on that box.
4. **Permissions**: the page is administrators'; `Intake Settings` is
   written by Workspace Administrator only. Holds. The sidebar group's
   Inbox, Deadlines and Spending are every desk user's, Ready to Submit
   the accounts and purchase roles', and Settings administrators'; frappe
   hides what a person cannot open.
5. **Cross-module**: Household and Submit Matching E-Invoices are OneBook
   decisions made here with no link to OneBook; Read Files Attached to
   Records reaches every module. Recommended: each says where it lands
   (Ready to Submit, Spending), as a link.
6. **UI and UX**:
   - a. **Empty fields that are not empty.** Most Pages Read and Confidence
     Floor show blank, but blank means 60 pages and 70% (`pipeline.py`,
     `act.py`). Quiet Minutes shows 0, which is its real value: OneAI acts
     at once. Recommended: the defaults written in, and each field saying
     what it does now ("60 pages", "70%").
   - b. **One flat list.** Eight settings of four kinds. Recommended:
     sections: What Is Read (attached files, most pages), How Sure (floor,
     audit), Filing (leave in place, quiet minutes), Books (household,
     submit e-invoices).
   - c. The month line is a violet badge. Recommended: the This Month
     section in 3, drawn as the page's own facts, not a badge.
   - d. "Confidence Floor" is a Percent field with no unit shown.
7. **Documented**: OneIntake's README describes each setting where it
   applies, but has no section for this page, so `how_to` cannot answer
   "what should the confidence floor be". Recommended: a section,
   OneIntake Settings, in `one_intake/README.md` (above Under the hood):
   each setting, its default, and who changes it.
8. **Legal**: the AI Addendum's `intake-acts` says OneAI files, links and
   *drafts*. With Submit Matching E-Invoices on, it also *submits* an
   invoice to the books, which the clause does not say. Recommended: the
   clause says a workspace may let it submit e-invoices from known
   suppliers that match an order, off unless switched on.
9. **Built from frappe**: the form is frappe's controls in a FieldGroup
   with Save in the page head, dirty-tracked and saved against the loaded
   values. Holds. It does not redraw when another administrator saves.

Your word: all of them, with switches instead of ticks, and cleaned up.

Done:

- **Switches.** Every on/off setting is frappe's Switch control, as
  frappe-ui draws one, the sentence beside it and the switch at the end.
- **Four parts.** What Is Read, How Sure OneAI Must Be, Filing and Books,
  each a heading and a line saying what it decides. Numbers sit in half a
  row rather than across the page.
- **Defaults written in.** Most Pages Read shows 60 and the Confidence
  Floor 70 where the record was empty, and the doctype now defaults to
  them.
- **This Month** is five numbers for everybody (arrived, handled by OneAI,
  needed a person, waiting now, undone), each opening the inbox on
  everybody's documents (`intake?box=…&everyone=1`), in place of the violet
  line.
- **Books** links to Ready to Submit and Spending.
- **Notice**: OneIntake Changed, on the bell, to every other administrator
  when the audit, household or submitting e-invoices is switched, or the
  floor moves ("Submit Matching E-Invoices on"). An empty floor saved as 70
  is not a change. Saving is against `modified`, so a second
  administrator's save since opening is refused; the page hears the record
  change through `opened`.
- **OneAI**: the page sentence, **Is OneIntake set up well for us?** and
  `workspace_intake`.
- **Legal**: the AI Addendum's `intake-acts` says OneAI drafts and does not
  submit, unless an administrator switches on submitting e-invoices, and
  what it then submits. AI Addendum revision 2.
- `one/README.md` has OneIntake Settings, for the Workspace;
  `one_intake/README.md` points to it.

Afterwards, on your word: OneIntake's settings that lived elsewhere are on
this page too.

- **Where OneAI Reads**: every mailbox, whether OneAI reads it and on whose
  behalf, and every OneCloud folder it reads, as lists. Starting one stays
  its holder's (OneAI then acts as them, `switches.py`); an administrator
  can stop any from here, and **Add a Folder** starts one. A person can
  still switch their own mailbox in OneMail and their own folders in
  OneCloud, since that is their consent rather than a workspace setting.
- **OneHR**: Screen New Applicants, Prepare Interviews, Transcribe
  Interview Recordings and Triage Grievances, still stored on HR Settings
  and hidden there, switched and saved here. Recording consent and how long
  audio is kept stay in HR Settings, which says where the rest went.
- OneCalendar, OneTask, OneProject, OneCRM, OneBook and OneInventory had no
  OneIntake settings to move.
- `workspace_intake` also reads which mailboxes and folders are read.

### Workspace › Holidays

The page is a Select of Holiday Lists ("One 2026"), **Open the List** and
**New List** buttons in the body, and a hand-drawn **Coming Up** list of
the next eight public holidays. Save sets `Company.default_holiday_list`.
The site has one list, One 2026: Friday off, the UAE's public holidays from
erpnext's `get_local_holidays`, made by the setup wizard, with a company
`Holiday List Assignment` from 1 January.

1. **Notifications**: changing the list sends nothing, though it moves
   everybody's leave, attendance and deadlines. HR Settings' **Holidays
   Coming Up** reminds each person of their own holidays; that holds.
   Nobody is told the list is running out (see 5b). Recommended:
   **Holidays Changed** on the bell to the other administrators and the HR
   managers, and **Holidays Run Out Soon** to the same people 60 days
   before the list's last day, when no list follows it.
2. **OneAI**: the panel does not know the page. Recommended: the page
   sentence, and one suggestion, **Are our holidays ready for next year?**,
   read by `workspace_holidays` (the list, its last day, the next list if
   any, who is on a different list). No AI call to read it.
3. **Intake**: deadlines move past a public holiday (§ 193 BGB) using
   `Company.default_holiday_list`, whatever the date. A deadline in January
   2027 is counted against the 2026 list, which has no 2027 days.
   Recommended: Intake reads the list in force on the date (the
   assignments, as hrms does).
4. **Permissions**: the page is administrators'. `Holiday List` is written
   by HR Manager only, so an administrator without it opens **Open the
   List** read-only and gets refused on **New List**. Recommended: the page
   edits the list itself, under the administrator's own check, so the two
   agree.
5. **Cross-module**:
   - a. **Save does not reach OneHR.** hrms reads only a submitted
     `Holiday List Assignment` (`hrms.utils.holiday_list`), never the
     company field. Choosing another list here changes the OneHR calendar,
     Intake deadlines and ERPNext's reports, and leaves leave, attendance,
     shifts and check-ins on the old one. The two answers disagree.
     Recommended: Save also assigns the chosen list to the company, from its
     first day, as the setup wizard does.
   - b. **The year ends.** One 2026 ends on 31 December. From 1 January
     the 2026 assignment still holds, but its list has no days, so every
     Friday is a working day for leave and attendance and nothing warns.
     Recommended: **Next Year's List**, made from this one (same day off,
     the country's public holidays), assigned from 1 January; plus the
     notice in 1.
   - c. People or branches on another list (an employee's own assignment)
     are not shown. Recommended: the count, with a link to them.
   - d. OneCalendar's sidebar has a **Holiday List** entry that opens
     erpnext's desk list. Recommended: it opens this page.
6. **UI and UX**:
   - a. The page shows eight days of a list and cannot change any of them;
     every change is a trip to erpnext's Holiday List form. Recommended:
     the page is the list: its name and dates, the day off, the country,
     and the year's holidays as a table with add and remove, saved with
     the page's Save.
   - b. The list is a Select, not a Link, so there is no "create new" and
     no search.
   - c. Coming Up is hand-drawn rows. National Day shows twice, 2 and 3
     December, as two identical lines; names stay in Arabic for an English
     reader because they were written in the language the list was made in.
     "(تقديري)" (estimated) is how the package marks lunar dates and is
     worth keeping, as a badge.
   - d. **Open the List** and **New List** are buttons in the body.
7. **Documented**: there is no Holidays section in `one/README.md`, so
   `how_to` cannot answer "how do I add a holiday". Recommended: **Holidays,
   for the Workspace**.
8. **Legal**: nothing to add. The public holidays come from the `holidays`
   package, which runs on the server and sends nothing out.
9. **Built from frappe**: recommended: a Link control; the holidays as
   frappe's EmbeddedList (`onedesk.shell.table`); erpnext's own
   `get_weekly_off_dates` and `get_local_holidays` behind the buttons;
   saving against `modified`; and a redraw on `doc_update` when somebody
   else saves the list.

Your word: all of them. Two changes to the findings as they were built:
the notices go to administrators only, since the page is theirs and an HR
manager could not open it; and the names being in Arabic turned out to be
erpnext's bug, not the list's language.

Done:

- **Save reaches OneHR.** The page edits the list in force today, as hrms
  decides it (`one/holidays.py`, `in_force`). Choosing another list
  (**Use Another List**) submits a company `Holiday List Assignment` from
  today, or from the list's first day, and the company field follows it.
  A daily job keeps the field on the list in force, so erpnext's reports
  move to the new year on 1 January.
- **The page is the list.** Its dates and counts at the top (public
  holidays, weekly days off, the next holiday, the last day and how far
  off it is); **Day Off Each Week**, which remakes every such day on save;
  **Country** and **State or Region**; and the public holidays as frappe's
  own table, add, rename and remove, saved with the page's Save against
  `modified` and redrawn when somebody else saves the list. **Add the
  Country's Public Holidays** adds what the country has that the table
  lacks, without saving. **Open the List** and **New List** are gone.
- **Next year.** **Make Next Year's List** in the page head makes it from
  this one (same day off, the country's public holidays) and assigns it
  from 1 January; the page then opens it (`?list=`), with a line saying
  when it starts and **Back to** this year's. Under 90 days from the end
  with nothing after it, the page says so above everything, with the same
  button.
- **Notices**: **Holidays Changed** on the bell to every other
  administrator, naming what was added, removed or renamed, or the new day
  off; **Holidays Run Out Soon** on the bell and by mail 60, 30 and 7 days
  before the list ends with no list after it.
- **Holidays in the reader's language.** erpnext's `get_local_holidays`
  passes frappe's `en`; the `holidays` package knows English as `en_US`, so
  it fell back to the country's own language. `holidays.local` picks the
  package's own code, and the setup wizard uses it. A patch renames the
  names nobody changed into the workspace's language: One 2026 reads
  "National Day", with lunar dates marked "(estimated)".
- **Intake and OneCalendar read by date**: deadlines count days off from
  every list the company has had, and the calendar shows each holiday from
  the list in force on its day. OneCalendar's sidebar no longer has
  erpnext's Holiday List; the page is One › Workspace › Holidays.
- **People on Their Own List** shows when anybody has an assignment of
  their own, and opens them.
- **OneAI**: the page sentence, **Are our holidays ready for next year?**,
  and `workspace_holidays`, which also lists what the country has that the
  list lacks. No AI call.
- `one/README.md` has Holidays, for the Workspace.

Afterwards, on your word: days off of more than one day, and changing the
holidays by asking.

- **Days Off Each Week** is frappe's MultiCheck, a tick per weekday, so a
  weekend of two (Saturday and Sunday, or Friday and Saturday) is two ticks.
  erpnext keeps one `weekly_off`; saving runs its `get_weekly_off_dates` once
  per day ticked (`holidays.set_days_off`), and the page reads the ticks
  back from the rows (`days_off`). Next year's list keeps them.
- **Ask OneAI**: `change_holidays` suggests a card an administrator
  approves: days added or renamed ("15 November, Founders Day"; a closure is
  a day each), days removed, and the days off. The card lists each change
  and what it was. Approving runs the page's own save as the approver, so
  the same notice goes out, and it is refused as stale if the list changed
  since. A date goes on the list whose year holds it; a date no list holds
  is refused with where to make next year's. A new proposal kind,
  **Holidays**, beside Customize and Signature.

## Products

### One › Home

Home is the `One` workspace: a header that says "One" (the page title
already does) and a `One Onboarding` block that draws nothing, because the
Getting Started panel floats in the corner instead. The rest of the page is
empty. OneCRM, OneHR and OneBook each have a home made of frappe's
workspace blocks (shortcuts, number cards, quick lists); One, where
everybody lands and where every product meets, has none.

1. **Notifications**: Home sends nothing, and needs to send nothing. What
   is waiting for a person is scattered over the bell, the OneIntake inbox,
   OneAI's cards, approvals and tasks, and Home gathers none of it.
2. **OneAI**: the panel does not know the page. Recommended: the page
   sentence and **What needs me today?**, read by a new `my_day` (the
   numbers in 5, and the first few of each). No AI call to read it.
3. **Intake**: what waits for this person in the OneIntake inbox is not on
   Home. Recommended: a number for it, opening the inbox on Waiting.
4. **Permissions**: the workspace is public with no roles, so everybody
   sees it. Holds. Recommended: each block counts only what the reader may
   open (`frappe.get_list`), and the workspace part in 5 shows only to
   administrators.
5. **Cross-module**: Home is where the products meet, and nothing meets
   here. Recommended, for everybody, **Today**, one number each, each
   opening its list:
   - tasks due today or late (OneTask's My Tasks);
   - meetings today (OneCalendar);
   - documents waiting for them (OneIntake);
   - OneAI suggestions waiting for their approval;
   - approvals waiting on them (leave, expense claims, where they approve).
   For administrators only, **The Workspace**, shown only when something
   needs them: a mailbox not connecting, a domain not working, credits
   running low, storage or seats nearly full, the holiday list ending.
6. **UI and UX**: a blank page with a heading repeating the title. The
   Getting Started panel (Set One up, 0 of 4) is the only thing on it, and
   it floats. Recommended: the two parts in 5 as the page; the "One"
   heading goes.
7. **Documented**: `one/README.md` has no Home section. Recommended:
   **Home**, saying what each number counts and who sees the workspace part.
8. **Legal**: nothing to add. Home only counts what the products already
   hold.
9. **Built from frappe**: the workspace is frappe's, and its blocks should
   stay frappe's: each number a `Number Card` of type Custom (a whitelisted
   method that counts for the reader), and the workspace part a
   `Custom HTML Block`, so the page stays editable in frappe's workspace
   editor.

Your word: build it.

Done:

- **Today**, for everybody: five of frappe's `Number Card`s of type Custom,
  each a method in `one/home.py` that counts for the reader and says where
  a click goes. Tasks Due or Late (OneTask's own `mine.tasks`, overdue and
  today) opens My Tasks; Meetings Today (OneCalendar's `events.mine`) the
  calendar; Documents Waiting (OneIntake's `inbox.counts`) the inbox on
  Waiting; OneAI Suggestions the reader's proposals still Proposed; and
  Approvals Waiting, leave and expense claims where the reader is the
  approver, the list with most of them.
- **The Workspace**, for administrators: a `Custom HTML Block` (`One Needs
  You`, a fixture) limited to Workspace Administrator, filled by
  `home.attention`. It reads only what the workspace keeps (the account's
  copy, its mailboxes, its holiday list), draws each as espresso's yellow
  alert linking to where it is fixed, and hides itself when nothing needs
  them. The thresholds are the notices' own (`account.LOW`,
  `account.NEARLY_FULL`).
- The "One" heading and the empty onboarding block are gone; Getting
  Started stays where it floats.
- **OneAI**: the page sentence, **What needs me today?** and `my_day`.
- `one/README.md` has **Home**.
- Checked with a mailbox made to fail for a moment: the block showed it,
  and went when it was cleared.

### OneMail

OneMail is its own page (`public/js/onemail.js`): the mailboxes and their
folders on the left, the conversations in the middle, the reading pane on
the right, and frappe's own email window for writing. All nine of its
README's stages are built; the README says the AI lane waits.

1. **Notifications**: one type, **Mailbox Not Reachable**, to everybody who
   holds the mailbox, once, when it breaks. New mail is the rail's count,
   not a notice. Holds.
2. **OneAI**: the panel knows nothing on this page: no page sentence, no
   suggestions, nothing it can read about the open conversation. The one
   OneAI part is OneIntake's, below. Recommended:
   - the page sentence, naming the mailbox, the folder and the open
     conversation (only one the reader holds);
   - `open_conversation`, reading its messages as text, as the reader;
   - three suggestions: **Summarise this conversation**, **Draft a reply**
     (a card whose Approve opens frappe's email window with the reply
     written in, never sent by itself), and in a folder **What needs an
     answer?** (conversations whose last message is not ours, oldest
     first).
3. **Intake**: a mailbox's ⋯ menu has **Read with OneAI…**, asked of its
   holder, and each message OneAI read carries its panel (`.om-intake`).
   OneIntake Settings lists every mailbox. Holds.
4. **Permissions**: a message opens only for the people who hold its
   mailbox (`access.allowed`), filing it on a record never widens that
   (`linking.py`), and nobody sees into anybody's own mailbox,
   administrators included. Holds.
5. **Cross-module**: mail is filed on the customer, supplier, employee,
   lead or document it is about, with a Mail tab on each; attachments live
   in OneCloud; faces and logos come from contacts. Holds.
6. **UI and UX**:
   - a. The page is titled **Mail**; the product is OneMail.
   - b. **Reply, Reply all and Forward are there twice**: as icons in the
     conversation's head and as buttons under the last message.
     Recommended: the buttons under the message stay (where the eye is when
     it finishes reading); the head keeps star, read, move, archive, delete
     and link.
   - c. **A folded message runs its lines together**: "Hello,Please find
     our quote attached.Rana". `api.snippet` strips the HTML without
     leaving a space where a paragraph or line ended.
   - d. **Every mailbox is open**, six folders each: three mailboxes already
     fill the column. Recommended: the open mailbox unfolded, the others
     folded to their name and unread count, and what a person folds stays
     folded.
   - e. A mailbox's name is its address, cut off
     ("member.probe9x@m.4dl…."). The workspace's says **Workspace** with the
     address under it; recommended: the reader's own says **Yours**, a
     shared one its name, each with the address under it.
7. **Documented**: `one_mail/README.md` is the manual above Under the hood
   and OneAI answers from it. When the AI part in 2 is built, it gets its
   paragraph.
8. **Legal**: the clauses and subprocessors cover mail, OneCloud and faces.
   Asking OneAI about a conversation sends its text to the model, which the
   AI Addendum must say: recommended, a clause in `one_mail/legal.py`
   (only when asked, only a conversation the asker holds, nothing kept).
9. **Built from frappe**: writing is frappe's email window, dates are
   `frappe.datetime`, a new message redraws an open mailbox through
   `frappe.realtime` (`live.py`), and buttons are espresso's. Holds.

Your word: all of them, and a reply drafted from what we tell it ("turn
down their offer", "we agree only if…").

Done:

- **OneAI** (`one_mail/ai.py`): the page sentence names the mailbox, the
  folder and the open conversation, only one the reader holds. Two
  readers, `open_conversation` and `waiting_for_answer`, and a suggest,
  `draft_reply`. Three suggestions: **Summarise this conversation**, **What
  needs an answer?**, and **Draft a reply**, a new kind of suggestion
  (`fill`) that puts "Draft a reply to this conversation that says:" in
  the panel's box for the reader to finish with what the reply should say.
  The reply comes back as a card (a new proposal kind, **Reply**) showing
  it in full; **Approve** opens frappe's email window with it written in,
  addressed and quoted as Reply opens it (`OneMail.reply_to`), to be read,
  changed and sent by the reader. Nothing is sent by OneAI.
- **Legal**: the AI Addendum's `onemail-asks` says a conversation's text
  goes to the model only when asked, only from a mailbox the asker holds,
  and that a drafted reply is never sent by OneAI. AI Addendum revision 3,
  so administrators agree again.
- **The title** is OneMail.
- **Reply, Reply all and Forward** are under the last message only; the
  head keeps star, read, move, archive, delete and file.
- **A folded message** keeps a space where each paragraph or line ended.
- **Mailboxes fold**: only the one open is unfolded, a folded one shows
  its unread count, and what a person folds or unfolds is kept in frappe's
  user settings (not the browser, which the borrowing guard refuses).
- **Mailbox names**: **Workspace**, **Yours** or a shared one's address,
  each with its address under it.
- `one_mail/README.md` has **Asking OneAI**; the line saying the AI lane
  waits is gone.
- Checked without a model: every reader and the card on the dev site, the
  chip filling the box, and Approve's email window with the reply in.

Then, on your word: **mail when storage is full**. Before, an attachment
the store refused failed the whole message, and it was lost. Now:

- The message always arrives. Each attachment is saved on its own
  (`inbound.Arrival.save_attachments_in_doc`, a savepoint each); one the
  store refuses as full (`store.NoRoom`, from the admin site's `NoRoom`) is
  written on the message (`one_unsaved`) instead.
- The reading pane shows it as an amber chip, **Not saved, storage is
  full**.
- **Attachments Not Saved**, a new notification type, to every
  administrator and everybody who holds the mailbox, once a day at most,
  linking Plan and Credits.
- `one_mail/room.py` `again`, hourly, reads the message back (from R2 on
  the workspace's address, from the server on a connected mailbox), saves
  what now fits and clears the mark.
- `README.md` says so under Attachments and faces.
- Checked on the dev site: a message arriving to a full store kept its text
  with the attachment marked and told both people; the hourly run saved it
  and the chip became the file.

Then, on your question "does writing an email have AI text tools": it did
not. Forms have the OneAI mark on every prose field, but the email window
is a dialog, so it never got one. Now (`oneai.js` `compose`):

- The mark sits beside **Message** in frappe's email window, wherever it is
  opened. It points the panel at Communication's own `content` field, so it
  is the same check (`touch.target`), the same card and the same Approve.
- The panel offers Improve it, Make it shorter, Make it longer, Make it
  more formal, Make it friendlier, Fix spelling and grammar, and
  Translate… (finished in the box). On an empty reply, Write a first draft
  and Reply saying….
- The model gets what is written, the subject, the recipients and the
  message replied to (`touch._email`), never the signature. Approve
  replaces only what was written; the signature and the quote stay
  (`oneai.parts`, `oneai.rewrite`). Nothing is saved on the server.
- The panel sits above the window's backdrop, and on a wide screen the
  window moves left to make room.
- Legal: `onemail-asks` says what goes to the model; AI Addendum
  revision 4.
- README: under Asking OneAI. Checked in the browser without a model: the
  mark, the chips, and a card applied into the window with the signature
  and quote kept.

### OneCloud

OneCloud is its own page (`public/js/onecloud.js`, 2,145 lines): an
explorer with a tree on the left (My Files, Recent, Starred, Shared with Me,
Libraries, Company, Records, Mail, Network, Requests, Recycle Bin), the
folder in the middle, and a preview pane with details and activity on the
right. The same explorer opens as a record's Files tab and as the picker.

1. **Notifications**: nine types. Shared with you, added to a library,
   file requests (sent, reminded, answered, complete), uploads through a
   link, a link shared with an address, and its code. Storage Nearly Full
   is One's, and Attachments Not Saved is OneMail's. They read well. Holds.
2. **OneAI**: the panel knows only that this is "Files": no page sentence,
   no suggestions, nothing about the open folder or the selected file. The
   only OneAI part is OneIntake's **Read with OneAI…** on a folder.
   Recommended:
   - a page sentence naming the open folder and the selected file (only
     what the reader may open);
   - a reader, `open_file`, that reads a text, PDF or office file's text as
     the reader;
   - suggestions: with a file selected, **Summarise this file** and **Who
     can see this?**; in a folder, **Find a file…** (a fill chip, "Find the
     file that…", searched by meaning through OneIntake's search) and
     **What is taking the space?**.
3. **Intake**: **Read with OneAI…** turns reading on for a folder, and a
   file OneAI read carries its panel. But the item is on every file's menu
   too, greyed out, because it only works on a folder. **Connect as a
   drive…** is the same. Recommended: hide what cannot apply to a file,
   and on a file offer **Read with OneAI** once, for that file.
4. **Permissions**: My Files is the owner's; Shared, Libraries and Company
   follow their members and roles; anybody on the team may connect a
   server under Network, for themselves or shared with the team, and only
   its owner or an administrator changes it; Storage Check is for
   administrators; a record's files follow the record. Two leaks:
   - **Records counts every file of a type**, not what the reader may
     open: "Employee 3" shows to somebody who may open one employee. The
     list under it is filtered (`get_list`); the count is not
     (`record_doctypes`). Recommended: count what they may read, or show no
     count.
   - **Records lists AI Chat and ToDo**: a OneAI conversation's uploads
     and an assignment's are not "records" anybody files by. Recommended:
     add both to `UNLISTED`.
5. **Cross-module**: mail attachments are under Mail, record files under
   Records, OneWriter and OneWorkbook open from here, and OneIntake reads
   folders. Two gaps:
   - **New has no Document or Workbook**: only folder, upload and file
     request. Recommended: **Document** and **Workbook** in New, made in
     the open folder and opened in their window.
   - Record types show their doctype names ("ToDo", "AI Chat"); the rest
     of One calls them what the product calls them.
6. **UI and UX**:
   - a. The page is titled **Files**; the product is OneCloud (as Mail was
     for OneMail).
   - b. With nothing selected, the preview pane is a large empty column
     saying "Select a file to preview it." Recommended: the folder's own
     details there (items, size, who can see it, reading on or off), which
     is what Windows and Drive show.
   - c. Requested files land in a folder named after the sender's address
     ("vendor@example.org") in the folder the request was made in, so My
     Files fills with email addresses. Recommended: one folder per request,
     named after it, with a folder per sender inside it named by their
     name.
7. **Documented**: `one_storage/README.md` covers finding your way,
   sharing, libraries, versions, the drive, servers, requests and limits.
   Nothing says what OneAI does here (Read with OneAI is not mentioned).
   Recommended: an **Asking OneAI** section, with 2 and 3.
8. **Legal**: R2 is a subprocessor and `onecloud-files` says where files
   are kept. Not said anywhere: that files can be shared outside the
   workspace by link, and that people outside can upload through a file
   request, so the workspace holds what third parties send. Also that a
   connected server's password is kept, encrypted, to reach it. Recommended:
   a clause `onecloud-outside` in the privacy notice, and, if 2 is built,
   a line in the AI Addendum that a file's text goes to the model when
   asked.
9. **Built from frappe**: dialogs are `frappe.ui.Dialog`, and changes
   arrive through `frappe.realtime` (`doctype_subscribe("File")`,
   `onecloud_change`). But the desk ships parts this page draws by hand:
   - the right-click menu is ours (`menu()`), and frappe has
     `frappe.ui.ContextMenu`;
   - the New menu is ours, and frappe has `frappe.ui.Dropdown`;
   - every toolbar button is hand-written `es-button` markup rather than
     `frappe.ui.button.html`;
   - the crumbs are hand-written `es-breadcrumbs` rather than
     `frappe.ui.breadcrumbs`;
   - the empty preview is ours, and frappe has `frappe.ui.empty_state`;
   - the search box is a bare `<input>` rather than a frappe control.
   The path box and the rename-in-place box are explorer parts frappe has
   no equivalent for, so they stay ours, drawn like a frappe-ui TextInput.
   Recommended: move each of the six onto frappe's part.

Your word: all of them.

Two findings were wrong, and are corrected here rather than built:
- **New › Document and Workbook** cannot be built yet: OneWriter and
  OneWorkbook are not rebuilt in OneDesk (only their marks are here), so
  there is no window for a new document to open in. It waits for them.
- **The empty state** was already frappe's (`onedesk.shell.empty` is
  `frappe.ui.empty_state`).

Done:

- **OneAI** (`one_storage/ai.py`): the page sentence names the open folder
  and the chosen file, only what the reader may open (`OneCloud.here`,
  sent by `oneai.where` as the page's folder and record). Three readers:
  `open_file` (what OneIntake read of it, or read now; a scan says to use
  Read with OneAI), `who_can_see` (owner, people, through a folder, links
  without their key) and `largest_files` (the reader's own, and how full
  the workspace is). Suggestions: in a folder **Find a file…** (a fill
  chip, searched by `find_documents`) and **What is taking the space?**;
  with one file chosen (section `file`) **Summarise this file**, **Who can
  see this?** and **Find a file…**. An open panel is told when the chosen
  file changes.
- **Intake**: folder-only rows are no longer shown on a file. A file has
  **Read with OneAI**, which reads that one file now as the person asking
  (`switches.read_now`, `pipeline.read_file(person=)`); a message's
  attachment is read with its mailbox.
- **Records** counts only files on records the reader may open
  (`_readable_files`, through `get_list`), and no longer lists AI Chat or
  ToDo.
- **File requests** make a folder of their own named after the request,
  where they were made, with a folder per person named by their contact's
  or user's name (`_where`, `_called`).
- **The title** is OneCloud.
- **The preview pane**, with nothing chosen, shows the folder: its folders,
  files and size, and for a folder of ours its owner, who it is shared
  with and whether OneAI reads it.
- **Frappe's parts**: the right-click menu is `frappe.ui.ContextMenu`, New
  is `frappe.ui.Dropdown`, every button (toolbar and dialogs) is
  `frappe.ui.button.html`, Details or Tiles is `frappe.ui.tab_buttons`, the
  crumbs are `frappe.ui.breadcrumbs`, and the search box is a frappe Data
  control through a new shared `onedesk.shell.search` (OneMail's box can
  move onto it next). The hand-drawn menu and its CSS are gone.
- **Legal**: `onecloud-outside` in the Privacy Policy (links, file
  requests, a connected server's password), revision 5; `onecloud-asks`
  in the AI Addendum, revision 5.
- **README**: an **Asking OneAI** section; the request folders.
- A guard, `tests/test_onecloud_ai.py`. Checked in the browser: the title,
  the folder pane, a file's and a folder's menus, New, the panel's
  suggestions with a file chosen, Records; `open_file` read a fresh file
  on the dev site. No model was called.

### OneCalendar

OneCalendar is its own page (`one_calendar/page/onecalendar`): the layers on
the left in two groups, Mine and Workspace, and frappe's own FullCalendar on
the right with Month, Week, Day and List. Every dated thing in One is a
layer read as the reader (`layers.py`); nothing is copied. Add Event makes a
frappe Event, Subscribe gives a private link for Google, Apple or Outlook,
and a record's own calendar is the same page with `?doctype=&name=`.

1. **Notifications**: One sends nothing about events.
   - Nobody is told they were invited, or that an event they are on moved
     or was cancelled.
   - The only mail is frappe's own morning digest, "Upcoming Events for
     Today" (`send_event_digest`). It goes around One's notification hub,
     in frappe's template, and it leaves out events you are only invited
     to (frappe's `get_events`). Settings calls it "Mails you before an
     event of yours starts", which it does not do.
   - frappe's Event has a reminders table (a notification some minutes
     before), but nothing sends it.
   Recommended: four types in `one_calendar/notifications.py`, through the
   hub: **Invited to an Event** (to each person added, with when and where),
   **Event Changed** (its time or place, to everybody on it), **Event
   Cancelled**, and **Starting Soon** (from the event's reminders, default
   ten minutes before, as a push and in the bell). And the morning digest
   as One's own **Today's Events**, from `events.mine`, replacing frappe's.
2. **OneAI**: the panel knows only that this is "Calendar": no page
   sentence, no suggestions, nothing it can read. Recommended:
   - a page sentence naming the days shown (and the record, on a record's
     calendar);
   - a reader, `my_calendar(start, end)`, which is `layers.entries` as the
     reader;
   - a reader, `busy_times(people, start, end)`, when colleagues are busy
     and never what the event is;
   - a suggest, `plan_event`: a card that makes the event when approved;
   - suggestions: **What is on this week?**, **Find a time to meet…** (a
     fill chip, "Find a time this week to meet "), and **Plan my day**.
3. **Intake**: an invitation OneIntake reads (an `.ics` in mail or a file)
   becomes an event shared with the person it is for (`planning.make_event`),
   and OneIntake's deadlines are a layer. Holds.
4. **Permissions**: each layer reads as the reader; an event about a record
   is seen by the record's readers and opens the record; Public is kept to
   Workspace Administrator and HR Manager on save (`events.validate`);
   Who's Off needs leave to be readable. Holds.
5. **Cross-module**: tasks, projects, deals and leads, leave and
   interviews, maintenance, and OneIntake's deadlines are all layers; a
   project, deal, lead or employee has a Calendar button. Two gaps:
   - **The workspace's days off are not on it**: Holidays shows the
     holiday list without the weekly days off, and a weekend looks like any
     other day. Recommended: holidays and weekly days off drawn as a shaded
     background, as the desk shades non-working hours.
   - **An event has no people from the calendar**: inviting somebody means
     opening the event's own form. Recommended: **Invite** in Add Event
     (team members by name, shared with them; outside guests by address,
     as participants), and outside guests mailed an invitation with the
     `.ics` so it lands in their own calendar.
6. **UI and UX**:
   - a. The page is titled **Calendar**; the product is OneCalendar.
   - b. **Clicking an event leaves the calendar** for frappe's Event form.
     Recommended: a small card on the event (`frappe.ui.Popover`) with
     when, where, who, the description, a Join link when there is one, and
     Open and Delete; the form stays one press away.
   - c. The page does not update while it is open: an event somebody adds
     or moves appears only on reload.
7. **Documented**: `one_calendar/README.md` is the manual above Under the
   hood and OneAI answers from it. When 1, 2 and 5 are built they get their
   paragraphs.
8. **Legal**: `calendar-link` covers the subscription. Not said: that
   frappe's **Google Calendar** connection (Setup) sends events to the
   Google account it is connected to, both ways, and a Meet link is made by
   Google. Recommended: a line in `calendar-link`'s document, and, if 2 is
   built, the AI Addendum says a calendar is read when asked, and that busy
   times are read without what they are.
9. **Built from frappe**: FullCalendar is the one frappe bundles, the
   toolbar is the desk calendar's own (`frappe.ui.button`,
   `frappe.ui.TabButtons`, `frappe.ui.Popover` date jumper), Add Event is a
   `frappe.ui.Dialog`, and the layers and view are frappe user settings.
   Two things are not:
   - **the layer switches are bare `<input type="checkbox">`**, and
     frappe's Check control is the part;
   - **nothing listens on `frappe.realtime`** (6c): frappe's
     `doctype_subscribe("Event")` and `list_update` are how a screen hears
     of a change.

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
