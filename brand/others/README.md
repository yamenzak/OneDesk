Other companies' marks, used only to say which app a button opens (the
calendar's Subscribe buttons) or which company a server or a key is with. Each is theirs; none is changed except to pass
frappe's SVG sanitiser, which drops `gradientTransform`, `style` and `<image>`:

- `google-calendar.svg` — Google Calendar's icon (Wikimedia Commons), as is.
- `apple-calendar.svg` — the Apple logo (Simple Icons), filled with the text
  colour so it reads in the dark theme. Named for the app because frappe's own
  sprite already has an `apple`, and the sprite's wins.
- `outlook.svg` — Outlook's 2025 icon (Wikimedia Commons). Its gradients'
  transforms are baked into their coordinates and its styles written as
  attributes; the five rotated highlights became circles of the same area,
  which is not visible at a button's size.

The providers OneAdmin's servers and setup name, from Simple Icons (CC0;
16.37.0 for the server providers added on 12 November 2026), each path filled
with its company's colour from Simple Icons (AWS's orange, so it reads in the
dark theme): `aws.svg`, `oracle.svg`, `cloudflare.svg`, `stripe.svg`,
`google-cloud.svg`, `digitalocean.svg`, `hetzner.svg`, `vultr.svg`,
`akamai.svg` and `scaleway.svg`. Simple Icons dropped Azure at Microsoft's
request, so `azure.svg` is Gil Barbara's SVG Logos (CC0, `logos:microsoft-azure`
in Iconify 1.2.20), as is. Each is named for the provider in lower case with
spaces as dashes, which is how a server's card and the Servers list find it.
`other.svg`, for a machine on no cloud we know, is Lucide's `server` (ISC),
drawn in the text colour.

`scripts/icons.py` registers them as Custom Icons beside the One marks.
