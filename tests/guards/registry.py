"""Every guard, by the passover point it serves (docs/PASSOVER.md, The points).

A guard fails in the code on a practice a reading of the screen can miss. Each
row says which point it serves, what it fails on, and where it runs: a test
(`tests/file.py::test_name`) or a command. A point still waiting for its guard
says what is coming in PLANNED. `python3 scripts/guards.py` lists them by
point, and `--run` runs them all.
"""

from typing import NamedTuple


class Guard(NamedTuple):
	id: str
	point: int
	what: str
	runs: str


POINTS = {
	1: "Demo coverage",
	2: "Rules on the server",
	3: "Hand-offs",
	4: "Tier declared",
	5: "Our look",
	6: "Nothing lost",
	7: "Extensible",
	8: "Built from frappe",
	9: "Overrides recorded",
	10: "Notifications",
	11: "Printed",
	12: "Plain words",
	13: "Documented, and OneAI knows and does",
	14: "Intake",
	15: "Permissions and roles",
	16: "Legal",
	17: "Clean code",
}

GUARDS = [
	# 4 Tier declared
	Guard(
		"islands-declared",
		4,
		"an island not declared, built and mounted",
		"tests/test_islands.py::test_every_island_is_declared_built_and_mounted",
	),
	Guard(
		"pages-on-shell",
		4,
		"a desk page neither on the shell nor named as not yet",
		"tests/test_shell.py::test_every_page_is_on_the_shell_or_named_as_not_yet",
	),
	Guard(
		"heads-declared",
		4,
		"a Record Head not declared in the tier registry",
		"tests/guards/test_tiers.py::test_every_record_head_is_declared",
	),
	Guard(
		"pages-declared",
		4,
		"a page of its own not declared, or declared without why",
		"tests/guards/test_tiers.py::test_every_page_of_its_own_is_declared",
	),
	Guard(
		"collections-declared",
		4,
		"a list, calendar or tree set up and not declared",
		"tests/guards/test_tiers.py::test_every_collection_set_up_is_declared",
	),
	Guard(
		"views-kept",
		4,
		"a view frappe offers taken away",
		"tests/guards/test_tiers.py::test_no_view_frappe_offers_is_taken_away",
	),
	Guard(
		"screens-declared",
		4,
		"a desk page of ours not declared with what it is",
		"tests/guards/test_tiers.py::test_every_desk_page_of_ours_is_declared",
	),
	Guard(
		"record-tabs-declared",
		4,
		"a record tab drawn outside the one place that draws them",
		"tests/test_layer.py::test_a_record_tab_is_declared_by_its_module_and_drawn_in_one_place",
	),
	# 5 Our look
	Guard(
		"shell-styles-shell",
		5,
		"anything but the shell styling the shell",
		"tests/test_shell.py::test_only_the_shell_styles_the_shell",
	),
	Guard(
		"page-draws-no-shell",
		5,
		"a page drawing a part the shell draws",
		"tests/test_shell.py::test_a_page_on_the_shell_draws_none_of_its_parts",
	),
	Guard(
		"portal-look",
		5,
		"a page outside the desk without the portal",
		"tests/test_shell.py::test_every_page_outside_the_desk_wears_the_portal",
	),
	# 8 Built from frappe
	Guard(
		"island-frappe-ui",
		8,
		"an island part that frappe-ui has, written by us",
		"tests/test_islands.py::test_an_island_is_frappe_ui_and_nothing_of_its_own",
	),
	Guard(
		"island-tokens",
		8,
		"a colour or size in an island that is not a frappe-ui token",
		"tests/test_islands.py::test_an_island_uses_frappe_ui_tokens",
	),
	Guard(
		"kit-reaches-desk",
		8,
		"an island reaching into desk other than through the kit",
		"tests/test_islands.py::test_only_the_kit_reaches_into_desk",
	),
	Guard(
		"list-is-frappes",
		8,
		"a list of records not drawn as frappe's table",
		"tests/test_shell.py::test_a_list_of_records_is_frappes_table",
	),
	Guard("dialog-is-frappes", 8, "a dialog not frappe's", "tests/test_shell.py::test_a_dialog_is_frappes"),
	Guard(
		"record-as-docview",
		8,
		"a record opened by a page not drawn as a docview",
		"tests/test_shell.py::test_a_record_a_page_opens_on_is_drawn_as_a_docview",
	),
	Guard(
		"formats-from-frappe",
		8,
		"a date, number or currency formatted by hand instead of through frappe",
		"tests/guards/test_formats.py::test_nothing_is_formatted_by_hand",
	),
	Guard(
		"hooks-exist",
		8,
		"a hook naming a function or asset that does not exist",
		"tests/test_hooks.py::test_the_function_exists",
	),
	# 9 Overrides recorded
	Guard(
		"overrides-hold",
		9,
		"an upstream line we lean on that has gone",
		"cmd: python3 scripts/overrides.py --check",
	),
	Guard(
		"upstream-unmoved",
		9,
		"something upstream moved under us",
		"tests/test_generated.py::test_nothing_upstream_moved_under_us",
	),
	Guard(
		"made-declared",
		9,
		"a kind of record we make that is not declared",
		"tests/test_makes_records.py::test_every_kind_made_is_declared",
	),
	# 10 Notifications
	Guard(
		"one-sender",
		10,
		"a mail or notification sent around the hub",
		"tests/test_notify.py::test_nothing_else_sends",
	),
	Guard(
		"types-declared",
		10,
		"a notification sent that is not declared",
		"tests/test_notify.py::test_every_type_sent_is_declared",
	),
	Guard(
		"types-say-needs",
		10,
		"a notification that does not say what it needs",
		"tests/test_notify.py::test_every_type_says_what_it_needs",
	),
	# 12 Plain words
	Guard(
		"screen-plain",
		12,
		"screen text with a colon or semicolon clause, a coinage or narration",
		"tests/test_wording.py::test_what_a_screen_says_is_plain",
	),
	Guard(
		"labels-are-names",
		12,
		"a label written as a sentence",
		"tests/test_wording.py::test_every_label_is_a_name_not_a_sentence",
	),
	Guard(
		"descriptions-plain",
		12,
		"a field description longer than two plain sentences",
		"tests/test_wording.py::test_every_description_is_one_or_two_plain_sentences",
	),
	Guard(
		"no-commit-voice",
		12,
		"screen text that reads like a commit message",
		"tests/test_console.py::test_no_screen_text_reads_like_a_commit_message",
	),
	Guard(
		"island-translated",
		12,
		"island text not passed through __()",
		"tests/test_islands.py::test_what_an_island_says_is_translated",
	),
	Guard(
		"translated",
		12,
		"a string with no Arabic or German",
		"tests/test_translations.py::test_every_string_reaches_a_reader",
	),
	Guard(
		"placeholders",
		12,
		"a translation that loses a placeholder",
		"tests/test_translations.py::test_placeholders_survive_translation",
	),
	# 13 Documented, and OneAI knows and does
	Guard(
		"docs-current",
		13,
		"a README or generated reference out of date",
		"tests/test_generated.py::test_docs_are_current",
	),
	Guard(
		"oneai-badge", 13, "OneAI badged by hand", "tests/test_ai_look.py::test_nothing_badges_oneai_by_hand"
	),
	Guard(
		"oneai-button",
		13,
		"an OneAI button drawn by hand",
		"tests/test_ai_look.py::test_no_oneai_button_is_drawn_by_hand",
	),
	Guard(
		"oneai-no-page-button",
		13,
		"an OneAI button placed on a page",
		"tests/test_oneai_place.py::test_no_oneai_button_on_a_page",
	),
	# 15 Permissions and roles
	Guard(
		"no-system-manager-code",
		15,
		"code that waits for System Manager",
		"tests/test_roles.py::test_no_code_waits_for_system_manager",
	),
	Guard(
		"no-system-manager-screen",
		15,
		"a screen that waits for System Manager",
		"tests/test_roles.py::test_no_screen_waits_for_system_manager",
	),
	Guard(
		"operator-verbs-gated",
		15,
		"an operator verb without its gate",
		"tests/test_console.py::test_every_operator_verb_is_gated",
	),
	# 16 Legal
	Guard(
		"legal-version",
		16,
		"a clause changed without a new revision or recorded hash",
		"tests/test_legal.py::test_every_document_is_at_the_version_recorded",
	),
	Guard(
		"subprocessors",
		16,
		"a company One calls that is not a declared subprocessor",
		"tests/test_legal.py::test_every_company_one_calls_is_a_declared_subprocessor",
	),
	Guard(
		"legal-assembled",
		16,
		"a module's legal file left out of the documents",
		"tests/test_legal.py::test_every_modules_legal_file_is_assembled",
	),
	Guard(
		"nothing-promised",
		16,
		"an agreement promising what is not built",
		"tests/test_legal.py::test_nobody_is_promised_what_is_not_built",
	),
]

#: Points whose guard is still to come, and what it will fail on.
PLANNED = {
	1: "a module with a feature and no demo record or integration test on it (the demo company, ARC 6)",
	2: "a rule decided in an endpoint or a button rather than the record's own hooks (ARC 7)",
	3: "a module README without its Connections section (ARC 10)",
	6: "a page of its own without the record frame (ARC 5)",
	7: "a page of its own that declares no places (ARC 5)",
	11: "a record that leaves the company with no shipped print format (ARC 9)",
	14: "a module with no Intake sample for its records (ARC 10)",
	17: "a narrative comment of more than a few lines, or a module out of the one layout (ARC 10)",
}
