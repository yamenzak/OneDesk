# OneDisplay

The one file for agents, OneAI and us: what OneDisplay is made of, its rules,
where each file is, and the decisions that cost something. What is known to
be missing is `SCRATCHPAD.md`; what people read is `docs/`.

OneDisplay is digital signage that runs on any screen with a browser: a TV in
a lobby, a kiosk at a door, a stick behind a meeting room's display. A screen
shows a **channel**: slides, a layout of widgets over them, and a schedule
that changes what shows through the day. What is heard is a **sound zone**:
music, voice ads and the calls of its queues, where one set of speakers is.
Every screen on one channel, and every player in one zone, plays the same
thing at the same moment.

Nothing here names a trade. A board is items, states and values, never beds
or bays; a zone is speakers, never a waiting room. The examples live in Help
and the demo.

## The records

| Record | What it is |
| --- | --- |
| `Display Screen` | One paired screen or radio (`kind`): its channel, its sound zone and whether it plays sound, how it is turned (`rotate`), muted, dark, the last command, when it was last seen, and what it reports of itself (Device). Only ever made by a TV asking for a code. |
| `Display Channel` | What is seen: a slide playlist, a widget collection, its size (`screen_size`, `width`, `height`, `sizes.py`), its language, a `programme` and the nightly `reload_at`. |
| `Sound Zone` | What is heard where one set of speakers is: a music playlist, a `programme` of Music or Muted rows, `ads`, whether calls are said (`announce`), and their language and voice. |
| `Channel Programme` | A schedule row: Slides, Widgets, Music, Screensaver, Screen Off or Muted, on some days, between two times. A later row wins. A channel takes only what is seen, a zone only Music and Muted. |
| `Channel Ad` | A voice ad in a sound zone, every few minutes or at times of day. |
| `Voice Pack`, `Voice Pack Clip` | One language, voice and tone, and each piece a call is joined from (a letter, a number, a word, a counter), with its recording as a file on the pack. |
| `Display Board`, `Display Board State`, `Display Board Item`, `Display Board Person` | Things people change by hand: the board's states (colour, time limit), its items (state, value, since when), and who may change it. |
| `Display Board Change` | Every change to a board, with the minutes the item spent in its state before. |
| `Slide Playlist`, `Display Slide` | What plays in order: a Presentation from OneCloud (every slide of it) or a Web Page (https only), each with seconds, optional dates and Paused. |
| `Widget Collection`, `Display Widget` | A layout: widgets in percent of the screen, each with a source, a mapping, settings, a layer and optional hours. |
| `Display Source` | Where a widget's rows come from: Records, Record, Report, Queue, Feed, Weather or Exchange Rates. |
| `Music Playlist`, `Display Track` | Tracks, each with its length and Paused, and a volume. |
| `Voice Ad` | A script, a tone, a language, a voice, a chime, and its recording. |
| `Display Voice` | A whole sentence recorded once in OneAI's voice, by language, voice and tone, with its public WAV: what a pack cannot join. |
| `Queue`, `Queue Service`, `Queue Counter`, `Queue Ticket` | A place where people wait, its services (with a prefix), its counters (with who staffs them), how long is too long, the zone its calls are said in, how its numbers are said, and each ticket. |
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
  alert, the brand, today's date in words, the channel (none for a radio)
  and its sound zone (`programme.heard`).
- **`/radio`** is the same page and script with nothing drawn (`TV.radio`):
  it pairs to a zone and shows the zone's name and what is playing.
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
server's `now`, taken from the quickest answers rather than the last
(`bestTrip`, aged after ten minutes), and needs nothing else, so two screens
agree to well under a second without talking. Music and a video with its own
sound are kept in step by `playbackRate`, at most 5% either way, and jump
only when more than two seconds out (`steer`). Ads "every few minutes" pick
their minute from a hash of the slot (`programme.ads`), so they sound random
and still play together. A call carries one `start`, three seconds after it
was made, so every player in a zone says it together.

### The frame

The player draws on the channel's frame, any size (`sizes.SIZES`: Landscape,
Portrait, Bar 1920 × 540, Square, Wall 3840 × 1080, or Custom), scaled to the
screen and turned by its `rotate`; a slide of another shape is letterboxed,
or fills the screen when its row says **Fill Screen**. Widgets are
positioned in percent and sized in `em` from their own box, so a layout looks
the same on any screen. Each kind is a renderer `KINDS[type](box, one, w, h)`
returning `{update, drop}`; a Custom widget runs in a sandboxed iframe and is
posted its rows.

**The bare widget, as a rule.** A renderer draws its content and behaviour
and nothing else: a ticker is text moving with its spacing, separator, speed
and direction, and has no background. Fill, words' colour, font, padding,
border, corners and shadow are the element's, set in the editor like any
object's and applied by `dress(box, look, unit)`. A **look**
(`widgets.LOOKS`) is a saved set of those offered per widget; a variation is
a look, never a new widget. `tests/test_display.py` holds that no renderer
sets a background, border or font of its own. A widget that only showed
data (Number, List) is now text and a table with data chips
(`chips.py`, `patches/number_and_list_are_words.py`).

### What a screen says about itself, and brakes

Every minute a screen reports its pixels, browser, memory where the browser
tells it (`deviceMemory`, `performance.memory`), how much its pictures take
decoded, its largest video, and why it last restarted (`report`, kept by
`screens._heard`). `screens._risks` sets **At Risk** with the reason before
anything fails. A browser gives no warning before it runs out of memory, so
the page reloads itself calmly between slides past about 80% of its heap,
and every night at the channel's `reload_at` (04:00 unless changed). A
frozen page cannot save itself; that is a native wrapper's job.

