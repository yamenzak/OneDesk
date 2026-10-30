# OneDisplay

The one file for agents, OneAI and us: what OneDisplay is made of, its rules,
where each file is, and the decisions that cost something. What is known to
be missing is `SCRATCHPAD.md`; what people read is `docs/`.

OneDisplay is digital signage that runs on any screen with a browser: a TV in
a lobby, a kiosk at a door, a stick behind a meeting room's display. A screen
shows a **channel**: slides, a layout of widgets over them, music, voice ads
and a schedule that changes what plays through the day. Every screen on one
channel plays the same thing at the same moment.

## The records

| Record | What it is |
| --- | --- |
| `Display Screen` | One paired screen: its channel, how it is turned (`rotate`), muted, dark, the last command and when it was last seen. Only ever made by a TV asking for a code. |
| `Display Channel` | What plays: a slide playlist, a widget collection, a music playlist, whether calls are read aloud and in which voice, a `programme` (schedule rows) and `ads`. |
| `Channel Programme` | A schedule row: Slides, Widgets, Music, Screensaver, Screen Off or Muted, on some days, between two times. A later row wins over an earlier one. |
| `Channel Ad` | A voice ad on a channel, every few minutes or at times of day. |
| `Slide Playlist`, `Display Slide` | Slides in order: Image, Video, Web Page (https only) or Design (HTML drawn at 1920 × 1080), each with seconds and optional dates. |
| `Widget Collection`, `Display Widget` | A layout: widgets in percent of the screen, each with a source, a mapping, settings, a layer and optional hours. |
| `Display Source` | Where a widget's rows come from: Records, Record, Report, Queue, Feed or Weather. |
| `Music Playlist`, `Display Track` | Tracks and a volume. |
| `Voice Ad` | A script, a tone, a language, a voice, a chime, and its recording. |
| `Display Voice` | A phrase recorded once in OneAI's voice, by language, voice and tone, with its public WAV. |
| `Queue`, `Queue Service`, `Queue Counter`, `Queue Ticket` | A place where people wait, its services (with a prefix), its counters (with who staffs them), and each ticket. |
| `Display Settings` | The emergency alert, on every screen. |

## How a screen plays

### Pairing and answers

- `/tv` (`www/tv.html`, `www/tv.py`) is one HTML file with its CSS inline and
  `public/js/one_display/tv.js`, which is **ES5 on purpose**: a 2017 TV runs
  Chromium 53. `tests/test_display.py` parses it with acorn at `ecmaVersion:
  5`. Nothing is bundled.
- `screens.start` (guest) gives a six-digit code and a secret; only the
  secret's hash is kept. `screens.pair` (desk) takes the code. `status` hands
  the token over once, then keeps only its hash.
- `screens.state` (guest, with the token) answers every two seconds with the
  server's time, the screen's turn, mute and dark, the last command, the
  alert, the brand, the zone, today's date in words, and the channel.
- **Full and light answers.** `programme.compose` builds the whole channel
  and a `revision` hash of it. A screen sends the revision it has as `have`;
  when it matches, `programme.light` sends only the mode, the ads and each
  widget's rows. A slide playlist goes over the wire once, not every two
  seconds.
- **Why polling.** An old TV's browser drops a WebSocket on every hiccup and
  some never reconnect; a plain request recovers by itself, and two seconds is
  what a person at a board expects.

### Playing in step

Every playlist runs on one clock that started at the Unix epoch, so where it
is now is the time mod its length. A screen keeps its offset from the
server's `now` and needs nothing else, so two screens agree to well under a
second without talking. Music does the same per track and nudges the player
when it drifts. Ads "every few minutes" pick their minute from a hash of the
slot (`programme.ads`), so they sound random and still play together.

### The frame

The player draws on a 1920 × 1080 frame (1080 × 1920 for a portrait
channel), scaled to the screen and turned by the screen's `rotate`. Widgets
are positioned in percent and sized in `em` from their own box, so a layout
looks the same on any screen. Each kind is a renderer `KINDS[type](box, one,
w, h)` returning `{update, drop}`; a Custom widget runs in a sandboxed iframe
and is posted its rows.

### Offline

A service worker at `/tv-worker.js` (`worker.py`, a page renderer, because
`www/` cannot serve a script) keeps the page, the script and every `/files/`
media first-fetched. The last answer is kept in localStorage, whenever the
channel changes shape and its rows once a minute, so a screen restarted with
no network plays what it had.

### Sound

