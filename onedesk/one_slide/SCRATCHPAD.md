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

## Planned, from the walkthrough (30 October)

- **Export as PowerPoint (.pptx).** Today the only export is PDF, as
  pictures. Plan: python-pptx (MIT, not installed yet) on the server, turning
  each element into a real PowerPoint one, so the file can be edited:
  text with its font, size, colour and weight; shapes as PowerPoint's own
  (rectangle, oval, triangle, diamond, star, right arrow, line); pictures;
  tables; a colour or two-colour fade for backgrounds and fills; videos as
  embedded movies. What has no PowerPoint equivalent (blur, free CSS) is
  left out, and the dialog says which slides lost something. Kept beside the
  presentation in OneCloud, like the PDF.
- **Slide masters.** Not today. A theme or template gives each new slide a
  layout, but it is copied in: change the template afterwards and no slide
  follows. Plan, in two steps:
  1. A master: elements every slide draws underneath its own (a logo, a
     footer, the slide number, the date), edited in **Edit Master** on the
     same canvas, kept on the presentation (`master`), and drawn by the
     slideshow, the PDF, the .pptx export and the TV alike. A slide can hide
     it. Slide number and date are new text fields filled when drawn.
  2. Linked layouts: each slide remembers its layout, the layout's title
     and body boxes are placeholders, and changing a layout's look restyles
     every slide on it while keeping their words.
