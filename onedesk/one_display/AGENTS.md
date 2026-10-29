# OneDisplay

The one file for agents, OneAI and us: what OneDisplay is made of, its rules,
where each file is, and the decisions that cost something. What is not built
yet, in the order it will be, is `SCRATCHPAD.md`.

OneDisplay is digital signage that runs on any screen with a browser: a TV in
a lobby, a kiosk at a door, a stick behind a meeting room's display. A screen
shows a **channel**. Tonight a channel is a queue board; the plan below makes
it slides, widgets, music and voice as well.

OneDisplay is **not registered** in `one/ready.py` yet: it has no Help, tour,
legal, notifications or abilities, and the guards that read those do not read
it. It is registered when stage 2 below is done.

## What is built

### A screen pairs, then asks

- `www/tv.html` and `www/tv.py` — the page a TV opens, `/tv`. One HTML file
  with its CSS inline and one script, `public/js/one_display/tv.js`, which is
  ES5 on purpose: a TV from 2017 runs Chromium 53 (Tizen 4, webOS 4), which
  has no arrow functions, no `fetch` and no `let`. Nothing on the page is
  bundled, so nothing may need to be. `acorn --ecma5` parses it.
- `screens.py` — the screen's side.
  - `start` (guest): a new screen is given a six-digit code to show and a
    secret only it keeps. Only the secret's hash is stored.
  - `status` (guest, with the secret): has somebody paired me? The first time
    the answer is yes, the screen is given its token, once; the stored copy is
    then cleared and only its hash is kept.
  - `pair` (desk): somebody types the code, names the screen and picks its
    channel and mode. **Add Display Screen** on the list opens this dialog;
    a screen record only ever comes from a TV.
  - `state` (guest, with the token): everything the screen shows now — its
    mode, muted and dark flags, the last command, the alert, the brand and the
    channel's board. `last_seen` is written at most every thirty seconds.
  - `take` (guest, with the token, kiosk only): hands out a ticket.
  - `control` (desk): reload, mute, unmute, off, on. The screen notices a new
    `command_at` and acts.
  - `alert` (desk): one message on every screen, over everything, read out,
    until it is ended. Kept on the single `Display Settings`.
- The screen keeps `{screen, secret}` and then `{screen, token}` in
  localStorage, so a power cut does not unpair it. Removing the record, or a
  token that no longer matches, sends it back to the pairing code.

**Why polling and not the socket.** Every two seconds the screen asks for its
state. An old TV's browser drops a WebSocket on every network hiccup and some
never reconnect; a plain request each time recovers by itself. Two seconds is
also what a person standing at a board expects. The socket comes in stage 3,
for the commands only, with polling kept as the fallback.

### The queue

- `Queue` — a place with `services` (each with a prefix: A, B, C) and
  `counters` (each with who staffs it).
- `Queue Ticket` — one ticket: `A007`, Waiting, then Called to a counter, then
  Done or No Show. Numbers start again each day per prefix; the next number
  comes from a cache counter (`incrby`) so two kiosks never hand out the same
  one, started from the records if the cache was emptied.
- `queue.py` — `take`, `board` (the last eight called today, newest first,
  and how many wait per service), and the counter's actions: `call_next`
  closes what the counter was serving and calls the longest waiting ticket,
  `recall` calls the same one again (the board announces it again because its
  `calls` went up), `finish` closes it as Done or No Show.
- `page/counter` — the counter's screen in the desk: pick the queue and the
  counter (it remembers, and starts on the counter you staff), Call Next, Call
  Again, Done, No Show, and who waits.
- The board announces a call it has not seen: a two-note chime through Web
  Audio, then `speechSynthesis` saying "Ticket A 7, counter 2" in the
  channel's language (the words are translated on the server). The first
  answer after a reload only fills what has been heard, so a reload says
  nothing. Browsers keep sound off until somebody presses a key, so the board
  says "Press OK to turn on sound" until the remote's OK is pressed once.

### Who may do what

- **OneDisplay Manager** — pairs screens, builds channels and queues, sends
  alerts. Made by `patches/roles.py` before the doctypes sync.
- **OneDisplay User** — works a counter: reads queues, reads and writes
  tickets.
- A screen is nobody. It holds a token that lets it read its own channel and,
  as a kiosk, take tickets; it can do nothing else.

