# OneDisplay — scratchpad

What is known to be missing or wrong. How it works and why is `AGENTS.md`.

## Before it is shown to a customer

- Try `/tv` on a real Tizen or webOS set. It was checked in desktop Chromium
  and its script parses as ES5; nothing has run on a TV yet, and the socket
  has not been tried on one either.
- Speech was tried for real once, in English, through the gateway on
  2026-10-30: a 5.8-second WAV, billed as audio output. Arabic and German
  have not been listened to.
- Video (Veo) and music (Lyria) have only been tried with OneAI's answer
  stubbed. Lyria's answer type is assumed to be MP3 or WAV; Veo's operation
  and download are read as Google documents them, through the gateway.
- A kiosk shows the ticket and prints nothing. A receipt printer needs a
  kiosk app, since a browser cannot print silently.

## Not built

- **Veo is not priced.** Google's page did not list it when it was read, so
  a video is charged its hold (`one_ai/models.py`, `UNPRICED`).

## The plan, from the walkthrough (31 October)

Eight stages, in this order because each stands on the one before. Every
stage ends as OneSlide's did: docs (AGENTS.md, Help with pictures), ar and
de, a demo check, a version, a commit, a looks commit, a push, and its
lines here removed.

### D1. Screens that report, and brakes

- **A screen says what it is.** It never reports its size. At pairing and
  in every `state` call it sends its pixels (`innerWidth`, `innerHeight`,
  `devicePixelRatio`), its browser, and its memory where the browser tells
  it (`navigator.deviceMemory`, `performance.memory`), kept on the Display
  Screen. Drawing stays on the channel's frame scaled to the screen: text
  and shapes are sharp at 4K; a picture is as sharp as its file.
- **What a channel weighs, and screens at risk.** For each channel: its
  media's size, the memory its pictures take decoded (width × height × 4),
  its videos, its widgets. Set against what each screen reports, the
  Display Screen shows **At risk** before anything fails.
- **Brakes before a crash.** A browser gives no warning before it runs out
  of memory, so: where `performance.memory` exists, reload calmly between
  slides past about 80% of the limit; reload every night at a quiet hour
  (a channel setting, default 04:00); count restarts and why, and show them
  on the Display Screen ("restarted 3 times today"). A frozen page cannot
  save itself; that is the native wrapper's job (see the end).
- **The demo lobby's words run under its queue board.** The slide is drawn
  across the whole frame and the board sits on its right third. The demo's
  slide keeps its words clear of the board.

### D2. Any size, and pictures as sharp as the screen

- **A screen of any size.** A layout is Landscape (1920 × 1080) or Portrait
  (1080 × 1920) and nothing else, so a square screen, a stretched bar over a
  counter (1920 × 540) or a video wall (3840 × 1080) cannot be laid out.
  OneSlide's editor takes any size (S2), widgets sit in percent and size in
  `em`, and the player scales one frame. Orientation becomes a width and
  height with presets and Custom on the Widget Collection and the channel;
  `screen.py` gives the editor that frame; `tv.js` draws it instead of its
  two; a slide of another shape is letterboxed, or filled when the playlist
  row says so.
- **Pictures as sharp as the screen, no sharper.** No compression for its
  own sake: a picture is resized only when it is larger than the largest
  screen it is shown on (from D1: 3840 across for a 4K screen), at high
  quality, never made larger, the original kept, served through
  `api.shown`. This is the one thing LightningJS does better (it manages
  picture memory itself); why it is not used is in AGENTS.md. Videos are
  not re-encoded; one beyond what a screen says it decodes is flagged on
  the playlist.

### D3. The editor and data, the same for screens as for slides

- **Rulers and guides in the screen's editor**, now left out by the
  `screen` check in `EditorNavbar.vue`.
- **Data chips on screens.** OneSlide's data from records (`data.py`, S9)
  offered in a screen's editor with Display Sources as its sources, and
  the TV refilling the chips when its source is read again.
- **Data that changes reaches screens at once.** A source is read again on
  its own clock (`sources.KEPT`: a minute for Records and Record, five for
  a Report, longer for feeds and weather). A saved record a source reads
  wakes the screens showing it, as a call does, its cache dropped first.
- **Pictures and videos dropped on a playlist.** Media reaches a screen
  only inside a presentation (one store, one renderer, one history, one way
  to share), but nobody should open an editor to show a photo. Dropping
  files on a Slide Playlist makes one presentation per file, the picture or
  video filling the slide, filed on the playlist, as
  `patches/presentations_on_screens.py` did for the old rows.

### D4. Widgets: bare, styled by the editor, with looks

- **Three kinds, no widget builder.** The editor is the builder. (1)
  Widgets with behaviour stay premade: Queue Board, Kiosk, Clock, Ticker,
  Weather. (2) A widget that only shows data becomes editor objects with
  data chips (D3): this takes the place of Number and List, and a patch
  turns existing ones into a text or a table. (3) Custom code stays in its
  sandbox.
