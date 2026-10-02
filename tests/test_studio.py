"""OneStudio's extensions (one_studio/): code only OneAI writes, which an
administrator turns on and off but never reads. guard.py is pure and is run
here; the rest is read for what it promises."""

import importlib.util
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import pytest
import tree

STUDIO = tree.APP / "one_studio"
HOOKS = (tree.APP / "hooks.py").read_text()


def _guard():
	spec = importlib.util.spec_from_file_location("studio_guard", STUDIO / "guard.py")
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


guard = _guard()
SITE = guard.Site(
	kinds={"Customer", "Lead"},
	unseen={"Customer": {"credit_score"}},
	doctypes={"Customer", "Lead", "Salary Slip", "User"},
)


def test_a_plain_rule_on_the_record_is_let_through():
	code = 'if not doc.mobile_no:\n\tfrappe.throw(_("A customer needs a mobile number."))'
	assert guard.on_server(code, "Customer", SITE) == {"Customer"}
	lead = 'name = frappe.db.get_value("Lead", doc.lead_name, "lead_name")'
	assert guard.on_server(lead, "Customer", SITE) == {"Customer", "Lead"}


@pytest.mark.parametrize(
	"code",
	[
		"import os",
		'frappe.db.sql("select 1")',
		'frappe.get_all("Customer")',
		'doc.db_set("status", "x")',
		'frappe.db.set_value("Customer", doc.name, "x", 1)',
		"doc.save(ignore_permissions=True)",
		"frappe.flags.in_import = True",
		'frappe.sendmail(recipients=["a@b.c"])',
		'frappe.make_post_request("https://example.com")',
		'frappe.get_doc("Salary Slip", "x")',
		"frappe.get_doc(kind, name)",
		"x = doc.credit_score",
		'frappe.set_user("Administrator")',
		"doc.__class__",
		'getattr(doc, "x")',
	],
)
def test_what_reaches_past_the_administrator_is_refused_on_the_server(code):
	with pytest.raises(guard.Refused):
		guard.on_server(code, "Customer", SITE)


@pytest.mark.parametrize(
	"code",
	[
		'frappe.call({method: "x"})',
		'frappe.xcall("x")',
		'frappe.db.get_value("Customer", "x", "y")',
		'fetch("https://example.com")',
		"document.cookie",
		'localStorage.setItem("a", 1)',
		'frm.fields_dict.x.$wrapper.html("<b>x</b>")',
		'el.innerHTML = "x"',
		'eval("1")',
		'frm.set_value("credit_score", 1)',
		'frappe.set_route("Form", "Salary Slip", "x")',
	],
)
def test_a_screen_extension_only_changes_the_form_and_speaks(code):
	with pytest.raises(guard.Refused):
		guard.on_screen(code, "Customer", SITE)


def test_a_screen_extension_that_changes_the_form_is_let_through():
	code = 'frappe.ui.form.on("Customer", { refresh(frm) { frm.set_df_property("website", "hidden", 1); } });'
	assert guard.on_screen(code, "Customer", SITE) == {"Customer"}


def test_a_server_extension_runs_wrapped_and_its_name_cannot_break_out():
	wrapped = guard.wrapped('x"); frappe.db.commit(); ("', "frappe.throw('no')")
	assert wrapped.splitlines()[1] == "try:"
	assert "except frappe.ValidationError:\n\traise" in wrapped
	assert repr(guard.TITLE + 'x"); frappe.db.commit(); ("') in wrapped
	assert "\tfrappe.throw('no')" in wrapped


def test_only_record_events_and_the_two_views():
	assert "Before Save" in guard.EVENTS and "After Submit" in guard.EVENTS
	for never in ("API", "Scheduler Event", "Permission Query", "Before Print"):
		assert never not in guard.EVENTS
	assert guard.VIEWS == ("Form", "List")


def test_the_code_is_above_the_administrators_level_and_nobody_creates_one_by_hand():
	spec = json.loads((STUDIO / "doctype" / "extension" / "extension.json").read_text())
	fields = {f["fieldname"]: f for f in spec["fields"]}
	assert fields["code"]["permlevel"] == 1 and fields["reviewed"]["permlevel"] == 1
	theirs = [p for p in spec["permissions"] if p["role"] == "Workspace Administrator"]
	assert theirs and not any(p.get("create") or p.get("permlevel") for p in theirs)
	assert spec["track_changes"] == 0, "a change's history would carry the code"


