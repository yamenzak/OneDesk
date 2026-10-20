# Derived from frappe/suite@df7f341 (suite/sheets/doctype/sheet/storage.py). Copyright (c) Frappe Technologies Pvt. Ltd. AGPL-3.0.
"""A workbook at rest: its JSON gzipped and base64'd in an envelope,
{"_z": "gzip", "data": "..."}, five to ten times smaller. Plain JSON reads
too. Unpacking stops at MAX_SHEETS_DATA_BYTES, so a small envelope can't
expand into a large allocation.
"""

import base64
import binascii
import gzip
import io
import json

MAX_SHEETS_DATA_BYTES = 75 * 1024 * 1024

_GZ_MARKER, _GZ_KIND, _DATA_KEY = "_z", "gzip", "data"


def encode_sheets_data(json_str: str) -> str:
	payload = base64.b64encode(gzip.compress((json_str or "{}").encode("utf-8"), compresslevel=6)).decode("ascii")
	return json.dumps({_GZ_MARKER: _GZ_KIND, _DATA_KEY: payload})


def decode_sheets_data(stored: str | None) -> str:
	if not stored:
		return "{}"
	envelope = _try_parse_envelope(stored)
	if envelope is None:
		return stored
	return _bounded_decompress(envelope[_DATA_KEY]).decode("utf-8")


def _bounded_decompress(b64_payload: str) -> bytes:
	if not isinstance(b64_payload, str) or len(b64_payload) > MAX_SHEETS_DATA_BYTES * 2:
		_throw_bomb()
	try:
		compressed = base64.b64decode(b64_payload, validate=True)
	except (binascii.Error, ValueError):
		_throw_bomb(unreadable=True)
	if len(compressed) > MAX_SHEETS_DATA_BYTES:
		_throw_bomb()
	try:
		with gzip.GzipFile(fileobj=io.BytesIO(compressed), mode="rb") as gz:
			out = gz.read(MAX_SHEETS_DATA_BYTES)
			if gz.read(1):
				_throw_bomb()
	except (OSError, EOFError):
		_throw_bomb(unreadable=True)
	return out


def _throw_bomb(unreadable: bool = False) -> None:
	import frappe

	if unreadable:
		frappe.throw(frappe._("This workbook's saved content doesn't read."))
	frappe.throw(
		frappe._(
			"This workbook is too large to save (over {0} MB). Formatting across a very large range is the usual cause: clear what you don't need, or split it across sheets."
		).format(MAX_SHEETS_DATA_BYTES // (1024 * 1024))
	)


def _try_parse_envelope(stored: str) -> dict | None:
	try:
		found = json.loads(stored)
	except (ValueError, TypeError):
		return None
	if isinstance(found, dict) and found.get(_GZ_MARKER) == _GZ_KIND and isinstance(found.get(_DATA_KEY), str):
		return found
	return None
