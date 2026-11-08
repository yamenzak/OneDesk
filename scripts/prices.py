"""Every price One sells and what is left of it at worst, from the code
(one_admin/price_list.py and costs.py), with each cost line and anything that
loses money.

    python3 scripts/prices.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from onedesk.one_admin import margins  # noqa: E402

if __name__ == "__main__":
	print(margins.table())
	sys.exit(1 if margins.findings() else 0)