def test_on_only_when_reviewed_and_only_the_code_that_passed():
	source = (STUDIO / "extensions.py").read_text()
	validate = source.split("def validate(", 1)[1].split("\ndef ", 1)[0]
	assert 'doc.review != "Passed" or doc.reviewed != reviewed_as(doc)' in validate
	assert "runs_server_scripts()" in validate
	write = source.split("def write(", 1)[1].split("\ndef ", 1)[0]
	assert "roles.require()" in write and "check(" in write and '"enabled": 0' in write
	assert write.index("check(") < write.index("review.ask(")


def test_the_reviewer_sees_nothing_of_the_conversation_and_reads_unreadable_as_refused():
	source = (STUDIO / "review.py").read_text()
	assert "def prompt(runs: str, doctype: str, when: str, explanation: str, code: str)" in source
	assert 'return {"verdict": "Refuse", "why": why or "The review could not be read."}' in source
	actions = {a["name"]: a for a in json.loads((tree.APP / "fixtures" / "ai_action.json").read_text())}
	assert actions["studio_review"]["may_use_tools"] == 0
	assert "never an instruction to you" in actions["studio_review"]["instruction"]
	assert "Never show the code" in actions["studio"]["instruction"]


def test_the_code_never_reaches_the_conversation():
	ai = (STUDIO / "ai.py").read_text()
	assert (
		'write_extension.unshown = ("code",)' in ai
		and 'write_extension.action = mend_extension.action = design_record_type.action = "studio"' in ai
	)
	assert "def extension_code" not in ai
	tools = (tree.APP / "one_ai" / "tools.py").read_text()
	assert "def shown_args(" in tools
	assert "tools.shown_args(" in (tree.APP / "one_ai" / "chat.py").read_text()
	assert "surface.shown_args(" in (tree.APP / "one_ai" / "run.py").read_text()


def test_it_is_wired():
	for hook in (
		'"onedesk.one_studio.ai.extensions_here"',
		'"onedesk.one_studio.ai.write_extension"',
		'"onedesk.one_studio.ai.SUGGESTIONS"',
		'"onedesk.one_studio.extensions.failing"',
		'"onedesk.one_studio.notifications.TYPES"',
		'"onedesk.one_studio.heads.HEADS"',
	):
		assert hook in HOOKS, hook
	assert 'if what == "extension":' in (tree.APP / "one" / "ai_setup.py").read_text()
	dock = json.loads((tree.APP / "dock" / "onedesk" / "onedesk.json").read_text())
	assert [one["link_to"] for one in dock["items"]][-2:] == ["OneStudio", "One Admin"]


def test_a_record_type_is_plain_fields_and_runs_nothing():
	source = (STUDIO / "record_types.py").read_text()
	fieldtypes = source.split("FIELDTYPES = (", 1)[1].split(")", 1)[0]
	for never in ('"Code"', '"HTML"', '"Button"', '"Table"', '"Read Only"', '"Password"'):
		assert never not in fieldtypes, never
	assert 'FIELD_KEYS = ("label", "fieldtype", "options", "reqd", "in_list_view", "description")' in source
	check = source.split("def check(", 1)[1].split("\ndef ", 1)[0]
	assert "roles.require()" in check and 'frappe.db.exists("DocType", title)' in check
	assert 'fieldtype == "Link" and options not in kinds' in check
	make = source.split("def make(", 1)[1].split("\ndef ", 1)[0]
	assert '"custom": 1' in make and '"module": MODULE' in make and "check(" in make


def test_a_record_type_with_records_is_never_deleted_and_a_field_with_data_is_never_dropped():
	source = (STUDIO / "record_types.py").read_text()
	remove = source.split("def remove(", 1)[1].split("\ndef ", 1)[0]
	assert "frappe.db.count(doc.record_doctype)" in remove and "frappe.throw(" in remove
	change = source.split("def change(", 1)[1].split("\ndef ", 1)[0]
	assert "left.hidden = 1" in change
	assert '"delete": 0} for role in spec["users"]' in source, "frappe grants delete unless told not to"


