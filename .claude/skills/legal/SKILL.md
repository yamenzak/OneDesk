---
name: legal
description: How to write and change what One agrees to — a module's clauses and subprocessors in its trust.py, the optional services, a change that takes effect on a set day, and the revision that makes people agree again. Load it before touching any trust.py, trust_center/, a clause, a subprocessor, a service, a host the code calls, or anything that changes what data leaves One, where it goes or why.
---

# Legal

What One promises is the code's to keep, so it is written beside the code:
each module declares its part in its own `trust.py`, and
`trust_center/assemble.py` puts the parts into the eight documents
(`trust_center/documents.py`) people read in TrustCenter. Point 19 holds it (`python3 scripts/lint.py --point 19`); `docs/READY.md`,
TrustCenter, is the mechanism.

## The words

Precise and plain, as GDPR Art. 12 asks (`agreements-plain`):

- **We** is Four Degree Labs, **you** the organisation, or the person
  where a policy is theirs. Never "the Company", "the Customer".
- **One point to a sentence,** none over 30 words; a number where there is
  one (72 hours, 30 days).
- **No legalese:** shall, herein, hereby, thereof, whereas, pursuant to,
  notwithstanding, forthwith, in no event.
- **Nothing promised that isn't built,** and nothing built the words leave
  out (`nothing-promised`): if the code sends it, a clause says so.
- **English only.** A translation would be a second text; TrustCenter's
  screens around it are translated.

## What a module declares

Through `trust_center/registry.py`, each with its `module=`:

- `clause(document=, section=, key=, body=, …)`: one paragraph of one
  document, in a section the document has (`clauses-in-sections`); its
  `meets` names the duties in `trust_center/laws.py` it answers, and every
  duty is met (`duties-met`).
- `subprocessor(name=, purpose=, data=, where=, safeguard=, …)`: a company
  that receives customer data. A host the code calls that nothing names
  fails `subprocessors`; a model's runner, `model-runners-declared`.
- `service(key=, title=, does=, sends=, off=, hosts=)`: sent out only once
  an administrator turns it on, off by default (Art. 25); only
  `services.call` reaches its hosts (`services-call`).
- `switchover(key=, document=, revision=, does=, hosts=)`: a change One
  can't work without, announced ahead; the old way runs until the
  published day (`switchover-day`).

## Changing what is agreed

A changed clause moves its document's hash, and `legal-version` fails until
it is settled one of two ways:

- **Record the new hash** in `tests/guards/test_legal.py` `VERSIONS`.
  Nobody is asked again. Until One is ready for production
  (`ready.PRODUCTION`, false today) every change is settled this way:
  nobody has agreed to anything yet, so `documents.CHANGES` stays empty.
- **A new revision**, once in production, for a real change: every
  workspace agrees again, and the change is published in
  `documents.CHANGES` with the day it takes effect, at least the notice
  the agreement promises ahead (`change-ahead`). Which way is the user's
  call, never Claude's.

The module's version says what changed for the reader, never the clause
(the `changelog` skill, `legal-said`).

## Claude's legal habits

- **Writing the clause after the code.** The code that sends data and the
  clause that says so are one commit.
- **Promising more than is built:** "encrypted end to end", "deleted
  within 24 hours", when it isn't. Say exactly what happens.
- **Naming laws we haven't read.** `laws.py` is our reading, not a
  lawyer's; a duty is added only with its article and the user's say.

## Before handing back

`../../env/bin/python scripts/lint.py`, then open TrustCenter, read the
module's part of each document as the person agreeing to it, and say
whether this changes what people agreed to, and which way.
