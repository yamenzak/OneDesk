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
desktop, and `phone`, the places its breadcrumb lists as a menu on a phone
(docs/PASSOVER.md, The panel).
