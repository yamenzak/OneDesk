"""The window (docs/WINDOW.md): every screen in one frame made of frappe's own
parts. It adds to frappe's page head and never replaces it, styles itself in
one file, and OneCloud on its own page draws none of the parts the window
has. These read the code that says so."""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import tree

WINDOW_JS = tree.APP / "public" / "js" / "window"
WINDOW_CSS = tree.APP / "public" / "css" / "window"
FRAME = (WINDOW_JS / "frame.js").read_text(encoding="utf-8")
CHROME = (WINDOW_JS / "chrome.js").read_text(encoding="utf-8")
ADAPTERS = {path.stem: path.read_text(encoding="utf-8") for path in WINDOW_JS.glob("*.js") if path.stem not in ("frame", "chrome")}
JS = FRAME + "".join(ADAPTERS.values())
CSS = "".join(path.read_text(encoding="utf-8") for path in sorted(WINDOW_CSS.glob("*.css")))
HOOKS = (tree.APP / "hooks.py").read_text(encoding="utf-8")
CLOUD = (tree.APP / "public" / "js" / "onecloud.js").read_text(encoding="utf-8")


def _method(source: str, name: str) -> str:
	return source.split(f"\t{name}(", 1)[1].split("\n\t}\n", 1)[0]


def test_the_window_is_one_folder_loaded_after_the_shell():
	"""The window is js/window and css/window: the frame first, then one
	adapter per kind of view, every file of the folder loaded and nothing of
	it anywhere else."""
	scripts = re.findall(r'"/assets/onedesk/js/([\w./]+)"', HOOKS)
	assert scripts.index("window/frame.js") > scripts.index("shell.js")
	loaded = [one for one in scripts if one.startswith("window/")]
	assert loaded[:2] == ["window/frame.js", "window/chrome.js"]
	assert sorted(loaded) == sorted(f"window/{path.name}" for path in WINDOW_JS.glob("*.js"))
	styles = re.findall(r'"/assets/onedesk/css/(window/[\w.]+)"', HOOKS)
	assert styles[:2] == ["window/chrome.css", "window/frame.css"]
	assert sorted(styles) == sorted(f"window/{path.name}" for path in WINDOW_CSS.glob("*.css"))
	assert {"page", "list", "board", "report", "tree", "form", "print", "workspace"} <= set(ADAPTERS)
	assert not (tree.APP / "public" / "js" / "window.js").exists()


def test_a_view_says_what_it_has_and_the_frame_places_it():
	"""One place decides where a view's parts go: `view()` in frame.js. An
	adapter installs through `adapt(kind)` and hands over parts; it never
	reaches into the frame's rows itself, so a change to the layout is made
	once and every view follows."""
	view = _method(FRAME, "view")
	for part in ("primary", "commands", "menu", "controls", "views", "search", "status"):
		assert part in view, part
	for kind, source in ADAPTERS.items():
		assert f'onedesk.window.adapt("{kind}", () => {{' in source, kind
		assert ".view({" in source, kind
		for reach in ("$commands", "views_slot(", "win.handle(", "win.search(", "win.status(", "win.can("):
			assert reach not in source, f"{kind}.js reaches into the frame: {reach}"
	assert set(ADAPTERS) <= set(re.findall(r'"(\w+)"', FRAME.split("ON: [", 1)[1].split("covers(", 1)[0]))


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
		if "window" in path.parent.parts[-1:] or "dist" in path.parts:
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
	for asked in ("win.nav_slot()", "win.details(", "win.view("):
		assert asked in windowed, asked
	page = (tree.APP / "one_storage" / "page" / "onecloud" / "onecloud.js").read_text(encoding="utf-8")
	assert "window: true, fit: true" in page and "hide_sidebar" not in page


