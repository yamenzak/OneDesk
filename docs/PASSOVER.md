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
| Settings, You | Notifications | next, after Agreements |
| Settings, You | Mail | |
| Settings, You | Calendar | |
| Settings, You | Sign-in | |
| Settings, You | What OneAI Remembers | |
| Settings, You | Agreements | built, waiting for your word |
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
