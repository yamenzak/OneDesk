"""/tv-worker.js: the service worker that lets a screen start with no
network. It has to be served from the site's root to look after /tv, and
frappe serves no script from www/, so this renderer does."""

from pathlib import Path

from frappe.website.page_renderers.base_renderer import BaseRenderer
from werkzeug.wrappers import Response

PATH = "tv-worker.js"
SCRIPT = Path(__file__).parent.parent / "public" / "js" / "one_display" / "worker.js"


class Worker(BaseRenderer):
	def can_render(self):
		return self.path == PATH

	def render(self):
		return Response(
			SCRIPT.read_text(),
			content_type="application/javascript; charset=utf-8",
			headers={"Cache-Control": "no-cache"},
		)
