# OneSheet — scratchpad

What is known to be missing or wrong. How it works and why is `AGENTS.md`.

- An Excel file's charts, pictures, colours and column widths aren't read
  in, so the editor shows the file plain; writing back keeps them in the
  file (patching.py). A row or column inserted in the editor moves the
  values but leaves the file's styles where they were.
- A picture column shows the picture's address, not the picture.
- Frozen rows are meant to head every printed page, as Excel's print titles
  do; the wkhtmltopdf on the dev bench prints them once, at the top.
- A print has no page numbers, and the letter head's foot comes after the
  last sheet rather than at the foot of every page.
- A link column searches every record of its type, not only the ones the
  form would offer for that field.
- On a phone the head shows the workbook's name alone and the bar scrolls:
  it is for reading and small changes, not for building a costing.
- For a right-to-left reader the grid still runs A to Z left to right, as
  Suite draws it, and a tab's menu opens to the right of the tab.
