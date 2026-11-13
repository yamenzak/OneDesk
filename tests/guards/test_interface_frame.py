"""The window (onedesk/one_interface/AGENTS.md): every screen in one frame made of frappe's own
parts. It adds to frappe's page head and never replaces it, styles itself in
one file, and OneCloud on its own page draws none of the parts the window
has. These read the code that says so."""

import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import tree

FRAME_JS = tree.APP / "public" / "js" / "one_interface"
FRAME_CSS = tree.APP / "public" / "css" / "one_interface"
FRAME = (FRAME_JS / "frame.js").read_text(encoding="utf-8")
CHROME = (FRAME_JS / "chrome.js").read_text(encoding="utf-8")
ADAPTERS = {path.stem: path.read_text(encoding="utf-8") for path in FRAME_JS.glob("*.js") if path.stem not in ("frame", "chrome", "phone", "nav_tree", "json_view", "look", "dialogs", "stamps", "star", "select", "keys", "views", "centre", "tour")}
JS = FRAME + "".join(ADAPTERS.values())
CSS = "".join(path.read_text(encoding="utf-8") for path in sorted(FRAME_CSS.glob("*.css")))
HOOKS = tree.hooks()
CLOUD = (tree.ROOT / "frontend" / "src" / "cloud" / "OneCloud.vue").read_text(encoding="utf-8")


def _read(*parts: str) -> str:
	return tree.ROOT.joinpath(*parts).read_text(encoding="utf-8")


TEXTS = {
	"frame": FRAME,
	"chrome": CHROME,
	"adapters": ADAPTERS,
	"css": CSS,
	"hooks": HOOKS,
	"cloud": CLOUD,
	"phone_js": (FRAME_JS / "phone.js").read_text(encoding="utf-8"),
	"nav": (FRAME_JS / "nav_tree.js").read_text(encoding="utf-8"),
	"tokens_css": (FRAME_CSS / "tokens.css").read_text(encoding="utf-8"),
	"chrome_css": (FRAME_CSS / "chrome.css").read_text(encoding="utf-8"),
	"phone_css": (FRAME_CSS / "phone.css").read_text(encoding="utf-8"),
	"views_css": (FRAME_CSS / "views.css").read_text(encoding="utf-8"),
	"desk_js": _read("onedesk", "public", "js", "desk.js"),
	"desk_css": _read("onedesk", "public", "css", "desk.css"),
	"band": _read("onedesk", "public", "js", "band.js"),
	"outside_js": _read("onedesk", "public", "js", "outside.js"),
	"lists": _read("onedesk", "public", "js", "one", "lists.js"),
	"outside_py": _read("onedesk", "one", "outside.py"),
	"control": _read("onedesk", "one", "control.py"),
	"boot": _read("onedesk", "one", "boot.py"),
	"company": _read("onedesk", "one", "company.py"),
	"cloud_page": _read("onedesk", "one_cloud", "page", "onecloud", "onecloud.js"),
	"cloud_items": _read("frontend", "src", "cloud", "CloudItems.vue"),
	"mail": _read("frontend", "src", "mail", "OneMail.vue"),
}
"""What the window's rules read, by name, so each rule is a check of these
texts and its proof hands it the same texts with one thing spoiled."""


def _js(t: dict) -> str:
	return t["frame"] + "".join(t["adapters"].values())


def spoiled(key: str, old: str, new: str = "") -> dict:
	"""TEXTS with `old` replaced in one of them (`adapters.list` names an
	adapter), for a proof; `old` must be there, so the example is real."""
	out = {**TEXTS, "adapters": dict(ADAPTERS)}
	where, _, kind = key.partition(".")
	held, at = (out["adapters"], kind) if kind else (out, where)
	assert old in held[at], f"{key} has no {old!r} to spoil"
	held[at] = held[at].replace(old, new)
	return out


def _method(source: str, name: str) -> str:
	return source.split(f"\t{name}(", 1)[1].split("\n\t}\n", 1)[0]


BEFORE_THE_SHELL = ("one_interface/centre.js", "one_interface/tour.js")
"""The centre frame and the tours, loaded with the desk's first scripts: every
centre declares itself to the frame as it loads, before the shell."""


def _one_folder(t: dict) -> None:
	scripts = re.findall(r'"/assets/onedesk/js/([\w./]+)"', t["hooks"])
	assert scripts.index("one_interface/frame.js") > scripts.index("shell.js")
	loaded = [one for one in scripts if one.startswith("one_interface/")]
	assert [one for one in loaded if one not in BEFORE_THE_SHELL][:2] == ["one_interface/frame.js", "one_interface/chrome.js"]
	assert all(scripts.index(one) < scripts.index("shell.js") for one in BEFORE_THE_SHELL)
	assert sorted(loaded) == sorted(f"one_interface/{path.name}" for path in FRAME_JS.glob("*.js"))
	styles = re.findall(r'"/assets/onedesk/css/(one_interface/[\w.]+)"', t["hooks"])
	assert [one for one in styles if one != "one_interface/centre.css"][:4] == ["one_interface/tokens.css", "one_interface/palettes.css", "one_interface/chrome.css", "one_interface/frame.css"]
	assert sorted(styles) == sorted(f"one_interface/{path.name}" for path in FRAME_CSS.glob("*.css"))
	assert {"page", "list", "board", "report", "tree", "form", "print", "workspace"} <= set(t["adapters"])


