"""Where the run stands (docs/run/RUN.md): each phase's count, the item in
progress, what is blocked, and the next item to take.

    python3 scripts/run.py           the summary
    python3 scripts/run.py --open    every open item, in order
"""

import re
import sys
from pathlib import Path

RUN = Path(__file__).resolve().parent.parent / "docs" / "run" / "RUN.md"
ITEM = re.compile(r"^- \[(?P<mark>.)\] (?P<id>P(?P<phase>\d+)\.\d+) (?P<text>.*)$")
DEFERRED = re.compile(r"^- \[(?P<mark>.)\] (?P<id>D\d+) (?P<text>.*?) — at (?P<at>P\d+\.\d+):")
CLOSED = {"x", "-"}
AFTER = {"P8.1": "P3", "P8.2": "P5", "P8.3": "P6", "P8.4": "P7", "P8.5": "P7", "P10.1": "P4"}
"""An item that waits for a whole phase before it may start."""


def items(text: str) -> list[dict]:
	return [match.groupdict() for match in map(ITEM.match, text.splitlines()) if match]


def closed(phase: str, all_items: list[dict]) -> bool:
	return all(one["mark"] in CLOSED for one in all_items if f"P{one['phase']}" == phase)


def may_start(one: dict, all_items: list[dict]) -> bool:
	before = AFTER.get(one["id"])
	return before is None or closed(before, all_items)


def short(one: dict) -> str:
	return f"{one['id']} {one['text'].split(' — ')[0][:110]}"


def main() -> None:
	all_items = items(RUN.read_text())
	phases: dict[str, list[dict]] = {}
	for one in all_items:
		phases.setdefault(f"P{one['phase']}", []).append(one)
	for phase, ones in phases.items():
		done = sum(one["mark"] in CLOSED for one in ones)
		print(f"{phase:>4}  {done}/{len(ones)}{'  gate passed' if done == len(ones) else ''}")
	doing = [one for one in all_items if one["mark"] == "~"]
	blocked = [one for one in all_items if one["mark"] == "!"]
	waiting = [one for one in all_items if one["mark"] == " "]
	for one in doing:
		print("doing  ", short(one))
	for one in blocked:
		print("blocked", short(one))
	ready = [one for one in waiting if may_start(one, all_items)]
	if "--open" in sys.argv:
		for one in waiting:
			print("open   ", short(one), "" if may_start(one, all_items) else f"(after {AFTER[one['id']]})")
		return
	deferred = [m.groupdict() for m in map(DEFERRED.match, RUN.read_text().splitlines()) if m and m["mark"] not in CLOSED]
	here = {one["id"] for one in doing} | ({ready[0]["id"]} if ready else set())
	for one in deferred:
		print("deferred", one["id"], "due" if one["at"] in here else f"at {one['at']}", one["text"][:90])
	if ready:
		print("next   ", short(ready[0]))
	elif not doing:
		print("nothing open: the run is finished, or everything waits on a phase")


if __name__ == "__main__":
	main()
