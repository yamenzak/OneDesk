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
- A picture cannot be bound to a record's image field, and a slide does not
  repeat once per row of a list; a table of a list's rows does that job.
  Freeze Data has no "as of" mark, and an export is live, not frozen.
- OneAI's deck recipes are One's five decks; a company's own templates are
  not offered as recipes yet. A deck OneAI writes is not linked to a layout,
  so Restyle from Layouts leaves it alone.
- Present Live follows the slideshow in the editor's own window; with the
  Presenter View, guests on the link are not told where it is.
- A guest on a link sees the slides only; the speaker notes, the layout of a
  screen and anything hidden stay out.
- On a phone the editor shows the slide, the bar and the head; the slides
  rail, the panel and **Theme** are left out. It is for looking and small
  changes, not for building a presentation.

## Planned, from the walkthrough (30 October)


## Planned: the phone as a remote (30 October)

- **The phone as a remote.** Not today. Plan: the presenter view shows a QR
  code; it carries a short-lived pairing token for this one session, the
  way a OneDisplay screen pairs. The phone opens a small page (no desk, no
  sign-in needed beyond the token, which dies when presenting ends): big
  next and back, the notes, the clock, the thumbnails to jump. Phone and
  presenter meet in a socketio room for the session, over the site's own
  realtime, the same room ShareCenter's Present Live uses, so viewers on a
  link follow a phone-driven talk too.
- **The laser pointer.** Possible, with one honest limit: a phone knows how
  it turns, not where the screen is. So it works like a presentation clicker
  with a gyroscope, not like a real laser. Hold the pointer button, the
  phone takes where it points now as the middle of the slide, and from then
  on turning it left, right, up and down moves a red dot by how far it
  turned (`DeviceOrientationEvent`, sent about 30 times a second, smoothed
  on the slide's side). Letting go hides the dot; pressing again
  re-centres, which is the calibration, and it takes a second. iPhones ask
  once for permission to use motion. If a phone has no gyroscope or says
  no, the same button becomes a touchpad: drag a finger to move the dot.
  Delay is the site's socketio round trip, tens of milliseconds on the same
  network, fine for pointing; it is not fine for drawing, so drawing on a
  slide stays on the laptop.

## Found, answering how a screen plays a presentation (30 October)

- **How it draws.** Not pictures, not GIFs, not a sandbox: `play.for_screen`
  sends each slide's stored elements, cleaned again, and the TV draws them
  as HTML and SVG with `public/js/one_slide/play.js` (ES5, for Chromium 53).
  Text stays text, shapes are SVG, pictures are `<img>`, videos are muted,
  looping `<video>` seeked to the shared clock. Only a Web Page row is a
  sandboxed iframe. Each slide is one node; the next is added, the old one
  removed a second later after the fade, and the next slide's pictures are
  fetched ahead.
- **Gap: videos are not let go.** A removed `<video>` is dropped from the
  page but never paused or emptied, and an old TV's decoder may hold it
  until it is collected. Plan: on removal, pause, remove `src`, `load()`.
- **Every slide, one length each.** All slides play in order, each for its
  own Advance, else the row's Seconds, else 10, never under 2. Nothing tells
  a still slide from a moving one: a video loops for the slide's time
  rather than setting it. Plan: Advance can say "when the video ends", the
  editor keeping a video's length on the element when it is added.
- **Gap: the slide's own transition is not played.** The TV uses the
  playlist's fade for every change; Suite's per-slide transition and its
  matched-element move are dropped. Plan: play the simple ones (fade, push)
  on the TV; the matched move stays the editor's.
- **OneDisplay inside OneSlide's docs.** The overview and AGENTS.md open with
  "the slides a screen in the showroom plays", Help has a page On a Screen,
  and AGENTS.md has two OneDisplay sections. Its `paper.py` paragraph says
  a screen plays the PDF's pictures, which is wrong (it draws `play.js`).
  Plan: the overview and AGENTS.md speak of presentations only; On a Screen
  and both sections move to OneDisplay's Help and AGENTS.md, OneSlide keeping
  one line that says another app can play a presentation; the wrong line
  goes.
- **OneDisplay inside OneSlide's code.** OneAI's slide design is OneDisplay's
  job (`display_design`): it answers OneDisplay's blocks on a 1920 by 1080
  screen and `convert.py` redraws them as Suite's elements, borrowing
  OneDisplay's QR code on the way. Plan: OneSlide gets its own job that
  writes Suite's elements at the presentation's size, which the deck job
  needs anyway; OneDisplay's designer calls OneSlide's, not the other way.