def test_the_interface_is_one_folder_loaded_after_the_shell():
	"""The window is js/one_interface and css/one_interface: the frame first, then one
	adapter per kind of view, every file of the folder loaded and nothing of
	it anywhere else; the centre frame and the tours load before the shell."""
	_one_folder(TEXTS)
	assert not (tree.APP / "public" / "js" / "window.js").exists()


def _frame_places(t: dict) -> None:
	view = _method(t["frame"], "view")
	for part in ("primary", "commands", "menu", "controls", "views", "search", "status"):
		assert part in view, part
	for kind, source in t["adapters"].items():
		assert f'onedesk.interface.adapt("{kind}", () => {{' in source, kind
		assert ".view({" in source, kind
		for reach in ("$commands", "views_slot(", "win.handle(", "win.search(", "win.status(", "win.can("):
			assert reach not in source, f"{kind}.js reaches into the frame: {reach}"
	assert set(t["adapters"]) <= set(re.findall(r'"(\w+)"', t["frame"].split("ON: [", 1)[1].split("covers(", 1)[0]))


def test_a_view_says_what_it_has_and_the_frame_places_it():
	"""One place decides where a view's parts go: `view()` in frame.js. An
	adapter installs through `adapt(kind)` and hands over parts; it never
	reaches into the frame's rows itself, so a change to the layout is made
	once and every view follows."""
	_frame_places(TEXTS)


def _adds_to_head(t: dict) -> None:
	build = _method(_js(t), "constructor")
	assert ".prependTo($content)" in build and ".insertAfter(" in build and ".insertBefore(" in build
	for moved in (".page-title\").appendTo", "$title_area.appendTo", ".standard-items-section\").appendTo", "page_head.remove", ".detach()"):
		assert moved not in build, moved
	assert "flex-wrap: wrap !important" in t["css"]


def test_the_window_adds_to_frappes_head_and_moves_none_of_it():
	"""frappe keeps references to its title area, actions and menu; the window
	only puts siblings beside them, and lays them out by CSS."""
	_adds_to_head(TEXTS)


def restyles(source: str) -> list[str]:
	"""The rules of a stylesheet outside the window that land on the window's
	own `.one-interface*` parts. Pure."""
	out = []
	for line in source.splitlines():
		if "{" not in line or ".one-interface" not in line.split("{")[0]:
			continue
		last = line.split("{")[0].split(",")[-1].strip().split()[-1]
		if last.startswith(".one-interface"):
			out.append(line.strip())
	return out


def test_only_the_window_styles_the_window():
	for path in tree.scoped(tree.APP.rglob("*.css")):
		if "one_interface" in path.parent.parts[-1:] or "dist" in path.parts:
			continue
		found = restyles(path.read_text(encoding="utf-8"))
		assert not found, f"{path.name}: {found[0]} restyles the window"


def _nav_pane(t: dict) -> None:
	js = _js(t)
	assert '"--sidebar-width"' in js and "NAV: { min: 180, max: 440" in js
	assert "onedesk.interface.keep(onedesk.interface.NAV.key" in js
	assert "frappe.ui.Sidebar" in js and "highlight_active_item" in js


def test_the_nav_pane_is_frappes_sidebar_resized_by_its_own_variable():
	_nav_pane(TEXTS)


def _browsers_history(t: dict) -> None:
	js = _js(t)
	can = _method(js, "can")
	assert "window.navigation" in can and "canGoBack" in can and "canGoForward" in can
	assert "window.history.back()" in js and "window.history.forward()" in js


def test_back_and_forward_are_the_browsers():
	_browsers_history(TEXTS)


def _cloud_on_window(t: dict) -> None:
	cloud = t["cloud"]
	assert '<template v-if="!win">' in cloud and '<div v-if="!win" class="border-t' in cloud
	for part in ("commands", "details"):
		assert f'part="{part}"' in cloud, part
	assert "interfaceHeading(props.win" in cloud and "ways: views" in cloud
	assert "interfaceTree(props.win" in cloud
	assert "interfaceSearch(props.win" in cloud and "interfaceStatus(props.win" in cloud and "interfaceHandles(props.win" in cloud
	assert "fit: true" in t["cloud_page"] and "hide_sidebar" not in t["cloud_page"]


