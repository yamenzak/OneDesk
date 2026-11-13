"""agent.py's name before P2.10, kept one release so a page loaded before the
update still reaches `onedesk.account_center.ai.write_bio`. Removed at P2.9
(docs/run/RUN.md, D13)."""

import sys

from onedesk.account_center import agent

sys.modules[__name__] = agent
