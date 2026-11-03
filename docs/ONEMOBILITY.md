# OneMobility, as it was first built

This is a record of OneMobility as it was built in the old repository
(`yamenzak/OneApp`, at `d53b02d`), before One moved onto the desk here. It is
history and a starting point, not a plan: when OneMobility is built in
onedesk it will sit on OneInterface, OneCloud, OneAI and the centres, and much
of what it had to build for itself there already exists here.

The original is worth reading in full before starting again. It lives in three
places in that repository:

- `apps/oneapp/oneapp/onemobility/` — the server: 28 Python files, nine
  doctypes, and a README of almost 1,500 lines that is the real design document.
- `apps/oneapp/frontend/src/modules/onemobility/` — the screens (about 6,400
  lines of Vue and JavaScript; the network map alone is 2,170).
- `tests/test_vehicle_events.py`, `test_vdv452.py`, `test_vdv457_3.py`,
  `test_forecast.py`, `test_scoring.py`, `test_marker_shapes.py` and others.

## What it was

A transport authority receives timetables as files and vehicle positions as a
feed, and then reads both in a spreadsheet. OneMobility was where they looked at
them instead: a live map of every vehicle, the network drawn under it, and a
clock that runs the same map backwards to any moment it has data for.

The sentence it was built to say was **"here is why the 12 ran late at 07:40
last Tuesday"**: the same screen, a different clock. Germany first, through
VDV, because that is where the customers were and the formats are published;
generally available, so it said Line and Stop rather than one customer's words.

It was not a planning tool, not an AVL system that talks to vehicles, not a
passenger app and not general BI. It read other people's timetables and
telemetry and showed an operator's own staff what happened.

## The decision everything followed from

**The model was GTFS's, and every format was an importer into it.** Agency,
route (called Line, because riders say line), trip, stop, stop time, shape,
calendar. VDV 452 was an importer, GTFS was an importer, NeTEx would have been
one. GTFS was chosen because it is the intersection: every other format fits
into it without losing anything a screen draws. VDV's planning concepts that
GTFS has no word for (duties, blocks, rosters) were dropped on import.

The live side was the same: VDV 454, GTFS-Realtime and SIRI are three spellings
of four facts: where a vehicle is, when it is due, how full it is, how late it
is. One normaliser per dialect, one model behind them.

## Reference data were doctypes; facts were not

| Doctypes (people open them) | Plain tables (people aggregate them) |
|---|---|
| Transit Source, Transit Feed, Transit Agency, Transit Line, Transit Stop, Transit Vehicle, Transit Claim, Transit Marker Style, OneMobility Settings | `observation` (positions), `stopEvent`, `stopCount`, `vehicleEvent`, `prediction`, and the roll-ups `serviceHour`, `vehicleDay`, `stopHour`, `eventHour` |

The arithmetic decided it: 500 vehicles reporting every 15 seconds over an
18-hour day is 2.2 million rows a day. As documents that is hours of CPU and
hundreds of bytes of bookkeeping per GPS ping; as plain rows it is about 110 MB
written in seconds by multi-row `INSERT`. So facts lived in tables created by a
patch, written in bulk, and read only through whitelisted endpoints that return
rows already grouped. Screens asked "occupancy by hour for line 12 in March",
never for rows, so the store could change later without any screen changing.

**Four tiers**, declared once in a shared `facts.py` engine:

- **Hot:** MariaDB, partitioned by day, about 30 days of raw rows. Retiring a
  day was `DROP PARTITION`, never a sixty-million-row `DELETE`.
- **Warm:** one compressed track object per vehicle per day on R2. This was the
  playback format.
- **Frozen:** one Parquet file per day on R2. A frozen day could be brought back
  from the map ("Bring this day back"), and was then held for a week.
- **Aggregate:** MariaDB, kept forever, storing **percentiles rather than
  means**: p50, p85 and p95 of delay, p85 of occupancy. A year of it is tens of
  thousands of rows, and every chart and forecast read only this tier.

How long each tier was kept was the workspace's choice, in Settings → Transit
history.

**A stop visit was inferred.** No feed says "vehicle 41 is serving
Alexanderplatz", only a coordinate. `arrivals.py` said a vehicle is at a stop
while it is within 50 metres of it, and one unbroken run of readings inside
that circle is one visit. From visits came dwell and **headway**, and headway
was the number that showed bunching: a ten-minute service running as a pair
four minutes apart and then a sixteen-minute gap averages ten and is unusable.
It refused to derive boardings from occupancy differences. It recorded
boardings only where a VDV 457-3 counter reported them.

