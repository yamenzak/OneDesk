"""What a slide holds, made safe to keep and to show. Every save passes each
element through `cleaned`: a text element's HTML is sanitised as any HTML
from a browser is, and an address that is not a page's, a file's or ours is
dropped. README, api.py.
"""

import json

from frappe.utils.html_utils import sanitize_html

#: Addresses a picture, a video or a poster may come from.
SAFE = ("/api/method/onedesk.one_slide.api.media?id=", "/assets/", "/files/", "/private/files/", "https://", "data:image/")


def cleaned(elements) -> str:
	"""The editor's elements, as kept. Pure but for the sanitiser."""
	held = json.loads(elements or "[]") if isinstance(elements, str) else elements or []
	if not isinstance(held, list):
		return "[]"
	return json.dumps([_element(one) for one in held if isinstance(one, dict)])


def _element(one: dict) -> dict:
	if one.get("type") == "text" and isinstance(one.get("content"), str):
		one["content"] = sanitize_html(one["content"], always_sanitize=True)
	for key in ("src", "poster"):
		if isinstance(one.get(key), str) and one[key] and not one[key].startswith(SAFE):
			one[key] = ""
	return one