def test_onecloud_on_its_page_draws_none_of_the_windows_parts():
	"""Its own bar, address and status are drawn only off the window (a
	record's files, the picker); on its page each goes to the window's part,
	and its name, New and views to the window's head over a list."""
	_cloud_on_window(TEXTS)


def _every_view_on(t: dict) -> None:
	frame, adapters = t["frame"], t["adapters"]
	on = re.findall(r'"(\w+)"', frame.split("ON: [", 1)[1].split("]", 1)[0])
	assert set(on) == set(adapters) | {"page"}, sorted(set(adapters) ^ set(on))
	assert "TRIAL" not in frame and "trial()" not in _js(t)
	assert "frappe.views.ListView" in adapters["list"] and "frappe.ui.form.Form" in adapters["form"]
	assert "frappe.views.ListView" not in frame and "frappe.ui.form.Form" not in frame
	assert "Window Preview" not in t["outside_js"] and "set_trial" not in t["outside_js"]


def test_every_view_is_on_the_window_for_everybody():
	"""Each kind was walked and joined; there is no preview left to turn on."""
	_every_view_on(TEXTS)


def _address_box(t: dict) -> None:
	js = _js(t)
	assert "class AddressBar extends frappe.search.AwesomeBar" in js and "this.setup_event_listeners($host)" in js
	assert "frappe.search.open_awesomebar_from_global_search_shortcut = function" in js
	assert ".navbar-modal-search-mobile" in js
	assert "this.handlers.path" in js and "path: (path) =>" in t["cloud"]
	hooks = t["hooks"].split("awesomebar_search = ", 1)[1].split("\n", 1)[0]
	assert '"onedesk.one.outside.awesomebar"' in hooks
	assert "del frappe.local.message_log[said:]" in t["outside_py"]


def test_the_address_box_is_frappes_search_bar():
	"""The address box is the breadcrumbs at rest and frappe's own search bar
	when typed in, so one place goes anywhere; Ctrl+K opens it."""
	_address_box(TEXTS)


def _list_setup(t: dict) -> str:
	return t["adapters"]["list"].split("List.prototype.setup_page = function", 1)[1].split("\n\t};", 1)[0]


def _one_reload(t: dict) -> None:
	js = _js(t)
	assert 'name === "refresh-cw"' in js and "this.interface.adopt_reload($button)" in js
	assert "!!this.handlers.refresh && !this.$reload" in js
	assert "refresh:" not in _list_setup(t)


def test_frappes_reload_is_the_one_in_the_address_row():
	"""Where frappe makes a reload button, that button is moved to the address
	row and the window's own Refresh steps aside; nothing duplicates it."""
	_one_reload(TEXTS)


def shared_marks(js: str) -> list[str]:
	"""The wrapped-class marks read off a prototype through inheritance
	rather than asked of the prototype itself, or [""] where the source has
	no mark at all. Pure."""
	marks = re.findall(r"if \(!?\w+ (?:&&|\|\|) !?(Object\.hasOwn\(\w+\.prototype, \"one_interface\"\)|\w+\.prototype\.one_interface)\)", js)
	return [one for one in marks if not one.startswith("Object.hasOwn")] if marks else [""]


def test_each_wrapped_class_has_its_own_mark():
	"""ListView inherits from BaseList, so a mark set on BaseList's prototype
	reads as set on ListView's and skipped its wrappers: the list lost its
	search and its count. Each mark is asked of the prototype itself."""
	assert not shared_marks(JS)


def _new_leads(t: dict) -> None:
	list_setup = _list_setup(t)
	assert "primary: this.page.btn_primary" in list_setup
	assert "menu: { $button: this.page.menu_btn_group, dropdown: this.page.menu_dropdown }" in list_setup
	view = _method(t["frame"], "view")
	assert 'menu.dropdown.align = "start"' in view
	order = re.findall(r'data-group="(\w+)"', t["frame"])
	assert order == ["primary", "own", "menu"], order
	assert "~ .one-interface-group:has(" in t["css"] and "::before" in t["css"]


def test_a_lists_new_leads_the_command_row():
	"""A list's primary button (New) is frappe's own node moved to the start of
	the command row, as OneCloud's New is, and frappe's menu (…) follows it
	after a line. A form's Save leads the same way
	(test_the_main_action_is_always_first_on_the_left)."""
	_new_leads(TEXTS)


def _filter_and_sort(t: dict) -> None:
	assert 'this.views_slot().prepend(controls.addClass("one-interface-filters"))' in t["frame"]
	assert 'controls: this.$page && this.$page.find(".filter-section").first()' in t["adapters"]["list"]
	assert '.one-interface[data-one-view="list"] .list-row-head {' in t["css"] and "border-radius: 0;" in t["css"]


