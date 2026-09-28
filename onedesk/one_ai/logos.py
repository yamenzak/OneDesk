"""The logos of the companies that make OneAI's models, served from here.

Fetched once from Google's favicon service (v2, `makers.logo`) and kept in
the cache, so a page listing models does not send each viewer's browser to
Google, and still draws when Google is slow. Only the makers `makers.py`
knows are served: this is not a way to fetch any site's icon.
"""

import base64

import frappe
import requests

from onedesk.one_admin import makers

#: How long a logo is kept. Makers do not change their marks often.
KEEP = 30 * 24 * 3600


def url(domain: str | None) -> str:
	"""Where a page loads a maker's logo from."""
	return f"/api/method/onedesk.one_ai.logos.logo?domain={domain}" if domain else ""


def known() -> set[str]:
	return {domain for _name, domain in [*makers.MAKERS.values(), *makers.BY_PROVIDER.values()] if domain}


@frappe.whitelist()
def logo(domain: str):
	"""A maker's logo as a PNG, cached; a 404 for a domain that is not one."""
	if domain not in known():
		raise frappe.DoesNotExistError
	key = f"one_ai_logo:{domain}"
	held = frappe.cache.get_value(key)
	if not held:
		try:
			got = requests.get(makers.logo(domain), timeout=10)
			got.raise_for_status()
		except requests.RequestException:
			raise frappe.DoesNotExistError from None
		held = base64.b64encode(got.content).decode()
		frappe.cache.set_value(key, held, expires_in_sec=KEEP)
	frappe.local.response.update(
		{
			"type": "binary",
			"filename": f"{domain}.png",
			"filecontent": base64.b64decode(held),
			"display_content_as": "inline",
		}
	)