## Getting data in

**A source was a folder**, and that was all the configuration there was. Upload
folded into Folder: a file landed in a OneCloud folder, and an SFTP, FTP, SMB or
WebDAV drop folder was the same thing. There was no format dropdown: `sniff.py`
opened each delivery and recognised it from what was inside. A GTFS feed by its
member names, VDV 452 by its `tbl;` lines, XML by its root element,
GTFS-Realtime by a protobuf field tag. It unwrapped a gzip nobody mentioned,
found a feed one folder down in a zip, read a delivery missing one file and said
so, and refused an unknown file by naming what it did find in it. The whole
folder was walked, oldest first, 25 files per poll, remembered per file, so a
late or corrected delivery was taken and a four-year backlog worked through.

Behind every door was one pipeline (fetch, parse, normalise, resolve, commit),
plus a **streaming** mode for sockets: windows of just under five minutes that
the scheduler chained, committing on a count and on a clock. It read SIRI,
VDV 454 (placing a vehicle at the last stop it called at, never between stops)
and GTFS-Realtime (protobuf decoded without a dependency).

**The VDV shelf** was written down in `vdv.py` and drawn on a Protocols screen:
every part of the standard, whether we read it, whether that was verified
against the published PDF, and **which door it arrives through**: a folder, a
stream, or the vehicle's own network. The last of those is all of IBIS-IP
(VDV 301), which needs a bridge on every vehicle. That column was the one that
saved a project a quarter.

**Duplicates were a conflict, not magic.** Every imported record carried a
natural key and was written through a `Transit Claim`. When two sources claimed
one key, the customer's precedence picked the winner as a whole claim, never
field by field. The loser was kept, and re-ordering sources re-settled at once.
The Disagreements screen listed every source's answer per contested key: Drawn,
Agrees or Overruled. A stop a vehicle used but no feed declared was an
**inferred** stop, drawn in amber, and only a person could accept it into the
network.

## What a person could do

- **Network:** the live map. Every vehicle moving, every line drawn, a clock to
  scrub back through any day with data and forward into what is expected.
- **Insights:** peak hours, punctuality, occupancy, dwell, bunching, the
  vehicles that report faults, all from the aggregate tier, narrowed by the
  same facet bar as the map.
- **Outlook:** a fortnight ahead, read from the same history. Arrival times,
  the chance of running late, the chance of being full, collapsing gaps,
  anomalies, fault chances. A score footer said how often those forecasts had
  held.
- **Against the plan:** each planned call matched to what actually came, by
  line, stop and nearest time (a trip id only matches about half the time in
  this market). A call with nothing within 45 minutes was reported missed
  rather than matched to the next hour's bus.
- **Protocols, Sources, Disagreements**, and the records themselves: lines,
  stops, vehicles, agencies, each a normal document with comments, history and
  permissions.

