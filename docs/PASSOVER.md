# The passover

Every screen of One, one at a time, walked against the twenty points of
`docs/STANDARD.md`. You decide when a screen is done and when the next one
starts. What each walk found and fixed is in its commit message; where each
area stands and what is up next are in `docs/PASSOVER-LOG.md`. How any pass
is run, whatever its focus, is the `passthrough` skill.

The rules check what a machine can (`python3 scripts/lint.py --list`). The
walk is for what it cannot: placement, the look, the words, the flow, a
phone. A new bad practice found on any screen gets a rule first, then the
fix.

## How one screen goes

1. Screenshot it and read the code behind it, and read its module in
   `docs/ATLAS.md`: what still waits, has no demo record, prints on
   ERPNext's format, lists only a number or reads in English.
2. Look at it in the browser as the people who use it, at 1440 and 390,
   light and dark, English and Arabic.
3. Write the findings under the twenty points, for the commit message, as a
   table of every point saying what was looked at, even where nothing was
   found. A point left out of the table is a point not checked. Then
   anything else about using it (the `ux` skill).
4. Fix them, look again in the browser, and run the gates: the rules, and
   the demo suite for the screen's module.
5. Commit, push, and show you a screenshot.
6. Wait for your word before the next screen. A module is not done while its
   modules have anything waiting in the atlas.
