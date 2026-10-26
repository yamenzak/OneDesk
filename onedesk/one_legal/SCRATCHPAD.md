# OneLegal: scratchpad

Known issues, plans and open questions, kept short. Something done or
answered leaves it.

## Known

- **Two ready modules still point at one_legal/README.md.** OneMail's and
  OneAI's `legal.py` name it in their docstrings; it is AGENTS.md now. A
  docstring is part of their fingerprint, so each changes with its next
  version rather than a version of its own for a comment.

- **The Terms still say "OneAI and Intake".** Intake is OneAI's reading
  now. Changing the Terms' words moves their hash, and so a version
  everybody is told of; it rides the next material revision rather than
  one of its own.

## Still to confirm

As the passover reaches the screens concerned:

- Encryption at rest of the platform's backups.
- How long sign-in and error records are kept.
- Inbound mail through Cloudflare Email Routing, when it is turned on.
