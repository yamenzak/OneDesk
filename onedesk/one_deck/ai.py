"""agent.py's name before P2.10, kept one release so a page loaded or a job
queued before the update still reaches `onedesk.one_deck.ai.<name>`.
Removed at P2.9 (docs/run/RUN.md, D13)."""

import sys

from onedesk.one_deck import agent

sys.modules[__name__] = agent
