# Intake samples

Real mail and files that arrive at the demo company, Sahara Glass &
Aluminium, one folder per app whose records they make. The demo's intake step
has Intake handle each one as it arrives and keeps what it made, so the Intake
inbox, its drafts and its marks have real documents in them. The build stops
at a sample that does not make what it says, and the demo suite
(`onedesk/one_demo/check.py`, `every_intake_sample_left_what_it_should`) reads
it all back.

A sample is two files with the same name:

- the document itself: a mail as it arrives (`.eml`, with its attachments), or
  a file dropped in the accounts team's Bank Statements folder;
- a `.json` saying what Intake makes of it, and what a model answered about
  it.

```json
{
  "file": "enquiry.eml",
  "answers": {
    "intake_look": {"verdict": "Action", "why": "...", "about": []},
    "intake_read": {"kind": "Inquiry", "...": "..."},
    "intake_audit": "right"
  },
  "makes": [
    {"doctype": "Lead", "values": {"company_name": "Creek View Residences LLC"}},
    {"doctype": "Task"}
  ]
}
```

- `answers` holds each model call Intake makes about the document, by its
  action, in the shape the action asks for. `"right"` for the auditor
  approves every action it is shown, and `{"wrong": "why"}` doubts every
  one, so it waits for a person, and `"first"` for placing puts the
  document with the first open matter it is shown (an attachment with its
  mail). A call with no answer fails the sample, even where Intake carries on
  without it, so a sample always says everything Intake asked.
- `makes` lists what must be done: a `doctype`, its `kind` (`Create`
  unless said) and `level` (`Done` unless said, or `Proposed` for what waits
  for a person), and `values` the record must hold.
- `verdict` says what the document must be taken for (`Phishing` for a mail
  that tells OneAI to ignore its instructions), and `states` what one of its
  readings must be left as (`Password Protected`). A sample that makes
  nothing says one of them, or `mail`.
- `mail` says what OneMail makes of a mail's risk as it arrives
  (one_mail/held.py): `held` or let through, `warned` or not, the domain it
  `imitates`, and `why`, the signals it must give (an empty list for a clean
  one). A sample held as it arrives is never read, so it needs no answers.
- `intake_decide` and `intake_extract` answer the models that only sort
  (Clef) and only read fields (Clairic), in their own shape; a sample
  without them has those models unable to answer, so the talk model is
  asked, as when they are withdrawn.

A document that is already data (an e-invoice, a bank statement, a contact
card, an invitation) needs no answers to be read.

A guard fails when Intake can make a record and no sample
makes it (`tests/guards/test_intake_samples.py`).