def test_filter_and_sort_are_commands_and_the_heads_are_flat():
	"""A list's Filter and Sort are frappe's own buttons moved among the
	commands, before the view toggles; the column heads are drawn as
	OneCloud's are, words with a line under them."""
	_filter_and_sort(TEXTS)


def _one_gutter(t: dict) -> None:
	assert '.one-interface[data-one-view="list"] .frappe-list {\n\t\tmargin-inline: 0;' in t["css"]
	assert ".one-interface[data-one-view=\"list\"] .list-row-container,\n" in t["css"]
	items = t["cloud_items"]
	assert "border-b border-outline-gray-1 px-2 py-1.5" in items and "'grid items-center px-2 text-base'" in items
	assert "rounded-full bg-surface-gray-3 px-2" in items


def test_every_row_sits_on_one_gutter():
	"""A list's own side margin and inset rows are taken away in the window,
	and the status row uses the command row's gutter, so every row starts and
	ends on the same edge; OneCloud's files sit on it too."""
	_one_gutter(TEXTS)


def _waits_late(t: dict) -> None:
	assert 'onedesk.interface.when(frappe.views, "KanbanV2Page"' in t["adapters"]["board"]
	assert 'onedesk.interface.when(frappe.ui.form, "PrintView"' in t["adapters"]["print"]
	when = t["frame"].split("\twhen(owner, name, then) {", 1)[1].split("\n\t},", 1)[0]
	assert "Object.defineProperty(owner, name" in when and "all.forEach((one) => one(value))" in when


def test_a_view_frappe_loads_late_is_waited_for():
	"""Kanban v2 and the print view are defined when their code first loads,
	after ours; their adapters wait for frappe to assign the class rather
	than looking for it once and finding nothing. Everybody waits through
	`when`: a second hook of one's own on the class took the window's place,
	and the board lost its command row."""
	_waits_late(TEXTS)
	public = tree.APP / "public" / "js"
	for path in tree.scoped(public.rglob("*.js")):
		if path.name != "frame.js":
			assert 'defineProperty(frappe.views, "KanbanV2Page"' not in path.read_text(), path.name


def _counted(t: dict) -> None:
	source = t["adapters"]["list"]
	counted = source.split("const COUNTED = [", 1)[1].split("]", 1)[0]
	for view in ("Kanban", "Calendar", "Dashboard"):
		assert f'"{view}"' not in counted, view
	for view in ("List", "Report", "Image"):
		assert f'"{view}"' in counted, view
	assert "counted(this)) win.view({ status" in source


def test_only_views_of_pages_show_a_count_and_paging():
	"""A board, a calendar and a dashboard show all they hold, so the status
	row carries no count or paging for them; a list, a report and an image
	grid do."""
	_counted(TEXTS)


def _tree_as_list(t: dict) -> None:
	assert 'controls: this.page.page_form.children(".tree-toolbar-actions")' in t["adapters"]["tree"]
	assert '.one-interface[data-one-view="tree"] .page-form {' in t["css"]
	assert '.one-interface[data-one-view="tree"] .layout-main-section-wrapper > .layout-main-section {\n\t\tmax-width: none;' in t["css"]


def test_a_tree_is_laid_out_as_a_list():
	"""A tree's Sort and Expand/Collapse sit before its view toggles, as a
	list's Filter and Sort do; its filters are the view row on the gutter, and
	frappe's centred column gives way to the window's width."""
	_tree_as_list(TEXTS)


def _two_bars(t: dict) -> None:
	chrome = t["chrome"]
	assert 'data-at="top"' in chrome and 'data-at="bottom"' in chrome
	for gone in ("place_bar", "one_bar", "Move This Bar"):
		assert gone not in chrome, gone
	assert "onedesk.dock.bar = " not in t["desk_js"] and "onedesk.interface.bars()" in t["desk_js"]
	assert "def place_bar" not in t["control"]
	chrome_css = t["tokens_css"] + t["chrome_css"]
	for token in ("--dock-bg: var(--one-frame);", "--dock-ink: var(--one-frame-ink);", "--dock-tile-active: transparent;"):
		assert token in chrome_css, token
	assert "border-start-end-radius: var(--one-radius-sheet);" in chrome_css and "border-end-start-radius: var(--one-radius-sheet);" in chrome_css
	assert ".one-bar {" not in t["desk_css"] and "one-bar-bottom" not in t["desk_css"]


def test_the_frame_is_a_top_bar_a_bottom_bar_and_the_rail():
	"""The shell's rail and bars are the window's frame: one bar across the
	top (where and when) and one across the bottom (what is running), never
	one that moves; frappe's rail draws from the frame's tokens; and the
	screen between them is inset with its corners rounded."""
	_two_bars(TEXTS)


