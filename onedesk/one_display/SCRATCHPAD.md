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
