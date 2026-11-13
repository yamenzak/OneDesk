# Browser checks

The key screens of every app, each opened in a browser as the demo person
whose work it is, against the demo workspace (`onedesk/one_demo`). A screen
passes when it shows what that person must see there, throws nothing in the
browser and refuses nothing. The list is `screens.mjs`; every desk page of
ours is on it (`tests/guards/test_browser.py`).

```sh
ONE_URL=http://onedesk.localhost:8002 ONE_DEMO_PASSWORD=… \
PLAYWRIGHT_FROM=/path/with/playwright CHROMIUM=/path/to/chromium \
node tests/browser/run.mjs            # every screen
node tests/browser/run.mjs project    # those whose address has "project"
```

`ONE_SHOTS=folder` keeps a screenshot of each screen.

A screen may also say `panel`, whether its module's panel is open on a
desktop, `phone`, the places its breadcrumb lists as a menu on a phone, and
`menu`, the places it lists on a desktop
(docs/STANDARD.md, The panel).

## Routes

`routes.mjs` opens every app from the rail as a person does, then a few of
its own rows (`ONE_ROWS`, 3), then presses Back all the way. At each step the
rail on screen must be the one that owns the page, must have rows, and the
address must not name another app; the last Back must land on Home. Back
from OneMail once drew Home inside OneMail's empty rail.
`tests/guards/test_rail.py` holds what can be read without a browser.

```sh
ONE_URL=… ONE_DEMO_PASSWORD=… node tests/browser/routes.mjs          # every app
node tests/browser/routes.mjs onemail                                 # apps whose name has "onemail"
```

Run it in a pass that touches navigation and after every upstream update.
