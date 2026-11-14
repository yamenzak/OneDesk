"""Files a browser can't open, turned into PDFs in One's office containers
(deploy/office/README.md), for a workspace and billed to it by the seconds
the container worked and the idle minutes it then keeps running. The same
Worker checks a mail's attachment (`inspect`, free: no container runs) and
opens a mail's link in a throwaway browser (`look`, billed by its seconds)."""

import math
import time
from urllib.parse import quote

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
#: Browser Rendering, per second of a browser open, in dollars.
BROWSING = 0.09 / 3600
MOST_CHECKED = 25 * 1024 * 1024
LOOK_WAIT = 45
CHECK_WAIT = 60


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


def look_credits(seconds: float, markup: float, per_dollar: float) -> int:
	"""A link's look: its browser's seconds, marked up, in whole credits, at
	least one. Pure."""
	return max(LEAST, math.ceil(seconds * BROWSING * (markup or 1) * (per_dollar or 0)))


def look(tenant: str, url: str) -> dict:
	"""A link opened in a throwaway browser, billed to the workspace: where
	it ended, the redirects on the way, whether it asks for a password, a
	picture of it, and what it cost."""
	site.require_admin()
	where, secret = _where()
	holding = ledger.reserve(tenant, HOLD, why="guard", reference=url[:140], action="guard_link")
	began = time.monotonic()
	try:
		answered = requests.post(f"{where}/guard/link", headers={"x-one-secret": secret}, json={"url": url}, timeout=LOOK_WAIT)
	except requests.RequestException as failed:
		ledger.release(holding)
		raise Refused(f"the link could not be opened: {failed}") from failed
	seconds = time.monotonic() - began
	if not answered.ok:
		ledger.release(holding)
		raise Refused(f"the link could not be opened: {answered.status_code}")
	charged = look_credits(seconds, price_list.MARKUP["guard"], price_list.credits_per_dollar())
	ledger.commit(holding, charged, seconds * BROWSING, model="guard/browser")
	return {**answered.json(), "credits": charged}


def inspect(name: str, content: bytes, programs: list[str]) -> dict:
	"""What an attachment is, read from its bytes: archives unpacked within
	limits, a program inside named, macros found. Nothing is kept."""
	site.require_admin()
	if len(content) > MOST_CHECKED:
		raise Refused(f"{name} is over {MOST_CHECKED // 1024 // 1024} MB")
	where, secret = _where()
	headers = {"x-one-secret": secret, "x-one-name": quote(name), "x-one-programs": ",".join(programs), "content-type": "application/octet-stream"}
	try:
		answered = requests.post(f"{where}/guard/file", headers=headers, data=content, timeout=CHECK_WAIT)
	except requests.RequestException as failed:
		raise Refused(f"the file could not be checked: {failed}") from failed
	if not answered.ok:
		raise Refused(f"the file could not be checked: {answered.status_code}")
	return answered.json()


def starting(raised: Exception) -> bool:
	return "starting" in str(raised)


def said(raised: Exception) -> str:
	"""What a workspace is told when a conversion is refused."""
	if starting(raised):
		return _("The office containers are starting. Try again in a few minutes.")
	return _("This file could not be converted.")