### Pictures as sharp as the screen

A picture is resized only when it is larger than the largest screen it is
shown on (`one_slide/sized.py`, at the edges in `store.SCREEN_EDGES`, quality
92), never made larger, the original kept, the copy served through
`one_slide.api.shown` with the edge. Videos are not re-encoded; one larger
than a screen says it shows is flagged on that screen.

### Offline

A service worker at `/tv-worker.js` (`worker.py`, a page renderer, because
`www/` cannot serve a script) keeps the page, the script and every `/files/`
media first-fetched. The last answer is kept in localStorage, whenever the
channel changes shape and its rows once a minute, so a screen restarted with
no network plays what it had.

### Sound

A screen plays sound only from its sound zone (`programme.heard`): music,
ads and calls, in one queue so two never talk over each other, the music
going quiet under them. An emergency alert is spoken in every zone. A video
plays its own sound only when its element says **Plays Sound** and the
screen's **Plays Sound** is on; the zone's music ducks to a quarter while
any screen in it plays such a video, known from the playlists' fixed timing
(`programme.duck`). Browsers keep sound off until a key is pressed, so a new
screen says so until OK is pressed once.

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

`voices.py` says text through OneAI's `display_voice` job (Gemini speech
through the gateway's `make`) and wraps it as a WAV every TV plays.

**Calls are joined from a voice pack** (`packs.py`). `packs.pieces` splits
whatever a ticket's format makes it into letters, numbers and separators:
A1828 is A, 1, 8, 2, 8; with **Whole Number**, 1828-3 is 1 thousand 828,
dash, 3, where the language joins thousands simply (`THOUSANDS`; elsewhere
the whole sentence is recorded). A queue's **Numbers Said** is Auto (digit by
digit from four digits), Digit by Digit or Whole Number. `programme.calls`
plays a whole sentence already kept as a `Display Voice`, else the pack's
clips, else asks for the whole sentence. A clip the pack lacks is recorded by
one background job per pack (`packs.ask`, `fill`), the call meanwhile said
in the screen's own voice. Clips are files on the `Voice Pack` (OneCloud's
Records › Voice Pack), attached quietly so a thousand of them leave no
timeline lines; **Make Again** replaces each in place, and deleting the pack
deletes them. `tv.js` decodes each clip once with Web Audio, cuts the
silence at either end and plays them end to end, holding at most 300.
Nothing is recorded while OneAI is off.

## Boards

`boards.py`. A `Display Board` is items, the business's own states (colour,
optional time limit) and/or a named value. `boards.change` is the only way
an item changes: it checks `may` (the board's people, or everyone with
OneDisplay when it names none), keeps a `Display Board Change` with the
minutes in the previous state, and wakes the screens. The **Boards** page
(`frontend/src/display/Boards.vue`) is the control on a phone; a board's QR
codes open one item's buttons. The **Board** and **Board Item** widgets draw
them; Board Item pointed at a counter shows what it serves. `tell.past_limits`
tells the board's people when an item passes its state's limit.

## Data on screens

A screen's editor offers OneSlide's data chips (`one_slide/data.py`) with a
Display Source as one more kind (`rows`, through the `one_slide_rows`
hook). A source is read again on its own clock (`sources.KEPT`); a saved
record a source reads (`live.record_saved`, on every doctype's save) drops
its cache and wakes the screens showing it, once a request.

## Slides

A slide playlist plays **presentations** from OneCloud, made in OneSlide,
and web pages (docs/ONESLIDE.md, stage 5). A row links a presentation's
**File**, picked through `one_slide.api.search`, which offers only what the
person picking may open; the playlist's `validate` checks the same, so a
playlist is never a way to show somebody's private slides. **New
Presentation** on the playlist makes one filed on the playlist and opens it.

Pictures and videos dropped on a playlist (`playlist.add_media`) become one
presentation each, the file filling its slide, filed on the playlist.

An element can come and go (OneSlide's Motion): `play.js` draws it on a box as
large as the slide moved by one keyframe track of `transform` and `opacity`;
a screen has nobody clicking, so what waits for a click comes a second after
the one before it.

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

`notifications.py`, sent by `tell.py`: **Past Its Time** (every two minutes,
an item past its state's limit, to the board's people, once each time),
**Screen Offline** (every five
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
| `screens.py` | Pairing screens and radios, a screen's answer and report, at risk, kiosk tickets, commands, the alert, previews |
| `programme.py` | What a channel shows and a zone plays now: the schedule, slides, layout, music, ads, calls, ducking |
| `sizes.py` | Screen sizes and the editor's frame for them |
| `packs.py` | Voice packs: splitting a ticket, the pieces a call needs, recording them |
| `boards.py`, `chips.py` | Boards, and data chips for what were Number and List |
| `playlist.py` | Pictures and videos dropped on a playlist |
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
| `patches/sizes_from_orientation.py`, `number_and_list_are_words.py`, `sound_in_zones.py`, `ads_on_their_record.py` | Orientation to sizes; Number and List to words; each channel's sound into a zone; ad recordings onto their ads |
| `page/boards/` | The Boards island |
| `../www/tv.html`, `../www/tv.py`, `../public/js/one_display/` | The player and its worker; `../public/js/one_slide/play.js` draws a slide |
| `../public/js/one_display/display_control.js` | Settings and the foot |
| `../../frontend/src/display/` | The counter and Boards |
| `../../realtime/handlers.js` | A screen joining its room, admitted by `live.admit` |
