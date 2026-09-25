# One

Written by hand. What One itself does and how to use it, screen by screen: the
sidebar that every workspace has, and Settings. Everything above **Under the
hood** is written for the people using One, and OneAI reads it to answer "how
do I…" questions. Under the hood is for the people who build it.

## Finding your way

One's sidebar has three groups:

- **You**: your own settings. Everybody has these.
- **Workspace**: the workspace's settings. Only its administrators see this
  group.
- **OneAI**: credits, your conversations with OneAI, and what it has suggested.

**OneAI is the round button in the corner.** Open it on any page and it offers
what makes sense there. You can also ask it how anything in One works.

## Settings

Each entry under **You** and **Workspace** opens one section of Settings in the
middle of the page.

**Saving works as it does on any record.**

- Save is at the top right, and Ctrl+S (Cmd+S on a Mac) does the same.
- Once you change something, the top of the page says **Not Saved**. Undo the
  change and it goes away.
- Moving to another section keeps what you changed until you come back.
- Closing the tab with unsaved changes asks you first.

**If somebody else changes the same thing while you have it open** — HR
updating your employee record, say — the page shows "This form has been
modified after you have loaded it". Press **Refresh** to see their change. Your
unsaved changes are dropped, so note them first. If you had changed nothing,
the page refreshes by itself. Saving over their change is refused.

### Profile

Your profile is how you appear to everybody in the workspace. If you work
here, it also holds the parts of your employee record you keep up to date
yourself.

**Your photo.** Click the photo, or **Add a Photo** under your name, and choose
an image from your computer, a link, your camera or OneCloud. **Remove Photo**
takes it off. Your name and photo are shown to everybody in the workspace.

**Your details**: first and last name, gender, birth date, mobile number,
location and a short bio.

**Language and Time**: the language One is shown to you in, and the time zone
your times are shown in.

**If you are an employee**, the page also shows:

- **At Work**: your employee ID, job title, department, manager, branch,
  employment type, date of joining and company email. HR keeps these, so you
  cannot change them here. Ask HR if something is wrong.
- **Where You Live**: your current and permanent address, and your personal
  email.
- **In an Emergency**: who HR should call if something happens to you at work,
  how they are related to you, and their phone number.
- **About You**: marital status and blood group. Only you and HR see these.
- **Where Your Pay Goes**: your bank, IBAN and account number, with all but the
  last four characters hidden. Only HR can change this, so ask them when your
  bank changes.

Your gender, birth date, mobile number and photo are on your employee record as
well. Changing them here changes both.

**OneAI on this page** offers:

- **What is missing from my profile?** It reads your profile and your employee
  record, and tells you what is empty or looks out of date, and what each is
  used for.
- **How do I fill this in?** It goes through the page with you: what each part
  is for, and what only HR can change.

### Agreements

Every agreement One runs under, and where you and your organisation stand on
each. Click a title, or **Read**, to open it in a new tab.

- **Yours**: the Acceptable Use Policy, the Privacy Policy and the Cookie
  Policy. They are about your own personal data, so only you can agree to them.
  Each says **Agreed** and when, or **Not agreed yet**.
- **Your Organisation's**: the Terms of Service, the Acceptable Use Policy, the
  Data Processing Addendum, the Subprocessors list and the AI Addendum. An
  administrator agrees to them once for everybody, and each says who agreed and
  when.
- **Published**: the open source notices, to read. Nobody is asked to agree to
  them.

**Updated since** means the document has changed since it was agreed to. **Read
what was agreed** opens the exact text that was agreed, as it was then. If
anything is waiting for you, **Agree Now** asks you, as One does when you sign
in. An administrator also has **Everybody's Agreements**: every acceptance in
the workspace, who agreed to which version, when and from where.

**OneAI on this page** reads the agreements themselves, not a summary, and
offers:

- **What have I agreed to?** What you and your organisation agreed to, in plain
  words, and what it means for your data.
- **Who else sees my data?** Which other companies receive data from the
  workspace, what they get, and where it is kept.

## Asking OneAI

Ask OneAI how anything in One works, in your own words and your own language.
It answers from this page and the other modules' own pages like it, and says
which section the answer comes from. If they do not cover something, it says
so rather than guessing.

On each section of Settings it also offers the few questions that make sense
there. They are listed under each section above.

## Under the hood

For the people who build One. OneAI does not read past this heading.

| File | What it does |
|---|---|
| `settings.py` | Every section's load and save; which sections a person may open |
| `page/settings`, `page/workspace_settings` | The two pages: yours, and the workspace's (administrators only) |
| `../public/js/settings.js` | Draws a section, and behaves like a desk form: dirty, stale saves, realtime |
| `sidebar/one/one.json` | One's sidebar, with a link per section |
| `ai.py` | What OneAI offers on these pages, and what it is told about where the reader is |

Profile writes a person's own User record, and their own Employee record when
they have one (`own.employee_of`), and only the fields named in `PROFILE` and
`EMPLOYEE_OWN`. Gender, birth date, mobile and photo go to the employee as well
(`SHARED`), because erpnext copies the employee's values onto the login every
time the employee is saved.
