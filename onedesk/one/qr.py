"""A QR code as SVG, drawn on the server so neither a TV nor a page needs a
library for it: OneDisplay's QR widget, a QR block OneAI designs on a slide,
and the code a presenter's phone scans."""


def svg(link: str) -> str:
	import pyqrcode

	rows = pyqrcode.create(str(link)[:1000], error="M").code
	size = len(rows) + 2
	cells = "".join(
		f'<rect x="{x + 1}" y="{y + 1}" width="1" height="1"/>' for y, row in enumerate(rows) for x, cell in enumerate(row) if cell
	)
	return (
		f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" shape-rendering="crispEdges">'
		f'<rect width="{size}" height="{size}" fill="#fff"/><g fill="#000">{cells}</g></svg>'
	)
