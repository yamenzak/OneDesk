# OneLegal

Written by hand. The agreements a workspace runs under, and how you are asked
to agree to them. Everything above **Under the hood** is for the people using
One, and OneAI reads it to answer questions about the agreements. Under the hood
is for the people who build it.

This is our own drafting, not a lawyer's, written from what One actually does.

## The agreements

One runs under eight documents:

- **Terms of Service**: the agreement between your organisation and Four Degree
  Labs.
- **Acceptable Use Policy**: what One may not be used for.
- **Privacy Policy**: what happens to personal data, yours and the personal
  data your organisation puts into One.
- **Cookie Policy**: what One keeps on your device.
- **Data Processing Addendum**: how we handle personal data your organisation
  is responsible for.
- **Subprocessors**: every other company that receives data from your
  workspace, what it receives, and where it keeps it.
- **AI Addendum**: how OneAI and Intake work, which models run, and what
  happens to what they read.
- **Open Source and Third-Party Notices**: the software One is built from.
  Nobody is asked to agree to this one.

Read any of them on the **Agreements** page, at `/app/legal`. Every version
somebody agreed to is kept, so you can always read exactly what was agreed.

## Who agrees to what

**Your organisation's agreements** (Terms of Service, Data Processing Addendum,
Subprocessors and AI Addendum) are agreed by one of your workspace's
administrators, on the organisation's behalf. One administrator agreeing is
enough for everybody.

**Your own** (Privacy Policy and Cookie Policy) are about your personal data, so
nobody can agree to them for you. Everybody who signs in agrees to them once.

**The Acceptable Use Policy is both**: your organisation promises it, and each
person agrees to it.

## When you are asked

The first time you sign in, and again whenever a document changes in a way that
matters, One asks before you carry on. The documents are listed, each opening in
a new tab so you can read it, with an **Updated** mark on any that changed since
you last agreed. Tick the box and press **Agree**.

If your workspace's own agreements are still waiting for an administrator, One
tells you so and opens once they have agreed. You cannot agree to those for
them.

What is recorded is not just "yes": it is the document, its exact version, the
time, the account, and the network address it came from.

## Connections

- **From One**: The Privacy Policy says what One keeps about people, such as profiles, notifications, sign-ins, the audit log and the Recycle Bin.
- **From OneAdmin**: The days a workspace keeps working after a failed payment or a closing come from OneAdmin. The Subprocessors list names the companies that host One and take payment.
- **From OneAI**: The Subprocessors list names the companies that run OneAI's models. The Privacy Policy says what is kept of a conversation with OneAI.
- **From OneMail**: The Subprocessors list names who sends the workspace's mail. It also names where people's pictures and organisations' logos come from.
- **From OneCloud**: The Subprocessors list says where files are stored. The Privacy Policy covers links and file requests for people outside the organisation.
- **From OneIntake**: The AI Addendum says that Intake acts on what arrives without being asked each time.
- **From OneHR**: The Privacy Policy says what is kept when somebody clocks in, such as where they are and sometimes a photo.
- **To One**: Settings shows each agreement, its version, and who agreed to it and when.
- **To OneAI**: OneAI answers questions about the agreements from their current text.

## Under the hood

For the people who build OneLegal. OneAI does not read past this heading.

**Each module declares what follows from what it does**, in its own `legal.py`
beside the code the clause is about: `clause()` for a paragraph of a document,
`subprocessor()` for a company it sends data to. `assemble.py` puts them into the
documents. So adding a supplier is a line in the module that uses it, and the
Privacy Policy and the Subprocessors list change with it.

| File | What it does |
|---|---|
| `registry.py` | `clause()` and `subprocessor()`, and the order they come out in |
| `documents.py` | Who we are (`PARTY`), each document's sections, audience and revision |
| `legal.py` | The text true of One as a whole |
| `<module>/legal.py` | That module's clauses and suppliers |
| `assemble.py` | Declarations into text and HTML, and the version |
| `gate.py` | Who has agreed to what; `outstanding`, `accept`, `require` |
| `reading.py` | What the Agreements page asks for |
| `page/legal`, `../public/js/legal.js` | The Agreements page, and the dialog that asks |
| `Legal Document Version`, `Legal Acceptance` | Every agreed version's text; every acceptance |

