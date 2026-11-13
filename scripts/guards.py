"""The guards by the point of the standard they serve (docs/STANDARD.md), and
a way to run them all.

    python3 scripts/guards.py         list them by point
    python3 scripts/guards.py --run   run every guard
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.guards.registry import GUARDS, PLANNED, POINTS


def show() -> None:
	for number, point in POINTS.items():
		print(f"{number}. {point.title}")
		for guard in GUARDS:
			if guard.point == number:
				print(f"   {guard.id}: {guard.what}")
		if number in PLANNED:
			print(f"   (coming) {PLANNED[number]}")


def run() -> int:
	tests = [guard.runs for guard in GUARDS if not guard.runs.startswith("cmd: ")]
	failed = subprocess.call([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/guards", *tests], cwd=ROOT)
	for guard in GUARDS:
		if guard.runs.startswith("cmd: "):
			failed |= subprocess.call(guard.runs[5:].split(), cwd=ROOT)
	return failed


if __name__ == "__main__":
	sys.exit(run() if "--run" in sys.argv else show())
