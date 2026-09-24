# Intake

Written by hand. Stage 1 of eleven is built: every file and message is read
into text, and documents are found by what is written in them. The plan for
the rest is `docs/INTAKE.md`. The part above **Under the hood** is the
manual; below it are the decisions and what is still to come.

Intake is OneAI handling what arrives. A supplier's invoice, an employee's
passport, a customer's order, a scan of the day's post or a letter from the
tax office goes to a mailbox, a scanner or a folder, and One reads it, files
it where it belongs and does what it asks.

## What is read

Every document in OneCloud and every message in OneMail is read for its words:
PDFs, Word and PowerPoint files, spreadsheets and CSV files, e-invoices
(XRechnung, ZUGFeRD and Factur-X), bank statements (CAMT and MT940), contact
cards and calendar invitations, messages saved as files, and zip files. That
costs nothing and needs no switch.

## Finding a document by what it says

Search finds a document by what is written in it, not only by its name:

- **Ctrl+K** shows documents and messages whose words match, under
  **In documents** and **In mail**, with the line they were found by;
- **OneCloud's** search box finds files by their contents as well as their
  names, and shows the matching words beside each;
- **OneMail's** search finds a message by what its attachments say.

You only ever find what you may open yourself.

## Letting OneAI read a folder or a mailbox

Right-click a folder in OneCloud and choose **Read with OneAI…**, or open a
mailbox's **⋯** menu in OneMail and choose the same. New files and mail there
are then read by OneAI too, which means scans and photos of documents are
read as well, and recordings are written down. A scan of the day's post is
cut into its letters. This is read with OneAI credits.

OneAI does there only what you may do yourself, because you switched it on.
Your My Files and your own mailbox can only be switched on by you. A folder
OneAI reads shows the OneAI mark, and so does every folder inside it.

**Stop reading with OneAI** in the same menu turns it off. Nothing already
read is forgotten.

## Under the hood

- `read.py` turns any file into text without a site or a model, and says
  what it could not do itself: a scan needs eyes, a recording needs ears, a
  locked PDF needs a password. The readers are in `readers/`, one per kind.
- `split.py` cuts a batch scan into its documents at blank pages, separator
  sheets and page numbering that starts again. A vision model marks the rest
  when it reads the pages (`vision.py`, the `read_pages` action).
- `pipeline.py` makes one **Reading** per content, keyed by the same hash
  OneCloud stores content under. The same PDF attached to ten records is one
  reading. A part (the letters of a batch scan, the files of a zip) is a
  Reading of its own with `part_of`.
- A reading that needs a model waits for credits rather than failing
  (`Waiting for Credits`). One that failed for a passing reason is tried
  again every quarter hour, five times. The same job catches up files and
  mail that were there before Intake was, forty at a time, as history.
- `search.py` keeps a FULLTEXT index on the Reading's title and text, and
  answers the awesome bar through Frappe's `awesomebar_search` hook. Every hit
  is checked against the File's or the Communication's own permission.
  Document text stays out of Frappe's global search, which checks only
  doctypes and would show one person's payslip to anybody who may read files.
- Mail signatures' pictures are not read: a picture under 20 KB, or one drawn
  inline in the message.

What is not built yet is everything after reading: understanding what a
document is and who it is about, filing it, and acting on it. `docs/INTAKE.md`
§17 lists the stages.
