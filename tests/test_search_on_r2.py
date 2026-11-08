"""Search kept on R2 (one_ai/vectors.py): the account lends each workspace a
key to its own `search/` prefix alone, the index is LanceDB's, and nothing of
Cloudflare's AI Search is left. These read the code that says so."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree  # noqa: E402

STORAGE = (tree.APP / "one_admin" / "storage.py").read_text()
PROXY = (tree.APP / "one_admin" / "proxy.py").read_text()
VECTORS = (tree.APP / "one_ai" / "vectors.py").read_text()
INDEX = (tree.APP / "one_ai" / "index.py").read_text()


def _body(source: str, name: str) -> str:
	return source.split(f"def {name}(", 1)[1].split("\ndef ", 1)[0]


def test_the_key_lent_is_for_the_workspaces_own_search_prefix_alone():
	lent = _body(STORAGE, "search_access")
	assert "keys.prefix(tenant.name) + SEARCH" in lent and '"prefix": prefix' in lent and "/search-credentials" in lent
	keeper = (tree.ROOT / "deploy" / "keeper" / "worker.js").read_text()
	assert "const SEARCH = /^tenants\\/[a-z0-9][a-z0-9-]{0,62}\\/search\\/$/;" in keeper, "the keeper lends a search prefix and nothing else"
	assert 'permission: "object-read-write", prefixes: [prefix]' in keeper and "JSON.parse(env.TENANT_BUCKETS).includes(bucket)" in keeper
	assert '"cf-r2-jurisdiction": "eu"' in keeper, "an EU workspace's index stays in the EU bucket"
	assert "storage.search_access(caller())" in _body(PROXY, "search_access"), "for the workspace that asks, by its own key"


def test_ai_search_is_gone():
	assert "def ai_search(" not in PROXY and "def ai_search_state(" not in PROXY
	assert not (tree.APP / "one_admin" / "search.py").exists() and not (tree.APP / "one_ai" / "search.py").exists()
	assert '"AI Search*"' not in (tree.APP / "one_admin" / "setup.py").read_text()


def test_the_index_holds_the_text_and_vectors_and_mariadb_only_which():
	chunk = (tree.APP / "one_ai" / "doctype" / "ai_chunk" / "ai_chunk.json").read_text()
	assert '"vector"' not in chunk and '"fieldname": "text"' not in chunk
	assert "vectors.put_many(" in _body(INDEX, "remember_many") and "vectors.find(" in _body(INDEX, "nearest")
	assert "vectors.drop(" in _body(INDEX, "forget_all")
	assert 'query_type="hybrid"' in _body(VECTORS, "find"), "by meaning and by words together"


def test_the_index_is_tidied_each_night():
	assert '"onedesk.one_ai.vectors.tidy"' in (tree.APP / "hooks.py").read_text()
	tidy = _body(VECTORS, "tidy")
	assert "optimize()" in tidy and "create_fts_index" in tidy


def test_a_save_marks_its_record_and_one_job_indexes_them_all():
	"""An import of thousands queues one job, not one a record, and each round
	is one embedding call and one write to R2."""
	marked = _body(INDEX, "changed")
	assert "frappe.cache.sadd(DIRTY" in marked and '"onedesk.one_ai.index.flush"' in marked
	assert 'job_id="one_index_flush"' in marked and "deduplicate=True" in marked
	flushed = _body(INDEX, "flush")
	assert "range(FLUSHED)" in flushed and "remember_many(" in flushed
	assert "done = flush()" in _body(INDEX, "catch_up"), "what was marked while a flush finished is caught up"
