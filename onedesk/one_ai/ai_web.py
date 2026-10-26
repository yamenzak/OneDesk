"""What OneAI may look up on the web (docs/AICENTER.md, Web search): the
question alone goes out, through the account, and only while the workspace
has its web search service on (legal.py). Off, the tool is not offered."""

from typing import Annotated

import frappe

from onedesk.one import account, apps
from onedesk.one_legal import services

SERVICE = "web_search"
ASKED = "onedesk.one_admin.proxy.ai_web_search"
MOST = 5


def web_search(
	question: Annotated[str, "What to look up, as a search engine would be asked: a company's name and town, a product, a general question. Never a customer's, a person's or a record's details: only this question leaves the workspace."],
) -> dict:
	"""Search the web: look up a new lead's company, check a supplier, find
	what a product costs or answer a general question. Answers each page
	found with its address, title and what it says. Say where an answer
	came from by its address."""
	apps.refuse_ai()
	said = services.call(SERVICE, account.ask, ASKED, query=question, most=MOST)
	if said is None:
		return {"pages": [], "said": frappe._("Web search is off for this workspace.")}
	return {"pages": said.get("pages") or []}


web_search.service = SERVICE


def offered(fn) -> bool:
	"""Whether a tool may be given now: one that needs a service only while
	it is on."""
	needs = getattr(fn, "service", None)
	return not needs or services.on(needs)
