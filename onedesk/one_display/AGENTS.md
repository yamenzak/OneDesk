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
| `Slide Playlist`, `Display Slide` | What plays in order: a Presentation from OneCloud (every slide of it) or a Web Page (https only), each with seconds, optional dates and Paused. |
| `Widget Collection`, `Display Widget` | A layout: widgets in percent of the screen, each with a source, a mapping, settings, a layer and optional hours. |
| `Display Source` | Where a widget's rows come from: Records, Record, Report, Queue, Feed, Weather or Exchange Rates. |
| `Music Playlist`, `Display Track` | Tracks, each with its length and Paused, and a volume. |
| `Voice Ad` | A script, a tone, a language, a voice, a chime, and its recording. |
| `Display Voice` | A phrase recorded once in OneAI's voice, by language, voice and tone, with its public WAV. |
| `Queue`, `Queue Service`, `Queue Counter`, `Queue Ticket` | A place where people wait, its services (with a prefix), its counters (with who staffs them), how long is too long, and each ticket. |
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
- **Woken, and polling behind it.** A screen also joins its own room on
  Frappe's socket (`live.py`, `realtime/handlers.js`, admitted by its
  token): any change to what it plays, a command, a call at a counter, sends
  `onedesk_display_wake` after commit, and the screen asks at once, within
  half a second of jitter. While the socket is up it polls every fifteen
  seconds instead of two. An old TV's browser drops a WebSocket on every
  hiccup and some never reconnect, so polling is never switched off: the
  socket only makes things arrive sooner.

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
- **Exchange Rates** are ERPNext's own (`get_exchange_rate`, from the
  workspace's Currency Exchange records), for the listed currencies in the
  source's currency or the company's; a currency with no rate is left out.

## Voices

`voices.py`. A phrase is recorded once per language, voice and tone through
OneAI's `display_voice` job (Gemini speech through the gateway's `make`),
wrapped as a WAV every TV plays, kept as a `Display Voice` with a public file.
A board's call is made on demand: the first answer that needs "Ticket A 7,
counter 2" enqueues it and sends no audio; the screen waits four seconds for
it and then says it in its own voice. Nothing is recorded while OneAI is off.

## Slides

A slide playlist plays **presentations** from OneCloud, made in OneSlide,
and web pages (docs/ONESLIDE.md, stage 5). A row links a presentation's
**File**, picked through `one_slide.api.search`, which offers only what the
person picking may open; the playlist's `validate` checks the same, so a
playlist is never a way to show somebody's private slides. **New
Presentation** on the playlist makes one filed on the playlist and opens it.

`programme.slides` gives a screen each of a presentation's slides in turn
(`one_slide/play.py`, `for_screen`): the editor's own elements, cleaned
when they were saved, each slide as long as `play.length` says (a video that
does not loop watched to its end, then the slide's Advance, else the row's
seconds) and changing with its own transition (Magic Move fades), hidden
elements left out, a table drawn to HTML, and its pictures
and videos at addresses sealed with the site's key (`play.seal`,
`one_slide.api.shown`), since a screen signs in as nobody.

**One renderer.** `public/js/one_slide/play.js` is ES5 and draws a slide
from its elements on the presentation's frame scaled to the screen: text as the
sanitised HTML it is, shapes as SVG (Suite's and our star and block arrow),
fades, blur, free CSS, pictures with their crop, videos joining the shared
clock. Eight-digit colours become `rgba()` for Chromium 53, and every
number, colour and address is checked again before it is drawn. A slide
taken off has its videos paused and emptied (`play.release`), since an old
TV keeps a video's decoder until then.

The pictures, videos and designed slides playlists held before stage 5
were turned into one-slide presentations filed on their playlist by
`patches/presentations_on_screens.py`, a designed slide through
`one_slide/convert.py`.

## What OneAI does

`make.py` makes a Custom widget's code and a piece of music;
`voices.record` records a voice ad. Each comes back as something a person
keeps or not; nothing goes on a screen by itself. Pictures, videos and
designed slides are made in a presentation, with OneSlide's own jobs
(`one_slide/ai.py`).

Music (Lyria) is one call, made in a `long` job. It arrives at the end of its
playlist **Paused**, its length read from the file, and whoever asked is told
(**Made by OneAI**, or **Not Made by OneAI**). A voice model is told only its own words, never
OneAI's voice, which it would read aloud (`jobs.MAKES`). `ai.py` gives the
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
silence), **Long Wait** (every two minutes, a ticket waiting longer than its
queue's **Tell Counters After**, to whoever staffs its counters, once per
ticket), **Made by OneAI** and **Not Made by OneAI** (to whoever asked for a
video or music), and **Emergency Alert Sent** (to the others who may send
one).

## Decisions that cost something

- **No Frappe Builder.** Builder's pages use flex `gap` and `:has()`, which a
  TV's Chromium ignores, its fonts come from Google, and installing it brings
  pandas, duckdb and litellm. Slides are made in OneSlide, Suite's editor
  with our Builder half, and drawn on the screen by an ES5 renderer of what
  it saves; widgets are placed in the same editor, as elements on a screen's
  backdrop presentation (`screen.py`, stage 7 of docs/ONESLIDE.md).
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
| `layout.py` | A collection's widgets, read and saved back |
| `screen.py` | A collection edited in OneSlide's editor: its backdrop presentation, widgets on and off its slide, what the TV draws behind them |
| `live.py` | Waking screens over the socket |
| `queue.py` | Tickets, the board, the counter's actions |
| `voices.py`, `make.py` | What OneAI records and makes |
| `worker.py` | Serves the TV's service worker |
| `tell.py`, `notifications.py` | What it tells people |
| `abilities.py`, `legal.py`, `setup.py`, `tour.py`, `ai.py` | The READY pieces |
| `demo.py`, `checks.py`, `tests/` | The showroom, its checks, the pure tests |
| `page/counter/` | The counter's island |
| `patches/widgets_from_queue.py` | The first slice's queue channels, moved onto widgets |
| `patches/presentations_on_screens.py` | Pictures, videos and designed slides, made presentations |
| `../www/tv.html`, `../www/tv.py`, `../public/js/one_display/` | The player and its worker; `../public/js/one_slide/play.js` draws a slide |
| `../public/js/one_display/display_control.js` | Settings and the foot |
| `../../frontend/src/display/` | The counter and the layout editor |
| `../../realtime/handlers.js` | A screen joining its room, admitted by `live.admit` |