def test_only_the_trial_puts_lists_and_forms_on_the_window():
	trial = re.findall(r'"(\w+)"', FRAME.split("TRIAL: [", 1)[1].split("]", 1)[0])
	assert set(trial) == set(ADAPTERS) - {"page"} and 'ON: ["page"]' in FRAME
	assert "onedesk.window.trial() && onedesk.window.TRIAL.includes(kind)" in FRAME
	assert "frappe.views.ListView" in ADAPTERS["list"] and "frappe.ui.form.Form" in ADAPTERS["form"]
	assert "frappe.views.ListView" not in FRAME and "frappe.ui.form.Form" not in FRAME
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


def test_frappes_reload_is_the_one_in_the_address_row():
	"""Where frappe makes a reload button, that button is moved to the address
	row and the window's own Refresh steps aside; nothing duplicates it."""
	assert 'name === "refresh-cw"' in JS and "this.window.adopt_reload($button)" in JS
	assert "!!this.handlers.refresh && !this.$reload" in JS
	list_setup = ADAPTERS["list"].split("List.prototype.setup_page = function", 1)[1].split("\n\t};", 1)[0]
	assert "refresh:" not in list_setup


def test_each_wrapped_class_has_its_own_mark():
	"""ListView inherits from BaseList, so a mark set on BaseList's prototype
	reads as set on ListView's and skipped its wrappers: the list lost its
	search and its count. Each mark is asked of the prototype itself."""
	marks = re.findall(r"if \(!?\w+ (?:&&|\|\|) !?(Object\.hasOwn\(\w+\.prototype, \"one_window\"\)|\w+\.prototype\.one_window)\)", JS)
	assert marks and all(one.startswith("Object.hasOwn") for one in marks), marks


def test_a_lists_new_leads_the_command_row():
	"""A list's primary button (New) is frappe's own node moved to the start of
	the command row, as OneCloud's New is, and frappe's menu (…) follows it
	after a line. A form's Save leads the same way
	(test_the_main_action_is_always_first_on_the_left)."""
	list_setup = ADAPTERS["list"].split("List.prototype.setup_page = function", 1)[1].split("\n\t};", 1)[0]
	assert "primary: this.page.btn_primary" in list_setup
	assert "menu: { $button: this.page.menu_btn_group, dropdown: this.page.menu_dropdown }" in list_setup
	view = _method(FRAME, "view")
	assert 'menu.dropdown.align = "start"' in view
	order = re.findall(r'data-group="(\w+)"', FRAME)
	assert order == ["primary", "own", "menu"], order
	assert "~ .one-window-group:has(" in CSS and "::before" in CSS


def test_filter_and_sort_are_commands_and_the_heads_are_flat():
	"""A list's Filter and Sort are frappe's own buttons moved among the
	commands, before the view toggles; the column heads are drawn as
	OneCloud's are, words with a line under them."""
	assert 'this.views_slot().prepend(controls.addClass("one-window-filters"))' in FRAME
	assert 'controls: this.$page && this.$page.find(".filter-section").first()' in ADAPTERS["list"]
	assert '.one-window[data-one-view="list"] .list-row-head {' in CSS and "border-radius: 0;" in CSS


def test_every_row_sits_on_one_gutter():
	"""A list's own side margin and inset rows are taken away in the window,
	and the status row uses the command row's gutter, so every row starts and
	ends on the same edge; OneCloud's files sit on it too."""
	assert '.one-window[data-one-view="list"] .frappe-list {\n\t\tmargin-inline: 0;' in CSS
	assert ".one-window[data-one-view=\"list\"] .list-row-container,\n" in CSS
	cloud_css = (tree.APP / "public" / "css" / "onecloud.css").read_text(encoding="utf-8")
	assert ".oc-windowed .oc-head {\n\tpadding-inline: calc(var(--spacing) * 2);" in cloud_css


