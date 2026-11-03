"""The workspace's search index on R2: each piece's text and vector in a
LanceDB table under its own `search/` prefix, reached with a key the account
lends for that prefix alone. AGENTS.md, index.py."""

import frappe

from onedesk.one import account

ACCESS = "one_ai_search_access"

#: Seconds before the lent key runs out that a new one is asked for.
EARLY = 5 * 60

#: Hits asked of the table per hit kept, since some go to permissions and
#: some are a second piece of the same source.
SPARE = 6

_open: dict = {}


def access() -> dict:
	"""The key to the index, as the account last lent it."""
	held = frappe.cache.get_value(ACCESS)
	if held:
		return held
	said = account.ask("onedesk.one_admin.proxy.search_access") or {}
	if not said.get("uri"):
		frappe.throw(frappe._("This workspace's search is not set up yet."))
	frappe.cache.set_value(ACCESS, said, expires_in_sec=max(int(said.get("expires_in") or 0) - EARLY, 60))
	return said


def _db():
	import lancedb

	lent = access()
	site = frappe.local.site
	held = _open.get(site)
	if held and held["key"] == lent["options"].get("aws_access_key_id"):
		return held["db"]
	db = lancedb.connect(lent["uri"], storage_options=lent["options"])
	_open[site] = {"key": lent["options"].get("aws_access_key_id"), "db": db}
	return db


def table_name(length: int) -> str:
	"""The table for vectors of one length. Pure."""
	return f"pieces_{int(length)}"


def _table(length: int, create: bool = False):
	db = _db()
	name = table_name(length)
	try:
		return db.open_table(name)
	except Exception:
		if not create:
			return None
	import pyarrow as pa

	schema = pa.schema(
		[
			("source_doctype", pa.string()),
			("source_name", pa.string()),
			("part", pa.int32()),
			("title", pa.string()),
			("text", pa.string()),
			("model", pa.string()),
			("vector", pa.list_(pa.float32(), int(length))),
		]
	)
	table = db.create_table(name, schema=schema, exist_ok=True)
	try:
		table.create_fts_index("text", replace=True)
	except Exception:
		frappe.log_error("search: words index")
	return table


def quoted(value: str) -> str:
	"""A value in a LanceDB filter, its quotes doubled. Pure."""
	return "'" + str(value).replace("'", "''") + "'"


def where(sources: list[tuple[str, str]]) -> str:
	"""A filter matching these sources. Pure."""
	return " or ".join(
		f"(source_doctype = {quoted(doctype)} and source_name = {quoted(name)})" for doctype, name in sources
	)


def put(doctype: str, name: str, rows: list[dict]) -> None:
	"""A source's pieces, in place of what it had."""
	if not rows:
		return
	table = _table(len(rows[0]["vector"]), create=True)
	table.delete(where([(doctype, name)]))
	table.add(rows)


def drop(sources: list[tuple[str, str]]) -> None:
	"""These sources' pieces gone, from every table."""
	if not sources:
		return
	db = _db()
	for name in db.table_names():
		table = db.open_table(name)
		for at in range(0, len(sources), 200):
			table.delete(where(sources[at : at + 200]))


def find(vector: list[float], text: str, doctypes: list[str] | tuple | None, most: int) -> list[dict]:
	"""The pieces nearest a question, by meaning and by its words together,
	best first: `most` times SPARE of them, for the caller to sift."""
	table = _table(len(vector))
	if table is None:
		return []
	kept = ("source_doctype", "source_name", "part", "title", "text")
	only = " or ".join(f"source_doctype = {quoted(one)}" for one in doctypes or ())
	try:
		asked = table.search(query_type="hybrid").vector(vector).text(text)
	except Exception:
		asked = table.search(vector)
	if only:
		asked = asked.where(only, prefilter=True)
	found = asked.limit(most * SPARE).to_list()
	return [
		{
			**{key: one.get(key) for key in kept},
			"score": round(float(one.get("_relevance_score") or (1 - float(one.get("_distance") or 1))), 4),
		}
		for one in found
	]


def tidy() -> None:
	"""Each night: each table's small writes folded together and its words
	index brought up to date."""
	from onedesk.one_ai import index

	if not index.on():
		return
	db = _db()
	for name in db.table_names():
		table = db.open_table(name)
		try:
			table.create_fts_index("text", replace=True)
			table.optimize()
		except Exception:
			frappe.log_error(f"search: tidying {name}")
