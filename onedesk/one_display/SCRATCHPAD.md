# OneDisplay — scratchpad

What is known to be missing or wrong. How it works and why is `AGENTS.md`.

## Before it is shown to a customer

- Try `/tv` on a real Tizen or webOS set. It was checked in desktop Chromium
  and its script parses as ES5; nothing has run on a TV yet.
- Speech has only been tried with OneAI's answer stubbed: the first real
  recording should be listened to in each language.
- A kiosk shows the ticket and prints nothing. A receipt printer needs a
  kiosk app, since a browser cannot print silently.

## Not built

- **A ticket waiting too long** tells nobody. It wants a threshold on the
  queue and a notification to the counters.
- **Commands over the socket.** Polling every two seconds is what a screen
  does; a socket would only make a command arrive sooner.
- **Video and music made by OneAI.** Pictures, slides, widget code and speech
  are made; the gateway has no video or music model yet.
- **A slide designer on a canvas.** A Design slide is HTML, written by hand or
  by OneAI, and previewed on the channel.
- **Pictures in Help.** The pages have none yet.
