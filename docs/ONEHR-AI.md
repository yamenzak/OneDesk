# OneAI in OneHR

Everything OneAI does in OneHR, where it is offered, and what runs on its
own. Hiring has its own document, `docs/HIRING.md`; this is the rest, and the
one list of all of it.

Two rules hold for every row. **Everything is offered in the OneAI panel** for
the page it opens on — no OneAI button goes on a page, and a guard fails if
one does. **Anything that writes is a card** somebody approves, except the few
background jobs below, which only ever write OneAI's own fields and comments.

## Asked for, in the panel

| Where | Offered as | What it does | Module |
|---|---|---|---|
| Expense claims | Claim a receipt · What can I claim? | A claim card from a receipt; the expense types and approval rule | `ai.py`, `ai_policy.py` |
| Leave | Book time off · How much leave do I have? · What is our leave policy? | A leave card; balances and who is off; leave types, holidays and notes, each cited | `ai.py`, `ai_policy.py` |
| Letters, OneHR home | Ask HR for a letter | A salary certificate, experience or employment letter drafted from the asker's own record, filed for HR to issue | `ai_letters.py` |
| An employee (HR) | Write a letter for this person | The same, about somebody else | `ai_letters.py` |
| A payroll entry | Check this payroll | Every slip against the same person's last, and anybody missing; the arithmetic is code | `ai_payroll.py` |
| A salary slip | What changed since last month? | The same for one slip | `ai_payroll.py` |
| Goals | Draft my goals for this cycle | Up to five Goal cards in the open cycle, against the workspace's KRAs | `ai_growth.py` |
| An appraisal | Draft my feedback · What training would help? | A feedback card; the weakest KRAs matched to the workspace's own programs and events | `ai.py`, `ai_growth.py` |
| Exits | Why are people leaving? | Reasons counted over twelve months | `ai.py` |
| Any settings page | Help me set this up | Every setting that matters, and one card with the changes | `one_ai/suggest.py` |
| Hiring | see `docs/HIRING.md` | | `hiring.py` |

## On its own, in the background

| When | What | Switch in HR Settings |
|---|---|---|
| A new applicant | Rated and placed among the others | Auto Screen New Applicants |
| A new interview | Questions and things to confirm | Auto Prepare Interviews |
| A recording ends | Transcribed, and remarked on | Auto Transcribe Recordings |
| A new grievance | Summarised, categorised, and if sensitive hidden from all but HR Managers and its raiser | Auto Triage Grievances |

Each is one call per event, runs as the disabled OneAI user so the timeline
says who wrote what, and keeps an unreadable answer in the error log with its
text.

## What the reader may see

Tools read as the person asking, with `get_list`, so the salary rules and an
employee's own-records limits apply as they do on a list. Three things are
read whatever the reader's role because they are the workspace's own names
and not anybody's record: the KRA list, the open appraisal cycle's dates, and
the training catalogue.

An employee's letter, goals and policy answers are always about themselves;
the employee is read from who is asking, never taken as an argument. HR may
name anybody, and a manager may name a direct report for goals and training.
