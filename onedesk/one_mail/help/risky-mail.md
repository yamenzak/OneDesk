# Risky Mail

{one_mail} checks every message that arrives for the signs of fraud. A risky
one shows a warning above it, and one that looks dangerous waits in **Held**
until you decide.

## What Is Checked

Each message gets a score from 0 to 100. Each sign adds to it once.

| Sign | Adds |
| --- | --- |
| The sender's domain says it didn't send the message (DMARC failed) | 50 |
| It came from a server the sender's domain doesn't send from (SPF failed) | 20, or 10 when the domain isn't sure |
| Its signature doesn't match the sender's domain (DKIM failed) | 15 |
| Replies would go to another address | 15 |
| The sender's name shows a different address | 25 |
| A link shows one website's name but opens another | 30 |
| A link opens a numbered address instead of a website's name | 20 |
| A link hides where it goes behind a link shortener | 10 |
| An attachment is a program, or hides a program behind a second extension | 60 |
| An attachment is a zip holding a program or a file with macros | 60 |
| An attachment can run macros, such as an `.xlsm` workbook | 50 |
| The sender's domain looks like one you know but isn't | 40 |
| The sender's domain is written with letters from another alphabet | 15 |
| {one_ai} read it as phishing | 50 |
| {one_ai} read it as spam | 20 |

The domains you know are your company's own, your mailboxes', and those of
your customers, suppliers and employees and their contacts. A domain looks
like one of them when only a letter or two differs, a hyphen is added,
letters that look alike are swapped, such as `rn` for `m` or `0` for `o`, or
only the ending differs. The warning says which domain it imitates.

{one_ai}'s signs are added only in a mailbox {one_ai} reads. Everything
else works without it.

## Warned and Held

These are the levels a workspace starts with; a Mail Manager can change them
(below).

| Score | What happens |
| --- | --- |
| 25 or more | A yellow warning above the message lists why |
| 50 or more | A new message waits in **Held**, under the mailbox's Inbox, with a red warning |

A held message isn't in your Inbox. No rule, out-of-office reply or agent
sees it, and it isn't linked to any record.

## Releasing or Deleting

Open **Held**, then open the message and read why it was held.

1. **Release** puts it where it arrived. Then its rules, an out-of-office
   reply, its links to records and {one_ai}'s reading run, as if it had just
   arrived. A message held only after {one_ai} read it had all of that
   already, so nothing runs again.
2. **Delete** moves it to Trash. Nothing runs on it.

Both are also in the command row, for the conversations you tick. Anyone
who uses the mailbox can release or delete its held mail.

> **Release only what you trust.** If a supplier writes from a new address
> about new bank details, call them on a number you already have.

## Previewing a Link

**Preview Link** opens a link in a throwaway browser away from your
workspace, without your sign-in or cookies, and shows you the page before you
go there. It is in a warning, and in any message's **⋯** menu.

| It shows | Why it matters |
| --- | --- |
| A picture of the page | You see it without visiting it |
| Where it ended, after any redirects | A warning says when that isn't where the link points |
| Whether it asks for a password | A red warning says so |

Then **Open Link** opens it yourself. In a warned message every link opens
Preview Link first. In a held message links can't be opened any other way,
and Reply and Forward come back once you release it. Each preview uses
credits.

## Opening an Attachment

Clicking an attachment checks it before it opens. It is read for what it
really is, whatever its name says, and an archive is unpacked to see what it
holds.

| The attachment | What you can open |
| --- | --- |
| A Word, Excel or PowerPoint file | **Open Clean Copy**, a PDF without macros, first; then the original |
| A program, or an archive holding one | Nothing: it can't be opened here |
| An archive too deep, too big or with a password | The original, with a warning that it wasn't checked |
| Anything else | **Open** |

> **The original is never changed.** If the check can't run, it says so and
> still offers the original.

## Changing the Levels

A Mail Manager sets both levels in [Settings](settings), under **Risky
Mail**: **Warn From** and **Hold From**, each from 1 to 100. Mail that
already arrived keeps its score.

On a mailbox connected from another provider, a held message stays where it
is on that provider's server, so a phone reading the mailbox still shows it.
