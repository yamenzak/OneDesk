# The passover

Every screen of One, one at a time, checked against six points. You decide when
a screen is done and when the next one starts. This file is where each screen's
findings and fixes are written down.

## The six points

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

## Everything follows frappe

This applies to every screen, on top of the six points. How a screen looks can
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

## How one screen goes

1. Screenshot it and read the code behind it.
2. Write the findings under the six points below.
3. Fix them, look again in the browser, and run the gates.
4. Commit, push, and show you a screenshot.
5. Wait for your word before the next screen.

## Where we are

| Area | Screen | State |
|---|---|---|
| Settings, You | Profile | the four gaps closed, waiting for your word |
| Settings, You | Notifications | next |
| Settings, You | Mail | |
| Settings, You | Calendar | |
| Settings, You | Sign-in | |
| Settings, You | What OneAI Remembers | |
| Settings, Workspace | General | |
| Settings, Workspace | People | |
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

### Profile

1. **Notifications**: nothing is sent when a person changes their own details.
   The employee record keeps the change in its history, where HR sees it.
   Whether HR should also be told about a new address or emergency contact is
   open.
2. **OneAI**: nothing here. What OneAI knows about a person is its own screen,
   What OneAI Remembers.
3. **Intake**: nothing yet. Later, a proof of address that Intake reads could
   offer to update the address here.
4. **Permissions**: a person changes their own login, and only the Profile
   fields. On their employee record they may change how to reach them, the
   emergency contact, marital status and blood group. That record is only ever
   the one whose `user_id` is theirs. Their job and their bank account are
   shown but never written, and the account shows only its last four
   characters. `tests/test_settings.py` holds this.
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