One queue for calls, ads and alerts, so two never talk over each other; the
music goes quiet under them. Browsers keep sound off until a key is pressed,
so a new screen says so until OK is pressed once.

## Sources

A widget never reads data. It declares **slots** (`widgets.TYPES`), and a
`Display Source` fills them through a **mapping**, `{"title": "{customer}"}`.
A premade widget (queue board, kiosk, weather, clock) takes its source whole
instead.

- **Only mapped fields leave the server** (`sources.fill`), each formatted
  there in the channel's language.
- **A source reads as whoever saved it** (`read_as`, set on save), with their
  permissions checked on every read (`sources._as`), and only fields they
  may read (`get_permitted_fields`). A source whose maker lost access goes
  blank.
- **Read once, cached** per source for its `refresh` or its kind's default
  (`sources.KEPT`); the last good answer stands when a read fails.
- **Feeds** are read only over https from addresses that resolve to the public
  internet (`sources._public`), without redirects, at most 1 MB, with
  `defusedxml`. A feed is the workspace's own choice of address, so it is not
  a subprocessor and not an optional service.
- **Weather** is Open-Meteo through TrustCenter's optional service
  `display_weather`, off until a workspace turns it on.

## Voices

`voices.py`. A phrase is recorded once per language, voice and tone through
OneAI's `display_voice` job (Gemini speech through the gateway's `make`),
wrapped as a WAV every TV plays, kept as a `Display Voice` with a public file.
A board's call is made on demand: the first answer that needs "Ticket A 7,
counter 2" enqueues it and sends no audio; the screen waits four seconds for
it and then says it in its own voice. Nothing is recorded while OneAI is off.

## What OneAI does

`make.py` makes a picture for a slide, a designed slide, and a Custom widget's
code; `voices.record` records a voice ad. Each comes back as something a
person keeps or not; nothing goes on a screen by itself. `ai.py` gives the
chat `queue_now`, `screens_now` and `plan_voice_ad` (a card), and says in
`NOT_FOR_AI` why every other change is a person's.

## Who may do what

`abilities.py`. **OneDisplay User** works a counter. **OneDisplay Manager**
runs the screens and what they show, and holds **Send an Emergency Alert**
(`display_alert`, a permission type on Display Settings). A screen itself is
nobody: its token lets it read its own channel and, from its own kiosk
widget, take tickets.

## What it tells people

`notifications.py`, sent by `tell.py`: **Screen Offline** (every five
minutes, a paired screen silent ten minutes and not turned off, once per
silence) and **Emergency Alert Sent** (to the others who may send one).

## Decisions that cost something

- **No Frappe Builder.** Builder's pages use flex `gap` and `:has()`, which a
  TV's Chromium ignores, its fonts come from Google, and installing it brings
  pandas, duckdb and litellm. A Design slide is plain HTML at 1920 × 1080,
  written by hand or by OneAI, and widgets are placed in our own editor
  (`frontend/src/display/Layout.vue`) over a live preview of the screen.
- **No LightningJS.** WebGL cannot draw HTML from a design or a custom
  widget, its text does not shape Arabic, and cheap sticks have unreliable
  WebGL. The player is plain DOM with `transform` and `opacity`.
- **Dates on the screen come from the server.** A TV's `Intl` is too old to
  trust, so today's date and the weather's day names are formatted with
  babel in the channel's language.

## Files

| File | What it is |
| --- | --- |
| `screens.py` | Pairing, a screen's answer, kiosk tickets, commands, the alert, previews |
| `programme.py` | What a channel plays now: the schedule, slides, layout, music, ads |
| `sources.py` | Reading a source, filling a widget's slots, feeds and weather |
| `widgets.py` | Every widget kind: slots, settings, which sources fill it |
| `layout.py` | The layout editor's server |
| `queue.py` | Tickets, the board, the counter's actions |
| `voices.py`, `make.py` | What OneAI records and makes |
| `worker.py` | Serves the TV's service worker |
| `tell.py`, `notifications.py` | What it tells people |
| `abilities.py`, `legal.py`, `setup.py`, `tour.py`, `ai.py` | The READY pieces |
| `demo.py`, `checks.py`, `tests/` | The showroom, its checks, the pure tests |
| `page/counter/`, `page/display_layout/` | The counter, and the layout editor's island |
| `patches/widgets_from_queue.py` | The first slice's queue channels, moved onto widgets |
| `../www/tv.html`, `../www/tv.py`, `../public/js/one_display/` | The player and its worker |
| `../public/js/one_display/display_control.js` | Settings and the foot |
| `../../frontend/src/display/` | The counter and the layout editor |
