"""Frappe Cloud, called rather than copied.

We are a press *customer* and not its operator. Its whitelisted HTTP API is the
whole boundary: no server, no agent daemon, no SSH, nothing that assumes we are
inside their infrastructure.

**Nothing here is stored.** There is no `Press Server`, no `Press Bench Group`
and no `Press Site` table, because a table of somebody else's state is wrong
between syncs and the way you find out is a customer who cannot be placed on a
bench that exists. What the operator's screens need — which benches exist, which
clusters a bench can reach, what a site plan costs — is asked for and held in
redis for a minute, so the answer is press's and the cost is one call a minute
rather than one a page.

**Failures are classified, because the retry decision depends on it.** A 503 is
worth another attempt in two minutes and a 400 will fail identically forever.
That decision lives in `faults.py`, which imports nothing of Frappe and is
therefore read back by a test rather than by a site.
"""

import json

import frappe
import requests

from onedesk.one_admin import faults, site
from onedesk.one_admin.faults import Again, Refused

#: A write can take a while — press does real work inside the request. A read
#: that has not answered in ten seconds is a read we should not be blocking a
#: page on.
TIMEOUT = 60
READ_TIMEOUT = 10

#: How long a catalogue answer is good for. Long enough that a screen redraw is
#: free, short enough that a bench added this morning is offerable by lunch.
CACHED_FOR = 60


def call(endpoint: str, timeout: int = TIMEOUT, **params):
	"""Invoke one whitelisted press method and return its `message`.

	The first argument is `endpoint` rather than `method` on purpose:
	`press.api.client.run_doc_method` takes a parameter of its own called
	`method`, and a matching name here would raise `TypeError` before the call
	ever left the process.
	"""
	site.require_admin()
	settings = _settings()
	url = f"{settings['url'].rstrip('/')}/api/method/{endpoint}"

	try:
		answer = requests.post(
			url,
			headers={
				"Authorization": f"token {settings['token']}",
				"Content-Type": "application/json",
				"X-Press-Team": settings["team"],
			},
			data=json.dumps(params),
			timeout=timeout,
		)
	except requests.Timeout as raised:
		raise Again(f"{endpoint} timed out") from raised
	except requests.RequestException as raised:
		raise Again(f"{endpoint} could not be reached: {raised}") from raised

	return _answered(endpoint, answer)


def _answered(endpoint: str, answer):
	if answer.status_code == 200:
		try:
			return answer.json().get("message")
		except ValueError as raised:
			raise Refused(
				f"{endpoint} answered 200 with something that is not JSON",
				answer.status_code,
				answer.text[: faults.KEPT],
			) from raised

	raise faults.raised(endpoint, answer.status_code, _detail(answer))


def _detail(answer) -> str:
	try:
		body = answer.json()
	except ValueError:
		body = None
	return faults.detail(body, answer.text)


def _settings() -> dict:
	"""Where to call and as whom.

	`site_config` wins over the doctype so a developer can point a laptop at a
	staging press without editing a record that a migrate would then ship.
	"""
	stored = frappe.get_cached_doc("One Admin Settings")
	found = {
		"url": frappe.conf.get("press_url") or stored.press_url,
		"team": frappe.conf.get("press_team") or stored.press_team,
		"token": frappe.conf.get("press_token") or stored.get_password("press_token", raise_exception=False),
	}
	missing = [key for key, value in found.items() if not value]
	if missing:
		raise Refused(
			f"Frappe Cloud is not configured: {', '.join(sorted(missing))}. "
			"Set it in One Admin Settings."
		)
	return found


def benches() -> list[dict]:
	"""Every bench group this team owns."""
	return _catalogue("benches", "press.api.bench.all") or []


def clusters(bench: str) -> list[dict]:
	"""Where a site on this bench may be placed.

	This is the list a customer chooses from when they are asked where their
	workspace should live — and it is press's answer rather than a table we keep,
	which is the whole point. A cluster press added is offerable within the
	minute; a cluster press retired stops being offered in the same minute.
	"""
	return _catalogue(f"clusters:{bench}", "press.api.bench.regions", name=bench) or []


def plans() -> list[dict]:
	"""What press charges us per site. Never what we charge a customer."""
	return _catalogue("plans", "press.api.site.get_plans") or []


def _catalogue(key: str, endpoint: str, **params):
	cache = frappe.cache()
	full = f"one:press:{key}"
	held = cache.get_value(full)
	if held is not None:
		return held
	answered = call(endpoint, timeout=READ_TIMEOUT, **params)
	cache.set_value(full, answered, expires_in_sec=CACHED_FOR)
	return answered


def forget() -> None:
	"""Drop every cached catalogue answer.

	For the operator who has just added a bench and does not want to wait a
	minute to see it, and for tests.
	"""
	frappe.cache().delete_keys("one:press:")