def _workspace_colour(t: dict) -> None:
	assert '"one_frame_colour"' in t["control"]
	assert 'bootinfo["one_frame_colour"]' in t["boot"]
	assert "root.dataset.oneFrameInk" in t["chrome"] and '"one_frame"' in t["chrome"]
	assert "letter_heads.on(colour)" in t["company"], "the frame's ink is the letter heads' rule, not a second one"
	assert "luminance" not in t["chrome"].lower()
	assert ':root[data-theme="dark"][data-one-frame="brand"]' in t["tokens_css"]
	assert ':root[data-one-frame-ink="dark"]:not([data-theme="dark"])' in t["tokens_css"]


def test_the_frame_wears_the_workspaces_colour():
	"""Frame Colour (Workspace › General › Contact and Branding, on the Company) is the
	frame's colour for everyone, with the ink that reads on it; a dark theme
	deepens it. Empty is One's own."""
	_workspace_colour(TEXTS)


def _taskbar(t: dict) -> None:
	chrome, frame = t["chrome"], t["frame"]
	bottom = chrome.split('data-at="bottom"', 1)[1].split("</footer>", 1)[0]
	assert bottom.index('class="one-bar-status"') < bottom.index('data-group="open"') < bottom.index('data-group="day"')
	assert bottom.rstrip().endswith('<div class="one-bar-group" data-group="when"><button class="one-bar-tool one-bar-now"></button></div>\n\t\t\t</div>')
	top = chrome.split('data-at="top"', 1)[1].split("</header>", 1)[0]
	assert "one-bar-name" in top and "one-bar-now" not in top
	place = frame.split("\tplace_status() {", 1)[1].split("\n\t},", 1)[0]
	assert "current.$status.appendTo($slot)" in place and "win.$status.appendTo(win.$wrapper)" in place
	assert "onedesk.interface.place_status();" in frame.split('$(document).on("page-change"', 1)[1]


def test_the_bottom_bar_is_a_taskbar():
	"""The window on screen shows its status (count, paging) at the start of
	the bottom bar, and the date and time close it, where Windows keeps its
	clock; the top bar opens with the workspace's name."""
	_taskbar(TEXTS)


def _rail_edge(t: dict) -> None:
	chrome_css = t["chrome_css"]
	assert ".one-rail-mark > i {\n\theight: 20px;" in chrome_css
	assert 'body.one-barred .dock-items.one-rail .dock-item::before {\n\tcontent: "";\n\theight: 8px;' in chrome_css
	assert "width: calc(100% + 16px);\n\tmargin-inline: -8px;" in chrome_css


def test_the_app_you_are_in_is_marked_on_the_rails_edge():
	"""As Discord marks a server: a bar of the frame's strongest ink on the
	rail's edge beside the active tile, a short one beside a hovered tile,
	and the tile itself unfilled. The tile list reaches the rail's edges so
	its scrolling box does not clip the bar."""
	_rail_edge(TEXTS)


def _flat_marks(t: dict) -> None:
	chrome_css = t["chrome_css"]
	assert ':root[data-one-frame="brand"] body.one-barred .dock-item .dock-item-icon > svg.one-flat' in chrome_css
	assert "drop-shadow" not in chrome_css and "background-clip: content-box;" not in chrome_css
	assert 'frappe.utils.icon(`${entry.icon}-flat`' in t["chrome"]


def flat_problems(icons: list[dict], marks: list[str]) -> list[str]:
	"""A brand mark without its flat twin among the icons, or a flat twin
	with a filter or a gradient. Pure."""
	names = {icon["name"] for icon in icons}
	out = [f"{mark} has no flat twin" for mark in marks if f"{mark}-flat" not in names]
	return out + [icon["name"] for icon in icons if icon["name"].endswith("-flat") and ("filter" in icon["svg"] or "Gradient" in icon["svg"])]


def test_the_rails_marks_go_flat_on_a_workspace_colour():
	"""An app's mark on a frame of its own hue all but disappears, so on a
	workspace's colour the rail shows each mark's flat twin, generated beside it
	from the same SVG: no filter, no shadow, no box behind it."""
	_flat_marks(TEXTS)
	icons = json.loads((tree.APP / "fixtures" / "custom_icon.json").read_text(encoding="utf-8"))
	found = flat_problems(icons, [mark.stem for mark in (tree.ROOT / "brand").glob("*.svg")])
	assert not found, found


def _main_first(t: dict) -> None:
	assert "primary: this.page.btn_primary" in t["adapters"]["list"] and "primary: this.page.btn_primary" in t["adapters"]["form"]
	assert '.custom-actions > :is([data-variant="solid"], .btn-primary),' in t["views_css"]


def test_the_main_action_is_always_first_on_the_left():
	"""One rule for the command row: the solid main action leads it on the
	left, a list's New and a form's Save, Submit or Update alike; where a form
	has none, its own solid button (Record Payment) leads its run."""
	_main_first(TEXTS)


