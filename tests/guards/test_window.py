"""The window (docs/WINDOW.md): every screen in one frame made of frappe's own
parts. It adds to frappe's page head and never replaces it, styles itself in
one file, and OneCloud on its own page draws none of the parts the window
has. These read the code that says so."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import tree

JS = (tree.APP / "public" / "js" / "window.js").read_text(encoding="utf-8")
CSS = (tree.APP / "public" / "css" / "window.css").read_text(encoding="utf-8")
HOOKS = (tree.APP / "hooks.py").read_text(encoding="utf-8")
CLOUD = (tree.APP / "public" / "js" / "onecloud.js").read_text(encoding="utf-8")


def _method(source: str, name: str) -> str:
	return source.split(f"\t{name}(", 1)[1].split("\n\t}\n", 1)[0]


def test_the_window_is_loaded_everywhere_after_the_shell():
	scripts = re.findall(r'"/assets/onedesk/js/([\w.]+)"', HOOKS)
	assert scripts.index("window.js") > scripts.index("shell.js")
	assert '"/assets/onedesk/css/window.css"' in HOOKS


def test_the_window_adds_to_frappes_head_and_moves_none_of_it():
	"""frappe keeps references to its title area, actions and menu; the window
	only puts siblings beside them, and lays them out by CSS."""
	build = _method(JS, "constructor")
	assert ".prependTo($content)" in build and ".insertAfter(" in build and ".insertBefore(" in build
	for moved in (".page-title\").appendTo", "$title_area.appendTo", ".standard-items-section\").appendTo", "page_head.remove", ".detach()"):
		assert moved not in build, moved
	assert "flex-wrap: wrap !important" in CSS


def test_only_the_window_styles_the_window():
	for path in tree.APP.rglob("*.css"):
		if path.name == "window.css" or "dist" in path.parts:
			continue
		for line in path.read_text(encoding="utf-8").splitlines():
			if "{" not in line or ".one-window" not in line.split("{")[0]:
				continue
			last = line.split("{")[0].split(",")[-1].strip().split()[-1]
			assert not last.startswith(".one-window"), f"{path.name}: {line.strip()} restyles the window"


def test_the_nav_pane_is_frappes_sidebar_resized_by_its_own_variable():
	assert '"--sidebar-width"' in JS and "NAV: { min: 180, max: 440" in JS
	assert "onedesk.window.keep(onedesk.window.NAV.key" in JS
	assert "frappe.ui.Sidebar" in JS and "highlight_active_item" in JS


def test_back_and_forward_are_the_browsers():
	can = _method(JS, "can")
	assert "window.navigation" in can and "canGoBack" in can and "canGoForward" in can
	assert "window.history.back()" in JS and "window.history.forward()" in JS


def test_onecloud_on_its_page_draws_none_of_the_windows_parts():
	windowed = _method(CLOUD, "build_in_window")
	for part in ("oc-bar", "oc-address", "oc-status", "oc-crumbs", "oc-search", "shell.panes", "shell.fit"):
		assert part not in windowed, part
	for asked in ("win.nav_slot()", "win.details(", "win.search(", "win.handle("):
		assert asked in windowed, asked
	page = (tree.APP / "one_storage" / "page" / "onecloud" / "onecloud.js").read_text(encoding="utf-8")
	assert "window: true, fit: true" in page and "hide_sidebar" not in page


def test_only_the_trial_puts_lists_and_forms_on_the_window():
	trial = JS.split("// The trial:", 1)[1]
	assert "(() => {\n\tif (!onedesk.window.trial()) return;" in trial
	assert "frappe.views.ListView" in trial and "frappe.ui.form.Form" in trial
	assert "frappe.views.ListView" not in JS.split("// The trial:", 1)[0]
	outside = (tree.APP / "public" / "js" / "outside.js").read_text(encoding="utf-8")
	assert 'label: __("Window Preview")' in outside and "onedesk.window.set_trial(" in outside


def test_the_address_box_is_frappes_search_bar():
	"""The address box is the breadcrumbs at rest and frappe's own search bar
	when typed in, so one place goes anywhere; Ctrl+K opens it."""
	assert "class AddressBar extends frappe.search.AwesomeBar" in JS and "this.setup_event_listeners($host)" in JS
	assert "frappe.search.open_awesomebar_from_global_search_shortcut = function" in JS
	assert ".navbar-modal-search-mobile" in JS
	assert "this.handlers.path" in JS and "path: (typed) =>" in CLOUD
	hooks = HOOKS.split("awesomebar_search = ", 1)[1].split("\n", 1)[0]
	assert '"onedesk.one.outside.awesomebar"' in hooks
	outside = (tree.APP / "one" / "outside.py").read_text(encoding="utf-8")
	assert "del frappe.local.message_log[said:]" in outside
