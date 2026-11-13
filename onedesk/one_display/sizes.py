"""The shapes a screen comes in. A channel and a widget collection each name
one, or Custom with any width and height, and the layout is drawn on that
frame in pixels; a screen of another size scales the frame to fit (tv.js).
The editor works on the same frame at half its pixels, so a landscape
screen is OneDeck's own 960 by 540."""

from frappe.utils import cint

SIZES = {
	"Landscape": (1920, 1080),
	"Portrait": (1080, 1920),
	"Bar": (1920, 540),
	"Square": (1080, 1080),
	"Wall": (3840, 1080),
}
SMALLEST = 240
LARGEST = 7680


def pixels(doc) -> tuple[int, int]:
	"""A channel's or collection's frame in pixels. Pure."""
	size = doc.get("screen_size") or "Landscape"
	if size in SIZES:
		return SIZES[size]
	wide, high = cint(doc.get("width")) or 1920, cint(doc.get("height")) or 1080
	return min(max(wide, SMALLEST), LARGEST), min(max(high, SMALLEST), LARGEST)


def settle(doc) -> None:
	"""validate: a named size writes its width and height; Custom keeps them in bounds."""
	doc.width, doc.height = pixels(doc)


def editor(doc) -> tuple[int, int]:
	"""The editor's frame, at half the pixels. Pure."""
	wide, high = pixels(doc)
	return round(wide / 2), round(high / 2)