def test_a_view_frappe_loads_late_is_waited_for():
	"""Kanban v2 and the print view are defined when their code first loads,
	after ours; their adapters wait for frappe to assign the class rather
	than looking for it once and finding nothing."""
	assert 'onedesk.window.when(frappe.views, "KanbanV2Page"' in ADAPTERS["board"]
	assert 'onedesk.window.when(frappe.ui.form, "PrintView"' in ADAPTERS["print"]
	when = FRAME.split("\twhen(owner, name, then) {", 1)[1].split("\n\t},", 1)[0]
	assert "Object.defineProperty(owner, name" in when and "then(value)" in when


def test_only_views_of_pages_show_a_count_and_paging():
	"""A board, a calendar and a dashboard show all they hold, so the status
	row carries no count or paging for them; a list, a report and an image
	grid do."""
	source = ADAPTERS["list"]
	counted = source.split("const COUNTED = [", 1)[1].split("]", 1)[0]
	for view in ("Kanban", "Calendar", "Dashboard"):
		assert f'"{view}"' not in counted, view
	for view in ("List", "Report", "Image"):
		assert f'"{view}"' in counted, view
	assert "counted(this)) win.view({ status" in source


def test_a_tree_is_laid_out_as_a_list():
	"""A tree's Sort and Expand/Collapse sit before its view toggles, as a
	list's Filter and Sort do; its filters are the view row on the gutter, and
	frappe's centred column gives way to the window's width."""
	assert 'controls: this.page.page_form.children(".tree-toolbar-actions")' in ADAPTERS["tree"]
	assert '.one-window[data-one-view="tree"] .page-form {' in CSS
	assert '.one-window[data-one-view="tree"] .layout-main-section-wrapper > .layout-main-section {\n\t\tmax-width: none;' in CSS


def test_the_frame_is_a_top_bar_a_bottom_bar_and_the_rail():
	"""The shell's rail and bars are the window's frame: one bar across the
	top (where and when) and one across the bottom (what is running), never
	one that moves; frappe's rail draws from the frame's tokens; and the
	screen between them is inset with its corners rounded."""
	assert 'data-at="top"' in CHROME and 'data-at="bottom"' in CHROME
	for gone in ("place_bar", "one_bar", "Move This Bar"):
		assert gone not in CHROME, gone
	desk = (tree.APP / "public" / "js" / "desk.js").read_text(encoding="utf-8")
	assert "onedesk.dock.bar = " not in desk and "onedesk.window.bars()" in desk
	settings = (tree.APP / "one" / "settings.py").read_text(encoding="utf-8")
	assert "def place_bar" not in settings
	chrome_css = (WINDOW_CSS / "chrome.css").read_text(encoding="utf-8")
	for token in ("--dock-bg: var(--one-frame);", "--dock-ink: var(--one-frame-ink);", "--dock-tile-active: transparent;"):
		assert token in chrome_css, token
	assert "border-start-end-radius: var(--radius-lg);" in chrome_css and "border-end-start-radius: var(--radius-lg);" in chrome_css
	desk_css = (tree.APP / "public" / "css" / "desk.css").read_text(encoding="utf-8")
	assert ".one-bar {" not in desk_css and "one-bar-bottom" not in desk_css


def test_the_frame_wears_the_workspaces_colour():
	"""Frame Colour (Workspace › General › Contact and Branding, on the Company) is the
	frame's colour for everyone, with the ink that reads on it; a dark theme
	deepens it. Empty is One's own."""
	assert '"one_frame_colour"' in (tree.APP / "one" / "settings.py").read_text(encoding="utf-8")
	assert 'bootinfo["one_frame_colour"]' in (tree.APP / "one" / "boot.py").read_text(encoding="utf-8")
	assert "root.dataset.oneFrameInk" in CHROME and '"one_frame"' in CHROME
	company = (tree.APP / "one" / "company.py").read_text(encoding="utf-8")
	assert "letter_heads.on(colour)" in company, "the frame's ink is the letter heads' rule, not a second one"
	assert "luminance" not in CHROME.lower()
	chrome_css = (WINDOW_CSS / "chrome.css").read_text(encoding="utf-8")
	assert ':root[data-theme="dark"][data-one-frame="brand"]' in chrome_css
	assert ':root[data-one-frame-ink="dark"]:not([data-theme="dark"])' in chrome_css


