Other companies' marks, used only to say which app a button opens — the
calendar's Subscribe buttons. Each is theirs; none is changed except to pass
frappe's SVG sanitiser, which drops `gradientTransform`, `style` and `<image>`:

- `google-calendar.svg` — Google Calendar's icon (Wikimedia Commons), as is.
- `apple-calendar.svg` — the Apple logo (Simple Icons), filled with the text
  colour so it reads in the dark theme. Named for the app because frappe's own
  sprite already has an `apple`, and the sprite's wins.
- `outlook.svg` — Outlook's 2025 icon (Wikimedia Commons). Its gradients'
  transforms are baked into their coordinates and its styles written as
  attributes; the five rotated highlights became circles of the same area,
  which is not visible at a button's size.

`scripts/icons.py` registers them as Custom Icons beside the One marks.