def _details_pane(t: dict) -> None:
	forms, views, band, frame = t["adapters"]["form"], t["views_css"], t["band"], t["frame"]
	assert 'win.details({ key: "form", width: 400, pane: $side })' in forms
	assert "new frappe.ui.Tabs(" in forms and 'onedesk.interface.PANEL = ["overview", "activity", "mail", "connections"]' in forms
	assert "dashboard.links_area.wrapper" in forms and "panel.panes.connections" in forms
	assert "panel.sections.append(dashboard.parent.children(" in forms and "frm.one_panel.head" in band
	assert "details_edge()" in frame
	assert "onedesk.band.put(" in band and "frm.dashboard.set_headline(" not in band.replace("if (html) frm.dashboard.set_headline(html, null, true);", "")
	assert "container-type: inline-size" in views and "@container (min-width: 520px)" in views


def test_a_forms_sidebar_is_the_details_pane_and_holds_the_record_panel():
	"""A form's sidebar is the window's details pane (one switch, one drag
	edge, as OneCloud's), and its Overview, Activity, Mail and Connections
	are frappe's own tabs, frappe's dashboard split between the first and last, with the head drawn there through one place (band.put) and laid
	out by the panel's width, not the screen's."""
	_details_pane(TEXTS)


ENGINE_READS = {"Note"}
"""The one doctype the engine reads by name: the top bar's news is frappe's
Note, which belongs to the frame, not to any screen."""
SPECIFIC = [
	r'data-(?:page-)?route="',
	r'data-doctype="[A-Z]',
	r'data-fieldname="',
	r'\bdoctype\s*[!=]==?\s*["\'][A-Z]',
	r'\bfieldname\s*[!=]==?\s*["\']',
	r'(?:get_doc|get_value|get_list|new_doc)\(\s*["\']([A-Z][\w ]*)',
	r'set_route\(\s*["\'](?:List|Form)["\']\s*,\s*["\']([A-Z][\w ]*)',
	r'\bfrm\.doc\.(?!name\b|doctype\b|docstatus\b|__)[a-z_]+',
]


def specifics(source: str) -> list[tuple[int, str]]:
	"""The lines of the engine's source naming one screen's doctype, field or
	route, once for each pattern that finds it. Pure."""
	found = []
	for n, line in enumerate(source.splitlines(), 1):
		for pattern in SPECIFIC:
			hit = re.search(pattern, line)
			if hit and not (hit.groups() and hit.group(1) in ENGINE_READS):
				found.append((n, line.strip()))
	return found


def test_the_engine_names_no_doctype():
	"""The window and the record panel are the engine: they work from what
	frappe says a screen has, so every doctype gets them the same. A doctype,
	a field or a route of one screen named in them is a specific, and it goes
	to the module that owns that screen."""
	files = [*FRAME_JS.glob("*.js"), *FRAME_CSS.glob("*.css"), tree.APP / "public" / "js" / "band.js"]
	found = [f"{path.relative_to(tree.APP)}:{n}: {line}" for path in files for n, line in specifics(path.read_text(encoding="utf-8"))]
	assert not found, "the engine names a screen's own doctype, field or route:\n" + "\n".join(found)


def _windows_tree(t: dict) -> None:
	nav = t["nav"]
	assert "onedesk.interface.Tree = class Tree" in nav and "Frame.prototype.tree" in nav
	assert 'class="standard-sidebar-item' in nav and "active-sidebar" in nav and "one-interface-count" in nav
	assert t["hooks"].index('"/assets/onedesk/js/one_interface/frame.js"') < t["hooks"].index('"/assets/onedesk/js/one_interface/nav_tree.js"')
	assert "interfaceTree(props.win" in t["mail"] and "interfaceTree(props.win" in t["cloud"] and "win.tree(" in t["lists"]
	assert "one-interface-nav-alone" in t["frame"] and ".sidebar-item-container.one-interface-nav-alone" in t["css"]


def test_a_screen_with_a_tree_hands_its_rows_to_the_windows():
	"""OneCloud's folders, OneMail's mailboxes and a module's lists are one tree,
	the window's (one_interface/nav_tree.js), drawn as the rail's own rows; no screen
	draws a tree of its own, and a rail whose one row is the screen shows only
	the tree."""
	_windows_tree(TEXTS)
	for gone in ("cloud/CloudTree.vue", "mail/MailBoxes.vue"):
		assert not (tree.ROOT / "frontend" / "src" / gone).exists(), gone
	for path in tree.scoped((tree.ROOT / "frontend" / "src").rglob("*.vue")):
		assert 'role="tree"' not in path.read_text(encoding="utf-8"), path.name


