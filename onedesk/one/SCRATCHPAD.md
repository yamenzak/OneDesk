# One: scratchpad

Known issues, plans and open questions, kept short. Something done or
answered leaves it.

## Known

- **Privacy is One's in name only.** `privacy.py`, `privacy_copy.py` and
  `privacy_public.py` are TrustCenter's Your Data, OneLegal's, and Your Data
  is in One's Help until they move into `one_legal` (ready.SHARED says so).
- **Webhooks is OneStudio's** and sits here until it moves.
- **The portal** (`portal*.py`) becomes its own module in a later plan;
  its Help page is One's until then.
- **Tours are drawn shifted in Arabic.** In a right-to-left desk every
  module's tour (OneMail's too, not only One's) highlights about the rail's
  width to the right of its mark, and a step's card can fall off the screen.
  The engine is `onedesk.tour` in `public/js/module_docs.js`; stage 9's
  Arabic looks need it fixed.
- **Deleted Document's own list and form are still reachable** by their
  address, and a row of the bin opens the form to show what the record held
  (and an administrator's Delete). The page does not draw that yet.

- **AccessCenter can't build One's roles yet**, as it can't OneAI's,
  OneLegal's or OneAccount's: its role builder (access.matrix_of) knows only
  the apps in People's list (people.APPS). Until it reads every module's
  abilities.py, nobody can be made One Manager from a screen; the demo check
  gives it directly.

## Planned

- docs/ONE.md stage 9: READY for One and OneAccount.
