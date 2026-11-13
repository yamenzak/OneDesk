# OneDoc — scratchpad

What is known to be missing or wrong. How it works and why is `AGENTS.md`.

- A Word file's comments and tracked changes do not come into OneDoc, and
  older `.doc`, `.odt` and `.rtf` files do not open in it; they open as files.
- A card OneAI writes is put into the stored HTML; somebody else with the
  document open at that moment saves over it with what their copy holds.
- A card in place of a selection across paragraphs is put in only by the
  approver's open copy; with the document closed, nothing is written.
- Page setup's header, footer and lines on paper need the patched-Qt build
  of wkhtmltopdf, as frappe's repeated headers do.
- On a phone the head shows the document's name alone, and the outline and
  the comments are left out: it is for reading and small changes.
- In a right-to-left language a list's bullets in a right-to-left document
  sit where frappe-ui's prose puts them, which is drawn for left to right.