OLD_NAMES = re.compile(
	r"onedesk\.window\b|one-window|\bone_window|\bWindowPart\b|\bwindow(?:Tree|Status|Search|Handles|Record|Part|Meters|HeadAction|Can|ModuleFoot|Foot\w*)\b"
	r"|js/window/|css/window/|\"One Window\"|data-window\b"
)


def old_names(text: str) -> list[int]:
	"""The lines that still call the window by an old name. Pure."""
	if not OLD_NAMES.search(text):
		return []
	return [number for number, line in enumerate(text.splitlines(), 1) if OLD_NAMES.search(line)]


def test_the_interface_has_one_name():
	"""OneInterface is the window's only name (onedesk/one_interface/AGENTS.md):
	the module, its folders, `onedesk.interface`, the `one-interface-*`
	classes, `page.interface` and the kit's `interface*` helpers. The
	browser's own `window` is the only window left in the code, and a patch
	that moves what was saved under the old name says it."""
	found = []
	for base in (tree.APP, tree.ROOT / "frontend" / "src", tree.ROOT / "tests"):
		for path in tree.scoped(base.rglob("*")):
			if path.suffix not in (".js", ".vue", ".css", ".py", ".html", ".json") or not path.is_file():
				continue
			if {"dist", "frontend", "node_modules", "__pycache__", "patches"} & set(path.relative_to(tree.ROOT).parts[1:-1]) or path == Path(__file__):
				continue
			found += [f"{path.relative_to(tree.ROOT)}:{number}" for number in old_names(path.read_text(encoding="utf-8", errors="ignore"))]
	assert not found, f"the window's old name is still used: {found[:20]}"


def _phone_reaches(t: dict) -> None:
	phone = t["phone_js"]
	assert '{ name: "apps"' in phone and "this.open_navigation()" in phone
	assert "frappe.boot.module_sidebars" in phone and "frappe.ui.sidebar_item.get_route" in phone
	groups = set(re.findall(r'data-group="(\w+)"', t["chrome"])) - {"find", "weather", "when"}
	carried = set(re.findall(r'\[data-group="(\w+)"\]', phone.split("TOOLS:", 1)[1].split("\n", 1)[0]))
	assert groups == carried, f"bar groups a phone cannot reach: {sorted(groups - carried)}"
	assert "phone.css" in t["hooks"] and "one_interface/phone.js" in t["hooks"]


def test_a_phone_reaches_every_app_and_every_bar_tool():
	"""A phone has no bars: its Apps tab opens frappe's navigation sheet,
	which searches every app's rail and carries each bar group that holds a
	tool, so nothing on the bars is reachable only from a desk."""
	_phone_reaches(TEXTS)


def _phone_address(t: dict) -> None:
	frame, phone_css, phone_js = t["frame"], t["phone_css"], t["phone_js"]
	assert 'button("address", "search"' in frame and 'if (name === "address") return this.address();' in frame
	assert "onedesk.interface.here()" in frame.split("open_awesomebar_from_global_search_shortcut = function", 1)[1].split("};", 1)[0]
	assert "one-head-tucked" in phone_js and "body.one-head-tucked .one-interface > .page-head" in phone_css
	bars = re.findall(r"background: var\((--one-[a-z-]+)\);", phone_css.split("@media (max-width: 767.98px) {", 1)[1].split("body.one-head-tucked", 1)[0])
	assert bars[:2] == ["--one-head-bg", "--one-head-bg"], bars


def test_a_phones_address_bar_is_typed_into_as_a_desks_is():
	"""On a phone the address bar's glass opens the address box (Ctrl+K's
	answers), the bar is the tab bar's material edge to edge, and it slides
	away as the page scrolls down."""
	_phone_address(TEXTS)


def _sheet_pull(t: dict) -> None:
	phone_js = t["phone_js"]
	pull = phone_js.split("\tpull(Sheet) {", 1)[1].split("\n\t},\n", 1)[0]
	assert "scrollTop > 0" in pull and 'sheet.close("swipe")' in pull and "passive: false" in pull
	assert 'Object.defineProperty(frappe.ui, "BottomSheet"' in phone_js


def test_a_sheet_closes_from_anywhere_at_its_top():
	"""frappe's sheet drags by its grip and header only; every sheet is also
	pulled down from its content while that is at the top."""
	_sheet_pull(TEXTS)


def _phone_search(t: dict) -> None:
	phone_js = t["phone_js"]
	find = phone_js.split("\tfind() {", 1)[1].split("\n\t},\n", 1)[0]
	assert find.index("$input[0].focus();") < find.index("requestAnimationFrame(")
	assert "new onedesk.interface.AddressBar(" in find
	assert 'one.name === "search"' in phone_js and "onedesk.interface.phone.find();" in phone_js
	assert "proto.address = function" in phone_js


