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
moment any clause does. `tests/test_legal.py` holds every document's hash. When
a clause changes the test fails, and there are two ways out: bump the revision
(material), or record the new hash (a typo).

**Every outside company One calls is declared.** `tests/test_legal.py` finds
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
