"""Web search through Cloudflare's AI Gateway (docs/AICENTER.md, Web search):
the question alone, to one provider, billed to the workspace at the
provider's list price. Whether a workspace may ask is its own optional
service (one_ai/trust.py, web_search); the account only searches."""

import requests

from onedesk.one_admin import faults, gateway, ledger
from onedesk.one_admin.faults import Refused

API = "https://api.cloudflare.com/client/v4/accounts/{account}/ai/websearch"

# Exa, at its list price for a search of up to ten results, in dollars.
PROVIDER = "exa"
PRICE = 7 / 1000

MOST = 10
LONGEST = 1024
TIMEOUT = 30


def body(query: str, most: int, gateway_id: str) -> dict:
	"""What the gateway is asked. Pure."""
	return {
		"query": " ".join((query or "").split())[:LONGEST],
		"provider": PROVIDER,
		"limit": max(1, min(int(most or 5), MOST)),
		"options": {"gateway": {"id": gateway_id}},
	}


def found(answer: dict) -> list[dict]:
	"""The pages the provider found: their address, title and what it says
	of them. Pure."""
	out = []
	for one in (answer or {}).get("items") or []:
		if one.get("url"):
			out.append({"url": one["url"], "title": one.get("title") or "", "about": one.get("description") or ""})
	return out


def find(tenant: str, query: str, most: int = 5) -> dict:
	"""One web search, billed to the workspace at the provider's price."""
	if not " ".join((query or "").split()):
		raise Refused("Say what to search the web for")
	money = gateway._money()
	credits = PRICE * money["markup"] * money["per_dollar"]
	holding = ledger.reserve(tenant, credits, why=f"web-search:{PROVIDER}", reference="web", action="web_search")
	settings = gateway._settings()
	try:
		answer = requests.post(
			API.format(account=settings["account"]),
			headers={
				"Authorization": f"Bearer {settings['token']}",
				gateway.GATEWAY: settings["gateway"],
				"Content-Type": "application/json",
			},
			json=body(query, most, settings["gateway"]),
			timeout=TIMEOUT,
		)
		if answer.status_code != 200:
			raise faults.raised(f"web-search:{PROVIDER}", answer.status_code, answer.text[: faults.KEPT])
		pages = found(answer.json())
	except Exception:
		ledger.release(holding)
		raise
	ledger.commit(holding, credits, PRICE, model=f"web-search:{PROVIDER}")
	return {"pages": pages, "credits": credits}