- **The bare widget, as a rule.** A widget draws its content and behaviour
  and nothing else: a ticker is text moving, with its spacing, separator,
  speed, direction and data; it has no background. Background, border,
  corners, padding, font and colours are the element's, set in the editor
  like any object's, and the renderer in `tv.js` takes them. A **look** is a
  saved set of those, offered per widget; variations are looks, not new
  widgets. Every widget scales from its own box (`em`), so one look works
  at any size. The rule goes in AGENTS.md, with a test that no renderer
  sets a background, border or font of its own.

### D5. Boards: things that change state, shown live

Queues move people through counters; businesses also need *things* moving
through states by hand, on screens: operating rooms, beds, bays, meeting
rooms, a score, today's special, a wait time. Build none of these; build
one generic **Board** each is set up as. No doctype, field or word in it
names a hospital, a sport or a restaurant; the examples live in Help and
the demo.

- A Board has **items** and the business's own **states** (each with a
  colour and an optional time limit) and/or **values** (a number, a word).
- A **control page** for a phone or tablet, like Counter: tap the item,
  tap the state, or +1 / −1 / type a value; a QR code on a door opens one
  item's buttons. Who may is set per board.
- Widgets: a **grid** of items (colour, state, time in it, "Cleaning ·
  12 min") and **one item** big; any value through data chips. Changes
  reach screens at once over their socket.
- A state past its limit tells someone (like Long Wait); every change is
  kept, so turnaround times can be read back.
- The screen above a counter is the same **one item** widget pointed at a
  counter: what it serves, large, flashing on a call, "Closed" when idle.

### D6. Sound: zones, content sound, and in step

- **Sound Zones.** A **Display Channel** becomes only what is seen. A
  **Sound Zone** is what is heard where one set of speakers is: its music
  and schedule, voice ads, the queues that call into it, alerts. A zone is
  played by a `/radio` page on whatever feeds the amplifier (a stick, an
  old phone, a PC), paired with a code on the same clock; with no PA, a
  screen plays its zone itself. A Queue names its zone; an emergency alert
  shows on every screen and is spoken in every zone. A patch moves each
  channel's music, ads and calls into a zone of its own.
- **Content sound stays with its picture.** A video's soundtrack plays from
  the screen showing it when the video's **Plays Sound** is on (a switch on
  the element in OneSlide; every video is muted today) and the screen's
  **Plays Sound** is on. The zone ducks its music while such a video plays,
  knowing when from the playlist's fixed timing.
- **In step.** Keep the quickest answers' clock offset rather than the
  last (`skew` in `tv.js`); correct music and video by `playbackRate` a few
  percent rather than jumps past 0.6 s; give every screen one moment to
  start a call once its recording is ready. A browser plays no sound until
  OK is pressed once; the TV already asks.

### D7. Voice packs for calls

Today a call is recorded as a whole sentence once per language, voice and
tone (`voices.spoken`), so the first call of each new ticket and counter is
said in the TV's own voice, and a busy queue grows thousands of recordings,
seen nowhere.

- A **pack** per language, voice and tone, made once in the background
  (Gemini speech): every letter, digits 0 to 9, numbers 0 to 999,
  "thousand", "and" where a language joins numbers with one (Arabic و),
  separators (dash, slash, point), "Ticket", "please go to", and each
  counter's and room's name.
- A ticket is whatever its format makes it (A1828, 2828, 1828-3): the
  player splits it into letters, numbers and separators and plays the
  pieces end to end with Web Audio. The queue says how numbers are read:
  digit by digit (default from four digits) or whole, up to 999,999. Arabic
  numbers keep one form after "رقم". A whole sentence already recorded is
  played instead; anything a pack cannot say is recorded whole, as today.
- In **OneCloud**: OneDisplay › Voice Packs › one folder per pack ("Arabic ·
  Kore · Announcement"), in R2 and counted in the storage bar. Make Again
  replaces the clips in place; deleting the folder deletes the pack. A
  **Voice Packs** screen shows what each covers and links to its folder.
  Music tracks and voice ads become files in OneCloud too.

### D8. An object comes and goes

Neither a slide nor a layout can bring one object in or take it out (fly
in, fade, wipe; on a click on a slide, after a delay or on a loop on a
screen); only whole slides change. Built once in OneSlide, saved on the
element, drawn by `play.js` with `transform` and `opacity` only so a TV
keeps up; OneSlide's own changelog and Help carry it as well.

### Beside the plan

- **A native wrapper** (Tizen, webOS, Android TV) around the same `/tv`:
  starts the player when the TV powers on, restarts a frozen page, and
  prints a kiosk's ticket silently. A separate project; no code here
  changes for it.