**Forecasting used no machine learning.** Every number was arithmetic over the
percentile tier: a weighted mean, a normal tail, a z-score. Each answer carried
its basis and its spread, and nothing was drawn without the spread. Every
prediction was written down **before** the answer existed (`scoring.py`) and
settled the night after, because re-forecasting yesterday from a history that
already contains yesterday always agrees with itself. What was scored was
whether reality landed inside the offered band, not the error of one number.
AI was kept for the sentence ("Line 12 is reliably late leaving the
Hauptbahnhof on weekday mornings, and has been since March") and never for
the arithmetic.

**What the vehicle said about itself** (VDV 301): doors, faults, trips, a
broken counter, lost GPS, as a `vehicleEvent` tier that stored edges, not
samples. A row was written only when a state changed, plus once every 15
minutes of silence so a dead bridge could be told from a quiet one. The
vocabulary was VDV's own (`AllDoorsClosed`, `EmergencyRelease`). Trouble was an
indexed column, and measured dwell came from the open-door spans. On the map a
faulted vehicle wore a red ring under its marker.

## The map

The live network screen was the product. It was deliberately **not** the
generic map view: that one (pins over a `Geolocation` field, for any doctype)
was built in the engine for everyone, with stops as its first user. The network
screen was a bespoke surface on top of it.

**Rendering.** MapLibre GL JS (BSD-3, so a plain dependency), on WebGL, which is
what makes a thousand moving markers possible. The ground was OpenFreeMap's
keyless vector tiles through one `basemap.py`. The plan was Protomaps
`.pmtiles` on our own R2, so no third party learns which city a customer
watches, and the move would be one URL. One of the four basemap styles was
ours: `scripts/gen_basemap.py` took Positron (BSD-3, vendored with its licence),
pointed it at OpenFreeMap and repainted it from a small palette in the
product's look. Three silent traps were fixed there. Positron expects a
Metropolis font, a `name:nonlatin` on every place and a `rank` on every city,
and OpenFreeMap provides none of the three, so the first render was a good map
of Berlin without the word Berlin on it.

**The layer stack**, bottom to top, in `Network.vue`:

1. `surface`: an optional canvas overlay (see below), under everything.
2. `lines-casing` then `lines`: every route drawn twice, a wide casing in the
   ground's ink and the line's own colour on top, widths interpolated by zoom
   (4.5 px at zoom 10 to 13 px at 16). The casing keeps two routes legible
   where they share a street. A line filtered out stayed at 18% opacity,
   because a route alone on a blank map has lost the junctions that make it
   readable.
3. `trail`: the dotted path of the vehicle that is open.
4. `stops` and `stops-interchange`: a circle per stop, bigger where more than
   one line has *actually* been seen there (observed, not timetabled), with a
   second inner circle for the interchange double ring. Inferred stops had an
   amber stroke.
5. `demand`: graduated circles per stop for the stop overlays.
6. `ghosts`: hollow amber rings where a trip is due to be, when the clock is
   past now. Deliberately unlike both a stop and a vehicle.
7. `vehicles`: a symbol layer of drawn silhouettes, rotated to their bearing,
   coloured by occupancy, at 40% opacity once a position goes stale.

**Moving a vehicle between reports** (`lib/motion.js`, pure and unit-tested).
A feed reports every 15 to 30 seconds and a marker that jumps reads as broken.
So each frame (`requestAnimationFrame`) the vehicle moved **along its own
line's shape**, never in a straight line through buildings:

- **project:** snap the reported GPS point onto the line's polyline, because raw
  GPS lands in gardens and on roofs.
- **advance:** interpolate along the shape between the last two reports, at a
  speed from a short rolling window rather than one noisy gap.
- **ease:** when a new report lands, glide to it over about a second rather
  than teleporting.
- **tangent:** the marker faces the road, from the shape's tangent at that
  point rather than from frame-to-frame movement (which points a standing bus
  north and swings a corrected one sideways). The shape is walked in both
  directions, so a vehicle going backwards along it is turned 180°, or half the
  fleet drives backwards up its own route. One pass returned point and bearing
  together, because this ran per vehicle, sixty times a second.
- **stale:** a vehicle that stopped reporting was carried forward faintly for a
  short grace period, then marked stale. A stale position drawn as live is what
  makes an operator stop trusting the screen.

**The markers** (`lib/markers.js` and `art/`). A mode (what the network runs,
from the feed) and a shape (what the map draws) were kept apart. They start
identical, and a workspace could set a shape per mode (`Transit Marker Style`)
or per line, for a heritage tram on a bus network. There were 33 drawings (bus,
tram, metro, train, ferry, cable car, rickshaw and the rest) as 40×40 SVGs, nose
up, with the body as exactly one path filled `#00FF00`. That green was the
trick: MapLibre needs a raster and a raster cannot be recoloured, so the green
was swapped for the occupancy colour in the SVG *source* before rasterising,
once per shape per occupancy band actually on screen. Below zoom 13 the map
used squat canvas-drawn silhouettes, deliberately wrong about proportion (a real
bus seen from above is a tick at 22 pixels). Above it, the detailed art at 0.78
scale, about 31 pixels. A test held every SVG to those rules. An emoji per line
(🚇 beside U6) was used wherever a thing was *named*, never as the marker: an
emoji cannot carry occupancy, is a side view that lies on its side when rotated,
and is mush at 16 pixels.

**The colours** (`lib/palette.js`) were one vocabulary for the map and the
charts. Occupancy was five named states (GTFS-RT's), with a separate token per
light and dark ground, chosen by running the palette validator for colour-blind
separation rather than by eye. Delay used a diverging scale, because early and
late are opposite failures. A line used its operator's own colour first ("the
100 is red"), with the palette only as a fallback.

**The overlays** (`lib/layers.js`, one declaration read by the map, the switcher
and the key). One overlay at a time, from two shapes:

- **Surface:** *where it runs late* and *where it fills up*, a measure averaged
  over a grid of places. Deliberately **not** MapLibre's `heatmap` layer, which
  draws density: two hundred readings thirty seconds late would glow brighter
  than ten readings ten minutes late. Instead the server returned the mean per
  grid cell, with the count as confidence, and cells under eight readings were
  dropped. `lib/surface.js` painted the grid into a canvas, one pixel per cell,
  and handed it to MapLibre as a canvas source with linear resampling, so the
  GPU did most of the smoothing. The blur was a **normalised convolution**
  (Knutsson's method): blur the weighted values and the weights separately and
  divide, so an empty cell pulls nothing towards zero and the blurred weight
  becomes the alpha. The kernel reached one cell and no further, because delay
  lives on corridors and junctions, not across a district. The cell size
  followed the zoom in three steps (about a kilometre, a hundred metres, ten
  metres), and the colour range was the 5th to 95th percentile, so one broken
  bus did not flatten the scale.
- **Points:** *where the service goes* (visits) and *where the wait bunches*
  (p85 headway over the average), as circles per stop whose *area* tracks the
  value.

The chosen overlay lived in the URL, so "the corridor where U6 loses its time"
was a link someone could send.

**What a person could do to it.** The controls were an icon rail under the zoom.
The legend was a small read-only key, bottom left, showing only rows for what
was drawn. Clicking a route isolated it: everything else went grey, without
re-querying anything, because isolation is a way of looking and a facet is a
question to the server. Hovering gave a stop's name and the lines seen there, a
vehicle's fleet number, line, load and delay, or a route's name and how many
were out. Popups were built as escaped HTML, because a stop name comes from a
customer's feed. The ground was the workspace's choice: four styles, place
names on or off, and Full, Quiet (the default) or Minimal detail. Those applied
without a reload by toggling layer visibility, and had to know both `road_*`
and `highway_*` layer names, because the two style families spell roads
differently.

**One screen, two clocks.** Live mode was the socket; playback was the day's
track objects fetched from R2 and scrubbed entirely in the browser, with no
query per frame. Dragging past now on today marked the clock *Expected*: the
vehicles left, every route took the colour of the delay it usually reaches at
that hour, and the hours ahead were drawn fainter behind a dashed "now" mark.
For a trip due to be somewhere, the server sent **two stops and a fraction of
time between them, never a coordinate**. The browser already held every shape
for the motion code, and a second geometry on the server would eventually
disagree about a corner.

**Privacy and the map.** A vehicle position is not personal data. The real fear
was a rival seeing load factors before a tender. The only thing leaving a
workspace was tile requests from the reader's own browser, which reveal an area
and never a route. That host was named as a subprocessor, and one setting drew
the ground flat with no tiles at all.

**The demo** was six real Berlin lines across four modes (the 100 bus, U1, U2,
U6, U8 and S1) in their operators' own colours, sharing real interchanges so
the casings could be judged, with ten vehicles reporting every minute over a
fourteen-hour day and lateness shaped per line and per hour. The first version
had every line equally punctual, which drew flat charts that looked correct and
hid every bug the charts existed to show.

## What carries over, and what onedesk already has

- **The map view** for any doctype with a position exists here (OneInterface's
  map view in Canvas). The network screen would be an island on top of it, the
  way OneMail and OneCloud are.
- **Folders** are OneCloud's. A source being a folder is natural here.
- **R2 storage, Cloudflare and the gateway** are already wired, so the warm and
  frozen tiers and the AI sentence have a home.
- **Centres**: its settings, roles, notifications, agreements, AI jobs and keys
  would be its part of each centre, not screens of its own. Its keys would go
  in a `shortcuts.py`: space to play or pause the clock, arrows to step it,
  L for live.
- **OneDisplay** can put the live map on a control-room wall.
- **Several companies**: a workspace running buses for two operators is the
  case this was not built for, and the first thing to design.

What should be taken nearly as it was: the GTFS-shaped model, facts outside the
document machinery, percentiles in the roll-up, `sniff.py`, the claim and
precedence model, `motion.js`, `surface.js` and the marker art with its rules.
They are pure, tested, and were the hard parts.
