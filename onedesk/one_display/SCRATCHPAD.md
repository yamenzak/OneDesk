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
- **A native wrapper** (Tizen, webOS, Android TV) around the same `/tv`:
  starts the player when the TV powers on, restarts a frozen page, and
  prints a kiosk's ticket silently. A separate project; no code here
  changes for it.
- **Templates are not mirrored for Arabic.** Their words come in the
  reader's language, but the layout is left to right, as OneDeck's decks
  are. Their pictures in the gallery are the English ones in the demo's
  colour, taken once; the template put on the screen is in the reader's.
- **Widgets on a screen do not come and go.** Motion is drawn by `play.js`,
  which draws a screen's backdrop; widgets are drawn by `tv.js`.
- **Whole numbers past 999 are joined only in English** (`packs.THOUSANDS`).
  Arabic and German change the words around a thousand, so those are
  recorded as whole sentences, as before.
- **A voice pack has not been listened to.** Its clips were tried with
  OneAI's answer stubbed; how joined Arabic pieces sound is unknown.
