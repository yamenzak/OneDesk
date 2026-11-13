"""Each upstream scheduled job One stops (Scheduled Job Type.stopped) is still
in its app's scheduler_events. A job is stopped by its method's dotted path, so
one renamed upstream would be missed: the stop finds nothing and theirs runs
beside ours."""

import ast
from pathlib import Path

import pytest
from tests.bench import APPS

ROOT = Path(__file__).resolve().parents[2]

STOPS = (
	("onedesk/one_calendar/tell.py", "FRAPPE_DIGEST"),
	("onedesk/one_project/board.py", "OVERDUE_JOB"),
	("onedesk/one_crm/stages.py", "REOPENER"),
	("onedesk/one_project/updates.py", "REPLACED"),
)


def _stopped() -> list[str]:
	found = []
	for path, name in STOPS:
		for node in ast.parse((ROOT / path).read_text()).body:
			if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == name:
				value = ast.literal_eval(node.value)
				found += [value] if isinstance(value, str) else list(value)
	return found


def test_every_job_we_stop_is_still_scheduled_upstream():
	if not (APPS / "erpnext").exists():
		pytest.skip("erpnext is not checked out beside this app")
	assert len(_stopped()) >= len(STOPS), "a stop's constant moved; update STOPS"
	gone = unscheduled(_stopped(), lambda app: (APPS / app / app / "hooks.py").read_text())
	assert not gone, f"no longer in its app's scheduler_events: {gone}"


def unscheduled(stopped: list[str], hooks) -> list[str]:
	"""The stopped jobs their app's hooks (`hooks(app)`) no longer name. Pure but for `hooks`."""
	return [method for method in stopped if f'"{method}"' not in hooks(method.split(".")[0])]


def test_the_stopped_job_rule_catches_its_example():
	hooks = {"erpnext": 'scheduler_events = {"daily": ["erpnext.crm.utils.open_leads"]}'}
	assert unscheduled(["erpnext.crm.utils.open_leads", "erpnext.crm.utils.renamed"], hooks.get) == ["erpnext.crm.utils.renamed"]