## The plan, and the decisions behind it

The full concept is seventeen features. They fall into six stages; each one
works on its own.

1. **Queue slice** (built). Pairing, the board, the kiosk, the counter, remote
   commands, the emergency alert, the brand from the company.
2. **Register the module.** Help pages, tour, notifications (a ticket waiting
   longer than a threshold; a screen offline for ten minutes), abilities,
   legal (what a guest screen stores), setup steps, AI reach. Then
   `ready.MODULES`.
3. **Live and offline.** The socket for commands and alerts, polling kept as
   the fallback. A service worker that keeps the last channel and its media,
   so a screen with no network keeps playing what it had. One clock: the
   server's time in every answer, so screens on one channel agree to a tenth
   of a second, which is what playing the same slide and the same song at once
   needs.
4. **Slides, playlists and schedules.** `Slide` (image, video, or an HTML
   sandbox in an iframe), `Slide Playlist`, `Widget` and `Widget Collection`
   over the slides, `Music Playlist`, and one `Display Schedule` that says
   what plays when, including screensaver and mute hours.
5. **The editor.** A slide is designed on a canvas. The study of Frappe
   Builder (below) says how.
6. **OneAI and voice.** Gemini TTS voice packs per language for the queue, so
   the board speaks with a real voice rather than the TV's; voice ads with a
   tone and a schedule; images, video and music generated through the AI
   gateway; a layout or a custom widget written from a sentence.

### Frappe Builder, read for stage 5

Builder (MIT, so it may be taken into this AGPL repo with Frappe's notice
kept) renders a page on the server as plain HTML and one generated
stylesheet. Its editor is a Vue 3 app of about 49,000 lines whose canvas is a
scaled div, not an iframe, with breakpoints fixed at 1400, 800 and 420. A
block tree is saved as JSON on `Builder Page`.

- **What to take.** The block model and the canvas, as a Builder plugin that
  edits a slide through `canvasStore.editOnCanvas(block, type, saveAction)`
  with our own save, and a fixed 1920 × 1080 artboard passed through
  `canvasStyles`. `User Font` for fonts that work offline, `Builder Component`
  as the model for premade widgets, repeaters and `dataKey` for boards bound
  to data, `Builder Snapshot` for versions, and the screenshot thumbnails.
- **What not to ship to a TV.** Builder's own page. Its templates use flex
  `gap`, which Chromium before 84 ignores without a word, and `:has()`; its
  fonts come from Google; and an iframe narrower than 1024 CSS pixels gets
  the tablet layout. So OneDisplay publishes a slide itself: Builder's
  `get_block_html` into a lean template with no tracking, local fonts, `gap`
  rewritten to margins, saved as a file the screen can keep offline, and
  drawn at 1920 × 1080 and scaled as a whole.
- **Depending, not copying.** Installing Builder costs pandas, duckdb and
  litellm, and site-wide website hooks. Copying costs a 49,000-line fork.
  Neither is decided; the plugin route is cheaper to try first.

### LightningJS, read and not chosen

Lightning (Apache-2.0) draws everything in WebGL. It is fast for tiles and
tickers on a weak CPU, and wrong as the base here: video on a TV is a native
overlay plane under the canvas anyway, HTML from the editor or a custom widget
cannot be drawn in WebGL at all, its SDF text does not shape Arabic, every
full-screen texture is 8 MB of the TV's memory, and WebGL is unreliable on
cheap sticks. The player stays plain DOM: absolute positioning, `transform`
and `opacity` for movement, one `<video>`, premade widgets as DOM and only
custom code in a sandboxed iframe. Lightning is worth a trial for one thing,
a dense board of many changing tiles, and only if DOM proves too slow there.

## Files

| File | What it is |
| --- | --- |
| `screens.py` | Pairing, a screen's state, kiosk tickets, commands, the alert |
| `queue.py` | Tickets, the board, the counter's actions |
| `demo.py` | The demo company's showroom queue and lobby channel |
| `page/counter/` | The counter's desk page |
| `doctype/display_screen/` | The screen record, its list (pair, alert) and form (commands) |
| `patches/roles.py` | OneDisplay Manager and OneDisplay User |
| `../www/tv.html`, `../www/tv.py` | The player |
| `../public/js/one_display/tv.js` | The player's script, ES5 |