- **Templates shipped with One.** Today there are two themes, Light and
  Dark (Suite's), and the company's own templates (**Save as Template**,
  Managers only, kept in OneCloud › Presentation Templates). **New ›
  Presentation** offers them all, and a template's slides become the layouts
  **Add Slide** offers. Nothing designed ships with One. Plan: a handful of
  finished decks (a pitch, a project update, a tender, a monthly review, a
  training session), each laid out in the business's colour and logo when
  it is chosen, with their words in ar and de as well.
- **A slide library.** Today a slide can be copied from one presentation
  and pasted into another (its pictures come with it), and that is all.
  Plan: **Insert Slide** opens a library by kind (title, agenda, section,
  two columns, picture and text, quote, team, timeline, figures, pricing,
  thank you), from two shelves: the slides One ships, and the company's own,
  where a Manager puts a slide with **Save to Library** on its right-click
  menu. An inserted slide takes the deck's colours and fonts.
- **Data from records.** Not today: a presentation can be filed on a record
  but reads nothing from it. OneWriter already does this for one record
  (**Insert a Field**, a grey block that shows what the record says now),
  and OneDisplay's sources (`one_display/sources.py`) already read records,
  a filtered list or a report as the person who saved them. Plan: one data
  layer for all three. A presentation declares its sources by name:
  - a record, fixed, or "the record this is for";
  - records reached through a link from another source (the project, then
    its customer, then the customer's contacts);
  - a filtered list (the project's open tasks), a report, or one figure
    (a count or a sum).
  On the slide, a text holds field chips (`{project.project_name}`,
  `{client.customer_name}`), a table is bound to a list with chosen
  columns, a picture to an image field, a figure to a figure. A slide can
  repeat once per row (a slide per task). Values are formatted as a print
  formats them, in the reader's language. A slide may draw from several
  unrelated records at once; nothing ties a deck to one doctype.
- **Batch: one deck per record.** Not today. Plan: a template whose main
  source is "the record this is for", of one doctype. From that doctype's
  list, filtered or with rows ticked, **Make Presentations** runs in the
  background, makes one deck per record from the template, files each on its
  record (or in a chosen folder) with a name pattern, and says when it is
  done. Optional in the same run: a PDF or .pptx of each, attached or mailed.
- **Live or frozen.** Plan: live by default. Chips are filled each time the
  deck is opened, presented, exported or played, and an open editor redraws
  when a record it shows is saved (the realtime event the workbook already
  listens to). A chip is filled as the person looking at it, so someone who
  may not read the project sees it empty, never its value. **Freeze Data**
  keeps every value as it is now, marked "as of" with the date, takes a
  version, and can be undone; an export and anything sent outside the
  workspace is frozen by default.
- **OneAI writes a whole deck.** Today OneAI makes one slide from a
  sentence, reads no records, and the OneAI panel does not see the open
  presentation. Plan: a deck job. "Write a pitch for project X for client
  Y" reads what it needs with OneAI's existing tools (the project, the
  customer, their quotations, tasks, files and mail), shows an outline as a
  card (each slide's title, what it says, which data it binds), and once
  approved builds the deck from the slide library in the business's brand,
  putting live chips wherever a value comes from a record instead of typing
  the number. Kinds of deck are recipes (pitch, project update, monthly
  review, tender response), each an outline and the library slides it
  prefers; a company can add its own. Per slide: rewrite, shorten,
  translate, turn into a timeline. The panel gets the open presentation and
  its selection, as it has the open document and workbook.
- **Presenting by link.** Not today. OneCloud's share link already has
  everything the access side needs (a public link with an optional password
  and an expiry, or invited people who each get a mail and come in with a
  one-time code, an opened count, revoke at any time), but what a guest gets
  through it is a download: a OneWriter document as .docx, a workbook as
  .xlsx. A presentation has no branch in `links.get` at all; its file opens
  `one_slide.api.download`, which wants read permission and sends the guest
  to the desk editor. Plan: the presentation viewer on ShareCenter (below),
  at `/s/<token>` instead of a download: the deck full screen,
  arrows, a slide counter, the transitions, drawn by `play.js` the way the
  TV draws a screen. Same Share dialog, same audiences, password, expiry
  and mailed code; nothing new to learn. Data chips are frozen at the
  moment the guest opens it, filled as the person who shared it, so a
  stranger never reaches the records themselves. "Allow download" offers
  PDF (and .pptx once export exists). Optional **Present Live**: the
  presenter's current slide is pushed over the site's socketio, and
  everyone on the link follows it, with a "you are ahead" catch-up button.
  The link records who opened it and when, and per slide how long it was
  looked at, shown on the presentation as Views. The same viewer is what
  OneWriter needs too: a document read in the browser, not downloaded.

## Planned: ShareCenter, one way to share anything (30 October)

Not OneSlide's alone; it goes to its own document when this is committed.
Today there are three ways to share, each built for one module:

- **Inside the team:** frappe's `DocShare`, drawn by OneCloud's Share dialog
  (`one_storage/share.py`) for files and folders, and read by AccessCenter
  as "what one person was given on one record".
- **Files to outsiders:** OneCloud's `Cloud Link` (`one_storage/links.py`,
  `/s/<token>`): anyone with the link, optional password and expiry, or
  invited people with a mailed one-time code; download, upload, opened count.
- **Records to a customer or supplier:** OnePortal's `Portal Link`
  (`one_portal/share.py`, `/portal/l/<token>`): a quotation or a quote request
  sent to a party's contact, used up by the answer, not by being opened.

Forms will need a fourth (a token per recipient), and a code editor a fifth.
Plan: one ShareCenter, a service in `one` beside AccessCenter and AICenter,
that every module uses instead of writing its own.

- **One link doctype.** `Share Link` replaces Cloud Link and Portal Link:
  what (a file, a folder or any record), who (anyone with the link, invited
  people by mail, a party's contacts, or signed-in people only), the gates
  (password, last day, one-time mailed code, used up by an answer), and what
  the guest may do (view, comment, download and in which formats, upload,
  answer, edit). Token stored hashed, as both are now. Old rows move over and
  `/s/` and `/portal/l/` keep working.
- **One dialog.** The same Share dialog on every file, document, workbook,
  presentation, record and form: People (inside the team, `DocShare` as now),
  Link, and Invite. A module only says which of these it allows and what a
  guest may do.
- **One guest page, viewers per kind.** `/s/<token>` checks the gates once,
  then hands the guest to the viewer the module registered in a hook
  (`one_share_viewers`): the presentation player, a document reader, a
  read-only workbook, a folder listing, the portal's record page, a form, and
  later the code editor. Anything with live data is filled as the person who
  shared it and frozen for the guest.
- **One place to see it all.** Shared by Me for each person (every link and
  invite, opened when and by whom, revoke, extend), and for a workspace
  administrator every outside link in the workspace, with a switch per module
  (no public links, password always, longest life) and Revoke All for a person
  who leaves.
- **One log.** Every open, code asked, download and answer is a row the owner
  can read and AccessCenter can show; the Views count on a presentation is
  this log read back.
- **Order.** Build the doctype and guest page under OneCloud's links first,
  since its rules are the most complete; move OnePortal onto it; then add the
  viewers (presentation, document, workbook); forms and the code editor
  arrive already using it.

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

## Found, answering fonts (30 October)

- **What a slide offers today.** Seventeen names in `FontSection.vue`:
  Inter, plus Anton and Courier Prime as webfonts we ship
  (`/assets/onedesk/slide/fonts.css`, Latin only), and fourteen system fonts
  (Arial, Tahoma, Georgia, Times New Roman and the rest) that look like
  whatever the viewer's computer has under that name. Nothing for Arabic:
  Arabic text falls back to whatever system font has the letters, so it
  looks different on a Mac, on Windows and on the TV. No direction setting
  either: a text box is not marked right-to-left.
- **What frappe offers.** Print Settings has a Select of six (Default,
  Helvetica Neue, Arial, Helvetica, Inter, Verdana, Monospace). A print
  format made in the builder has a Google Font field picked from
  `frappe/data/google_fonts.json`, 53 families, none Arabic, loaded from
  fonts.googleapis.com when printed; Website Theme does the same. A call to
  Google on every view is the kind of service TrustCenter keeps off by
  default.
- **The TV.** `play.js` sets Inter and loads no font file, so a slide's Anton
  or brand font falls back on a screen.
- **Plan: one font library for the workspace**, used by OneSlide, OneWriter,
  OneWorkbook, print formats and OneDisplay alike.
  - One ships a chosen set as files on our own server, Arabic among them,
    all under the OFL: IBM Plex Sans Arabic, Noto Naskh Arabic, Noto Kufi
    Arabic, Cairo, Tajawal, Almarai, Amiri, beside the Latin ones.
  - A workspace adds its own brand font (.woff2, .ttf, .otf), kept as a
    File, offered in every font picker.
  - **Add from Google Fonts**: search Google's catalogue, and the chosen
    family is downloaded once into the workspace and served from it. Google
    is reached only when someone adds a font, never when anyone reads, so
    it is a TrustCenter optional service with one clause, off until turned
    on.
  - One `fonts.css` for the workspace, which every editor, the PDF, the
    portal and the TV load; the TV's service worker caches the files.
  - The font picker groups them (Arabic, Sans, Serif, Display, Mono, Your
    Fonts) and shows each name in its own face, Arabic ones in Arabic.
  - A text box gets a direction (automatic by its first letter, or set),
    and a new presentation in an Arabic workspace starts right-aligned in
    an Arabic font. Print formats and OneWriter take their default from the
    same place.
  - **Where the files live.** No exception to R2. A font added from Google
    or uploaded is a workspace File like any other, so its bytes go to R2
    through `store.write`. The set One ships is code, not data: app assets
    beside Inter and Anton today, in every install the same. One wrinkle:
    `store.fetch` answers with a redirect to a signed R2 address that
    changes every ten minutes, and a browser loads a font from another
    address only if it answers with CORS headers. So `fonts.css` names each
    font at our own address, and for a font that address streams the bytes
    (tens of kilobytes) with `Cache-Control: immutable`, which is safe
    because the R2 key is the content's hash. Cloudflare in front then
    keeps it, and the TV's service worker too.
