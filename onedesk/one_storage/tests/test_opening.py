"""How an office file opens in OneCloud and what Edit offers on it
(one_storage/opening.py)."""

import json

from onedesk.one_storage import opening


def test_excel_csv_and_word_files_edit_in_the_native_editors():
	assert opening.way("Budget.xlsx") == {"edit": "workbook", "make": None, "copy": None}
	assert opening.way("Prices.CSV")["edit"] == "workbook"
	assert opening.way("Handover.docx")["edit"] == "document"


def test_a_powerpoint_file_makes_a_presentation_and_is_never_edited():
	assert opening.way("Pitch.pptx") == {"edit": None, "make": "presentation", "copy": None}


def test_macro_files_and_an_older_excel_file_are_copied_into_one():
	for name, kind in (("Model.xlsm", "workbook"), ("Old.xls", "workbook"), ("Letter.docm", "document")):
		assert opening.way(name) == {"edit": None, "make": None, "copy": kind}, name


def test_opendocument_and_older_word_files_offer_only_oneos():
	for name in ("Notes.odt", "Sheet.ods", "Talk.odp", "Old.doc", "Old.ppt", "picture.png", "README"):
		assert opening.way(name) is None, name


def test_what_was_found_counts_only_for_the_version_it_was_read_from():
	item = {"file_name": "Budget.xlsx", "content_hash": "abc", "one_fidelity": json.dumps(["comments"]), "one_fidelity_of": "abc"}
	assert opening.kept(item) == ["comments"]
	assert opening.kept({**item, "content_hash": "def"}) is None
	assert opening.kept({**item, "one_fidelity_of": None}) is None


def test_a_file_no_editor_reads_has_nothing_to_find():
	assert opening.kept({"file_name": "Data.csv"}) == []


def test_a_row_says_what_edit_offers_and_what_is_known_to_be_dropped():
	fresh = {"file_name": "Budget.xlsx", "content_hash": "abc"}
	assert opening.row(fresh) == {"edit": "workbook", "make": None, "copy": None}
	read = {**fresh, "one_fidelity": "[]", "one_fidelity_of": "abc"}
	assert opening.row(read)["loses"] == []
	assert opening.row({"file_name": "Pitch.pptx"})["loses"] == []
	assert opening.row({"file_name": "Folder", "is_folder": 1}) is None