**A version is `revision.hash`.** `revision` is a number in `documents.py`, bumped
when a change is material, and bumping it makes everybody agree again. `hash` is
eight hex characters of a SHA-256 over the assembled plain text, so it moves the
moment any clause does. `tests/guards/test_legal.py` holds every document's hash. When
a clause changes the test fails, and there are two ways out: bump the revision
(material), or record the new hash (a typo).

**Every outside company One calls is declared.** `tests/guards/test_legal.py` finds
every `https://` host the Python calls, and fails on one not mapped to a declared
subprocessor (or listed as not receiving customer data). Declaring a new
supplier changes the Subprocessors list's hash, so it is a decision, not an
accident.

**Ported from OneApp's `onelegal`**, with OneDesk's facts:

- The lifecycle periods are read from `one_admin/ladder.py`.
- Intake's acting without being asked is said in the AI Addendum.
- Nothing is promised that is not built yet (a full backup from the settings,
  a storage overage grace period).

**Still to confirm**, as the passover reaches the screens concerned:

- Encryption at rest of the platform's backups.
- How long sign-in and error records are kept.
- Inbound mail through Cloudflare Email Routing, when it is turned on.

**The passover adds each screen's lines** (docs/PASSOVER.md, point 8).

### __init__.py

Each module declares the clauses that follow from what it does, in its own
`legal.py` beside the code the clause is about, and OneLegal assembles them into
the documents a person is shown and asked to agree to. The package deliberately
imports nothing: `registry`, `documents`, `legal` and `assemble` are pure, so the
tests can assemble every document and check its hash without a site.

### registry.py

What a module declares, and where it declares it. Two kinds of declaration, both
made from the module the fact belongs to:

* a **clause**: a paragraph that has to appear in one of the documents, because
  of something that module does;
* a **subprocessor**: a third party that module hands customer data to.

Both are registered by calling a function at import time from
`<module>/legal.py`. Import time rather than a scan of the source, because a
clause that has to be found by a regular expression is a clause somebody will
break by reformatting it.

The ordering is deliberate and dull: within a section, clauses come out in
`(order, module, key)` order. A stable order means the assembled document's hash
only changes when the *text* changes, so a version bump means what it says.

`subprocessor()` takes everything a subprocessor list has to say and nothing it
does not: who they are, what for, what they get, where that sits, and what makes
the transfer lawful. One company is one row with several uses, because "who are
your subprocessors" is a question about companies. What a company *does* varies
by use and so does where it does it (Cloudflare keeps a workspace's files in the
region it chose and runs a model on whichever of its locations is nearest), so
`where` belongs to the use. The safeguard is the contract we have with the
company, so that belongs to the company, and declaring two different ones is an
error rather than a second row.

### assemble.py

Declarations plus documents into one rendered page, and the version that names
it. The version is the whole point of the file. It is `revision.hash`:

* `revision` is a number in `documents.py` that a person bumps when a change is
  material. Bumping it is what makes every workspace agree again.
* `hash` is the first eight hex characters of a SHA-256 over the assembled text.
  Nobody types it. It changes the moment any clause anywhere changes, which is
  how `tests/guards/test_legal.py` can tell a typo from a new subprocessor and insist
  somebody says which.

So a document that has drifted without a bump fails the suite, and a document
that has been bumped is a document everybody re-agrees to. Neither can happen by
accident, and that is the difference between a legal page and a legal system.

### documents.py

The documents themselves: who we are, what each one is for, and where its
clauses go. The text comes from two places: `legal.py`, for what is true of One
as a whole, and each module's own `legal.py`, for what follows from what that
module does. What is in `documents.py` is the frame they are slotted into.

**Revisions.** Each document carries a `revision`. Bump it when a change is
material: a new subprocessor, a changed retention period, anything that alters
what somebody agreed to. Do not bump it for a typo. `tests/guards/test_legal.py` carries
the hash of every document's assembled text and fails when the text moves, so
the choice is always made on purpose: either "this is material, everybody agrees
again", or "this is a typo, record the new hash".

**Audience.** Two, and the split is why One asks twice.

- `customer`: the organisation. Accepted by a workspace administrator, whose
  acceptance binds the organisation and everybody in it.
- `user`: the person. Accepted by everybody who signs in, because a privacy
  notice is about *their* personal data, and an employer cannot agree to that
  for them.

The acceptable use policy is `both`: the organisation promises it, and each
person acknowledges it.

