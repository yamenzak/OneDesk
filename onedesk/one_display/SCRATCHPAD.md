# OneDisplay — scratchpad

What is known to be missing or wrong, in the order it will be done. The plan
and its reasons are `AGENTS.md`.

## Before it is shown to a customer

- Try `/tv` on a real Tizen or webOS set. It was checked in desktop Chromium
  and its script parses as ES5; nothing has run on a TV yet.
- A paired screen's list row says Online from `last_seen`, which is written at
  most every thirty seconds, so Offline shows after ninety. Good enough for a
  list; a notification for a screen gone quiet is stage 2.
- The board shows the company's logo only if the company has one; the demo
  company has none, so the head shows its name on its colour.
- A kiosk shows the ticket for eight seconds and prints nothing. Printing to
  a receipt printer is a kiosk app's job (the browser cannot reach one
  silently); until then the person reads the number off the screen.

## Stage 2 — register the module

- Help pages with pictures (`docs/`), a tour of pairing, What's New.
- `notifications.py`: a ticket waiting past a threshold, a screen offline ten
  minutes, an alert sent (to every OneDisplay Manager).
- `abilities.py`: send alerts as its own ability, not only Manager.
- `legal.py`: what a screen keeps in its browser (an id and a token) and that
  it is a guest.
- `setup.py`: make a queue, make a channel, pair a screen.
- `ai.py`: OneAI may call next and read the board; it may not send an alert.
- `checks.py` for the demo, `tour.py`, Settings foot.
- Then `ready.MODULES`.

## Stage 3 — live and offline

- Socket for commands and the alert, polling kept as the fallback.
- Service worker: the page, the script and the last state, so a screen
  restarted with no network shows what it last had.
- Server time in every answer; the screen keeps its offset.

## Stages 4 to 6

See `AGENTS.md`, The plan.
