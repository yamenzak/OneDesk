# OneSlide — scratchpad

What is known to be missing or wrong. How it works and why is `AGENTS.md`.

- Two people cannot work on one presentation at the same moment: a second
  tab is told it is open elsewhere and offered **Edit here**. Suite's slides
  have no co-editing; the workbook's and the document's relay could carry it.
- A PDF is pictures of the slides, so its words cannot be selected or found.
- `play.js` has not run on a real TV, only in desktop Chromium and parsed as
  ES5. Line heads other than the arrow are drawn as a filled triangle.
- A free CSS box keeps what was typed; only what `css.json` allows is drawn.
  The editor saves the typed text and the server keeps the allowed part, so
  a reload shows the cleaned text.
- Suite's own unit tests are vendored but not run: they need jsdom.
- The channel builder on this engine is stage 7 of docs/ONESLIDE.md.
- The Light and Dark layouts say "Title" and "Subtitle" in English whatever
  the reader's language: they are Suite's fixture text, kept as it ships.
- On a phone the editor shows the slide, the bar and the head; the slides
  rail, the panel and **Theme** are left out. It is for looking and small
  changes, not for building a presentation.
