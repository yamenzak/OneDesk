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

