# OneWorkbook — scratchpad

What is known to be missing or wrong. How it works and why is `AGENTS.md`.

- An Excel file's charts, pictures, colours and column widths aren't read
  in, and aren't written back: its values, formulas, number formats and
  merged cells are.
- A picture column shows the picture's address, not the picture.
- Frozen rows are meant to head every printed page, as Excel's print titles
  do; the wkhtmltopdf on the dev bench prints them once, at the top.
- A print has no page numbers, and the letter head's foot comes after the
  last sheet rather than at the foot of every page.
- A link column searches every record of its type, not only the ones the
  form would offer for that field.
