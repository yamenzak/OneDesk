# Invoices for the first agents' gate

Fifty real supplier invoices, each as it arrived by mail, for
`onedesk/one_ai/agents/evaluate.py`: OneMail's receptionist hands each to
OneBook's accountant, and the draft it makes is held to what the invoice
says. The gate is 50 drafts with at most 2 a person had to correct.

A sample is two files with the same name: the mail (`.eml`, with its
attachment) and a `.json`:

```json
{
  "file": "gulf-sealants-gs-11873.eml",
  "expect": {
    "supplier_name": "Gulf Sealants Trading LLC",
    "bill_no": "GS-11873",
    "bill_date": "2026-10-04",
    "due_date": "2026-11-03",
    "grand_total": 4032.0,
    "currency": "AED"
  }
}
```

`expect` holds only what the invoice says; leave out what it doesn't. Run
with the models (`live`), the samples need no `answers`. A supplier the demo
company does not know is made by Intake first, as it would be on real mail.
