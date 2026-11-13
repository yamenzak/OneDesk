"""The synced records whose label is an app's name, which scripts/docs.py
writes from the registry and `--check` holds to it, so a rename in a manifest
renames them too. An app's Sidebar (its manifest's `sidebar`) is titled with
its name; the rest are named in NAMED by their file under onedesk/, the field,
the row of `items` that holds it when it is not the record's own, and the
words around the name as `{0}`. Pure."""

import json
from pathlib import Path
from typing import NamedTuple

from onedesk.one import registry


class Named(NamedTuple):
	file: str
	field: str
	app: str
	words: str = "{0}"
	row: tuple[str, str] | None = None


NAMED = (
	Named("one_admin/page/oneadmin/oneadmin.json", "title", "one_admin"),
	Named("one/page/one_hub/one_hub.json", "title", "one_hub"),
	Named("one_book/page/books/books.json", "title", "one_book"),
	Named("one_calendar/page/onecalendar/onecalendar.json", "title", "one_calendar"),
	Named("one_chat/page/onechat/onechat.json", "title", "one_chat"),
	Named("one_cloud/page/onecloud/onecloud.json", "title", "one_cloud"),
	Named("one_crm/page/onecrm/onecrm.json", "title", "one_crm"),
	Named("one_deck/page/presentation/presentation.json", "title", "one_deck"),
	Named("one_doc/page/document/document.json", "title", "one_doc"),
	Named("one_factory/page/onefactory/onefactory.json", "title", "one_factory"),
	Named("one_hr/page/onehr/onehr.json", "title", "one_hr"),
	Named("one_inventory/page/inventory/inventory.json", "title", "one_inventory"),
	Named("one_mail/page/onemail/onemail.json", "title", "one_mail"),
	Named("one_quality/page/onequality/onequality.json", "title", "one_quality"),
	Named("one_sheet/page/workbook/workbook.json", "title", "one_sheet"),
	Named("one_admin/workspace/one_admin/one_admin.json", "title", "one_admin"),
	Named("one_hr/workspace/onehr_setup/onehr_setup.json", "title", "one_hr", "{0} Setup"),
	Named("one/sidebar/one/one.json", "label", "one_hub", row=("link_to", "one-hub")),
	Named("one/sidebar/one/one.json", "label", "account_center", row=("url", "/desk/one?center=account")),
	Named("one/sidebar/one/one.json", "label", "trust_center", row=("url", "/desk/one?center=trust")),
	Named("one_admin/sidebar/one_admin/one_admin.json", "label", "one_ai", row=("icon", "oneai")),
)


def named(root: Path) -> tuple[Named, ...]:
	"""Every label the registry writes: each app's Sidebar title, then NAMED."""
	found = []
	for app in registry.apps():
		if not app.sidebar:
			continue
		for path in sorted((root / app.id / "sidebar").glob("*/*.json")):
			if json.loads(path.read_text(encoding="utf-8")).get("name") == app.sidebar:
				found.append(Named(str(path.relative_to(root)), "title", app.id))
	return (*found, *NAMED)


def holder(record: dict, one: Named) -> dict:
	"""The dict in a record that holds a label: the record, or its row."""
	if not one.row:
		return record
	key, value = one.row
	rows = [row for row in record.get("items") or [] if row.get(key) == value]
	if len(rows) != 1:
		raise ValueError(f"{one.file}: {len(rows)} rows have {key} {value!r}, not one")
	return rows[0]


def wanted(one: Named) -> str:
	return one.words.format(registry.name(one.app))
