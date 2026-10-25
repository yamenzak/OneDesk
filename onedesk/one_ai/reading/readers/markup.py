"""Walking XML by local names, whatever namespace a sender's software used.

E-invoices and bank statements come in several versions of each standard, and
each version has its own namespace URIs. What we want from them is the same
element in every version, so the paths here ignore namespaces. Pure.
"""

import xml.etree.ElementTree as ET


def root(content: bytes):
	"""The document element, or None when it is not XML. Entities are refused,
	since nothing we read needs one and a billion-laughs file is a way to stall a
	worker."""
	if b"<!ENTITY" in content[:4096]:
		return None
	try:
		return ET.fromstring(content)
	except ET.ParseError:
		return None


def local(tag) -> str:
	return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def children(element, name: str) -> list:
	if element is None:
		return []
	return [child for child in element if local(child.tag) == name]


def find(element, path: str):
	"""The first element at a slash-separated path of local names."""
	for step in path.split("/"):
		found = children(element, step)
		if not found:
			return None
		element = found[0]
	return element


def either(*elements):
	"""The first that exists. `or` cannot say it: an element with no children
	is falsy."""
	return next((one for one in elements if one is not None), None)


def find_all(element, path: str) -> list:
	*above, last = path.split("/")
	parent = find(element, "/".join(above)) if above else element
	return children(parent, last)


def text(element, path: str = "") -> str | None:
	found = find(element, path) if path else element
	if found is None or found.text is None:
		return None
	return " ".join(found.text.split()) or None


def attribute(element, path: str, name: str) -> str | None:
	found = find(element, path)
	return found.get(name) if found is not None else None