**What each revision changed**, for the documents whose history is kept here
(the newest is also beside the number in `documents.py`):

- Terms of Service: 7, credits we give by hand, their expiry, and taking back a
  mistake. 8, first agreed on the signup page, before payment. 9, closing a
  workspace yourself, and the full download. 10, extensions OneAI writes and an
  administrator turns on; record types. 11, extensions on One's own pages and on
  a schedule, tried once before they are kept.
- Privacy Policy: 2, push. 3, a calendar link. 4, where a person is signed in.
  5, OneCloud's links, file requests and servers. 6, OneCalendar's guests and
  Google. 7, OneAI reads an organisation's account. 8, the signup page. 9, the
  One account. 10, the Recycle Bin. 11, the Audit Log. 12 to 14, your data
  copied or deleted. 15, webhooks. 16, who read an announcement. 17, a project's
  Featured Media opens for anybody with its link. 18, attendance on a project's
  site becomes time on the project. 19, users' and employees' pictures from
  Gravatar, the company's logo. 20, the outside people named on a project.
  21, Workload's hours, lowered by approved leave without saying why. 22, a
  project's Time view shows each person's hours, and their cost only to those
  who see timesheet rates.
- AI Addendum: 5, OneAI reads a file in OneCloud when asked. 6, OneAI reads your
  calendar, and colleagues' busy times. 7, OneAI reads your tasks, and suggests
  tasks and their steps. 8, OneAI writes extensions, read a second time, and
  designs record types. 9, OneAI mends an extension from its errors, which can
  carry record data. 10, an extension tried once on a record, and what happened
  told to OneAI. 11, OneAI reads a project when asked, and suggests its tasks.
  12, OneAI reads a project's money with its customer and suppliers. 13, OneAI
  reads a project's outside contacts, and drafts a reminder, a member or a
  contact for you to approve. 14, OneAI reads the team's week as Workload
  shows it. 15, OneAI suggests a new project, made only when you approve it. 16, OneAI
  suggests a project's status and its milestones. 17, OneAI reads a project's
  time by person, and suggests time on your timesheet and a cost type's
  budget. 18, OneAI reads a task as its page shows it, with the hours each
  person logged on it. 19, OneAI suggests a change to a task, made only when
  you approve it.

### gate.py

Who has agreed to what, and who may not carry on until they do. Two parties,
because two different things are being agreed to and only one of them can be
agreed to by somebody else.

* **The workspace.** The Terms of Service, the Data Processing Addendum, the
  Subprocessors list and the AI Addendum are a contract with the organisation.
  The person who creates the workspace accepts them, and that binds everybody in
  it. One acceptance covers the workspace.
* **The person.** The Privacy Policy and the Cookie Policy describe the handling
  of *their* personal data, and an employer cannot agree to that on their
  behalf. Every person who signs in accepts those for themselves, once, and
  again whenever the version changes.

The Acceptable Use Policy is both: the organisation promises it and each person
acknowledges it, because it is the one document that describes what an
individual may not do.

What is recorded is not "yes": it is the document, the exact version, the text
that version hashed to, the account, the time, and the address it came from.
`Legal Document Version` keeps the rendered text of every version anybody has
ever agreed to, so the question "what did I agree to in March" has an answer.

`SHOWN` lists each document's title and summary, for the dialog to show in the
reader's language. They are listed in `gate.py` rather than marked in
`documents.py`, because the version is a hash of the text: a translated title
there would give every language a different version. The documents themselves
are in English, which governs.

### legal.py

OneLegal's own clauses: the part of each document about One as a whole. Every
other module's `legal.py` says something about that module. This one says what
is true of the product, the company and the contract, and it is the file to read
first to know what a customer is agreeing to.

Our own drafting from what the product does, not a lawyer's. Ported from
OneApp's `onelegal/legal.py` and corrected for what OneDesk actually does:

- Intake writes without being asked each time, so "nothing is written without
  somebody asking" is gone.
- The full download (one/closing.py) is offered to whoever pays, not promised as
  a backup.
- The lifecycle's periods are read from `one_admin/ladder.py` rather than typed
  here, so the Terms say what the code does.

Anything not yet confirmed against a screen is left out rather than guessed at.
The passover (docs/PASSOVER.md, point 8) adds each screen's lines as it reaches
them.