def test_the_bottom_bar_is_a_taskbar():
	"""The window on screen shows its status (count, paging) at the start of
	the bottom bar, and the date and time close it, where Windows keeps its
	clock; the top bar opens with the workspace's name."""
	bottom = CHROME.split('data-at="bottom"', 1)[1].split("</footer>", 1)[0]
	assert bottom.index('class="one-bar-status"') < bottom.index('data-group="open"') < bottom.index('data-group="day"')
	assert bottom.rstrip().endswith('<div class="one-bar-group" data-group="when"><button class="one-bar-tool one-bar-now"></button></div>\n\t\t\t</div>')
	top = CHROME.split('data-at="top"', 1)[1].split("</header>", 1)[0]
	assert "one-bar-name" in top and "one-bar-now" not in top
	place = FRAME.split("\tplace_status() {", 1)[1].split("\n\t},", 1)[0]
	assert "current.$status.appendTo($slot)" in place and "win.$status.appendTo(win.$wrapper)" in place
	assert "onedesk.window.place_status();" in FRAME.split('$(document).on("page-change"', 1)[1]


def test_the_app_you_are_in_is_marked_on_the_rails_edge():
	"""As Discord marks a server: a bar of the frame's strongest ink on the
	rail's edge beside the active tile, a short one beside a hovered tile,
	and the tile itself unfilled. The tile list reaches the rail's edges so
	its scrolling box does not clip the bar."""
	chrome_css = (WINDOW_CSS / "chrome.css").read_text(encoding="utf-8")
	assert "body.one-barred .dock-item.active::before {\n\theight: 20px;" in chrome_css
	assert "body.one-barred .dock-item:hover::before {\n\theight: 8px;" in chrome_css
	assert "width: calc(100% + 16px);\n\tmargin-inline: -8px;" in chrome_css


def test_the_rails_marks_go_flat_on_a_workspace_colour():
	"""An app's mark on a frame of its own hue all but disappears, so on a
	workspace's colour the rail shows each mark's flat twin, generated beside it
	from the same SVG: no filter, no shadow, no box behind it."""
	chrome_css = (WINDOW_CSS / "chrome.css").read_text(encoding="utf-8")
	assert ':root[data-one-frame="brand"] body.one-barred .dock-item .dock-item-icon > svg.one-flat' in chrome_css
	assert "drop-shadow" not in chrome_css and "background-clip: content-box;" not in chrome_css
	assert 'frappe.utils.icon(`${entry.icon}-flat`' in CHROME
	icons = json.loads((tree.APP / "fixtures" / "custom_icon.json").read_text(encoding="utf-8"))
	names = {icon["name"] for icon in icons}
	for mark in (tree.ROOT / "brand").glob("*.svg"):
		assert f"{mark.stem}-flat" in names, mark.stem
	for icon in icons:
		if icon["name"].endswith("-flat"):
			assert "filter" not in icon["svg"] and "Gradient" not in icon["svg"], icon["name"]


def test_the_main_action_is_always_first_on_the_left():
	"""One rule for the command row: the solid main action leads it on the
	left, a list's New and a form's Save, Submit or Update alike; where a form
	has none, its own solid button (Record Payment) leads its run."""
	lists = (WINDOW_JS / "list.js").read_text(encoding="utf-8")
	forms = (WINDOW_JS / "form.js").read_text(encoding="utf-8")
	views = (WINDOW_CSS / "views.css").read_text(encoding="utf-8")
	assert "primary: this.page.btn_primary" in lists and "primary: this.page.btn_primary" in forms
	assert '.custom-actions > [data-variant="solid"] {\n\t\torder: -1;' in views