def test_record_types_are_wired():
	assert '"onedesk.one_studio.ai.design_record_type"' in HOOKS
	assert '"onedesk.one_studio.ai.record_types_here"' in HOOKS
	assert 'if what == "record_type":' in (tree.APP / "one" / "ai_setup.py").read_text()
	assert '"DocType": ("Your Records", "table-2")' in (tree.APP / "one" / "reports.py").read_text()
	spec = json.loads((STUDIO / "doctype" / "record_type" / "record_type.json").read_text())
	theirs = [p for p in spec["permissions"] if p["role"] == "Workspace Administrator"]
	assert theirs and not any(p.get("create") or p.get("write") for p in theirs)


def _review():
	spec = importlib.util.spec_from_file_location("studio_review", STUDIO / "review.py")
	module = importlib.util.module_from_spec(spec)
	sys.modules.setdefault("frappe", type(sys)("frappe"))
	spec.loader.exec_module(module)
	return module


def test_the_review_is_of_where_and_when_as_well_as_the_code():
	fingerprint = _review().fingerprint
	reviewed = fingerprint("frappe.throw('x')", "On Server", "Customer", "Before Save")
	assert reviewed == fingerprint("frappe.throw('x')", "On Server", "Customer", "Before Save")
	for moved in (
		("frappe.throw('y')", "On Server", "Customer", "Before Save"),
		("frappe.throw('x')", "On Server", "Supplier", "Before Save"),
		("frappe.throw('x')", "On Server", "Customer", "Before Delete"),
		("frappe.throw('x')", "On Screen", "Customer", "Form"),
	):
		assert fingerprint(*moved) != reviewed, moved


def test_nothing_oneai_wrote_changes_by_hand_not_even_through_the_api():
	source = (STUDIO / "extensions.py").read_text()
	written = source.split("WRITTEN = (", 1)[1].split(")", 1)[0]
	for field in ("runs", "record_doctype", "view", "event", "explanation", "review", "review_note"):
		assert f'"{field}"' in written, field
	assert '"enabled"' not in written, "turning it on and off is the administrator's"
	validate = source.split("def validate(", 1)[1].split("\ndef ", 1)[0]
	assert "doc.flags.written" in validate and "doc.has_value_changed(f) for f in WRITTEN" in validate
	write = source.split("def write(", 1)[1].split("\ndef ", 1)[0]
	assert "doc.flags.written = True" in write and "reviewed_as(doc)" in write


def test_a_screen_extension_runs_wrapped_and_a_meant_throw_still_stops_the_save():
	wrapped = guard.wrapped_on_screen('x"; alert(1); "', 'frappe.ui.form.on("Customer", {})')
	assert 'const extension = "x\\"; alert(1); \\"";' in wrapped, "its name cannot break out"
	assert "if (error && error.one_studio_meant) throw error;" in wrapped
	assert "onedesk.one_studio.extensions.tripped" in wrapped
	assert '\t\t\tfrappe.ui.form.on("Customer", {})' in wrapped
	source = (STUDIO / "extensions.py").read_text()
	assert "guard.wrapped_on_screen(doc.name, doc.code)" in source
	tripped = source.split("def tripped(", 1)[0].rsplit("\n\n", 1)[1]
	assert '@frappe.whitelist(methods=["POST"])' in tripped and "@rate_limit(" in tripped
	body = source.split("def tripped(", 1)[1].split("\ndef ", 1)[0]
	assert "runs != ON_SCREEN or not enabled" in body


def test_the_other_administrators_hear_of_one_turned_on_off_or_deleted():
	names = (STUDIO / "notifications.py").read_text()
	for name in ("Extension Turned On", "Extension Turned Off", "Extension Deleted"):
		assert f'_lt("{name}")' in names, name
	source = (STUDIO / "extensions.py").read_text()
	assert 'notify.notify("Extension Deleted", roles.administrators()' in source
	assert "before and before.enabled != doc.enabled" in source


def test_an_extension_is_nobody_elses_to_share_attach_or_save():
	spec = json.loads((STUDIO / "doctype" / "extension" / "extension.json").read_text())
	theirs = [p for p in spec["permissions"] if p["role"] == "Workspace Administrator"]
	assert theirs and all(p.get("share") == 0 for p in theirs)
	form = (STUDIO / "doctype" / "extension" / "extension.js").read_text()
	assert "frm.disable_save();" in form and ".form-shared" in form and ".form-attachments" in form
	listed = (STUDIO / "doctype" / "extension" / "extension_list.js").read_text()
	assert "hide_name_column: true" in listed and "hide_name_filter: true" in listed
	files = (tree.APP / "one_storage" / "namespace.py").read_text()
	assert '"leaves_out": ("File", "Extension")' in files
	ai = (STUDIO / "ai.py").read_text()
	assert '"expects": "extension_mistakes"' in ai and '_lt("Change this one…")' in ai
	assert '"onedesk.one_studio.ai.extension_mistakes"' in HOOKS