def test_a_phones_search_drops_from_the_top_with_the_keyboard_up():
	"""The box is focused in the tap that opens it, which a phone needs to
	raise its keyboard, and every way into search on a phone lands there."""
	_phone_search(TEXTS)


SPOILS = [
	(_one_folder, "hooks", '"/assets/onedesk/js/one_interface/chrome.js",', ""),
	(_frame_places, "adapters.list", ".view({", ".places({"),
	(_adds_to_head, "frame", ".prependTo($content)", ".prependTo($content).detach()"),
	(_nav_pane, "frame", "NAV: { min: 180, max: 440", "NAV: { min: 0, max: 440"),
	(_browsers_history, "frame", "window.history.forward()", "history.go(1)"),
	(_cloud_on_window, "cloud_page", "fit: true", "fit: true, hide_sidebar: true"),
	(_every_view_on, "outside_js", "frappe", "set_trial(); frappe"),
	(_address_box, "outside_py", "del frappe.local.message_log[said:]", "pass"),
	(_one_reload, "adapters.list", "List.prototype.setup_page = function", "List.prototype.setup_page = function refresh: "),
	(_new_leads, "adapters.list", "primary: this.page.btn_primary", "own: this.page.btn_primary"),
	(_filter_and_sort, "frame", 'this.views_slot().prepend(controls.addClass("one-interface-filters"))', "this.views_slot().append(controls)"),
	(_one_gutter, "cloud_items", "rounded-full bg-surface-gray-3 px-2", "rounded-full bg-gray-200 px-2"),
	(_waits_late, "adapters.board", 'onedesk.interface.when(frappe.views, "KanbanV2Page"', 'Object.defineProperty(frappe.views, "KanbanV2Page"'),
	(_counted, "adapters.list", "const COUNTED = [", 'const COUNTED = ["Kanban", '),
	(_tree_as_list, "adapters.tree", 'controls: this.page.page_form.children(".tree-toolbar-actions")', "controls: null"),
	(_two_bars, "desk_js", "onedesk.interface.bars()", "onedesk.dock.bar = bar()"),
	(_workspace_colour, "company", "letter_heads.on(colour)", "luminance(colour) > 0.5"),
	(_taskbar, "frame", "onedesk.interface.place_status();", "onedesk.interface.status();"),
	(_rail_edge, "chrome_css", ".one-rail-mark > i {\n\theight: 20px;", ".one-rail-mark > i {\n\theight: 32px;"),
	(_flat_marks, "chrome_css", "svg.one-flat", "svg.one-flat { filter: drop-shadow(0 0 1px) }"),
	(_main_first, "views_css", '.custom-actions > :is([data-variant="solid"], .btn-primary),', ".custom-actions > .btn-primary,"),
	(_details_pane, "band", "onedesk.band.put(", "frm.dashboard.set_headline("),
	(_windows_tree, "nav", "onedesk.interface.Tree = class Tree", "onedesk.interface.Tree = class Rows"),
	(_phone_reaches, "phone_js", "this.open_navigation()", "this.open_apps()"),
	(_phone_address, "phone_js", "one-head-tucked", "one-head-hidden"),
	(_sheet_pull, "phone_js", 'sheet.close("swipe")', "sheet.close()"),
	(_phone_search, "phone_js", "proto.address = function", "proto.go = function"),
]


@pytest.mark.parametrize("rule, key, old, new", SPOILS, ids=[one[0].__name__.strip("_") for one in SPOILS])
def test_the_window_rules_catch_their_examples(rule, key, old, new):
	"""Each rule above holds on the window as it is and fails on the same
	texts with the one thing it guards spoiled."""
	bad = spoiled(key, old, new)
	with pytest.raises(AssertionError):
		rule(bad)


def test_the_window_scans_catch_their_examples():
	assert restyles(".one-card .one-interface-head { color: red; }") == [".one-card .one-interface-head { color: red; }"]
	assert not restyles(".one-interface .one-card { color: red; }")
	assert shared_marks("if (!List || List.prototype.one_interface) return;") == ["List.prototype.one_interface"]
	assert shared_marks("") == [""]
	assert not shared_marks('if (!List || Object.hasOwn(List.prototype, "one_interface")) return;')
	assert flat_problems([{"name": "onebook", "svg": "<svg/>"}, {"name": "onemail-flat", "svg": '<svg filter="x"/>'}], ["onebook", "onemail"]) == [
		"onebook has no flat twin",
		"onemail-flat",
	]
	assert not flat_problems([{"name": "onebook-flat", "svg": "<svg/>"}], ["onebook"])
	assert [n for n, _line in specifics('if (frm.doc.customer) frappe.set_route("List", "Sales Invoice");')] == [1, 1]
	assert not specifics('frappe.db.get_list("Note", {});')
	assert old_names("a\nonedesk.window.open()\n") == [2]
	assert not old_names("window.history.back()")
