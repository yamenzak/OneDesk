"""Files a browser can't open, turned into PDFs in One's office containers
(deploy/office/README.md), for a workspace and billed to it by the seconds
the container worked and the idle minutes it then keeps running."""

import math
import time

import frappe
import requests
from frappe import _

from onedesk.one_admin import ledger, price_list, site, vault
from onedesk.one_admin.faults import Refused

#: standard-1 (half a vCPU, 4 GiB, 8 GB) per second, in dollars: memory and
#: disk for every second it runs, CPU while it works.
RUNNING = 4 * 0.0000025 + 8 * 0.00000007
WORKING = 0.5 * 0.00002
#: An instance sleeps this long after its last request.
IDLE_AFTER = 5 * 60
WAIT = 150
MOST_BYTES = 50 * 1024 * 1024
HOLD = 5
LEAST = 1


def cost(seconds: float) -> float:
	"""What one conversion costs us at most, in dollars: its seconds of
	work and the idle minutes after it. Pure."""
	return seconds * (RUNNING + WORKING) + IDLE_AFTER * RUNNING


def credits(seconds: float, markup: float, per_dollar: float) -> int:
	"""A conversion's price: its cost, marked up, in whole credits, at least
	one. Pure."""
	return max(LEAST, math.ceil(cost(seconds) * (markup or 1) * (per_dollar or 0)))


def _where() -> tuple[str, str]:
	settings = frappe.get_cached_doc("One Admin Settings")
	url = (settings.office_url or "").rstrip("/")
	secret = vault.get("office_secret") if url else None
	if not url or not secret:
		raise Refused("the office containers are not set up")
	return url, secret


def convert(tenant: str, name: str, content: bytes, reference: str | None = None) -> dict:
	"""A file as a PDF, billed to the workspace: the bytes and what it cost."""
	site.require_admin()
	if len(content) > MOST_BYTES:
		raise Refused(f"{name} is over {MOST_BYTES // 1024 // 1024} MB")
	url, secret = _where()
	holding = ledger.reserve(tenant, HOLD, why="office", reference=reference or name, action="office_convert")
	began = time.monotonic()
	try:
		answered = requests.post(
			f"{url}/forms/libreoffice/convert",
			headers={"x-one-secret": secret},
			files={"files": (name, content)},
			timeout=WAIT,
		)
	except requests.RequestException as failed:
		ledger.release(holding)
		raise Refused(f"the office containers did not answer: {failed}") from failed
	seconds = time.monotonic() - began
	if answered.status_code == 503:
		ledger.release(holding)
		raise Refused("the office containers are starting")
	if not answered.ok or not answered.content.startswith(b"%PDF"):
		ledger.release(holding)
		raise Refused(f"the office containers could not convert {name}: {answered.status_code}")
	charged = credits(seconds, price_list.MARKUP["office"], price_list.credits_per_dollar())
	ledger.commit(holding, charged, cost(seconds), model="office/standard-1")
	return {"data": answered.content, "credits": charged, "seconds": round(seconds, 1)}


def starting(raised: Exception) -> bool:
	return "starting" in str(raised)


def said(raised: Exception) -> str:
	"""What a workspace is told when a conversion is refused."""
	if starting(raised):
		return _("The office containers are starting. Try again in a few minutes.")
	return _("This file could not be converted.")
