"""Search on Cloudflare's AI Search, one instance per workspace, reading the
workspace's own `search/` prefix in R2 (docs/AICENTER.md, Search). No
instance is made here: one is made by hand and recorded with `adopt`, and
until then a workspace is told it has none and searches as it did."""

import json
import re

import frappe
import requests

from onedesk.one_admin import faults, gateway, ledger
from onedesk.one_admin.faults import Refused

# Which workspace searches which instance: {tenant: instance}.
HELD = "one_ai_search_instances"

API = "https://api.cloudflare.com/client/v4/accounts/{account}/ai-search/namespaces/default/instances/{instance}/search"

# What one search costs at Cloudflare, in dollars: keyword as you type, and
# meaning (vectors with keywords, reranked) when asked.
PRICE = {"keyword": 0.10 / 1000, "meaning": 0.75 / 1000}
RETRIEVAL = {"keyword": "keyword", "meaning": "hybrid"}

MOST = 50
TIMEOUT = 20


class NoSearch(frappe.ValidationError):
	"""The workspace has no instance yet, so it searches as it did; its name
	reaches the workspace as the refusal's kind (one_ai/search.py)."""


def name_for(tenant: str) -> str:
	"""The instance a workspace's would be called. Pure."""
	return "one-" + re.sub(r"[^a-z0-9-]+", "-", tenant.lower()).strip("-")[:50]


def instances() -> dict:
	try:
		return json.loads(frappe.db.get_default(HELD) or "{}")
	except ValueError:
		return {}


def instance_of(tenant: str) -> str | None:
	return instances().get(tenant)


def adopt(tenant: str, instance: str | None = None) -> str:
	"""Record that a workspace's instance exists, made by hand: from now on
	the workspace searches it."""
	held = instances()
	held[tenant] = instance or name_for(tenant)
	frappe.db.set_default(HELD, json.dumps(held, sort_keys=True))
	return held[tenant]


def body(query: str, mode: str, most: int) -> dict:
	"""What AI Search is asked. Pure."""
	return {
		"query": query,
		"ai_search_options": {
			"retrieval": {
				"retrieval_type": RETRIEVAL[mode],
				"max_num_results": max(1, min(int(most or 10), MOST)),
				"keyword_match_mode": "or",
			},
			"reranking": {"enabled": mode == "meaning"},
		},
	}


def found(answer: dict) -> list[dict]:
	"""AI Search's chunks as hits: the object's key, its text and score. Pure."""
	out = []
	for one in ((answer or {}).get("result") or {}).get("chunks") or []:
		item = one.get("item") or {}
		if item.get("key"):
			out.append({"key": item["key"], "text": one.get("text") or "", "score": float(one.get("score") or 0)})
	return out


def find(tenant: str, query: str, mode: str = "keyword", most: int = 10) -> dict:
	"""One search of a workspace's instance, billed to it at Cloudflare's price."""
	if mode not in PRICE:
		raise Refused(f"{mode} is not a way to search")
	instance = instance_of(tenant)
	if not instance:
		raise NoSearch("This workspace has no search instance yet.")
	money = gateway._money()
	credits = PRICE[mode] * money["markup"] * money["per_dollar"]
	holding = ledger.reserve(tenant, max(credits, gateway._LEAST), why=f"ai-search:{mode}", reference="search", action="search")
	settings = gateway._settings()
	try:
		answer = requests.post(
			API.format(account=settings["account"], instance=instance),
			headers={"Authorization": f"Bearer {settings['token']}", "Content-Type": "application/json"},
			json=body(query, mode, most),
			timeout=TIMEOUT,
		)
		if answer.status_code != 200:
			raise faults.raised(f"ai-search:{instance}", answer.status_code, answer.text[: faults.KEPT])
		hits = found(answer.json())
	except Exception:
		ledger.release(holding)
		raise
	ledger.commit(holding, credits, PRICE[mode], model=f"ai-search:{mode}")
	return {"hits": hits, "credits": credits}