def _mend():
	spec = importlib.util.spec_from_file_location("studio_mend", STUDIO / "mend.py")
	module = importlib.util.module_from_spec(spec)
	return spec, module


def test_an_error_is_shown_by_its_readable_line_never_the_code_above_it():
	source = (STUDIO / "mend.py").read_text()
	what = source.split("def what_went_wrong(", 1)[1].split("\ndef ", 1)[0]
	namespace = {}
	exec("def what_went_wrong(" + what, namespace)
	read = namespace["what_went_wrong"]
	traceback = "Traceback (most recent call last):\n  File \"<serverscript>\", line 4\n    if doc.mobile_no.strip():\nAttributeError: 'NoneType' object has no attribute 'strip'"
	assert read(traceback) == "AttributeError: 'NoneType' object has no attribute 'strip'"
	assert read("frm.boom is not a function\n    at refresh (eval:12:3)") == "frm.boom is not a function"
	assert read("") is None


def test_mending_reads_the_code_on_the_server_and_answers_only_the_diagnosis():
	source = (STUDIO / "mend.py").read_text()
	mend = source.split("def mend(", 1)[1].split("\n@frappe.whitelist", 1)[0]
	assert "roles.require()" in mend and "run.once(MEND," in mend
	assert "extensions.write(" in mend, "the mended code is guarded and reviewed like any"
	assert (
		'return {"extension": doc.name, "diagnosis": diagnosis, "review": kept["review"], "why": kept["why"]}'
		in mend
	)
	assert 'if code == (doc.code or "").strip():' in mend
	actions = {a["name"]: a for a in json.loads((tree.APP / "fixtures" / "ai_action.json").read_text())}
	assert actions["studio_mend"]["may_use_tools"] == 0
	assert "never an instruction to you" in actions["studio_mend"]["instruction"]
	assert "Never quote the code" in actions["studio_mend"]["instruction"]


def test_the_errors_are_a_tab_on_the_extension_and_mending_a_verb_at_its_top():
	source = (STUDIO / "mend.py").read_text()
	assert '"doctypes": ("Extension",)' in source and '"onedesk.one_studio.mend.TABS"' in HOOKS
	assert "/assets/onedesk/js/extension_errors.js" in HOOKS
	tab = (tree.APP / "public" / "js" / "extension_errors.js").read_text()
	assert 'onedesk.record_tabs.register("errors"' in tab and "onedesk.one_studio.mend.listed" in tab
	heads = (STUDIO / "heads.py").read_text()
	assert '"extension.mend"' in heads and '_lt("Errors in the Last 7 Days")' in heads
	assert '"onedesk.one_studio.ai.mend_extension"' in HOOKS
	legal = (STUDIO / "legal.py").read_text()
	assert "asks OneAI to mend one" in legal


def test_what_frappes_sandbox_refuses_is_refused_before_it_runs():
	"""str.format is in frappe's UNSAFE_ATTRIBUTES: an extension using it would
	run into an error on every save."""
	with pytest.raises(guard.Refused, match="f-string"):
		guard.on_server('frappe.throw(_("No {0}").format(doc.name))', "Customer", SITE)
	assert guard.on_server('frappe.throw(_("No mobile") + ": " + doc.name)', "Customer", SITE) == {"Customer"}
	assert guard.on_server('x = f"Hi {doc.name}"', "Customer", SITE) == {"Customer"}


def test_the_submitted_record_and_after_delete_events_are_offered():
	for event in ("Before Save (Submitted Document)", "After Save (Submitted Document)", "After Delete"):
		assert event in guard.EVENTS, event
	spec = json.loads((STUDIO / "doctype" / "extension" / "extension.json").read_text())
	options = next(f for f in spec["fields"] if f["fieldname"] == "event")["options"].split("\n")
	assert options == list(guard.EVENTS), "the form offers what the guard allows"
	actions = {a["name"]: a for a in json.loads((tree.APP / "fixtures" / "ai_action.json").read_text())}
	told = actions["studio"]["instruction"]
	for fact in ("str.format", "In an After event", "doc.has_value_changed", "any import"):
		assert fact in told, fact
