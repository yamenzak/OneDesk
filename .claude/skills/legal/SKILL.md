---
name: legal
description: How to write and change what One agrees to — a module's clauses and subprocessors in its legal.py, the optional services, a change that takes effect on a set day, and the revision that makes people agree again. Load it before touching any legal.py, trust_center/, a clause, a subprocessor, a service, a host the code calls, or anything that changes what data leaves One, where it goes or why.
---

# Legal

What One promises is the code's to keep, so it is written beside the code
that keeps it: every module declares its own part in its own `legal.py`,
and `trust_center/assemble.py` puts the parts into the eight documents
(Terms, Acceptable Use, Privacy, Cookies, DPA, Subprocessors, AI Addendum,
Licences) that people read in TrustCenter and agree to.

## The words

Precise and plain, which is what the GDPR asks of us (Art. 12):

- **We** is Four Degree Labs and **you** is the organisation, or the person
  where a policy is theirs. Never "the Company", "the Customer", "the
  Provider".
- **One point to a sentence,** none over 30 words. A list of what is sent
  is one point.
- **A number where there is one:** 72 hours, 30 days, two months.
- **No legalese:** not shall, herein, hereby, thereof, whereas, pursuant
  to, notwithstanding, aforementioned, forthwith, in no event.
- **Nothing promised that isn't built,** and nothing built that the words
  leave out: if the code sends it, a clause says so.
- **English only.** What is agreed to is the words; a translation would be
  a second text. TrustCenter's screens around them are translated.

## What a module declares

In `<module>/legal.py`, through `trust_center/registry.py`:

- `clause(document=, section=, key=, module=, body=, meets=…)`: one
  paragraph of one document. `meets` names the duties in
  `trust_center/laws.py` it answers (`"gdpr.13"`); every duty there is met by
  at least one clause.
- `subprocessor(name=, purpose=, data=, where=, safeguard=, …)`: a company
  that receives customer data, what for, what it gets, where, under what
  safeguard. A host the code calls that no subprocessor or service names
  fails the guard.
- `service(key=, title=, does=, sends=, off=, hosts=)`: something sent out
  only once an administrator turns it on and agrees, off by default
  (Art. 25); only `services.call` may reach its hosts.
- `switchover(key=, document=, revision=, does=, hosts=)`: a change One
  can't work without, announced ahead. The old way runs until the day the
  published change says it takes effect, the new way from it, and both go
  `CLEAN_DAYS` later.

## Changing what is agreed

Any change to a clause moves the document's hash, and `test_legal.py`
fails until one of two things is done:

- **A typo or a clarification** that changes nobody's rights: record the
  new hash. People are not asked again.
- **A real change**: bump the document's revision, which asks every
  workspace to agree again, and publish the change in `documents.CHANGES`
  with the day it takes effect, far enough ahead for the notice the
  agreement promises (a new subprocessor in advance, with a chance to
  object). Decide which with the user; it is never Claude's call.

The module's version records `legal:` (the `changelog` skill); its words
say what changed for the reader in plain terms, never the clause.

## Claude's legal habits, and what to do instead

- **Writing the clause after the code.** The code that sends data and the
  clause that says so are one commit.
- **Promising more than is built:** "encrypted end to end", "deleted
  within 24 hours", when it isn't. Say exactly what happens.
- **Legal tone.** Long sentences, "shall", "reasonable efforts". Write it
  as the rest of One is written, shorter.
- **Recording a hash to make the guard pass** when the change was real.
- **Naming laws we haven't read.** `laws.py` is our reading, not a
  lawyer's; add a duty there only with its article and the user's say.

## Before handing back

    python3 -m pytest -q tests/guards/test_legal.py

Then open TrustCenter, read the module's part of each document as the
person agreeing to it, and say in your reply whether this changes what
people have agreed to, and which way (recorded hash or new revision).
