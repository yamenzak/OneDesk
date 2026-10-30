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
- **A designed slide's picture blocks are not cropped** by the designer; a
  picture fills or fits its block, as the slide says.

## Planned, from the walkthrough (31 October)

- **Pictures at the screen's size.** A slide's pictures reach a screen as
  their original files, so a 6000-pixel photo from a phone is decoded at full
  size by a TV with 1 GB. Serve each picture through `api.shown` no wider
  than the frame it is drawn on (1920 across for a landscape screen),
  resized once and kept, the original untouched. This is the one thing
  LightningJS does better (it manages picture memory itself); the rest of
  why it is not used is in AGENTS.md.
- **A screen of any size.** A layout is Landscape (1920 × 1080) or Portrait
  (1080 × 1920) and nothing else, so a square screen, a stretched bar over a
  counter (1920 × 540) or a video wall (3840 × 1080) cannot be laid out.
  The pieces are there: OneSlide's editor takes any size (docs/ONESLIDE.md,
  S2), widgets sit in percent and size in `em`, and the player scales one
  frame. Plan: Orientation becomes a width and height with presets and
  Custom on the Widget Collection and the channel; `screen.py` gives the
  editor that frame; `tv.js` draws it instead of its two; a slide of
  another shape is letterboxed, or filled when the playlist row says so.
- **Rulers and guides in the screen's editor.** The layout is edited in
  OneSlide's editor, but its Guides menu is left out when the presentation
  is a screen's backdrop (`EditorNavbar.vue`, the `screen` check). Nothing
  stops them working there; offer them.
- **An object comes and goes.** Neither a slide nor a layout can bring one
  object in or take it out with an animation (fly in, fade, wipe; on a
  click on a slide, after a delay on a screen); only whole slides change
  with a transition. Plan it once in OneSlide, saved on the element, drawn
  by `play.js` with `transform` and `opacity` only, so a TV keeps up.
- **A widget styled like everything else.** A widget's look is its kind's
  few settings (size, colour, heading), so a queue board always looks the
  same. Give every widget the editor's own properties (font, size, colours,
  background, corners, padding), saved on the element and applied by the
  widget's renderer in `tv.js`, which keeps its layout and takes the rest.
- **Widgets in three kinds, no widget builder.** The editor is the builder;
  a second, smaller one would only copy it. (1) Widgets with behaviour stay
  premade (Queue Board, Kiosk, Clock, Ticker, Weather) and get preset looks
  and the style properties above. (2) A widget that only shows data becomes
  ordinary editor objects: OneSlide's data chips (`one_slide/data.py`, S9)
  pointed at a Display Source, a text or a table designed like any slide.
  This takes the place of Number and List. It needs the Data menu offered
  in a screen's editor (now hidden by the `screen` check) with Display
  Sources as its sources, and the TV refilling the chips on the source's
  refresh. (3) Custom code stays, in its sandbox, for what nothing else does.
- **Pictures and videos dropped on a playlist.** Media reaches a screen only
  inside a presentation, which is right: one store, one renderer, one
  history, one way to share. But nobody should open an editor to show a
  photo. Dropping files on a Slide Playlist makes one presentation per file,
  the picture or video filling the slide, filed on the playlist, as
  `patches/presentations_on_screens.py` already did for the old rows; it
  opens in OneSlide later if words are wanted on it.
- **Sound in step.** Slides agree to a fraction of a second; sound is
  looser. `tv.js` takes the server's clock from each answer alone
  (`skew = now - (sent + received) / 2`, the last one wins), and moves a
  track only when it is more than 0.6 s off, so two screens in one room can
  sound an echo. Plan: keep the answers that came back quickest and take
  their offset (tens of milliseconds becomes about ten on a network);
  correct music and video by `playbackRate` a few percent either way rather
  than jumps; have the server say when a call's recording is ready and give
  every screen one moment to start it, so no screen falls back to its own
  voice while another speaks OneAI's; and a **Plays Sound** switch on each
  Display Screen, so one screen in a room carries the sound, as signage
  usually does.
- **What is seen and what is heard, apart: Sound Zones.** A channel now
  carries both its pictures and its sound (music, voice ads, calls), which
  does not fit a business with many screens and one set of speakers. Plan:
  - A **Display Channel** is only what is seen: slides, layout, widgets,
    its schedule. Its music, ads and calls move out.
  - A **Sound Zone** is what is heard where one set of speakers is
    ("Showroom", "Workshop"): the music playlist and its schedule, voice
    ads, the queues that call into it, and alerts.
  - A zone is played by whatever feeds its amplifier: a `/radio` page on a
    stick, an old phone or a PC on the PA's input, paired with a code as a
    TV is, on the same clock. Where there is no PA, a screen plays its zone
    itself (a switch on the Display Screen).
  - A **Queue** names the zone its calls are spoken in, so a call comes
    from the ceiling once, not from five TVs. The queue board stays a
    widget on any channel; the kiosk stays its own channel.
  - An **emergency alert** shows on every screen and is spoken in every
    zone.
  - **Content sound stays with its picture.** A video's own soundtrack
    plays from the screen showing it, when the video's **Plays Sound** is on
    (a switch on the element in OneSlide; every video on a screen is muted
    today) and the screen's **Plays Sound** is on (one TV of a row of five
    carries it). The zone turns its music down while such a video plays and
    back up after, knowing when without being told, since a playlist's
    timing is fixed in advance. A TV playing its own zone does the same.
  - A browser plays no sound until OK is pressed once; the TV already asks.
  This also ends most of "Sound in step" above: one place per zone makes
  the sound, so there is no echo to correct.
- **Voice packs for calls.** Today a call is recorded as a whole sentence,
  once per language, voice and tone (`voices.spoken`), so the first call of
  every new ticket and counter is said in the TV's own voice while it is
  made, and a busy queue grows thousands of recordings. They sit in the
  workspace's storage on `Display Voice` records, seen nowhere. Plan:
  - A **pack** per language and tone, made once in the background through
    the same job (Gemini speech): every letter, the digits 0 to 9, the whole
    numbers 0 to 999, "thousand", "and" where the language joins numbers
    with one (Arabic و), the separators (dash, slash, point), "Ticket",
    "please go to", and the name of each counter and room.
  - A ticket is whatever the queue's format makes it (A1828, 2828,
    1828-3): the TV splits it into letters, numbers and separators and plays
    the pieces end to end with Web Audio, so every call is in OneAI's voice
    from the first ticket.
  - The queue says how a number is read: digit by digit (the default from
    four digits up, as counters say them) or whole, built up to 999,999
    from 0 to 999 and "thousand". Arabic numbers keep one form by following
    "رقم".
  - A whole sentence still recorded is played when it is kept, since pieces
    joined sound joined; anything a pack cannot say is recorded whole as
    today.
  - **Voice Packs** in OneDisplay: each pack's language, tone and voice,
    what it covers, its size, and Make Again after a change of voice or
    names.
  - Packs stay **out of OneCloud's folders**: a thousand small clips nobody
    opens would bury people's files. They are counted in the workspace's
    storage bar, so the space is never hidden. Music tracks and voice ads
    are the other way round: people choose, replace and reuse them, so they
    are files in OneCloud like any other.

